from opentrons import protocol_api

metadata = {
    'protocolName': 'AMPure XP 0.8x bead cleanup of PCR products',
    'description': '0.8x AMPure XP cleanup of 50 uL PCR products, two 80% ethanol washes, elution in 50 uL water.',
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

    tip_counts = {p20: 0, p300: 0}

    def pick_up(pip):
        # Unlimited tips: reset the rack once all 96 have been used
        if tip_counts[pip] >= 96:
            pip.reset_tipracks()
            tip_counts[pip] = 0
        pip.pick_up_tip()
        tip_counts[pip] += 1

    def move(pip, vol, src, dest, mix_after=None):
        """Single-tip transfer of vol from src to dest, optional mix (reps, vol) after dispensing."""
        pick_up(pip)
        pip.aspirate(vol, src)
        pip.dispense(vol, dest)
        if mix_after:
            pip.mix(mix_after[0], mix_after[1], dest)
        pip.drop_tip()

    samples = sample_plate.wells()          # A1..H12
    elutions = elution_plate.wells()        # A1..H12
    waste_well = waste.wells_by_name()['A1']

    # 1. Add 40 uL beads (0.8x) and mix
    for w in samples:
        move(p300, 40, beads['A1'], w, mix_after=(10, 60))

    # 2-3. Bind and separate
    protocol.comment('Incubate sample_plate 5 min at room temperature (beads bind DNA)')
    protocol.comment('Engage magnetic module; wait 5 min until solution clears')

    # 4. Remove 90 uL supernatant
    for w in samples:
        move(p300, 90, w, waste_well)

    # 5-8. Two 80% ethanol washes
    for i in (1, 2):
        for w in samples:
            move(p300, 200, ethanol['A1'], w)
        for w in samples:
            move(p300, 200, w, waste_well)
        protocol.comment('Ethanol wash {} complete'.format(i))

    # 9-10. Dry and release
    protocol.comment('Air dry beads 5 min at room temperature (magnet engaged); beads should appear matte not shiny')
    protocol.comment('Disengage magnetic module')

    # 11. Elute in 50 uL water and mix
    for w in samples:
        move(p300, 50, water['A1'], w, mix_after=(10, 40))

    # 12. Incubate and separate
    protocol.comment('Incubate sample_plate 2 min at room temperature; then re-engage magnetic module 5 min')

    # 13. Transfer 45 uL eluate to clean plate
    for s, d in zip(samples, elutions):
        move(p300, 45, s, d)
