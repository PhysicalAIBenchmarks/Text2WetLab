from opentrons import protocol_api

metadata = {
    'protocolName': 'In-house OT-2 magnetic-bead RNA extraction (48 samples)',
    'description': 'Automated low-cost SARS-CoV-2 RNA extraction (PLOS ONE 2021, '
                   'OT-2 in-house protocol), 48 samples.',
    'apiLevel': '2.13',
}

N_COLS = 6
SAMPLE_VOL = 250
ISO_VOL = 250
BEADS_VOL = 40
WASH_VOL = 500
ELUTION_VOL = 100
CHUNK = 180  # p300 transfer chunk (tip max 200 uL)


def run(ctx: protocol_api.ProtocolContext):
    waste = ctx.load_labware('usascientific_96_wellplate_2.4ml_deep', 1, 'waste plate')
    tr_a = ctx.load_labware('opentrons_96_filtertiprack_200ul', 2)
    tr_b = ctx.load_labware('opentrons_96_filtertiprack_200ul', 3)
    tr_c = ctx.load_labware('opentrons_96_filtertiprack_200ul', 9)
    mag = ctx.load_module('magnetic module', 4)
    plate = mag.load_labware('usascientific_96_wellplate_2.4ml_deep', 'sample plate')
    res = ctx.load_labware('nest_12_reservoir_15ml', 5, 'reagents')
    temp = ctx.load_module('tempdeck', 6)
    temp.set_temperature(4)
    elu_plate = temp.load_labware('thermo_96_wellplate_200ul', 'elution plate')
    rack1 = ctx.load_labware('opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', 10, 'samples 1-24')
    rack2 = ctx.load_labware('opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', 7, 'samples 25-48')
    tips1000 = ctx.load_labware('opentrons_96_filtertiprack_1000ul', 11)

    p1000 = ctx.load_instrument('p1000_single_gen2', 'left', tip_racks=[tips1000])
    p300 = ctx.load_instrument('p300_multi_gen2', 'right', tip_racks=[tr_a, tr_b, tr_c])

    beads = res.wells()[1]
    elution_buf = res.wells()[3]
    iso = [res.wells()[5], res.wells()[6]]
    etoh = [res.wells()[8], res.wells()[9], res.wells()[10], res.wells()[11]]

    odd = [plate.columns()[i] for i in range(0, 12, 2)]          # columns 1,3,...,11
    sample_tops = [c[0] for c in odd]                           # multi targets (A row)
    waste_tops = [waste.columns()[i][0] for i in range(0, 12, 2)]
    elu_tops = [elu_plate.columns()[i][0] for i in range(0, 12, 2)]

    # 36 tip columns, one per (step, column): exactly three racks of 12 columns
    tip_cols = []
    for rack in (tr_a, tr_b, tr_c):
        tip_cols += [col[0] for col in rack.columns()]

    def tip(stage, c):
        return tip_cols[stage * N_COLS + c]

    BEAD_T, ISO_T, MIX_T, W1_T, W2_T, ELU_T = range(6)

    def remove_supernatant(c, vol):
        """Collect `vol` from plate column c to the waste plate (magnet engaged)."""
        left = vol
        while left > 0:
            v = min(CHUNK, left)
            p300.aspirate(v, sample_tops[c].bottom(1.5), rate=0.5)
            p300.dispense(v, waste_tops[c].top(-2))
            left -= v
        p300.blow_out(waste_tops[c].top(-2))

    def add_reagent(srcs, vol, c, src_idx):
        left = vol
        while left > 0:
            v = min(CHUNK, left)
            p300.aspirate(v, srcs[src_idx].bottom(2))
            p300.dispense(v, sample_tops[c].top(-3))
            left -= v

    # ---- Step 1: 40 uL beads, 250 uL isopropanol, 250 uL sample per well ----
    for c in range(N_COLS):
        p300.pick_up_tip(tip(BEAD_T, c))
        p300.mix(3, 40, beads.bottom(2))
        p300.aspirate(BEADS_VOL, beads.bottom(2))
        p300.dispense(BEADS_VOL, sample_tops[c].top(-3))
        p300.blow_out(sample_tops[c].top(-3))
        p300.drop_tip()
    for c in range(N_COLS):
        p300.pick_up_tip(tip(ISO_T, c))
        add_reagent(iso, ISO_VOL, c, c // 3)
        p300.drop_tip()

    sample_tubes = rack1.wells() + rack2.wells()
    for i, tube in enumerate(sample_tubes):
        dest = plate.columns()[2 * (i // 8)][i % 8]
        p1000.pick_up_tip()
        p1000.aspirate(SAMPLE_VOL, tube.bottom(2))
        p1000.dispense(SAMPLE_VOL, dest.top(-3))
        p1000.blow_out(dest.top(-3))
        p1000.drop_tip()

    # mix by pipetting five times, keep tips for later supernatant removal
    for c in range(N_COLS):
        p300.pick_up_tip(tip(MIX_T, c))
        p300.mix(5, CHUNK, sample_tops[c].bottom(2))
        p300.return_tip()
    ctx.delay(minutes=5, msg='Incubate 5 min at room temperature')

    # ---- Step 2/3: magnet 4 min, discard supernatant ----
    mag.engage()
    ctx.delay(minutes=4, msg='Magnet on 4 min')
    for c in range(N_COLS):
        p300.pick_up_tip(tip(MIX_T, c))
        remove_supernatant(c, SAMPLE_VOL + ISO_VOL + BEADS_VOL)
        p300.drop_tip()

    # ---- Steps 4-5: two washes with 500 uL 70% ethanol, collect and discard ----
    for stage, wells in ((W1_T, etoh[0:2]), (W2_T, etoh[2:4])):
        for c in range(N_COLS):
            p300.pick_up_tip(tip(stage, c))
            add_reagent(wells, WASH_VOL, c, c // 3)
            remove_supernatant(c, WASH_VOL)
            p300.drop_tip()

    # ---- Step 6: air dry 4 min ----
    ctx.delay(minutes=4, msg='Air dry 4 min')

    # ---- Step 7: magnet off, add 100 uL elution buffer, resuspend ----
    mag.disengage()
    for c in range(N_COLS):
        p300.pick_up_tip(tip(ELU_T, c))
        p300.aspirate(ELUTION_VOL, elution_buf.bottom(2))
        p300.dispense(ELUTION_VOL, sample_tops[c].bottom(1))
        p300.mix(5, 80, sample_tops[c].bottom(1))
        p300.blow_out(sample_tops[c].top(-2))
        p300.return_tip()

    # ---- Step 8: after 30 s, magnet on ----
    ctx.delay(seconds=30)
    mag.engage()

    # ---- Step 9: after 90 s collect eluate into the elution plate ----
    ctx.delay(seconds=90)
    for c in range(N_COLS):
        p300.pick_up_tip(tip(ELU_T, c))
        p300.aspirate(ELUTION_VOL, sample_tops[c].bottom(1.5), rate=0.5)
        p300.dispense(ELUTION_VOL, elu_tops[c].bottom(1))
        p300.drop_tip()
    mag.disengage()
