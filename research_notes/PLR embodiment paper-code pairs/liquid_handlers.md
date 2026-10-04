# PLR-Supported Liquid Handler Embodiments: Paper–Code Pairs

Researched 2026-10-04. Sources: bioRxiv, PubMed, Google Scholar, GitHub, PyLabRobot docs.

---

## PLR Support Status (from docs.pylabrobot.org/dev/user_guide/machines.html)

| Machine | PLR Support |
|---------|------------|
| Hamilton STAR / STARlet | Full v0 (legacy API) |
| Hamilton VANTAGE / Nimbus / Prep | v0 (legacy API / WIP) |
| Opentrons OT-2 | Mostly v1 |
| Opentrons Flex | Basic v1 |
| Tecan Freedom EVO | Basic v0 (legacy API) |
| Brooks PreciseFlex | Full v1 |
| **Tecan Fluent** | **NOT in PLR** (pyFluent exists independently) |
| **Beckman Coulter Biomek i5/i7/FXp** | **NOT in PLR** |
| **Andrew Alliance PIPETMAX** | **NOT in PLR** |
| **Formulatrix Dragonfly** | **NOT in PLR** (Mantis listed as WIP dispenser) |
| **Sartorius Picus** | **NOT in PLR** |
| **Eppendorf epMotion** | **NOT in PLR** |

---

## Hamilton STAR / STARlet

### Pair 1

```
Machine: Hamilton Microlab STARlet
Paper: "Enabling high-throughput biology with flexible open-source automation" — Chory EJ, Gretton DW, DeBenedictis EA, Esvelt KM, 2021
  URL: https://www.biorxiv.org/content/10.1101/2020.04.14.041368v1.full  (bioRxiv preprint)
  Published: Molecular Systems Biology 2021 (EMBO Press)
  DOI: 10.15252/msb.20209942
Code (experiment-specific repos):
  https://github.com/dgretton/pyhamilton_population_dynamics
    Description: Simulates microbial population dynamics and gene flow by moving liquid
                 between 96-well plates according to arbitrary flow matrices
  https://github.com/dgretton/many_asynchronous_turbidostats
    Description: Feedback-controlled turbidostat system maintaining hundreds of bacterial
                 cultures in log-phase growth without user intervention
  https://github.com/dgretton/roboplaque
    Description: Automated plaque assays for phage biology
Notes: Uses pyhamilton (https://github.com/dgretton/pyhamilton), NOT PLR directly.
       PLR's Hamilton backend (legacy v0) is built on the same VENUS/HSL bridge approach.
       pyhamilton is described as "a related automation framework" per user search criteria.
```

### Pair 2

```
Machine: Hamilton Microlab STARlet
Paper: "Systematic molecular evolution enables robust biomolecule discovery" — DeBenedictis EA, Chory EJ, Gretton DW, Wang B, Esvelt KM, 2022
  URL: https://www.nature.com/articles/s41592-021-01348-4
  DOI: 10.1038/s41592-021-01348-4
  Published: Nature Methods, vol. 19, pp. 55–64 (Jan 2022)
  bioRxiv preprint: https://www.biorxiv.org/content/10.1101/2020.04.01.021022v1.full
    DOI: 10.1101/2020.04.01.021022
Code: https://github.com/dgretton/std-96-pace
  Description: PRANCE (Phage-and-Robotics-Assisted Near-Continuous Evolution) — runs 96
               parallel phage-assisted continuous evolution experiments simultaneously in a
               96-well plate; 30-minute cycle time; automated luminescence/absorbance
               feedback controls selection stringency in real time
Notes: Uses pyhamilton for all liquid handling. The std-96-pace repo is the actual
       PRANCE experiment code (not the library). This is a peer-reviewed Nature Methods paper.
```

---

## Opentrons OT-2

### Pair 1

```
Machine: Opentrons OT-2
Paper: "AssemblyTron: Flexible automation of DNA assembly with Opentrons OT-2 lab robots" — Bryant JA Jr., Kellinger M, Longmire C, Miller R, Wright RC, 2023
  URL: https://academic.oup.com/synbio/article/8/1/ysac032/6956284
  DOI: 10.1093/synbio/ysac032
  Published: Synthetic Biology, Vol 8(1), Dec 2022 (peer-reviewed, Oxford University Press)
  bioRxiv preprint: https://www.biorxiv.org/content/10.1101/2022.09.29.510219v1
Code: https://github.com/PlantSynBioLab/AssemblyTron
  Description: Python package that reads j5 DNA assembly design outputs and executes them
               on the OT-2; automates PCR (with annealing temperature gradient), Golden Gate
               assembly, and homology-dependent IVA; demonstrated on four-fragment chromoprotein
               reporter plasmid assemblies
Notes: Uses Opentrons Python API natively (not PLR). OT-2 is PLR-supported (Mostly v1).
       PLR wraps the same Opentrons API.
```

### Pair 2

```
Machine: Opentrons OT-2
Paper: "An Open-Source Modular Framework for Automated Pipetting and Imaging Applications" — Ouyang W, Bowman R, Wang H, Bumke KE, Collins JT, Spjuth O, Carreras-Puigvert J, Diederich B, 2021
  URL: https://www.biorxiv.org/content/10.1101/2021.06.24.449732v1.full
  DOI: 10.1101/2021.06.24.449732
  Published: bioRxiv preprint (2021); check for final journal version
Code: https://github.com/openUC2/UC2-Hi2
  Description: Full system combining OT-2 pipetting automation with custom UC2-based modular
               microscope (Hi2); OT-2 moves samples; Raspberry Pi-based control stack run
               from Jupyter or REST API; ~7000 EUR total system cost
Notes: Uses OT-2 via its Python API and REST API. Focus of paper is the open-source
       microscopy integration (Hi2 system), not just liquid handling. Real biological
       application: automated sample preparation and imaging workflows.
```

---

## Opentrons Flex

No peer-reviewed/preprint paper with a public GitHub repo specifically using the Flex for biological experiments found as of this search. The Flex is newer (released 2023); early-adopter papers are expected to emerge 2024–2026.

---

## Tecan Freedom EVO

No peer-reviewed journal paper with a public GitHub repo using the Tecan Freedom EVO for biology experiments with Python was found. Candidate resources identified but excluded:

- **robotevo** (https://github.com/qPCR4vir/robotevo): Generates Freedom EVOware scripts from Python; associated with a 2018 doctoral thesis on RNA virus detection (not a peer-reviewed journal paper). Author: Viña Rodríguez, Ernst-Moritz-Arndt-Universität.
- **pyTecan** (https://github.com/btownshend/pyTecan): Python interface to Tecan EVO 100; no associated journal paper found.
- **PyEvo** (people.csail.mit.edu/georgiou/pyevo): COM API wrapper for Freedom EVOWare; no associated paper.

**Gap**: Tecan EVO is PLR-supported (Basic v0 legacy API), but no published biology paper + GitHub pair was identified. Further investigation recommended via Google Scholar citing pylabrobot with "Tecan" filter.

---

## Tecan Fluent

### Pair 1 (best available — LLM-mediated automation paper)

```
Machine: Tecan Fluent (via pyFluent interface)
Paper: "Autonomous liquid-handling robotics scripting through large language models enables accessible and safe protein engineering workflows" — Gao et al., 2025
  URL: https://www.biorxiv.org/content/10.1101/2025.09.30.679666v1.full
  DOI: 10.1101/2025.09.30.679666
  Published: bioRxiv preprint (Sep 2025)
Code: Web deployment at https://ai4ot.cn/ (described as open-source; dedicated GitHub repo
      not explicitly linked in the paper as of fetch date — check paper supplement)
  Description: LabscriptAI framework uses LLMs to generate protocols for Tecan Fluent,
               Opentrons OT-2/Flex, and Hamilton STAR/Vantage. Biological experiments
               shown include cell-free GFP protein synthesis, GALS enzyme variant screening
               (318 GFP variants from 53 iGEM teams), and plate reader fluorescein calibration
Notes: Tecan Fluent is NOT currently in PLR. pyFluent is an independently developed Python
       interface. This paper is primarily an LLM/automation-methods paper, but it does perform
       real biology (cell-free protein synthesis, enzyme engineering). Caveat: public GitHub
       repo URL was not confirmed from the paper text — needs verification from supplement.
```

---

## Beckman Coulter Biomek i5 / i7 / FXp

**NOT PLR-supported** as of PLR docs (2026-10-04).

Best candidate found:
- bioRxiv 2025 paper on automated arrayed CRISPRa library screening uses Biomek i7, but automation is via Beckman's proprietary Biomek 5 software (not Python/GitHub).
- No Python-based, GitHub-linked biology paper found for any Biomek model.

**Recommendation**: Search Beckman's application notes and bioRxiv specifically for "Biomek" + "Python" — some Broad Institute workflows may use Biomek with custom scripts.

---

## Andrew Alliance PIPETMAX

**NOT PLR-supported** as of PLR docs (2026-10-04). No paper+code pair found. Andrew Alliance robots are controlled via Andrew+ proprietary software. No Python API or GitHub codebase associated with biology papers was identified.

---

## Formulatrix Dragonfly (non-contact dispenser)

**NOT PLR-supported**. PLR docs list Formulatrix Mantis as a WIP dispenser (not Dragonfly). No paper+code pair found. Dragonfly is manufactured by SPT Labtech (not Formulatrix — note: Formulatrix makes the Mosquito crystallography dispenser). The Dragonfly Discovery is used primarily for assay development and library preparation but no Python-controlled, GitHub-backed biology paper was identified.

---

## Sartorius Picus (electronic pipette)

**NOT PLR-supported** as of PLR docs (2026-10-04). Sartorius Picus is a handheld/semi-automated electronic multichannel pipette, not a standalone liquid-handling robot. No paper+code pair found.

---

## Eppendorf epMotion

**NOT PLR-supported** as of PLR docs (2026-10-04). No paper+code pair found for biology experiments with Python automation and public GitHub code.

---

## Notes on Search Gaps

1. **Web search budget exhausted (200/200)** during this research session. Remaining gaps (Tecan EVO journal papers, Biomek Python scripts, Flex papers) should be searched via:
   - Google Scholar: `cite:10.1016/j.device.2023.100111` (papers citing PLR Device paper)
   - GitHub topic: `pylabrobot`, `opentrons`, `pyhamilton`
   - bioRxiv: `Hamilton STAR python github`, `Tecan EVO python automation`

2. **pyhamilton vs PLR**: The Hamilton STAR papers above use pyhamilton (dgretton/pyhamilton), not PLR. However, PLR's Hamilton backend is built on the same Venus/HSL bridge architecture. The user's criteria "PyLabRobot or a related automation framework" covers pyhamilton.

3. **Opentrons Python API vs PLR**: AssemblyTron and UC2-Hi2 use the native Opentrons Python API, not PLR. PLR's OT-2 backend wraps the same API. Same caveat applies.

4. **TurboPRANCE** (Boileau et al. 2026 bioRxiv, https://www.biorxiv.org/content/10.64898/2026.03.02.709196v1.full) — Hamilton STARlet, Chory lab at Duke. Code to be released upon final publication. Not included above as code is not yet public.

---

## Quick Reference Table

| Machine | Paper | Year | DOI | GitHub Code |
|---------|-------|------|-----|-------------|
| Hamilton STARlet | Chory et al., EMBO MSB | 2021 | 10.15252/msb.20209942 | github.com/dgretton/pyhamilton_population_dynamics |
| Hamilton STARlet | DeBenedictis/Chory et al., Nature Methods | 2022 | 10.1038/s41592-021-01348-4 | github.com/dgretton/std-96-pace |
| Opentrons OT-2 | Bryant et al., Synthetic Biology | 2023 | 10.1093/synbio/ysac032 | github.com/PlantSynBioLab/AssemblyTron |
| Opentrons OT-2 | Ouyang et al., bioRxiv | 2021 | 10.1101/2021.06.24.449732 | github.com/openUC2/UC2-Hi2 |
| Tecan Fluent | Gao et al., bioRxiv | 2025 | 10.1101/2025.09.30.679666 | ai4ot.cn (GitHub TBC) |
| Tecan EVO | — | — | — | No confirmed pair |
| Beckman Biomek | — | — | — | Not PLR-supported; no pair |
| Andrew Alliance | — | — | — | Not PLR-supported; no pair |
| Formulatrix Dragonfly | — | — | — | Not PLR-supported; no pair |
| Sartorius Picus | — | — | — | Not PLR-supported; no pair |
| Eppendorf epMotion | — | — | — | Not PLR-supported; no pair |
