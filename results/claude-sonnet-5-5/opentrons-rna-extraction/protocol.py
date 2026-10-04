from opentrons import protocol_api

metadata = {
    'protocolName': 'In-house magnetic-bead SARS-CoV-2 RNA extraction (OT-2, 48 samples)',
    'description': 'Lazaro-Perona et al. PLOS ONE 2021 OT-2in-house protocol',
    'apiLevel': '2.13',
}

N_SAMPLES = 48
SAMPLE_VOL = 250
IPA_VOL = 250
BEAD_VOL = 40
WASH_VOL = 500
ELUTION_VOL = 100


def run(ctx: protocol_api.ProtocolContext):
    waste = ctx.load_labware('usascientific_96_wellplate_2.4ml_deep', 1, 'waste')
    tips200 = [ctx.load_labware('opentrons_96_filtertiprack_200ul', s) for s in (2, 3, 9)]
    mag = ctx.load_module('magnetic module', 4)
    plate = mag.load_labware('usascientific_96_wellplate_2.4ml_deep')
    res = ctx.load_labware('nest_12_reservoir_15ml', 5, 'reagents')
    temp = ctx.load_module('tempdeck', 6)
    elplate = temp.load_labware('thermo_96_wellplate_200ul')
    rack1 = ctx.load_labware('opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', 10, 'samples 1-24')
    rack2 = ctx.load_labware('opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', 7, 'samples 25-48')
    tips1000 = ctx.load_labware('opentrons_96_filtertiprack_1000ul', 11)

    p1000 = ctx.load_instrument('p1000_single_gen2', 'left', tip_racks=[tips1000])
    m300 = ctx.load_instrument('p300_multi_gen2', 'right', tip_racks=tips200)

    temp.start_set_temperature(4)

    n_cols = N_SAMPLES // 8
    cols = [c for c in range(0, 12, 2)][:n_cols]          # odd columns 1,3,...,11 (0-indexed even)
    sample_wells = [plate.columns()[c][r] for c in cols for r in range(8)]
    sample_tubes = (rack1.wells() + rack2.wells())[:N_SAMPLES]
    targets = [plate.columns()[c][0] for c in cols]
    waste_t = [waste.columns()[c][0] for c in cols]
    elu_t = [elplate.columns()[c][0] for c in cols]

    beads = res.wells()[1]
    elbuf = res.wells()[3]
    ipa = [res.wells()[5], res.wells()[6]]
    etoh = res.wells()[8:12]

    def multi_dispense(src_for, vol, dests, max_v=200, tip_per_dest=False):
        """Distribute vol (split into <=200 uL aspirations) to each dest column."""
        n = -(-vol // max_v)
        each = vol / n
        for i, d in enumerate(dests):
            for _ in range(n):
                m300.aspirate(each, src_for(i))
                m300.dispense(each, d.top(-2))
            m300.blow_out(d.top(-2))

    def remove(col_i, vol, tip_kept=True):
        n = -(-vol // 190)
        each = vol / n
        for _ in range(n):
            m300.aspirate(each, targets[col_i].bottom(1))
            m300.dispense(each, waste_t[col_i].top(-2))
            m300.blow_out(waste_t[col_i].top(-2))

    # 0. Make sure the magnet is off
    mag.disengage()

    # 1. Magnetic beads (40 uL), then isopropanol (250 uL), then sample (250 uL)
    m300.pick_up_tip()
    for i, d in enumerate(targets):
        m300.aspirate(BEAD_VOL, beads.bottom(2))
        m300.dispense(BEAD_VOL, d.top(-2))
        m300.blow_out(d.top(-2))
    m300.drop_tip()

    m300.pick_up_tip()
    multi_dispense(lambda i: ipa[0 if i < 3 else 1].bottom(2), IPA_VOL, targets)
    m300.drop_tip()

    for tube, well in zip(sample_tubes, sample_wells):
        p1000.pick_up_tip()
        p1000.aspirate(SAMPLE_VOL, tube.bottom(2))
        p1000.dispense(SAMPLE_VOL, well.bottom(3))
        p1000.mix(5, 400, well.bottom(2))          # mix by pipetting five times
        p1000.blow_out(well.top(-2))
        p1000.drop_tip()

    # 2. Incubate 5 min at room temperature
    ctx.delay(minutes=5, msg='Binding incubation')

    # 3. Magnet 4 min, remove supernatant
    mag.engage()
    ctx.delay(minutes=4, msg='Magnet on')
    for i in range(n_cols):
        m300.pick_up_tip()
        remove(i, SAMPLE_VOL + IPA_VOL + BEAD_VOL)
        m300.drop_tip()

    # 4. Two ethanol 70% washes (magnet on)
    for w in range(2):
        m300.pick_up_tip()
        multi_dispense(lambda i: etoh[2 * w + i // 3].bottom(2),
                       WASH_VOL, targets)
        m300.drop_tip()
        ctx.delay(seconds=30, msg='Settle beads')
        for i in range(n_cols):
            m300.pick_up_tip()
            remove(i, WASH_VOL)
            m300.drop_tip()

    # 5. Air dry 4 min
    ctx.delay(minutes=4, msg='Air dry')

    # 6. Magnet off, add 100 uL elution buffer and resuspend
    mag.disengage()
    for i, d in enumerate(targets):
        m300.pick_up_tip()
        m300.aspirate(ELUTION_VOL, elbuf.bottom(2))
        m300.dispense(ELUTION_VOL, d.bottom(2))
        m300.mix(5, 80, d.bottom(2))
        m300.blow_out(d.top(-2))
        m300.drop_tip()

    # 7. After 30 s magnet on; after 90 s collect eluate
    ctx.delay(seconds=30)
    mag.engage()
    ctx.delay(seconds=90)
    temp.await_temperature(4)
    for i, d in enumerate(targets):
        m300.pick_up_tip()
        m300.aspirate(ELUTION_VOL, d.bottom(1))
        m300.dispense(ELUTION_VOL, elu_t[i].bottom(2))
        m300.blow_out(elu_t[i].top(-1))
        m300.drop_tip()
    mag.disengage()
