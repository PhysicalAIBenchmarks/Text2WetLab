# paper2protocol

bioRxiv paper → experiments (with figure links) → numbered natural-language liquid-handling
instructions (96-well plates, tubes, reservoirs) for a downstream parser LLM.

Design: `docs/superpowers/specs/2026-10-03-paper2protocol-design.md`

## Usage

Needs `ANTHROPIC_API_KEY` in `.env`.

```bash
uv run paper2protocol search "KDM2B HIF"                       # find DOIs by title words
uv run paper2protocol list 10.64898/2026.03.26.714448           # numbered experiments + figures
uv run paper2protocol convert 10.64898/2026.03.26.714448 -e 1   # instructions + checks + critic
```

Outputs go to `out/<doi>/`: `paper.json`, `experiments.json`, and `exp<N>/` with
`protocol.json`, `protocol.txt` (the deliverable), `check.json`, `critic.json`.

Full text comes from bioRxiv JATS XML, falling back to Europe PMC. If both fail
(bioRxiv sometimes rate-limits), download the XML in a browser and pass `--xml file.xml`.

## Pipeline

`ingest → [screen: TODO] → identify → extract → check → critic → render`

- `identify` groups Methods subsections into bench workflows and links them to figures
  (`?` = figure label not found in the paper, typically supplementary figures).
- `extract` produces a typed `Protocol`; anything not in the paper is marked `[assumed]`.
- `check` is deterministic volume bookkeeping (over-draws, capacity, unfilled sources).
- `critic` is an LLM review against the source text; advisory only.

## LLM settings and cache

Per-stage model/effort live in `llm.STAGES` (Sonnet 5.5 by default; don't use Fable or
Opus 5.5 for this biology content). Every response is cached in `.cache/llm/`, keyed on the
exact request, so re-runs are free. `--cache refresh` re-calls, `--cache off` bypasses,
`--cache only` is offline (a miss is an error).

## Tests

```bash
uv run pytest -q
```

`tests/test_pipeline.py` replays recorded responses from `tests/fixtures/kdm2b/llm_cache`.
After changing a prompt, schema or model, re-run the CLI on that paper and copy
`.cache/llm/` over the fixture cache.
