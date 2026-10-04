from opentrons import protocol_api

metadata = {'protocolName': 'AMPure XP cleanup', 'apiLevel': '2.15'}


def run(protocol: protocol_api.ProtocolContext):
    sp = protocol.load_labware('corning_96_wellplate_360ul_flat', 1, label='sample_plate')
    beads = protocol.load_labware('nest_1_reservoir_195ml', 2, label='beads_reservoir')
    etoh = protocol.load_labware('nest_1_reservoir_195ml', 3, label='ethanol_reservoir')
    water = protocol.load_labware('nest_1_reservoir_195ml', 4, label='water_reservoir')
    waste = protocol.load_labware('nest_1_reservoir_195ml', 5, label='waste')
    ep = protocol.load_labware('corning_96_wellplate_360ul_flat', 6, label='elution_plate')
    t20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    t300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)
    protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[t20])
    p = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[t300])

    wells = [w for col in sp.columns() for w in col]
    ewells = [w for col in ep.columns() for w in col]

    def move(vol, src, dsts, mix=0, mixvol=0, src_clear=None, to_waste=False):
        p.reset_tipracks()
        for i, d in enumerate(dsts):
            p.pick_up_tip()
            s = src[i] if isinstance(src, list) else src
            p.aspirate(vol, s.bottom(src_clear) if src_clear else s)
            p.dispense(vol, d.top(-2) if to_waste else d.bottom(2) if not mix else d.bottom(2))
            if mix:
                p.mix(mix, mixvol, d.bottom(2))
            p.blow_out(d.top(-2))
            p.drop_tip()

    move(40, beads['A1'], wells, mix=10, mixvol=60)
    protocol.comment('Incubate sample_plate 5 min at room temperature (beads bind DNA)')
    protocol.comment('Engage magnetic module; wait 5 min until solution clears')
    move(90, wells, [waste['A1']] * 96, src_clear=0.7, to_waste=True)
    for n in (1, 2):
        move(200, etoh['A1'], wells)
        move(200, wells, [waste['A1']] * 96, src_clear=0.7, to_waste=True)
    protocol.comment('Air dry beads 5 min at room temperature (magnet engaged); beads should appear matte not shiny')
    protocol.comment('Disengage magnetic module')
    move(50, water['A1'], wells, mix=10, mixvol=30)
    protocol.comment('Incubate sample_plate 2 min at room temperature; then re-engage magnetic module 5 min')
    move(45, wells, ewells, src_clear=0.7)
