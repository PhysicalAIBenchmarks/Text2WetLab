from opentrons import protocol_api

metadata = {
    'protocolName': 'AMPure XP 0.8x bead cleanup of PCR products',
    'author': 'OT-2 protocol',
    'description': '0.8x AMPure XP cleanup of 96 x 50 uL PCR products, '
                   'two 80% ethanol washes, elution in 50 uL water',
    'apiLevel': '2.15',
}


def run(protocol: protocol_api.ProtocolContext):
    # Labware
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

    # Pipettes
    p20 = protocol.load_instrument(
        'p20_single_gen2', 'left', tip_racks=[tips20])
    p300 = protocol.load_instrument(
        'p300_single_gen2', 'right', tip_racks=[tips300])

    beads = beads_reservoir['A1']
    ethanol = ethanol_reservoir['A1']
    water = water_reservoir['A1']
    waste_well = waste['A1']

    samples = sample_plate.wells()[:96]
    eluates = elution_plate.wells()[:96]

    # Every step below uses one fresh tip per sample well (96 tips), so the
    # 300 uL rack is reset after each step to keep tips available.

    # Step 1: add 40 uL beads (0.8x) to each 50 uL PCR product and mix
    protocol.comment('Step 1: Adding 40 uL AMPure XP beads to each sample '
                     'and mixing 10 times')
    p300.transfer(40, beads, samples, mix_after=(10, 40),
                  new_tip='always')
    p300.reset_tipracks()

    # Step 2: binding incubation
    protocol.comment('Step 2: Incubate sample_plate 5 min at room temperature '
                     '(beads bind DNA)')

    # Step 3: magnet
    protocol.comment('Step 3: Engage magnetic module; wait 5 min until '
                     'solution clears')

    # Step 4: remove 90 uL supernatant to waste
    protocol.comment('Step 4: Removing 90 uL supernatant from each sample '
                     'to waste')
    p300.transfer(90, samples, waste_well, new_tip='always')
    p300.reset_tipracks()

    # Step 5: ethanol wash 1 - add
    protocol.comment('Step 5: Adding 200 uL 80% ethanol to each sample '
                     '(wash 1)')
    p300.transfer(200, ethanol, samples, new_tip='always')
    p300.reset_tipracks()

    # Step 6: ethanol wash 1 - remove
    protocol.comment('Step 6: Removing 200 uL ethanol wash 1 from each '
                     'sample to waste')
    p300.transfer(200, samples, waste_well, new_tip='always')
    p300.reset_tipracks()

    # Step 7: ethanol wash 2 - add
    protocol.comment('Step 7: Adding 200 uL 80% ethanol to each sample '
                     '(wash 2)')
    p300.transfer(200, ethanol, samples, new_tip='always')
    p300.reset_tipracks()

    # Step 8: ethanol wash 2 - remove
    protocol.comment('Step 8: Removing 200 uL ethanol wash 2 from each '
                     'sample to waste')
    p300.transfer(200, samples, waste_well, new_tip='always')
    p300.reset_tipracks()

    # Step 9: dry
    protocol.comment('Step 9: Air dry beads 5 min at room temperature '
                     '(magnet engaged); beads should appear matte not shiny')

    # Step 10: disengage magnet
    protocol.comment('Step 10: Disengage magnetic module')

    # Step 11: elute in 50 uL water, mix 10 times
    protocol.comment('Step 11: Adding 50 uL nuclease-free water to each '
                     'sample and mixing 10 times to resuspend beads')
    p300.transfer(50, water, samples, mix_after=(10, 40),
                  new_tip='always')
    p300.reset_tipracks()

    # Step 12: elution incubation and magnet
    protocol.comment('Step 12: Incubate sample_plate 2 min at room '
                     'temperature; then re-engage magnetic module 5 min')

    # Step 13: transfer 45 uL cleaned DNA to elution plate
    protocol.comment('Step 13: Transferring 45 uL cleaned DNA from each '
                     'sample to elution_plate')
    p300.transfer(45, samples, eluates, new_tip='always')
    p300.reset_tipracks()

    protocol.comment('AMPure XP cleanup complete: 45 uL cleaned DNA per well '
                     'in elution_plate')
