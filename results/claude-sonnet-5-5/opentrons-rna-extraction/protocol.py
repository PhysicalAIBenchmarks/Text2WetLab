from opentrons import protocol_api

metadata = {
    'protocolName': 'In-house magnetic-bead SARS-CoV-2 RNA extraction (OT-2, 48 samples)',
    'description': 'Gutierrez-Arroyo et al. 2021 PLOS ONE OT-2 in-house protocol',
    'apiLevel': '2.13',
}

N_SAMPLES = 48
SAMPLE_VOL = 250
IPA_VOL = 250
BEAD_VOL = 40
WASH_VOL = 500
ELUTION_VOL = 100
SUP_VOL = SAMPLE_VOL + IPA_VOL + BEAD_VOL


def run(ctx: protocol_api.ProtocolContext):
    waste = ctx.load_labware('usascientific_96_wellplate_2.4ml_deep', 1, 'waste')
    tips200 = [ctx.load_labware('opentrons_96_filtertiprack_200ul', s)
               for s in (2, 3, 9)]
    mag = ctx.load_module('magnetic module', 4)
    plate = mag.load_labware('usascientific_96_wellplate_2.4ml_deep')
    res = ctx.load_labware('nest_12_reservoir_15ml', 5)
    temp = ctx.load_module('tempdeck', 6)
    elplate = temp.load_labware('thermo_96_wellplate_200ul')
    rack1 = ctx.load_labware(
        'opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', 10)
    rack2 = ctx.load_labware(
        'opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', 7)
    tips1000 = ctx.load_labware('opentrons_96_filtertiprack_1000ul', 11)

    p1000 = ctx.load_instrument('p1000_single_gen2', 'left',
                                tip_racks=[tips1000])
    m300 = ctx.load_instrument('p300_multi_gen2', 'right', tip_racks=tips200)

    temp.start_set_temperature(4)

    beads = res.wells()[1]
    elbuf = res.wells()[3]
    ipa = [res.wells()[5], res.wells()[6]]
    etoh1 = [res.wells()[8], res.wells()[9]]   # wash 1
    etoh2 = [res.wells()[10], res.wells()[11]]  # wash 2

    cols = [plate.columns()[i] for i in (0, 2, 4, 6, 8, 10)]
    ncols = N_SAMPLES // 8
    sample_wells = [c[r] for c in [plate.columns()[i] for i in (0, 2, 4, 6, 8, 10)]
                    for r in range(8)]
    sample_tubes = rack1.wells() + rack2.wells()
    top_cols = [plate.columns()[i][0] for i in (0, 2, 4, 6, 8, 10)]
    waste_cols = [waste.columns()[i][0] for i in (0, 2, 4, 6, 8, 10)]
    el_cols = [elplate.columns()[i][0] for i in (0, 2, 4, 6, 8, 10)]

    def src(lst, i):
        return lst[i // 3]  # 3 plate columns per reservoir well

    def multi_transfer(src_well, dst, vol, per=200, **kw):
        n = -(-vol // per)
        each = vol / n
        for _ in range(n):
            m300.aspirate(each, src_well.bottom(2))
            m300.dispense(each, dst)
            m300.blow_out(dst)

    def remove(i, vol, per=180):
        n = -(-vol // per)
        each = vol / n
        m300.flow_rate.aspirate = 40
        for _ in range(n):
            m300.aspirate(each, top_cols[i].bottom(1))
            m300.dispense(each, waste_cols[i].top(-2))
            m300.blow_out(waste_cols[i].top(-2))
        m300.flow_rate.aspirate = 92.86

    # 1. samples (250 uL) into odd columns, magnet off
    mag.disengage()
    for tube, well in zip(sample_tubes, sample_wells):
        p1000.pick_up_tip()
        p1000.aspirate(SAMPLE_VOL, tube.bottom(2))
        p1000.dispense(SAMPLE_VOL, well.top(-2))
        p1000.blow_out(well.top(-2))
        p1000.drop_tip()

    # 2. isopropanol + beads, mix 5x
    for i in range(ncols):
        m300.pick_up_tip()
        multi_transfer(src(ipa, i), top_cols[i].top(-2), IPA_VOL)
        m300.mix(3, 150, beads.bottom(2))
        m300.aspirate(BEAD_VOL, beads.bottom(2))
        m300.dispense(BEAD_VOL, top_cols[i].top(-2))
        m300.mix(5, 180, top_cols[i].bottom(2))
        m300.blow_out(top_cols[i].top(-2))
        m300.drop_tip()

    ctx.delay(minutes=5, msg='Incubate 5 min at room temperature')

    # 3. magnet 4 min, discard supernatant
    mag.engage()
    ctx.delay(minutes=4, msg='Magnet on 4 min')
    for i in range(ncols):
        m300.pick_up_tip()
        remove(i, SUP_VOL)
        m300.drop_tip()

    # 4. two ethanol washes
    for ethanol in (etoh1, etoh2):
        for i in range(ncols):
            m300.pick_up_tip()
            multi_transfer(src(ethanol, i), top_cols[i].top(-2), WASH_VOL, per=170)
            remove(i, WASH_VOL, per=170)
            m300.drop_tip()

    # 5. air dry 4 min
    ctx.delay(minutes=4, msg='Air dry 4 min')

    # 6. elution
    mag.disengage()
    for i in range(ncols):
        m300.pick_up_tip()
        m300.aspirate(ELUTION_VOL, elbuf.bottom(2))
        m300.dispense(ELUTION_VOL, top_cols[i].bottom(2))
        m300.mix(10, 80, top_cols[i].bottom(2))
        m300.blow_out(top_cols[i].top(-2))
        m300.drop_tip()
    ctx.delay(seconds=30)
    mag.engage()
    ctx.delay(seconds=90)

    temp.await_temperature(4)
    for i in range(ncols):
        m300.pick_up_tip()
        m300.flow_rate.aspirate = 30
        m300.aspirate(ELUTION_VOL, top_cols[i].bottom(1))
        m300.flow_rate.aspirate = 92.86
        m300.dispense(ELUTION_VOL, el_cols[i].bottom(2))
        m300.drop_tip()
    mag.disengage()
