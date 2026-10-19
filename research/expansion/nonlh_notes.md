# Non-liquid-handling (non-LH) candidates: notes

Source agent: `nonlh`. Data file: `nonlh_candidates.jsonl` (82 candidates, one JSON object per line).

## How the search was run

GitHub API access was unavailable: the `gh` token was invalid, and unauthenticated calls are limited to 60 per hour. Web search was rate-limited for part of the session. The search used these methods instead:

- **Europe PMC REST search** (journals plus bioRxiv/ChemRxiv preprints). Queries:
  - `"self-driving laboratory" AND github`
  - `"robotic arm" AND "plate reader" AND github`
  - `"PF400" OR "PreciseFlex"`
  - `"xArm" AND laboratory AND automation`
  - turbidostat/morbidostat/continuous culture + github
  - pycro-manager / Micro-Manager smart microscopy
  - colony picking (twice)
  - SiLA 2
  - Chemputer/XDL titles
  - mobile robotic chemist
  - Pioreactor / eVOLVER / Chi.Bio
  - autofocus microscopy
  - event-driven acquisition
  - cloud lab / Emerald Cloud Lab / Strateos
  - LabOP / Autoprotocol
  - self-driving lab titles
  - flow chemistry self-optimising
  - LLM + robot + chemistry/biology
  - HardwareX robotic arm / incubator / microscope
  - plate reader + python
  - smart/feedback/adaptive microscopy
  - Opentrons + robotic arm
  - digital twin lab robot
  - electrochemistry SDL + github
  - powder dispensing
- **Code links from full text.** For about 75 DOIs, the Europe PMC full-text XML was scanned for links to GitHub, GitLab, Zenodo and figshare.
- **Repository checks.** About 90 repos were checked with a shallow, blob-less `git clone` of the file tree only. This confirmed each repo exists, gave the file list, and identified the licence from the LICENSE file text. I searched each file list for mock/simulator/fake/virtual/demo files to judge whether it can be simulated.
- **DOI confirmation.** DOIs I was unsure of were checked on Crossref: Atlas, BayBE, ORGANA, MADSci, AlabOS, ChemOS 2.0, PyLabRobot, PANDA and RoboChem.
- **Web searches** for code locations: RoboChem, PANDA, SDL-Demo, SAMPLE and WEI.

**Duplicate check against `docs/task-sources.md`:** no paper overlaps exactly. Related entries are marked in `duplicate_of_existing`:
- `ad-sdl-pf400-module` is related to `glas-preciseflex` (both are PF400 drivers).
- `uc2-esp` is in the same UC2 ecosystem as `uc2-hi2`.
- `pylabrobot-nonlh` is covered by the PyLabRobot/LH agents.

Existing corpus entries that are partly non-LH were not re-added: aros-cellpainting, optoplate-ml, lustro, wrmxpress, proxy-viscometer and polymerisation-kinetics-robot.

**Caveats:**
- Fields marked "unverified" or "check Zenodo" were not opened.
- The HELAO DOI and Pioreactor's testing mode are taken from memory and not confirmed.
- A licence recorded as "LICENSE present, unrecognised" needs reading before any code is vendored (Coscientist, ACRA, BEAR, UC2-REST).

## Counts

By readiness: **ready 20**, partial 48, no 14. Estimated tasks: 89 from ready candidates, 169 in total.

| task_type | n | ready | partial | no |
|---|---|---|---|---|
| imaging | 16 | 7 | 9 | 0 |
| synthesis | 16 | 1 | 11 | 4 |
| protocol_language | 10 | 5 | 5 | 0 |
| bioreactor | 9 | 1 | 6 | 2 |
| other | 9 | 0 | 4 | 5 |
| plate_transport | 8 | 1 | 5 | 2 |
| characterisation | 8 | 2 | 5 | 1 |
| scheduling | 6 | 3 | 3 | 0 |

By domain: biology 43, chemistry 22, materials 13, other 4.

## Which categories best extend Text2WetLab

1. **Protocol languages that compile to hardware (XDL/χDL, LabOP, Autoprotocol): best fit.**
   - The target is text, so the grader can parse it and check its structure: step and parameter matching, plus compile or simulate checks.
   - XDL ships a static verifier and simulation mode. Cronin's ACRA repo has more than 100 reference XDLs from literature procedures that were executed on the Chemputer, with yields reported.
   - CLAIRify ships a verifier and about 100 protocol texts.
   - LabOP has a hardware-free execution engine. DNAda emits Autoprotocol JSON with seal, thermocycle, spin and incubate steps.
   - The task shape is the same as Text2WetLab ("methods -> code"). It adds chemistry and also covers non-pipetting bio steps such as thermocycling, sealing and spinning.
   - Overlap with PyLabRobot is low.
2. **Automated microscopy acquisition: high fit, almost no overlap.**
   - The Micro-Manager demo configuration (through pymmcore-plus or pycro-manager), Navigate's "synthetic" devices, ImSwitch's virtual microscope and the mock camera in etSTED all let acquisition code run headless.
   - A grader can check the event sequence: axes, positions, z-stacks, channels, exposures, intervals, and the feedback rules used in smart microscopy.
   - Imaging methods sections are precise and number-heavy, which suits grading.
   - PyLabRobot does not cover microscopes.
3. **Bioreactor/turbidostat control programs: good fit once small stubs are written.**
   - eVOLVER `custom_script.py`, Chi.Bio custom programs and Pioreactor automations/experiment profiles are small control loops.
   - Grading can replay recorded OD traces and check pump and LED commands against the methods text: dilution thresholds, setpoints and light programs.
   - Licences are the main issue: Chi.Bio and evotron have none, while eVOLVER and Pioreactor are MIT.
4. **Workcell scheduling/orchestration (WEI/MADSci, AlabOS, SLab.jl): good fit.**
   - WEI has a `simulate_interface`, MADSci has virtual example modules, and AlabOS has `fake_lab` devices.
   - Workflow YAML and task graphs can be compared step by step: module, action and arguments.
   - This overlaps PyLabRobot's arm, reader, incubator and centrifuge backends at the device level, but not at the workflow-language level. Grade the workflow and keep PyLabRobot for device execution.
5. **Chemistry/materials SDLs with custom rigs (flow, electrochemistry, gantries): mixed fit.**
   - Most release the optimiser and data but not runnable instrument code, or they use serial drivers with no mocks (RoboChem, AFION, Clio).
   - The exception is PANDA-BEAR, which ships mocks for its CNC and potentiostats.
   - Use selectively.
6. **Arms moving plates (PF400, xArm, UR, mobile robots): low fit on their own.**
   - Driver code is low-level (TCP command strings, joint positions) and depends on site teach-points, so methods text cannot specify it.
   - It is better to grade at the workflow layer (point 4). This category also overlaps glas-preciseflex and PyLabRobot most heavily.
7. **LLM-agent papers (Coscientist, ChemCrow, ORGANA, LLM-RDF): weak sources of reference code.** Execution goes through proprietary clouds (RoboRXN, ECL) or depends on LH. They are useful as related work and baselines.

**Recommendation:** add three new task families:
- methods text to XDL (ACRA, CLAIRify, blueprints, peptide)
- imaging-methods text to Micro-Manager MDA or Navigate feature lists (pycro-manager, Mantis, EDA, OpenFlexure)
- methods text to workcell workflow (WEI, AlabOS, LabOP)

Grade each against a simulator-backed trace.

## Top 15 candidates

1. `chemputer-acra`: more than 100 literature-to-XDL pairs executed on the Chemputer; xdl dry-run is possible. Check the licence text.
2. `clairify-xdl`: NL-to-XDL with a bundled verifier and about 100 protocol texts; MIT; executed on a Franka.
3. `wei-science-factory`: open Digital Discovery paper; MIT; WEI workflow YAML runs in simulate mode (PF400, sealer, thermocycler, camera).
4. `alabos-alab`: MIT; fake-lab devices; solid-state synthesis recipes become task graphs (furnace profiles, XRD).
5. `navigate-2024`: Nature Methods; synthetic hardware for every device class; smart light-sheet feature lists.
6. `pycromanager-2021`: Nature Methods; BSD; Micro-Manager demo config; acquisition events are checkable.
7. `mantis-shrimpy`: open PNAS Nexus; acquisition-settings YAML maps directly to the methods; BSD.
8. `labop`: protocol language with a hardware-free execution engine; iGEM interlab growth-curve and calibration protocols.
9. `autoprotocol-dnada`: ACS Synth Biol (CC BY); Apache-2.0; Autoprotocol JSON with thermocycle, seal and spin steps.
10. `panda-bear`: open Materials Horizons paper; mocks for CNC and potentiostats; electrodeposition and CV parameters.
11. `eda-event-driven`: Nature Methods; BSD; a feedback rule controls the imaging rate, checked by replaying image streams.
12. `evolver-2018`: MIT DPU `custom_script.py`; turbidostat/chemostat logic is checked by replaying OD traces.
13. `chemputer-blueprints`: Nature Communications (CC BY); XDL 2.0 blueprints with chiral syntheses executed.
14. `openflexure-autofocus`: J Microscopy (CC BY); GPL server with mock hardware; tiled scans with autofocus.
15. `slab-scheduling`: SLAS Technology; MIT Julia scheduler; time constraints in the methods text can be checked against makespan.

Next tier (partial): `madsci-ad-sdl`, `chibio-2020` (no licence), `pioreactor` (no first-party paper), `mobile-robots-dai-2024` (Zenodo bundle), `robochem` (paywalled paper), `etsted` (GPL), `openworkstation`.
