"""
OT-2 in-house magnetic-bead SARS-CoV-2 RNA extraction, 48 samples.

Based on Lazaro-Perona et al., "Automated low-cost SARS-CoV-2 RNA extraction
protocols", PLOS ONE 2021 (doi:10.1371/journal.pone.0246302), OT-2in-house:

 1. 40 uL magnetic beads + 250 uL isopropanol + 250 uL inactivated sample per
    well; mix by pipetting 5x; incubate 5 min at room temperature.
 2. Engage the GEN1 magnetic module for 4 min.
 3. Collect the supernatant and discard.
 4. Add 500 uL 70% ethanol, collect and discard.
 5. Add 500 uL 70% ethanol, collect and discard.
 6. Air dry 4 min.
 7. Disengage the magnet, add 100 uL elution buffer.
 8. After 30 s engage the magnet.
 9. After 90 s collect the eluate into a 96-well plate (kept at 4 C).
"""
from opentrons import protocol_api

metadata = {
    'protocolName': 'OT-2 in-house magnetic bead RNA extraction (48 samples)',
    'author': 'Implementation of Lazaro-Perona et al., PLOS ONE 2021',
    'description': 'Isopropanol/magnetic bead RNA extraction with two 70% '
                   'ethanol washes and elution into a 4 C plate.',
    'apiLevel': '2.15',
}

NUM_SAMPLES = 48

SAMPLE_VOL = 250
BEAD_VOL = 40
ISOPROPANOL_VOL = 250
BINDING_VOL = SAMPLE_VOL + BEAD_VOL + ISOPROPANOL_VOL  # 540 uL supernatant
ETHANOL_VOL = 500
ELUTION_VOL = 100
ELUATE_VOL = 95  # leave a few uL behind so beads are not carried over

INCUBATION_MIN = 5
MAGNET_MIN = 4
DRY_MIN = 4
ELUTION_WAIT_SEC = 30
ELUTION_MAGNET_SEC = 90

MAX_TIP_VOL = 180  # working volume for 200 uL filter tips


def run(ctx: protocol_api.ProtocolContext):
    # ---------------- labware ----------------
    waste_plate = ctx.load_labware(
        'usascientific_96_wellplate_2.4ml_deep', '1', 'supernatant waste')
    tips200 = [ctx.load_labware('opentrons_96_filtertiprack_200ul', slot)
               for slot in ['2', '3', '9']]
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

    # ---------------- pipettes ----------------
    p1000 = ctx.load_instrument('p1000_single_gen2', 'left',
                                tip_racks=tips1000)
    m300 = ctx.load_instrument('p300_multi_gen2', 'right', tip_racks=tips200)

    # ---------------- reagents ----------------
    beads = reservoir['A2']
    elution_buffer = reservoir['A4']
    isopropanol = [reservoir['A6'], reservoir['A7']]
    ethanol_wash1 = [reservoir['A9'], reservoir['A10']]
    ethanol_wash2 = [reservoir['A11'], reservoir['A12']]

    # ---------------- sample layout ----------------
    sample_cols = [1, 3, 5, 7, 9, 11]  # odd columns of the extraction plate
    num_cols = NUM_SAMPLES // 8
    mag_cols = [mag_plate.columns_by_name()[str(c)][0]
                for c in sample_cols[:num_cols]]
    waste_cols = [waste_plate.columns_by_name()[str(c)][0]
                  for c in sample_cols[:num_cols]]
    elution_cols = [elution_plate.columns_by_name()[str(c)][0]
                    for c in sample_cols[:num_cols]]
    # one well per sample, column-wise (A1..H1 = samples 1-8, A3..H3 = 9-16...)
    sample_dest_wells = [w for c in sample_cols[:num_cols]
                         for w in mag_plate.columns_by_name()[str(c)]]
    sample_tubes = [t for rack in sample_racks for t in rack.wells()]
    sample_tubes = sample_tubes[:NUM_SAMPLES]

    def reagent_source(sources, col_index):
        # first half of the columns from the first trough, rest from the second
        per_source = -(-num_cols // len(sources))
        return sources[col_index // per_source]

    def split(volume):
        n = -(-volume // MAX_TIP_VOL)
        return [volume / n] * int(n)

    def remove_supernatant(volume, label):
        ctx.comment('Removing %s (%d uL per well) to waste' % (label, volume))
        m300.flow_rate.aspirate = 30
        for src, dest in zip(mag_cols, waste_cols):
            m300.pick_up_tip()
            for vol in split(volume):
                m300.aspirate(vol, src.bottom(1))
                m300.dispense(vol, dest.top(-2))
                m300.blow_out(dest.top(-2))
            m300.drop_tip()
        m300.flow_rate.aspirate = 94

    def add_ethanol(sources):
        m300.pick_up_tip()
        for i, dest in enumerate(mag_cols):
            src = reagent_source(sources, i)
            for vol in split(ETHANOL_VOL):
                m300.aspirate(vol, src.bottom(1))
                m300.dispense(vol, dest.top(-2))
                m300.blow_out(dest.top(-2))
        m300.drop_tip()

    # keep eluates cold
    tempdeck.set_temperature(4)
    magdeck.disengage()

    # ---------- Step 1: beads + isopropanol + sample, mix, incubate ----------
    ctx.comment('Dispensing %d uL magnetic beads' % BEAD_VOL)
    m300.pick_up_tip()
    for dest in mag_cols:
        m300.mix(5, 150, beads.bottom(1))  # keep beads in suspension
        m300.aspirate(BEAD_VOL, beads.bottom(1))
        m300.dispense(BEAD_VOL, dest.bottom(2))
        m300.blow_out(dest.top(-2))
    m300.drop_tip()

    ctx.comment('Dispensing %d uL isopropanol' % ISOPROPANOL_VOL)
    m300.pick_up_tip()
    for i, dest in enumerate(mag_cols):
        src = reagent_source(isopropanol, i)
        for vol in split(ISOPROPANOL_VOL):
            m300.aspirate(vol, src.bottom(1))
            m300.dispense(vol, dest.top(-2))
            m300.blow_out(dest.top(-2))
    m300.drop_tip()

    ctx.comment('Adding %d uL of each sample and mixing 5 times' % SAMPLE_VOL)
    for tube, dest in zip(sample_tubes, sample_dest_wells):
        p1000.pick_up_tip()
        p1000.aspirate(SAMPLE_VOL, tube.bottom(2))
        p1000.dispense(SAMPLE_VOL, dest.bottom(3))
        p1000.mix(5, 400, dest.bottom(2))
        p1000.blow_out(dest.top(-2))
        p1000.drop_tip()

    ctx.delay(minutes=INCUBATION_MIN,
              msg='Incubating %d min at room temperature' % INCUBATION_MIN)

    # ---------- Step 2: magnet 4 min ----------
    magdeck.engage()
    ctx.delay(minutes=MAGNET_MIN,
              msg='Magnetic separation %d min' % MAGNET_MIN)

    # ---------- Step 3: discard supernatant ----------
    remove_supernatant(BINDING_VOL, 'binding supernatant')

    # ---------- Steps 4-5: two 70% ethanol washes (magnet engaged) ----------
    for n, sources in enumerate([ethanol_wash1, ethanol_wash2], start=1):
        ctx.comment('Ethanol 70%% wash %d' % n)
        add_ethanol(sources)
        remove_supernatant(ETHANOL_VOL, 'ethanol wash %d' % n)

    # ---------- Step 6: air dry ----------
    ctx.delay(minutes=DRY_MIN, msg='Air drying beads %d min' % DRY_MIN)

    # ---------- Step 7: magnet off, add elution buffer ----------
    magdeck.disengage()
    ctx.comment('Adding %d uL elution buffer' % ELUTION_VOL)
    for dest in mag_cols:
        m300.pick_up_tip()
        m300.aspirate(ELUTION_VOL, elution_buffer.bottom(1))
        m300.dispense(ELUTION_VOL, dest.bottom(1))
        m300.mix(5, 80, dest.bottom(1))  # resuspend the beads
        m300.blow_out(dest.top(-2))
        m300.drop_tip()

    # ---------- Step 8: after 30 s, magnet on ----------
    ctx.delay(seconds=ELUTION_WAIT_SEC, msg='Elution %d s' % ELUTION_WAIT_SEC)
    magdeck.engage()

    # ---------- Step 9: after 90 s, recover eluate ----------
    ctx.delay(seconds=ELUTION_MAGNET_SEC,
              msg='Magnetic separation %d s' % ELUTION_MAGNET_SEC)
    ctx.comment('Transferring eluates to the 4 C elution plate')
    m300.flow_rate.aspirate = 20
    for src, dest in zip(mag_cols, elution_cols):
        m300.pick_up_tip()
        m300.aspirate(ELUATE_VOL, src.bottom(1))
        m300.dispense(ELUATE_VOL, dest.bottom(1))
        m300.blow_out(dest.top(-2))
        m300.drop_tip()
    m300.flow_rate.aspirate = 94

    magdeck.disengage()
    ctx.comment('Extraction finished. Eluates are held at 4 C on slot 6.')
