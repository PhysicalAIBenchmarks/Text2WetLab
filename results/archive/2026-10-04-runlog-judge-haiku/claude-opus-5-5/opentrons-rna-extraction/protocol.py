"""OT-2 in-house magnetic-bead SARS-CoV-2 RNA extraction, 48 samples.

Based on: "Automated low-cost SARS-CoV-2 RNA extraction protocols",
PLOS ONE 2021, doi:10.1371/journal.pone.0246302 (OT-2in-house protocol).

 1. Per well: 40 uL magnetic beads, 250 uL isopropanol and 250 uL
    inactivated sample. Mix by pipetting 5 times, incubate 5 min at RT.
 2. Engage the GEN1 magnetic module for 4 min.
 3. Collect the supernatant and discard.
 4. Add 500 uL 70% ethanol, collect and discard.
 5. Add 500 uL 70% ethanol, collect and discard.
 6. Air dry for 4 min.
 7. Disengage the magnet and add 100 uL elution buffer.
 8. After 30 s engage the magnet.
 9. After 90 s collect the eluate and transfer to the elution plate (4 C).
"""
from opentrons import protocol_api

metadata = {
    'protocolName': 'OT-2 in-house magnetic bead RNA extraction (48 samples)',
    'author': 'Based on PLOS ONE 2021 doi:10.1371/journal.pone.0246302',
    'description': 'Magnetic-bead RNA extraction of 48 inactivated samples',
    'apiLevel': '2.15',
}

NUM_SAMPLES = 48

BEAD_VOL = 40
ISOPROPANOL_VOL = 250
SAMPLE_VOL = 250
ETHANOL_VOL = 500
ELUTION_VOL = 100
BINDING_VOL = BEAD_VOL + ISOPROPANOL_VOL + SAMPLE_VOL  # 540 uL

BINDING_INCUBATION_MIN = 5
MAGNET_BINDING_MIN = 4
DRY_MIN = 4
ELUTION_PRE_MAGNET_SEC = 30
ELUTION_MAGNET_SEC = 90

MAX_MULTI_VOL = 200  # 200 uL filter tips


def split_volume(total, max_vol=MAX_MULTI_VOL):
    """Split a volume into equal pipetting steps no larger than max_vol."""
    n = -(-total // max_vol)
    return [total / n] * n


def run(ctx: protocol_api.ProtocolContext):
    # ---------------------------------------------------------------- labware
    waste_plate = ctx.load_labware(
        'usascientific_96_wellplate_2.4ml_deep', '1', 'waste plate')
    tips200 = [ctx.load_labware('opentrons_96_filtertiprack_200ul', slot,
                                '200 uL filter tips')
               for slot in ('2', '3', '9')]
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
    tips1000 = [ctx.load_labware('opentrons_96_filtertiprack_1000ul', '11',
                                 '1000 uL filter tips')]

    # --------------------------------------------------------------- pipettes
    p1000 = ctx.load_instrument('p1000_single_gen2', 'left',
                                tip_racks=tips1000)
    m300 = ctx.load_instrument('p300_multi_gen2', 'right', tip_racks=tips200)

    # ---------------------------------------------------------------- liquids
    beads = reservoir.wells_by_name()['A2']
    elution_buffer = reservoir.wells_by_name()['A4']
    isopropanol = [reservoir.wells_by_name()[w] for w in ('A6', 'A7')]
    ethanol_wash1 = [reservoir.wells_by_name()[w] for w in ('A9', 'A10')]
    ethanol_wash2 = [reservoir.wells_by_name()[w] for w in ('A11', 'A12')]

    # Samples go in the odd columns (1, 3, 5, 7, 9, 11) of the mag plate.
    sample_cols = [1, 3, 5, 7, 9, 11]
    mag_cols = [mag_plate.columns_by_name()[str(c)] for c in sample_cols]
    mag_heads = [col[0] for col in mag_cols]
    mag_wells = [w for col in mag_cols for w in col]  # A1..H1, A3..H3, ...
    waste_heads = [waste_plate.columns_by_name()[str(c)][0]
                   for c in sample_cols]
    elution_heads = [elution_plate.columns_by_name()[str(c)][0]
                     for c in sample_cols]
    sample_tubes = [t for rack in sample_racks for t in rack.wells()]

    # Each reagent column feeds 3 plate columns (24 wells).
    def reagent_for(sources, idx):
        return sources[idx * len(sources) // len(mag_heads)]

    # ------------------------------------------------------------------ setup
    magdeck.disengage()
    tempdeck.set_temperature(4)

    # ---------------------------------------------- step 1: binding mixture
    # Magnetic beads (40 uL) into the empty wells.
    m300.pick_up_tip()
    for dest in mag_heads:
        m300.mix(5, 150, beads.bottom(2))
        m300.aspirate(BEAD_VOL, beads.bottom(2))
        m300.dispense(BEAD_VOL, dest.bottom(2))
        m300.blow_out(dest.top(-2))
    m300.drop_tip()

    # Isopropanol (250 uL), dispensed from the top of the wells.
    m300.pick_up_tip()
    for i, dest in enumerate(mag_heads):
        src = reagent_for(isopropanol, i)
        for vol in split_volume(ISOPROPANOL_VOL):
            m300.aspirate(vol, src.bottom(1))
            m300.dispense(vol, dest.top(-2))
            m300.blow_out(dest.top(-2))
    m300.drop_tip()

    # Samples (250 uL) with the single-channel P1000, mix 5 times.
    for tube, dest in zip(sample_tubes[:NUM_SAMPLES], mag_wells):
        p1000.pick_up_tip()
        p1000.aspirate(SAMPLE_VOL, tube.bottom(2))
        p1000.dispense(SAMPLE_VOL, dest.bottom(2))
        p1000.mix(5, 400, dest.bottom(2))
        p1000.blow_out(dest.top(-2))
        p1000.drop_tip()

    ctx.delay(minutes=BINDING_INCUBATION_MIN,
              msg='Incubating 5 min at room temperature.')

    # ---------------------------------------------- step 2: magnet 4 min
    magdeck.engage()
    ctx.delay(minutes=MAGNET_BINDING_MIN, msg='Separating beads (4 min).')

    # ---------------------------------------- helper: remove supernatant
    def remove_supernatant(volume):
        m300.flow_rate.aspirate = 50
        for src, waste in zip(mag_heads, waste_heads):
            m300.pick_up_tip()
            for vol in split_volume(volume):
                m300.aspirate(vol, src.bottom(1))
                m300.dispense(vol, waste.top(-2))
                m300.blow_out(waste.top(-2))
            m300.drop_tip()
        m300.flow_rate.aspirate = 94

    def add_ethanol(sources):
        m300.pick_up_tip()
        for i, dest in enumerate(mag_heads):
            src = reagent_for(sources, i)
            for vol in split_volume(ETHANOL_VOL):
                m300.aspirate(vol, src.bottom(1))
                m300.dispense(vol, dest.top(-2))
                m300.blow_out(dest.top(-2))
        m300.drop_tip()

    # ---------------------------------------- step 3: discard supernatant
    remove_supernatant(BINDING_VOL)

    # ------------------------------------- steps 4-5: two ethanol washes
    add_ethanol(ethanol_wash1)
    remove_supernatant(ETHANOL_VOL)
    add_ethanol(ethanol_wash2)
    remove_supernatant(ETHANOL_VOL)

    # ------------------------------------------------- step 6: air dry
    ctx.delay(minutes=DRY_MIN, msg='Air drying beads (4 min).')

    # ---------------------------------- step 7: magnet off, elution buffer
    magdeck.disengage()
    for dest in mag_heads:
        m300.pick_up_tip()
        m300.aspirate(ELUTION_VOL, elution_buffer.bottom(1))
        m300.dispense(ELUTION_VOL, dest.bottom(1))
        m300.mix(5, 80, dest.bottom(1))
        m300.blow_out(dest.top(-2))
        m300.drop_tip()

    # ------------------------------------ step 8: 30 s, then magnet on
    ctx.delay(seconds=ELUTION_PRE_MAGNET_SEC, msg='Eluting (30 s).')
    magdeck.engage()

    # ------------------------- step 9: 90 s, transfer eluate to 4 C plate
    ctx.delay(seconds=ELUTION_MAGNET_SEC, msg='Separating beads (90 s).')
    m300.flow_rate.aspirate = 25
    for src, dest in zip(mag_heads, elution_heads):
        m300.pick_up_tip()
        m300.aspirate(ELUTION_VOL, src.bottom(0.5))
        m300.dispense(ELUTION_VOL, dest.bottom(1))
        m300.blow_out(dest.top(-2))
        m300.drop_tip()
    m300.flow_rate.aspirate = 94

    magdeck.disengage()
    ctx.comment('Extraction complete. Eluates are held at 4 C on the '
                'temperature module.')
