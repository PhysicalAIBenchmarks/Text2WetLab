"""OT-2 in-house magnetic-bead SARS-CoV-2 RNA extraction, 48 samples.

Implements the "OT-2in-house" protocol of Pérez-Pérez et al., PLOS ONE 2021
(doi:10.1371/journal.pone.0246302):

  1. Per well: 40 uL magnetic beads + 250 uL isopropanol + 250 uL inactivated
     sample. Mix by pipetting five times, incubate 5 min at room temperature.
  2. Activate the GEN1 magnetic module for 4 min.
  3. Collect the supernatant and discard.
  4. Add 500 uL 70% ethanol, collect and discard.
  5. Add 500 uL 70% ethanol, collect and discard.
  6. Air dry for 4 min.
  7. Turn off the magnetic module and add 100 uL elution buffer.
  8. After 30 s turn on the magnetic module.
  9. After 90 s collect the supernatant (eluate) and transfer it to a
     96-well microtiter plate (kept at 4 C on the temperature module).

Samples occupy the odd columns (1, 3, 5, 7, 9, 11) of the deep-well plate on
the magnetic module. Eluates go to the same well positions of the elution
plate; supernatants/washes go to the same well positions of the waste plate.
"""
from opentrons import protocol_api

metadata = {
    'protocolName': 'OT-2 in-house magnetic bead RNA extraction (48 samples)',
    'author': 'Based on Perez-Perez et al., PLOS ONE 2021; 16(2): e0246302',
    'description': 'Isopropanol/magnetic bead RNA extraction, 2x 70% ethanol '
                   'washes, elution in 100 uL elution buffer.',
    'apiLevel': '2.13',
}

# ---------------------------------------------------------------- parameters
NUM_SAMPLES = 48
BEAD_VOL = 40
ISOPROPANOL_VOL = 250
SAMPLE_VOL = 250
WASH_VOL = 500
ELUTION_VOL = 100
SUPERNATANT_VOL = BEAD_VOL + ISOPROPANOL_VOL + SAMPLE_VOL  # 540 uL

BINDING_INCUBATION_MIN = 5
MAGNET_BINDING_MIN = 4
DRY_MIN = 4
ELUTION_OFF_SEC = 30
ELUTION_MAGNET_SEC = 90

MAX_MULTI_VOL = 180   # working volume for 200 uL filter tips (air gap room)
ASPIRATE_HEIGHT = 1.0  # mm above well bottom when removing supernatant


def _split(total, max_vol):
    """Split a volume into equal transfers no larger than max_vol."""
    n = -(-total // max_vol)
    return [total / n] * n


def run(ctx: protocol_api.ProtocolContext):
    # ------------------------------------------------------------- labware
    waste_plate = ctx.load_labware(
        'usascientific_96_wellplate_2.4ml_deep', '1', 'Waste plate')
    tips200 = [ctx.load_labware('opentrons_96_filtertiprack_200ul', slot)
               for slot in ['2', '3', '9']]
    tips1000 = [ctx.load_labware('opentrons_96_filtertiprack_1000ul', '11')]

    magdeck = ctx.load_module('magnetic module', '4')
    mag_plate = magdeck.load_labware(
        'usascientific_96_wellplate_2.4ml_deep', 'Extraction plate')

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

    # ------------------------------------------------------------ pipettes
    p1000 = ctx.load_instrument('p1000_single_gen2', 'left',
                                tip_racks=tips1000)
    m300 = ctx.load_instrument('p300_multi_gen2', 'right', tip_racks=tips200)

    # ------------------------------------------------------------- reagents
    beads = reservoir.wells_by_name()['A2']
    elution_buffer = reservoir.wells_by_name()['A4']
    isopropanol = [reservoir.wells_by_name()[w] for w in ['A6', 'A7']]
    ethanol = [reservoir.wells_by_name()[w] for w in ['A9', 'A10', 'A11', 'A12']]

    # --------------------------------------------------------- sample layout
    sample_cols = [1, 3, 5, 7, 9, 11]
    mag_cols = [mag_plate.columns_by_name()[str(c)] for c in sample_cols]
    mag_heads = [col[0] for col in mag_cols]
    waste_heads = [waste_plate.columns_by_name()[str(c)][0] for c in sample_cols]
    elution_heads = [elution_plate.columns_by_name()[str(c)][0]
                     for c in sample_cols]
    sample_dest = [well for col in mag_cols for well in col][:NUM_SAMPLES]
    sample_tubes = [tube for rack in sample_racks for tube in rack.wells()]

    # Each isopropanol column (6 mL needed) serves 3 sample columns; each
    # ethanol column (12 mL needed) serves 3 sample columns for one wash.
    def isopropanol_for(i):
        return isopropanol[i // 3]

    def ethanol_for(wash, i):
        return ethanol[wash * 2 + i // 3]

    # --------------------------------------------------------- start state
    tempdeck.set_temperature(4)
    if magdeck.status == 'engaged':
        magdeck.disengage()

    # ---------------------------------------------------------- helpers
    def remove_supernatant(vol, label):
        ctx.comment(f'Removing {vol} uL {label} to waste plate')
        m300.flow_rate.aspirate = 30
        for src, dst in zip(mag_heads, waste_heads):
            m300.pick_up_tip()
            for v in _split(vol, MAX_MULTI_VOL):
                m300.aspirate(v, src.bottom(ASPIRATE_HEIGHT))
                m300.air_gap(10)
                m300.dispense(v + 10, dst.top(-2))
                m300.blow_out(dst.top(-2))
            m300.drop_tip()
        m300.flow_rate.aspirate = 94

    def add_ethanol(wash):
        ctx.comment(f'Wash {wash + 1}: adding {WASH_VOL} uL 70% ethanol')
        m300.pick_up_tip()
        for i, dst in enumerate(mag_heads):
            src = ethanol_for(wash, i)
            for v in _split(WASH_VOL, MAX_MULTI_VOL):
                m300.aspirate(v, src)
                m300.dispense(v, dst.top(-2))
                m300.blow_out(dst.top(-2))
        m300.drop_tip()

    # ======================== Step 1: beads + isopropanol + sample, mix ====
    ctx.comment(f'Step 1: adding {BEAD_VOL} uL magnetic beads')
    m300.pick_up_tip()
    m300.mix(10, 150, beads)
    for dst in mag_heads:
        m300.aspirate(BEAD_VOL, beads)
        m300.dispense(BEAD_VOL, dst.bottom(2))
        m300.blow_out(dst.top(-2))
    m300.drop_tip()

    ctx.comment(f'Step 1: adding {ISOPROPANOL_VOL} uL isopropanol')
    m300.pick_up_tip()
    for i, dst in enumerate(mag_heads):
        for v in _split(ISOPROPANOL_VOL, MAX_MULTI_VOL):
            m300.aspirate(v, isopropanol_for(i))
            m300.dispense(v, dst.top(-2))
            m300.blow_out(dst.top(-2))
    m300.drop_tip()

    ctx.comment(f'Step 1: adding {SAMPLE_VOL} uL sample and mixing 5 times')
    for tube, dst in zip(sample_tubes[:NUM_SAMPLES], sample_dest):
        p1000.pick_up_tip()
        p1000.aspirate(SAMPLE_VOL, tube.bottom(2))
        p1000.dispense(SAMPLE_VOL, dst.bottom(2))
        p1000.mix(5, 400, dst.bottom(2))
        p1000.blow_out(dst.top(-2))
        p1000.drop_tip()

    ctx.comment('Incubating 5 min at room temperature')
    ctx.delay(minutes=BINDING_INCUBATION_MIN)

    # ======================== Step 2: magnet 4 min ==========================
    magdeck.engage()
    ctx.delay(minutes=MAGNET_BINDING_MIN, msg='Magnetic module engaged 4 min')

    # ======================== Step 3: discard supernatant ===================
    remove_supernatant(SUPERNATANT_VOL, 'supernatant')

    # ======================== Steps 4-5: two 70% ethanol washes =============
    for wash in range(2):
        add_ethanol(wash)
        remove_supernatant(WASH_VOL, f'ethanol wash {wash + 1}')

    # ======================== Step 6: air dry ===============================
    ctx.delay(minutes=DRY_MIN, msg='Air drying beads 4 min')

    # ======================== Step 7: magnet off, elution buffer ============
    magdeck.disengage()
    ctx.comment(f'Step 7: adding {ELUTION_VOL} uL elution buffer')
    for dst in mag_heads:
        m300.pick_up_tip()
        m300.aspirate(ELUTION_VOL, elution_buffer)
        m300.dispense(ELUTION_VOL, dst.bottom(1))
        m300.mix(10, 80, dst.bottom(1))
        m300.blow_out(dst.top(-2))
        m300.drop_tip()

    # ======================== Step 8: 30 s, magnet on =======================
    ctx.delay(seconds=ELUTION_OFF_SEC, msg='Elution 30 s off magnet')
    magdeck.engage()

    # ======================== Step 9: 90 s, recover eluate ==================
    ctx.delay(seconds=ELUTION_MAGNET_SEC, msg='Magnet engaged 90 s')
    m300.flow_rate.aspirate = 20
    for src, dst in zip(mag_heads, elution_heads):
        m300.pick_up_tip()
        m300.aspirate(ELUTION_VOL, src.bottom(ASPIRATE_HEIGHT))
        m300.dispense(ELUTION_VOL, dst.bottom(1))
        m300.blow_out(dst.top(-2))
        m300.drop_tip()

    magdeck.disengage()
    ctx.comment('Extraction complete. Eluates held at 4 C on the '
                'temperature module (slot 6).')
