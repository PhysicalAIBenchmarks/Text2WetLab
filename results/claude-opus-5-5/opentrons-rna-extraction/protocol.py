"""
OT-2 in-house magnetic-bead SARS-CoV-2 RNA extraction (48 samples).

Based on: Automated low-cost SARS-CoV-2 RNA extraction protocols,
PLOS ONE 2021, doi:10.1371/journal.pone.0246302 (OT-2in-house protocol).

Per sample (Table 1 / "OT-2in-house protocol"):
 1. 40 uL magnetic beads + 250 uL isopropanol + 250 uL inactivated sample,
    mix by pipetting 5 times, incubate 5 min at room temperature.
 2. Engage GEN1 magnetic module for 4 min.
 3. Collect the supernatant and discard.
 4. Add 500 uL 70% ethanol, collect and discard.
 5. Add 500 uL 70% ethanol, collect and discard.
 6. Air dry 4 min.
 7. Disengage magnet, add 100 uL elution buffer.
 8. After 30 s engage the magnet.
 9. After 90 s collect the eluate and transfer it to the 96-well plate (4 C).
"""
import math

from opentrons import protocol_api

metadata = {
    'protocolName': 'OT-2 in-house magnetic bead RNA extraction (48 samples)',
    'author': 'Implemented from PLOS ONE 2021 16(2): e0246302',
    'description': 'Isopropanol/magnetic bead RNA extraction with two 70% '
                   'ethanol washes and 100 uL elution, GEN1 magnetic module.',
    'apiLevel': '2.13',
}

NUM_SAMPLES = 48

# Volumes (uL), from Table 1 of the paper
BEAD_VOL = 40
ISOPROPANOL_VOL = 250
SAMPLE_VOL = 250
WASH_VOL = 500
ELUTION_VOL = 100
SUPERNATANT_VOL = BEAD_VOL + ISOPROPANOL_VOL + SAMPLE_VOL  # 540 uL

# Times (minutes), from the paper
BINDING_INCUBATION_MIN = 5
MAGNET_BINDING_MIN = 4
AIR_DRY_MIN = 4
ELUTION_RESUSPEND_SEC = 30
ELUTION_MAGNET_SEC = 90

MAX_MULTI_VOL = 180  # working volume per trip with 200 uL filter tips


def run(ctx: protocol_api.ProtocolContext):
    # ---------------------------------------------------------------- labware
    waste_plate = ctx.load_labware(
        'usascientific_96_wellplate_2.4ml_deep', '1', 'supernatant waste')
    tips200 = [ctx.load_labware('opentrons_96_filtertiprack_200ul', slot,
                                '200 uL filter tips')
               for slot in ['2', '3', '9']]
    tips1000 = [ctx.load_labware('opentrons_96_filtertiprack_1000ul', '11',
                                 '1000 uL filter tips')]

    magdeck = ctx.load_module('magnetic module', '4')
    mag_plate = magdeck.load_labware(
        'usascientific_96_wellplate_2.4ml_deep', 'extraction plate')

    reservoir = ctx.load_labware('nest_12_reservoir_15ml', '5', 'reagents')

    tempdeck = ctx.load_module('tempdeck', '6')
    elution_plate = tempdeck.load_labware(
        'thermo_96_wellplate_200ul', 'elution plate')

    rack_1 = ctx.load_labware(
        'opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', '10',
        'samples 1-24')
    rack_2 = ctx.load_labware(
        'opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', '7',
        'samples 25-48')

    # -------------------------------------------------------------- pipettes
    p1000 = ctx.load_instrument('p1000_single_gen2', 'left',
                                tip_racks=tips1000)
    m300 = ctx.load_instrument('p300_multi_gen2', 'right',
                               tip_racks=tips200)

    # -------------------------------------------------------------- reagents
    beads = reservoir['A2']
    elution_buffer = reservoir['A4']
    isopropanol = [reservoir['A6'], reservoir['A7']]
    ethanol_wash1 = [reservoir['A9'], reservoir['A10']]
    ethanol_wash2 = [reservoir['A11'], reservoir['A12']]

    # ------------------------------------------------------- sample layout
    sample_cols = [1, 3, 5, 7, 9, 11]
    num_cols = math.ceil(NUM_SAMPLES / 8)
    sample_cols = sample_cols[:num_cols]
    mag_cols = [mag_plate.columns_by_name()[str(c)] for c in sample_cols]
    mag_tops = [col[0] for col in mag_cols]            # multichannel targets
    waste_tops = [waste_plate.columns_by_name()[str(c)][0]
                  for c in sample_cols]
    elution_tops = [elution_plate.columns_by_name()[str(c)][0]
                    for c in sample_cols]
    sample_tubes = (rack_1.wells() + rack_2.wells())[:NUM_SAMPLES]
    sample_dests = [well for col in mag_cols for well in col][:NUM_SAMPLES]

    def reagent_source(sources, col_index):
        """Split columns of the plate evenly over the reservoir channels."""
        per_source = math.ceil(num_cols / len(sources))
        return sources[col_index // per_source]

    def split(volume, max_vol=MAX_MULTI_VOL):
        n = math.ceil(volume / max_vol)
        return [volume / n] * n

    # Keep the eluates cold for the whole run
    tempdeck.set_temperature(4)
    magdeck.disengage()

    # ================================================ Step 1: reagent mix
    ctx.comment('Step 1: 40 uL beads + 250 uL isopropanol + 250 uL sample')

    # 40 uL magnetic beads per well (beads resuspended first)
    m300.flow_rate.aspirate = 50
    m300.flow_rate.dispense = 100
    m300.pick_up_tip()
    m300.mix(10, 150, beads.bottom(2))
    for dest in mag_tops:
        m300.mix(2, 150, beads.bottom(2))
        m300.aspirate(BEAD_VOL, beads.bottom(2))
        m300.dispense(BEAD_VOL, dest.bottom(5))
        m300.blow_out(dest.top(-2))
    m300.drop_tip()

    # 250 uL isopropanol per well (dispensed from above, same tips)
    m300.flow_rate.aspirate = 94
    m300.flow_rate.dispense = 94
    m300.pick_up_tip()
    for i, dest in enumerate(mag_tops):
        src = reagent_source(isopropanol, i)
        for vol in split(ISOPROPANOL_VOL):
            m300.aspirate(vol, src.bottom(1.5))
            m300.dispense(vol, dest.top(-2))
            m300.blow_out(dest.top(-2))
    m300.drop_tip()

    # 250 uL inactivated sample per well, mix 5 times
    for tube, dest in zip(sample_tubes, sample_dests):
        p1000.pick_up_tip()
        p1000.aspirate(SAMPLE_VOL, tube.bottom(2))
        p1000.dispense(SAMPLE_VOL, dest.bottom(3))
        p1000.mix(5, 400, dest.bottom(3))
        p1000.blow_out(dest.top(-2))
        p1000.drop_tip()

    ctx.comment('Incubating 5 min at room temperature')
    ctx.delay(minutes=BINDING_INCUBATION_MIN)

    # ===================================================== Step 2: magnet
    magdeck.engage()
    ctx.delay(minutes=MAGNET_BINDING_MIN, msg='Magnet engaged: 4 min')

    # ------------------------------------------- supernatant removal helper
    def remove_supernatant(volume):
        m300.flow_rate.aspirate = 30
        m300.flow_rate.dispense = 150
        for src, waste in zip(mag_tops, waste_tops):
            m300.pick_up_tip()
            for vol in split(volume):
                m300.aspirate(vol, src.bottom(1))
                m300.dispense(vol, waste.top(-2))
                m300.blow_out(waste.top(-2))
            m300.drop_tip()

    def add_ethanol(sources):
        m300.flow_rate.aspirate = 94
        m300.flow_rate.dispense = 94
        m300.pick_up_tip()
        for i, dest in enumerate(mag_tops):
            src = reagent_source(sources, i)
            for vol in split(WASH_VOL):
                m300.aspirate(vol, src.bottom(1.5))
                m300.dispense(vol, dest.top(-2))
                m300.blow_out(dest.top(-2))
        m300.drop_tip()

    # =============================================== Step 3: discard sup.
    ctx.comment('Step 3: removing 540 uL supernatant')
    remove_supernatant(SUPERNATANT_VOL)

    # =============================================== Steps 4-5: washes
    for n, sources in enumerate([ethanol_wash1, ethanol_wash2], start=1):
        ctx.comment('Step {}: 500 uL 70% ethanol wash {}'.format(n + 3, n))
        add_ethanol(sources)
        remove_supernatant(WASH_VOL)

    # =============================================== Step 6: air dry
    ctx.delay(minutes=AIR_DRY_MIN, msg='Air drying beads for 4 min')

    # =============================================== Step 7: elution buffer
    magdeck.disengage()
    ctx.comment('Step 7: adding 100 uL elution buffer')
    m300.flow_rate.aspirate = 50
    m300.flow_rate.dispense = 100
    for dest in mag_tops:
        m300.pick_up_tip()
        m300.aspirate(ELUTION_VOL, elution_buffer.bottom(1.5))
        m300.dispense(ELUTION_VOL, dest.bottom(1))
        m300.mix(5, 80, dest.bottom(1))
        m300.blow_out(dest.bottom(5))
        m300.touch_tip(v_offset=-3)
        m300.drop_tip()

    # =============================================== Step 8: magnet
    ctx.delay(seconds=ELUTION_RESUSPEND_SEC)
    magdeck.engage()

    # =============================================== Step 9: collect eluate
    ctx.delay(seconds=ELUTION_MAGNET_SEC)
    ctx.comment('Step 9: transferring eluates to the 4 C elution plate')
    m300.flow_rate.aspirate = 20
    m300.flow_rate.dispense = 50
    for src, dest in zip(mag_tops, elution_tops):
        m300.pick_up_tip()
        m300.aspirate(ELUTION_VOL, src.bottom(0.5))
        m300.dispense(ELUTION_VOL, dest.bottom(1))
        m300.blow_out(dest.top(-2))
        m300.drop_tip()

    magdeck.disengage()
    ctx.comment('Extraction finished. Eluates are held at 4 C in slot 6.')
