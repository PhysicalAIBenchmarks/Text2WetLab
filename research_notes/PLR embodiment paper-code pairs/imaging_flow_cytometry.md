# PLR-Supported Imaging & Flow Cytometry: Paper–Code Pairs

Researched: 2026-10-04

---

## PLR Instrument Coverage Audit

Before listing paper–code pairs, a correction to the assumed instrument list:
the following instruments from the task brief are **NOT in the PyLabRobot codebase**
(checked via `gh api repos/PyLabRobot/pylabrobot/contents/pylabrobot`):

| Instrument assumed in PLR | Actual PLR status |
|---|---|
| Keyence BZ-X800 (plate imager) | Only a Keyence *barcode scanner* is in PLR (`pylabrobot/keyence/barcode_scanner.py`) |
| Beckman Coulter CytoFLEX S | Not present |
| BD LSRFortessa / FACSymphony | Not present |
| Nikon/Yokogawa CQ1 | Not present |

**Instruments that ARE in PyLabRobot** with imaging/cytometry capability:

| Instrument | PLR module path | Added (approx.) |
|---|---|---|
| BioTek/Agilent Cytation 5 | `pylabrobot/agilent/biotek/cytation/cytation5.py` | Oct 2024 (PR #277) |
| BioTek/Agilent Cytation 1 | `pylabrobot/agilent/biotek/cytation/cytation1.py` | 2024–2025 |
| Molecular Devices ImageXpress Pico | `pylabrobot/molecular_devices/imageXpress/pico/pico.py` | Mar 2026 (PR #883) |
| Revvity Celigo | `pylabrobot/revvity/celigo/celigo.py` | Sep 2026 (PR #1189) |
| LI-COR Odyssey Classic (model 9120) | `pylabrobot/li_cor/odyssey/odyssey.py` | 2026 (PR #1025) |

---

## Entries with Paper + Code

### 1 — Molecular Devices ImageXpress (Nano)

```
Machine: Molecular Devices ImageXpress Nano
  (same manufacturer family as PLR-supported ImageXpress Pico)
Paper: "wrmXpress: A modular package for high-throughput image analysis
        of parasitic and free-living worms"
  Authors: Nicolas J. Wheeler, Kendra J. Gallo, Elena J. G. Rehborg,
           Kaetlyn T. Ryan, John D. Chan, Mostafa Zamanian
  Year: 2022
  Journal: PLOS Neglected Tropical Diseases
  URL: https://journals.plos.org/plosntds/article?id=10.1371/journal.pntd.0010937
  DOI: 10.1371/journal.pntd.0010937
Code: https://github.com/zamanianlab/wrmXpress
  Description: Python + CellProfiler pipeline package for high-throughput
    analysis of worm imaging data acquired on an ImageXpress Nano. Supports
    five analysis modes — optical flow (motility), segmentation (Cellpose /
    YOLOv8), CellProfiler (morphology / fluorescence), tracking (Trackpy),
    and diagnostics. Biology includes anthelmintic phenotypic screening of
    C. elegans, Brugia malayi, and Schistosoma mansoni across motility,
    viability, fecundity, and feeding endpoints.
Notes: Uses the ImageXpress Nano (older model); PLR driver targets the
  ImageXpress Pico (newer). Both are Molecular Devices ImageXpress family
  instruments communicating the same plate/HTD file format. The wrmXpress
  wrapper.py explicitly parses HTD metadata files produced by all
  ImageXpress systems.
```

---

### 2 — Molecular Devices ImageXpress (Nano) — wrmXpress 2.0 GUI

```
Machine: Molecular Devices ImageXpress Nano
  (same manufacturer family as PLR-supported ImageXpress Pico)
Paper: "A graphical user interface for wrmXpress 2.0 streamlines
        helminth phenotypic screening"
  Authors: Zachary Caterer, Rachel V. Horejsi, Carly Weber, Blake Mathisen,
           Chase N. Nelson, Maggie Bagatta, Ireland Coughlin, Megan Wettstein,
           Ankit Kulshrestha, Hui Siang Benjamin Lee, Leonardo R. Nunn,
           Mostafa Zamanian, Nicolas J. Wheeler
  Year: 2025
  Journal: International Journal for Parasitology: Drugs and Drug Resistance
  URL: https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11984613/
  DOI: 10.1016/j.ijpddr.2025.100588
Code: https://github.com/wheelerlab-uwec/wrmXpress-gui
  Description: Dash-based GUI wrapping wrmXpress 2.0 for lab users without
    Python experience. Adds a new tracking pipeline that measures distance,
    velocity, tortuosity, and directional change from worm movies.
  Analysis scripts repo: https://github.com/wheelerlab-uwec/GUI_ms
    (praziquantel dose-response analysis for Schistosoma mansoni miracidia,
    R script + raw data)
Notes: The biology demonstration in this paper uses a Zeiss Stemi 508 +
  DMK37BUK178 camera for live microscopy; however the wrmXpress tool stack
  targets ImageXpress data. The analysis code and PLR-compatible ImageXpress
  data format apply equally to the Pico model PLR supports.
```

---

## Entries with Code Found but No Peer-Reviewed Paper Attached

### CytoFLEX S (Beckman Coulter) — GUI Automation Scripts

```
Machine: Beckman Coulter CytoFLEX S (NOT currently in PLR)
Code: https://github.com/FlorianBauer/cytexpert-autoit-scripts
  Description: AutoIt scripts that drive the CytExpert GUI via Windows
    UI automation to start software, load templates, open/close the hatch,
    run samples, and save output FCS files. No liquid handling robot
    integration.
Notes: No associated peer-reviewed paper. Not Python. Listed here as the
  only public CytoFLEX-specific automation codebase found. The PLR
  codebase has no CytoFLEX driver.
```

---

## Instruments with No Paper–Code Pair Found

### BioTek/Agilent Cytation 5

PLR support: Full microscopy backend added Oct 2024 (PR #277 by rickwierenga).
Capabilities in PLR: brightfield, phase contrast, color brightfield,
fluorescence (DAPI, GFP, RFP, YFP, Cy5, Cy7, FRET modes), well-by-well
movement, autofocus.

Search result: No peer-reviewed paper found that (a) uses Cytation 5 as an
imaging instrument for a real biology experiment AND (b) provides Python
automation code on GitHub. Cytation 5 is widely used as a plate reader
(absorbance/fluorescence/luminescence) in biology; its microscopy mode
is less commonly the subject of standalone automation papers.

### Revvity Celigo

PLR support: Full native driver added Sep 2026 (PR #1189). The Celigo module
in PLR (`pylabrobot/revvity/celigo/`) is the most complete imaging driver in
PLR, including camera (Lumenera SDK), galvo, laser, FTDI USB-IO, coordinate
systems, scan planning, autofocus, and diagnostics — all without requiring
the Celigo application.

Search result: No peer-reviewed paper found with a public GitHub codebase
for Celigo-driven automated biology.

### LI-COR Odyssey Classic

PLR support: Driver for model 9120 added 2026. Provides dual-channel IR
imaging at 700 nm and 800 nm, configurable resolution, and TIFF download.

Search result: No peer-reviewed paper found with associated GitHub code
specifically for Odyssey-automated biology workflow.

### Keyence BZ-X800

PLR status: NOT SUPPORTED. PLR contains only a Keyence barcode scanner
(`pylabrobot/keyence/barcode_scanner.py`). The BZ-X800 plate imager is not
integrated.

Search result: No PLR driver. No paper–code pair found.

### Beckman Coulter CytoFLEX S

PLR status: NOT SUPPORTED. No CytoFLEX driver in PLR.

Search result: The "otcyto" paper/project mentioned in the task brief does
not appear to exist under that name in any indexed preprint or journal.
CytExpert AutoIt scripts exist (see above) but are not Python and have no paper.

### BD LSRFortessa / FACSymphony

PLR status: NOT SUPPORTED.

Search result: No Python automation paper+code pair found. OpenPanel
(https://github.com/pkheisig/OpenPanel) supports panel design for both
instruments but is a panel design UI tool, not a biology experiment driver.

### Nikon/Yokogawa CQ1

PLR status: NOT SUPPORTED.

Search result: No paper–code pair found.

---

## Search Strategy Notes

- PyLabRobot codebase audited via GitHub API (`gh api repos/PyLabRobot/pylabrobot/...`)
- PR history checked for imaging-related merges (#277, #883, #985, #1025, #1122, #1189)
- wrmXpress searched via PLOS NTD (DOI confirmed), Zamanian Lab GitHub confirmed
- "otcyto" and CytoFLEX+OT-2 paper: no results found (may be a misremembered project name)
- Web search budget (200 calls) exhausted during session
- Cytation 5 biology paper: no GitHub-linked automation paper found despite extensive search
- CQ1, FACSymphony, LSRFortessa: no paper+code pairs found

---

## Recommended Next Steps

1. **Cytation 5**: Search Google Scholar for "Cytation 5 imaging python github" or
   "BioTek Cytation 5 automated fluorescence screening" filtering for papers with
   "code availability" statements. The instrument is commonly used in phenotypic
   screening but papers seldom tag GitHub repos with "cytation5".

2. **Celigo**: The Revvity publication list PDF lists many Celigo papers (see
   https://resources.revvity.com/pdfs/pbr-list-cellometer-cellaca-celigo-systems.pdf)
   — cross-reference each against GitHub for associated code.

3. **CytoFLEX S**: The ReacSight paper (Bertaux et al., 2021, DOI 10.1101/2020.12.27.424467,
   GitLab: https://gitlab.inria.fr/InBio/Public/reacsight) demonstrates fully automated
   flow cytometry in a bioreactor pipeline — but uses a Guava EasyCyte (Luminex), not
   CytoFLEX S. May serve as a structural template for a CytoFLEX implementation.

4. **PLR flow cytometry gap**: Consider opening a PLR feature request for CytoFLEX S /
   LSRFortessa drivers — the instruments have public APIs (CytoFLEX has a documented
   TCP command interface; BD BDFACS instruments support FACSDiva SDK).
