from opentrons import protocol_api

metadata = {
    'protocolName': 'AMPure XP 0.8x bead cleanup of PCR products',
    'author': 'OT-2 protocol',
    'description': 'Clean up 50 uL PCR products with 0.8x AMPure XP beads, '
                   'two 80% ethanol washes, elute in 50 uL water.',
    'apiLevel': '2.15',
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

    tips20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tips300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)

    # ---------------- Pipettes ----------------
    p20 = protocol.load_instrument(
        'p20_single_gen2', 'left', tip_racks=[tips20])
    p300 = protocol.load_instrument(
        'p300_single_gen2', 'right', tip_racks=[tips300])

    # ---------------- Wells ----------------
    samples = sample_plate.wells()[:96]      # A1..H12 (column order)
    eluates = elution_plate.wells()[:96]
    beads = beads_reservoir['A1']
    ethanol = ethanol_reservoir['A1']
    water = water_reservoir['A1']
    waste_well = waste['A1']

    def pick(vol):
        """Choose the pipette suited to a volume."""
        return p20 if vol <= 20 else p300

    def one_to_many(vol, source, dests, mix_after=None):
        """Transfer vol from one source into each destination, fresh tip each."""
        pip = pick(vol)
        for dest in dests:
            pip.pick_up_tip()
            pip.aspirate(vol, source)
            pip.dispense(vol, dest)
            if mix_after is not None:
                reps, mix_vol = mix_after
                pip.mix(reps, mix_vol, dest)
            pip.blow_out(dest.top())
            pip.drop_tip()
        pip.reset_tipracks()

    def many_to_one(vol, sources, dest):
        """Transfer vol from each source into one destination, fresh tip each."""
        pip = pick(vol)
        for src in sources:
            pip.pick_up_tip()
            pip.aspirate(vol, src)
            pip.dispense(vol, dest)
            pip.blow_out(dest.top())
            pip.drop_tip()
        pip.reset_tipracks()

    def many_to_many(vol, sources, dests):
        """Transfer vol pairwise (A1->A1, A2->A2, ...), fresh tip each."""
        pip = pick(vol)
        for src, dest in zip(sources, dests):
            pip.pick_up_tip()
            pip.aspirate(vol, src)
            pip.dispense(vol, dest)
            pip.blow_out(dest.top())
            pip.drop_tip()
        pip.reset_tipracks()

    # ---------------- Step 1: add beads (0.8x) ----------------
    protocol.comment('Step 1: Add 40 uL AMPure XP beads to each 50 uL PCR '
                     'product and mix 10x.')
    one_to_many(40, beads, samples, mix_after=(10, 40))

    # ---------------- Steps 2-3: bind & magnet ----------------
    protocol.comment('Step 2: Incubate sample_plate 5 min at room temperature '
                     '(beads bind DNA).')
    protocol.comment('Step 3: Engage magnetic module; wait 5 min until '
                     'solution clears.')

    # ---------------- Step 4: remove supernatant ----------------
    protocol.comment('Step 4: Remove 90 uL supernatant from each well to waste.')
    many_to_one(90, samples, waste_well)

    # ---------------- Steps 5-6: ethanol wash 1 ----------------
    protocol.comment('Step 5: Ethanol wash 1 - add 200 uL 80% ethanol to each well.')
    one_to_many(200, ethanol, samples)
    protocol.comment('Step 6: Remove 200 uL ethanol wash 1 from each well to waste.')
    many_to_one(200, samples, waste_well)

    # ---------------- Steps 7-8: ethanol wash 2 ----------------
    protocol.comment('Step 7: Ethanol wash 2 - add 200 uL 80% ethanol to each well.')
    one_to_many(200, ethanol, samples)
    protocol.comment('Step 8: Remove 200 uL ethanol wash 2 from each well to waste.')
    many_to_one(200, samples, waste_well)

    # ---------------- Steps 9-10: dry & disengage ----------------
    protocol.comment('Step 9: Air dry beads 5 min at room temperature (magnet '
                     'engaged); beads should appear matte not shiny.')
    protocol.comment('Step 10: Disengage magnetic module.')

    # ---------------- Step 11: elute ----------------
    protocol.comment('Step 11: Add 50 uL nuclease-free water to each well and '
                     'mix 10x to resuspend beads.')
    one_to_many(50, water, samples, mix_after=(10, 40))

    # ---------------- Step 12: incubate & re-engage ----------------
    protocol.comment('Step 12: Incubate sample_plate 2 min at room temperature; '
                     'then re-engage magnetic module 5 min.')

    # ---------------- Step 13: transfer eluate ----------------
    protocol.comment('Step 13: Transfer 45 uL cleaned DNA from each well to '
                     'elution_plate (A1->A1, ...).')
    many_to_many(45, samples, eluates)

    protocol.comment('AMPure XP cleanup complete. Eluate (45 uL per well) is in '
                     'elution_plate.')
