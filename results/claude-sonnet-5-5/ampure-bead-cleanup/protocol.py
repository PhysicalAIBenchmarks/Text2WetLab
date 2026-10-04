from opentrons import protocol_api

metadata = {'protocolName': 'AMPure XP 0.8x cleanup', 'apiLevel': '2.15'}


def run(protocol: protocol_api.ProtocolContext):
    sample = protocol.load_labware('corning_96_wellplate_360ul_flat', 1, label='sample_plate')
    beads = protocol.load_labware('nest_1_reservoir_195ml', 2, label='beads_reservoir')
    etoh = protocol.load_labware('nest_1_reservoir_195ml', 3, label='ethanol_reservoir')
    water = protocol.load_labware('nest_1_reservoir_195ml', 4, label='water_reservoir')
    waste = protocol.load_labware('nest_1_reservoir_195ml', 5, label='waste')
    elut = protocol.load_labware('corning_96_wellplate_360ul_flat', 6, label='elution_plate')
    t20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    t300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)
    protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[t20])
    p300 = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[t300])

    wells = [w for col in sample.columns() for w in col]
    ewells = [w for col in elut.columns() for w in col]

    def step(vol, src, dsts, **kw):
        p300.reset_tipracks()
        for i, d in enumerate(dsts):
            p300.transfer(vol, src, d, new_tip='always', **kw)

    step(40, beads['A1'], wells, mix_after=(10, 50))
    protocol.comment('Incubate sample_plate 5 min at room temperature (beads bind DNA)')
    protocol.comment('Engage magnetic module; wait 5 min until solution clears')
    p300.reset_tipracks()
    for w in wells:
        p300.transfer(90, w, waste['A1'], new_tip='always')
    for _ in range(2):
        step(200, etoh['A1'], wells)
        p300.reset_tipracks()
        for w in wells:
            p300.transfer(200, w, waste['A1'], new_tip='always')
    protocol.comment('Air dry beads 5 min at room temperature (magnet engaged); beads should appear matte not shiny')
    protocol.comment('Disengage magnetic module')
    step(50, water['A1'], wells, mix_after=(10, 40))
    protocol.comment('Incubate sample_plate 2 min at room temperature; then re-engage magnetic module 5 min')
    p300.reset_tipracks()
    for s, d in zip(wells, ewells):
        p300.transfer(45, s, d, new_tip='always')
