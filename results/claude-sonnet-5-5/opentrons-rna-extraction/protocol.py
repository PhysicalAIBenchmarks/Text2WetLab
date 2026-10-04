from opentrons import protocol_api

metadata = {
    'protocolName': 'In-house magnetic-bead RNA extraction, 48 samples (OT-2)',
    'description': 'Gutierrez-Arroyo et al. 2021 PLOS ONE OT-2 in-house protocol',
    'apiLevel': '2.13',
}

N_SAMPLES = 48
N_COLS = N_SAMPLES // 8
SAMPLE_VOL = 250
IPA_VOL = 250
BEAD_VOL = 40
ETOH_VOL = 500
ELUTION_VOL = 100


def run(ctx: protocol_api.ProtocolContext):
    waste_plate = ctx.load_labware('usascientific_96_wellplate_2.4ml_deep', 1, 'waste')
    tips200 = [ctx.load_labware('opentrons_96_filtertiprack_200ul', s) for s in (2, 3, 9)]
    mag = ctx.load_module('magnetic module', 4)
    plate = mag.load_labware('usascientific_96_wellplate_2.4ml_deep', 'extraction plate')
    res = ctx.load_labware('nest_12_reservoir_15ml', 5, 'reagents')
    temp = ctx.load_module('tempdeck', 6)
    elu = temp.load_labware('thermo_96_wellplate_200ul', 'elution plate')
    rack1 = ctx.load_labware('opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', 10, 'samples 1-24')
    rack2 = ctx.load_labware('opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', 7, 'samples 25-48')
    tips1000 = ctx.load_labware('opentrons_96_filtertiprack_1000ul', 11)

    p1000 = ctx.load_instrument('p1000_single_gen2', 'left', tip_racks=[tips1000])
    m300 = ctx.load_instrument('p300_multi_gen2', 'right', tip_racks=tips200)

    temp.start_set_temperature(4)

    beads = res.wells()[1]
    elution_buf = res.wells()[3]
    ipa = [res.wells()[5], res.wells()[6]]
    etoh = [res.wells()[i] for i in (8, 9, 10, 11)]

    cols = [plate.columns()[2 * i] for i in range(N_COLS)]       # odd columns 1,3,...,11
    top = [c[0] for c in cols]
    waste = [waste_plate.columns()[2 * i][0] for i in range(N_COLS)]
    out = [elu.columns()[2 * i][0] for i in range(N_COLS)]

    # make sure magnet is disengaged
    mag.disengage()
    temp.await_temperature(4)

    # 1. beads 40 uL, isopropanol 250 uL, sample 250 uL per well
    m300.pick_up_tip()
    for t in top:
        m300.aspirate(BEAD_VOL, beads)
        m300.dispense(BEAD_VOL, t.top(-2))
        m300.blow_out(t.top(-2))
    m300.drop_tip()

    m300.pick_up_tip()
    for i, t in enumerate(top):
        src = ipa[0] if i < 3 else ipa[1]
        for _ in range(2):
            m300.aspirate(IPA_VOL / 2, src)
            m300.dispense(IPA_VOL / 2, t.top(-2))
        m300.blow_out(t.top(-2))
    m300.drop_tip()

    samples = rack1.wells() + rack2.wells()
    for i in range(N_SAMPLES):
        dst = cols[i // 8][i % 8]
        p1000.pick_up_tip()
        p1000.aspirate(SAMPLE_VOL, samples[i])
        p1000.dispense(SAMPLE_VOL, dst)
        p1000.mix(5, 400, dst)  # mix by pipetting five times
        p1000.blow_out(dst.top())
        p1000.drop_tip()

    ctx.delay(minutes=5, msg='Incubate 5 min at room temperature')

    def remove(vol_total, i, rate=0.5):
        """Remove supernatant from column i to waste, with magnet engaged."""
        remaining = vol_total
        m300.pick_up_tip()
        while remaining > 0:
            v = min(180, remaining)
            m300.aspirate(v, cols[i][0].bottom(1), rate=rate)
            m300.dispense(v, waste[i].top(-2))
            remaining -= v
        m300.blow_out(waste[i].top(-2))
        m300.drop_tip()

    # 2. magnet 4 min, 3. discard supernatant
    mag.engage()
    ctx.delay(minutes=4, msg='Magnet on 4 min')
    for i in range(N_COLS):
        remove(SAMPLE_VOL + IPA_VOL + BEAD_VOL, i)

    # 4-5. two ethanol washes, 500 uL each, collected and discarded
    for w in range(2):
        m300.pick_up_tip()
        for i, t in enumerate(top):
            src = etoh[i * 4 // N_COLS]
            for _ in range(3):
                v = ETOH_VOL / 3
                m300.aspirate(v, src)
                m300.dispense(v, t.top(-2))
            m300.blow_out(t.top(-2))
        m300.drop_tip()
        for i in range(N_COLS):
            remove(ETOH_VOL, i)

    # 6. air dry 4 min
    ctx.delay(minutes=4, msg='Air dry 4 min')

    # 7. magnet off, add 100 uL elution buffer
    mag.disengage()
    m300.pick_up_tip()
    for t in cols:
        m300.aspirate(ELUTION_VOL, elution_buf)
        m300.dispense(ELUTION_VOL, t[0].bottom(1))
        m300.blow_out(t[0].top(-2))
    m300.drop_tip()

    # 8. after 30 s turn magnet on
    ctx.delay(seconds=30, msg='Elution 30 s')
    mag.engage()

    # 9. after 90 s collect eluate into the elution plate
    ctx.delay(seconds=90, msg='Magnet 90 s')
    for i in range(N_COLS):
        m300.pick_up_tip()
        m300.aspirate(ELUTION_VOL, cols[i][0].bottom(1), rate=0.5)
        m300.dispense(ELUTION_VOL, out[i])
        m300.drop_tip()

    mag.disengage()
