from opentrons import protocol_api

metadata = {
    'apiLevel': '2.13',
    'protocolName': 'AMPure XP PCR Cleanup',
    'description': '0.8x AMPure XP magnetic bead cleanup of 96 PCR products',
}


def run(protocol: protocol_api.ProtocolContext):
    # ---------------- Labware ----------------
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

    # ---------------- Pipettes ----------------
    tips_20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tips_300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)

    p20 = protocol.load_instrument(
        'p20_single_gen2', 'left', tip_racks=[tips_20])
    p300 = protocol.load_instrument(
        'p300_single_gen2', 'right', tip_racks=[tips_300])

    # All transfers in this protocol are 40-200 uL -> p300 is used throughout.

    # ---------------- Locations ----------------
    sample_wells = sample_plate.wells()          # A1..H12, in order
    elution_wells = elution_plate.wells()        # A1..H12, in order
    bead_source = beads_reservoir['A1']
    ethanol_source = ethanol_reservoir['A1']
    water_source = water_reservoir['A1']
    waste_dest = waste['A1']

    # ---------------- Helpers ----------------
    def add_to_plate(volume, source, dests, mix_reps=0, mix_volume=0):
        """One source -> many destination wells, one fresh tip per well."""
        for dest in dests:
            p300.pick_up_tip()
            p300.aspirate(volume, source)
            p300.dispense(volume, dest)
            if mix_reps:
                p300.mix(mix_reps, mix_volume, dest)
            p300.drop_tip()
        p300.reset_tipracks()

    def remove_to_waste(volume, sources, dest):
        """Many source wells -> one destination, one fresh tip per well."""
        for src in sources:
            p300.pick_up_tip()
            p300.aspirate(volume, src)
            p300.dispense(volume, dest)
            p300.drop_tip()
        p300.reset_tipracks()

    def transfer_pairs(volume, sources, dests):
        """Paired well-to-well transfers (A1->A1, A2->A2, ...)."""
        for src, dest in zip(sources, dests):
            p300.pick_up_tip()
            p300.aspirate(volume, src)
            p300.dispense(volume, dest)
            p300.drop_tip()
        p300.reset_tipracks()

    # ---------------- Protocol ----------------

    # Step 1: Add 40 uL AMPure XP beads to each sample well, mix 10x.
    # Wells hold 50 uL PCR product + 40 uL beads = 90 uL; mix below that.
    protocol.comment('Step 1: Adding 40 uL AMPure XP beads to each sample '
                     'well and mixing 10 times.')
    add_to_plate(40, bead_source, sample_wells, mix_reps=10, mix_volume=80)

    # Step 2: Incubation (manual step, not simulated).
    protocol.comment('Step 2: Incubate sample plate 5 minutes at room '
                     'temperature (beads bind DNA).')

    # Step 3: Magnet (manual step, not simulated).
    protocol.comment('Step 3: Engage magnetic module; wait 5 minutes until '
                     'solution clears.')

    # Step 4: Remove 90 uL supernatant from each well to waste.
    protocol.comment('Step 4: Removing 90 uL supernatant from each well '
                     'to waste.')
    remove_to_waste(90, sample_wells, waste_dest)

    # Step 5: Wash 1 - add 200 uL 80% ethanol to each well.
    protocol.comment('Step 5: Wash 1 - adding 200 uL 80% ethanol to each '
                     'well.')
    add_to_plate(200, ethanol_source, sample_wells)

    # Step 6: Remove 200 uL ethanol wash 1 to waste.
    protocol.comment('Step 6: Removing 200 uL ethanol wash 1 to waste.')
    remove_to_waste(200, sample_wells, waste_dest)

    # Step 7: Wash 2 - add 200 uL 80% ethanol to each well.
    protocol.comment('Step 7: Wash 2 - adding 200 uL 80% ethanol to each '
                     'well.')
    add_to_plate(200, ethanol_source, sample_wells)

    # Step 8: Remove 200 uL ethanol wash 2 to waste.
    protocol.comment('Step 8: Removing 200 uL ethanol wash 2 to waste.')
    remove_to_waste(200, sample_wells, waste_dest)

    # Step 9: Air dry (manual step, not simulated).
    protocol.comment('Step 9: Air dry beads 5 minutes at room temperature '
                     '(magnet engaged); beads should appear matte, not '
                     'shiny.')

    # Step 10: Disengage magnet (manual step, not simulated).
    protocol.comment('Step 10: Disengage magnetic module.')

    # Step 11: Elute - add 50 uL nuclease-free water, mix 10x.
    protocol.comment('Step 11: Adding 50 uL nuclease-free water to each '
                     'well and mixing 10 times.')
    add_to_plate(50, water_source, sample_wells, mix_reps=10, mix_volume=45)

    # Step 12: Incubation + magnet (manual steps, not simulated).
    protocol.comment('Step 12: Incubate sample plate 2 minutes at room '
                     'temperature; then re-engage magnetic module for 5 '
                     'minutes.')

    # Step 13: Transfer 45 uL cleaned DNA to elution plate (paired wells).
    protocol.comment('Step 13: Transferring 45 uL cleaned DNA from sample '
                     'plate to elution plate.')
    transfer_pairs(45, sample_wells, elution_wells)

    protocol.comment('AMPure XP cleanup complete. Elution plate holds 45 uL '
                     'cleaned DNA per well; 5 uL remains in each sample '
                     'well with the beads.')
