# Automate a magnetic-bead RNA extraction on an Opentrons OT-2

`/data/paper.txt` is the text of "Automated low-cost SARS-CoV-2 RNA extraction protocols" (PLOS ONE, 2021, doi:10.1371/journal.pone.0246302). Implement its **in-house OT-2 magnetic-bead protocol** for **48 samples** as an Opentrons Python protocol, using the reagent volumes, step order, incubation, magnet and drying times described in the paper.

Write the protocol to **`/app/protocol.py`**.

## Deck (fixed: the operator has loaded the robot like this)

| Slot | Contents | Load name |
|---|---|---|
| 1 | Waste plate for removed supernatant | `usascientific_96_wellplate_2.4ml_deep` |
| 2, 3, 9 | 200 µL filter tips | `opentrons_96_filtertiprack_200ul` |
| 4 | Magnetic Module GEN1 (`'magnetic module'`) holding the sample/extraction plate | `usascientific_96_wellplate_2.4ml_deep` |
| 5 | Reagent reservoir | `nest_12_reservoir_15ml` |
| 6 | Temperature Module GEN1 (`'tempdeck'`) holding the elution plate | `thermo_96_wellplate_200ul` (custom, see below) |
| 10 | Samples 1–24, inactivated, in 2 mL tubes | `opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap` |
| 7 | Samples 25–48, inactivated, in 2 mL tubes | `opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap` |
| 11 | 1000 µL filter tips | `opentrons_96_filtertiprack_1000ul` |
| 12 | Fixed trash | |

Pipettes: `p1000_single_gen2` on the **left** mount, `p300_multi_gen2` on the **right** mount.

Reservoir (slot 5) columns: **2** magnetic beads; **4** elution buffer; **6–7** isopropanol; **9–12** 70% ethanol. Other columns are empty.

Place the 48 samples in the **odd columns (1, 3, 5, 7, 9, 11)** of the magnetic-module plate, one sample per well, and recover each eluate into its own well of the elution plate on the temperature module, which must be kept at 4 °C. Send removed supernatant and washes to the waste plate in slot 1.

## Tools and constraints

- Use OT-2 Python API `apiLevel` between `'2.2'` and `'2.15'`; Opentrons 7.5.0 is installed.
- Simulate with: `opentrons_simulate -L /data/labware /app/protocol.py` (`/data/labware` holds the `thermo_96_wellplate_200ul` definition). Your protocol must simulate without errors.
- No internet access besides the model API; the authors' published code is not available.
- The protocol is graded on what the simulated robot actually does (volumes, order, timing, magnet and tip handling) and by a reviewer comparing it with the paper.
