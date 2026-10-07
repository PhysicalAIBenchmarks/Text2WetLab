"""
OT-2 in-house magnetic-bead SARS-CoV-2 RNA extraction (48 samples).

Implements the "OT-2in-house" protocol described in:

    Lázaro-Perona F., et al. "Evaluation of two automated low-cost RNA
    extraction protocols for SARS-CoV-2 detection." PLOS ONE 16(2): e0246302
    (2021). https://doi.org/10.1371/journal.pone.0246302

Protocol steps and volumes (from the paper, Table 1 / "Protocol design"):

    1. Dispense 40 µL magnetic beads + 250 µL isopropanol + 250 µL sample per
       well, mix by pipetting five times, incubate 5 min at room temperature.
    2. Activate the GEN1 magnetic module for 4 min.
    3. Collect the supernatant and discard.
    4. Add 500 µL of 70% ethanol, collect and discard (wash 1).
    5. Add 500 µL of 70% ethanol, collect and discard (wash 2).
    6. Air dry for 4 min (magnet still engaged).
    7. Turn off the magnetic module and add 100 µL elution buffer.
    8. After 30 s, turn on the magnetic module.
    9. After 90 s, collect the supernatant and transfer to a 96-well plate.

The 48 inactivated samples are placed into the odd columns (1, 3, 5, 7, 9, 11)
of the deep-well plate on the magnetic module, one sample per well. Each eluate
is recovered into the matching well of the elution plate held at 4 °C on the
temperature module.
"""

from opentrons import protocol_api

metadata = {
    "protocolName": "OT-2 in-house magnetic-bead RNA extraction (48 samples)",
    "description": (
        "OT-2in-house SARS-CoV-2 RNA extraction per Lázaro-Perona et al. 2021 "
        "(PLOS ONE, doi:10.1371/journal.pone.0246302)."
    ),
    "author": "OT-2",
    "apiLevel": "2.15",
}

# --- Reagent / sample volumes (µL), exactly as in the paper -----------------
BEADS_VOL = 40
ISOPROPANOL_VOL = 250
SAMPLE_VOL = 250
WASH_VOL = 500        # 70% ethanol, both washes
ELUTION_VOL = 100

# --- Timings (paper) --------------------------------------------------------
BIND_INCUBATION_MIN = 5   # step 1
MAGNET_BIND_MIN = 4       # step 2
AIR_DRY_MIN = 4           # step 6
ELUTION_WAIT_SEC = 30     # step 8 (elution buffer before re-engaging magnet)
ELUTION_MAGNET_SEC = 90   # step 9 (re-engaging before collecting eluate)

MIX_REPETITIONS = 5        # "Mix by pipetting five times"
MIX_VOLUME = 250

# Binding reaction total volume to discard in step 3.
BINDING_SUPERNATANT_VOL = BEADS_VOL + ISOPROPANOL_VOL + SAMPLE_VOL  # 540 µL


def run(protocol: protocol_api.ProtocolContext):

    # ------------------------------------------------------------------ labware
    tips_1000 = protocol.load_labware("opentrons_96_filtertiprack_1000ul", 11)
    tips_200_2 = protocol.load_labware("opentrons_96_filtertiprack_200ul", 2)
    tips_200_3 = protocol.load_labware("opentrons_96_filtertiprack_200ul", 3)
    tips_200_9 = protocol.load_labware("opentrons_96_filtertiprack_200ul", 9)

    # Slot 1: waste plate for discarded supernatant and washes.
    waste = protocol.load_labware("usascientific_96_wellplate_2.4ml_deep", 1)

    # Slot 4: GEN1 magnetic module holding the sample/extraction (deep-well) plate.
    mag_mod = protocol.load_module("magnetic module", 4)
    mag_plate = mag_mod.load_labware("usascientific_96_wellplate_2.4ml_deep")

    # Slot 5: reagent reservoir.
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 5)

    # Slot 6: GEN1 temperature module holding the elution plate.
    temp_mod = protocol.load_module("tempdeck", 6)
    elu_plate = temp_mod.load_labware("thermo_96_wellplate_200ul")

    # Slots 10 and 7: inactivated samples in 2 mL tubes (24 per rack).
    rack_samples_1_24 = protocol.load_labware(
        "opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap", 10
    )
    rack_samples_25_48 = protocol.load_labware(
        "opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap", 7
    )
    # Slot 12 is the fixed trash.

    # ------------------------------------------------------------------ pipettes
    p1000 = protocol.load_instrument(
        "p1000_single_gen2", "left", tip_racks=[tips_1000]
    )
    p300 = protocol.load_instrument(
        "p300_multi_gen2", "right", tip_racks=[tips_200_2, tips_200_3, tips_200_9]
    )

    # Gentle flow rates to avoid disturbing the magnetic bead pellets.
    p1000.flow_rate.aspirate = 150
    p1000.flow_rate.dispense = 150
    p300.flow_rate.aspirate = 60
    p300.flow_rate.dispense = 60

    # ------------------------------------------------------------------ reservoir map
    beads_well = reservoir["A2"]                       # col 2: magnetic beads
    elution_buffer = reservoir["A4"]                   # col 4: elution buffer
    iso_wells = [reservoir["A6"], reservoir["A7"]]     # col 6-7: isopropanol
    etoh_wash1 = [reservoir["A9"], reservoir["A10"]]   # col 9-10: 70% ethanol
    etoh_wash2 = [reservoir["A11"], reservoir["A12"]]  # col 11-12: 70% ethanol

    # ------------------------------------------------------------------ sample layout
    odd_columns = [1, 3, 5, 7, 9, 11]

    # 48 samples in order 1..48 (each rack holds 24 tubes, A1..D6).
    source_tubes = list(rack_samples_1_24.wells()) + list(rack_samples_25_48.wells())

    # Sample i -> the matching odd-column well of the magnetic plate (one per well).
    mag_wells = []
    for c in odd_columns:
        mag_wells.extend(mag_plate.columns()[c - 1])

    # Split isopropanol/ethanol across a pair of reservoir columns
    # (12 mL needed per reagent <= 15 mL per column when halved).
    def iso_source(i):
        return iso_wells[0] if i < 24 else iso_wells[1]

    def etoh1_source(i):
        return etoh_wash1[0] if i < 24 else etoh_wash1[1]

    def etoh2_source(i):
        return etoh_wash2[0] if i < 24 else etoh_wash2[1]

    def remove_supernatant(volume, src_col, dst_col):
        """Aspirate `volume` µL from a column of 8 wells and discard to waste.

        Uses the p300 multichannel with one set of tips, in <=190 µL chunks so it
        never exceeds the 200 µL tip capacity. Tips are picked up / dropped by the
        caller.
        """
        remaining = volume
        while remaining > 0:
            vol = min(190, remaining)
            p300.aspirate(vol, src_col[0].bottom(2))
            p300.dispense(vol, dst_col[0].top(-5))
            remaining -= vol

    # ------------------------------------------------------------------ setup
    # Keep the elution plate at 4 °C (blocks until the module reaches target).
    temp_mod.set_temperature(celsius=4)
    mag_mod.disengage()

    # ================= Step 1: reagent mix =====================================
    protocol.comment(
        "Step 1: add 40 µL beads, 250 µL isopropanol and 250 µL sample per well; "
        "mix 5x; incubate 5 min at room temperature."
    )
    # 40 µL magnetic beads — one multichannel tip reused (clean reagent), the
    # beads are resuspended in the reservoir immediately before each pickup.
    p300.pick_up_tip()
    for c in odd_columns:
        p300.mix(3, BEADS_VOL, beads_well)
        p300.aspirate(BEADS_VOL, beads_well)
        p300.dispense(BEADS_VOL, mag_plate.columns()[c - 1][0])
    p300.drop_tip()

    # 250 µL isopropanol — one single-channel tip reused (clean reagent).
    p1000.pick_up_tip()
    for i in range(48):
        p1000.aspirate(ISOPROPANOL_VOL, iso_source(i))
        p1000.dispense(ISOPROPANOL_VOL, mag_wells[i])
    p1000.drop_tip()

    # 250 µL sample + mix five times — fresh tip per sample (avoids carry-over).
    for i in range(48):
        p1000.pick_up_tip()
        p1000.aspirate(SAMPLE_VOL, source_tubes[i])
        p1000.dispense(SAMPLE_VOL, mag_wells[i])
        p1000.mix(MIX_REPETITIONS, MIX_VOLUME, mag_wells[i])
        p1000.drop_tip()

    protocol.delay(minutes=BIND_INCUBATION_MIN)

    # ================= Step 2: engage magnet 4 min ==============================
    protocol.comment("Step 2: activate the GEN1 magnetic module for 4 min.")
    mag_mod.engage()  # uses the deep-well plate's default engage height (14.94 mm)
    protocol.delay(minutes=MAGNET_BIND_MIN)

    # ================= Step 3: discard binding supernatant ======================
    protocol.comment("Step 3: collect and discard the binding supernatant.")
    for k, c in enumerate(odd_columns):
        p300.pick_up_tip()
        remove_supernatant(
            BINDING_SUPERNATANT_VOL, mag_plate.columns()[c - 1], waste.columns()[k]
        )
        p300.drop_tip()

    # ================= Step 4: wash 1 (70% ethanol) =============================
    protocol.comment("Step 4: add 500 µL 70% ethanol, collect and discard.")
    p1000.pick_up_tip()
    for i in range(48):
        p1000.aspirate(WASH_VOL, etoh1_source(i))
        p1000.dispense(WASH_VOL, mag_wells[i])
    p1000.drop_tip()
    for k, c in enumerate(odd_columns):
        p300.pick_up_tip()
        remove_supernatant(WASH_VOL, mag_plate.columns()[c - 1], waste.columns()[k])
        p300.drop_tip()

    # ================= Step 5: wash 2 (70% ethanol) =============================
    protocol.comment("Step 5: add 500 µL 70% ethanol, collect and discard.")
    p1000.pick_up_tip()
    for i in range(48):
        p1000.aspirate(WASH_VOL, etoh2_source(i))
        p1000.dispense(WASH_VOL, mag_wells[i])
    p1000.drop_tip()
    for k, c in enumerate(odd_columns):
        p300.pick_up_tip()
        remove_supernatant(WASH_VOL, mag_plate.columns()[c - 1], waste.columns()[k])
        p300.drop_tip()

    # ================= Step 6: air dry 4 min ====================================
    protocol.comment("Step 6: air dry the beads for 4 min (magnet still engaged).")
    protocol.delay(minutes=AIR_DRY_MIN)

    # ================= Step 7: disengage + add elution buffer ===================
    protocol.comment("Step 7: turn off the magnet and add 100 µL elution buffer.")
    mag_mod.disengage()
    p300.pick_up_tip()
    for c in odd_columns:
        p300.aspirate(ELUTION_VOL, elution_buffer)
        p300.dispense(ELUTION_VOL, mag_plate.columns()[c - 1][0])
    p300.drop_tip()

    # ================= Step 8: wait 30 s, re-engage =============================
    protocol.comment("Step 8: after 30 s turn on the magnetic module.")
    protocol.delay(seconds=ELUTION_WAIT_SEC)
    mag_mod.engage()

    # ================= Step 9: wait 90 s, recover eluate ========================
    protocol.comment(
        "Step 9: after 90 s collect the supernatant and transfer to the 4 °C plate."
    )
    protocol.delay(seconds=ELUTION_MAGNET_SEC)
    for k, c in enumerate(odd_columns):
        src_col = mag_plate.columns()[c - 1]
        dst_col = elu_plate.columns()[c - 1]
        p300.pick_up_tip()
        p300.aspirate(ELUTION_VOL, src_col[0].bottom(1))
        p300.dispense(ELUTION_VOL, dst_col[0])
        p300.blow_out(dst_col[0])
        p300.drop_tip()

    mag_mod.disengage()
    protocol.comment("Extraction complete: 48 eluates on the 4 °C elution plate.")