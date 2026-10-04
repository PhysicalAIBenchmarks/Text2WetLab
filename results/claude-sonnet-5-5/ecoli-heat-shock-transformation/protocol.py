from opentrons import protocol_api

metadata = {
    'protocolName': 'APEX Protocol 1 - heat shock transformation (LV, 8 plasmids)',
    'apiLevel': '2.15',
}

N = 8
ROWS = 'ABCDEFGH'
# Paper: Low Volume (LV) configuration used for automated runs:
# 1 uL DNA (1.5e-4 pmol/uL) + 10 uL cells + 50 uL SOC.
DNA_UL = 1
SOC_UL = 50
# Paper defaults: 4 C 30 min, 42 C 30 s, SOC recovery 37 C 1 h.
INCUBATE_C, INCUBATE_MIN = 4, 30
SHOCK_C, SHOCK_SEC = 42, 30
RECOVER_C, RECOVER_MIN = 37, 60


def run(protocol: protocol_api.ProtocolContext):
    plasmids = protocol.load_labware('biorad_96_wellplate_200ul_pcr', 1, label='plasmid_plate')
    soc = protocol.load_labware('nest_12_reservoir_15ml', 2, label='soc_reservoir')
    tc = protocol.load_module('thermocycler')
    tplate = tc.load_labware('biorad_96_wellplate_200ul_pcr', label='transformation_plate')
    tips20 = protocol.load_labware('opentrons_96_tiprack_20ul', 4)
    tips300 = protocol.load_labware('opentrons_96_tiprack_300ul', 5)
    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tips20])
    p300 = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tips300])

    wells = [f'{r}1' for r in ROWS[:N]]

    # Keep the pre-chilled cells cold while the lid is open.
    # Lid heater is off while open; block held at 4 C.
    tc.open_lid()
    tc.set_block_temperature(INCUBATE_C)

    # 1) Add 1 uL plasmid to 10 uL cells (fresh tip per transformation, no mixing
    #    to avoid damaging the cells; dispense into the cell droplet).
    for w in wells:
        p20.pick_up_tip()
        p20.aspirate(DNA_UL, plasmids[w])
        p20.dispense(DNA_UL, tplate[w])
        p20.touch_tip()
        p20.drop_tip()

    # 2) Cold incubation of DNA + cells: 4 C, 30 min. Lid at 4 C block is closed;
    #    lid warmed to 42 C (choice: prevents condensation / evaporation of the small volumes).
    tc.close_lid()
    tc.set_lid_temperature(SHOCK_C)
    tc.set_block_temperature(INCUBATE_C, hold_time_minutes=INCUBATE_MIN)

    # 3) Heat shock 42 C for 30 s.
    tc.set_block_temperature(SHOCK_C, hold_time_seconds=SHOCK_SEC)

    # 4) Return block to 4 C (rapid shift back, as on ice) while SOC is added.
    #    This is my choice; the paper only says cells are then recovered in SOC.
    tc.set_block_temperature(INCUBATE_C)
    tc.open_lid()
    for w in wells:
        p300.pick_up_tip()
        p300.aspirate(SOC_UL, soc['A1'])
        p300.dispense(SOC_UL, tplate[w])
        p300.drop_tip()

    # 5) Recovery at 37 C for 1 h, lid closed and heated at 37 C.
    tc.close_lid()
    tc.set_lid_temperature(RECOVER_C)
    tc.set_block_temperature(RECOVER_C, hold_time_minutes=RECOVER_MIN)

    # Hold cells at 4 C afterwards and leave the lid open for Protocol 2 (out of scope).
    tc.deactivate_lid()
    tc.set_block_temperature(INCUBATE_C)
    tc.open_lid()
