from opentrons import protocol_api

metadata = {
    'protocolName': 'AMPure XP 0.8x cleanup of PCR products',
    'author': 'OT-2',
    'description': '0.8x AMPure XP bead cleanup of 50 uL PCR products, 2x 80% EtOH wash, elute in 50 uL water.',
}
requirements = {'robotType': 'OT-2', 'apiLevel': '2.15'}


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

    def new_tip(pip):
        try:
            pip.pick_up_tip()
        except protocol_api.labware.OutOfTipsError:
            pip.reset_tipracks()
            pip.pick_up_tip()

    def move(pip, vol, src, dest, mix_after=None):
        """Single-tip-per-transfer liquid move, optional post-dispense mix."""
        new_tip(pip)
        pip.aspirate(vol, src)
        pip.dispense(vol, dest)
        if mix_after:
            reps, mix_vol = mix_after
            pip.mix(reps, mix_vol, dest)
        pip.drop_tip()

    # 1. Add 40 uL beads (0.8x) and mix
    protocol.comment('Adding 40 uL AMPure XP beads (0.8x) to each sample')
    for s in samples:
        move(p300, 40, beads['A1'], s, mix_after=(10, 60))

    # 2-3. Bind and magnet
    protocol.comment('Incubate sample_plate 5 min at room temperature (beads bind DNA)')
    protocol.comment('Engage magnetic module; wait 5 min until solution clears')

    # 4. Remove 90 uL supernatant
    protocol.comment('Removing 90 uL supernatant to waste')
    for s in samples:
        move(p300, 90, s, waste_well)

    # 5-8. Two 80% ethanol washes
    for wash in (1, 2):
        protocol.comment(f'Ethanol wash {wash}: adding 200 uL 80% ethanol')
        new_tip(p300)  # one tip for adding clean ethanol to all wells (no contact with sample)
        for s in samples:
            p300.aspirate(200, ethanol['A1'])
            p300.dispense(200, s.top())
        p300.drop_tip()
        protocol.comment(f'Ethanol wash {wash}: removing 200 uL ethanol to waste')
        for s in samples:
            move(p300, 200, s, waste_well)

    # 9-10. Dry and release
    protocol.comment('Air dry beads 5 min at room temperature (magnet engaged); beads should appear matte not shiny')
    protocol.comment('Disengage magnetic module')

    # 11. Elute in 50 uL water
    protocol.comment('Adding 50 uL nuclease-free water and mixing to resuspend beads')
    for s in samples:
        move(p300, 50, water['A1'], s, mix_after=(10, 40))

    # 12. Incubate and magnet
    protocol.comment('Incubate sample_plate 2 min at room temperature; then re-engage magnetic module 5 min')

    # 13. Transfer 45 uL eluate
    protocol.comment('Transferring 45 uL cleaned DNA to elution_plate')
    for s, e in zip(samples, eluates):
        move(p300, 45, s, e)
