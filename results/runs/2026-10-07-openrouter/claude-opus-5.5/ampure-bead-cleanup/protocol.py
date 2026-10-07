from opentrons import protocol_api

metadata = {
    'protocolName': 'AMPure XP 0.8x bead cleanup of PCR products',
    'description': '0.8x AMPure XP cleanup of 50 uL PCR products, two 80% ethanol '
                   'washes, elution in 50 uL nuclease-free water.',
    'apiLevel': '2.15',
}


def run(protocol: protocol_api.ProtocolContext):
    sample_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 1, label='sample_plate')
    beads_reservoir = protocol.load_labware('nest_1_reservoir_195ml', 2, label='beads_reservoir')
    ethanol_reservoir = protocol.load_labware('nest_1_reservoir_195ml', 3, label='ethanol_reservoir')
    water_reservoir = protocol.load_labware('nest_1_reservoir_195ml', 4, label='water_reservoir')
    waste = protocol.load_labware('nest_1_reservoir_195ml', 5, label='waste')
    elution_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 6, label='elution_plate')

    tips20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tips300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)
    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tips20])
    p300 = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tips300])

    tip_counts = {p20: 0, p300: 0}

    def pick_up(pip):
        if tip_counts[pip] >= 96:
            pip.reset_tipracks()
            tip_counts[pip] = 0
        pip.pick_up_tip()
        tip_counts[pip] += 1

    def pipette_for(volume):
        return p20 if volume <= 20 else p300

    def move(volume, source, dest, mix_reps=0, mix_vol=0):
        """Move volume from source to dest with a fresh tip, optionally mixing after."""
        pip = pipette_for(volume)
        pick_up(pip)
        pip.aspirate(volume, source)
        pip.dispense(volume, dest)
        if mix_reps:
            pip.mix(mix_reps, mix_vol, dest)
        pip.drop_tip()

    samples = sample_plate.wells()  # A1..H12, column order
    eluates = elution_plate.wells()
    beads = beads_reservoir['A1']
    ethanol = ethanol_reservoir['A1']
    water = water_reservoir['A1']
    waste_well = waste['A1']

    # 1. Add 40 uL beads (0.8x) to each sample and mix
    for well in samples:
        move(40, beads, well, mix_reps=10, mix_vol=40)

    # 2-3.
    protocol.comment('Incubate sample_plate 5 min at room temperature (beads bind DNA)')
    protocol.comment('Engage magnetic module; wait 5 min until solution clears')

    # 4. Remove 90 uL supernatant to waste
    for well in samples:
        move(90, well, waste_well)

    # 5-8. Two 80% ethanol washes
    for wash in (1, 2):
        for well in samples:
            move(200, ethanol, well)
        for well in samples:
            move(200, well, waste_well)

    # 9-10.
    protocol.comment('Air dry beads 5 min at room temperature (magnet engaged); '
                     'beads should appear matte not shiny')
    protocol.comment('Disengage magnetic module')

    # 11. Elute in 50 uL nuclease-free water and mix
    for well in samples:
        move(50, water, well, mix_reps=10, mix_vol=40)

    # 12.
    protocol.comment('Incubate sample_plate 2 min at room temperature; '
                     'then re-engage magnetic module 5 min')

    # 13. Transfer 45 uL cleaned DNA to the elution plate
    for src, dst in zip(samples, eluates):
        move(45, src, dst)
