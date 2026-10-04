from opentrons import protocol_api

metadata = {'protocolName': 'AMPure XP cleanup', 'apiLevel': '2.15'}


def run(protocol: protocol_api.ProtocolContext):
    sample = protocol.load_labware('corning_96_wellplate_360ul_flat', 1, label='sample_plate')
    beads = protocol.load_labware('nest_1_reservoir_195ml', 2, label='beads_reservoir')
    etoh = protocol.load_labware('nest_1_reservoir_195ml', 3, label='ethanol_reservoir')
    water = protocol.load_labware('nest_1_reservoir_195ml', 4, label='water_reservoir')
    waste = protocol.load_labware('nest_1_reservoir_195ml', 5, label='waste')
    elution = protocol.load_labware('corning_96_wellplate_360ul_flat', 6, label='elution_plate')
    t20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    t300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)
    protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[t20])
    p300 = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[t300])

    wells = sample.wells()

    def step(src, dsts, vol, **kw):
        p300.reset_tipracks()
        for d_idx, d in enumerate(dsts):
            s = src if not isinstance(src, list) else src[d_idx]
            p300.transfer(vol, s, d, new_tip='always', **kw)

    # 1
    step(beads['A1'], wells, 40, mix_after=(10, 40))
    protocol.comment('Incubate sample_plate 5 min at room temperature (beads bind DNA)')
    protocol.comment('Engage magnetic module; wait 5 min until solution clears')
    # 4
    p300.reset_tipracks()
    for w in wells:
        p300.transfer(90, w, waste['A1'], new_tip='always')
    # 5-8
    for _ in range(2):
        step(etoh['A1'], wells, 200)
        p300.reset_tipracks()
        for w in wells:
            p300.transfer(200, w, waste['A1'], new_tip='always')
    protocol.comment('Air dry beads 5 min at room temperature (magnet engaged); beads should appear matte not shiny')
    protocol.comment('Disengage magnetic module')
    # 11
    step(water['A1'], wells, 50, mix_after=(10, 30))
    protocol.comment('Incubate sample_plate 2 min at room temperature; then re-engage magnetic module 5 min')
    # 13
    p300.reset_tipracks()
    for w, e in zip(wells, elution.wells()):
        p300.transfer(45, w, e, new_tip='always')
