"""Leak guard: the protocol must be reconstructed from the paper's text, not copied from code
or scripts the authors published (e.g. an Opentrons .py protocol in the supplementary files).

Three layers:
  1. resolve's prompt forbids fetching the paper's own code/supplementary files;
  2. code-hosting domains are blocked in the web tools (BLOCKED_DOMAINS);
  3. audit() inspects every URL the model searched/fetched and flags suspicious ones,
     because same-domain supplementary files (e.g. journals.plos.org/...s001) can't be
     blocked by domain.
"""

import re
from urllib.parse import unquote

from pydantic import BaseModel

from .models import Paper

# Applied to both web_search and web_fetch. Plain hostnames only (subdomains covered).
BLOCKED_DOMAINS = [
    "github.com", "githubusercontent.com", "gitlab.com", "bitbucket.org",
    "protocols.opentrons.com", "library.opentrons.com",
]

CODE_EXT = re.compile(r"\.(py|ipynb|r|rmd|m|jl|ot2|zip|tar|gz)(\?|#|$)", re.I)
SUPP_HINT = re.compile(r"type=supplementary|supplementary[-_ ]?(material|file|data)|/suppl|/bin/|figshare|zenodo|\.s0\d\d", re.I)


class WebEvent(BaseModel):
    kind: str           # "fetch" (page opened), "search" (query run), "result" (URL listed in results)
    value: str          # URL or query


class Flag(BaseModel):
    severity: str       # "accessed" = page was fetched; "seen" = only listed/queried
    value: str
    reason: str


def web_events(resp: dict) -> list[WebEvent]:
    """Pull every searched query / fetched URL / listed result URL out of a raw response dict."""
    events = []
    for b in resp.get("content", []):
        t = b.get("type")
        if t == "server_tool_use" and b.get("name") == "web_fetch":
            events.append(WebEvent(kind="fetch", value=str(b.get("input", {}).get("url", ""))))
        elif t == "server_tool_use" and b.get("name") == "web_search":
            events.append(WebEvent(kind="search", value=str(b.get("input", {}).get("query", ""))))
        elif t == "web_search_tool_result" and isinstance(b.get("content"), list):
            events += [WebEvent(kind="result", value=r.get("url", "")) for r in b["content"] if r.get("url")]
        elif t == "web_fetch_tool_result" and isinstance(b.get("content"), dict) and b["content"].get("url"):
            events.append(WebEvent(kind="fetch", value=b["content"]["url"]))
    return events


def audit(events: list[WebEvent], paper: Paper) -> list[Flag]:
    doi = paper.doi.lower()
    doi_tail = doi.split("/", 1)[-1]
    flags, seen = [], set()
    for e in events:
        v = unquote(e.value).lower()
        reasons = []
        if e.kind == "search":
            if re.search(r"\.py\b|python script|source code|github|opentrons protocol|supplementary", v):
                reasons.append("search query looks for code/supplementary files")
        else:
            if CODE_EXT.search(v.split("?")[0]) or CODE_EXT.search(v):
                reasons.append("code/script/archive file")
            if any(d in v for d in BLOCKED_DOMAINS):
                reasons.append("code-hosting site")
            if (doi in v or doi_tail in v) and SUPP_HINT.search(v):
                reasons.append("this paper's supplementary files")
        key = (e.kind, v)
        if reasons and key not in seen:
            seen.add(key)
            flags.append(Flag(severity="accessed" if e.kind == "fetch" else "seen",
                              value=e.value, reason="; ".join(reasons)))
    return flags


PROMPT_RULE = (
    "IMPORTANT: the protocol must be reconstructed from the paper's text. Do NOT search for, "
    "open or use this paper's own code, scripts, robot protocol files (e.g. .py, notebooks, "
    "Opentrons protocols), code repositories or supplementary files. Cited OTHER papers and "
    "commercial kit manuals are fine."
)
