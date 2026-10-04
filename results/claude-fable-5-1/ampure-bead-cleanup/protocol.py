from opentrons import protocol_api

metadata = {
    'protocolName': 'AMPure XP 0.8x magnetic bead cleanup of PCR products',
    'author': 'Claude',
    'description': ('0.8x AMPure XP cleanup of 50 uL PCR products: bind, remove '
                    'supernatant, two 80% ethanol washes, dry, elute in 50 uL water.'),
    'apiLevel': '2.15',
}


def run(protocol: protocol_api.ProtocolContext):
    # ------------------------------------------------------------------ deck
    sample_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 1,
                                         label='sample_plate')
    beads_reservoir = protocol.load_labware('nest_1_reservoir_195ml', 2,
                                            label='beads_reservoir')
    ethanol_reservoir = protocol.load_labware('nest_1_reservoir_195ml', 3,
                                              label='ethanol_reservoir')
    water_reservoir = protocol.load_labware('nest_1_reservoir_195ml', 4,
                                            label='water_reservoir')
    waste = protocol.load_labware('nest_1_reservoir_195ml', 5, label='waste')
    elution_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 6,
                                          label='elution_plate')

    tips20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tips300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)

    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tips20])
    p300 = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tips300])

    samples = sample_plate.wells()          # A1..H12, column order
    eluates = elution_plate.wells()         # A1..H12, column order
    beads = beads_reservoir['A1']
    ethanol = ethanol_reservoir['A1']
    water = water_reservoir['A1']
    waste_well = waste['A1']

    def pick(volume):
        """Choose the pipette suited to the volume."""
        return p20 if volume <= 20 else p300

    def transfer_each(volume, sources, dests, mix_after=None):
        """Transfer `volume` per well with a fresh tip for each well.
        `sources`/`dests` may be a single well or a list of wells."""
        pip = pick(volume)
        if not isinstance(sources, list):
            sources = [sources] * len(dests)
        if not isinstance(dests, list):
            dests = [dests] * len(sources)
        for src, dst in zip(sources, dests):
            pip.pick_up_tip()
            pip.aspirate(volume, src)
            pip.dispense(volume, dst)
            if mix_after:
                reps, mix_vol = mix_after
                pip.mix(reps, mix_vol, dst)
            pip.blow_out(dst.top())
            pip.drop_tip()
        pip.reset_tipracks()

    # ----------------------------------------------------------------- steps
    # 1. Add 0.8x beads (40 uL) to 50 uL PCR product, mix 10x
    protocol.comment('Step 1: Add 40 uL AMPure XP beads to each sample, mix 10x')
    transfer_each(40, beads, samples, mix_after=(10, 40))

    # 2. Bind
    protocol.comment('Step 2: Incubate sample_plate 5 min at room temperature '
                     '(beads bind DNA)')

    # 3. Magnet
    protocol.comment('Step 3: Engage magnetic module; wait 5 min until solution clears')

    # 4. Remove supernatant (90 uL) to waste
    protocol.comment('Step 4: Remove 90 uL supernatant from each sample to waste')
    transfer_each(90, samples, waste_well)

    # 5. Ethanol wash 1 - add
    protocol.comment('Step 5: Add 200 uL 80% ethanol to each sample (wash 1)')
    transfer_each(200, ethanol, samples)

    # 6. Ethanol wash 1 - remove
    protocol.comment('Step 6: Remove 200 uL ethanol (wash 1) from each sample to waste')
    transfer_each(200, samples, waste_well)

    # 7. Ethanol wash 2 - add
    protocol.comment('Step 7: Add 200 uL 80% ethanol to each sample (wash 2)')
    transfer_each(200, ethanol, samples)

    # 8. Ethanol wash 2 - remove
    protocol.comment('Step 8: Remove 200 uL ethanol (wash 2) from each sample to waste')
    transfer_each(200, samples, waste_well)

    # 9. Dry
    protocol.comment('Step 9: Air dry beads 5 min at room temperature (magnet engaged); '
                     'beads should appear matte not shiny')

    # 10. Disengage magnet
    protocol.comment('Step 10: Disengage magnetic module')

    # 11. Elute: add 50 uL water, mix 10x
    protocol.comment('Step 11: Add 50 uL nuclease-free water to each sample, mix 10x')
    transfer_each(50, water, samples, mix_after=(10, 40))

    # 12. Elution incubation and magnet
    protocol.comment('Step 12: Incubate sample_plate 2 min at room temperature; '
                     'then re-engage magnetic module 5 min')

    # 13. Transfer 45 uL cleaned DNA to elution plate
    protocol.comment('Step 13: Transfer 45 uL cleaned DNA from each sample to elution_plate')
    transfer_each(45, samples, eluates)

    protocol.comment('Protocol complete: 45 uL cleaned DNA per well in elution_plate.')
