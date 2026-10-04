# L_other: non-Opentrons task candidates

Tasks whose source paper drives a machine other than an Opentrons OT-2. They sit beside the OT-2 tasks of #36 (`tasks/<task>/` with `public/`, `private/`, `harbor/` and a `task.toml` whose `[[source]]` names the paper). Papers go under `sources/<slug>/` exactly as in #36.

Run 2026-10-04. **Licence was not used to filter**: all 12 candidate papers were ingested (`scripts/ingest.py`) and run through `paper2protocol list`. Licence stays in each `record.json` as the `redistributable` flag, and each new slug's `pipeline/paper.json` (verbatim text) is gitignored, as #36 does for non-CC papers. Nothing is published: this is a local branch, and `master.csv` now has rows for these papers, so check it before any HuggingFace deploy.

## What the ingest found

"Experiments" are the workflows `list` found; "LH" is how many it rates liquid handling `mostly`.

| Slug | Machine | PDF + full text | Code | Experiments (LH mostly) |
|---|---|---|---|---|
| `chory-2021-hamilton` | Hamilton STARlet + CLARIOstar | yes | 4 repos cloned | 5 (5) |
| `debenedictis-2022-prance` | Hamilton STARlet + CLARIOstar | **no** (paywalled; Europe PMC 500) | `std-96-pace` cloned | not run, no text |
| `wrmxpress` | ImageXpress Nano | yes | **not cloned** (748 MB) | 5 (1) |
| `wrmxpress-gui` | ImageXpress Nano | yes | cloned | 1 (0) |
| `glas-preciseflex` | Brooks PreciseFlex | **no** (RSC PDF not found) | both repos cloned | not run, no text |
| `aros-cellpainting` | Liconic STX | yes | 3 repos cloned | 1 (1) |
| `electroporation-bayesopt` | BTX Gemini X2 (comparison) | yes | cloned | 6 (3) |
| `lustro` | Tecan Spark | yes | cloned (no `.py`) | 7 (0) |
| `optoplate-ml` | Tecan Spark | yes | Optoplate-96 cloned; `zavalab/ML` **not cloned** (1.8 GB) | 4 (0) |
| `litos` | LED hardware | yes | cloned (C firmware) | 7 (1) |
| `auto-qpcr` | QuantStudio data | yes | cloned | 4 (0) |
| `uc2-hi2` | OT-2 + UC2 microscope | **no** (protocols.io) | cloned | not run, no text |

## Which are addable as tasks

Judged on what `list` found, not on licence. Still no task has been converted: see the blockers below.

- **Addable first:** `chory-2021-hamilton` (5 of 5 experiments mostly liquid handling, code is real Hamilton scripts), `aros-cellpainting` (a single large Cell Painting screen, 84 `.py` files in `robotlab`), `electroporation-bayesopt` (3 experiments mostly liquid handling, incl. the Bayesian-optimisation run).
- **Addable with work:** `wrmxpress` (one `mostly` experiment, the fecundity assay), `litos` (one `mostly`, the MAPK-inhibitor drug screen, but the device is LED hardware).
- **Needs text first:** `debenedictis-2022-prance` and `glas-preciseflex` have code but no full text. Give `ingest.py` a PDF with `--pdf-url` once one is found, or point to a local PDF.
- **Weak:** `wrmxpress-gui`, `optoplate-ml` (all `partly`) and `lustro` (all `little`) are optogenetics/imaging with light handling, not pipetting; they would make thin liquid-handling tasks.
- **Not a protocol:** `auto-qpcr` is a data-analysis app (all `partly`, about the analysis), and `uc2-hi2` is an OT-2 protocol that belongs to the L2 stream. AssemblyTron is already `golden-gate-assembly` in #36, not L_other.

## Blockers for converting any of them

- `paper2protocol convert` emits Opentrons IR. `Step.kind` is only `transfer`/`mix`/`manual` on this branch, so the 16 non-OT kinds in the uncommitted `models.py` change (`backup/l2-outputs-oct04` worktree) are needed first.
- `check.py` calls `opentrons_simulate`, which cannot validate Hamilton or imager protocols, so grading needs the `instrument_family` gate (`feat/nonot-checker`).
- Some `list` outputs defer details elsewhere (Chory: "Supplemental methods", Fig 2A deck layout), which `assess` may reject as under-specified.

## Proposed PR stack

All cut from `origin/feat/ingestion` (#36's head), in this order.

1. `feat/l-other-tasks` (this branch): this doc, the 12 `sources/<slug>/` records and `pipeline/experiments.json`, `sources.json` entries, rebuilt `master.csv`, `.gitignore` entries for the new `paper.json` files.
2. `feat/nonot-step-kinds`: `paper2protocol/models.py`.
3. `feat/l-other-hamilton-clariostar`: `chory-2021-hamilton` (+ `debenedictis-2022-prance` once it has text).
4. `feat/l-other-liconic-pharmbio`: `aros-cellpainting`.
5. `feat/l-other-electroporation`: `electroporation-bayesopt` (needs an IR for an optimisation loop).
6. `feat/l-other-imagexpress`: `wrmxpress`.
7. `feat/nonot-checker`.

## Corrections to the pasted table

Paper dates and attributions that did not hold: AssemblyTron was published 2022, not 2023. "Harmer 2024, microPublication" LITOS resolved to a Pertz-lab 2022 Sci Rep paper. Ouyang 2021 bioRxiv UC2-Hi2 resolved to a protocols.io protocol.
