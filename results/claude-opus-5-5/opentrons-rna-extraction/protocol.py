"""OT-2 in-house magnetic-bead SARS-CoV-2 RNA extraction (48 samples).

Implements the "OT-2in-house" protocol of Rodriguez-Sanchez et al.,
"Automated low-cost SARS-CoV-2 RNA extraction protocols", PLOS ONE 2021,
doi:10.1371/journal.pone.0246302:

 1. Dispense 40 uL magnetic beads, 250 uL isopropanol and 250 uL inactivated
    sample per well. Mix by pipetting five times; incubate 5 min at RT.
 2. Activate the GEN1 magnetic module for 4 min.
 3. Collect the supernatant and discard.
 4. Add 500 uL 70% ethanol, collect and discard.
 5. Add 500 uL 70% ethanol, collect and discard.
 6. Air dry for 4 min.
 7. Turn off the magnetic module and add 100 uL elution buffer.
 8. After 30 s turn on the magnetic module.
 9. After 90 s collect the supernatant (eluate) and transfer it to a
    96-well plate (kept at 4 C on the temperature module).
"""
import math

from opentrons import protocol_api

metadata = {
    'protocolName': 'OT-2 in-house magnetic bead RNA extraction (48 samples)',
    'author': 'Based on Rodriguez-Sanchez et al., PLOS ONE 2021',
    'description': 'Isopropanol/magnetic bead RNA extraction with two 70% '
                   'ethanol washes on the GEN1 magnetic module',
    'apiLevel': '2.15',
}

NUM_SAMPLES = 48

# Volumes (uL), Table 1 of the paper (OT-2in-house row)
BEAD_VOL = 40
ISOPROPANOL_VOL = 250
SAMPLE_VOL = 250
WASH_VOL = 500
ELUTION_VOL = 100
BINDING_TOTAL = BEAD_VOL + ISOPROPANOL_VOL + SAMPLE_VOL  # 540 uL

# Times
BINDING_INCUBATION_MIN = 5
MAGNET_MIN = 4
DRY_MIN = 4
ELUTION_BEFORE_MAGNET_SEC = 30
ELUTION_MAGNET_SEC = 90

SAMPLE_MIX_REPS = 5
MAX_TIP_VOL = 180  # working volume per trip with 200 uL filter tips


def split(volume, max_vol=MAX_TIP_VOL):
    n = math.ceil(volume / max_vol)
    return [volume / n] * n


def run(ctx: protocol_api.ProtocolContext):
    # ---------------- Labware ----------------
    waste_plate = ctx.load_labware(
        'usascientific_96_wellplate_2.4ml_deep', '1', 'Waste plate')
    tips200 = [ctx.load_labware('opentrons_96_filtertiprack_200ul', slot)
               for slot in ['2', '3', '9']]
    tips1000 = [ctx.load_labware('opentrons_96_filtertiprack_1000ul', '11')]

    mag_mod = ctx.load_module('magnetic module', '4')
    mag_plate = mag_mod.load_labware(
        'usascientific_96_wellplate_2.4ml_deep', 'Extraction plate')

    reservoir = ctx.load_labware('nest_12_reservoir_15ml', '5', 'Reagents')

    temp_mod = ctx.load_module('tempdeck', '6')
    elution_plate = temp_mod.load_labware(
        'thermo_96_wellplate_200ul', 'Elution plate')

    sample_racks = [
        ctx.load_labware('opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap',
                         '10', 'Samples 1-24'),
        ctx.load_labware('opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap',
                         '7', 'Samples 25-48'),
    ]

    # ---------------- Pipettes ----------------
    p1000 = ctx.load_instrument('p1000_single_gen2', 'left',
                                tip_racks=tips1000)
    m300 = ctx.load_instrument('p300_multi_gen2', 'right',
                               tip_racks=tips200)

    # ---------------- Reagents ----------------
    beads = reservoir['A2']
    elution_buffer = reservoir['A4']
    isopropanol = [reservoir['A6'], reservoir['A7']]
    ethanol_wash1 = [reservoir['A9'], reservoir['A10']]
    ethanol_wash2 = [reservoir['A11'], reservoir['A12']]

    # ---------------- Layout ----------------
    sample_cols = [1, 3, 5, 7, 9, 11]
    num_cols = math.ceil(NUM_SAMPLES / 8)
    mag_cols = [mag_plate.columns_by_name()[str(c)][0]
                for c in sample_cols[:num_cols]]
    waste_cols = [waste_plate.columns_by_name()[str(c)][0]
                  for c in sample_cols[:num_cols]]
    elution_cols = [elution_plate.columns_by_name()[str(c)][0]
                    for c in sample_cols[:num_cols]]
    sample_tubes = [tube for rack in sample_racks for tube in rack.wells()]
    dest_wells = [well for c in sample_cols[:num_cols]
                  for well in mag_plate.columns_by_name()[str(c)]]

    def reagent_source(sources, idx):
        # each reservoir column serves 3 plate columns (24 samples)
        return sources[idx * len(sources) // num_cols]

    def remove_supernatant(volume, label):
        ctx.comment(f'Removing {label} ({volume} uL/well) to waste plate')
        m300.flow_rate.aspirate = 30
        for src, dst in zip(mag_cols, waste_cols):
            m300.pick_up_tip()
            for vol in split(volume):
                m300.aspirate(vol, src.bottom(1))
                m300.dispense(vol, dst.top(-2))
                m300.blow_out(dst.top(-2))
            m300.drop_tip()
        m300.flow_rate.aspirate = 94

    def add_reagent(sources, volume, label):
        ctx.comment(f'Adding {volume} uL {label} per well')
        m300.pick_up_tip()
        for i, dst in enumerate(mag_cols):
            src = reagent_source(sources, i)
            for vol in split(volume):
                m300.aspirate(vol, src.bottom(1))
                m300.dispense(vol, dst.top(-2))
                m300.blow_out(dst.top(-2))
        m300.drop_tip()

    # Elution plate kept at 4 C throughout
    temp_mod.set_temperature(4)
    mag_mod.disengage()

    # ===== Step 1: beads + isopropanol + sample, mix, incubate 5 min =====
    ctx.comment(f'Adding {BEAD_VOL} uL magnetic beads per well')
    m300.pick_up_tip()
    m300.mix(10, 150, beads.bottom(1))  # resuspend beads
    for dst in mag_cols:
        m300.aspirate(BEAD_VOL, beads.bottom(1))
        m300.dispense(BEAD_VOL, dst.bottom(2))
        m300.blow_out(dst.bottom(5))
    m300.drop_tip()

    add_reagent(isopropanol, ISOPROPANOL_VOL, 'isopropanol')

    ctx.comment(f'Adding {SAMPLE_VOL} uL sample per well and mixing '
                f'{SAMPLE_MIX_REPS} times')
    for tube, dst in zip(sample_tubes[:NUM_SAMPLES], dest_wells):
        p1000.pick_up_tip()
        p1000.aspirate(SAMPLE_VOL, tube.bottom(1))
        p1000.dispense(SAMPLE_VOL, dst.bottom(2))
        p1000.mix(SAMPLE_MIX_REPS, 400, dst.bottom(2))
        p1000.blow_out(dst.top(-2))
        p1000.drop_tip()

    ctx.delay(minutes=BINDING_INCUBATION_MIN,
              msg='Binding: incubating 5 min at room temperature')

    # ===== Step 2: magnet 4 min =====
    mag_mod.engage()
    ctx.delay(minutes=MAGNET_MIN, msg='Magnetic module engaged 4 min')

    # ===== Step 3: discard supernatant =====
    remove_supernatant(BINDING_TOTAL, 'binding supernatant')

    # ===== Steps 4-5: two washes with 70% ethanol =====
    for n, sources in enumerate([ethanol_wash1, ethanol_wash2], start=1):
        add_reagent(sources, WASH_VOL, f'70% ethanol (wash {n})')
        remove_supernatant(WASH_VOL, f'70% ethanol wash {n}')

    # ===== Step 6: air dry =====
    ctx.delay(minutes=DRY_MIN, msg='Air drying beads 4 min')

    # ===== Step 7: magnet off, add elution buffer =====
    mag_mod.disengage()
    ctx.comment(f'Adding {ELUTION_VOL} uL elution buffer per well')
    for dst in mag_cols:
        m300.pick_up_tip()
        m300.aspirate(ELUTION_VOL, elution_buffer.bottom(1))
        m300.dispense(ELUTION_VOL, dst.bottom(1))
        m300.mix(5, 80, dst.bottom(1))  # resuspend beads
        m300.blow_out(dst.bottom(5))
        m300.drop_tip()

    # ===== Step 8: after 30 s engage magnet =====
    ctx.delay(seconds=ELUTION_BEFORE_MAGNET_SEC,
              msg='Elution: waiting 30 s before engaging magnet')
    mag_mod.engage()

    # ===== Step 9: after 90 s transfer eluate to the 4 C elution plate =====
    ctx.delay(seconds=ELUTION_MAGNET_SEC, msg='Magnet engaged 90 s')
    ctx.comment('Transferring eluate to elution plate (4 C)')
    m300.flow_rate.aspirate = 20
    for src, dst in zip(mag_cols, elution_cols):
        m300.pick_up_tip()
        m300.aspirate(ELUTION_VOL, src.bottom(1))
        m300.dispense(ELUTION_VOL, dst.bottom(1))
        m300.blow_out(dst.top(-2))
        m300.drop_tip()
    m300.flow_rate.aspirate = 94

    mag_mod.disengage()
    ctx.comment('Extraction complete. Elution plate is held at 4 C.')
