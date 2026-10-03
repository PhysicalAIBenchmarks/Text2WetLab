"""The only module that talks to Anthropic: structured output + on-disk response cache.

Cache key = sha256 of the exact request (model, system, messages, output schema, limits)
plus CACHE_VERSION, so an identical call to an identical model is served from disk.
"""

import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import TypeVar

import anthropic
from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError

from . import guard

load_dotenv()

CACHE_VERSION = 1
CACHE_DIR = Path(os.environ.get("P2P_CACHE_DIR", ".cache/llm"))
CACHE_MODE = os.environ.get("P2P_CACHE_MODE", "use")  # use | refresh | off | only

# Per-stage model config. Sonnet by default; Fable / Opus 5.5 are not used for this
# biology content. Bump a single stage here if it struggles.
STAGES: dict[str, dict] = {
    "identify": {"model": "claude-sonnet-5-5", "effort": "medium", "max_tokens": 32000},
    "resolve": {"model": "claude-sonnet-5-5", "effort": "high", "max_tokens": 64000},
    "extract": {"model": "claude-sonnet-5-5", "effort": "high", "max_tokens": 64000},
    "critic": {"model": "claude-sonnet-5-5", "effort": "high", "max_tokens": 32000},
}

# Server-side web tools (run on Anthropic's side; no client loop needed). Code hosts are
# blocked so the model can't copy the authors' scripts (see guard.py). Per-call caps can be
# raised with P2P_WEB_SEARCH_MAX / P2P_WEB_FETCH_MAX when resolve runs out of quota.
WEB_TOOLS = [
    {"type": "web_search_20260209", "name": "web_search",
     "max_uses": int(os.environ.get("P2P_WEB_SEARCH_MAX", 8)), "blocked_domains": guard.BLOCKED_DOMAINS},
    {"type": "web_fetch_20260209", "name": "web_fetch",
     "max_uses": int(os.environ.get("P2P_WEB_FETCH_MAX", 10)), "blocked_domains": guard.BLOCKED_DOMAINS},
]
# Every web search/fetch/result seen by tool-using calls, for guard.audit(). Callers clear it.
WEB_EVENTS: list = []

SYSTEM = (
    "You are an expert wet-lab scientist helping convert published biology methods into "
    "precise, executable liquid-handling instructions. Be faithful to the paper: never "
    "invent results, and mark anything not stated in the paper as an assumption."
)

T = TypeVar("T", bound=BaseModel)
_client: anthropic.Anthropic | None = None


class LLMRefusal(RuntimeError):
    def __init__(self, stage: str, category: str | None, explanation: str | None):
        self.stage, self.category = stage, category
        super().__init__(f"Model declined the {stage} request (category={category}): {explanation or ''}")


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


def cache_key(req: dict) -> str:
    blob = json.dumps({"cache_version": CACHE_VERSION, **req}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode()).hexdigest()


def _cache_path(key: str) -> Path:
    return CACHE_DIR / key[:2] / f"{key}.json"


def _call(stage: str, req: dict) -> dict:
    """Return the response as a plain dict, from cache when allowed."""
    key = cache_key(req)
    path = _cache_path(key)
    if CACHE_MODE in ("use", "only") and path.exists():
        print(f"  [{stage}] cache hit {key[:10]}", file=sys.stderr)
        return json.loads(path.read_text())["response"]
    if CACHE_MODE == "only":
        raise RuntimeError(f"[{stage}] cache miss {key[:10]} in cache-only mode")

    print(f"  [{stage}] calling {req['model']} ...", file=sys.stderr)
    t0 = time.time()
    with _get_client().messages.stream(**req) as stream:
        msg = stream.get_final_message()
    resp = msg.to_dict(mode="json")
    u = resp.get("usage", {})
    web = u.get("server_tool_use") or {}
    print(f"  [{stage}] done in {time.time() - t0:.0f}s — in {u.get('input_tokens')} "
          f"(cache write {u.get("cache_creation_input_tokens")}, read {u.get("cache_read_input_tokens")}), out {u.get('output_tokens')}"
          + (f", web searches {web.get('web_search_requests')}, fetches {web.get('web_fetch_requests')}" if web else ""),
          file=sys.stderr)

    if CACHE_MODE != "off":
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({
            "key": key, "stage": stage, "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "refusal": resp.get("stop_reason") == "refusal", "request": req, "response": resp,
        }, ensure_ascii=False, indent=1))
    return resp


def structured(stage: str, context: str, task: str, schema: type[T], tools: list[dict] | None = None) -> T:
    """Run one stage. `context` (paper text) is sent first and marked for prompt caching;
    `task` holds the stage-specific instructions. `tools` = server tools such as WEB_TOOLS."""
    cfg = STAGES[stage]
    req = {
        "model": cfg["model"],
        "max_tokens": cfg["max_tokens"],
        "system": SYSTEM,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": context, "cache_control": {"type": "ephemeral"}},
            {"type": "text", "text": task},
        ]}],
        "output_config": {
            "effort": cfg["effort"],
            "format": {"type": "json_schema", "schema": anthropic.transform_schema(schema)},
        },
    }
    if tools:
        req["tools"] = tools
    first_req = req
    for attempt in range(2):
        resp = _call(stage, req)
        # Server-tool loops can pause; resume by re-sending the paused assistant turn.
        WEB_EVENTS.extend(guard.web_events(resp))
        for _ in range(5):
            if resp.get("stop_reason") != "pause_turn":
                break
            req = {**req, "messages": req["messages"] + [{"role": "assistant", "content": resp["content"]}]}
            resp = _call(stage, req)
            WEB_EVENTS.extend(guard.web_events(resp))
        if resp.get("stop_reason") == "refusal":
            sd = resp.get("stop_details") or {}
            raise LLMRefusal(stage, sd.get("category"), sd.get("explanation"))
        if resp.get("stop_reason") == "max_tokens":
            raise RuntimeError(f"[{stage}] hit max_tokens={cfg['max_tokens']}; raise it in llm.STAGES")
        # With tools, earlier text blocks are commentary; the JSON answer is the last one.
        text = [b["text"] for b in resp["content"] if b["type"] == "text"][-1]
        try:
            return schema.model_validate_json(text)
        except ValidationError:
            if attempt:
                raise
            print(f"  [{stage}] output failed validation, retrying uncached", file=sys.stderr)
            _cache_path(cache_key(req)).unlink(missing_ok=True)
            req = first_req
    raise AssertionError("unreachable")
