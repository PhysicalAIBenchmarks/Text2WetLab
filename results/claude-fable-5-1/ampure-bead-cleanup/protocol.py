"""AMPure XP 0.8x magnetic bead cleanup of 50 uL PCR products (96 samples)."""

from opentrons import protocol_api

metadata = {
    'protocolName': 'AMPure XP 0.8x bead cleanup of PCR products',
    'author': 'OT-2 protocol',
    'description': ('0.8x AMPure XP cleanup: 40 uL beads into 50 uL PCR product, '
                    'bind, remove supernatant, two 200 uL 80% ethanol washes, '
                    'air dry, elute in 50 uL nuclease-free water, transfer 45 uL eluate.'),
    'apiLevel': '2.15',
}

NUM_SAMPLES = 96

BEAD_VOL = 40        # 0.8x of 50 uL PCR product
SUPERNATANT_VOL = 90  # 50 uL sample + 40 uL beads
ETHANOL_VOL = 200
WATER_VOL = 50
ELUATE_VOL = 45


def run(protocol: protocol_api.ProtocolContext):
    # ------------------------------------------------------------------ deck
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

    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tips20])
    p300 = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tips300])

    beads = beads_reservoir['A1']
    ethanol = ethanol_reservoir['A1']
    water = water_reservoir['A1']
    waste_well = waste['A1']

    samples = sample_plate.wells()[:NUM_SAMPLES]
    eluates = elution_plate.wells()[:NUM_SAMPLES]

    # All volumes in this protocol are 40-200 uL, so the p300 is used throughout.
    # The p20 is loaded per the deck setup but is not needed.

    def pick(pipette):
        """Pick up a fresh tip, resetting the rack when it is exhausted."""
        try:
            pipette.pick_up_tip()
        except protocol_api.labware.OutOfTipsError:
            pipette.reset_tipracks()
            pipette.pick_up_tip()

    def transfer_each(pipette, vol, source, dests, mix_after=None,
                      blow_out_dest=True):
        """One source well -> each destination well, fresh tip per well."""
        for dest in dests:
            pick(pipette)
            pipette.aspirate(vol, source)
            pipette.dispense(vol, dest)
            if mix_after:
                reps, mix_vol = mix_after
                pipette.mix(reps, mix_vol, dest)
            if blow_out_dest:
                pipette.blow_out(dest.top())
            pipette.drop_tip()

    def remove_each(pipette, vol, sources, dest):
        """Each source well -> one destination well, fresh tip per well."""
        for src in sources:
            pick(pipette)
            pipette.aspirate(vol, src)
            pipette.dispense(vol, dest)
            pipette.blow_out(dest.top())
            pipette.drop_tip()

    # ------------------------------------------------------------ step 1
    protocol.comment('Step 1: add 40 uL AMPure XP beads (0.8x) to each sample '
                     'and mix 10x.')
    transfer_each(p300, BEAD_VOL, beads, samples, mix_after=(10, 70))
    p300.reset_tipracks()

    # ------------------------------------------------------------ step 2-3
    protocol.comment('Step 2: Incubate sample_plate 5 min at room temperature '
                     '(beads bind DNA).')
    protocol.comment('Step 3: Engage magnetic module; wait 5 min until solution '
                     'clears.')

    # ------------------------------------------------------------ step 4
    protocol.comment('Step 4: remove 90 uL supernatant from each sample to waste.')
    remove_each(p300, SUPERNATANT_VOL, samples, waste_well)
    p300.reset_tipracks()

    # ------------------------------------------------------------ step 5-6
    protocol.comment('Step 5: wash 1 - add 200 uL 80% ethanol to each sample '
                     '(magnet engaged, do not disturb pellet).')
    transfer_each(p300, ETHANOL_VOL, ethanol, samples)
    p300.reset_tipracks()

    protocol.comment('Step 6: wash 1 - remove 200 uL ethanol from each sample '
                     'to waste.')
    remove_each(p300, ETHANOL_VOL, samples, waste_well)
    p300.reset_tipracks()

    # ------------------------------------------------------------ step 7-8
    protocol.comment('Step 7: wash 2 - add 200 uL 80% ethanol to each sample.')
    transfer_each(p300, ETHANOL_VOL, ethanol, samples)
    p300.reset_tipracks()

    protocol.comment('Step 8: wash 2 - remove 200 uL ethanol from each sample '
                     'to waste.')
    remove_each(p300, ETHANOL_VOL, samples, waste_well)
    p300.reset_tipracks()

    # ------------------------------------------------------------ step 9-10
    protocol.comment('Step 9: Air dry beads 5 min at room temperature (magnet '
                     'engaged); beads should appear matte not shiny.')
    protocol.comment('Step 10: Disengage magnetic module.')

    # ------------------------------------------------------------ step 11
    protocol.comment('Step 11: elute - add 50 uL nuclease-free water to each '
                     'sample and mix 10x to resuspend beads.')
    transfer_each(p300, WATER_VOL, water, samples, mix_after=(10, 40))
    p300.reset_tipracks()

    # ------------------------------------------------------------ step 12
    protocol.comment('Step 12: Incubate sample_plate 2 min at room temperature; '
                     'then re-engage magnetic module 5 min.')

    # ------------------------------------------------------------ step 13
    protocol.comment('Step 13: transfer 45 uL cleaned DNA from each sample to '
                     'the matching elution_plate well.')
    for src, dest in zip(samples, eluates):
        pick(p300)
        p300.aspirate(ELUATE_VOL, src)
        p300.dispense(ELUATE_VOL, dest)
        p300.blow_out(dest.top())
        p300.drop_tip()
    p300.reset_tipracks()

    protocol.comment('Cleanup complete: 45 uL eluate per well in elution_plate.')
