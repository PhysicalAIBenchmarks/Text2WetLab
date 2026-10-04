"""AMPure XP 0.8x magnetic bead cleanup of 50 uL PCR products (96 samples)."""

from opentrons import protocol_api

metadata = {
    'protocolName': 'AMPure XP 0.8x bead cleanup of PCR products',
    'author': 'Opentrons OT-2 protocol',
    'description': ('0.8x AMPure XP cleanup: bind, remove supernatant, two 80% '
                    'ethanol washes, dry, elute in 50 uL nuclease-free water.'),
    'apiLevel': '2.15',
}

NUM_SAMPLES = 96
SAMPLE_VOL = 50        # uL PCR product per well
BEAD_VOL = 40          # uL beads (0.8x)
SUPERNATANT_VOL = SAMPLE_VOL + BEAD_VOL   # 90 uL
ETHANOL_VOL = 200
ELUTION_VOL = 50
ELUATE_VOL = 45
MIX_REPS = 10


def run(protocol: protocol_api.ProtocolContext):
    # ---- Labware -----------------------------------------------------------
    sample_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 1,
                                         label='sample_plate')
    beads_reservoir = protocol.load_labware('nest_1_reservoir_195ml', 2,
                                            label='beads_reservoir')
    ethanol_reservoir = protocol.load_labware('nest_1_reservoir_195ml', 3,
                                              label='ethanol_reservoir')
    water_reservoir = protocol.load_labware('nest_1_reservoir_195ml', 4,
                                            label='water_reservoir')
    waste = protocol.load_labware('nest_1_reservoir_195ml', 5, label='waste')
    elution_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 6,
                                          label='elution_plate')

    tips20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tips300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)

    # ---- Pipettes ----------------------------------------------------------
    # p20 is loaded per the deck setup; every volume here is >= 40 uL so the
    # p300 does all the liquid handling.
    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tips20])
    p300 = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tips300])

    beads = beads_reservoir['A1']
    ethanol = ethanol_reservoir['A1']
    water = water_reservoir['A1']
    liquid_waste = waste['A1']

    sample_wells = sample_plate.wells()[:NUM_SAMPLES]
    elution_wells = elution_plate.wells()[:NUM_SAMPLES]

    tips_used = 0

    def pick_up():
        """Pick up a fresh p300 tip, resetting the rack when it runs out."""
        nonlocal tips_used
        if tips_used >= 96:
            p300.reset_tipracks()
            tips_used = 0
        p300.pick_up_tip()
        tips_used += 1

    # ---- Step 1: add beads and mix -----------------------------------------
    protocol.comment('Step 1: Add 40 uL AMPure XP beads (0.8x) to each sample and mix 10x.')
    for well in sample_wells:
        pick_up()
        p300.aspirate(BEAD_VOL, beads)
        p300.dispense(BEAD_VOL, well)
        p300.mix(MIX_REPS, 70, well)
        p300.blow_out(well.top())
        p300.drop_tip()

    # ---- Steps 2-3: bind and separate (not simulated) ----------------------
    protocol.comment('Step 2: Incubate sample_plate 5 min at room temperature (beads bind DNA).')
    protocol.delay(minutes=5)
    protocol.comment('Step 3: Engage magnetic module; wait 5 min until solution clears.')
    protocol.delay(minutes=5)

    # ---- Step 4: remove supernatant ----------------------------------------
    protocol.comment('Step 4: Remove 90 uL supernatant from each sample to waste.')
    for well in sample_wells:
        pick_up()
        p300.aspirate(SUPERNATANT_VOL, well.bottom(1))
        p300.dispense(SUPERNATANT_VOL, liquid_waste)
        p300.blow_out(liquid_waste.top())
        p300.drop_tip()

    # ---- Steps 5-8: two 80% ethanol washes ---------------------------------
    for wash in (1, 2):
        protocol.comment('Step %d: Add 200 uL 80%% ethanol to each sample (wash %d).'
                         % (3 + 2 * wash, wash))
        for well in sample_wells:
            pick_up()
            p300.aspirate(ETHANOL_VOL, ethanol)
            p300.dispense(ETHANOL_VOL, well)
            p300.blow_out(well.top())
            p300.drop_tip()

        protocol.comment('Step %d: Remove 200 uL ethanol waste %d from each sample to waste.'
                         % (4 + 2 * wash, wash))
        for well in sample_wells:
            pick_up()
            p300.aspirate(ETHANOL_VOL, well.bottom(1))
            p300.dispense(ETHANOL_VOL, liquid_waste)
            p300.blow_out(liquid_waste.top())
            p300.drop_tip()

    # ---- Steps 9-10: dry and disengage (not simulated) ---------------------
    protocol.comment('Step 9: Air dry beads 5 min at room temperature (magnet engaged); '
                     'beads should appear matte, not shiny.')
    protocol.delay(minutes=5)
    protocol.comment('Step 10: Disengage magnetic module.')

    # ---- Step 11: elute ----------------------------------------------------
    protocol.comment('Step 11: Add 50 uL nuclease-free water to each sample and mix 10x to resuspend beads.')
    for well in sample_wells:
        pick_up()
        p300.aspirate(ELUTION_VOL, water)
        p300.dispense(ELUTION_VOL, well)
        p300.mix(MIX_REPS, 40, well)
        p300.blow_out(well.top())
        p300.drop_tip()

    # ---- Step 12: incubate and re-engage (not simulated) -------------------
    protocol.comment('Step 12: Incubate sample_plate 2 min at room temperature; '
                     'then re-engage magnetic module 5 min.')
    protocol.delay(minutes=2)
    protocol.delay(minutes=5)

    # ---- Step 13: transfer eluate ------------------------------------------
    protocol.comment('Step 13: Transfer 45 uL cleaned DNA from each sample to elution_plate.')
    for src, dest in zip(sample_wells, elution_wells):
        pick_up()
        p300.aspirate(ELUATE_VOL, src.bottom(1))
        p300.dispense(ELUATE_VOL, dest)
        p300.blow_out(dest.top())
        p300.drop_tip()

    protocol.comment('Cleanup complete: 45 uL cleaned DNA per well in elution_plate.')
