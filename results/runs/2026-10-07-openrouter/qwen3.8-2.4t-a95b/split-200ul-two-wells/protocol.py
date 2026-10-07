metadata = {
    'protocolName': 'Split 200 uL into two 100 uL wells',
    'apiLevel': '2.15',
}


def run(protocol):
    # Load labware exactly as the operator set up the deck
    reservoir = protocol.load_labware(
        'nest_1_reservoir_195ml', 1, label='reservoir')
    plate = protocol.load_labware(
        'corning_96_wellplate_360ul_flat', 2, label='plate')

    # Load tip racks
    tips20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tips300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)

    # Pipettes
    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tips20])
    p300 = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tips300])

    # 100 uL each into plate wells A1 and B1 from reservoir A1 (100 uL is within
    # the p300's 20-300 uL range)
    p300.distribute(
        100,
        reservoir.wells_by_name()['A1'],
        [plate.wells_by_name()['A1'], plate.wells_by_name()['B1']],
        new_tip='always',
    )

    # Make sure no tip is left on the pipette at the end
    if p300.has_tip:
        p300.drop_tip()
    p300.reset_tipracks()
