# L_other: non-Opentrons task candidates

Tasks whose source paper drives a machine other than an Opentrons OT-2. They sit beside the OT-2 tasks of #36 (`tasks/<task>/` with `public/`, `private/`, `harbor/` and a `task.toml` whose `[[source]]` names the paper) and use the same Harbor layout as the existing tasks. Papers go under `sources/<slug>/` exactly as in #36.

Checked 2026-10-04 from Crossref (paper licence) and the GitHub API (repo licence, archived, last push). **Verdicts are metadata-level: no paper's methods section has been read yet.**

## Verdicts

- **A**: paper CC BY and repo MIT, workflow has real liquid handling. Addable once the base PR is in.
- **B**: addable, with a caveat (domain, licence, or little liquid handling).
- **P**: private only. Paper not redistributable or repo unlicensed, so ingest for comparison and never publish (same rule as #36's `redistributable` flag).
- **X**: not addable as a protocol task.

| # | Machine | Paper (licence) | Code (licence) | Verdict | Why |
|---|---|---|---|---|---|
| 1 | Hamilton STARlet + BMG CLARIOstar | Chory 2021, Mol Syst Biol, `10.15252/msb.20209942` (CC BY 4.0) | `dgretton/pyhamilton_population_dynamics`, `many_asynchronous_turbidostats`, `roboplaque`, `platereader` (all MIT) | **A** | Turbidostat and plaque-assay loops with plate-reader feedback. Best first pair. |
| 2 | Hamilton STARlet + CLARIOstar | DeBenedictis 2022, Nat Methods, `10.1038/s41592-021-01348-4` (no CC licence found) | `dgretton/std-96-pace` (MIT) | **B** | PRANCE: repo is fine, but keep `paper.json` gitignored. Same code serves both machines. |
| 3 | ImageXpress Nano | Wheeler 2022, PLOS NTD, `10.1371/journal.pntd.0010937` (CC BY 4.0) | `zamanianlab/wrmXpress` (MIT) | **B** | CC BY and MIT, but mostly image analysis; liquid handling is the drug plating. |
| 4 | ImageXpress Nano | Caterer 2025, IJPDDR, `10.1016/j.ijpddr.2025.100588` (CC BY 4.0) | `wheelerlab-uwec/wrmXpress-gui` (no SPDX) | **P** | A GUI for #3, no new wet-lab protocol, repo licence unclear. |
| 5 | Brooks PreciseFlex 400 | Cousty 2024, Digital Discovery, `10.1039/d4dd00253a` (CC BY 3.0) | `swisscatplus/glas` (MIT) | **B** | Clean licences, but chemistry and a scheduler, not a biology protocol. Good architectural test. |
| 6 | Liconic STX | Johansson 2025, bioRxiv, `10.1101/2025.05.30.657006` (CC BY 4.0) | `pharmbio/robotlab` (MIT); `pharmbio/aros` (no licence, 21 KB, last push 2023) | **B** | Cell Painting + TPP, multi-instrument. Largest scope; `aros` is near empty, so `robotlab` is the real code. |
| 7 | BTX Gemini X2 | Crits-Christoph 2025, bioRxiv, `10.1101/2025.11.18.689155` (**CC BY-NC-ND**) | `cultivarium/electroporation-bayesian-optimization` (no SPDX) | **P** | NC-ND paper, unlicensed code. The loop is a Bayesian optimiser, not a fixed protocol. |
| 8 | Tecan Spark | Harmer 2023, ACS Synth Biol, `10.1021/acssynbio.3c00215` (**CC BY-NC-ND**) | `mccleanlab/Lustro` (none) | **P** | NC-ND paper, unlicensed code. |
| 9 | Tecan Spark | Harmer 2024, ACS Synth Biol, `10.1021/acssynbio.3c00761` (not checked) | `mccleanlab/Optoplate-96` (MIT), `zavalab/ML` (none) | **P** | Optoplate code is MIT, ML code is not; paper licence unchecked. |
| 10 | Tecan Spark | "Harmer 2024, microPublication" | `pertzlab/LITOS` (MIT) | **X** | Could not find this paper. The only LITOS paper found is Pertz-lab Sci Rep 2022 (`10.1038/s41598-022-17312-x`), an LED illumination device, not a liquid-handling protocol. |
| 11 | QuantStudio 3/5 | Maussion 2021, Sci Rep, `10.1038/s41598-021-99727-6` (CC BY 4.0) | `neuroeddu/Auto-qPCR` (no SPDX) | **X** | Data-analysis web app for qPCR output. No liquid-handling workflow. |
| 12 | OT-2 | Ouyang 2021, bioRxiv, "UC2-Hi2" | `openUC2/UC2-Hi2` (no SPDX, **archived**, 2022) | **X** | No bioRxiv paper found, repo is an archived GRBL microscope. The closest hit is the protocols.io UC2 immunostaining protocol (`10.17504/protocols.io.bw8dphs6`), which is OT-2 and belongs to the L2 stream, not here. |
| 13 | OT-2 | Bryant, AssemblyTron, `10.1093/synbio/ysac032` (CC BY 4.0, published **2022**, not 2023) | `PlantSynBioLab/AssemblyTron` | already in | Already the `golden-gate-assembly` task in #36 (source slug `assemblytron`). Exclude; it is not L_other. |

Net: **1 is A, 4 are B (2, 3, 5, 6), 4 are P (4, 7, 8, 9), 3 are X (10, 11, 12), and 1 is already a task (13).** Two of the pasted table's OT-2 rows (12, 13) are not L_other at all.

Note the paper years in the pasted table are off for AssemblyTron (2022) and Harmer ("2024" LITOS is unresolved).

## Proposed PR stack

All branches cut from `origin/feat/ingestion` (#36's head), one worktree, and stacked in this order. Nothing here depends on the OT-2 stream's unpushed commits.

1. `feat/l-other-tasks` (this PR): this document only.
2. `feat/nonot-step-kinds`: `paper2protocol/models.py` only (new `Step.kind` values and `ContainerKind`s). Already drafted, uncommitted, in the `backup/l2-outputs-oct04` worktree. Must precede every instrument PR.
3. `feat/l-other-hamilton-clariostar`: rows 1 and 2 (same machines, same repos).
4. `feat/l-other-imagexpress`: row 3.
5. `feat/l-other-preciseflex-glas`: row 5.
6. `feat/l-other-liconic-pharmbio`: row 6.
7. `feat/nonot-checker`: gates `paper2protocol/check.py` on an `instrument_family` field, since `opentrons_simulate` cannot validate non-OT protocols. Needed before any L_other task can be graded, not just ingested.

Rows 4, 7, 8, 9 can be ingested into `sources/<slug>/` for comparison under the `redistributable: no` rule, but get no public task.

## Open before building

- Nothing here has a grader. Every L_other task needs a Harbor `tests/` that does not use `opentrons_simulate`; until `feat/nonot-checker` lands, tasks would be graded by schema checks and the LLM rubric only.
- Whether pyhamilton scripts (which depend on a Windows Hamilton Venus install) count as "code" for the `sources/<slug>/code/` comparison step, or only as reading material.
- Rows 2, 3, 5, 6 should be read in full before committing to a task each, to confirm each has at least one experiment that is mostly liquid handling.
