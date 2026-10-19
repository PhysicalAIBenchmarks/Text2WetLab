# Amass search: Text2WetLab expansion candidates

Source agent: amass. Output: `amass_candidates.jsonl` (109 rows: 76 screened candidates + 33 rows that duplicate corpus papers, with ids starting `dup-`).

## Credits
- Start: 50,005. End: 48,155. **Spent: 1,850** (cap 8,000).
- Cost: about 0.4 credits per record with `include=fulltext` (a 25-record query cost about 10 credits).
- About 6% of queries returned HTTP 500 on the first try. They were retried at a smaller `limit` (20, then 10), and all but about 4 recovered.

## Queries run (about 190 distinct, all on biomedcore with fulltext)
- **Platform terms:** "Opentrons", "Opentrons OT-2 liquid handling robot" (one query per year, 2019 to 2026), "Opentrons Python protocol code available" (one query per year, 2019 to 2026), "open-source liquid handling robot automated protocol" (one query per year), "Opentrons Flex" (several), "PyLabRobot", "pyhamilton Hamilton robot Python", "Hamilton STAR open-source python script", "Hamilton Venus", "Tecan EVO/Fluent script", "Biomek", "Echo acoustic", "liquid handling robot Python API", "github liquid handling robot protocol", "liquid handling robot protocol deposited Zenodo", "scripts for the OT-2 are available on GitHub", "custom Opentrons protocol was written in Python".
- **Domain terms (about 120 queries):** OT-2 or Opentrons combined with PCR setup, qPCR, RNA extraction, DNA extraction (plant, soil), Golden Gate/MoClo, Gibson, transformation, miniprep, NGS/Nextera/RNA-seq/nanopore/16S library prep, normalization/PicoGreen, serial dilution/dose response, ELISA/immunoassay/serology, cell culture/passaging/transfection/organoid, plating/colony picking, protein expression/purification/solubility/thermal stability, CRISPR, cell-free, MIC/antimicrobial, metabolomics/LC-MS/MALDI/proteomics, COVID/pooling/LAMP/wastewater, ddPCR, ChIP, phage/plaque, Bacillus/Pseudomonas/Streptomyces/Mycobacterium/Plasmodium, zebrafish/Drosophila/C. elegans, crystallization, formulation/hydrogel/polymer/perovskite/electrochemistry/nanoparticles, self-driving lab/Bayesian optimisation, education/colour mixing.
- **Totals:** 4,019 unique records retrieved. 964 mention liquid handlers anywhere. 135 have a liquid-handling robot as the main subject; those were screened by hand.
- **Recall:** it plateaued. The last 20 queries added only 4 new relevant papers. Amass's full text often strips hyperlinks, so code URLs were also pulled from the Europe PMC full-text XML of 97 PMC papers. That step found about 25 extra repo links. GitHub searches (`gh search repos`) found repos for papers without links: MassSpecPreppy, RoboCTAB, OT2Eye, ot2_spot_assay, pipette_opt, ReacSight and FINDUS.

## Verification method
- **GitHub REST API:** it was rate-limited (the 5,000/hr limit is shared with other agents). Repos were therefore checked with a shallow `git clone` instead.
- **Robot code:** each repo's `.py` files were grepped for `from/import opentrons`, `apiLevel`, v1-style `robot.`/`instruments.P*`, `pylabrobot`, `pyhamilton` and Flex `robotType`.
- **Licence:** read from the LICENSE file.
- **Zenodo:** records were checked through the Zenodo API.
- **GitLab:** the Cambridge GitLab (PEG assay) was checked through the GitLab API.
- **Simulation:** `opentrons_simulate` is not installed here, so no candidate was simulated. "Ready" is a judgement from reading the code.

## Counts (76 screened candidates, excluding the 33 `dup-` rows)
- **Verified robot code** (repo or file checked, with Opentrons/PLR/pyhamilton .py or Opentrons JSON): 23. Of these, 17 have Opentrons Python API v2 code, 1 is v1-only (krisp pooling), 2 are Opentrons Protocol Designer JSON (HCR on Flex, bean KASP), 1 is pyhamilton, and 1 is the PyLabRobot library. Non-Python vendor code was also found: Tecan .exd (roboRNA), Agilent Bravo, Myra, binary .pkg methods and LabDroid jobs.
- **Readiness:** 3 ready, 22 partial, 51 no.
- **New vs duplicate:**
  - 33 Amass hits were papers already in the corpus. They are recorded as `dup-<slug>` rows. They cover 32 corpus slugs, including both the bioRxiv and journal DOIs of APEX, BOTany and AssemblyTron.
  - 5 screened candidates are new papers that share code or a group with corpus entries, so `duplicate_of_existing` is filled in: y1h-yeast-lap (LAPrepository), galaxy-synbiocad (DNA-Bot), facs-automation (CZ Biohub), oscar-ur-arm (pipette-tool-change), modular-pipetting-imaging-uc2 (UC2).
  - The other 71 screened candidates are fully new.
- **Wet-lab validated:** 70 of 76.

## Top 15 candidates
1. **massspecpreppy** (Proteomics 2023): 10 OT-2 v2 scripts for BCA, SP3 digestion and Evotip loading. BCA recovery was 101.3% vs 96.3% manual. GPL-3.0. Ready, about 6 tasks.
2. **tidytron** (SLAS Tech 2023): 37 OT-2 v2 scripts for washing and reusing tips and plates, validated against DNA, E. coli and yeast contamination. Apache-2.0. Ready, about 4 tasks.
3. **lysostaphin-turbidity** (Microb Cell Fact 2026): one self-contained OT-2 turbidity/dilution assay script, quantifying 0.63 to 10 mg/L lysostaphin. AGPL-3.0, so it cannot be vendored. Ready, about 2 tasks.
4. **beckham-enzyme-pipeline** (Sci Rep 2024): 21 OT-2 v2 scripts for transformation, cherry-picking and mag-bead Ni purification of 96 PET hydrolases (up to 400 ug each). No LICENSE. Partial, about 8 tasks.
5. **roboctab** (Plants 2025): CTAB plant DNA extraction script in both OT-2 and Flex versions, a natural OT-2-to-Flex pair. No LICENSE. Partial, about 4 tasks.
6. **peg-solubility-assay** (Sci Rep 2021, Cambridge GitLab): two OT-2 v2 scripts for PEG-titration protein solubility from about 200 ug of protein. No LICENSE. Partial, about 4 tasks.
7. **ot2-yeast-spot-assay** (SLAS Tech 2022, bioinfo-tsukuba): yeast spot-assay protocol generator with a custom Petri-dish mount. No LICENSE. Partial, about 3 tasks.
8. **pasta-spatial** (Nat Methods 2026): OT-2 v2 script for cyclic tyramide-oligo staining. Needs custom slide labware. No LICENSE. Partial.
9. **krisp-sars2-pooling** (Sci Rep 2021): hypercube pools of 27 and 81 samples, Ct up to 32 detected. MIT, but the code is v1 API and needs porting. Partial.
10. **y1h-yeast-lap** (Curr Protoc 2024): yeast one-hybrid screening using LAP-CellMediaInoculation OT-2 scripts. The code repo is already in the corpus; the paper is new. Partial.
11. **ht-hcr-sea-urchin** (Development 2025): Flex Protocol Designer JSON for 48-well whole-mount HCR; 101 genes imaged. The only validated Flex workflow with code found. Partial.
12. **openblend-media** (Biotech Bioeng 2021): MIT package that generates OT-2 media-blending plates; improved Pichia titre. Partial.
13. **bean-kasp-anthracnose** (Plant Methods 2023): OT-2 JSON protocols for DNA extraction and KASP genotyping. No license. Partial.
14. **aml-drug-synergy-pyhamilton** (SLAS Discov 2023): pyhamilton drug-combination dilution matrix, the one Hamilton-Python candidate found. No license. Partial.
15. **roborna-nirvana** (Sci Rep 2023): Tecan EVO magnetic-bead RNA extraction plus nanopore variant calling. Detection limit comparable to commercial kits. Non-Python, so it suits a paper-only port task. Partial.

Honourable mentions:
- **No code yet, but high value if the supplementary files hold scripts** (each marked "no" or "partial"): swabseq-flex (Opentrons Flex NGS diagnostic, 2026), cfrna-extraction-pipeline (Nat Protoc), nfkb-luciferase-ot2 (SLAS), tmt-bead-platform-ot2 and auto-sp-proteomics (templates in SI).
- **Related LLM-to-protocol work:** putzsebastian/KAISA-LSE_SDL-Platform (MIT) contains an "LLM protocol-generation replication study" with hundreds of GPT-generated Opentrons protocols.

Estimated task yield: ready plus partial candidates give about 64 tasks in total; the 3 ready candidates give about 12 of them.
