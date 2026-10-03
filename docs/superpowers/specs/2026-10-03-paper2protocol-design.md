# paper2protocol — design

**Date:** 2026-10-03
**Status:** approved in brainstorming, pending spec review
**Context:** hackathon — working end-to-end code beats exhaustive tests and exception handling.

## Goal

Take a bioRxiv paper, identify the experiments it describes, let the user pick one, and
emit a simple numbered list of natural-language liquid-handling instructions (plates,
tubes, transfers). A separate downstream LLM (not built here) parses those instructions.

Also included: a deterministic sanity check and an LLM critic that reviews the output
against the source. A restricted-research screen is planned but **deferred (TODO)**.

## Non-goals (v1)

PDF parsing, non-bioRxiv sources, deck/labware mapping, the downstream parser LLM,
automatic revise loops, a UI, a gold-standard eval set, the restricted-research screen
(TODO, see below).

## Pipeline

```
ingest → [screen: TODO] → identify → (user picks) → extract → check → critic → render
```

| Module | In → Out | LLM? |
|---|---|---|
| `ingest.py` | DOI → `Paper` | no |
| `identify.py` | `Paper` → `list[Experiment]` | yes |
| `extract.py` | `Paper`, `Experiment` → `Protocol` | yes |
| `check.py` | `Protocol` → `list[CheckIssue]` | no |
| `critic.py` | `Paper`, `Experiment`, `Protocol` → `CriticReport` | yes |
| `render.py` | `Protocol` → numbered NL text | no |
| `llm.py` | shared Anthropic wrapper + disk cache | — |
| `models.py` | Pydantic models | — |
| `cli.py` | entry point | — |

Location: top-level package `paper2protocol/` in this repo, added to `pyproject.toml`
with a `paper2protocol` console script.

## Components

### ingest
- `GET https://api.biorxiv.org/details/biorxiv/<DOI>` → metadata including the latest
  version's JATS XML URL. Fetch and parse with `lxml`.
- `Paper`: `doi`, `title`, `abstract`, `sections: list[Section]` (id, heading path, text),
  `figure_legends: list[Legend]`.
- Section ids are stable (`s1`, `s1.2`, …) so later stages can reference them.
- No JATS available → raise with a clear message (no PDF fallback).
- **Stretch:** `search "<title words>"` via the Europe PMC REST search API (preprints,
  `SRC:PPR`, publisher bioRxiv) → list of (title, DOI) to choose from.

### screen — TODO (not implemented in v1)
Not built now. Leave a `# TODO: restricted-research screen` at the point in `cli.py`
between ingest and identify where it will gate the pipeline. Intended future design:
runs first on title + abstract + Methods; team-owned policy file; verdict
`allow | block | review`; anything but `allow` stops before experiments are listed;
no CLI bypass.

### identify — experiments, not sections
Methods subsections are not 1:1 with experiments; one workflow often chains several
subsections (e.g. cell culture → transfection → luciferase assay, with buffer recipes from
a reagents section), and one subsection can serve several experiments.

- Input: full section list plus Results text and figure legends (which reveal what was
  actually combined).
- `Experiment`: `id`, `title`, `goal`, `section_refs: list[str]` (ordered), `shared_refs`
  (recipes/reagent sections), `unresolved_refs: list[str]` ("as described previously"),
  `liquid_handling_fraction` hint (`mostly | partly | little`) to help users choose,
  `figure_refs: list[str]` — the figures/panels whose data this experiment produces
  (e.g. `["Fig 2A-C", "Supp Fig S3"]`), taken from Results citations and figure legends.
- Ingest keeps each legend's label (`Figure 2`, `Figure S3`) so `figure_refs` can be
  matched to real figures; refs the model gives that don't match a known legend label are
  kept but marked unverified.

### extract
- Input: paper text restricted to the experiment's `section_refs` + `shared_refs`, plus
  the experiment description.
- `Protocol`:
  - `containers: list[Container]` — `name`, `kind` (`96-well plate | tube | reservoir | other`),
    `max_volume_ul`, `assumed: bool`
  - `initial_contents: list[Content]` — container/well, reagent, volume_ul
  - `steps: list[Step]`, each one of:
    - `transfer`: source (container + wells), dest (container + wells), volume_ul per dest,
      reagent, optional mix
    - `mix`: container + wells, volume_ul, repetitions
    - `manual`: free-text action (incubate, centrifuge, thermocycle, read) + params
  - every step: `source_quote` (verbatim from paper, may be empty), `assumed: bool`,
    `note`
  - `assumptions: list[str]` — every value not stated in the paper
- Gaps are filled with sensible defaults (96-well plate, 1.5 mL tubes, reservoirs) and
  recorded as assumptions; never block.

### check (deterministic)
Light bookkeeping, no deck/tip simulation:
- track per-well/tube volume from `initial_contents` through transfers;
  flag withdrawals exceeding contents, and fills exceeding `max_volume_ul`
- every non-manual step has volume, source, dest
- every source container/well is filled before first use
Output `list[CheckIssue(step_index, severity, message)]`.

### critic (LLM)
Compares `Protocol` against the source sections: missing/reordered steps, numbers that
don't match the paper, unreasonable assumptions, check-issue explanations.
Output `CriticReport(verdict: "ok" | "minor_issues" | "major_issues", issues: list[...])`.
Advisory only.

### render (deterministic)
Numbered plain-English lines, e.g.:

```
1. Add 100 µL of DMEM + 10% FBS to wells A1–H12 of 96-well plate "plate1".
2. Transfer 10 µL from tube "cells" to each well A1–H12 of plate1. [assumed: tube label]
3. MANUAL: Incubate plate1 for 24 h at 37 °C, 5% CO2.

Containers: ...
Assumptions: ...
```

## LLM layer (`llm.py`)

- One function, roughly `structured(stage, system, content, schema) -> schema instance`,
  using the Anthropic Python SDK's structured-output parse helper with Pydantic models.
- API key: `ANTHROPIC_API_KEY` in `.env`, loaded with `python-dotenv` (`.env` is gitignored).
- Per-stage config in one dict:

  | Stage | Model | Effort |
  |---|---|---|
  | identify | `claude-sonnet-5-5` | medium |
  | extract | `claude-sonnet-5-5` | high |
  | critic | `claude-sonnet-5-5` | high |

  Do **not** use Fable or Opus 5.5 (biology content). `claude-haiku-4-5` is an option for
  cheap stages; upgrade only if testing shows Sonnet struggling.
- Refusals: on `stop_reason == "refusal"` raise `LLMRefusal(stage, category)`; CLI
  reports it and stops. No automatic model fallback.
- Paper text is placed first in each request with `cache_control` so identify/extract/
  critic on one paper reuse Anthropic's prompt cache.

### Disk cache
- Key: sha256 of canonical JSON (sorted keys) of the full request — model, system,
  messages, output schema, max_tokens, thinking/effort config — plus `CACHE_VERSION`.
  API key excluded.
- Stored at `.cache/llm/<first 2 hex>/<hash>.json` (gitignored): request, raw response,
  usage, model, timestamp, `refusal` flag.
- Modes via `--cache {use,refresh,off,only}`; default `use`. `only` = offline, miss is
  an error. Refusals are cached; `refresh` retries them.

## CLI

```
paper2protocol list <DOI>                    # ingest → identify; prints numbered experiments with their figure refs
paper2protocol convert <DOI> --experiment N  # extract → check → critic → render
paper2protocol search "<title words>"        # stretch
```

Example `list` output:

```
1. Luciferase reporter assay in HEK293T        [Fig 2A-C]       liquid handling: mostly
   sections: Cell culture → Transfection → Luciferase assay
2. qPCR of target genes after knockdown         [Fig 3B, S4]     liquid handling: mostly
3. Confocal imaging of fixed cells              [Fig 1D]         liquid handling: little
```

`list` caches its result, so `convert` reuses it without re-calling the LLM.

Output dir `out/<doi-slug>/`:
`paper.json`, `experiments.json`, and per experiment `exp<N>/`:
`protocol.json`, `protocol.txt`, `check.json`, `critic.json`.

## Error handling (hackathon level)

- Fail fast with a readable message for: unknown DOI, missing JATS,
  LLM refusal.
- One retry on structured-output validation failure, then raise.
- Everything else: let exceptions propagate.

## Testing (hackathon level)

- `check.py`: a few unit tests on hand-built `Protocol` objects (the one piece where
  silent arithmetic bugs matter).
- One end-to-end smoke test on a fixture paper with `--cache only` and recorded cache
  entries in `tests/fixtures/llm_cache/`.

## Dependencies

`anthropic`, `httpx`, `lxml`, `pydantic`, `python-dotenv`; `pytest` (dev).
