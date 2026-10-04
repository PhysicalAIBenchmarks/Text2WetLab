from opentrons import protocol_api

metadata = {
    'protocolName': 'In-house magnetic-bead RNA extraction (OT-2), 48 samples',
    'description': 'Gutierrez-Arroyo et al. 2021 PLOS ONE OT-2 in-house protocol',
    'apiLevel': '2.13',
}

N_SAMPLES = 48
COLS = [0, 2, 4, 6, 8, 10]  # odd columns 1,3,...,11 (0-indexed)


def run(ctx: protocol_api.ProtocolContext):
    waste = ctx.load_labware('usascientific_96_wellplate_2.4ml_deep', 1, 'waste plate')
    tips200 = [ctx.load_labware('opentrons_96_filtertiprack_200ul', s) for s in (2, 3, 9)]
    mag = ctx.load_module('magnetic module', 4)
    plate = mag.load_labware('usascientific_96_wellplate_2.4ml_deep', 'sample plate')
    res = ctx.load_labware('nest_12_reservoir_15ml', 5, 'reservoir')
    temp = ctx.load_module('tempdeck', 6)
    elplate = temp.load_labware('thermo_96_wellplate_200ul', 'elution plate')
    rack1 = ctx.load_labware('opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', 10, 'samples 1-24')
    rack2 = ctx.load_labware('opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', 7, 'samples 25-48')
    tips1000 = ctx.load_labware('opentrons_96_filtertiprack_1000ul', 11)

    p1000 = ctx.load_instrument('p1000_single_gen2', 'left', tip_racks=[tips1000])
    m300 = ctx.load_instrument('p300_multi_gen2', 'right', tip_racks=tips200)

    temp.set_temperature(4)

    beads = res.columns()[1][0]
    elution_buf = res.columns()[3][0]
    ipa = [res.columns()[5][0], res.columns()[6][0]]
    etoh = [res.columns()[i][0] for i in (8, 9, 10, 11)]

    sample_wells = rack1.wells() + rack2.wells()
    dest_wells = [plate.columns()[COLS[i // 8]][i % 8] for i in range(N_SAMPLES)]
    ncols = len(COLS)

    def remove_supernatant(col, vol, tip_ready=False):
        """Aspirate vol from sample-plate column to waste in <=180 uL steps."""
        src = plate.columns()[col][0]
        dst = waste.columns()[col][0]
        left = vol
        while left > 0:
            v = min(180, left)
            m300.aspirate(v, src.bottom(1))
            m300.dispense(v, dst.top(-2))
            left -= v
        m300.blow_out(dst.top(-2))

    def add_big(vol, source, target):
        left = vol
        while left > 0:
            v = min(200, left)
            m300.aspirate(v, source)
            m300.dispense(v, target)
            left -= v

    # 1. Sample 250 uL into the deep-well plate (single channel, new tip each)
    mag.disengage()
    for s, d in zip(sample_wells, dest_wells):
        p1000.pick_up_tip()
        p1000.aspirate(250, s.bottom(2))
        p1000.dispense(250, d.bottom(2))
        p1000.drop_tip()

    # 40 uL beads + 250 uL isopropanol, mix 5x, per column
    for i, col in enumerate(COLS):
        tgt = plate.columns()[col][0]
        m300.pick_up_tip()
        m300.aspirate(40, beads.bottom(2))
        m300.dispense(40, tgt.bottom(3))
        add_big(250, ipa[i // 3].bottom(2), tgt.bottom(5))
        m300.mix(5, 180, tgt.bottom(2))
        m300.blow_out(tgt.top(-2))
        m300.drop_tip()

    ctx.delay(minutes=5, msg='Incubate 5 min at room temperature')

    # 2. magnet 4 min
    mag.engage()
    ctx.delay(minutes=4, msg='Magnet on 4 min')

    # 3. discard supernatant (500 sample+IPA+beads = 540 uL)
    for col in COLS:
        m300.pick_up_tip()
        remove_supernatant(col, 540)
        m300.drop_tip()

    # 4-5. two 500 uL ethanol 70% washes
    for w in range(2):
        for i, col in enumerate(COLS):
            tgt = plate.columns()[col][0]
            m300.pick_up_tip()
            add_big(500, etoh[(i + 2 * w) % 4].bottom(2), tgt.top(-3))
            remove_supernatant(col, 500)
            m300.drop_tip()

    # 6. air dry 4 min
    ctx.delay(minutes=4, msg='Air dry 4 min')

    # 7. magnet off, 100 uL elution buffer, resuspend
    mag.disengage()
    for col in COLS:
        tgt = plate.columns()[col][0]
        m300.pick_up_tip()
        m300.aspirate(100, elution_buf.bottom(2))
        m300.dispense(100, tgt.bottom(2))
        m300.mix(10, 80, tgt.bottom(2))
        m300.blow_out(tgt.top(-2))
        m300.drop_tip()

    # 8. 30 s then magnet on
    ctx.delay(seconds=30)
    mag.engage()

    # 9. after 90 s collect eluate into elution plate
    ctx.delay(seconds=90)
    for col in COLS:
        m300.pick_up_tip()
        m300.aspirate(100, plate.columns()[col][0].bottom(0.8))
        m300.dispense(100, elplate.columns()[col][0].bottom(2))
        m300.drop_tip()

    mag.disengage()
