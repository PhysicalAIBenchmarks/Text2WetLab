"""
OT-2 in-house magnetic-bead SARS-CoV-2 RNA extraction, 48 samples.

Based on: Automated low-cost SARS-CoV-2 RNA extraction protocols,
PLOS ONE 2021, doi:10.1371/journal.pone.0246302 (OT-2in-house protocol).

1. 40 uL magnetic beads + 250 uL isopropanol + 250 uL inactivated sample,
   mix 5x, incubate 5 min at room temperature.
2. Engage GEN1 magnetic module for 4 min.
3. Collect the supernatant and discard.
4. Add 500 uL 70% ethanol, collect and discard.
5. Add 500 uL 70% ethanol, collect and discard.
6. Air dry 4 min.
7. Disengage magnet, add 100 uL elution buffer.
8. After 30 s engage magnet.
9. After 90 s collect the eluate and transfer to the elution plate (4 C).
"""
from opentrons import protocol_api

metadata = {
    'protocolName': 'OT-2 in-house magnetic bead RNA extraction (48 samples)',
    'author': 'Based on PLOS ONE 2021 doi:10.1371/journal.pone.0246302',
    'description': 'Magnetic-bead SARS-CoV-2 RNA extraction for 48 samples',
    'apiLevel': '2.13',
}

NUM_SAMPLES = 48
BEAD_VOL = 40
ISOPROPANOL_VOL = 250
SAMPLE_VOL = 250
ETHANOL_VOL = 500
ELUTION_VOL = 100
BINDING_TOTAL_VOL = BEAD_VOL + ISOPROPANOL_VOL + SAMPLE_VOL  # 540 uL

BINDING_INCUBATION_MIN = 5
MAGNET_BINDING_MIN = 4
AIR_DRY_MIN = 4
ELUTION_RESUSPEND_SEC = 30
ELUTION_MAGNET_SEC = 90

MULTI_MAX = 180  # working volume per trip with 200 uL filter tips


def run(ctx: protocol_api.ProtocolContext):
    # ---------------- labware ----------------
    waste_plate = ctx.load_labware(
        'usascientific_96_wellplate_2.4ml_deep', '1', 'waste plate')
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

    tube_racks = [
        ctx.load_labware(
            'opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', '10',
            'samples 1-24'),
        ctx.load_labware(
            'opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', '7',
            'samples 25-48'),
    ]

    # ---------------- pipettes ----------------
    p1000 = ctx.load_instrument('p1000_single_gen2', 'left',
                                tip_racks=tips1000)
    m300 = ctx.load_instrument('p300_multi_gen2', 'right',
                               tip_racks=tips200)

    # ---------------- reagents ----------------
    beads = reservoir.wells_by_name()['A2']
    elution_buffer = reservoir.wells_by_name()['A4']
    isopropanol = [reservoir.wells_by_name()[w] for w in ['A6', 'A7']]
    ethanol_wash1 = [reservoir.wells_by_name()[w] for w in ['A9', 'A10']]
    ethanol_wash2 = [reservoir.wells_by_name()[w] for w in ['A11', 'A12']]

    # ---------------- sample layout ----------------
    num_cols = NUM_SAMPLES // 8
    odd_col_idx = [0, 2, 4, 6, 8, 10][:num_cols]  # columns 1,3,5,7,9,11
    mag_cols = [mag_plate.columns()[i] for i in odd_col_idx]
    mag_heads = [col[0] for col in mag_cols]
    elution_heads = [elution_plate.columns()[i][0] for i in odd_col_idx]
    waste_heads = [waste_plate.columns()[i][0] for i in odd_col_idx]

    sample_tubes = tube_racks[0].wells() + tube_racks[1].wells()
    dest_wells = [well for col in mag_cols for well in col]

    # keep eluates cold during the run
    tempdeck.set_temperature(4)
    magdeck.disengage()

    def split(vol, max_vol=MULTI_MAX):
        n = -(-vol // max_vol)
        base = vol / n
        return [base] * n

    def remove_liquid(vol, label):
        """Remove liquid from every sample column (magnet engaged) to waste."""
        m300.flow_rate.aspirate = 30
        for src, dst in zip(mag_heads, waste_heads):
            m300.pick_up_tip()
            for v in split(vol):
                m300.aspirate(v, src.bottom(1))
                m300.dispense(v, dst.top(-2))
                m300.blow_out(dst.top(-2))
            m300.drop_tip()
        m300.flow_rate.aspirate = 94
        ctx.comment('{} removed to waste plate'.format(label))

    def add_reagent(vol, sources, label):
        """Add reagent to all sample columns with a single tip column,
        dispensing from the top so the tips do not touch sample."""
        m300.pick_up_tip()
        per_source = -(-len(mag_heads) // len(sources))
        for i, dst in enumerate(mag_heads):
            src = sources[i // per_source]
            for v in split(vol):
                m300.aspirate(v, src.bottom(1))
                m300.dispense(v, dst.top(-2))
                m300.blow_out(dst.top(-2))
        m300.drop_tip()
        ctx.comment('{} added'.format(label))

    # ============ Step 1: binding mix ============
    # magnetic beads (resuspend beads first)
    m300.pick_up_tip()
    m300.mix(10, 150, beads.bottom(1))
    for dst in mag_heads:
        m300.aspirate(BEAD_VOL, beads.bottom(1))
        m300.dispense(BEAD_VOL, dst.bottom(2))
        m300.blow_out(dst.top(-2))
    m300.drop_tip()

    # isopropanol
    add_reagent(ISOPROPANOL_VOL, isopropanol, 'Isopropanol')

    # samples, then mix the whole binding mix 5 times
    for tube, dst in zip(sample_tubes[:NUM_SAMPLES], dest_wells):
        p1000.pick_up_tip()
        p1000.aspirate(SAMPLE_VOL, tube.bottom(2))
        p1000.dispense(SAMPLE_VOL, dst.bottom(2))
        p1000.mix(5, 400, dst.bottom(2))
        p1000.blow_out(dst.top(-2))
        p1000.drop_tip()

    ctx.delay(minutes=BINDING_INCUBATION_MIN,
              msg='Incubating binding mix at room temperature')

    # ============ Step 2-3: capture beads, discard supernatant ============
    magdeck.engage()
    ctx.delay(minutes=MAGNET_BINDING_MIN, msg='Magnetic bead capture')
    remove_liquid(BINDING_TOTAL_VOL, 'Supernatant')

    # ============ Step 4-5: two 70% ethanol washes ============
    for wash_sources, label in [(ethanol_wash1, 'Ethanol wash 1'),
                                (ethanol_wash2, 'Ethanol wash 2')]:
        add_reagent(ETHANOL_VOL, wash_sources, label)
        remove_liquid(ETHANOL_VOL, label)

    # ============ Step 6: air dry ============
    ctx.delay(minutes=AIR_DRY_MIN, msg='Air drying beads')

    # ============ Step 7: elution ============
    magdeck.disengage()
    for dst in mag_heads:
        m300.pick_up_tip()
        m300.aspirate(ELUTION_VOL, elution_buffer.bottom(1))
        m300.dispense(ELUTION_VOL, dst.bottom(1))
        m300.mix(5, 80, dst.bottom(1))
        m300.blow_out(dst.bottom(5))
        m300.drop_tip()

    # ============ Step 8: magnet on after 30 s ============
    ctx.delay(seconds=ELUTION_RESUSPEND_SEC, msg='Elution')
    magdeck.engage()

    # ============ Step 9: after 90 s recover eluate ============
    ctx.delay(seconds=ELUTION_MAGNET_SEC, msg='Separating beads from eluate')
    m300.flow_rate.aspirate = 20
    for src, dst in zip(mag_heads, elution_heads):
        m300.pick_up_tip()
        m300.aspirate(ELUTION_VOL, src.bottom(0.5))
        m300.dispense(ELUTION_VOL, dst.bottom(1))
        m300.blow_out(dst.top(-2))
        m300.drop_tip()

    magdeck.disengage()
    ctx.comment('Extraction complete. Eluates are held at 4 C on the '
                'temperature module.')
