from opentrons import protocol_api

metadata = {
    'protocolName': 'AMPure XP 0.8x bead cleanup of PCR products',
    'description': '0.8x AMPure XP cleanup of 50 uL PCR products, 2x 80% ethanol wash, elution in 50 uL water.',
    'apiLevel': '2.15',
}


def run(protocol: protocol_api.ProtocolContext):
    sample_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 1, label='sample_plate')
    beads = protocol.load_labware('nest_1_reservoir_195ml', 2, label='beads_reservoir')
    ethanol = protocol.load_labware('nest_1_reservoir_195ml', 3, label='ethanol_reservoir')
    water = protocol.load_labware('nest_1_reservoir_195ml', 4, label='water_reservoir')
    waste = protocol.load_labware('nest_1_reservoir_195ml', 5, label='waste')
    elution_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 6, label='elution_plate')

    tips20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tips300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)
    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tips20])
    p300 = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tips300])

    tips_used = {p20: 0, p300: 0}

    def pick_up(pip):
        if tips_used[pip] >= 96:
            pip.reset_tipracks()
            tips_used[pip] = 0
        pip.pick_up_tip()
        tips_used[pip] += 1

    def move(pip, volume, src, dest, mix_reps=0, mix_vol=0):
        """Move volume from src to dest with a fresh tip, splitting if needed."""
        pick_up(pip)
        remaining = volume
        while remaining > 0:
            v = min(remaining, pip.max_volume)
            pip.aspirate(v, src)
            pip.dispense(v, dest)
            remaining -= v
        if mix_reps:
            pip.mix(mix_reps, mix_vol, dest)
        pip.drop_tip()

    samples = sample_plate.wells()          # A1:H12
    eluates = elution_plate.wells()         # A1:H12
    waste_well = waste['A1']

    # 1. Add 0.8x beads (40 uL) and mix
    for well in samples:
        move(p300, 40, beads['A1'], well, mix_reps=10, mix_vol=40)

    # 2-3. Bind and separate
    protocol.comment('Incubate sample_plate 5 min at room temperature (beads bind DNA)')
    protocol.comment('Engage magnetic module; wait 5 min until solution clears')

    # 4. Remove supernatant
    for well in samples:
        move(p300, 90, well, waste_well)

    # 5-8. Two 80% ethanol washes
    for wash in (1, 2):
        protocol.comment(f'Ethanol wash {wash}')
        for well in samples:
            move(p300, 200, ethanol['A1'], well)
        for well in samples:
            move(p300, 200, well, waste_well)

    # 9-10. Dry and release
    protocol.comment('Air dry beads 5 min at room temperature (magnet engaged); '
                     'beads should appear matte not shiny')
    protocol.comment('Disengage magnetic module')

    # 11. Elute in water and mix
    for well in samples:
        move(p300, 50, water['A1'], well, mix_reps=10, mix_vol=40)

    # 12. Incubate and separate
    protocol.comment('Incubate sample_plate 2 min at room temperature; '
                     'then re-engage magnetic module 5 min')

    # 13. Transfer cleaned DNA to elution plate
    for src, dest in zip(samples, eluates):
        move(p300, 45, src, dest)
