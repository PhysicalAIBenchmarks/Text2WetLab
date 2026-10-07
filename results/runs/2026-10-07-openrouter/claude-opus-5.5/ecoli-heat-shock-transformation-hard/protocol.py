"""APEX Protocol 1 - heat shock transformation of E. coli DH5a on the OT-2 thermocycler.

Kasprzyk, Herrera & Stracquadanio, "APEX: Automated Protein EXpression in Escherichia coli",
bioRxiv 2024, doi:10.1101/2024.08.13.607171.

Paper parameters used:
  - Low Volume (LV) configuration, selected for all automated runs after the volume optimisation:
    1 uL DNA (1.5e-4 pmol) + 10 uL competent cells, recovered in 50 uL SOC (Figure 4 legend).
  - Default Protocol 1 programme: DNA + cells at 4 C for 30 min, heat shock at 42 C for 30 s,
    recovery in SOC at 37 C for 1 h, all on the thermocycler module.

Choices where the paper is silent are marked "CHOICE" below.
"""
from opentrons import protocol_api

metadata = {
    'protocolName': 'APEX Protocol 1 - Heat shock transformation (8 plasmids, LV)',
    'author': 'APEX (Kasprzyk et al. 2024), implemented for OT-2',
    'description': 'Heat shock transformation of DH5a with pEX01-pEX08 on the thermocycler module',
    'apiLevel': '2.15',
}

N_SAMPLES = 8
DNA_VOL = 1          # uL plasmid per transformation (LV)
SOC_VOL = 50         # uL SOC per transformation (LV)

COLD_TEMP = 4        # C
COLD_INCUBATION_MIN = 30
HEAT_SHOCK_TEMP = 42  # C
HEAT_SHOCK_SEC = 30
RECOVERY_TEMP = 37   # C
RECOVERY_MIN = 60

# CHOICE: the paper does not give a post-shock chill; a short 2 min return to 4 C is the
# standard step that stops the heat shock before SOC is added.
POST_SHOCK_CHILL_MIN = 2

# CHOICE: lid temperature for the closed-lid incubations. A lid warmer than the block
# prevents condensation on the plate seal/lid without affecting the samples.
LID_TEMP = 45


def run(protocol: protocol_api.ProtocolContext):
    # ---------------- deck ----------------
    plasmid_plate = protocol.load_labware(
        'biorad_96_wellplate_200ul_pcr', 1, label='plasmid_plate')
    soc_reservoir = protocol.load_labware(
        'nest_12_reservoir_15ml', 2, label='soc_reservoir')
    tips20 = protocol.load_labware('opentrons_96_tiprack_20ul', 4)
    tips300 = protocol.load_labware('opentrons_96_tiprack_300ul', 5)

    tc = protocol.load_module('thermocycler')
    tf_plate = tc.load_labware(
        'biorad_96_wellplate_200ul_pcr', label='transformation_plate')

    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tips20])
    p300 = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tips300])

    plasmids = plasmid_plate.columns()[0][:N_SAMPLES]   # A1..H1 = pEX01..pEX08
    cells = tf_plate.columns()[0][:N_SAMPLES]           # A1..H1 = competent DH5a
    soc = soc_reservoir.wells_by_name()['A1']

    # Tips are unlimited: reset the (single) rack of a pipette once all 96 tips are used.
    tips_used = {p20: 0, p300: 0}

    def pick_up(pip):
        if tips_used[pip] == 96:
            pip.reset_tipracks()
            tips_used[pip] = 0
        pip.pick_up_tip()
        tips_used[pip] += 1

    # ---------------- keep cells cold ----------------
    # Cells were loaded onto a pre-chilled block; hold them at 4 C with the lid open for pipetting.
    tc.open_lid()
    tc.set_block_temperature(COLD_TEMP)

    # ---------------- add DNA ----------------
    # 1 uL plasmid into 10 uL cells, fresh tip each, dispensed into the cells and mixed gently
    # (CHOICE: 3 x 5 uL at a slow rate - competent cells are fragile).
    for src, dest in zip(plasmids, cells):
        pick_up(p20)
        p20.aspirate(DNA_VOL, src.bottom(1))
        p20.dispense(DNA_VOL, dest.bottom(1))
        p20.mix(3, 5, dest.bottom(1), rate=0.5)
        p20.blow_out(dest.bottom(3))
        p20.drop_tip()

    # ---------------- 4 C incubation, 30 min ----------------
    tc.close_lid()
    tc.set_lid_temperature(LID_TEMP)
    tc.set_block_temperature(COLD_TEMP, hold_time_minutes=COLD_INCUBATION_MIN,
                             block_max_volume=DNA_VOL + 10)

    # ---------------- heat shock, 42 C for 30 s ----------------
    tc.set_block_temperature(HEAT_SHOCK_TEMP, hold_time_seconds=HEAT_SHOCK_SEC,
                             block_max_volume=DNA_VOL + 10)

    # ---------------- back to 4 C ----------------
    tc.set_block_temperature(COLD_TEMP, hold_time_minutes=POST_SHOCK_CHILL_MIN,
                             block_max_volume=DNA_VOL + 10)

    # ---------------- add SOC ----------------
    tc.deactivate_lid()
    tc.open_lid()
    # 50 uL SOC per well with the 300 uL pipette, fresh tip each, dispensed along the
    # wall above the cells then gently mixed (CHOICE: 3 x 30 uL at a slow rate).
    for dest in cells:
        pick_up(p300)
        p300.aspirate(SOC_VOL, soc.bottom(2))
        p300.dispense(SOC_VOL, dest.bottom(2))
        p300.mix(3, 30, dest.bottom(1), rate=0.5)
        p300.blow_out(dest.bottom(5))
        p300.drop_tip()

    # ---------------- recovery, 37 C for 1 h ----------------
    tc.close_lid()
    tc.set_lid_temperature(LID_TEMP)
    tc.set_block_temperature(RECOVERY_TEMP, hold_time_minutes=RECOVERY_MIN,
                             block_max_volume=DNA_VOL + 10 + SOC_VOL)

    # ---------------- finish ----------------
    # CHOICE: after recovery, chill to 4 C and leave the block holding there so the outgrowths
    # don't keep growing before spotting (Protocol 2, out of scope). Lid opened for the operator.
    tc.set_block_temperature(COLD_TEMP)
    tc.deactivate_lid()
    tc.open_lid()
    protocol.comment('Recovery complete: transformations are in transformation_plate A1-H1 '
                     '(61 uL each), held at 4 C. Proceed to Protocol 2 (spotting).')
