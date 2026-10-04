"""AMPure XP (0.8x) magnetic bead cleanup of 96 x 50 uL PCR products on the OT-2."""

from opentrons import protocol_api

metadata = {
    'protocolName': 'AMPure XP 0.8x bead cleanup of PCR products',
    'author': 'Generated',
    'description': 'Add 0.8x beads, bind, wash twice with 80% ethanol, dry, elute in water, transfer eluate.',
    'apiLevel': '2.15',
}

# Volumes (uL)
BEAD_VOL = 40          # 0.8x of 50 uL PCR product
SUPERNATANT_VOL = 90   # 50 uL product + 40 uL beads
ETHANOL_VOL = 200
WATER_VOL = 50
ELUATE_VOL = 45
MIX_REPS = 10
MIX_VOL = 40


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

    beads = beads_reservoir['A1']
    ethanol = ethanol_reservoir['A1']
    water = water_reservoir['A1']
    waste_well = waste['A1']

    sample_wells = sample_plate.wells()      # A1..H12, column-major order
    elution_wells = elution_plate.wells()

    # Every step below uses a fresh tip per well: exactly 96 tips per step.
    # After each step the rack is spent, so refresh it before the next step.
    def pick_up(pipette):
        try:
            pipette.pick_up_tip()
        except protocol_api.labware.OutOfTipsError:
            pipette.reset_tipracks()
            pipette.pick_up_tip()

    def one_to_many(pipette, volume, source, dests, mix_after=None, dispense_top=False):
        """Transfer `volume` from a single source well to each destination well, fresh tip each."""
        for dest in dests:
            pick_up(pipette)
            pipette.aspirate(volume, source)
            pipette.dispense(volume, dest.top() if dispense_top else dest)
            if mix_after:
                reps, vol = mix_after
                pipette.mix(reps, vol, dest)
            pipette.blow_out(dest.top())
            pipette.drop_tip()

    def many_to_one(pipette, volume, sources, dest):
        """Remove `volume` from each source well into a single destination (waste), fresh tip each."""
        for src in sources:
            pick_up(pipette)
            pipette.aspirate(volume, src)
            pipette.dispense(volume, dest.top())
            pipette.blow_out(dest.top())
            pipette.drop_tip()

    def many_to_many(pipette, volume, sources, dests):
        """Pairwise transfer A1->A1, A2->A2, ... with a fresh tip for each pair."""
        for src, dest in zip(sources, dests):
            pick_up(pipette)
            pipette.aspirate(volume, src)
            pipette.dispense(volume, dest)
            pipette.blow_out(dest.top())
            pipette.drop_tip()

    # ---------------- Step 1: add beads and mix ----------------
    protocol.comment('Step 1: Add 40 uL AMPure XP beads (0.8x) to each 50 uL PCR product and mix 10x.')
    one_to_many(p300, BEAD_VOL, beads, sample_wells, mix_after=(MIX_REPS, MIX_VOL))

    # ---------------- Steps 2-3: bind and separate (not simulated) ----------------
    protocol.comment('Step 2: Incubate sample_plate 5 min at room temperature (beads bind DNA).')
    protocol.comment('Step 3: Engage magnetic module; wait 5 min until solution clears.')

    # ---------------- Step 4: remove supernatant ----------------
    protocol.comment('Step 4: Remove 90 uL cleared supernatant from each well to waste.')
    many_to_one(p300, SUPERNATANT_VOL, sample_wells, waste_well)

    # ---------------- Steps 5-6: ethanol wash 1 ----------------
    protocol.comment('Step 5: Ethanol wash 1 - add 200 uL 80% ethanol to each well (magnet engaged).')
    one_to_many(p300, ETHANOL_VOL, ethanol, sample_wells)
    protocol.comment('Step 6: Remove 200 uL ethanol wash 1 from each well to waste.')
    many_to_one(p300, ETHANOL_VOL, sample_wells, waste_well)

    # ---------------- Steps 7-8: ethanol wash 2 ----------------
    protocol.comment('Step 7: Ethanol wash 2 - add 200 uL 80% ethanol to each well (magnet engaged).')
    one_to_many(p300, ETHANOL_VOL, ethanol, sample_wells)
    protocol.comment('Step 8: Remove 200 uL ethanol wash 2 from each well to waste.')
    many_to_one(p300, ETHANOL_VOL, sample_wells, waste_well)

    # ---------------- Steps 9-10: dry and disengage (not simulated) ----------------
    protocol.comment('Step 9: Air dry beads 5 min at room temperature (magnet engaged); '
                     'beads should appear matte, not shiny.')
    protocol.comment('Step 10: Disengage magnetic module.')

    # ---------------- Step 11: elute ----------------
    protocol.comment('Step 11: Add 50 uL nuclease-free water to each well and mix 10x to resuspend beads.')
    one_to_many(p300, WATER_VOL, water, sample_wells, mix_after=(MIX_REPS, MIX_VOL))

    # ---------------- Step 12: elution incubation (not simulated) ----------------
    protocol.comment('Step 12: Incubate sample_plate 2 min at room temperature; '
                     'then re-engage magnetic module for 5 min.')

    # ---------------- Step 13: transfer eluate ----------------
    protocol.comment('Step 13: Transfer 45 uL cleaned DNA from each well to the matching elution_plate well.')
    many_to_many(p300, ELUATE_VOL, sample_wells, elution_wells)

    protocol.comment('Cleanup complete. Elution plate holds 45 uL purified DNA per well.')
