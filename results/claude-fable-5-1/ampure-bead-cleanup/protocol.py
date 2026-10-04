from opentrons import protocol_api
from opentrons.protocol_api.labware import OutOfTipsError

metadata = {
    'protocolName': 'AMPure XP 0.8x bead cleanup of PCR products',
    'author': 'OT-2 protocol',
    'description': 'Clean up 50 uL PCR products in a 96-well plate with 0.8x AMPure XP beads, '
                   'two 80% ethanol washes, and elution in 50 uL nuclease-free water.',
    'apiLevel': '2.15',
}

NUM_SAMPLES = 96


def run(protocol: protocol_api.ProtocolContext):
    # ---------------------------------------------------------------- labware
    sample_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 1, label='sample_plate')
    beads_res = protocol.load_labware('nest_1_reservoir_195ml', 2, label='beads_reservoir')
    ethanol_res = protocol.load_labware('nest_1_reservoir_195ml', 3, label='ethanol_reservoir')
    water_res = protocol.load_labware('nest_1_reservoir_195ml', 4, label='water_reservoir')
    waste_res = protocol.load_labware('nest_1_reservoir_195ml', 5, label='waste')
    elution_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 6, label='elution_plate')

    tips20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tips300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)

    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tips20])
    p300 = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tips300])

    beads = beads_res['A1']
    ethanol = ethanol_res['A1']
    water = water_res['A1']
    waste = waste_res['A1']

    samples = sample_plate.wells()[:NUM_SAMPLES]
    eluates = elution_plate.wells()[:NUM_SAMPLES]

    # ---------------------------------------------------------------- helpers
    def pick_up(pip):
        """Pick up a tip; refill the rack (tips are unlimited) if it is empty."""
        try:
            pip.pick_up_tip()
        except OutOfTipsError:
            pip.reset_tipracks()
            pip.pick_up_tip()

    def pipette_for(volume):
        return p20 if volume <= 20 else p300

    # ---------------------------------------------------------------- step 1: add beads
    protocol.comment('Step 1: add 40 uL AMPure XP beads (0.8x) to each sample and mix 10x')
    for well in samples:
        pip = pipette_for(40)
        pick_up(pip)
        pip.aspirate(40, beads)
        pip.dispense(40, well)
        pip.mix(10, 60, well)          # 90 uL in well; mix with 60 uL
        pip.blow_out(well.top())
        pip.drop_tip()

    # ---------------------------------------------------------------- steps 2-3: bind, magnet
    protocol.comment('Step 2: incubate sample_plate 5 min at room temperature (beads bind DNA)')
    protocol.comment('Step 3: engage magnetic module; wait 5 min until solution clears')

    # ---------------------------------------------------------------- step 4: remove supernatant
    protocol.comment('Step 4: remove 90 uL supernatant from each sample to waste')
    for well in samples:
        pip = pipette_for(90)
        pick_up(pip)
        pip.aspirate(90, well.bottom(0.5))
        pip.dispense(90, waste)
        pip.blow_out(waste.top())
        pip.drop_tip()

    # ---------------------------------------------------------------- steps 5-8: two ethanol washes
    for wash in (1, 2):
        protocol.comment('Step {}: add 200 uL 80% ethanol to each sample'.format(5 if wash == 1 else 7))
        pip = pipette_for(200)
        pick_up(pip)                   # one tip: ethanol dispensed from above the beads
        for well in samples:
            pip.aspirate(200, ethanol)
            pip.dispense(200, well.top(-2))
            pip.blow_out(well.top())
        pip.drop_tip()

        protocol.comment('Step {}: remove 200 uL ethanol waste {} from each sample to waste'
                         .format(6 if wash == 1 else 8, wash))
        for well in samples:
            pip = pipette_for(200)
            pick_up(pip)
            pip.aspirate(200, well.bottom(0.5))
            pip.dispense(200, waste)
            pip.blow_out(waste.top())
            pip.drop_tip()

    # ---------------------------------------------------------------- steps 9-10: dry, disengage
    protocol.comment('Step 9: air dry beads 5 min at room temperature (magnet engaged); '
                     'beads should appear matte, not shiny')
    protocol.comment('Step 10: disengage magnetic module')

    # ---------------------------------------------------------------- step 11: elute
    protocol.comment('Step 11: add 50 uL nuclease-free water to each sample and mix 10x to resuspend beads')
    for well in samples:
        pip = pipette_for(50)
        pick_up(pip)
        pip.aspirate(50, water)
        pip.dispense(50, well)
        pip.mix(10, 40, well)          # 50 uL in well; mix with 40 uL
        pip.blow_out(well.top())
        pip.drop_tip()

    # ---------------------------------------------------------------- step 12: incubate, re-engage
    protocol.comment('Step 12: incubate sample_plate 2 min at room temperature; '
                     'then re-engage magnetic module for 5 min')

    # ---------------------------------------------------------------- step 13: transfer eluate
    protocol.comment('Step 13: transfer 45 uL cleaned DNA from each sample to elution_plate')
    for src, dest in zip(samples, eluates):
        pip = pipette_for(45)
        pick_up(pip)
        pip.aspirate(45, src.bottom(0.5))
        pip.dispense(45, dest)
        pip.blow_out(dest.top())
        pip.drop_tip()

    protocol.comment('Cleanup complete: 45 uL eluate per well in elution_plate.')
