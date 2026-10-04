"""APEX Protocol 1 - automated heat shock transformation on the OT-2 thermocycler.

Kasprzyk, Herrera & Stracquadanio, "APEX: Automated Protein EXpression in
Escherichia coli", bioRxiv 2024, doi:10.1101/2024.08.13.607171.

Low Volume (LV) configuration, which the paper selected for all automated runs
after the volume optimisation (Table 1 / Fig. 4 legend):
    1 uL plasmid DNA (1.5e-4 pmol) + 10 uL competent cells + 50 uL SOC.
Default temperature programme (Results, Protocol 1):
    4 C for 30 min (DNA + cells), 42 C heat shock for 30 s,
    recovery in SOC at 37 C for 1 h.
"""

from opentrons import protocol_api

metadata = {
    'protocolName': 'APEX Protocol 1 - heat shock transformation (LV, 8 plasmids)',
    'author': 'APEX (Kasprzyk et al. 2024), OT-2 implementation',
    'description': 'Heat shock transformation of DH5alpha with pEX01-pEX08 '
                   'using the thermocycler module (Low Volume configuration).',
    'apiLevel': '2.15',
}

N_TRANSFORMATIONS = 8

# LV configuration (paper)
DNA_VOL = 1      # uL plasmid per transformation
CELL_VOL = 10    # uL competent cells already in the transformation plate
SOC_VOL = 50     # uL SOC recovery medium

# Temperature programme (paper defaults)
COLD_TEMP = 4
INCUBATION_MIN = 30
HEAT_SHOCK_TEMP = 42
HEAT_SHOCK_SEC = 30
RECOVERY_TEMP = 37
RECOVERY_MIN = 60

# Not specified in the paper (sound choices):
# - a short 2 min return to 4 C after the heat shock, the standard ice step of
#   chemical transformation, before SOC is added;
# - lid heated to 45 C during the 37 C recovery to stop condensation on the
#   lid/evaporation of the small volume; the lid is left unheated during the
#   4 C / 42 C steps so it does not warm the cells;
# - after recovery the block is held at 4 C so outgrowths stop growing while
#   waiting for Protocol 2 (spotting, out of scope).
POST_SHOCK_CHILL_MIN = 2
RECOVERY_LID_TEMP = 45
FINAL_HOLD_TEMP = 4


def run(protocol: protocol_api.ProtocolContext):
    # ---- Deck ----
    plasmid_plate = protocol.load_labware(
        'biorad_96_wellplate_200ul_pcr', 1, label='plasmid_plate')
    soc_reservoir = protocol.load_labware(
        'nest_12_reservoir_15ml', 2, label='soc_reservoir')
    tips20 = protocol.load_labware('opentrons_96_tiprack_20ul', 4)
    tips300 = protocol.load_labware('opentrons_96_tiprack_300ul', 5)

    tc = protocol.load_module('thermocycler')
    tf_plate = tc.load_labware(
        'biorad_96_wellplate_200ul_pcr', label='transformation_plate')

    p20 = protocol.load_instrument(
        'p20_single_gen2', 'left', tip_racks=[tips20])
    p300 = protocol.load_instrument(
        'p300_single_gen2', 'right', tip_racks=[tips300])

    wells = ['A1', 'B1', 'C1', 'D1', 'E1', 'F1', 'G1', 'H1'][:N_TRANSFORMATIONS]
    plasmids = [plasmid_plate[w] for w in wells]
    cells = [tf_plate[w] for w in wells]
    soc = soc_reservoir['A1']

    tips_used = {p20: 0, p300: 0}

    def pick_up(pip):
        # Tips are unlimited: refill the (single) rack once it is used up.
        if tips_used[pip] == 96:
            pip.reset_tipracks()
            tips_used[pip] = 0
        pip.pick_up_tip()
        tips_used[pip] += 1

    # ---- Keep competent cells cold, open lid for pipetting ----
    tc.deactivate_lid()
    tc.open_lid()
    tc.set_block_temperature(COLD_TEMP)

    # ---- Add 1 uL plasmid to each 10 uL cell aliquot ----
    # Fresh tip per plasmid; gentle, slow mixing to avoid damaging the
    # fragile chemically competent cells.
    default_asp, default_disp = p20.flow_rate.aspirate, p20.flow_rate.dispense
    for src, dest in zip(plasmids, cells):
        pick_up(p20)
        p20.aspirate(DNA_VOL, src.bottom(1))
        p20.dispense(DNA_VOL, dest.bottom(1))
        p20.flow_rate.aspirate, p20.flow_rate.dispense = 3.5, 3.5
        p20.mix(3, 5, dest.bottom(1))
        p20.flow_rate.aspirate, p20.flow_rate.dispense = default_asp, default_disp
        p20.blow_out(dest.top(-2))
        p20.touch_tip(dest)
        p20.drop_tip()

    # ---- Incubation on "ice", heat shock, chill ----
    tc.close_lid()
    tc.set_block_temperature(COLD_TEMP, hold_time_minutes=INCUBATION_MIN,
                             block_max_volume=DNA_VOL + CELL_VOL)
    tc.set_block_temperature(HEAT_SHOCK_TEMP, hold_time_seconds=HEAT_SHOCK_SEC,
                             block_max_volume=DNA_VOL + CELL_VOL)
    tc.set_block_temperature(COLD_TEMP, hold_time_minutes=POST_SHOCK_CHILL_MIN,
                             block_max_volume=DNA_VOL + CELL_VOL)
    tc.open_lid()

    # ---- Add 50 uL SOC recovery medium ----
    # Fresh tip per well so no cells are carried back into the SOC stock.
    for dest in cells:
        pick_up(p300)
        p300.aspirate(SOC_VOL, soc.bottom(1))
        p300.dispense(SOC_VOL, dest.bottom(1))
        p300.mix(3, 30, dest.bottom(1))
        p300.blow_out(dest.top(-2))
        p300.drop_tip()

    # ---- Recovery at 37 C for 1 h ----
    total_vol = DNA_VOL + CELL_VOL + SOC_VOL
    tc.close_lid()
    tc.set_lid_temperature(RECOVERY_LID_TEMP)
    tc.set_block_temperature(RECOVERY_TEMP, hold_time_minutes=RECOVERY_MIN,
                             block_max_volume=total_vol)

    # ---- Hold outgrowths cold for Protocol 2 ----
    tc.deactivate_lid()
    tc.set_block_temperature(FINAL_HOLD_TEMP, block_max_volume=total_vol)
    tc.open_lid()
    protocol.comment('Transformation complete: outgrowths (61 uL) in '
                     'transformation_plate A1-H1, held at 4 C for spotting.')
