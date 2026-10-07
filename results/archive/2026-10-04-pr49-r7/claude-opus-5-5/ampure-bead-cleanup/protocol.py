from opentrons import protocol_api

metadata = {
    'protocolName': 'AMPure XP 0.8x bead cleanup of PCR products',
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

    samples = sample_plate.wells()  # A1..H12, column order
    eluates = elution_plate.wells()
    waste_well = waste['A1']

    def pick_up(pip):
        try:
            pip.pick_up_tip()
        except Exception:
            pip.reset_tipracks()
            pip.pick_up_tip()

    def move(pip, vol, src, dest, mix=None, new_tip_each=True):
        """Transfer vol from src (well or list) to each dest well, pairing lists."""
        srcs = src if isinstance(src, list) else [src] * len(dest)
        if not new_tip_each:
            pick_up(pip)
        for s, d in zip(srcs, dest):
            if new_tip_each:
                pick_up(pip)
            pip.aspirate(vol, s)
            pip.dispense(vol, d)
            if mix:
                pip.mix(mix[0], mix[1], d)
            pip.blow_out(d.top())
            if new_tip_each:
                pip.drop_tip()
        if not new_tip_each:
            pip.drop_tip()

    # 1. Add 40 uL beads (0.8x) and mix
    move(p300, 40, beads['A1'], samples, mix=(10, 60))

    # 2-3
    protocol.comment('Incubate sample_plate 5 min at room temperature (beads bind DNA)')
    protocol.comment('Engage magnetic module; wait 5 min until solution clears')

    # 4. Remove supernatant
    move(p300, 90, samples, [waste_well] * 96)

    # 5-8. Two ethanol washes
    for n in (1, 2):
        move(p300, 200, ethanol['A1'], samples, new_tip_each=False)
        move(p300, 200, samples, [waste_well] * 96)
        protocol.comment('Ethanol wash %d complete' % n)

    # 9-10
    protocol.comment('Air dry beads 5 min at room temperature (magnet engaged); beads should appear matte not shiny')
    protocol.comment('Disengage magnetic module')

    # 11. Elute in 50 uL water and mix
    move(p300, 50, water['A1'], samples, mix=(10, 40))

    # 12
    protocol.comment('Incubate sample_plate 2 min at room temperature; then re-engage magnetic module 5 min')

    # 13. Transfer 45 uL eluate to elution plate
    move(p300, 45, samples, eluates)
