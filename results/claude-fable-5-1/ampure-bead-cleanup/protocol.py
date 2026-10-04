from opentrons import protocol_api

metadata = {
    'protocolName': 'AMPure XP 0.8x bead cleanup of PCR products',
    'author': 'OT-2',
    'description': 'Add 40 uL beads to 50 uL PCR product, bind, remove supernatant, '
                   'two 200 uL 80% ethanol washes, dry, elute in 50 uL water, '
                   'transfer 45 uL eluate to a clean plate.',
    'apiLevel': '2.15',
}


def run(protocol: protocol_api.ProtocolContext):
    # ---------------- Labware ----------------
    sample_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 1, label='sample_plate')
    beads_reservoir = protocol.load_labware('nest_1_reservoir_195ml', 2, label='beads_reservoir')
    ethanol_reservoir = protocol.load_labware('nest_1_reservoir_195ml', 3, label='ethanol_reservoir')
    water_reservoir = protocol.load_labware('nest_1_reservoir_195ml', 4, label='water_reservoir')
    waste = protocol.load_labware('nest_1_reservoir_195ml', 5, label='waste')
    elution_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 6, label='elution_plate')

    tips20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tips300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)

    # ---------------- Pipettes ----------------
    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tips20])
    p300 = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tips300])

    # Tip usage counters so racks are reset once exhausted (tips are unlimited)
    tip_count = {p20: 0, p300: 0}

    def pick_up(pip):
        if tip_count[pip] >= 96:
            pip.reset_tipracks()
            tip_count[pip] = 0
        pip.pick_up_tip()
        tip_count[pip] += 1

    def pipette_for(volume):
        return p20 if volume <= 20 else p300

    def transfer(volume, sources, dests, mix_after=None):
        """Transfer `volume` from each source to the paired destination with a
        fresh tip per transfer. `sources` may be a single well (fans out to all
        destinations). `mix_after` = (repetitions, mix_volume) or None."""
        if not isinstance(sources, (list, tuple)):
            sources = [sources] * len(dests)
        pip = pipette_for(volume)
        for src, dst in zip(sources, dests):
            pick_up(pip)
            pip.aspirate(volume, src)
            pip.dispense(volume, dst)
            if mix_after:
                reps, mix_vol = mix_after
                pip.mix(reps, mix_vol, dst)
            pip.blow_out(dst.top())
            pip.drop_tip()

    samples = sample_plate.wells()[:96]          # A1:H12
    eluates = elution_plate.wells()[:96]         # A1:H12

    # 1. Add 40 uL beads (0.8x) to each 50 uL PCR product; mix 10x -> 90 uL/well
    protocol.comment('Step 1: Add 40 uL AMPure XP beads to each sample well and mix 10 times.')
    transfer(40, beads_reservoir['A1'], samples, mix_after=(10, 70))

    # 2. Incubate
    protocol.comment('Step 2: Incubate sample_plate 5 min at room temperature (beads bind DNA).')

    # 3. Magnet
    protocol.comment('Step 3: Engage magnetic module; wait 5 min until solution clears.')

    # 4. Remove 90 uL supernatant to waste -> 0 uL/well
    protocol.comment('Step 4: Remove 90 uL supernatant from each well to waste.')
    transfer(90, samples, [waste['A1']] * 96)

    # 5. Wash 1: add 200 uL 80% ethanol -> 200 uL/well
    protocol.comment('Step 5: Add 200 uL 80% ethanol to each well (wash 1).')
    transfer(200, ethanol_reservoir['A1'], samples)

    # 6. Remove ethanol wash 1 -> 0 uL/well
    protocol.comment('Step 6: Remove 200 uL ethanol (wash 1) from each well to waste.')
    transfer(200, samples, [waste['A1']] * 96)

    # 7. Wash 2: add 200 uL 80% ethanol -> 200 uL/well
    protocol.comment('Step 7: Add 200 uL 80% ethanol to each well (wash 2).')
    transfer(200, ethanol_reservoir['A1'], samples)

    # 8. Remove ethanol wash 2 -> 0 uL/well
    protocol.comment('Step 8: Remove 200 uL ethanol (wash 2) from each well to waste.')
    transfer(200, samples, [waste['A1']] * 96)

    # 9. Dry
    protocol.comment('Step 9: Air dry beads 5 min at room temperature (magnet engaged); '
                     'beads should appear matte not shiny.')

    # 10. Disengage magnet
    protocol.comment('Step 10: Disengage magnetic module.')

    # 11. Elute: add 50 uL nuclease-free water, mix 10x -> 50 uL/well
    protocol.comment('Step 11: Add 50 uL nuclease-free water to each well and mix 10 times to resuspend beads.')
    transfer(50, water_reservoir['A1'], samples, mix_after=(10, 40))

    # 12. Incubate and re-engage magnet
    protocol.comment('Step 12: Incubate sample_plate 2 min at room temperature; '
                     'then re-engage magnetic module 5 min.')

    # 13. Transfer 45 uL cleaned DNA to elution plate -> 5 uL left in sample, 45 uL in elution
    protocol.comment('Step 13: Transfer 45 uL cleaned DNA from each sample well to the elution plate.')
    transfer(45, samples, eluates)

    protocol.comment('Cleanup complete. Eluate (45 uL/well) is in elution_plate A1:H12.')
