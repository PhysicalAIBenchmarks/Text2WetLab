"""Magnetic-bead RNA extraction (SARS-CoV-2), in-house OT-2 protocol, 48 samples.

Implements the "OT-2 in-house" magnetic-bead extraction described in
"Evaluation of two automated low-cost RNA extraction protocols for SARS-CoV-2
detection" (La'zaro-Perona et al., PLOS ONE 2021, doi:10.1371/journal.pone.0246302).

Deck layout (operator has loaded the robot as follows):
    1   waste plate  (usascientific_96_wellplate_2.4ml_deep)
    2,3 200 uL filter tips
    4   Magnetic Module GEN1 + sample/extraction deep-well plate
    5   12-column reagent reservoir (beads, isopropanol, ethanol, elution)
    6   Temperature Module GEN1 + elution plate (thermo_96_wellplate_200ul)
    7   samples 25-48 (2 mL tubes)
    9   200 uL filter tips
    10  samples 1-24  (2 mL tubes)
    11  1000 uL filter tips
    12  fixed trash
"""

from opentrons import protocol_api

metadata = {
    "protocolName": "Mag-bead RNA extraction (OT-2 in-house, 48 samples)",
    "apiLevel": "2.15",
}

NUM_SAMPLES = 48
# Samples occupy the odd columns of the magnetic-module plate, one per well.
ODD_COLUMNS = [1, 3, 5, 7, 9, 11]

ENGAGE_HEIGHT = 7  # mm above well bottom for the GEN1 magnetic module


def run(protocol: protocol_api.ProtocolContext):
    # ---------------------------------------------------------------- deck ----
    waste_plate = protocol.load_labware(
        "usascientific_96_wellplate_2.4ml_deep", "1"
    )
    tips_200_a = protocol.load_labware("opentrons_96_filtertiprack_200ul", "2")
    tips_200_b = protocol.load_labware("opentrons_96_filtertiprack_200ul", "3")
    tips_200_c = protocol.load_labware("opentrons_96_filtertiprack_200ul", "9")

    mag_module = protocol.load_module("magnetic module", "4")
    mag_plate = mag_module.load_labware("usascientific_96_wellplate_2.4ml_deep")

    reservoir = protocol.load_labware("nest_12_reservoir_15ml", "5")

    temp_module = protocol.load_module("tempdeck", "6")
    elution_plate = temp_module.load_labware("thermo_96_wellplate_200ul")

    tubes_7 = protocol.load_labware(
        "opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap", "7"
    )
    tubes_10 = protocol.load_labware(
        "opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap", "10"
    )

    tips_1000 = protocol.load_labware("opentrons_96_filtertiprack_1000ul", "11")
    # Slot 12 is the fixed trash; nothing is loaded there.

    # ------------------------------------------------------------ pipettes ----
    p1000 = protocol.load_instrument(
        "p1000_single_gen2", "left", tip_racks=[tips_1000]
    )
    p300 = protocol.load_instrument(
        "p300_multi_gen2", "right", tip_racks=[tips_200_a, tips_200_b, tips_200_c]
    )

    # --------------------------------------------------- reagent reservoir ----
    beads = reservoir["A2"]
    elution_buffer = reservoir["A4"]
    isopropanol_6 = reservoir["A6"]
    isopropanol_7 = reservoir["A7"]
    ethanol = [reservoir["A9"], reservoir["A10"], reservoir["A11"], reservoir["A12"]]

    # ------------------------------------------- sample & destination wells ----
    # The multi-channel pipette addresses whole columns; anchor each target
    # column with its top well (A of that column).
    sample_anchors = [mag_plate.columns_by_name()[str(c)][0] for c in ODD_COLUMNS]
    waste_anchors = [waste_plate.columns_by_name()[str(c)][0] for c in ODD_COLUMNS]
    elution_anchors = [
        elution_plate.columns_by_name()[str(c)][0] for c in ODD_COLUMNS
    ]
    # Individual wells, in order, for the single-channel 1000 uL pipette.
    sample_columns = [mag_plate.columns_by_name()[str(c)] for c in ODD_COLUMNS]
    sample_wells = [w for col in sample_columns for w in col]  # 48 wells
    # Samples 1-24 live in slot 10; samples 25-48 live in slot 7.
    source_wells = list(tubes_10.wells()) + list(tubes_7.wells())  # 48 tubes

    # ------------------------------------- startup: disengage magnet + chill ---
    mag_module.disengage()
    # Keep the elution plate at 4 °C before any eluate reaches it.
    temp_module.set_temperature(4)

    # ------------------------------------------------------------- binding ----

    # 2. Add 40 uL magnetic beads (reservoir column 2) to every sample well.
    protocol.comment("2. 40 uL magnetic beads")
    p300.pick_up_tip()
    for anchor in sample_anchors:
        p300.transfer(40, beads, anchor, new_tip="never")
    p300.drop_tip()

    # 3. Add 250 uL isopropanol (reservoir columns 6-7) to every sample well.
    protocol.comment("3. 250 uL isopropanol")
    p300.pick_up_tip()
    for i, anchor in enumerate(sample_anchors):
        source = isopropanol_6 if i < 3 else isopropanol_7
        p300.transfer(250, source, anchor, new_tip="never")
    p300.drop_tip()

    # 4. Add 250 uL of each sample, fresh tip per sample, mix 5 times.
    protocol.comment("4. 250 uL sample (fresh tip per sample, mix 5x)")
    for source, dest in zip(source_wells, sample_wells):
        p1000.pick_up_tip()
        p1000.aspirate(250, source)
        p1000.dispense(250, dest)
        p1000.mix(5, 250, dest)
        p1000.drop_tip()

    # 5. Incubate 5 min at room temperature.
    protocol.comment("5. Incubate 5 min at room temperature")
    protocol.delay(minutes=5)

    # 6. Engage the magnet and wait 4 min.
    protocol.comment("6. Engage magnet, wait 4 min")
    mag_module.engage(height_from_base=ENGAGE_HEIGHT)
    protocol.delay(minutes=4)

    # 7. Remove ~540 uL supernatant (40 + 250 + 250) to the waste plate.
    protocol.comment("7. Remove ~540 uL supernatant to waste")
    for anchor, waste_anchor in zip(sample_anchors, waste_anchors):
        p300.pick_up_tip()
        for _ in range(2):  # 2 x 270 uL = 540 uL
            p300.transfer(270, anchor, waste_anchor, new_tip="never")
        p300.drop_tip()

    # 8. Wash 1: add 500 uL 70% ethanol, then remove to waste (magnet engaged).
    protocol.comment("8. Wash 1: 500 uL 70% ethanol in, then out")
    p300.pick_up_tip()
    for i, anchor in enumerate(sample_anchors):
        source = ethanol[i % len(ethanol)]
        for _ in range(2):  # 2 x 250 uL = 500 uL
            p300.transfer(250, source, anchor, new_tip="never")
    p300.drop_tip()

    for anchor, waste_anchor in zip(sample_anchors, waste_anchors):
        p300.pick_up_tip()
        for _ in range(2):  # remove 500 uL
            p300.transfer(250, anchor, waste_anchor, new_tip="never")
        p300.drop_tip()

    # 9. Wash 2: add 500 uL 70% ethanol, then remove to waste (magnet engaged).
    protocol.comment("9. Wash 2: 500 uL 70% ethanol in, then out")
    p300.pick_up_tip()
    for i, anchor in enumerate(sample_anchors):
        source = ethanol[i % len(ethanol)]
        for _ in range(2):  # 2 x 250 uL = 500 uL
            p300.transfer(250, source, anchor, new_tip="never")
    p300.drop_tip()

    for anchor, waste_anchor in zip(sample_anchors, waste_anchors):
        p300.pick_up_tip()
        for _ in range(2):  # remove 500 uL
            p300.transfer(250, anchor, waste_anchor, new_tip="never")
        p300.drop_tip()

    # 10. Air-dry the beads 4 min with the magnet engaged.
    protocol.comment("10. Air-dry 4 min (magnet engaged)")
    protocol.delay(minutes=4)

    # ------------------------------------------------------------ elution -----

    # 11. Disengage and add 100 uL elution buffer; mix to resuspend.
    protocol.comment("11. Disengage, add 100 uL elution buffer, resuspend")
    mag_module.disengage()

    p300.pick_up_tip()
    for anchor in sample_anchors:
        p300.transfer(100, elution_buffer, anchor, new_tip="never")
    p300.drop_tip()

    for anchor in sample_anchors:  # resuspend: fresh tip per column
        p300.pick_up_tip()
        p300.mix(10, 80, anchor)
        p300.drop_tip()

    # 12. Wait 30 s, engage the magnet, wait 90 s.
    protocol.comment("12. Wait 30 s, engage magnet, wait 90 s")
    protocol.delay(seconds=30)
    mag_module.engage(height_from_base=ENGAGE_HEIGHT)
    protocol.delay(minutes=1, seconds=30)

    # 13. Transfer 80 uL eluate to the 4 °C elution plate (own well each).
    protocol.comment("13. Transfer 80 uL eluate to elution plate (4 °C)")
    for anchor, elution_anchor in zip(sample_anchors, elution_anchors):
        p300.pick_up_tip()
        p300.transfer(80, anchor, elution_anchor, new_tip="never")
        p300.drop_tip()

    # 14. Disengage the magnet at the end of the run.
    protocol.comment("14. Disengage magnet (end of run)")
    mag_module.disengage()