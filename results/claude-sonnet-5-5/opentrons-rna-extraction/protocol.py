from opentrons import protocol_api

metadata = {
    'protocolName': 'OT-2 in-house magnetic-bead SARS-CoV-2 RNA extraction (48 samples)',
    'description': 'Gutierrez-Arroyo et al. 2021 PLOS ONE OT-2in-house protocol: '
                   '250 uL sample + 250 uL isopropanol + 40 uL beads, 5 min incubation, '
                   '4 min magnet, 2 x 500 uL 70% ethanol, 4 min air dry, 100 uL elution.',
    'apiLevel': '2.13',
}

N_SAMPLES = 48
SAMPLE_VOL = 250
IPA_VOL = 250
BEAD_VOL = 40
WASH_VOL = 500
ELUTION_VOL = 100
MAX_TRANSFER = 200  # filter-tip capacity


def run(ctx: protocol_api.ProtocolContext):
    waste_plate = ctx.load_labware('usascientific_96_wellplate_2.4ml_deep', 1, 'Waste plate')
    tips200 = [ctx.load_labware('opentrons_96_filtertiprack_200ul', s) for s in (2, 3, 9)]
    tips1000 = ctx.load_labware('opentrons_96_filtertiprack_1000ul', 11)
    mag = ctx.load_module('magnetic module', 4)
    sample_plate = mag.load_labware('usascientific_96_wellplate_2.4ml_deep', 'Extraction plate')
    reservoir = ctx.load_labware('nest_12_reservoir_15ml', 5, 'Reagent reservoir')
    temp = ctx.load_module('tempdeck', 6)
    elution_plate = temp.load_labware('thermo_96_wellplate_200ul', 'Elution plate')
    rack1 = ctx.load_labware('opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', 10, 'Samples 1-24')
    rack2 = ctx.load_labware('opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', 7, 'Samples 25-48')

    p1000 = ctx.load_instrument('p1000_single_gen2', 'left', tip_racks=[tips1000])
    p300 = ctx.load_instrument('p300_multi_gen2', 'right', tip_racks=tips200)

    temp.start_set_temperature(4)

    beads = reservoir['A2']
    elution_buffer = reservoir['A4']
    ipa = [reservoir['A6'], reservoir['A7']]
    ethanol = [reservoir['A9'], reservoir['A10'], reservoir['A11'], reservoir['A12']]

    n_cols = N_SAMPLES // 8
    cols = [2 * i for i in range(n_cols)]  # 0-based indices of columns 1,3,5,7,9,11
    sample_tubes = rack1.wells() + rack2.wells()
    sample_wells = [sample_plate.columns()[c][r] for c in cols for r in range(8)]
    sample_tops = [sample_plate.columns()[c][0] for c in cols]
    waste_tops = [waste_plate.columns()[c][0] for c in cols]
    elution_tops = [elution_plate.columns()[c][0] for c in cols]

    def chunks(total):
        out = []
        while total > 0:
            v = min(MAX_TRANSFER, total)
            out.append(v)
            total -= v
        return out

    def remove_supernatant(i, volume):
        src = sample_tops[i]
        for v in chunks(volume):
            p300.aspirate(v, src.bottom(1.0), rate=0.5)
            p300.dispense(v, waste_tops[i].top(-2))
            p300.blow_out(waste_tops[i].top(-2))

    # 1. Samples (250 uL each) into odd columns, one fresh tip per sample
    for tube, well in zip(sample_tubes, sample_wells):
        p1000.pick_up_tip()
        p1000.aspirate(SAMPLE_VOL, tube.bottom(2))
        p1000.dispense(SAMPLE_VOL, well.bottom(2))
        p1000.drop_tip()

    # 2. Isopropanol 250 uL + beads 40 uL, mix 5x (fresh tip per column)
    for i in range(n_cols):
        p300.pick_up_tip()
        src_ipa = ipa[i // 3]
        for v in chunks(IPA_VOL):
            p300.aspirate(v, src_ipa.bottom(1))
            p300.dispense(v, sample_tops[i].top(-2))
        p300.mix(3, 100, beads.bottom(1))
        p300.aspirate(BEAD_VOL, beads.bottom(1))
        p300.dispense(BEAD_VOL, sample_tops[i].bottom(2))
        p300.mix(5, 180, sample_tops[i].bottom(2))
        p300.blow_out(sample_tops[i].top(-2))
        p300.drop_tip()

    # 3. Incubate 5 min at room temperature
    ctx.delay(minutes=5, msg='Bead binding incubation')

    # 4. Magnet 4 min, discard supernatant
    mag.engage()
    ctx.delay(minutes=4, msg='Magnet on')
    for i in range(n_cols):
        p300.pick_up_tip()
        remove_supernatant(i, SAMPLE_VOL + IPA_VOL + BEAD_VOL)
        p300.drop_tip()

    # 5-6. Two 70% ethanol washes (500 uL), collect and discard
    for w in range(2):
        p300.pick_up_tip()
        for i in range(n_cols):
            src = ethanol[2 * w + i // 3]
            for v in chunks(WASH_VOL):
                p300.aspirate(v, src.bottom(1))
                p300.dispense(v, sample_tops[i].top(-2))
        p300.drop_tip()
        for i in range(n_cols):
            p300.pick_up_tip()
            remove_supernatant(i, WASH_VOL)
            p300.drop_tip()

    # 7. Air dry 4 min
    ctx.delay(minutes=4, msg='Air dry beads')

    # 8. Magnet off, add 100 uL elution buffer
    mag.disengage()
    p300.pick_up_tip()
    for i in range(n_cols):
        p300.aspirate(ELUTION_VOL, elution_buffer.bottom(1))
        p300.dispense(ELUTION_VOL, sample_tops[i].bottom(3), rate=2.0)
    p300.drop_tip()

    # 9. After 30 s magnet on; after 90 s collect eluate
    ctx.delay(seconds=30)
    mag.engage()
    ctx.delay(seconds=90)
    temp.await_temperature(4)
    for i in range(n_cols):
        p300.pick_up_tip()
        p300.aspirate(ELUTION_VOL, sample_tops[i].bottom(1.0), rate=0.5)
        p300.dispense(ELUTION_VOL, elution_tops[i].bottom(2))
        p300.drop_tip()
    mag.disengage()
