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

    def to_plate(vol, src, mix=None):
        p.reset_tipracks()
        for w in wells:
            p.pick_up_tip()
            p.aspirate(vol, src)
            p.dispense(vol, w)
            if mix:
                p.mix(mix, 40, w)
            p.drop_tip()

    def from_plate(vol, dst_for):
        p.reset_tipracks()
        for i, w in enumerate(wells):
            p.pick_up_tip()
            p.aspirate(vol, w.bottom(1))
            p.dispense(vol, dst_for(i))
            p.drop_tip()

    to_plate(40, beads['A1'], mix=10)
    protocol.comment('Incubate sample_plate 5 min at room temperature (beads bind DNA)')
    protocol.comment('Engage magnetic module; wait 5 min until solution clears')
    from_plate(90, lambda i: waste['A1'])
    to_plate(200, etoh['A1'])
    from_plate(200, lambda i: waste['A1'])
    to_plate(200, etoh['A1'])
    from_plate(200, lambda i: waste['A1'])
    protocol.comment('Air dry beads 5 min at room temperature (magnet engaged); beads should appear matte not shiny')
    protocol.comment('Disengage magnetic module')
    to_plate(50, water['A1'], mix=10)
    protocol.comment('Incubate sample_plate 2 min at room temperature; then re-engage magnetic module 5 min')
    from_plate(45, lambda i: ewells[i])
