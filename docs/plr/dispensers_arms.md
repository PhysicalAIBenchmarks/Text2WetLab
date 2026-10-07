# PLR-Supported Dispenser & Robotic Arm: Paper–Code Pairs

Research date: 2026-10-04

## PLR device coverage — clarifications upfront

Before per-entry listings, two corrections to the task's initial device list:

- **Mosquito HV/LV** is made by **SPT Labtech** (formerly TTP Labtech), not Formulatrix. It is **not** in PLR's device registry.
- **Dragonfly** is made by **SPT Labtech**, not Formulatrix. It is **not** in PLR's device registry.
- **Universal Robots UR3/UR5** are **not** in PLR's device registry (`docs/_static/devices.json` and `pylabrobot/` module tree).
- **Hamilton CO-RE Grip / iSWAP** are integrated accessories of the Hamilton STAR/Vantage, not separate PLR devices; the Hamilton STAR itself is fully supported.

Confirmed PLR-supported devices relevant to this search (from `docs/_static/devices.json`):
- `formulatrix-mantis` — Formulatrix Mantis (WIP, PR #987 open as of 2026-04)
- `brooks-preciseflex` — Brooks/Precise Automation PreciseFlex 400 (Full v1)
- `inheco-odtc` — Inheco ODTC On-Deck Thermal Cycler (legacy support)
- `ufactory-xarm6` — UFACTORY xArm 6 (Basic v1, merged ~2026-09)
- `hamilton-star` / `hamilton-vantage` — Hamilton STAR/Vantage with iSWAP/CO-RE Grip (Full v0)

---

## Entries with confirmed paper + code

---

### Machine: Brooks PreciseFlex 400

```
Machine: Brooks PreciseFlex 400 (SCARA robotic arm)
PLR support: pylabrobot/brooks/precise_flex/ — Full v1

Paper: "GLAS: an open-source easily expandable Git-based scheduling architecture
        for integral lab automation"
  Authors: Jean-Charles Cousty, Tanguy Cavagna, Alec Schmidt, Edy Mariano,
           Keyan Villat, Florian de Nanteuil, Pascal Miéville (Swiss Cat+ / EPFL)
  Year: 2024
  URL:  https://pubs.rsc.org/en/content/articlehtml/2024/dd/d4dd00253a
  DOI:  10.1039/D4DD00253A
  Preprint: https://doi.org/10.26434/chemrxiv-2024-bf0bq-v2

Code: https://github.com/swisscatplus/glas
  Description: GLAS (Git-based Lab Automated Scheduler) orchestrates a full
  automated chemistry laboratory at EPFL's Swiss Cat+ facility. The repo
  contains: orchestrator (scheduling engine), task and workflow definitions,
  node modules for each connected instrument, and a REST API. A Brooks PreciseFlex
  SCARA arm (the paper refers to a PreciseFlex 3400, a longer-reach variant in
  the same family as the 400) moves plates/vials between instruments. The
  system demonstrates multi-step catalysis optimisation campaigns (reaction
  screening, purification, analysis) that run overnight without operator
  intervention.
  Web client: https://github.com/swisscatplus/glas-web-client

Notes:
  - Experiment domain is automated synthetic chemistry / catalysis, not
    biological assays. However, the GLAS architecture is instrument-agnostic
    and the task's search strategy specifically targets this paper.
  - PLR's own PreciseFlex 400 driver (pylabrobot/brooks/precise_flex/) is
    developed independently of GLAS; GLAS uses its own socket-level wrapper.
  - PLR confirmed firmware: PreciseFlex 400 (robot_type 12), GPL 5.1D4,
    TCP Command Server 3.0D4.
```

---

### Machine: Hamilton STAR (with iSWAP / CO-RE Grip arm)

```
Machine: Hamilton STAR / STARlet (liquid-handling robot with integrated arm)
PLR support: pylabrobot/hamilton/star/ — Full v0 (liquid handling + arm)

Paper: "Enabling high-throughput biology with flexible open-source automation"
  Authors: Gretton D, Sherrill-Mix S, Mehta S, … (MIT Media Lab / Weiss Lab)
  Year: 2021
  URL:  https://www.embopress.org/doi/10.15252/msb.20209942
        https://pmc.ncbi.nlm.nih.gov/articles/PMC7993322/
  DOI:  10.15252/msb.20209942
  Preprint: https://www.biorxiv.org/content/10.1101/2020.04.14.041368

Code: https://github.com/dgretton/pyhamilton
  Description: Pyhamilton is a Python package for open-ended programming of
  Hamilton STAR/STARlet robots. Experiment-specific repos linked from the paper
  include:
    - pyhamilton_population_dynamics — simulates geographic population
      dynamics with bacterial cultures using complex multi-source pipetting
    - roboplaque — doubles speed of automated bacterial phage plaque assays
    - many_basic_turbidostats / many_asynchronous_turbidostats — maintains
      ~500 simultaneous bacterial turbidostat cultures with real-time OD
      feedback and fluorescence monitoring
  The CO-RE Grip is Hamilton STAR's built-in plate-gripper arm; it is used
  for plate transport in all these workflows and is not a separate PLR device.

  Linked NGS protocol repo (no associated paper, but uses Inheco ODTC):
    https://github.com/stefangolas/ngs-protocols
    Protocols: 10X GEM-X, PacBio HiFi Plex, Oxford Nanopore LSK109/LSK114,
    QIAseq RNA Fusion, KAPA Roche HyperPrep. Runs on Hamilton STAR +
    Inheco On-Deck Thermal Cycler + Inheco CPAC + Hamilton HHS heater shakers.
    Note: author states protocols are "illustrative guides" not sample-tested.

Notes:
  - The CO-RE Grip / iSWAP is Hamilton STAR's internal arm; not a separate
    PLR device but fully used within pyhamilton workflows.
  - PLR's Hamilton STAR support supersedes pyhamilton for new projects but
    the pyhamilton paper remains the canonical biology-automation reference
    for this hardware family.
```

---

## Entries where PLR support exists but no qualifying paper+code pair was found

---

### Machine: Formulatrix Mantis

```
Machine: Formulatrix Mantis (microfluidic non-contact nanoliter dispenser)
PLR support: PR #987 (opened 2026-04-04 by user xbtu2) — WIP / not merged yet

Paper: None found that combines (a) Mantis as primary instrument, (b) biology
  experiment, and (c) open Python code on GitHub.

Context:
  The Mantis is widely used in NGS library preparation (miniaturised reactions,
  <100 nL) and drug-screening workflows, but these applications typically rely on
  proprietary vendor software (Formulatrix's MANTIS API) with no published code.
  PLR integration is in-progress; the open PR adds a chip-based contactless
  dispensing backend (firmware 4.20.3).

Search leads that did NOT qualify:
  - JBEI/ART (Nat Commun, 2020, DOI: 10.1038/s41467-020-18008-4,
    GitHub: JBEI/ART): machine-learning recommendation tool for metabolic
    engineering — code available but no Mantis mentioned in the automation stack.
  - pyhamilton paper: uses Hamilton STAR, no Mantis.
  - GLAS: chemistry, no Mantis.

Action: Monitor PLR PR #987 for merge. Once merged, the lab behind xbtu2 may
  publish a methods paper. Search "Formulatrix Mantis python autoprotocol
  github" on bioRxiv periodically.
```

---

### Machine: Inheco ODTC

```
Machine: Inheco ODTC (On-Deck Thermal Cycler for 96/384-well PCR)
PLR support: pylabrobot/legacy/thermocycling/inheco/odtc_backend.py
  (ExperimentalODTCBackend, also SiLA 1 discovery support)

Paper: None found that pairs (a) Inheco ODTC as primary instrument, (b) biology
  experiment, (c) open Python code on GitHub linked to a peer-reviewed paper.

Context:
  The ODTC is heavily used in automated NGS workflows on Hamilton STAR/Tecan EVO
  platforms. The best open-source lead found is:
    https://github.com/stefangolas/ngs-protocols
  which uses Hamilton STAR + Inheco ODTC + Inheco CPAC for 5 NGS library prep
  protocols, but this repo has no associated published paper and the author
  notes the protocols were not tested with biological samples.

PLR forum discussion (https://discuss.pylabrobot.org/t/inheco-odtc-in-plr/423)
  confirms the ODTC backend was developed internally by at least one lab that is
  "using [it] in lab for awhile now and it's working nicely" (Cody, 2026-08),
  but no publication or external code has been posted.

Action: Contact PLR contributor cmoscy (https://github.com/cmoscy/pylabrobot)
  whose odtc branch contains the most complete SiLA implementation, to ask about
  associated biology use case and publication timeline.
```

---

### Machine: UFACTORY xArm 6

```
Machine: UFACTORY xArm 6 (6-axis collaborative robot arm)
PLR support: pylabrobot/ufactory/xarm6/ — Basic v1 (merged ~2026-09)

Paper: None found pairing (a) xArm 6 specifically, (b) biology experiment,
  (c) open Python code on GitHub.

Context:
  PLR's xArm 6 driver is very recent (PRs merged September–October 2026).
  The driver supports Cartesian motion, joint control, gripper operations,
  pick-and-drop workflows, and freedrive mode. No lab publication has appeared
  yet. The driver file (pylabrobot/ufactory/xarm6/xarm6.py) contains no
  institutional or paper references.

Action: Watch for publications from labs contributing the xArm driver. The
  xArm is a cost-effective arm frequently adopted in university labs; a
  biology-automation paper is plausible in the 2026–2027 timeframe.
```

---

## Entries for devices NOT in PLR (per task request)

---

### Machine: SPT Labtech Mosquito (HV / LV / Crystal)

```
Machine: SPT Labtech Mosquito (formerly TTP Labtech)
  — nanoliter positive-displacement pipettor for crystallography / NGS miniaturisation
PLR support: NOT present in pylabrobot device registry.
  (Note: Mosquito is made by SPT Labtech, not Formulatrix.)

Paper: "Automation in biological crystallization" (review)
  Authors: Newman J et al.
  Year: 2014
  URL:  https://pmc.ncbi.nlm.nih.gov/articles/PMC4051518/
  DOI:  10.1107/S1399004714005003

Code: None found — the paper is a review and references no open Python code.
  Crystallography facilities (e.g., Weizmann ISPC, Diamond Light Source) use
  Mosquito in automated workflows, but vendor software (Mosquito X1 GUI, SAMI
  scheduler) is proprietary and no Python automation repo was found.

Status: Incomplete — paper exists but no qualifying open-code repo found.
  Mosquito is not in PLR; this entry is informational only.
```

---

### Machine: SPT Labtech Dragonfly Discovery

```
Machine: SPT Labtech Dragonfly Discovery (multi-channel non-contact reagent dispenser)
  — formerly TTP Labtech Dragonfly
PLR support: NOT present in pylabrobot device registry.
  (Note: Dragonfly is made by SPT Labtech, not Formulatrix.)

Paper: None found with open Python code on GitHub.
  Dragonfly is commonly used in HTS reagent dispensing and NGS setup but all
  automation is via vendor software (Dragonfly API, LabView drivers).

Status: Incomplete — no qualifying paper+code pair found.
  Dragonfly is not in PLR; this entry is informational only.
```

---

### Machine: Universal Robots UR3 / UR5

```
Machine: Universal Robots UR3 / UR5 (collaborative 6-axis robot arm)
PLR support: NOT present in pylabrobot device registry.

Best candidate found:

Paper: "BioMARS: A Multi-Agent Robotic System for Autonomous Biological
  Experiments"
  Authors: Yibo Qiu, Zan Huang et al.
  Year: 2025
  URL:  https://arxiv.org/abs/2507.01485
  arXiv: 2507.01485

Code: https://github.com/AlexandreQ27/BioMARS
  Description: LLM/VLM-orchestrated dual-arm robot platform for autonomous
  cell culture. Demonstrated on: HeLa, Y79, DC2.4 cell passaging; iPSC-RPE
  differentiation optimisation. 90% reduction in hands-on time vs manual.
  Hardware described as "collaborative dual-arm robot" — exact UR model not
  confirmed in the paper abstract; likely UR5e or similar based on the payload
  and reach described, but this is not confirmed in available text.

Notes:
  - UR arm model not confirmed (abstract only says "collaborative dual-arm robot").
  - This is an arXiv preprint (not yet peer-reviewed / journal-published as of
    2026-10-04).
  - UR3/UR5 are not in PLR; this entry is informational only.

Status: Partial — paper+code pair exists, but UR model not confirmed and paper
  is preprint-only. Not a PLR instrument.
```

---

### Machine: Hamilton CO-RE Grip / iSWAP Plate Handler

```
Machine: Hamilton CO-RE Grip (internal plate-handling arm of Hamilton STAR)
PLR support: NOT a separate PLR device. Arm motion is integrated into
  pylabrobot/hamilton/star/ (iSWAP commands in the STAR driver).

The pyhamilton paper (see Hamilton STAR entry above) is the canonical
reference. The CO-RE Grip is used implicitly in all Hamilton STAR multi-plate
workflows.

Status: Covered under the Hamilton STAR entry. No separate paper+code pair
  exists because it is not a standalone device.
```

---

## Summary table

| Machine | PLR-supported | Paper found | Code found | Qualifies |
|---|---|---|---|---|
| Brooks PreciseFlex 400 | Yes (Full v1) | Yes — DOI 10.1039/D4DD00253A | Yes — swisscatplus/glas | YES (chemistry lab) |
| Hamilton STAR + CO-RE Grip | Yes (Full v0) | Yes — DOI 10.15252/msb.20209942 | Yes — dgretton/pyhamilton | YES (biology) |
| Formulatrix Mantis | Yes (WIP PR#987) | No | No | NO — WIP |
| Inheco ODTC | Yes (legacy) | No (pub) | Partial (no paper) | NO — no paper |
| UFACTORY xArm 6 | Yes (Basic v1) | No | No | NO — too new |
| SPT Labtech Mosquito | No | Review only | No | NO — not PLR |
| SPT Labtech Dragonfly | No | No | No | NO — not PLR |
| Universal Robots UR3/UR5 | No | Preprint only | Yes — AlexandreQ27/BioMARS | Partial — not PLR, UR model unconfirmed |
| Hamilton CO-RE Grip (standalone) | No | N/A | N/A | N/A — integrated into STAR |
