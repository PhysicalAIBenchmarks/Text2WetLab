from opentrons import protocol_api

# metadata
metadata = {
    'protocolName': 'AMPure XP Bead Cleanup of PCR Products',
    'author': 'Claude',
    'description': '0.8x AMPure XP magnetic bead cleanup of 50 uL PCR products.',
    'apiLevel': '2.13',
}


def run(protocol: protocol_api.ProtocolContext):
    # load labware with labels as specified
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

    # load pipettes
    p20 = protocol.load_instrument(
        'p20_single_gen2', 'left',
        tip_racks=[protocol.load_labware('opentrons_96_tiprack_20ul', 10)])
    p300 = protocol.load_instrument(
        'p300_single_gen2', 'right',
        tip_racks=[protocol.load_labware('opentrons_96_tiprack_300ul', 11)])

    wells = sample_plate.wells()  # A1..H12 in row-major order

    # Step 1: add 40 uL beads to each sample well, mix 10x
    p300.transfer(
        40, beads_reservoir['A1'], wells,
        mix_after=(10, 40), new_tip='once')

    p300.reset_tipracks()

    # Step 2: incubate (not simulated)
    protocol.comment('Incubate sample_plate 5 min at room temperature '
                     '(beads bind DNA)')

    # Step 3: engage magnet (not simulated)
    protocol.comment('Engage magnetic module; wait 5 min until solution clears')

    # Step 4: transfer 90 ul supernatant to waste
    # pick up a fresh tip and aspirate the full 90 uL from each well
    for well in wells:
        p300.pick_up_tip()
        p300.aspirate(90, well)
        p300.dispense(90, waste['A1'])
        p300.drop_tip()

    p300.reset_tipracks()

    # Step 5: wash 1 - add 200 uL ethanol
    p300.transfer(
        200, ethanol_reservoir['A1'], wells, new_tip='once')

    # Step 6: remove ethanol waste 1 (200 uL) to waste
    p300.reset_tipracks()
    for well in wells:
        p300.pick_up_tip()
        p300.aspirate(200, well)
        p300.dispense(200, waste['A1'])
        p300.drop_tip()

    p300.reset_tipracks()

    # Step 7: wash 2 - add 200 uL ethanol
    p300.transfer(
        200, ethanol_reservoir['A1'], wells, new_tip='once')

    # Step 8: remove ethanol waste 2 (200 uL) to waste
    p300.reset_tipracks()
    for well in wells:
        p300.pick_up_tip()
        p300.aspirate(200, well)
        p300.dispense(200, waste['A1'])
        p300.drop_tip()

    p300.reset_tipracks()

    # Step 9: air dry (not simulated)
    protocol.comment('Air dry beads 5 min at room temperature (magnet '
                     'engaged); beads should appear matte not shiny')

    # Step 10: disengage magnet (not simulated)
    protocol.comment('Disengage magnetic module')

    # Step 11: elute in 50 uL water, mix 10x
    p300.reset_tipracks()
    p300.transfer(
        50, water_reservoir['A1'], wells,
        mix_after=(10, 30), new_tip='once')

    # Step 12: incubate + re-engage (not simulated)
    protocol.comment('Incubate sample_plate 2 min at room temperature; '
                     'then re-engage magnetic module 5 min')

    # Step 13: transfer 45 uL cleaned DNA to elution plate
    p300.transfer(
        45, wells, elution_plate.wells(), new_tip='once')