# Web expansion sweep — notes (source_agent: web, 2026-10-11/12)

Goal: find new (paper, public robot code, reported wet-lab results) triples for Text2WetLab, deduplicated
against the 48 papers in `docs/task-sources.md` and the folders under `sources/`.

## Searches run

Literature indexes
- Europe PMC REST search: `("opentrons" OR "pylabrobot" OR "pyhamilton") AND ("github.com" OR "zenodo")`
  → 251 records (2016–2026); full-text XML pulled for 204 of them, then GitHub/Zenodo links and
  Opentrons-mention counts extracted per paper (ranked table in the scratch run; top ~120 inspected by hand).
- Crossref `query.bibliographic` lookups to resolve DOIs, venues and licences for 15 titles found only
  via repo READMEs (halogenation platform, MassSpecPreppy, C. glutamicum autoclone, Culturomics,
  esterification library, plant phenotyping, LAP format, enzyme-discovery pipeline, ELISA protocols.io entry, …).
- Targeted web searches: Opentrons/Flex protocol papers 2023–2026; PyLabRobot/Hamilton validated protocols;
  SLAS Technology / HardwareX / ACS Synth Biol / PLOS ONE Opentrons code-availability statements;
  self-driving-lab + OT-2 + Bayesian optimisation; protocol-to-code benchmarks and datasets.
  (Web-search quota was exhausted late in the run; Crossref + Europe PMC + GitHub APIs covered the rest.)

Code indexes
- GitHub code search (`search/code`) for `apiLevel` co-occurring with doi / biorxiv / "et al" /
  publication / cite, plus `opentrons doi.org`, `pylabrobot doi`, `protocol_api zenodo` → 245 hits, mostly noise,
  ~15 usable repos.
- GitHub repo search: `topic:opentrons`, `topic:opentrons-ot2`, `topic:liquid-handling`, `topic:opentrons-flex`,
  name/readme searches for opentrons+paper/manuscript/biorxiv/zenodo → 398 + 469 rows, filtered to ~70 relevant repos.
- Hugging Face dataset API searches: opentrons, protocol-code, lab automation, pylabrobot, bioprot,
  protocolqa, labbench, bioplanner, "wet lab protocol".

Verification (per candidate repo): `gh api repos/OWNER/REPO` for existence/licence/default branch,
`git/trees/<branch>?recursive=1` for the full file list, and raw content checks on up to 60 `.py` files for
`from opentrons` / `import opentrons` / `apiLevel` / `protocol_api` / `pylabrobot`. ~45 repos were verified this
way (a GitHub secondary rate limit forced the last five to be checked via the unauthenticated API).

## Counts

| | |
|---|---|
| Candidates screened and recorded | 60 |
| Repos verified to exist (API) | 45 (all 45 existed; 0 dead links) |
| Repos with confirmed Opentrons/PLR `.py` (import or `apiLevel`) | 31 |
| readiness = ready | 21 |
| readiness = partial | 29 |
| readiness = no | 10 |
| New (not in the 48-paper corpus) | 52 |
| Marked `duplicate_of_existing` | 8 (opencell-automation, moeller-hackflex, shotgun-proteomics-jove, apex, pipetting-robot-nanoliter, proxy-viscometer, uc2-hi2, lap-transposon-genotyping) |
| Sum of `est_tasks` | 159 (≈118 from the `ready` + strong `partial` rows) |
| Platform mix | ot2 40, flex 4, other 16 (Jubilee, ACRO/Integra, BMS Myra, acoustic dispenser, analysis-only) |

Licence notes: 13 candidate repos carry a permissive licence (MIT/Apache-2.0/BSD-3), 4 are copyleft
(GPL-3.0, AGPL-3.0), and 21 have no licence file at all (reference-only, cannot be vendored — same constraint
the corpus already applies to APEX and HULP). Paper licences: 24 of the new candidates are CC BY or CC BY-NC,
8 are CC BY-NC-ND (link-only), and 6 are subscription/unclear.

## Existing datasets/benchmarks we could absorb or compare against

| Dataset / benchmark | Content & size | Robot code? | Licence |
|---|---|---|---|
| **BioProBench** (arXiv 2505.07889, ICML 2026; `github.com/YuyangSunshine/bioprobench`, HF `BioProBench`) | 22,413 human-written protocols → 523,784 task instances across 5 tasks (QA, step ordering, error correction, generation, reasoning) | No — natural-language protocol reasoning only | CC BY-NC 4.0 (repo shows NOASSERTION) |
| **BioProt / BioPlanner** (EMNLP 2023, arXiv 2310.10632; `github.com/bioplanner/bioplanner`) | 100 protocols.io protocols with pseudocode + function-library annotations; 5 python eval/prompt files | Pseudocode, not robot API code | no LICENSE file in repo |
| **LAB-Bench** (`futurehouse/lab-bench`) | 1,967 items total; relevant subsets ProtocolQA 108, CloningScenarios 33 | No | CC BY-SA 4.0 |
| **LAB-Bench 2** (`EdisonScientific/labbench2`, arXiv 2604.09554) | successor set incl. `protocolqa2` config (size endpoint unavailable at time of check) | No | CC BY-SA 4.0 |
| **AEGIS** (arXiv 2607.15620) | 24 OT-2 protocols across 5 assay families, plus validation benchmark and monitoring model weights; live OT-2 demo | Yes — OT-2 Python protocols, stated MIT | MIT (per paper; repo URL not given in the abstract page) |
| **ProtoPilot** (arXiv 2606.31763) | 294 tasks derived from 98 gold-standard protocols; reports Opentrons code-gate pass rates (88.2% vs 32.4% baseline) and wet-lab checks | Generated Opentrons code; release not stated | not stated |
| **ProtoAct / BioP2E** (arXiv 2608.01690) | 22 cell-culture protocols → 258 monitoring conditions, 910 executable subtasks, 962 grounded action calls | Embodied action calls (manipulator), not liquid-handler Python | not stated |
| **ProtoCode** (SLAS Technology 29(3), 2024) | LLM pipeline turning published PCR protocols into machine-readable thermocycler files; web server only, no dataset dump | Thermocycler files, not Opentrons | web service, licence unstated |
| **BioCoder** (arXiv 2308.16458) | 2,269 bioinformatics coding problems | No robot code | open (repo) |
| **Opentrons/PhysicalAI** (HF) | Flex teleoperation/inference episodes (HDF5 + GIFs) for plate handoffs to a plate reader | Embodiment data, no protocol `.py` | unstated |
| **Opentrons/Protocols** (`github.com/Opentrons/Protocols`) | Public protocol library source; large, but entries are vendor/kit protocols and rarely cite a paper — low triple yield, useful as solution-style exemplars | Yes, OT-2/Flex Python | no LICENSE file |

Take-away: nothing in this list pairs a *published paper* with *runnable liquid-handler code* and *wet-lab results*
the way Text2WetLab does. AEGIS (24 OT-2 protocols, MIT) is the closest and the best absorb/compare target;
BioProBench and LAB-Bench ProtocolQA are text-only and belong in a related-work comparison, not an absorb.

## Top 15 candidates

1. **tidytron** — SLAS Technol 2024, Apache-2.0 repo, 37 OT-2 scripts, wash-and-reuse validated by carryover assays. Highest ready-to-task density found.
2. **beckham-enzyme-pipeline** — Sci Rep 2024 (CC BY), 21 modular OT-2 scripts covering transformation → inoculation → assay; repo unlicensed.
3. **massspecpreppy** — Proteomics 2023, GPL-3.0, one script per stage (BCA, digestion, SP3, Evotip) with quantitative manual-vs-robot comparison (101.3% vs 96.3% BCA recovery).
4. **jubiotech-ot2-autoclone** — Appl Microbiol Biotechnol 2022 (CC BY), AGPL-3.0, seven one-protocol-per-file scripts (Golden Gate, heat-shock, digest, plasmid prep, plating).
5. **culturomics-isolation** — iMetaOmics 2025 (CC BY), 11 single-step OT-2 scripts (microvolume extraction, two-step PCR, bead purification, pooling).
6. **ant-cloning** — ACS Synth Biol 2020, five numbered end-to-end scripts (PCR → digestion → OE-PCR → transformation → plating) explicitly tied to the paper.
7. **roboctab** — Plants 2025 (CC BY) with *both* OT-2 and Flex versions of one CTAB extraction: a natural easy/hard pair and rare Flex coverage.
8. **cayman-his-elisa** — protocols.io CC BY text + MIT repo with loading, wash/substrate and a hardware test script (Arcadia Science).
9. **greenaway-halogenation** — BSD-3-Clause, nine OT-2 scripts across screening stages plus NMR prep; chemistry breadth for the benchmark.
10. **greenaway-pocs** — Chem Sci 2024 (CC BY), repo even ships `simulate.py`, so the scripts are known to pass `opentrons_simulate`.
11. **exfab-qiaseq-flex** — protocols.io CC BY NGS protocol with a matching GPL-3.0 Flex script, one-to-one.
12. **lucks-cellfree-biosensor** — open preprint, script maps to a single figure (384-well cell-free build); good viscous-liquid hard task.
13. **hyrad-adna-capture** — Mol Ecol Resour 2022, one self-contained script driving magnetic + temperature modules.
14. **damplab-moclo-transformation** — Synth Biol 2022 (CC BY) + BSD-3 MoClo/transformation templates; closest licence-clean analogue to the existing APEX tasks.
15. **lap-format-repository** — ACS Synth Biol 2023 LAP paper (new to the corpus) over the already-known LAPrepository code: ~37 validated entry scripts, each a candidate task once licence is clarified.

Runners-up worth a second look: `sapp-dmx-protein-design` (Nat Commun 2026, MIT, SEC pooling),
`blots-ot2` (Current Protocols 2026 — protocol-journal text is ideal NL input), `greenaway-mocs`,
`formulations-prep-shampoo` (viscous handling), `plant-phenotyping-ot2`, `moeller-library-dup`
(9 MIT scripts beyond the Hackflex one already tracked), `opentrons-accs-dup` (BSD-3 framework repo not yet ingested).

## Gaps / follow-ups

- Flex and PyLabRobot coverage is still thin: only 4 Flex candidates (roboctab, exfab-qiaseq-flex,
  exposomics-384-flex, flex-genomics-di-omics) and no new PyLabRobot paper+code+results triple beyond the
  PyLabRobot paper itself (already in corpus via chory/olh forks).
- Hamilton/Tecan papers mostly release analysis code only (helleckes-catib-screening, proteoautonet) —
  the robot methods stay in vendor formats.
- Three repos need a paper identified before they count as triples: `exposomics-384-flex`,
  `spot-assay-ot2`, `biomationscripter`.
- AEGIS's own OT-2 protocol set (MIT) should be located and screened next; its repo URL was not in the
  abstract page.
