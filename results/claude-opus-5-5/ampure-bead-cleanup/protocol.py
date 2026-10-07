from opentrons import protocol_api

metadata = {
    'protocolName': 'AMPure XP 0.8x bead cleanup of PCR products',
    'description': '0.8x AMPure XP cleanup of 50 uL PCR products, two 80% ethanol washes, elution in 50 uL water.',
    'apiLevel': '2.15',
}


def run(protocol: protocol_api.ProtocolContext):
    sample_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 1, label='sample_plate')
    beads_res = protocol.load_labware('nest_1_reservoir_195ml', 2, label='beads_reservoir')
    ethanol_res = protocol.load_labware('nest_1_reservoir_195ml', 3, label='ethanol_reservoir')
    water_res = protocol.load_labware('nest_1_reservoir_195ml', 4, label='water_reservoir')
    waste_res = protocol.load_labware('nest_1_reservoir_195ml', 5, label='waste')
    elution_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 6, label='elution_plate')

    tips20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tips300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)
    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tips20])
    p300 = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tips300])

    beads = beads_res['A1']
    ethanol = ethanol_res['A1']
    water = water_res['A1']
    waste = waste_res['A1']
    samples = sample_plate.wells()          # A1..H12, column order
    eluates = elution_plate.wells()

    def pick_up(pip):
        """Pick up a tip, refilling (resetting) the rack when it is used up."""
        try:
            pip.pick_up_tip()
        except protocol_api.labware.OutOfTipsError:
            pip.reset_tipracks()
            pip.pick_up_tip()

    def move(pip, vol, src, dest, mix_after=0, new_tip=True, blow_out=False):
        if new_tip:
            pick_up(pip)
        pip.aspirate(vol, src)
        pip.dispense(vol, dest)
        if mix_after:
            pip.mix(mix_after, vol, dest)
        if blow_out:
            pip.blow_out(dest)
        if new_tip:
            pip.drop_tip()

    # 1. Add 40 uL beads (0.8x) to each sample, mix 10x (fresh tip per well).
    for well in samples:
        move(p300, 40, beads, well, mix_after=10)

    # 2-3. Bind and separate.
    protocol.comment('Incubate sample_plate 5 min at room temperature (beads bind DNA)')
    protocol.comment('Engage magnetic module; wait 5 min until solution clears')

    # 4. Remove 90 uL supernatant to waste.
    for well in samples:
        move(p300, 90, well, waste.top(), blow_out=True)

    # 5-8. Two 80% ethanol washes.
    for n in (1, 2):
        protocol.comment('Ethanol wash {}'.format(n))
        pick_up(p300)
        for well in samples:
            # Dispense from the top of the well so the tip can be reused.
            move(p300, 200, ethanol, well.top(), new_tip=False, blow_out=True)
        p300.drop_tip()
        for well in samples:
            move(p300, 200, well, waste.top(), blow_out=True)

    # 9-10. Dry and release beads.
    protocol.comment('Air dry beads 5 min at room temperature (magnet engaged); '
                     'beads should appear matte not shiny')
    protocol.comment('Disengage magnetic module')

    # 11. Resuspend beads in 50 uL nuclease-free water, mix 10x.
    for well in samples:
        move(p300, 50, water, well, mix_after=10)

    # 12. Elute and separate.
    protocol.comment('Incubate sample_plate 2 min at room temperature; '
                     'then re-engage magnetic module 5 min')

    # 13. Transfer 45 uL cleaned DNA to the elution plate (A1->A1, ...).
    for src, dest in zip(samples, eluates):
        move(p300, 45, src, dest)
