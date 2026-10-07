from opentrons import protocol_api

metadata = {
    'protocolName': 'OT-2 in-house magnetic-bead SARS-CoV-2 RNA extraction (48 samples)',
    'description': 'Automated low-cost SARS-CoV-2 RNA extraction, OT-2 in-house protocol (PLOS ONE 2021, '
                   'doi:10.1371/journal.pone.0246302)',
    'apiLevel': '2.13',
}

N_SAMPLES = 48
SAMPLE_VOL = 250
IPA_VOL = 250
BEAD_VOL = 40
ETOH_VOL = 500
ELUTION_VOL = 100
TOTAL_VOL = SAMPLE_VOL + IPA_VOL + BEAD_VOL  # 540 uL per well
MAX_TIP = 200  # 200 uL filter tips


def run(protocol: protocol_api.ProtocolContext):
    # ---------------- labware ----------------
    waste = protocol.load_labware('usascientific_96_wellplate_2.4ml_deep', 1, 'waste plate')
    tips200 = [protocol.load_labware('opentrons_96_filtertiprack_200ul', s) for s in (2, 3, 9)]
    mag = protocol.load_module('magnetic module', 4)
    sample_plate = mag.load_labware('usascientific_96_wellplate_2.4ml_deep', 'sample/extraction plate')
    reservoir = protocol.load_labware('nest_12_reservoir_15ml', 5, 'reagent reservoir')
    temp = protocol.load_module('tempdeck', 6)
    elution_plate = temp.load_labware('thermo_96_wellplate_200ul', 'elution plate')
    rack1 = protocol.load_labware('opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', 10, 'samples 1-24')
    rack2 = protocol.load_labware('opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', 7, 'samples 25-48')
    tips1000 = protocol.load_labware('opentrons_96_filtertiprack_1000ul', 11)

    p1000 = protocol.load_instrument('p1000_single_gen2', 'left', tip_racks=[tips1000])
    p300m = protocol.load_instrument('p300_multi_gen2', 'right', tip_racks=tips200)

    # ---------------- layout ----------------
    beads = reservoir.columns()[1][0]            # column 2
    elution_buffer = reservoir.columns()[3][0]   # column 4
    ipa = [reservoir.columns()[5][0], reservoir.columns()[6][0]]       # columns 6-7
    etoh = [reservoir.columns()[8][0], reservoir.columns()[9][0],
            reservoir.columns()[10][0], reservoir.columns()[11][0]]    # columns 9-12
    etoh_wash1 = etoh[0:2]
    etoh_wash2 = etoh[2:4]

    # 48 samples in odd columns 1,3,5,7,9,11 (A-H each)
    odd_cols = [0, 2, 4, 6, 8, 10]
    n_cols = N_SAMPLES // 8
    cols = odd_cols[:n_cols]
    sample_wells = []
    for c in cols:
        sample_wells += sample_plate.columns()[c]
    sources = rack1.wells() + rack2.wells()
    sample_cols = [sample_plate.columns()[c][0] for c in cols]
    waste_cols = [waste.columns()[c][0] for c in cols]
    elution_cols = [elution_plate.columns()[c][0] for c in cols]

    def chunks(vol):
        n = -(-vol // MAX_TIP)
        return [vol / n] * n

    # ---------------- setup ----------------
    temp.set_temperature(4)
    mag.disengage()

    # ---------------- step 1: magnetic beads ----------------
    p300m.pick_up_tip()
    for col in sample_cols:
        p300m.mix(3, 150, beads, rate=0.8)
        p300m.aspirate(BEAD_VOL, beads.bottom(1.5), rate=0.5)
        p300m.dispense(BEAD_VOL, col.bottom(2))
        p300m.blow_out(col.top(-2))
    p300m.drop_tip()

    # ---------------- isopropanol ----------------
    p300m.pick_up_tip()
    for i, col in enumerate(sample_cols):
        src = ipa[0] if i < n_cols // 2 else ipa[1]
        for v in chunks(IPA_VOL):
            p300m.aspirate(v, src.bottom(1.5))
            p300m.dispense(v, col.top(-2), rate=0.8)
            p300m.blow_out(col.top(-2))
    p300m.drop_tip()

    # ---------------- samples: 250 uL, new tip each, mix 5x ----------------
    for src, dst in zip(sources[:N_SAMPLES], sample_wells):
        p1000.pick_up_tip()
        p1000.aspirate(SAMPLE_VOL, src.bottom(2))
        p1000.dispense(SAMPLE_VOL, dst.bottom(2))
        p1000.mix(5, 400, dst.bottom(2))
        p1000.blow_out(dst.top(-2))
        p1000.drop_tip()

    # ---------------- incubate 5 min at room temperature ----------------
    protocol.delay(minutes=5, msg='Incubate 5 min at room temperature')

    # ---------------- magnet 4 min, remove supernatant ----------------
    mag.engage()
    protocol.delay(minutes=4, msg='Magnet engaged 4 min')

    def remove_liquid(volume):
        for col, wcol in zip(sample_cols, waste_cols):
            p300m.pick_up_tip()
            for v in chunks(volume):
                p300m.aspirate(v, col.bottom(0.8), rate=0.4)
                p300m.dispense(v, wcol.top(-2))
                p300m.blow_out(wcol.top(-2))
            p300m.drop_tip()

    remove_liquid(TOTAL_VOL)

    # ---------------- two ethanol 70% washes ----------------
    for wash_src in (etoh_wash1, etoh_wash2):
        p300m.pick_up_tip()
        for i, col in enumerate(sample_cols):
            src = wash_src[0] if i < n_cols // 2 else wash_src[1]
            for v in chunks(ETOH_VOL):
                p300m.aspirate(v, src.bottom(1.5))
                p300m.dispense(v, col.top(-2), rate=0.8)
                p300m.blow_out(col.top(-2))
        p300m.drop_tip()
        remove_liquid(ETOH_VOL)

    # ---------------- air dry 4 min ----------------
    protocol.delay(minutes=4, msg='Air dry 4 min')

    # ---------------- elution ----------------
    mag.disengage()
    for col in sample_cols:
        p300m.pick_up_tip()
        p300m.aspirate(ELUTION_VOL, elution_buffer.bottom(1.5))
        p300m.dispense(ELUTION_VOL, col.bottom(2))
        p300m.mix(5, 80, col.bottom(2))
        p300m.blow_out(col.top(-2))
        p300m.drop_tip()
    protocol.delay(seconds=30, msg='Wait 30 s before engaging magnet')
    mag.engage()
    protocol.delay(seconds=90, msg='Wait 90 s for bead separation')

    for col, ecol in zip(sample_cols, elution_cols):
        p300m.pick_up_tip()
        p300m.aspirate(ELUTION_VOL, col.bottom(0.8), rate=0.4)
        p300m.dispense(ELUTION_VOL, ecol.bottom(1.5))
        p300m.blow_out(ecol.top(-1))
        p300m.drop_tip()

    mag.disengage()
