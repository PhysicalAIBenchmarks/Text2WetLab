from opentrons import protocol_api

metadata = {
    'protocolName': 'APEX Protocol 1 - automated heat shock transformation (LV configuration)',
    'description': 'Heat shock transformation of 8 plasmids into DH5a on the OT-2 thermocycler '
                   '(Kasprzyk et al., APEX, bioRxiv 2024).',
    'apiLevel': '2.13',
}

N = 8
# Paper: the Low Volume (LV) configuration was selected for all automated runs:
# 1 uL DNA + 10 uL competent cells, then 50 uL SOC (Fig. 4 legend).
DNA_UL = 1
SOC_UL = 50
# Paper defaults: 4 C for 30 min, 42 C for 30 s, recovery in SOC at 37 C for 1 h.
INCUBATE_C, INCUBATE_MIN = 4, 30
SHOCK_C, SHOCK_S = 42, 30
RECOVER_C, RECOVER_MIN = 37, 60


def run(protocol: protocol_api.ProtocolContext):
    plasmid_plate = protocol.load_labware('biorad_96_wellplate_200ul_pcr', 1, label='plasmid_plate')
    soc_res = protocol.load_labware('nest_12_reservoir_15ml', 2, label='soc_reservoir')
    tc = protocol.load_module('thermocycler')
    tc_plate = tc.load_labware('biorad_96_wellplate_200ul_pcr', label='transformation_plate')
    tips20 = protocol.load_labware('opentrons_96_tiprack_20ul', 4)
    tips300 = protocol.load_labware('opentrons_96_tiprack_300ul', 5)
    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tips20])
    p300 = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tips300])

    wells = ['%s1' % r for r in 'ABCDEFGH'][:N]
    soc = soc_res['A1']

    # Keep the cells cold (pre-chilled block) while the lid is open for DNA addition.
    tc.open_lid()
    tc.set_block_temperature(INCUBATE_C)

    # 1) Add 1 uL plasmid n to 10 uL cells n, fresh tip each time.
    # Paper does not specify mixing; a gentle mix (3x 5 uL) is used to disperse the DNA
    # without vortex-like shear on the competent cells.
    for w in wells:
        p20.pick_up_tip()
        p20.aspirate(DNA_UL, plasmid_plate[w])
        p20.dispense(DNA_UL, tc_plate[w])
        p20.mix(3, 5, tc_plate[w])
        p20.drop_tip()

    # 2) DNA/cell incubation at 4 C for 30 min. Lid heated to 42 C (not stated in the paper)
    # to avoid condensation on the lid during the incubations.
    tc.close_lid()
    tc.set_lid_temperature(42)
    tc.set_block_temperature(INCUBATE_C, hold_time_minutes=INCUBATE_MIN)

    # 3) Heat shock 42 C for 30 s on the thermocycler (rapid ramp).
    tc.set_block_temperature(SHOCK_C, hold_time_seconds=SHOCK_S)

    # 4) Move to the 37 C recovery temperature, add SOC (fresh tip per well), recover 1 h.
    # The paper gives no cooling step after the shock, so SOC is added straight away.
    tc.set_block_temperature(RECOVER_C)
    tc.open_lid()
    for w in wells:
        p300.pick_up_tip()
        p300.aspirate(SOC_UL, soc)
        p300.dispense(SOC_UL, tc_plate[w])
        p300.drop_tip()
    tc.close_lid()
    tc.set_block_temperature(RECOVER_C, hold_time_minutes=RECOVER_MIN)

    # 5) Park the plate cold (4 C) and open the lid for the next step (spotting, out of scope).
    tc.set_block_temperature(INCUBATE_C)
    tc.deactivate_lid()
    tc.open_lid()
