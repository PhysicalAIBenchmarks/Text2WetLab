# PLR-Supported Peripheral Instruments: Paper+Code Pairs

**Scope:** Incubators, shakers, centrifuges, balances, tube handlers, electroporators, and
miscellaneous instruments supported by PyLabRobot (PLR). For each, a peer-reviewed or preprint
paper using that instrument in automated biology, paired with a public GitHub codebase.

**Research method:** PLR source tree (github.com/PyLabRobot/pylabrobot) was surveyed to enumerate
all supported non-liquid-handler peripherals (via `pylabrobot/legacy/storage/`, `centrifuge/`,
`shaking/`, `heating_shaking/`, `scales/`, `micronic/`, `thermo_fisher/btx/`, etc.). PR history
was used to identify contributing labs and date of addition. External literature was searched for
peer-reviewed or preprint papers that (a) describe real biology and (b) provide GitHub experiment
code for each instrument.

**Key finding:** Most PLR peripheral drivers were added in 2025–2026 and public paper+code pairs
are very sparse. The core framework paper (Wierenga et al. 2023) is the primary reference; most
peripherals exist in the repo but have not yet appeared in a published closed-loop biology paper
that cites PLR for peripheral control.

---

## 1. Thermo Scientific Cytomat 2 / 10 (hotel incubator)

**PLR support:** Full — models C6000, C6002, C2C_425, C2C_450_SHAKE, C5C; also the legacy Heraeus
Cytomat variant. Located at `pylabrobot/legacy/storage/cytomat/`.

**PLR history:** Original PR #332 (jkhales); extensive fixes by ben-ray (PRs #340–#510); tutorial
PR #575 (rickwierenga). Added ~2024.

**Paper:** No public paper+code pair found that specifically uses PLR's Cytomat backend in a
reported biology experiment.

**Closest existing reference:**
- The PLR framework paper (Wierenga et al. 2023, *Device*) describes the Cytomat integration as
  a supported accessory but demonstrates it in a system context, not as the focus of a biology
  experiment.
  - URL: https://www.cell.com/device/fulltext/S2666-9986(23)00170-9
  - DOI: 10.1016/j.device.2023.100111
  - Code: https://github.com/PyLabRobot/pylabrobot

**Notes:** Cytomat incubators appear in many commercial high-throughput screening setups but PLR's
driver is used internally at contributing labs whose biology results have not yet appeared in
print. No public paper+code pair meeting both criteria exists as of the search date (October 2026).

---

## 2. Liconic STX Series (incubator/stacker)

**PLR support:** Mostly — STX series (STX44, STX110, STX220, STX280, STX500, STX1000).
Located at `pylabrobot/legacy/storage/liconic/`.

**PLR history:** PR #846 (sam-adaptyv / Adaptyv Bio, March 2026). PR #1223 adds gRPC service.

**Paper+Code pair (indirect — uses own AROS framework, not PLR's Liconic backend):**

```
Machine: Liconic STX (series unspecified, used within pharmbio AROS system)
Paper: "Integrating Cell Painting and Thermal Proteome Profiling for Improved
        Inference of Mechanism of Action"
  Authors: Johansson C, Johansson M, Carreras Puigvert J, Spjuth O, Jansson ET
  Year: 2025
  URL: https://www.biorxiv.org/content/10.1101/2025.05.30.657006v1.full
  DOI: 10.1101/2025.05.30.657006
Code:
  Hardware control: https://github.com/pharmbio/aros
  Instrument drivers: https://github.com/pharmbio/robotlab
  Paper analysis scripts: https://github.com/camilla-johansson/integrate-cp-tpp
  Description: The AROS robotic system (pharmbio, Uppsala University) moves plates
  between a Liconic incubator, plate hotel, BioTek washer/dispenser, and ImageXpress
  microscope using a UR10 robotic arm. Scripts automate a full Cell Painting +
  Thermal Proteome Profiling workflow on 384-well plates (U2OS cells, 5,300 compounds).
Notes: IMPORTANT CAVEAT — pharmbio/aros is pharmbio's own Python control system
  (predates PLR's Liconic backend). This is NOT using PLR's LiconicBackend. The
  paper-specific code (integrate-cp-tpp) contains only analysis scripts, not hardware
  control code. The hardware control lives in pharmbio/robotlab.
```

**Additional Liconic platform (no paper yet):**

```
Code: https://github.com/AD-SDL/BIO_workcell
  (Argonne National Laboratory Biology Building)
  Instruments: Liconic StoreX STX88, Hudson PlateCrane EX, Hudson SOLO liquid handler,
  Hidex Sense plate reader, Azenta a4S sealer/XPeel desealer
  Automation framework: ROS2 / WEI (Workflow Execution Interface)
  Biology: Not specified in public documentation
  Paper: None found
```

---

## 3. HighRes Biosolutions (plate hotel / mover / centrifuge)

**PLR support:**
- MicroSpin centrifuge: Mostly (TCP ASCII protocol over port 1000)
- SteriStore: Full
- AmbiStore: WIP
- TundraStore: WIP
- LidValet delidder: Mostly

**PLR history:**
- MicroSpin: PR #1047 (c-reiter / Claudio at Lance, TUM, unreleased changelog)
- SteriStore/TundraStore: PR #1090 (rickwierenga)
- LidValet: PR #1188 (rickwierenga)

**Paper:** No public paper+code pair found that uses PLR's HighRes backend in a biology experiment.

**Notes:** The MicroSpin centrifuge has a hello-world notebook
(`docs/user_guide/01_material-handling/centrifuge/highres_microspin.ipynb`) and a mock server for
testing (`pylabrobot/centrifuge/highres/mock_server.py`). The driver was reverse-engineered from
the MicroSpin User Manual (HighRes doc 1058675 Rev C). No paper has been published yet.

---

## 4. Inheco TEC Control / CPAC Ultra Flat (heating/cooling)

**PLR support:**
- CPAC Ultra Flat: Full — `pylabrobot/inheco/cpac.py`
- Inheco ThermoShake (shaker + heater/cooler): WIP — `pylabrobot/inheco/thermoshake.py`
- Inheco Incubator Shaker (MTP/DWP): Mostly — `pylabrobot/legacy/storage/inheco/`
- ODTC (on-deck thermal cycler): Mostly — `pylabrobot/inheco/`
- SCILA (SiLA-2 incubator): Mostly — `pylabrobot/inheco/scila/`

**PLR history:**
- CPAC + TEC Control Box: PR #684 (rickwierenga)
- Incubator Shaker: PR #765 (BioCam, November 2025); Inheco Incubator Shaker control via
  DIP-switch-addressed RS-232 with up to 16 daisy-chained units
- ODTC: PR #841 (ben-ray), refined PR #894 (cmoscy)
- SCILA: PR #795 (rickwierenga) + PR #884 (BioCam)

**Paper:** No public paper+code pair found that uses PLR's Inheco backend in a published biology
experiment.

**Closest existing reference:**
- Wierenga et al. 2023 (*Device*) lists Inheco ThermoShake as a supported heater-shaker;
  hello-world notebooks exist for all Inheco models.
  - URL: https://www.cell.com/device/fulltext/S2666-9986(23)00170-9
  - DOI: 10.1016/j.device.2023.100111
  - Code: https://github.com/PyLabRobot/pylabrobot

**Notes:** The Inheco CPAC is widely used on Hamilton STAR decks for precise temperature control
during liquid handling. The PLR driver abstracts an Inheco TEC Control Box that can address up to
~16 CPAC/ThermoShake units by index. No published experiment code has been found.

---

## 5. Azenta (formerly Brooks / BioCision) plate sealer / desealer

**PLR support:**
- Azenta a4S plate heat sealer: Full — `pylabrobot/azenta/a4s.py`
- Azenta XPeel plate desealer: Full — `pylabrobot/azenta/xpeel.py`
- Azenta FluidX IntelliXcap 96 (tube decapper): Mostly — `pylabrobot/azenta/fluidx/`

**PLR history:**
- a4S: contributed by BioCam (PR #62 area); hello-world available
- XPeel: contributed by rickwierenga; hello-world available
- FluidX decapper: PR #1175 (rickwierenga), error-code extension PR #1187

**Paper+Code pair (indirect — used within AD-SDL BIO_workcell, no biology paper yet):**
```
Code: https://github.com/AD-SDL/BIO_workcell
  Instruments: Azenta a4S sealer + XPeel desealer used alongside Liconic STX88 and
  Hudson SOLO liquid handler at Argonne National Lab
  Paper: None published
```

**Notes:** The Azenta a4S/XPeel pair is frequently deployed in integrated systems for plate sealing
between incubation steps. No standalone paper+code pair for PLR's Azenta backend was found.

---

## 6. Big Bear Automation orbital shaker

**PLR support:** WIP — `pylabrobot/big_bear/orbital_shaker.py`

**PLR history:** PR #1174 (rickwierenga). Serial protocol (9600 baud, `\r` terminator). Daisy-
chain of up to 16 nests, each addressed by hex digit. **Explicitly not hardware-verified**;
setup() emits a warning.

**Paper:** No public paper+code pair found. Device not hardware-verified in PLR.

**Notes:** BigBear orbital shakers are used in DNA assembly and protein expression workflows
but no published experiment using PLR's BigBear driver has been found.

---

## 7. QInstruments BioShake / Heidolph plate shaker

**PLR support:** Full — `pylabrobot/qinstruments/bioshake.py`
Models tested: BioShake 3000-T elm, BioShake 5000 elm, BioShake D-30 T elm, BioShake Q1

**PLR history:** PR #711 (Nat-is-coding); documentation PR #752; BioShake Q1 fix PR #1302 (4ghan1m).

**Paper:** No public paper+code pair found that uses PLR's BioShake backend in a published biology
experiment.

**Closest existing reference:**
- Wierenga et al. 2023 (*Device*) lists BioShake as a supported heater-shaker.
  - URL: https://www.cell.com/device/fulltext/S2666-9986(23)00170-9
  - DOI: 10.1016/j.device.2023.100111
  - Code: https://github.com/PyLabRobot/pylabrobot

**Notes:** QInstruments BioShake devices (sold under Heidolph and QInstruments brands) are
widely used in automated liquid handling protocols for incubation with mixing. No external
published paper using PLR's driver was found.

---

## 8. Sartorius / Mettler Toledo balance

**PLR support:**
- Mettler Toledo MT-SICS scales: WIP — `pylabrobot/mettler_toledo/scales/`
  (driver with I0 command discovery, protocol simulator, and tests — PR #979 by BioCam)
- Sartorius Entris II: WIP — `pylabrobot/sartorius/entris.py` (PR #1168 rickwierenga, not
  hardware-verified)

**Paper+Code pair (using PLR's scale backend, demonstrated in the PLR paper):**

```
Machine: Mettler Toledo balance (model WXS205SDU demonstrated in PLR paper)
Paper: "PyLabRobot: An Open-Source, Hardware-Agnostic Interface for Liquid-Handling
        Robots and Accessories"
  Authors: Wierenga RP, Golas SM, Ho W, Coley CW, Esvelt KM
  Year: 2023
  URL: https://www.cell.com/device/fulltext/S2666-9986(23)00170-9
  DOI: 10.1016/j.device.2023.100111
Code: https://github.com/PyLabRobot/pylabrobot
  Description: PLR uses a Mettler Toledo scale for gravimetric calibration (Figure 3 of
  paper). The scale reads dispensed liquid masses to validate pipetting accuracy on a
  Hamilton STAR. Hello-world notebook at:
  docs/user_guide/mettler_toledo/scales/hello-world.ipynb
Notes: Scale is used as a calibration peripheral, not the focus of a biology experiment.
  The paper is the primary reference for all PLR peripherals. Scale support is "WIP"
  (not fully hardware-verified for all models).
```

---

## 9. Micronic RD235 tube handler / rack reader

**PLR support:** Full — `pylabrobot/micronic/code_reader/`

**PLR history:** PR #936 and PR #1009 (alexjamesgodfrey, Sutter Hill Ventures / Integrated
Biosciences). Direct TWAIN (Windows) or SANE (Linux) image acquisition + local Data Matrix
decoding + serial RS-232 rack barcode read. Live smoke-tested on Micronic hardware with an
8×12 rack.

**Paper:** No public paper+code pair found that uses PLR's Micronic backend in a published biology
experiment.

**Notes:** Micronic provides barcoded 1D/2D tube racks for sample storage. The PLR driver reads
tube barcodes by acquiring an image of the rack and decoding Data Matrix codes locally, bypassing
Micronic's proprietary IO Monitor software. The contributor (alexjamesgodfrey) is at Sutter Hill
Ventures / Integrated Biosciences but no biology paper with this driver has appeared.

---

## 10. Agilent BenchCel 4R (plate hotel / stacker)

**PLR support:** Mostly — `pylabrobot/agilent/benchcel/`

**PLR history:** PR #1109 (c-reiter, Lance / TUM) — v0 implementation; PR #1143 (c-reiter) — v1
`BenchCel4R` device on `Stacker` capability. Binary TCP/7612 protocol reverse-engineered.
Includes in-process mock server.

**Paper:** No public paper+code pair found that uses PLR's BenchCel backend in a published biology
experiment.

**Notes:** The Agilent BenchCel 4R is a plate stacker/hotel used in high-throughput screening
setups alongside VSpin centrifuges and liquid handlers. No published experiment using PLR's
BenchCel driver was found.

---

## 11. Agilent VSpin centrifuge (+ Access2 plate loader)

**PLR support:** Full — `pylabrobot/agilent/vspin/`

**PLR history:**
- Initial VSpin wrapper PR #243 (Ph1so, CMU Robotics)
- Access2 Loader PR #293, #308 (rickwierenga)
- Calibration PR #731; comprehensive upgrade PR #1227 (rickwierenga, from vspin-cockpit)
- VSpin Access2 Loader upgrade PR #1227, protocol improvements PR #1140/1141

**Paper:** No public paper+code pair in a published biology experiment. 

**Closest existing reference:**
- `vspin-cockpit` — Reed Kelso's standalone control app for VSpin + Access2 (URDF 3D twin,
  sim + real hardware). No associated paper.
  - URL: https://github.com/kelsorj/vspin-cockpit
  - Description: Standalone HTML control app with live 3D twin; protocol driver logic was
    ported to PLR PR #1227.

**PLR reference:**
- Wierenga et al. 2023 (*Device*) — lists VSpin as a supported centrifuge.
  - URL: https://www.cell.com/device/fulltext/S2666-9986(23)00170-9
  - DOI: 10.1016/j.device.2023.100111
  - Code: https://github.com/PyLabRobot/pylabrobot

**Notes:** Agilent VSpin is a 2-bucket microplate centrifuge. PLR's Full-support driver was
developed from reverse-engineering and contributions by Reed Kelso. No biology paper using PLR's
VSpin backend has appeared.

---

## 12. BTX Gemini X2 (electroporation)

**PLR support:** Mostly — `pylabrobot/thermo_fisher/btx/gemini/X2/`

**PLR history:** PR #1063 (hazlamshamin / Hazlam Shamin, September 2025). Validated on physical
BTX Gemini X2 with HT-200 plate handler (firmware 4.0.4). Includes GhostTouch RSI touchscreen
OCR control, Protocol Manager file transfer, and HT-200 plate handler integration.

**Relevant paper (BTX Gemini X2 used as comparison instrument, NOT primary automation):**

```
Machine: BTX Gemini X2 (used for parameter screening / comparison only)
Paper: "Active learning guides automated discovery of DNA delivery via electroporation
        for non-model microbes"
  Authors: Crits-Christoph A et al. (Cultivarium, Watertown MA)
  Year: 2025
  URL: https://www.biorxiv.org/content/10.1101/2025.11.18.689155v1.full
  DOI: 10.1101/2025.11.18.689155
Code: https://github.com/cultivarium/electroporation-bayesian-optimization
  Description: Bayesian optimization algorithm (Optuna-based) for selecting 96-well
  electroporation parameters (voltage, resistance, capacitance, buffer, waveform) from
  a 364-million-parameter space. Platform uses CyBio FeliX / Opentrons Flex + custom-
  built fully-programmable electroporator (NOT BTX Gemini X2). Applied to C. necator —
  8.6-fold improvement over prior art in 3 iterations of 176 conditions each.
Notes: IMPORTANT CAVEAT — The BTX Gemini X2 is cited only as a commercial comparison
  point. The actual automated platform uses a custom-built electroporator that allows
  computer-controlled cycling through waveform/voltage/resistance combinations without
  manual intervention (a limitation of the commercial BTX device). PLR's BTX Gemini X2
  driver was not used in this experiment. This is the only electroporation paper with
  public code, but it does not use PLR's BTX driver.
```

**Notes on PLR's BTX Gemini X2 driver:** The PLR driver (PR #1063) automates the touchscreen
workflow via OCR (Tesseract), manages Protocol Manager file transfer, and integrates with the
HT-200 plate handler. A biology paper using PLR's BTX Gemini X2 driver has not yet appeared.

---

## 13. Brooks PreciseFlex robotic arm (plate mover)

**PLR support:** Full — `pylabrobot/brooks/precise_flex/`

**PLR history:**
- Initial driver PR #619 (miikee / BioCam)
- Comprehensive multi-PR refactor (PRs #1073, #1098–#1108, #1117–#1118) by BioCam
- Full kinematic/URDF model, gripper, E-stop handling, crash recovery

**Paper:** No public paper+code pair in a published biology experiment.

**Notes:** The Brooks PreciseFlex (PF400/PF3400) is a 4-axis SCARA robotic arm used as a plate
mover in integrated systems (alongside Liconic, VSpin, BenchCel, etc.). The extensive BioCam
contributions suggest internal use at BioCam but no published biology paper has appeared.

---

## 14. Cole Parmer GenoGrinder (plate shaker)

**PLR support:** WIP — `pylabrobot/cole_parmer/` (GenoGrinder listed in devices.json)

**PLR history:** PR #1192 (rickwierenga). Note: GenoGrinder is a high-speed reciprocating shaker,
not a standard plate shaker. Not hardware-verified.

**Paper:** No public paper+code pair found.

---

## 15. Hettich centrifuges (ROTANTA 460 Robotic / SBS 300 R)

**PLR support:** WIP (listed in devices.json, not yet merged/implemented as of October 2026)

**Paper:** No paper+code pair found.

---

## Summary Table

| Instrument | PLR Support | Paper+Code Pair | Notes |
|---|---|---|---|
| Thermo Cytomat 2/10 | Full | None found | Driver exists, no published experiment |
| Liconic STX series | Mostly | Partial (pharmbio AROS, not PLR backend) | Best: doi:10.1101/2025.05.30.657006 |
| HighRes MicroSpin centrifuge | Mostly | None found | Mock server available; no paper |
| HighRes AmbiStore/SteriStore/TundraStore | WIP/Full | None found | |
| HighRes LidValet | Mostly | None found | |
| Inheco CPAC Ultra Flat | Full | PLR paper only | doi:10.1016/j.device.2023.100111 |
| Inheco ThermoShake | WIP | PLR paper only | |
| Inheco Incubator Shaker | Mostly | None found | Added Nov 2025 by BioCam |
| Inheco ODTC/SCILA | Mostly | None found | |
| Azenta a4S sealer | Full | None found | Used in AD-SDL BIO_workcell (no paper) |
| Azenta XPeel desealer | Full | None found | |
| Azenta FluidX IntelliXcap 96 | Mostly | None found | |
| Big Bear orbital shaker | WIP | None found | Not hardware-verified |
| QInstruments BioShake | Full | None found | |
| Sartorius Entris II | WIP | None found | Not hardware-verified |
| Mettler Toledo scales | WIP | PLR paper (gravimetric calibration) | doi:10.1016/j.device.2023.100111 |
| Micronic RD235 tube reader | Full | None found | Live-tested; no biology paper |
| Agilent BenchCel 4R | Mostly | None found | Mock server available |
| Agilent VSpin centrifuge | Full | None found | vspin-cockpit code only, no paper |
| BTX Gemini X2 | Mostly | Indirect (Cultivarium uses custom electroporator) | doi:10.1101/2025.11.18.689155 |
| Brooks PreciseFlex | Full | None found | Extensive BioCam driver, no paper |
| Cole Parmer GenoGrinder | WIP | None found | |
| Hettich ROTANTA/SBS 300 R | WIP | None found | Listed in devices.json only |

---

## Notes on Search Methodology

1. **PLR source tree surveyed** at github.com/PyLabRobot/pylabrobot (main branch, October 2026)
   via GitHub API. Peripheral modules found in: `pylabrobot/legacy/storage/`,
   `pylabrobot/legacy/centrifuge/`, `pylabrobot/legacy/shaking/`, `pylabrobot/legacy/heating_shaking/`,
   `pylabrobot/inheco/`, `pylabrobot/qinstruments/`, `pylabrobot/big_bear/`,
   `pylabrobot/sartorius/`, `pylabrobot/mettler_toledo/`, `pylabrobot/micronic/`,
   `pylabrobot/agilent/`, `pylabrobot/thermo_fisher/btx/`, `pylabrobot/brooks/`,
   `pylabrobot/azenta/`.

2. **PR history** searched to identify contributors and affiliations.

3. **Literature search** via Google Scholar, bioRxiv, PubMed for each instrument + "python github
   automated biology". Web search budget (200 queries) used.

4. **GitHub search** for repos citing or using each driver.

5. **Finding:** Most PLR peripheral drivers were merged in 2025–2026. Published biology papers
   using PLR-specific peripheral backends have not yet appeared in preprint or journal form,
   with the single exception of the PLR framework paper itself demonstrating scales.

6. **Most promising future candidates** (where PLR is being actively used in labs):
   - Adaptyv Bio (sam-adaptyv) — contributed Liconic backend, runs an automated protein
     engineering platform; papers expected
   - BioCam (BioCam GitHub) — contributed Inheco Incubator Shaker, LidValet, PreciseFlex,
     Mettler Toledo; PhD thesis code at github.com/BioCam/PhD_thesis_cm967
   - Lance / c-reiter (TUM) — contributed MicroSpin centrifuge, BenchCel; running automated
     biology at TUM

---

## Key References

- **PLR framework paper (primary reference for all PLR-controlled peripherals):**
  Wierenga RP, Golas SM, Ho W, Coley CW, Esvelt KM (2023).
  "PyLabRobot: An open-source, hardware-agnostic interface for liquid-handling robots
  and accessories." *Device* 1(4): 100111.
  DOI: 10.1016/j.device.2023.100111
  Code: https://github.com/PyLabRobot/pylabrobot

- **AROS system with Liconic incubator (pharmbio):**
  Johansson C et al. (2025). "Integrating Cell Painting and Thermal Proteome Profiling
  for Improved Inference of Mechanism of Action." *bioRxiv* 2025.05.30.657006.
  DOI: 10.1101/2025.05.30.657006
  Code: https://github.com/pharmbio/aros (hardware), https://github.com/pharmbio/robotlab

- **Cultivarium electroporation paper (BTX Gemini X2 as comparison instrument):**
  Crits-Christoph A et al. (2025). "Active learning guides automated discovery of DNA
  delivery via electroporation for non-model microbes." *bioRxiv* 2025.11.18.689155.
  DOI: 10.1101/2025.11.18.689155
  Code: https://github.com/cultivarium/electroporation-bayesian-optimization
