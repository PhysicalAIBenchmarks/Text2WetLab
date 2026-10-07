"""
OT-2in-house magnetic-bead RNA extraction, 48 samples.

Lazaro-Perona et al., "Automated low-cost SARS-CoV-2 RNA extraction
protocols", PLOS ONE 2021, doi:10.1371/journal.pone.0246302.

Per sample (Table 1 / OT-2in-house protocol):
 1. 40 uL magnetic beads + 250 uL isopropanol + 250 uL inactivated sample,
    mix by pipetting 5 times, incubate 5 min at room temperature.
 2. Engage GEN1 magnetic module for 4 min.
 3. Collect the supernatant and discard.
 4. Add 500 uL 70% ethanol, collect and discard.
 5. Add 500 uL 70% ethanol, collect and discard.
 6. Air dry 4 min.
 7. Disengage magnet, add 100 uL elution buffer.
 8. After 30 s engage the magnet.
 9. After 90 s collect the eluate and transfer to the 96-well plate (4 C).
"""
import math

metadata = {
    'protocolName': 'OT-2in-house magnetic bead RNA extraction (48 samples)',
    'author': 'Implementation of Lazaro-Perona et al. 2021, PLOS ONE',
    'description': 'Isopropanol/magnetic bead RNA extraction with GEN1 '
                   'magnetic module, two 70% ethanol washes, 100 uL elution',
    'apiLevel': '2.13',
}

NUM_SAMPLES = 48

BEAD_VOL = 40
ISOPROPANOL_VOL = 250
SAMPLE_VOL = 250
SAMPLE_MIX_REPS = 5
BINDING_INCUBATION_MIN = 5
MAGNET_BINDING_MIN = 4
ETHANOL_VOL = 500
DRY_MIN = 4
ELUTION_VOL = 100
ELUTION_PRE_MAGNET_SEC = 30
ELUTION_MAGNET_SEC = 90

MAX_TIP_VOL = 180  # usable volume per trip with 200 uL filter tips


def run(ctx):
    # ---------------------------------------------------------------- labware
    waste_plate = ctx.load_labware(
        'usascientific_96_wellplate_2.4ml_deep', '1', 'supernatant waste')
    tips200 = [ctx.load_labware('opentrons_96_filtertiprack_200ul', s)
               for s in ['2', '3', '9']]
    tips1000 = [ctx.load_labware('opentrons_96_filtertiprack_1000ul', '11')]

    magdeck = ctx.load_module('magnetic module', '4')
    mag_plate = magdeck.load_labware(
        'usascientific_96_wellplate_2.4ml_deep', 'extraction plate')

    reservoir = ctx.load_labware('nest_12_reservoir_15ml', '5', 'reagents')

    tempdeck = ctx.load_module('tempdeck', '6')
    elution_plate = tempdeck.load_labware(
        'thermo_96_wellplate_200ul', 'elution plate')

    sample_racks = [
        ctx.load_labware('opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap',
                         '10', 'samples 1-24'),
        ctx.load_labware('opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap',
                         '7', 'samples 25-48'),
    ]

    # --------------------------------------------------------------- pipettes
    p1000 = ctx.load_instrument('p1000_single_gen2', 'left',
                                tip_racks=tips1000)
    m300 = ctx.load_instrument('p300_multi_gen2', 'right', tip_racks=tips200)

    # ---------------------------------------------------------------- reagents
    beads = reservoir['A2']
    elution_buffer = reservoir['A4']
    isopropanol = [reservoir['A6'], reservoir['A7']]
    ethanol_wash1 = [reservoir['A9'], reservoir['A10']]
    ethanol_wash2 = [reservoir['A11'], reservoir['A12']]

    # ------------------------------------------------------------ sample map
    num_cols = math.ceil(NUM_SAMPLES / 8)
    # odd columns 1, 3, 5, 7, 9, 11 of the extraction plate
    mag_cols = [mag_plate.columns()[i] for i in range(0, 2 * num_cols, 2)]
    mag_heads = [col[0] for col in mag_cols]
    waste_heads = [waste_plate.columns()[i][0]
                   for i in range(0, 2 * num_cols, 2)]
    # eluates go to columns 1-6 of the elution plate
    elution_heads = [elution_plate.columns()[i][0] for i in range(num_cols)]

    sample_tubes = [w for rack in sample_racks for w in rack.wells()]
    dest_wells = [w for col in mag_cols for w in col][:NUM_SAMPLES]

    def reservoir_for(col_idx, sources):
        # split plate columns evenly across the reagent reservoir columns
        per_src = math.ceil(num_cols / len(sources))
        return sources[col_idx // per_src]

    def split(vol, max_vol=MAX_TIP_VOL):
        n = math.ceil(vol / max_vol)
        return [vol / n] * n

    def remove_supernatant(vol, extra=20):
        """Remove liquid from each column (magnet engaged) to the waste."""
        m300.flow_rate.aspirate = 30
        m300.flow_rate.dispense = 150
        for src, dst in zip(mag_heads, waste_heads):
            m300.pick_up_tip()
            trips = split(vol)
            for i, v in enumerate(trips):
                last = i == len(trips) - 1
                asp_vol = v + extra if last else v
                height = 0.8 if last else 1.5
                m300.aspirate(asp_vol, src.bottom(height))
                m300.dispense(asp_vol, dst.top(-3))
                m300.blow_out(dst.top(-3))
            m300.drop_tip()
        m300.flow_rate.aspirate = 92.86
        m300.flow_rate.dispense = 92.86

    def add_reagent(vol, sources, label):
        """Add a reagent to all columns from the top, one tip column."""
        ctx.comment('Adding %s uL %s' % (vol, label))
        m300.pick_up_tip()
        for i, dest in enumerate(mag_heads):
            src = reservoir_for(i, sources)
            for v in split(vol):
                m300.aspirate(v, src.bottom(1))
                m300.air_gap(10)
                m300.dispense(v + 10, dest.top(-2))
                m300.blow_out(dest.top(-2))
        m300.drop_tip()

    # ================================================================ start
    tempdeck.set_temperature(4)
    magdeck.disengage()

    # ---- Step 1: beads, isopropanol and sample ----------------------------
    ctx.comment('Step 1: adding 40 uL magnetic beads')
    m300.pick_up_tip()
    m300.mix(10, 150, beads.bottom(1))
    for dest in mag_heads:
        m300.mix(3, 150, beads.bottom(1))
        m300.aspirate(BEAD_VOL, beads.bottom(1))
        m300.dispense(BEAD_VOL, dest.bottom(2))
        m300.blow_out(dest.top(-2))
    m300.drop_tip()

    add_reagent(ISOPROPANOL_VOL, isopropanol, 'isopropanol')

    ctx.comment('Adding 250 uL sample and mixing 5 times')
    for n, (tube, dest) in enumerate(zip(sample_tubes, dest_wells), start=1):
        ctx.comment('Sample %d: %s -> extraction plate %s -> elution plate %s'
                    % (n, tube.display_name, dest.well_name,
                       elution_plate.columns()[(n - 1) // 8]
                       [(n - 1) % 8].well_name))
        p1000.pick_up_tip()
        p1000.aspirate(SAMPLE_VOL, tube.bottom(2))
        p1000.dispense(SAMPLE_VOL, dest.bottom(2))
        p1000.mix(SAMPLE_MIX_REPS, 400, dest.bottom(2))
        p1000.blow_out(dest.top(-2))
        p1000.drop_tip()

    ctx.comment('Incubating 5 min at room temperature')
    ctx.delay(minutes=BINDING_INCUBATION_MIN)

    # ---- Step 2: magnet 4 min ---------------------------------------------
    magdeck.engage()
    ctx.delay(minutes=MAGNET_BINDING_MIN, msg='Magnetic separation 4 min')

    # ---- Step 3: collect supernatant and discard --------------------------
    remove_supernatant(BEAD_VOL + ISOPROPANOL_VOL + SAMPLE_VOL)

    # ---- Steps 4-5: two 70% ethanol washes (magnet engaged) --------------
    for wash, sources in enumerate([ethanol_wash1, ethanol_wash2], start=1):
        ctx.comment('Wash %d: 500 uL 70%% ethanol' % wash)
        add_reagent(ETHANOL_VOL, sources, '70% ethanol')
        remove_supernatant(ETHANOL_VOL)

    # ---- Step 6: air dry --------------------------------------------------
    ctx.delay(minutes=DRY_MIN, msg='Air drying beads 4 min')

    # ---- Step 7: magnet off, add elution buffer ---------------------------
    magdeck.disengage()
    ctx.comment('Adding 100 uL elution buffer and resuspending beads')
    for dest in mag_heads:
        m300.pick_up_tip()
        m300.aspirate(ELUTION_VOL, elution_buffer.bottom(1))
        m300.dispense(ELUTION_VOL, dest.bottom(1))
        m300.mix(5, 80, dest.bottom(1))
        m300.blow_out(dest.top(-2))
        m300.drop_tip()

    # ---- Step 8: after 30 s engage magnet ----------------------------------
    ctx.delay(seconds=ELUTION_PRE_MAGNET_SEC)
    magdeck.engage()

    # ---- Step 9: after 90 s transfer eluate to elution plate --------------
    ctx.delay(seconds=ELUTION_MAGNET_SEC)
    m300.flow_rate.aspirate = 20
    for src, dest in zip(mag_heads, elution_heads):
        m300.pick_up_tip()
        m300.aspirate(ELUTION_VOL, src.bottom(0.8))
        m300.dispense(ELUTION_VOL, dest.bottom(1))
        m300.blow_out(dest.top(-2))
        m300.drop_tip()
    m300.flow_rate.aspirate = 92.86

    magdeck.disengage()
    ctx.comment('Extraction finished. Eluates are in columns 1-%d of the '
                'elution plate, held at 4 C.' % num_cols)
