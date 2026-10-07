# PLR-Supported Plate Reader and PCR Instrument: Paper–Code Pairs

Research compiled: 2026-10-04

Only entries where BOTH a peer-reviewed (or preprint) paper AND an experiment-specific GitHub
repository exist are listed as complete pairs. Partial findings (paper without code, or code
without paper) are noted separately per instrument.

---

## 1. BMG Labtech CLARIOstar (Plus)

**PLR support status:** Officially supported (`CLARIOstarBackend` in PyLabRobot)

### Entry 1 — COMPLETE

```
Machine: BMG CLARIOstar
Paper: "Enabling high-throughput biology with flexible open-source automation"
       — Chory EJ, Gretton DW, DeBenedictis EA, Esvelt KM. Molecular Systems Biology, 2021.
  URL: https://www.embopress.org/doi/full/10.15252/msb.20209942
  DOI: 10.15252/msb.20209942
Code: https://github.com/dgretton/pyhamilton
  (CLARIOstar interface module: https://github.com/dgretton/platereader)
  Description: PyHamilton drives a Hamilton STARlet liquid handler; the
               companion `platereader` package provides the Python control
               layer for the CLARIOstar reader. Experiment scripts automate
               (a) M13 bacteriophage plaque assays, (b) simulated
               metapopulation dynamics across 480 simultaneous bacterial
               cultures (turbidostat), and (c) metabolic profiling of E. coli
               across 100 media compositions in triplicate.
Notes: `platereader` is a lightweight wrapper (10 commits); the bulk of
       protocol logic lives in `pyhamilton`. Both repos are from the Esvelt
       lab / MIT Media Lab Sculpting Evolution Group.
```

### Entry 2 — COMPLETE

```
Machine: BMG CLARIOstar
Paper: "Systematic molecular evolution enables robust biomolecule discovery"
       — DeBenedictis EA, Chory EJ, Gretton DW, Wang B, Golas S, Esvelt KM.
         Nature Methods, 2022.
  URL: https://www.nature.com/articles/s41592-021-01348-4
  DOI: 10.1038/s41592-021-01348-4
  Preprint (2020): https://www.biorxiv.org/content/10.1101/2020.04.01.021022v1
Code: https://github.com/dgretton/std-96-pace   (primary PRANCE platform)
      https://github.com/dgretton/roboplaque    (robotics-accelerated plaque assays)
  Description: PRANCE (Phage-assisted Robotically Accelerated Continuous
               Evolution) houses 96 parallel phage-evolution "lagoons" on a
               Hamilton robot; the CLARIOstar positioned inside the enclosure
               provides real-time fluorescence/luminescence feedback to
               autonomously adjust selection stringency. Demonstrated on
               T7 RNA polymerase, aminoacyl-tRNA synthetase, and tRNA
               evolution.
Notes: The preprint title differs ("A high-throughput platform for
       feedback-controlled directed evolution"). Published version is the
       canonical reference. GitHub repos are maintained by Dana Gretton (MIT).
```

---

## 2. BioTek / Agilent Synergy H1

**PLR support status:** Officially supported (`SynergyH1Backend` in PyLabRobot 0.2.1)

### Partial — paper without code

```
Machine: BioTek Synergy Neo2 Hybrid
Paper: "Data-driven discovery of innate immunomodulators via machine
       learning-guided high throughput screening"
       — Tang Y, Kim JY, IP CKM, Bahmani A, Chen Q, Rosenberger MG,
         Esser-Kahn AP, Ferguson AL. bioRxiv, 2023.
  URL: https://www.biorxiv.org/content/10.1101/2023.06.26.546393v1.full
  DOI: 10.1101/2023.06.26.546393
Code: NOT FOUND — no GitHub repository is linked in the paper.
  Description: Active-learning HTS in RAW-Dual macrophage reporter cells
               (NF-κB / IRF pathways) in 384-well format. BioTek Synergy
               Neo2 read absorbance and luminescence; compound transfer was
               via a Janus G3 robotic platform. Four iterative ML screening
               rounds. No code repo was published.
Notes: Listed as a known gap. The Synergy Neo2 is closely related to Synergy
       H1 (same Gen5 software stack). A second search for equivalent papers
       with code found none. If one is discovered later, this entry should
       be upgraded to COMPLETE.
```

### Partial — code without peer-reviewed paper

```
Machine: Synergy H1 via PyLabRobot SynergyH1Backend
Code: https://github.com/PyLabRobot/pylabrobot (SynergyH1Backend module)
  Description: PyLabRobot's native Synergy H1 driver allows Python-scripted
               absorbance/fluorescence reads from within automated liquid-
               handler workflows. No standalone biology paper demonstrating
               this backend in a published experiment was found as of
               2026-10-04.
Notes: The PLR paper itself (Wierenga et al. Device 2023,
       DOI: 10.1016/j.device.2023.100111) documents the Synergy H1 backend
       but does not describe a specific biological experiment using it.
```

---

## 3. Molecular Devices SpectraMax i3x

**PLR support status:** NOT in the official PyLabRobot 0.2.1 supported-reader list
(SpectraMax i3x is listed in the task as a target but does not appear in PLR docs or
source as of the date of this research).

### Partial — code without peer-reviewed paper

```
Machine: Molecular Devices SpectraMax (M5 / i3x-class)
Code: https://github.com/GormleyLab/Spectramax
  Description: High-level Python wrapper for the SoftMax Pro Automation API
               (COM/OLE). Supports drawer open/close, UV-Vis reads,
               temperature incubation, CSV/XML/SDA export, async events, and
               simulation mode. Explicitly mentions SPECTRAmax M5. No linked
               biology paper in the repo.
Notes: No peer-reviewed paper associated with this library was found. The
       GormleyLab repository is the best available Python control layer for
       SpectraMax instruments but cannot be paired with a specific biology
       paper. This entry remains incomplete.
```

---

## 4. Applied Biosystems QuantStudio 5 / 7

**PLR support status:** NOT in PyLabRobot 0.2.1 supported list. QuantStudio machines
are RT-PCR thermocyclers; PLR has a general thermocycler API but no QuantStudio-specific
backend in mainline as of 2026-10.

### Entry 1 — COMPLETE (data-analysis framing; instrument named explicitly)

```
Machine: Applied Biosystems QuantStudio 3 / 5
Paper: "Auto-qPCR: a python-based web app for automated and reproducible
       analysis of qPCR data"
       — Maussion G, Thomas RA, Demirova I, Gu G, Cai E, Chen CX-Q,
         Abdian N, Strauss TJP, Kelaï S, Nauleau-Javaudin A, Beitel LK,
         Ramoz N, Gorwood P, Durcan TM. Scientific Reports, 2021.
  URL: https://www.nature.com/articles/s41598-021-99727-6
  DOI: 10.1038/s41598-021-99727-6
  Preprint: https://www.biorxiv.org/content/10.1101/2021.01.14.426748
Code: https://github.com/neuroeddu/Auto-qPCR
  Description: Python web-app that ingests QuantStudio 3/5 CSV exports and
               automates ΔCt, ΔΔCt, and absolute-quantification pipelines.
               Biological use cases: genomic instability in iPSC lines,
               gene expression in cortical/dopaminergic neuron differentiation,
               cocaine-treatment dataset reanalysis. The instrument is
               explicitly named; code processes real experimental data.
Notes: This is a post-acquisition analysis tool, not real-time instrument
       control. The QuantStudio 5 generates the raw data; Auto-qPCR automates
       downstream processing. Listed as a complete pair because the instrument
       is explicitly named, real biology was done, and a reusable Python
       codebase was published alongside the paper.
```

### Entry 2 — PARTIAL (instrument control library; conference poster only)

```
Machine: Applied Biosystems QuantStudio 5
Paper/Poster: "Qslib: Python control of qPCR machines for molecular
              programming experiments" — Evans CG. DNA28 conference poster,
              2022. (Zenodo record, not a peer-reviewed journal article.)
  URL: https://zenodo.org/records/7495939
  DOI: 10.5281/zenodo.7495939
Code: https://github.com/cgevans/qslib
  Description: Full SCPI-over-TCP instrument control library for QuantStudio
               5 (96-well). Supports protocol creation, real-time temperature
               monitoring, fluorescence data as Pandas DataFrames, and
               Jupyter-notebook interaction. Designed for DNA computing and
               molecular programming (non-qPCR) experiments.
Notes: The associated publication is a conference poster (DNA28), not a
       peer-reviewed journal article. A subsequent Nature paper
       ("A thermodynamically favoured molecular computer," Nature 2026,
       DOI: 10.1038/s41586-026-10996-5) likely uses qslib for QuantStudio
       experiments, but that paper's methods could not be confirmed at time
       of research. Upgrade this entry if the Nature 2026 paper is confirmed
       to use qslib + QuantStudio 5.
```

---

## 5. Bio-Rad CFX96 / CFX384

**PLR support status:** NOT in PyLabRobot supported list.

### No complete pair found

```
Machine: Bio-Rad CFX96 / CFX384
Status: NO COMPLETE PAPER+CODE PAIR FOUND

Searches on PubMed, bioRxiv, and GitHub combining "CFX96," "CFX384,"
"Bio-Rad," "Python," "automation," and "github" returned no peer-reviewed
paper with an associated GitHub experiment codebase specific to these
instruments. The Bio-Rad CFX Maestro software does not expose a public
Python API, and community-written Python wrappers specific to CFX96/CFX384
were not found with linked publications.

Closest partial finding:
- Bio-Rad offers a "CFX Automation System II" product but no open Python SDK.
- The CFX Opus line has a BR.io API for networking but no peer-reviewed
  demonstration with open code was located.
Notes: This is the weakest instrument in the survey. Recommend revisiting
       with a targeted PubMed search: "CFX96[tiab] AND python[tiab] AND
       github[tiab]" or checking preprint servers for synthetic-biology
       labs known to publish code (Shipman, Bhatt, Bhatt labs, etc.).
```

---

## 6. Tecan Spark (plate reader)

**PLR support status:** Officially supported as `Tecan Spark 20M` in PyLabRobot 0.2.1

### Entry 1 — COMPLETE

```
Machine: Tecan Spark (plate reader)
Paper: "Lustro: High-throughput optogenetic experiments enabled by automation
       and a yeast optogenetic toolkit"
       — Harmer ZP, McClean MN. ACS Synthetic Biology, 2023.
  URL: https://www.biorxiv.org/content/10.1101/2023.04.07.536078v2
  (preprint; published ACS Synth Biol 2023 — journal DOI not confirmed in
   this research session; confirm via https://pubs.acs.org)
Code: https://github.com/mccleanlab/Lustro
  Description: Sample analysis scripts for Tecan Spark output from
               high-throughput optogenetics experiments in 96-well yeast
               cultures. Lustro integrates an optoPlate-96 LED illumination
               device + Tecan Spark plate reader on an automated platform.
               Scripts process fluorescence readings (mScarlet-I) and
               generate growth / reporter graphs.
Notes: The Tecan Spark reader is confirmed as the measurement device
       (fluorescence of mScarlet-I). The optoPlate illumination hardware
       code is at https://github.com/mccleanlab/Optoplate-96. The Lustro
       repo contains analysis scripts only, not full instrument-control
       code — real-time Spark interaction occurs via Tecan's own software.
```

### Entry 2 — COMPLETE

```
Machine: Tecan Spark (plate reader)
Paper: "Dynamic Multiplexed Control and Modeling of Optogenetic Systems Using
       the High-Throughput Optogenetic Platform, Lustro"
       — Harmer ZP, Thompson JC, Cole DL, Venturelli OS, Zavala VM,
         McClean MN. ACS Synthetic Biology, 2024.
  URL: https://pmc.ncbi.nlm.nih.gov/articles/PMC11106771/
  DOI: 10.1021/acssynbio.3c00761
Code: https://github.com/mccleanlab/Optoplate-96
      https://github.com/zavalab/ML/tree/master/Optogenetics
  Description: Extends Lustro for multiplexed control of two optogenetic
               split transcription factor systems (CRY2/CIB1 and eMagAF/eMagBF)
               using distinct light programs. Machine-learning (neural nets +
               Bayesian optimization) identifies optimal light conditions.
               Tecan Spark reads fluorescence from yeast reporter strains.
               ML code is in the Zavala lab ML repo.
Notes: Two GitHub repos are needed to reproduce: Optoplate-96 (illumination
       hardware firmware/scripts) and zavalab/ML (modeling + optimization
       code). The Tecan Spark is explicitly named. A companion JoVE video
       protocol was also published (JOVE 2023).
```

### Entry 3 — COMPLETE

```
Machine: Tecan Spark (plate reader)
Paper: "Enhancing high-throughput optogenetics: Integration of LITOS with
       Lustro enables simultaneous light stimulation and shaking"
       — Harmer ZP, Höhener TC, Landolt AE, Mitchell C, McClean M.
         microPublication Biology, 2024.
  URL: https://pmc.ncbi.nlm.nih.gov/articles/PMC10873752/
  DOI: 10.17912/micropub.biology.001073
Code: https://github.com/pertzlab/LITOS
  Description: LITOS (Light-Induced Temperature-Oscillation System) is
               integrated with Lustro; a 3D-printed adapter allows concurrent
               LED stimulation and shaking. Tecan Spark reads mScarlet-I
               fluorescence from yeast cultures.
Notes: This is a short methods note in microPublication Biology
       (peer-reviewed). The Tecan Spark is explicitly named. LITOS code
       is from the Pertz lab (University of Bern).
```

---

## Summary Table

| Instrument              | PLR Support        | Paper+Code Pair    | Notes                                   |
|-------------------------|--------------------|--------------------|------------------------------------------|
| BMG CLARIOstar          | Official           | 2 complete pairs   | Esvelt lab (MIT), pyhamilton + platereader |
| BioTek Synergy H1       | Official           | 0 complete pairs   | Neo2 paper found but no code; gap         |
| Mol. Dev. SpectraMax i3x| Not in PLR 0.2.1  | 0 complete pairs   | Code exists (GormleyLab) but no paper     |
| AB QuantStudio 5/7      | Not in PLR 0.2.1  | 1 complete (post-acq) + 1 partial poster | Best: Auto-qPCR + QSLib |
| Bio-Rad CFX96/CFX384    | Not in PLR 0.2.1  | 0 complete pairs   | No paper+code pair found; biggest gap     |
| Tecan Spark             | Official           | 3 complete pairs   | McClean lab (Lustro series)              |

---

## Key Repositories Referenced

| Repo | Instrument | Role |
|------|-----------|------|
| https://github.com/dgretton/pyhamilton | BMG CLARIOstar | Hamilton robot + CLARIOstar control |
| https://github.com/dgretton/platereader | BMG CLARIOstar | CLARIOstar Python interface |
| https://github.com/dgretton/std-96-pace | BMG CLARIOstar | PRANCE directed evolution platform |
| https://github.com/dgretton/roboplaque | BMG CLARIOstar | Robotic plaque assays |
| https://github.com/mccleanlab/Lustro | Tecan Spark | Spark output analysis scripts |
| https://github.com/mccleanlab/Optoplate-96 | Tecan Spark | LED illumination control + Spark integration |
| https://github.com/zavalab/ML/tree/master/Optogenetics | Tecan Spark | ML optimization code |
| https://github.com/pertzlab/LITOS | Tecan Spark | LITOS illumination system |
| https://github.com/neuroeddu/Auto-qPCR | QuantStudio 5 | qPCR data analysis web app |
| https://github.com/cgevans/qslib | QuantStudio 5 | Instrument control via SCPI |
| https://github.com/GormleyLab/Spectramax | SpectraMax M5 | SoftMax Pro Python wrapper |
