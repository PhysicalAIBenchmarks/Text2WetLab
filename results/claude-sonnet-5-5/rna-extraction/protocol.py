from opentrons import protocol_api

metadata = {
    'protocolName': 'In-house magnetic-bead SARS-CoV-2 RNA extraction (48 samples)',
    'description': 'OT-2 in-house protocol, PLOS ONE 2021, doi:10.1371/journal.pone.0246302',
    'apiLevel': '2.13',
}

N_SAMPLES = 48
SAMPLE_VOL = 250
ISO_VOL = 250
BEAD_VOL = 40
ETOH_VOL = 500
ELUTION_VOL = 100


def run(ctx: protocol_api.ProtocolContext):
    waste_plate = ctx.load_labware('usascientific_96_wellplate_2.4ml_deep', 1, 'waste')
    tips200 = [ctx.load_labware('opentrons_96_filtertiprack_200ul', s) for s in (2, 3, 9)]
    tips1000 = ctx.load_labware('opentrons_96_filtertiprack_1000ul', 11)
    mag = ctx.load_module('magnetic module', 4)
    plate = mag.load_labware('usascientific_96_wellplate_2.4ml_deep', 'sample plate')
    res = ctx.load_labware('nest_12_reservoir_15ml', 5, 'reagents')
    temp = ctx.load_module('tempdeck', 6)
    elu_plate = temp.load_labware('thermo_96_wellplate_200ul', 'elution plate')
    rack1 = ctx.load_labware('opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', 10, 'samples 1-24')
    rack2 = ctx.load_labware('opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', 7, 'samples 25-48')

    p1000 = ctx.load_instrument('p1000_single_gen2', 'left', tip_racks=[tips1000])
    p300 = ctx.load_instrument('p300_multi_gen2', 'right', tip_racks=tips200)

    temp.start_set_temperature(4)

    ncols = N_SAMPLES // 8
    cols = [1 + 2 * i for i in range(ncols)]  # odd columns 1,3,5,7,9,11 (1-based)
    sample_cols = [plate.columns()[c - 1][0] for c in cols]
    waste_cols = [waste_plate.columns()[c - 1][0] for c in cols]
    elu_cols = [elu_plate.columns()[c - 1][0] for c in cols]

    beads = res.columns()[1][0]
    elution = res.columns()[3][0]
    iso_wells = [res.columns()[5][0], res.columns()[6][0]]
    etoh_wells = [res.columns()[i][0] for i in (8, 9, 10, 11)]

    # tracking of reservoir usage (per channel volumes) to rotate columns
    iso_used = [0]
    etoh_used = [0]

    def iso_src(vol):
        i = min(int(iso_used[0] // 13000), len(iso_wells) - 1)
        iso_used[0] += vol
        return iso_wells[i]

    def etoh_src(vol):
        i = min(int(etoh_used[0] // 13000), len(etoh_wells) - 1)
        etoh_used[0] += vol
        return etoh_wells[i]

    mag.disengage()

    # Step 1: samples (250 uL) into odd columns of the plate, new 1000 uL tip each
    samples = rack1.wells() + rack2.wells()
    for i in range(N_SAMPLES):
        dest = plate.columns()[cols[i // 8] - 1][i % 8]
        p1000.transfer(SAMPLE_VOL, samples[i].bottom(2), dest.top(-2),
                       new_tip='always', blow_out=True, blowout_location='destination well')

    # Step 2: isopropanol 250 uL + beads 40 uL, mix 5x, one tip per column
    for well in sample_cols:
        p300.pick_up_tip()
        p300.mix(5, 150, beads)
        for _ in range(2):
            p300.aspirate(ISO_VOL / 2, iso_src(ISO_VOL / 2).bottom(1))
            p300.dispense(ISO_VOL / 2, well.top(-2))
            p300.blow_out(well.top(-2))
        p300.mix(2, 150, beads)
        p300.aspirate(BEAD_VOL, beads.bottom(1))
        p300.dispense(BEAD_VOL, well.bottom(3))
        p300.mix(5, 180, well.bottom(2))
        p300.blow_out(well.top(-2))
        p300.drop_tip()

    ctx.delay(minutes=5, msg='Incubate 5 min at room temperature')

    # Step 3: magnet 4 min, discard supernatant
    mag.engage()
    ctx.delay(minutes=4, msg='Magnet on 4 min')

    def remove(vol, well, waste):
        n = int(-(-vol // 180))
        each = vol / n
        p300.flow_rate.aspirate = 40
        for _ in range(n):
            p300.aspirate(each, well.bottom(1))
            p300.dispense(each, waste.top(-2))
        p300.blow_out(waste.top(-2))
        p300.flow_rate.aspirate = 94

    total = SAMPLE_VOL + ISO_VOL + BEAD_VOL
    for well, waste in zip(sample_cols, waste_cols):
        p300.pick_up_tip()
        remove(total, well, waste)
        p300.drop_tip()

    # Steps 4-5: two ethanol 70% washes (500 uL), collected and discarded
    for _ in range(2):
        for well, waste in zip(sample_cols, waste_cols):
            p300.pick_up_tip()
            for _ in range(3):
                v = ETOH_VOL / 3
                p300.aspirate(v, etoh_src(v).bottom(1))
                p300.dispense(v, well.top(-2))
            remove(ETOH_VOL, well, waste)
            p300.drop_tip()

    # Step 6: air dry 4 min
    ctx.delay(minutes=4, msg='Air dry 4 min')

    # Step 7: magnet off, add 100 uL elution buffer and resuspend
    mag.disengage()
    for well in sample_cols:
        p300.pick_up_tip()
        p300.aspirate(ELUTION_VOL, elution.bottom(1))
        p300.dispense(ELUTION_VOL, well.bottom(2))
        p300.mix(5, 80, well.bottom(2))
        p300.blow_out(well.top(-2))
        p300.drop_tip()

    # Step 8: after 30 s magnet on
    ctx.delay(seconds=30)
    mag.engage()

    # Step 9: after 90 s collect eluate into elution plate
    ctx.delay(seconds=90)
    temp.await_temperature(4)
    for well, dest in zip(sample_cols, elu_cols):
        p300.pick_up_tip()
        p300.flow_rate.aspirate = 20
        p300.aspirate(ELUTION_VOL, well.bottom(1))
        p300.flow_rate.aspirate = 94
        p300.dispense(ELUTION_VOL, dest.bottom(1))
        p300.blow_out(dest.top(-2))
        p300.drop_tip()

    mag.disengage()
