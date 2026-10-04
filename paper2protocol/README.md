# paper2protocol

Paper (bioRxiv, PLOS, or any open-access article in Europe PMC) → experiments (with figure links) → numbered natural-language liquid-handling
instructions (96-well plates, tubes, reservoirs) for a downstream parser LLM.

Design: `docs/superpowers/specs/2026-10-03-paper2protocol-design.md`

## Usage

Needs `ANTHROPIC_API_KEY` in `.env`.

```bash
uv run paper2protocol search "KDM2B HIF"                       # find DOIs by title words (--biorxiv: preprints only)
uv run paper2protocol list 10.64898/2026.03.26.714448           # numbered experiments + figures
uv run paper2protocol assess 10.64898/2026.03.26.714448 -e 1    # enough detail to run it? (web research)
uv run paper2protocol convert 10.64898/2026.03.26.714448 -e 1   # assess → instructions + checks + critic
```

`convert` runs `assess` first and stops if the verdict is `reject` (`--force` overrides,
`--skip-assess` skips it, `--no-web` assesses without web research).

Outputs go to `data/pipeline_runs/<doi>/`: `paper.json`, `experiments.json`, and `exp<N>/` with
`sufficiency.json`, `web_access.json`, `protocol.json`, `protocol.txt` (the deliverable), `check.json`, `critic.json`.

The paper can be a DOI, a doi.org link or a publisher URL (e.g.
`https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0246302`).

Full text comes from the sources in `sources.py`, tried in order: Europe PMC (most
open-access journals via PMC, plus preprints; tables as text), PLOS, bioRxiv. Force one with
`--source`, or pass a downloaded JATS file with `--xml file.xml`. To add a publisher, write a
fetch function returning JATS XML and append a `Source` to `SOURCES`.

## Leak guard

The protocol must come from the paper's text, not from the authors' own code (e.g. an
Opentrons `.py` in the supplementary files). `guard.py` (1) tells the research model not to
use the paper's code/supplementary files, (2) blocks code-hosting domains (GitHub, GitLab,
Opentrons protocol library) in the web tools, and (3) audits every searched/fetched URL.
Flags print as `!! LEAK FLAG`, are logged in `exp<N>/web_access.json`, and an opened
flagged URL adds a warning to the top of `protocol.txt`.

## Pipeline

`ingest → [screen: TODO] → identify → resolve → extract → check → critic → render`

- `identify` groups Methods subsections into bench workflows and links them to figures
  (`?` = figure label not found in the paper, typically supplementary figures).
- `resolve` lists the details needed to run the experiment, researches gaps with Anthropic's
  server-side web search/fetch (cited papers via the reference DOIs, kit manuals), marks each
  gap resolved / assumable / missing, and returns proceed / proceed_with_assumptions / reject.
  Its findings are passed to `extract` and `critic`. It costs the most: roughly 2 min and
  ~$1 per experiment, because fetched pages are re-read across tool steps.
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

`tests/test_pipeline.py` replays recorded responses from `tests/fixtures/plos_rna/llm_cache`
(PLOS ONE 10.1371/journal.pone.0246302, experiment 2).
After changing a prompt, schema or model, re-run `list` and `convert -e 1` on that paper,
copy the hit cache entries into the fixture cache, and strip non-text content blocks
(web-fetch results make entries several MB).
