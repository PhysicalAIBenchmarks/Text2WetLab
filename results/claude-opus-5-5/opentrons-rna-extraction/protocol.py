"""OT-2 in-house magnetic-bead SARS-CoV-2 RNA extraction (48 samples).

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
 9. After 90 s collect the eluate into the elution plate (kept at 4 C).
"""
from opentrons import protocol_api

metadata = {
    'protocolName': 'OT-2 in-house magnetic bead RNA extraction (48 samples)',
    'author': 'Implementation of Lazaro-Perona et al. PLOS ONE 2021',
    'description': 'Isopropanol/magnetic bead RNA extraction, 2x 70% ethanol '
                   'washes, elution in 100 uL; elution plate held at 4 C.',
    'apiLevel': '2.13',
}

NUM_SAMPLES = 48

SAMPLE_VOL = 250
BEAD_VOL = 40
ISOPROPANOL_VOL = 250
ETHANOL_VOL = 500
ELUTION_VOL = 100
BINDING_VOL = SAMPLE_VOL + BEAD_VOL + ISOPROPANOL_VOL  # 540 uL

SAMPLE_MIX_REPS = 5
BINDING_INCUBATION_MIN = 5
MAGNET_BINDING_MIN = 4
AIR_DRY_MIN = 4
ELUTION_RESUSPEND_SEC = 30
ELUTION_MAGNET_SEC = 90

MAX_TIP_VOL = 180  # working volume per stroke with 200 uL filter tips


def run(ctx: protocol_api.ProtocolContext):
    # ----------------------------------------------------------- labware
    waste_plate = ctx.load_labware(
        'usascientific_96_wellplate_2.4ml_deep', '1', 'Waste plate')
    tips200 = [ctx.load_labware('opentrons_96_filtertiprack_200ul', slot)
               for slot in ['2', '3', '9']]
    tips1000 = [ctx.load_labware('opentrons_96_filtertiprack_1000ul', '11')]

    magdeck = ctx.load_module('magnetic module', '4')
    mag_plate = magdeck.load_labware(
        'usascientific_96_wellplate_2.4ml_deep', 'Extraction plate')
    magdeck.disengage()

    reservoir = ctx.load_labware('nest_12_reservoir_15ml', '5', 'Reagents')

    tempdeck = ctx.load_module('tempdeck', '6')
    elution_plate = tempdeck.load_labware(
        'thermo_96_wellplate_200ul', 'Elution plate')

    sample_racks = [
        ctx.load_labware('opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap',
                         '10', 'Samples 1-24'),
        ctx.load_labware('opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap',
                         '7', 'Samples 25-48'),
    ]

    # ----------------------------------------------------------- pipettes
    p1000 = ctx.load_instrument('p1000_single_gen2', 'left',
                                tip_racks=tips1000)
    m300 = ctx.load_instrument('p300_multi_gen2', 'right',
                               tip_racks=tips200)

    # ----------------------------------------------------------- reagents
    beads = reservoir.wells_by_name()['A2']
    elution_buffer = reservoir.wells_by_name()['A4']
    isopropanol = [reservoir.wells_by_name()[w] for w in ['A6', 'A7']]
    ethanol = [reservoir.wells_by_name()[w]
               for w in ['A9', 'A10', 'A11', 'A12']]

    # ----------------------------------------------------------- layout
    sample_cols = [1, 3, 5, 7, 9, 11]
    num_cols = NUM_SAMPLES // 8
    mag_cols = [mag_plate.columns_by_name()[str(c)] for c in sample_cols]
    mag_heads = [col[0] for col in mag_cols][:num_cols]
    waste_heads = [waste_plate.columns_by_name()[str(c)][0]
                   for c in sample_cols][:num_cols]
    # each eluate goes to the same well position in the elution plate
    elution_heads = [elution_plate.columns_by_name()[str(c)][0]
                     for c in sample_cols][:num_cols]

    sample_tubes = [tube for rack in sample_racks for tube in rack.wells()]
    sample_dests = [well for col in mag_cols for well in col]

    # Elution plate kept cold for the whole run
    tempdeck.set_temperature(4)

    def strokes(total):
        """Split a volume into equal strokes that fit a 200 uL filter tip."""
        n = -(-total // MAX_TIP_VOL)
        return [total / n] * n

    def remove_supernatant(volume, label):
        """With the magnet engaged, collect liquid and discard to waste."""
        ctx.comment('Removing {} to waste plate'.format(label))
        m300.flow_rate.aspirate = 30
        for src, dst in zip(mag_heads, waste_heads):
            m300.pick_up_tip()
            for vol in strokes(volume):
                m300.aspirate(vol, src.bottom(1))
                m300.dispense(vol, dst.top(-2))
                m300.blow_out(dst.top(-2))
            m300.drop_tip()
        m300.flow_rate.aspirate = 94

    def add_ethanol(wash_index):
        ctx.comment('Wash {}: adding {} uL 70% ethanol'.format(
            wash_index + 1, ETHANOL_VOL))
        m300.pick_up_tip()
        for i, dst in enumerate(mag_heads):
            src = ethanol[(wash_index * num_cols + i) // 3]
            for vol in strokes(ETHANOL_VOL):
                m300.aspirate(vol, src.bottom(1))
                m300.dispense(vol, dst.top(-2))
                m300.blow_out(dst.top(-2))
        m300.drop_tip()

    # =================================================== Step 1: binding mix
    # 40 uL magnetic beads (resuspended first) into each sample well
    ctx.comment('Adding {} uL magnetic beads'.format(BEAD_VOL))
    m300.pick_up_tip()
    m300.mix(10, 150, beads.bottom(2))
    for dst in mag_heads:
        m300.aspirate(BEAD_VOL, beads.bottom(1))
        m300.dispense(BEAD_VOL, dst.bottom(2))
        m300.blow_out(dst.top(-2))
    m300.drop_tip()

    # 250 uL isopropanol
    ctx.comment('Adding {} uL isopropanol'.format(ISOPROPANOL_VOL))
    m300.pick_up_tip()
    for i, dst in enumerate(mag_heads):
        src = isopropanol[i // 3]
        for vol in strokes(ISOPROPANOL_VOL):
            m300.aspirate(vol, src.bottom(1))
            m300.dispense(vol, dst.top(-2))
            m300.blow_out(dst.top(-2))
    m300.drop_tip()

    # 250 uL inactivated sample, mixed 5 times by pipetting
    ctx.comment('Adding {} uL sample and mixing {}x'.format(
        SAMPLE_VOL, SAMPLE_MIX_REPS))
    for src, dst in zip(sample_tubes[:NUM_SAMPLES], sample_dests):
        p1000.pick_up_tip()
        p1000.aspirate(SAMPLE_VOL, src.bottom(2))
        p1000.dispense(SAMPLE_VOL, dst.bottom(2))
        p1000.mix(SAMPLE_MIX_REPS, 400, dst.bottom(2))
        p1000.blow_out(dst.top(-2))
        p1000.drop_tip()

    ctx.delay(minutes=BINDING_INCUBATION_MIN,
              msg='Incubating binding mix 5 min at room temperature')

    # =================================================== Step 2: magnet
    magdeck.engage()
    ctx.delay(minutes=MAGNET_BINDING_MIN,
              msg='Magnetic module engaged for 4 min')

    # =================================================== Step 3: discard
    remove_supernatant(BINDING_VOL, 'binding supernatant')

    # =================================================== Steps 4-5: washes
    for wash in range(2):
        add_ethanol(wash)
        remove_supernatant(ETHANOL_VOL, 'ethanol wash {}'.format(wash + 1))

    # =================================================== Step 6: air dry
    ctx.delay(minutes=AIR_DRY_MIN, msg='Air drying beads for 4 min')

    # =================================================== Step 7: elution
    magdeck.disengage()
    ctx.comment('Adding {} uL elution buffer'.format(ELUTION_VOL))
    for dst in mag_heads:
        m300.pick_up_tip()
        m300.aspirate(ELUTION_VOL, elution_buffer.bottom(1))
        m300.dispense(ELUTION_VOL, dst.bottom(1))
        m300.mix(5, 80, dst.bottom(1))  # resuspend the dried beads
        m300.blow_out(dst.bottom(5))
        m300.drop_tip()

    # =================================================== Step 8: magnet
    ctx.delay(seconds=ELUTION_RESUSPEND_SEC,
              msg='Beads in elution buffer for 30 s')
    magdeck.engage()

    # =================================================== Step 9: recover
    ctx.delay(seconds=ELUTION_MAGNET_SEC,
              msg='Magnetic module engaged for 90 s')
    ctx.comment('Transferring eluates to the elution plate (4 C)')
    m300.flow_rate.aspirate = 20
    for src, dst in zip(mag_heads, elution_heads):
        m300.pick_up_tip()
        m300.aspirate(ELUTION_VOL, src.bottom(1))
        m300.dispense(ELUTION_VOL, dst.bottom(1))
        m300.blow_out(dst.top(-2))
        m300.drop_tip()

    magdeck.disengage()
    ctx.comment('Extraction finished. Eluates are on the 4 C elution plate.')
