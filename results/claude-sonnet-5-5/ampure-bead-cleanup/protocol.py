from opentrons import protocol_api

metadata = {'protocolName': 'AMPure XP 0.8x cleanup', 'apiLevel': '2.15'}


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

    wells = [w for col in sample.columns() for w in col]
    ewells = [w for col in elution.columns() for w in col]
    used = [0]

    def tip():
        if used[0] >= 96:
            p300.reset_tipracks()
            used[0] = 0
        used[0] += 1
        p300.pick_up_tip()

    def add(src, vol, mix=None):
        for w in wells:
            tip()
            p300.aspirate(vol, src)
            p300.dispense(vol, w.bottom(2))
            if mix:
                p300.mix(10, mix, w.bottom(2))
            p300.drop_tip()

    def remove(vol, dst):
        for w in wells:
            tip()
            p300.aspirate(vol, w.bottom(1))
            p300.dispense(vol, dst)
            p300.drop_tip()

    add(beads['A1'], 40, mix=40)
    protocol.comment('Incubate sample_plate 5 min at room temperature (beads bind DNA)')
    protocol.comment('Engage magnetic module; wait 5 min until solution clears')
    remove(90, waste['A1'])
    add(etoh['A1'], 200)
    remove(200, waste['A1'])
    add(etoh['A1'], 200)
    remove(200, waste['A1'])
    protocol.comment('Air dry beads 5 min at room temperature (magnet engaged); beads should appear matte not shiny')
    protocol.comment('Disengage magnetic module')
    add(water['A1'], 50, mix=30)
    protocol.comment('Incubate sample_plate 2 min at room temperature; then re-engage magnetic module 5 min')
    for w, e in zip(wells, ewells):
        tip()
        p300.aspirate(45, w.bottom(1))
        p300.dispense(45, e.bottom(2))
        p300.drop_tip()
