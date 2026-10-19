# Simulator verification of the 25 ready liquid-handling candidates (2026-10-12)

Each repo was shallow-cloned and every file with `def run` and an Opentrons import/apiLevel (max 15 per repo) was run
through `opentrons_simulate` (Opentrons 7.5.0) in an empty temp dir with a 120 s timeout, with any custom labware JSON in the repo passed via `-L`.
Files using network, shell or file-deletion calls would have been skipped; none did.

**Result:** 128 protocol files found, 30 pass as-is, in 10 of 25 repos (3 fully, 7 partly). 14 repos fail every file; 1 had no protocol file.

Failures (98 files): 43 custom labware referenced by an absolute path on the author's machine, 24 API version newer than 7.5 supports,
15 extra Python packages, 5 missing input files (CSV/JSON), 10 other (indentation, index errors), 1 syntax.
Most are fixable by vendoring the labware JSON and inputs, or by simulating with a newer Opentrons release.

| Candidate | Status | Passed / run | Licence |
|---|---|---|---|
| `ant-cloning` | partly_verified | 7/10 | none |
| `gfp-codon-burden-ot2` | partly_verified | 7/15 | MIT |
| `massspecpreppy` | partly_verified | 3/10 | GPL-3.0 |
| `tidytron` | partly_verified | 3/15 | Apache-2.0 |
| `beckham-enzyme-pipeline` | partly_verified | 2/15 | none (no LICENSE file) |
| `culturomics-isolation` | partly_verified | 2/11 | none |
| `jubiotech-ot2-autoclone` | partly_verified | 2/7 | AGPL-3.0 |
| `msd-biochem-assays-ot2` | verified | 2/2 | Apache-2.0 |
| `exfab-qiaseq-flex` | verified | 1/1 | GPL-3.0 |
| `hyrad-adna-capture` | verified | 1/1 | none |
| `blots-ot2` | failed | 0/1 | none |
| `cayman-his-elisa` | failed | 0/4 | MIT |
| `damplab-moclo-transformation` | no_protocol_found | 0/0 | BSD-3-Clause |
| `ester-library-synthesis` | failed | 0/3 | MIT |
| `flat-agar-celegans-ot2` | failed | 0/3 | MIT |
| `formulations-prep-shampoo` | failed | 0/1 | none |
| `greenaway-halogenation` | failed | 0/9 | BSD-3-Clause |
| `greenaway-mocs` | failed | 0/5 | none |
| `greenaway-pocs` | failed | 0/6 | none |
| `lucks-cellfree-biosensor` | failed | 0/1 | none |
| `lysostaphin-turbidity` | failed | 0/1 | AGPL-3.0 |
| `plant-phenotyping-ot2` | failed | 0/2 | MIT |
| `roboctab` | failed | 0/2 | none |
| `roche-pipetting-performance-ot2` | failed | 0/2 | GPL-3.0 |
| `sapp-dmx-protein-design` | failed | 0/1 | MIT |
