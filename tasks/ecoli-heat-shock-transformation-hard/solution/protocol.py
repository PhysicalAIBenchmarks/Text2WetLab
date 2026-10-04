metadata = {
    'protocolName': 'APEX Protocol 1: low-volume heat shock transformation (Kasprzyk et al., bioRxiv 2024, doi:10.1101/2024.08.13.607171)',
    'apiLevel': '2.13',
}


def run(protocol):
    tips20 = protocol.load_labware('opentrons_96_tiprack_20ul', 4)
    tips300 = protocol.load_labware('opentrons_96_tiprack_300ul', 5)
    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tips20])
    p300 = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tips300])
    plasmids = protocol.load_labware('biorad_96_wellplate_200ul_pcr', 1, label='plasmid_plate')
    soc = protocol.load_labware('nest_12_reservoir_15ml', 2, label='soc_reservoir')
    tc = protocol.load_module('thermocycler')
    plate = tc.load_labware('biorad_96_wellplate_200ul_pcr', label='transformation_plate')
    wells = ['A1', 'B1', 'C1', 'D1', 'E1', 'F1', 'G1', 'H1']

    # Keep the competent cells cold while the lid is open for pipetting.
    tc.open_lid()
    tc.set_lid_temperature(105)
    tc.set_block_temperature(4)

    # Low-volume (LV) configuration: 1 uL DNA into 10 uL cells, one fresh tip per plasmid.
    for w in wells:
        p20.transfer(1, plasmids[w], plate[w], new_tip='always')

    # Protocol 1: 30 min at 4 C with the DNA, heat shock at 42 C for 30 s, back to 4 C.
    tc.close_lid()
    tc.set_block_temperature(4, hold_time_minutes=30, block_max_volume=11)
    tc.set_block_temperature(42, hold_time_seconds=30, block_max_volume=11)
    tc.set_block_temperature(4, hold_time_minutes=2, block_max_volume=11)

    # Recovery: 50 uL SOC per transformation, then 1 h at 37 C.
    tc.open_lid()
    for w in wells:
        p300.transfer(50, soc['A1'], plate[w], new_tip='always')
    tc.close_lid()
    tc.set_block_temperature(37, hold_time_minutes=60, block_max_volume=61)
    tc.open_lid()
    tc.deactivate_lid()
    tc.set_block_temperature(4)
    protocol.comment('Recovery done: spot the transformations on selective agar (APEX Protocol 2).')
