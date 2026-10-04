from opentrons import protocol_api

metadata = {'protocolName': 'AMPure XP cleanup', 'apiLevel': '2.15'}


def run(protocol: protocol_api.ProtocolContext):
    sample = protocol.load_labware('corning_96_wellplate_360ul_flat', 1, label='sample_plate')
    beads = protocol.load_labware('nest_1_reservoir_195ml', 2, label='beads_reservoir')
    etoh = protocol.load_labware('nest_1_reservoir_195ml', 3, label='ethanol_reservoir')
    water = protocol.load_labware('nest_1_reservoir_195ml', 4, label='water_reservoir')
    waste = protocol.load_labware('nest_1_reservoir_195ml', 5, label='waste')
    elut = protocol.load_labware('corning_96_wellplate_360ul_flat', 6, label='elution_plate')
    tr20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tr300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)
    protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tr20])
    p300 = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tr300])

    wells = [w for col in sample.columns() for w in col]
    ewells = [w for col in elut.columns() for w in col]

    def step(vol, src, dsts, mix=None, drop_in=None):
        p300.reset_tipracks()
        for i, d in enumerate(dsts):
            p300.pick_up_tip()
            p300.aspirate(vol, src)
            p300.dispense(vol, d)
            if mix:
                p300.mix(10, mix, d)
            p300.drop_tip()

    def remove(vol, srcs, dst):
        p300.reset_tipracks()
        for s in srcs:
            p300.pick_up_tip()
            p300.aspirate(vol, s.bottom(1))
            p300.dispense(vol, dst)
            p300.drop_tip()

    step(40, beads['A1'], wells, mix=50)
    protocol.comment('Incubate sample_plate 5 min at room temperature (beads bind DNA)')
    protocol.comment('Engage magnetic module; wait 5 min until solution clears')
    remove(90, wells, waste['A1'])
    step(200, etoh['A1'], wells)
    remove(200, wells, waste['A1'])
    step(200, etoh['A1'], wells)
    remove(200, wells, waste['A1'])
    protocol.comment('Air dry beads 5 min at room temperature (magnet engaged); beads should appear matte not shiny')
    protocol.comment('Disengage magnetic module')
    step(50, water['A1'], wells, mix=40)
    protocol.comment('Incubate sample_plate 2 min at room temperature; then re-engage magnetic module 5 min')
    p300.reset_tipracks()
    for s, d in zip(wells, ewells):
        p300.pick_up_tip()
        p300.aspirate(45, s.bottom(1))
        p300.dispense(45, d)
        p300.drop_tip()
