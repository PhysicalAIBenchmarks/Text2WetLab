# Reference · BOTany (Voiniciuc lab, Plant Physiology 2026) — author-published OT-2 scripts

**Gold standard for comparison only. Not an input to `paper2protocol`.**

## Provenance

- Paper: *BOTany methods: accessible automation for plant synthetic biology*, Plant Physiology
  200(3) kiag066, 2026. doi:10.1093/plphys/kiag066
- The published full text isn't in Europe PMC, so the pipeline ran on the bioRxiv preprint
  doi:10.1101/2025.08.21.671538 (v1, 2025-08-22), which bioRxiv links to the published DOI.
  Outputs: `out/10.1101_2025.08.21.671538/`. Methods may have changed between versions.
- Repo: https://github.com/cvoiniciuc/BOTany branch `main`,
  commit `c7588d321a59b0d9078c288504e63598b0f60b5e` (cited in the preprint text)
- Licence: **none declared** in the repo. Kept here for private comparison only; do not
  redistribute without the authors' permission.
- `scripts/` = `OT-2 Protocols/`, `labware/` = `Custom Labware/`, `tables/` = `Tables/`
  (runtime-parameter spreadsheets), all verbatim. `REPO_README.md` = the repo's README.

## Mapping to the pipeline's experiments

| Pipeline experiment | Outcome | Reference scripts |
|---|---|---|
| 1. MoClo L1 Golden Gate + colony PCR | rejected (twice) | `BOTany1-Primers`, `BOTany2A/2B-PCR`, `BOTany3A/3B-MoClo` |
| 2. E. coli heat-shock transformation | converted | `BOTany4-Shock&Go` (+ `BOTany3A/3B-MoClo` for the assemblies) |
| 3. MagBead plasmid extraction → GG/transformation/cPCR | rejected | `BOTany5-MagBead` (+ 3, 4, 2) |
| 4. Pichia electroporation | converted (2nd run) | `BOTany5-MagBead` for the miniprep; electroporation is manual |
| 5. Universal mosaic inoculation of Pichia | converted | `BOTany6-Universal` |

Exp 1 and 4 were rerun with `P2P_WEB_SEARCH_MAX=20 P2P_WEB_FETCH_MAX=25` after the first
resolve ran out of web quota. Exp 1 was rejected again with quota to spare: the construct
identities and genotyping primers aren't public. `experiments.json` was rebuilt from the
cached resolve/extract prompts after a `--cache refresh` re-ran `identify`; the rebuild
reproduces all five original resolve prompts exactly, but `shared_refs` for exp 1, 3 and 4
couldn't be recovered and are empty.

The scripts are parameterised: volumes and layouts come from the `tables/` spreadsheets,
saved as CSV and loaded as runtime parameters, so score against script + table together.

## Why this is kept out of the pipeline

Same reasoning as `ref/dna-bot-ysaa010/README.md`: the pipeline reads only fetched JATS XML
and what `resolve` retrieves; `paper2protocol/guard.py` blocks github.com, and the paper
cites the repo URL, so that guard is load-bearing. Score after a run; don't tune prompts on these.
