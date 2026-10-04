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

    used = {p20: 0, p300: 0}

    def pick_up(pip):
        if used[pip] >= 96:
            pip.reset_tipracks()
            used[pip] = 0
        pip.pick_up_tip()
        used[pip] += 1

    def pipette_for(vol):
        return p20 if vol <= 20 else p300

    def move(vol, src, dest, mix_reps=0, mix_vol=None):
        pip = pipette_for(vol)
        pick_up(pip)
        pip.aspirate(vol, src)
        pip.dispense(vol, dest)
        if mix_reps:
            pip.mix(mix_reps, mix_vol, dest)
        pip.drop_tip()

    samples = sample_plate.wells()  # A1..H12
    waste_well = waste['A1']

    # 1. Add 40 uL beads, mix 10x
    for w in samples:
        move(40, beads['A1'], w, mix_reps=10, mix_vol=40)

    # 2-3.
    protocol.comment('Incubate sample_plate 5 min at room temperature (beads bind DNA)')
    protocol.comment('Engage magnetic module; wait 5 min until solution clears')

    # 4. Remove 90 uL supernatant
    for w in samples:
        move(90, w, waste_well)

    # 5-8. Two ethanol washes
    for _ in range(2):
        for w in samples:
            move(200, ethanol['A1'], w)
        for w in samples:
            move(200, w, waste_well)

    # 9-10.
    protocol.comment('Air dry beads 5 min at room temperature (magnet engaged); beads should appear matte not shiny')
    protocol.comment('Disengage magnetic module')

    # 11. Elute in 50 uL water, mix 10x
    for w in samples:
        move(50, water['A1'], w, mix_reps=10, mix_vol=40)

    # 12.
    protocol.comment('Incubate sample_plate 2 min at room temperature; then re-engage magnetic module 5 min')

    # 13. Transfer 45 uL eluate to elution plate
    for src, dest in zip(samples, elution_plate.wells()):
        move(45, src, dest)
