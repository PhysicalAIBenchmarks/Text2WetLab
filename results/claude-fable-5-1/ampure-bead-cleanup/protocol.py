from opentrons import protocol_api

metadata = {
    'protocolName': 'AMPure XP 0.8x bead cleanup of PCR products',
    'author': 'OT-2 protocol',
    'description': 'Bead binding, supernatant removal, two 80% ethanol washes, '
                   'drying, elution in nuclease-free water, transfer of eluate.',
    'apiLevel': '2.15',
}

WELLS = [f'{row}{col}' for col in range(1, 13) for row in 'ABCDEFGH']


def run(protocol: protocol_api.ProtocolContext):
    # ---- Labware ----
    sample_plate = protocol.load_labware(
        'corning_96_wellplate_360ul_flat', 1, label='sample_plate')
    beads_reservoir = protocol.load_labware(
        'nest_1_reservoir_195ml', 2, label='beads_reservoir')
    ethanol_reservoir = protocol.load_labware(
        'nest_1_reservoir_195ml', 3, label='ethanol_reservoir')
    water_reservoir = protocol.load_labware(
        'nest_1_reservoir_195ml', 4, label='water_reservoir')
    waste = protocol.load_labware(
        'nest_1_reservoir_195ml', 5, label='waste')
    elution_plate = protocol.load_labware(
        'corning_96_wellplate_360ul_flat', 6, label='elution_plate')

    tips20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tips300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)

    p20 = protocol.load_instrument(
        'p20_single_gen2', 'left', tip_racks=[tips20])
    p300 = protocol.load_instrument(
        'p300_single_gen2', 'right', tip_racks=[tips300])

    beads = beads_reservoir['A1']
    ethanol = ethanol_reservoir['A1']
    water = water_reservoir['A1']
    waste_well = waste['A1']

    # ---- Tip handling: unlimited tips via reset_tipracks ----
    tips_used = {'p20': 0, 'p300': 0}

    def pick_up(pipette):
        key = 'p20' if pipette is p20 else 'p300'
        if tips_used[key] >= 96:
            pipette.reset_tipracks()
            tips_used[key] = 0
        pipette.pick_up_tip()
        tips_used[key] += 1

    def choose_pipette(volume):
        return p20 if volume <= 20 else p300

    def transfer_each(volume, source, dests, mix_after=None):
        """One source well into every destination well, fresh tip per well.
        mix_after: (repetitions, mix_volume) or None."""
        pipette = choose_pipette(volume)
        for dest in dests:
            pick_up(pipette)
            pipette.aspirate(volume, source)
            pipette.dispense(volume, dest)
            if mix_after is not None:
                reps, mix_vol = mix_after
                pipette.mix(reps, mix_vol, dest)
            pipette.blow_out(dest.top())
            pipette.drop_tip()

    def remove_each(volume, sources, dest):
        """Each source well into one destination well, fresh tip per well."""
        pipette = choose_pipette(volume)
        for src in sources:
            pick_up(pipette)
            pipette.aspirate(volume, src)
            pipette.dispense(volume, dest)
            pipette.blow_out(dest.top())
            pipette.drop_tip()

    def transfer_paired(volume, sources, dests):
        """Pairwise transfer (A1->A1, A2->A2, ...), fresh tip per pair."""
        pipette = choose_pipette(volume)
        for src, dest in zip(sources, dests):
            pick_up(pipette)
            pipette.aspirate(volume, src)
            pipette.dispense(volume, dest)
            pipette.blow_out(dest.top())
            pipette.drop_tip()

    samples = [sample_plate[w] for w in WELLS]
    eluates = [elution_plate[w] for w in WELLS]

    # 1. Add 40 uL beads to each sample (50 uL PCR product -> 90 uL), mix 10x
    protocol.comment('Step 1: Add 40 uL AMPure XP beads (0.8x) to each sample and mix 10 times')
    transfer_each(40, beads, samples, mix_after=(10, 50))

    # 2. Incubate
    protocol.comment('Step 2: Incubate sample_plate 5 min at room temperature (beads bind DNA)')

    # 3. Magnet
    protocol.comment('Step 3: Engage magnetic module; wait 5 min until solution clears')

    # 4. Remove 90 uL supernatant to waste
    protocol.comment('Step 4: Remove 90 uL supernatant from each sample to waste')
    remove_each(90, samples, waste_well)

    # 5. Ethanol wash 1: add 200 uL 80% ethanol
    protocol.comment('Step 5: Add 200 uL 80% ethanol to each sample (wash 1)')
    transfer_each(200, ethanol, samples)

    # 6. Remove ethanol wash 1
    protocol.comment('Step 6: Remove 200 uL ethanol wash 1 from each sample to waste')
    remove_each(200, samples, waste_well)

    # 7. Ethanol wash 2: add 200 uL 80% ethanol
    protocol.comment('Step 7: Add 200 uL 80% ethanol to each sample (wash 2)')
    transfer_each(200, ethanol, samples)

    # 8. Remove ethanol wash 2
    protocol.comment('Step 8: Remove 200 uL ethanol wash 2 from each sample to waste')
    remove_each(200, samples, waste_well)

    # 9. Dry
    protocol.comment('Step 9: Air dry beads 5 min at room temperature (magnet engaged); '
                     'beads should appear matte not shiny')

    # 10. Disengage magnet
    protocol.comment('Step 10: Disengage magnetic module')

    # 11. Elute: add 50 uL nuclease-free water, mix 10x
    protocol.comment('Step 11: Add 50 uL nuclease-free water to each sample and mix 10 times')
    transfer_each(50, water, samples, mix_after=(10, 40))

    # 12. Incubate and re-engage magnet
    protocol.comment('Step 12: Incubate sample_plate 2 min at room temperature; '
                     'then re-engage magnetic module 5 min')

    # 13. Transfer 45 uL cleaned DNA to elution plate
    protocol.comment('Step 13: Transfer 45 uL cleaned DNA from each sample to elution_plate')
    transfer_paired(45, samples, eluates)

    protocol.comment('Protocol complete.')
