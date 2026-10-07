# Risks

Written after ingesting 36 papers (31 PDFs, 36 codebases) into `sources/master.csv`. Each risk says what we saw,
how bad it is, and what is already done about it. "Seen" means observed in this repo, not hypothetical.
Open work is tracked as GitHub issues labelled `unmet-ask`.

Severity: **High** = can invalidate the benchmark or break a licence; **Medium** = distorts results or wastes
money; **Low** = annoying.

## 1. Legal and licensing

| # | Risk | Seen | Sev | Mitigation / state |
|---|---|---|---|---|
| L1 | Redistributing third-party code with no licence | 15 of 36 papers have at least one repository with no licence (BOTany, TransporterScreening, HULP, LAPrepository, OpenLC, ...). The public HF dataset already holds 41 `ref/` files, 24 of them unlicensed | High | `scripts/deploy_hf.py` is an allowlist and `sources/<slug>/code/` is never published. **Existing HF files are still live** (issue filed) |
| L2 | Copyleft code in a permissively licensed benchmark | APEX `apex-nf` is AGPL-3.0, covid19clinic is GPL-3.0, sidekick is CERN-OHL-S | High | Recorded `redistributable = no`; never vendored. APEX is the best real reference for two tasks and is therefore unusable as shipped code |
| L3 | PDFs are not ours to publish | 4 PDFs are `no` (CC BY-NC-ND, bioRxiv "cc_no", CC BY-NC); 2 are `unknown` (Elsevier COVID permission) | High | PDFs live only in a cache outside the repo; records keep URL + SHA-256 + licence; `deploy_hf.py` refuses any `.pdf`; a test enforces it |
| L4 | The Harbor oracle is a copy of an unlicensed script | `solution/protocol.py` equals the HULP authors' script, upstream has no licence | High | Excluded from HF; **still in the public GitHub repo** (issue filed) |
| L5 | A site's terms may forbid scripted downloads | Every publisher site bot-blocked the scripts; only official open-data routes worked | Medium | We use Europe PMC / PMC Open Access S3 / bioRxiv API; agents were told not to bypass bot checks or use shadow libraries, and did not |

## 2. Provenance: is each claim about a source actually true?

| # | Risk | Seen | Sev |
|---|---|---|---|
| P1 | A task attributed to a source that does not contain it | `ampure-bead-cleanup` was credited to "Pioneer NGS"; its repo has no AMPure step (it is a Hamilton/PyLabRobot consolidation + PCR setup). The master CSV now marks the link "claimed, NOT supported" | High |
| P2 | Wrong description of a source | ProxyViscometer was described as timing aspiration; the paper measures dispense flow gravimetrically | Medium |
| P3 | Low-confidence identification | POLAR robot 1 is matched only to the POLAR PLOS ONE paper, which never mentions Opentrons; its OT-2 variant is a protocols.io entry marked "in development" | Medium |
| P4 | Same study, two DOIs, or code at the wrong version | BOTany is a preprint plus a published version; DNA-BOT's paper links branch `oup_synbio`, the default branch differs (we pin `ae9aebb`); code commits are "latest", not "at publication" | Medium |
| P5 | Origin claims that do not hold | "Every candidate came from Amass" was false for the earlier pipeline outputs: of the 7 papers behind them only AssemblyTron and DNA-BOT were on the Amass list (all 24 Amass papers are now in the source list) | Low |

## 3. Data quality of the ingestion itself

| # | Risk | Seen | Sev | State |
|---|---|---|---|---|
| D1 | Experiment splits written by language models | 74 of 113 rows are hand-read by agents, 39 come from the pipeline's `identify`. Agents also disagreed with detectors (e.g. 0 vs 2 Opentrons scripts in TransporterScreening) | Medium | Rows are labelled by source; the pipeline's split wins where it exists; **no human has checked the hand-read splits** |
| D2 | Code detectors miss real Opentrons code | Scripts that never `import opentrons` were counted as 0; fixed by also matching `load_labware(`/`protocol_api` | Low | fixed, tested |
| D3 | Papers whose full text the pipeline cannot read | The pipeline only accepts JATS XML. Two JoVE papers, the SLAS paper and the MALDI paper have none, so they cannot be split by the pipeline at all | Medium | issue filed (needs a PDF-text path) |
| D4 | 5 papers have no PDF | 4 paywalled or bot-blocked, 1 not identified | Medium | list in `master.csv` (`pdf_status`) |
| D5 | Artifacts held outside git | 110 MB of PDFs and 1.3 GB of clones sit in `~/.cache`; a re-run depends on the network and on sites not changing | Medium | records hold SHA-256 so a re-download is verifiable; no backup exists |
| D6 | Re-running the ingest script clobbering curated fields | An agent warned about it; the script overwrote notes and could loosen a licence | Medium | fixed: curated fields kept, a stored "no" can never become "yes"; tested |
| D7 | Work lost between sessions | The 24-paper candidate list and three papers' pipeline outputs existed only as untracked files in another checkout | Medium | now committed |

## 4. Re-running the pipeline (paper -> IR)

| # | Risk | Seen | Sev | State |
|---|---|---|---|---|
| R1 | Cost | `scripts/rerun_plan.py` (free token counts): about $10-27 in tokens for 23 papers to identify and 38 experiments to convert on `claude-sonnet-5-5`; web search/fetch per-use fees are **not** included and are unverified | Medium | dry-run only; set `P2P_WEB_SEARCH_MAX` / `P2P_WEB_FETCH_MAX` to cap |
| R2 | Safety-classifier refusals on biology | The pipeline detects a refusal and raises `LLMRefusal`, but does not enable fallbacks or retry; SARS-CoV-2 and pathogen papers are in scope. No refusal appears in any committed output | Medium | not mitigated |
| R3 | Non-reproducible LLM stages | The response cache is gitignored and not committed; a re-run is a new sample | High for the paper claim | issue filed |
| R4 | Leakage of the answer into the model's context | `resolve` does web research; the leak guard blocks code hosts, but same-domain supplements and AGPL/author code can still surface | Medium | guard exists; `P2P` audit flags suspicious URLs |
| R5 | Detail that is not in the paper | KDM2B: 0% of steps stated; 70% of all converted steps are `assumed` | High for validity | verdicts and critic issues recorded per row |
| R6 | Model drift | Stages pin `claude-sonnet-5-5`; a model change changes every output | Low | pinned in `llm.STAGES` |

## 5. Harbor and the API key

| # | Risk | Evidence | Sev |
|---|---|---|---|
| H1 | The agent holds the real key | Harbor's claude-code agent runs with `bypassPermissions` inside the sandbox and reads the key from its environment; it can print it to logs | High |
| H2 | The key we have is not a dedicated one | It belongs to the workspace shared with Claude Code (8 keys); a benchmark run should use a separate workspace and a spend-capped key | High |
| H3 | Runaway spend | Defaults: concurrency 4, no turn or dollar cap; `-k`/`-r` multiply cost; the judge is billed again on oracle runs and `regrade` | High |
| H4 | Network allowlist might not be enforced | Depends on the sandbox provider; unverified for Daytona, Modal, E2B | Medium |
| H5 | No local runtime | Docker is not installed on this Mac, so nothing can be run locally; Harbor itself is not installed | Medium |
| H6 | Only one task is Harbor-runnable | The other six lack `environment/`, `solution/`, `tests/`, and their `task.toml` names fail Harbor's `org/name` rule | Medium |
| H7 | Judge failures look like model failures | `grade.py` turns a blocked key or bad model id into reward 0 with `judge_error=1` | Medium |
| H8 | Hidden grader is public | `tasks/opentrons-rna-extraction/tests` and `solution` are in the public GitHub repo, so a web-enabled model can read them | High |

Runbook with exact commands and the unverified list: [`harbor-runbook.md`](harbor-runbook.md).

## 6. Benchmark validity

| # | Risk | Detail | Sev |
|---|---|---|---|
| V1 | Contamination | Tasks come from public papers and public repos that models have probably seen; the RNA oracle is public | High |
| V2 | Selection bias | Sources were found by searching for papers that name an Opentrons repo, so the set over-represents groups that publish code, and is OT-2-centric | Medium |
| V3 | Judged tasks are few | 3 of 7 tasks can return a verdict; only 2 were tested by `spec_check` (21 protocols) | High |
| V4 | The criteria can be gamed or brittle | The old hard-coded criteria misjudged 7 of 21 protocols; the new checker passed all 21 but has not met a real model's output | Medium |
| V5 | Simulator is not a robot | Opentrons 7.5.0 simulation; no liquid physics beyond bookkeeping; collisions only against labware rims | Medium |
| V6 | Real references mostly cannot run | 15 of 22 scripts do not simulate on the pinned stack | Medium |
| V7 | Hand-written tasks are not from the literature | 5 of 7 tasks, and their numbers differ from the real scripts | High |

## 7. Process

- **Agent output is unverified until checked.** Every number in the ingestion records was spot-verified (hashes,
  pinned commits, licences) but the experiment splits and identifications were not.
- **Shared working tree.** Several sessions edit one machine's folders; this already lost track of untracked files.
- **A public repo created by default.** `opentrons-mujoco-viz` is public without the question being answered.
