from opentrons import protocol_api

metadata = {'protocolName': 'AMPure XP 0.8x bead cleanup', 'apiLevel': '2.15'}


def run(protocol: protocol_api.ProtocolContext):
    sample = protocol.load_labware('corning_96_wellplate_360ul_flat', 1, label='sample_plate')
    beads = protocol.load_labware('nest_1_reservoir_195ml', 2, label='beads_reservoir')
    etoh = protocol.load_labware('nest_1_reservoir_195ml', 3, label='ethanol_reservoir')
    water = protocol.load_labware('nest_1_reservoir_195ml', 4, label='water_reservoir')
    waste = protocol.load_labware('nest_1_reservoir_195ml', 5, label='waste')
    elution = protocol.load_labware('corning_96_wellplate_360ul_flat', 6, label='elution_plate')
    tips20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tips300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)
    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tips20])
    p300 = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tips300])

    used = {'n': 0}

    def pick():
        if used['n'] >= 96:
            p300.reset_tipracks()
            used['n'] = 0
        p300.pick_up_tip()
        used['n'] += 1

    wells = sample.wells()

    def move(vol, srcs, dests, mix=None):
        for s, d in zip(srcs, dests):
            pick()
            p300.aspirate(vol, s)
            p300.dispense(vol, d)
            if mix:
                p300.mix(10, mix, d)
            p300.drop_tip()

    move(40, [beads['A1']] * 96, wells, mix=40)
    protocol.comment('Incubate sample_plate 5 min at room temperature (beads bind DNA)')
    protocol.comment('Engage magnetic module; wait 5 min until solution clears')
    move(90, wells, [waste['A1']] * 96)
    for i in (1, 2):
        move(200, [etoh['A1']] * 96, wells)
        move(200, wells, [waste['A1']] * 96)
    protocol.comment('Air dry beads 5 min at room temperature (magnet engaged); beads should appear matte not shiny')
    protocol.comment('Disengage magnetic module')
    move(50, [water['A1']] * 96, wells, mix=40)
    protocol.comment('Incubate sample_plate 2 min at room temperature; then re-engage magnetic module 5 min')
    move(45, wells, elution.wells())
