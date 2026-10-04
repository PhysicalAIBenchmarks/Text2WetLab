from opentrons import protocol_api

metadata = {'protocolName': 'AMPure XP 0.8x cleanup', 'apiLevel': '2.15'}


def run(protocol: protocol_api.ProtocolContext):
    sp = protocol.load_labware('corning_96_wellplate_360ul_flat', 1, label='sample_plate')
    beads = protocol.load_labware('nest_1_reservoir_195ml', 2, label='beads_reservoir')
    etoh = protocol.load_labware('nest_1_reservoir_195ml', 3, label='ethanol_reservoir')
    water = protocol.load_labware('nest_1_reservoir_195ml', 4, label='water_reservoir')
    waste = protocol.load_labware('nest_1_reservoir_195ml', 5, label='waste')
    ep = protocol.load_labware('corning_96_wellplate_360ul_flat', 6, label='elution_plate')
    tr20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tr300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)
    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tr20])
    p300 = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tr300])

    wells = [w for col in sp.columns() for w in col]
    ewells = [w for col in ep.columns() for w in col]

    def move(src, dsts, vol, mix=0, mixvol=0, low_asp=False):
        p300.reset_tipracks()
        for i, d in enumerate(dsts):
            s = src[i] if isinstance(src, list) else src
            p300.pick_up_tip()
            p300.aspirate(vol, s.bottom(1) if low_asp else s)
            p300.dispense(vol, d if not isinstance(d, tuple) else d[0])
            if mix:
                p300.mix(mix, mixvol, d)
            p300.drop_tip()

    waste_w = waste['A1']
    move(beads['A1'], wells, 40, mix=10, mixvol=40)
    protocol.comment('Incubate sample_plate 5 min at room temperature (beads bind DNA)')
    protocol.comment('Engage magnetic module; wait 5 min until solution clears')
    move(wells, [waste_w] * 96, 90, low_asp=True)
    for _ in range(2):
        move(etoh['A1'], wells, 200)
        move(wells, [waste_w] * 96, 200, low_asp=True)
    protocol.comment('Air dry beads 5 min at room temperature (magnet engaged)')
    protocol.comment('Disengage magnetic module')
    move(water['A1'], wells, 50, mix=10, mixvol=40)
    protocol.comment('Incubate sample_plate 2 min at room temperature; then re-engage magnetic module 5 min')
    move(wells, ewells, 45, low_asp=True)
