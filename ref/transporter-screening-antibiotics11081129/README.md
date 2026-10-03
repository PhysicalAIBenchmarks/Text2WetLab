# Reference · E. coli transporter knockout screen (Munro & Kell 2022) — author-published OT-2 scripts

**Gold standard for comparison only. Not an input to `paper2protocol`.**

## Provenance

- Paper: *Analysis of a Library of Escherichia coli Transporter Knockout Strains to Identify
  Transport Pathways of Antibiotics*, Antibiotics 11(8) 1129, 2022.
  doi:10.3390/antibiotics11081129 · PMC9405208
- Repo: https://github.com/ljm176/TransporterScreening branch `main`,
  commit `455fc2e569ad4a873ab415186a29e3e396e8cc4e` (cited in Methods: "Scripts used in
  operation can be found at github.com/ljm176/TransporterScreening")
- Licence: **none declared** in the repo. Kept here for private comparison only; do not
  redistribute without the author's permission.
- `scripts/` = the two OT-2 scripts at the repo root, verbatim.
- `inputs/Plates.csv` = knockout-strain plate map. The R analysis (`.Rmd`) and Growth Profiler
  result CSVs were not copied — they are analysis, not bench protocol.

## Mapping to the paper

| Script | Stage | Paper Methods detail |
|---|---|---|
| `LoadMedia_GPPlates.py` | media loading | P300 multi; 297 µl from a 1-well reservoir into every column of 5 Growth Profiler plates, one tip, top dispense, rate 0.5 |
| `innoc_glycerol_droplets_V2.py` | inoculation | P20 multi; per column, aspirate 20 µl from a deep-well glycerol-stock plate, dispense 3 µl into the same column of 6 GP plates, fresh tip per column |

Note: both scripts share the metadata name "GP Load Glycerol Droplets", and use the custom
labware `gp_plate_96` (Growth Profiler plate), whose definition is not in the repo.

## Why this is kept out of the pipeline

Same reasoning as `ref/dna-bot-ysaa010/README.md`: the pipeline reads only fetched JATS XML
and what `resolve` retrieves; `paper2protocol/guard.py` blocks github.com, and this paper's
Methods cites the repo URL, so that guard is load-bearing. Score against these after a run;
don't use them to tune prompts.
