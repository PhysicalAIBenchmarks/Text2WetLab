# GitHub code-first sweep: PyLabRobot + Opentrons (paper, code, results) triples

Agent: `github` · run 2026-10-11/12 · output: `github_candidates.jsonl` (77 records, one per candidate repo)

## What was run

**GitHub code search** (`gh search code`, ~8 s between calls, 92 queries logged):
- PyLabRobot: `"import pylabrobot"`, `"from pylabrobot.liquid_handling import LiquidHandler"`, `pylabrobot.liquid_handling.backends`, `ChatterboxBackend`, `LiquidHandlerChatterboxBackend` (py and ipynb), `pylabrobot` + `LiquidHandler` / `STAR` / `OTDeck` / `STARLetDeck` / `TIP_CAR_480_A00` / `Cor_96_wellplate_360ul_Fb` / `HTF_L` / `plate_reader` / `aspirate dispense` / `pick_up_tips`, `pylabrobot` in `requirements.txt` / `pyproject.toml` / `.ipynb`, `pylabrobot doi` / `biorxiv` in README.
  - Note: exact dotted-phrase queries such as `"from pylabrobot"` return 0 on the legacy code-search API. Bare-token queries work.
- Opentrons: `"from opentrons import protocol_api"` + doi/biorxiv/paper/publication (all 0 hits on the legacy API), `apiLevel` + doi / biorxiv / "et al" / Nature / PLOS / Supplementary / doi.org / Cell / Science, `"protocol_api" "doi"`, `opentrons|OT-2|OT2` + doi / biorxiv / medRxiv / chemRxiv / "please cite" / Journal / published / Citation / "Nature Communications" / "ACS Synthetic Biology" / PLOS / "Scientific Reports" / SLAS / HardwareX / protocols.io / "Digital Discovery" / zenodo in README.md, `opentrons` in CITATION.cff, and pyhamilton / Hamilton STAR / Tecan EVO + doi.
  - `apiLevel` queries are very noisy: they match CPython `locale.py`, `twisted adbapi`, androguard and similar. Real protocol hits were separated by importing-file verification.

**Repo search** (`gh search repos`, 79 result files): `pylabrobot`, `opentrons`, `opentrons protocol(s)`, `OT-2`, `OT2 protocol`, `opentrons flex`, `pyhamilton`, `liquid handler`, `liquid-handling`, `self-driving lab`, topics (`opentrons`, `ot-2`, `opentrons-ot2`, `pylabrobot`, `liquid-handling`, `lab-automation`, `laboratory-automation`, `self-driving-lab`, `hamilton`), README-match variants, plus **date-partitioned** `opentrons` / `ot2` / `pylabrobot` searches over 11 creation windows from 2016 to 2026. These got past the 100-result cap and found 1,041 repos, 729 of them not seen before.

**Other sources**
- Opentrons/Protocols library (833 protocol folders, shallow clone): grepped every README for DOI, bioRxiv, PubMed, protocols.io, "et al." and journal names. **None cite a research paper.** The only "publication" hits are kit-vendor boilerplate and a thermocycler white paper. The library is not a source of triples.
- PyLabRobot `docs/img/used_by` showcase: Adaptyv, Bio-Techne, Cheshire Labs, Constructive, Duke (Chory lab), MIT, Pioneer Labs, RetroBio, Sanofi, TTx, UKM, X. These are mostly companies with no public protocol code.
- GitHub "Used by" page for pylabrobot: 13 repos and 6 packages.
- WebSearch + Crossref (`api.crossref.org`) were used to resolve paper titles, DOIs and licences. bioRxiv full text was read for the OLH and LabscriptAI preprints.

**Verification:** for each shortlisted repo I listed the tree via the GitHub API, fetched up to 40 `.py` files from raw.githubusercontent, and confirmed real imports or metadata (`from opentrons` / `apiLevel` / `protocol_api`, `from pylabrobot`, `pyhamilton`). I also scanned the README for citations.

Two GitHub REST rate-limit lockouts interrupted the run (core 5,000/h). Rate-limited repos were re-screened afterwards.

## Counts

| | n |
|---|---|
| Repos screened (metadata + README + tree via API) | 1,542 |
| Extra repos README-screened (date-partitioned enumeration) | 729 |
| **Total distinct repos screened** | **2,271** |
| Opentrons-related repos among them (name/desc/README) | ~880 (363 + 515) |
| Repos hit by PyLabRobot code queries | 227 (≈170 are TTS "Chatterbox" noise, PLR forks or agent-skill mirrors) |
| **Genuine public repos using PyLabRobot (outside the PLR org)** | **~50** |
| Opentrons protocol library folders checked | 833 |
| Candidates recorded in `github_candidates.jsonl` | 77 |
| … duplicates of the existing 48-paper corpus (marked, not dropped) | 22 |
| … new candidates | 55 |
| New candidates with a resolvable paper or preprint DOI (excl. protocols.io-only) | 25 |
| Readiness, all 77 records: ready / partial / no | 10 / 65 / 2 |
| Readiness, new candidates only: ready / partial / no | 10 / 43 / 2 |
| API split, all 77 records: opentrons_v2 / opentrons_v1 / pylabrobot / other (pyhamilton, HTTP API) | 63 / 2 / 5 / 7 |
| Estimated tasks: all new candidates / "ready" only | ~124 / ~36 |

## PyLabRobot ecosystem

- **Size:** about 50 public non-fork repos actually use PyLabRobot. GitHub's dependents page lists only 13 repos and 6 packages. Most are teaching or demo material, tooling, agent/MCP wrappers or vendor drivers:
  - Teaching/demo: Chory lab BME590 courses, `stefangolas/PyLabRobot_Tutorials_BME590`, `rickwierenga/plr-game-of-life`, `tic-tac-tobot`, T-Rex game.
  - Tooling: Cheshire-Labs orca, `Koeng101/pylabrobot-protobuf`, `maraxen/praxis`, `norle/plr-gui`.
  - Agent/MCP wrappers: `Infera-Bio/plr-mcp`, IvoryOS-PLR, `nygmeta/OpenLabAI`, Biomni's `lab_automation.py`, many "scientific-skills" mirrors.
  - Vendor drivers: `SLKS99/PyFluent` for Tecan Fluent.
- **Paper-linked PLR code is nearly absent.** Only two triples were found:
  1. **OLH: A Purpose-Built Open Source Liquid Handler** (Golas, …, Chory; bioRxiv 2026, 10.64898/2026.03.02.709168). PLR turbidostat code is at `chory-lab/plr-turbidostat`, with an MIT PLR fork at `chory-lab/olh-pylabrobot`. Results: pipetting MAE 4.1 vs 7.2 µL manual, and about 200 turbidostat cultures held at setpoint. *Partial*: custom hardware, and the turbidostat repo has no licence.
  2. **LabscriptAI** (bioRxiv 2025.09.30.679666; `KRATSZ/LabScript-AI`, 131★). This is an LLM protocol-generation system with a PLR simulator. Experiments ran on OT-2, Flex, Hamilton Vantage and Tecan Fluent: 318 GFP variants characterised, and enzyme mutants with more than 3× activity. *Partial*: the repo holds the agent, not the executed scripts. It is also **directly related work / a competitor for Text2WetLab**.
- Real PLR wet-lab scripts without a paper: `har1eyk/hamilton-starlet-scripts` (STARlet protein extraction, Orange G volume QC) and `Pioneer-Research-Labs/ngs_library_prep` (already in the corpus as `pioneer-ngs`).
- PyHamilton (the PLR predecessor) has more paper-linked code: `finyl/parseq-pyhamilton` (parSEQ, bioRxiv 2023), `stefangolas/iPSC-Robot` (bioRxiv 2020) and the dgretton repos (already in the corpus as `chory-2021-hamilton`). These could be ported to the PLR STAR simulator.
- **Conclusion:** PLR is not yet a source of published triples. If PLR tasks are needed, port Opentrons or PyHamilton triples into PLR (for example parSEQ, MSD Bradford/PicoGreen, GFP burden) rather than waiting for native PLR papers.

## Top 15 new candidates

| # | id | paper (venue, year) | code | why |
|---|---|---|---|---|
| 1 | `gfp-codon-burden-ot2` | Codon usage modulates burden vs yield (J Biol Eng 2025, CC BY) | alexismhill3/gfp_deoptimization_burden (MIT) | apiLevel 2.18 growth/induction protocols per day; raw + processed plate-reader data in repo; ready |
| 2 | `msd-biochem-assays-ot2` | Automation of biochemical assays using an open-sourced, inexpensive robotic liquid handler (SLAS Tech 2024) | MSDLLCpapers/Opentrons-OT2-BioChemical-Assays (Apache-2.0) | Bradford + PicoGreen standard curves, self-contained; ready |
| 3 | `massspecpreppy-ot2` | MassSpecPreppy (Proteomics 2023) | stemicha/MassSpecPreppy (GPL-3.0) | BCA + red/alk + SP3 digestion templates; ready (needs parameter fill) |
| 4 | `arcadia-his-elisa-ot2` | Automated Cayman His-tag ELISA (Arcadia pub, CC BY) | Arcadia-Science/cayman-his-elisa-opentrons-workflow (MIT) | 2-protocol ELISA with plate-map CSV + analysis notebook; ready |
| 5 | `flat-agar-celegans-ot2` | Flat agar and optimized media for C. elegans imaging (Arcadia pub, CC BY) | Arcadia-Science/menisquish-flat-agar (MIT) | bleach sync, OP50 spotting, worm plating; ready |
| 6 | `roboctab-dna-extraction` | RoboCTAB high-throughput plant DNA extraction (Plants 2025, CC BY) | tomstamour/RoboCTAB (no licence) | OT-2 + Flex versions; ready (licence flag) |
| 7 | `lysostaphin-turbidity-ot2` | Turbid but accurate: lysostaphin quantification (Microb Cell Fact 2026, CC BY) | JuBiotech/Supplement-to-Prigolovkin-et-al.-2025 (AGPL) | enzyme turbidity assay, raw data; ready (link only, AGPL) |
| 8 | `halogenation-pharma-ot2` | Automated late-stage halogenation of pharmaceuticals (ChemRxiv 2026) | GreenawayLab/automated_halogenation_of_pharmaceuticals (BSD-3) | chemistry reaction-setup and NMR-prep protocols; ready |
| 9 | `roche-pipetting-performance-ot2` | Deep integration of low-cost LH robots in pharma (SLAS Tech 2024) | arthur-theuer/pipetting-performance (GPL-3.0) | photometric accuracy/precision QC (p20/p300); ready; repo-paper link inferred, verify |
| 10 | `shampoo-formulations-ot2` | High-throughput shampoo formulations dataset (Sci Data 2024, CC BY) | AniketChitre/formulations-prep (no licence) | viscous formulation prep + dataset; ready |
| 11 | `ant-cloning-ot2` | Automating Cloning by Natural Transformation (ACS Synth Biol 2020) | ljm176/ANTCloning | 5-step PCR → DpnI → OE-PCR → transformation → plating pipeline; partial (licence, OA) |
| 12 | `moc-screening-ot2` | Automated workflow for metal-organic cage screening (Angew Chem 2025, CC BY) | GreenawayLab/development-automated-workflow-mocs | 5 apiv2 scripts + Zenodo data; partial (no licence) |
| 13 | `tobis-cytof-barcoding-ot2` | Multiplexed single-cell analysis of organoid signalling (Nat Protoc 2021) | TAPE-Lab/OT-2_Code | 35/126-plex barcode production/aliquoting; partial (paywall, licence) |
| 14 | `sarscov2-hypercube-pooling-ot2` | Efficient SARS-CoV-2 specimen pooling (Sci Rep 2021, CC BY) | CERI-KRISP/... (MIT) | APIv1 pooling scripts: good v1→v2 "hard" task |
| 15 | `parseq-pyhamilton` | parSEQ (bioRxiv 2023) | finyl/parseq-pyhamilton | Hamilton barcoding PCR / cherry-pick / Illumina + nanopore library prep; best PLR-port candidate |

Honourable mentions:
- `pasta-spatial-ot2` (Nat Methods 2026; repo has no licence)
- `robotic-titration-cv-ot2` and `viscous-liquid-bo-ot2` (Digital Discovery; robot driven by a camera/HTTP loop)
- `olh-turbidostat-plr` (the only native PLR triple)
- `pac832-galr1-ot2` (rich data; paper DOI not yet found)
- `ecoli-protein-expr-purif-ot2` and `trypanosomatid-drug-combo-ot2` (READMEs say "our paper" but give no DOI)

Related work worth citing, not as tasks: `labscriptai-protein-eng`, `prism-protocol-gen` (Digital Discovery 2026) and `ot2-cherrypick`. These are LLM- or GUI-driven protocol generators evaluated on real robots.

## Duplicates of the existing corpus (marked `duplicate_of_existing`)

| Repo(s) | Existing corpus entry |
|---|---|
| COPICK | copick |
| Opentrons-ProxyViscometer, beatricesoh/OTProxyViscometer | proxy-viscometer |
| czbiohub 2024-accs-pub, accs-protocol-software-pub | opencell-automation |
| AssemblyTron | assemblytron |
| OT-Mation | ot-mation |
| dgretton pyhamilton, roboplaque, population_dynamics | chory-2021-hamilton |
| Slowpoke | slowpoke |
| HULP RNA extraction | hulp-rna-extraction |
| covid19clinic | covid19clinic |
| StandardDigestion-Opentrons | shotgun-proteomics-jove |
| BOTany | botany |
| Moeller library | moeller-hackflex |
| SideKick Liquid-Handler | sidekick |
| TransporterScreening | transporter-screening |
| Pioneer ngs_library_prep | pioneer-ngs |
| Biocomputation-CBGP/OT2 | lap-transposon-genotyping (same group/workflow) |
| BU-ISCIII opentrons_covid19 | possibly covid-diagnostic-capacity-2021 (needs checking) |
| fastKris | protein-crystallization-ot2 (topic overlap only) |

## Caveats

- `est_tasks` is a rough count: an easy+hard pair counts as 2, and distinct experiments are counted separately.
- Open-access status comes from Crossref licence metadata; bioRxiv entries show bioRxiv's generic licence URL. Check each paper before vendoring a PDF.
- No `.py` was run through `opentrons_simulate` or the PLR simulator. "Ready" is judged from code inspection: self-contained apiv2, standard or bundled labware, and no external hardware loops.
- Repo-to-paper links marked "inferred" (`roche-pipetting-performance-ot2`, `vadr-vacuum-miniprep-flex`) need a manual check.
