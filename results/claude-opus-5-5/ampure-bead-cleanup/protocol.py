from opentrons import protocol_api

metadata = {
    'protocolName': 'AMPure XP 0.8x cleanup of PCR products',
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

    used = {id(p20): 0, id(p300): 0}

    def pick_up(pip):
        if used[id(pip)] >= 96:
            pip.reset_tipracks()
            used[id(pip)] = 0
        pip.pick_up_tip()
        used[id(pip)] += 1

    def move(pip, vol, src, dst, mix_after=None):
        pick_up(pip)
        pip.aspirate(vol, src)
        pip.dispense(vol, dst)
        if mix_after:
            reps, mix_vol = mix_after
            pip.mix(reps, mix_vol, dst)
        pip.blow_out(dst.top())
        pip.drop_tip()

    samples = sample_plate.wells()          # A1..H12 (column order)
    eluates = elution_plate.wells()

    # 1. Add 0.8x beads (40 uL) and mix
    for w in samples:
        move(p300, 40, beads['A1'], w, mix_after=(10, 50))

    protocol.comment('Incubate sample_plate 5 min at room temperature (beads bind DNA)')
    protocol.comment('Engage magnetic module; wait 5 min until solution clears')

    # 4. Remove supernatant
    for w in samples:
        move(p300, 90, w, waste['A1'])

    # 5-8. Two ethanol washes
    for n in (1, 2):
        for w in samples:
            move(p300, 200, ethanol['A1'], w)
        for w in samples:
            move(p300, 200, w, waste['A1'])

    protocol.comment('Air dry beads 5 min at room temperature (magnet engaged); '
                     'beads should appear matte not shiny')
    protocol.comment('Disengage magnetic module')

    # 11. Elute in 50 uL water and mix
    for w in samples:
        move(p300, 50, water['A1'], w, mix_after=(10, 40))

    protocol.comment('Incubate sample_plate 2 min at room temperature; '
                     'then re-engage magnetic module 5 min')

    # 13. Transfer 45 uL eluate to clean plate
    for s, d in zip(samples, eluates):
        move(p300, 45, s, d)
