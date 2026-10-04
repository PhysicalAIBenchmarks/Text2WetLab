from opentrons import protocol_api
from opentrons.protocol_api.labware import OutOfTipsError

metadata = {
    'protocolName': 'AMPure XP 0.8x bead cleanup of PCR products',
    'author': 'OT-2 protocol',
    'description': 'Clean up 50 uL PCR products with 0.8x AMPure XP beads, two 80% ethanol washes, elute in 50 uL water',
    'apiLevel': '2.15',
}


def run(protocol: protocol_api.ProtocolContext):
    # ---- Labware ----
    sample_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 1, label='sample_plate')
    beads_reservoir = protocol.load_labware('nest_1_reservoir_195ml', 2, label='beads_reservoir')
    ethanol_reservoir = protocol.load_labware('nest_1_reservoir_195ml', 3, label='ethanol_reservoir')
    water_reservoir = protocol.load_labware('nest_1_reservoir_195ml', 4, label='water_reservoir')
    waste = protocol.load_labware('nest_1_reservoir_195ml', 5, label='waste')
    elution_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 6, label='elution_plate')

    tips20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tips300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)

    # ---- Pipettes ----
    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tips20])
    p300 = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tips300])

    beads = beads_reservoir['A1']
    ethanol = ethanol_reservoir['A1']
    water = water_reservoir['A1']
    waste_well = waste['A1']

    samples = sample_plate.wells()[:96]        # A1:H12
    eluates = elution_plate.wells()[:96]       # A1:H12

    def pick_up(pipette):
        """Pick up a tip; tips are unlimited, so refill the rack when exhausted."""
        try:
            pipette.pick_up_tip()
        except OutOfTipsError:
            pipette.reset_tipracks()
            pipette.pick_up_tip()

    def transfer_each(pipette, volume, source, dests, mix_after=None):
        """One source well -> each destination well, fresh tip per well."""
        for dest in dests:
            pick_up(pipette)
            pipette.aspirate(volume, source)
            pipette.dispense(volume, dest)
            if mix_after:
                reps, mix_vol = mix_after
                pipette.mix(reps, mix_vol, dest)
            pipette.blow_out(dest.top())
            pipette.drop_tip()

    def remove_each(pipette, volume, sources, dest):
        """Each source well -> one destination (waste or elution), fresh tip per well."""
        for src in sources:
            pick_up(pipette)
            pipette.aspirate(volume, src.bottom(1))
            pipette.dispense(volume, dest)
            pipette.blow_out(dest.top())
            pipette.drop_tip()

    def pair_transfer(pipette, volume, sources, dests):
        """Source wells -> destination wells, paired in order, fresh tip per pair."""
        for src, dest in zip(sources, dests):
            pick_up(pipette)
            pipette.aspirate(volume, src.bottom(1))
            pipette.dispense(volume, dest)
            pipette.blow_out(dest.top())
            pipette.drop_tip()

    # 1. Add 40 uL beads (0.8x) to each 50 uL PCR product, mix 10x
    protocol.comment('Step 1: Add 40 uL AMPure XP beads to each sample well and mix 10 times')
    transfer_each(p300, 40, beads, samples, mix_after=(10, 70))

    # 2. Bind
    protocol.comment('Step 2: Incubate sample_plate 5 min at room temperature (beads bind DNA)')

    # 3. Magnet
    protocol.comment('Step 3: Engage magnetic module; wait 5 min until solution clears')

    # 4. Remove 90 uL supernatant to waste
    protocol.comment('Step 4: Remove 90 uL supernatant from each sample well to waste')
    remove_each(p300, 90, samples, waste_well)

    # 5. Ethanol wash 1 - add 200 uL 80% ethanol
    protocol.comment('Step 5: Add 200 uL 80% ethanol to each sample well (wash 1)')
    transfer_each(p300, 200, ethanol, samples)

    # 6. Remove ethanol wash 1
    protocol.comment('Step 6: Remove 200 uL ethanol (wash 1) from each sample well to waste')
    remove_each(p300, 200, samples, waste_well)

    # 7. Ethanol wash 2 - add 200 uL 80% ethanol
    protocol.comment('Step 7: Add 200 uL 80% ethanol to each sample well (wash 2)')
    transfer_each(p300, 200, ethanol, samples)

    # 8. Remove ethanol wash 2
    protocol.comment('Step 8: Remove 200 uL ethanol (wash 2) from each sample well to waste')
    remove_each(p300, 200, samples, waste_well)

    # 9. Dry
    protocol.comment('Step 9: Air dry beads 5 min at room temperature (magnet engaged); '
                     'beads should appear matte not shiny')

    # 10. Disengage magnet
    protocol.comment('Step 10: Disengage magnetic module')

    # 11. Elute - add 50 uL nuclease-free water, mix 10x
    protocol.comment('Step 11: Add 50 uL nuclease-free water to each sample well and mix 10 times')
    transfer_each(p300, 50, water, samples, mix_after=(10, 40))

    # 12. Elution incubation and magnet
    protocol.comment('Step 12: Incubate sample_plate 2 min at room temperature; '
                     'then re-engage magnetic module 5 min')

    # 13. Transfer 45 uL cleaned DNA to elution plate
    protocol.comment('Step 13: Transfer 45 uL cleaned DNA from each sample well to the matching elution_plate well')
    pair_transfer(p300, 45, samples, eluates)

    protocol.comment('Cleanup complete: 45 uL eluate per well in elution_plate')
