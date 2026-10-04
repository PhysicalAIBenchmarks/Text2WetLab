# Non-OT Instrument PR Stack

Generated 2026-10-04. Outlines the PR stack to extend Text2WetLab to non-Opentrons instruments.
All papers confirmed as peer-reviewed or preprint + public GitHub code (see research_notes/).

---

## Base PR (must merge before any instrument PR)

### `feat/nonot-step-kinds`
**Files:** `paper2protocol/models.py`
**What:** Extends `Step.kind` Literal with 16 new step kinds (plate_reader_read/shake,
imager_acquire, incubator_load/unload/set_temp, storage_store/retrieve, centrifuge_spin,
robot_arm_move, liquid_handler_transfer/mix, electroporation_pulse, plate_seal/deseal).
Also extends `ContainerKind` with plate_384, plate_1536, micronic_tube_96, vial, deepwell_24.
**Status:** DONE (models.py already updated — commit this first).

---

## Instrument PRs (stack on top of base PR, order independent)

### PR 1: `feat/l3-hamilton-pyhamilton`
**Papers:**
- Chory EJ et al. (2021) — DOI: 10.15252/msb.20209942 — Mol Systems Bio
  Repos: dgretton/pyhamilton_population_dynamics, dgretton/many_asynchronous_turbidostats, dgretton/roboplaque
- DeBenedictis EA et al. (2022) — DOI: 10.1038/s41592-021-01348-4 — Nature Methods (PRANCE)
  Repo: dgretton/std-96-pace
**Instrument:** Hamilton Microlab STARlet (pyhamilton framework, not PLR directly)
**New step kinds needed:** liquid_handler_transfer, liquid_handler_mix, plate_reader_read (CLARIOstar in loop)
**Pipeline gaps:** identify works; extract needs non-OT checker (no opentrons_simulate); eval 2D only

### PR 2: `feat/l3-bmg-clariostar`
**Papers:**
- Chory EJ et al. (2021) — DOI: 10.15252/msb.20209942 (same as Hamilton pair — CLARIOstar in loop)
  Repo: dgretton/platereader
- DeBenedictis EA et al. (2022) — DOI: 10.1038/s41592-021-01348-4 (PRANCE — CLARIOstar feedback)
  Repo: dgretton/std-96-pace
**Instrument:** BMG Labtech CLARIOstar Plus (PLR-supported: CLARIOstarBackend)
**New step kinds needed:** plate_reader_read, plate_reader_shake
**Pipeline gaps:** As Hamilton — extract needs non-OT checker

### PR 3: `feat/l3-imagexpress`
**Papers:**
- Wheeler NJ et al. (2022) — DOI: 10.1371/journal.pntd.0010937 — PLoS NTD (wrmXpress)
  Repo: zamanianlab/wrmXpress
- Caterer Z et al. (2025) — DOI: 10.1016/j.ijpddr.2025.100588 — Int J Parasitol D&DR (wrmXpress GUI)
  Repo: wheelerlab-uwec/wrmXpress-gui
**Instrument:** Molecular Devices ImageXpress Nano (PLR supports Pico — same HTD file format)
**New step kinds needed:** imager_acquire, plate_reader_read (viability endpoint)
**Pipeline gaps:** extract needs image-analysis step schema; eval needs imager timeline viz

### PR 4: `feat/l3-preciseflex-glas`
**Papers:**
- Cousty JC et al. (2024) — DOI: 10.1039/D4DD00253A — Digit Discovery (GLAS)
  Repos: swisscatplus/glas, swisscatplus/glas-web-client
**Instrument:** Brooks PreciseFlex 3400/400 SCARA arm (PLR: Full v1 pylabrobot/brooks/precise_flex/)
**Domain:** Automated synthetic chemistry / catalysis (not biology — EPFL Swiss Cat+)
**New step kinds needed:** robot_arm_move, liquid_handler_transfer, centrifuge_spin, plate_seal
**Pipeline gaps:** Wet-lab common sense check different (chemistry, not cells); no biology endpoint; eval needs workcell-level viz

### PR 5: `feat/l3-liconic-pharmbio`
**Papers:**
- Johansson C et al. (2025) — DOI: 10.1101/2025.05.30.657006 — bioRxiv (AROS: Cell Painting + TPP)
  Repos: pharmbio/aros, pharmbio/robotlab, camilla-johansson/integrate-cp-tpp
**Instrument:** Liconic STX (pharmbio AROS framework — NOT PLR's LiconicBackend; own Python control)
**New step kinds needed:** storage_store, storage_retrieve, incubator_load, incubator_unload, incubator_set_temp, imager_acquire, robot_arm_move (UR10)
**Pipeline gaps:** Multi-instrument workflow; pharmbio/aros is the control layer (not PLR); eval needs compound+plate-level tracking

### PR 6: `feat/l3-btx-cultivarium`
**Papers:**
- Crits-Christoph A et al. (2025) — DOI: 10.1101/2025.11.18.689155 — bioRxiv (Bayesian electroporation)
  Repo: cultivarium/electroporation-bayesian-optimization
**Instrument:** Custom electroporator (BTX Gemini X2 cited as comparison only — PLR BTX driver NOT used)
**New step kinds needed:** electroporation_pulse, liquid_handler_transfer (CyBio FeliX / OT Flex)
**Caveat:** The actual automation uses a custom-built electroporator + CyBio FeliX + Opentrons Flex.
           BTX Gemini X2 is a comparison reference only. Scope: ingest the Bayesian optimization
           code as the experiment logic; electroporation parameters as the protocol IR.
**Pipeline gaps:** Extract is non-standard (optimization loop, not a fixed protocol); needs new IR schema for Bayesian step sequences

### PR 7: `feat/l3-tecan-fluent-llm` (lower priority — GitHub repo TBC)
**Papers:**
- Gao et al. (2025) — DOI: 10.1101/2025.09.30.679666 — bioRxiv (LabscriptAI: LLM → Tecan Fluent)
  Repo: web deployment at ai4ot.cn — GitHub URL TBC (check paper supplement)
**Instrument:** Tecan Fluent (pyFluent — NOT in PLR)
**New step kinds needed:** liquid_handler_transfer, liquid_handler_mix, plate_reader_read
**Caveat:** Repo URL unconfirmed. Hold until GitHub link verified.

---

## Eval / Checker PRs (after all instrument PRs)

### `feat/nonot-checker`
**What:** Replace `opentrons_simulate` in the check/eval step with:
- For PLR-supported instruments (Hamilton, CLARIOstar, PreciseFlex, ImageXpress Pico, BTX Gemini):
  Use PyLabRobot simulation backends (ChatterBoxBackend or equivalent mock) to validate step sequences.
- For non-PLR instruments (Tecan Fluent, pharmbio AROS): Schema-only validation (check step kinds
  are valid, volumes in range, containers exist).
**Approach:** `check.py` currently calls `opentrons_simulate`; gate on IR instrument hint field
(new field: `instrument_family: Literal["ot2", "hamilton", "bmg", "imagexpress", "preciseflex", "liconic", "generic"]`).

### `feat/nonot-viz`
**What:** Extend `eval/ir_viz.py` 2D timeline to render new step kinds:
- plate_reader_read → colored absorbance/fluorescence bar on the timeline
- imager_acquire → camera icon + well annotation
- incubator_* / storage_* → temperature/humidity annotation
- electroporation_pulse → voltage/waveform annotation
- robot_arm_move → plate-move arrow between labware positions

---

## Priority order

1. `feat/nonot-step-kinds` (DONE — merge first)
2. `feat/l3-hamilton-pyhamilton` + `feat/l3-bmg-clariostar` (same papers, do together)
3. `feat/l3-imagexpress` (cleanest: PLR driver exists, wrmXpress code is high quality)
4. `feat/l3-preciseflex-glas` (different domain — chemistry — good architectural test)
5. `feat/l3-liconic-pharmbio` (complex multi-instrument — largest scope)
6. `feat/l3-btx-cultivarium` (custom instrument — needs new IR schema)
7. `feat/l3-tecan-fluent-llm` (pending repo URL confirmation)
8. `feat/nonot-checker` + `feat/nonot-viz` (after at least 2 instrument PRs merged)
