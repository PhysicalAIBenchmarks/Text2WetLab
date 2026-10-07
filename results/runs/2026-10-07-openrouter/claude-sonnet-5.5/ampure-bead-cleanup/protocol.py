from opentrons import protocol_api

metadata = {
    'protocolName': 'AMPure XP bead cleanup of PCR products (0.8x)',
    'apiLevel': '2.13',
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

    wells = [sample_plate.wells_by_name()[f'{r}{c}'] for c in range(1, 13) for r in 'ABCDEFGH']
    elut = [elution_plate.wells_by_name()[f'{r}{c}'] for c in range(1, 13) for r in 'ABCDEFGH']

    def reagent_in(source, volume, mix=None):
        p300.reset_tipracks()
        for w in wells:
            p300.pick_up_tip()
            p300.aspirate(volume, source)
            p300.dispense(volume, w)
            if mix:
                p300.mix(10, mix, w)
            p300.blow_out(w.top())
            p300.drop_tip()

    def remove_to(volume, dest):
        p300.reset_tipracks()
        for w in wells:
            p300.pick_up_tip()
            p300.aspirate(volume, w)
            p300.dispense(volume, dest)
            p300.blow_out(dest)
            p300.drop_tip()

    # 1. beads
    reagent_in(beads['A1'], 40, mix=40)

    # 2-3
    protocol.comment('Incubate sample_plate 5 min at room temperature (beads bind DNA)')
    protocol.comment('Engage magnetic module; wait 5 min until solution clears')

    # 4. supernatant
    remove_to(90, waste['A1'])

    # 5-8. ethanol washes
    reagent_in(ethanol['A1'], 200)
    remove_to(200, waste['A1'])
    reagent_in(ethanol['A1'], 200)
    remove_to(200, waste['A1'])

    # 9-10
    protocol.comment('Air dry beads 5 min at room temperature (magnet engaged); beads should appear matte not shiny')
    protocol.comment('Disengage magnetic module')

    # 11. elution
    reagent_in(water['A1'], 50, mix=40)

    # 12
    protocol.comment('Incubate sample_plate 2 min at room temperature; then re-engage magnetic module 5 min')

    # 13. transfer eluate
    p300.reset_tipracks()
    for src, dst in zip(wells, elut):
        p300.pick_up_tip()
        p300.aspirate(45, src)
        p300.dispense(45, dst)
        p300.drop_tip()
