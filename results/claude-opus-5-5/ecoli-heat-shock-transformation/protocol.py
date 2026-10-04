"""APEX Protocol 1 - heat shock transformation of E. coli DH5alpha on the OT-2 thermocycler.

Kasprzyk, Herrera & Stracquadanio, "APEX: Automated Protein EXpression in Escherichia coli",
bioRxiv 2024, doi:10.1101/2024.08.13.607171.

Paper parameters used:
  * Low Volume (LV) configuration, selected for all automated runs after the volume optimisation:
    1 uL plasmid DNA (1.5e-4 pmol) + 10 uL competent cells, recovered in 50 uL SOC.
  * Default Protocol 1 programme on the thermocycler module:
    DNA + cells at 4 C for 30 min, heat shock at 42 C for 30 s, recovery in SOC at 37 C for 1 h.
"""
from opentrons import protocol_api

metadata = {
    'protocolName': 'APEX Protocol 1 - Heat shock transformation (LV, 8 plasmids)',
    'author': 'APEX (Kasprzyk et al. 2024) re-implementation',
    'description': 'Thermocycler heat shock transformation of DH5alpha with pEX01-pEX08',
    'apiLevel': '2.15',
}

N_TRANSFORMATIONS = 8
DNA_VOL = 1      # uL, LV configuration
CELL_VOL = 10    # uL, already in the transformation plate
SOC_VOL = 50     # uL, LV configuration

INCUBATION_TEMP = 4       # C, DNA + cells pre-incubation
INCUBATION_MIN = 30
HEAT_SHOCK_TEMP = 42      # C
HEAT_SHOCK_SEC = 30
# The paper does not state a post-shock chill; the standard heat shock method returns cells to ice
# for ~2 min before adding SOC, so we bring the block back to 4 C and hold 2 min.
CHILL_TEMP = 4
CHILL_MIN = 2
RECOVERY_TEMP = 37        # C
RECOVERY_MIN = 60
# Not specified in the paper: heated lid during the 1 h recovery to prevent evaporation/condensation
# of the 61 uL outgrowth (the paper notes the thermocycler avoids needing manual plate covers).
LID_TEMP = 45


def run(protocol: protocol_api.ProtocolContext):
    # ---- labware (fixed deck) ----
    plasmid_plate = protocol.load_labware('biorad_96_wellplate_200ul_pcr', 1, label='plasmid_plate')
    soc_reservoir = protocol.load_labware('nest_12_reservoir_15ml', 2, label='soc_reservoir')
    tips20 = protocol.load_labware('opentrons_96_tiprack_20ul', 4)
    tips300 = protocol.load_labware('opentrons_96_tiprack_300ul', 5)

    tc = protocol.load_module('thermocycler')
    tf_plate = tc.load_labware('biorad_96_wellplate_200ul_pcr', label='transformation_plate')

    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tips20])
    p300 = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tips300])

    def pick_up(pip):
        # tips are unlimited: refill the rack when it is empty
        if not any(t.has_tip for rack in pip.tip_racks for t in rack.wells()):
            pip.reset_tipracks()
        pip.pick_up_tip()

    wells = ['A1', 'B1', 'C1', 'D1', 'E1', 'F1', 'G1', 'H1'][:N_TRANSFORMATIONS]
    soc = soc_reservoir.wells_by_name()['A1']

    # ---- keep competent cells cold while the lid is open for pipetting ----
    tc.open_lid()
    tc.deactivate_lid()
    tc.set_block_temperature(INCUBATION_TEMP)

    # ---- 1. add 1 uL plasmid DNA to 10 uL cells (fresh tip each, gentle mix) ----
    for w in wells:
        pick_up(p20)
        p20.aspirate(DNA_VOL, plasmid_plate.wells_by_name()[w].bottom(1))
        dest = tf_plate.wells_by_name()[w]
        p20.dispense(DNA_VOL, dest.bottom(1))
        # gentle mixing; competent cells are fragile, so small volume and slow flow
        p20.mix(3, 5, dest.bottom(1), rate=0.5)
        p20.blow_out(dest.bottom(3))
        p20.touch_tip(dest)
        p20.drop_tip()

    # ---- 2. pre-incubation on the cold block: 4 C, 30 min (lid closed) ----
    tc.close_lid()
    tc.set_block_temperature(INCUBATION_TEMP, hold_time_minutes=INCUBATION_MIN, block_max_volume=CELL_VOL + DNA_VOL)

    # ---- 3. heat shock: 42 C, 30 s, then straight back to the cold block ----
    tc.set_block_temperature(HEAT_SHOCK_TEMP, hold_time_seconds=HEAT_SHOCK_SEC, block_max_volume=CELL_VOL + DNA_VOL)
    tc.set_block_temperature(CHILL_TEMP, hold_time_minutes=CHILL_MIN, block_max_volume=CELL_VOL + DNA_VOL)

    # ---- 4. add 50 uL SOC to each transformation (fresh tip each to avoid cross-contamination) ----
    tc.open_lid()
    for w in wells:
        pick_up(p300)
        p300.aspirate(SOC_VOL, soc.bottom(1))
        dest = tf_plate.wells_by_name()[w]
        p300.dispense(SOC_VOL, dest.bottom(1))
        p300.mix(3, 30, dest.bottom(1), rate=0.5)
        p300.blow_out(dest.bottom(5))
        p300.touch_tip(dest)
        p300.drop_tip()

    # ---- 5. recovery: 37 C for 1 h, lid closed and heated ----
    total_vol = DNA_VOL + CELL_VOL + SOC_VOL
    tc.set_lid_temperature(LID_TEMP)
    tc.close_lid()
    tc.set_block_temperature(RECOVERY_TEMP, hold_time_minutes=RECOVERY_MIN, block_max_volume=total_vol)

    # ---- done: outgrowths ready for spotting (Protocol 2, out of scope) ----
    tc.deactivate_lid()
    tc.open_lid()
    # Block is left at 37 C so the outgrowth stays at recovery temperature until the operator
    # retrieves it / starts Protocol 2.
    protocol.comment('Transformation complete: 61 uL outgrowths in transformation_plate A1-H1.')
