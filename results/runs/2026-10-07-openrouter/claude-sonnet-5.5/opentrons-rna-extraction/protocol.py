import math

metadata = {
    'protocolName': 'Magnetic-bead SARS-CoV-2 RNA extraction (48 samples, OT-2)',
    'description': 'In-house magnetic-bead RNA extraction, 48 samples',
    'apiLevel': '2.13',
}

N_COLS = 6            # 48 samples = 6 columns x 8 rows (odd columns of plate)
MAX_TIP_VOL = 200     # filter tip capacity for the p300 multi


def run(protocol):
    # ---------------- labware / modules ----------------
    tips200 = [protocol.load_labware('opentrons_96_filtertiprack_200ul', s)
               for s in (2, 3, 9)]
    tips1000 = protocol.load_labware('opentrons_96_filtertiprack_1000ul', 11)
    waste = protocol.load_labware('usascientific_96_wellplate_2.4ml_deep', 1)
    reservoir = protocol.load_labware('nest_12_reservoir_15ml', 5)
    racks = [
        protocol.load_labware(
            'opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', 10),
        protocol.load_labware(
            'opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', 7),
    ]

    mag = protocol.load_module('magnetic module', 4)
    plate = mag.load_labware('usascientific_96_wellplate_2.4ml_deep')
    temp = protocol.load_module('tempdeck', 6)
    elu_plate = temp.load_labware('thermo_96_wellplate_200ul')

    p1000 = protocol.load_instrument('p1000_single_gen2', 'left',
                                     tip_racks=[tips1000])
    p300 = protocol.load_instrument('p300_multi_gen2', 'right',
                                    tip_racks=tips200)

    # ---------------- layout ----------------
    sample_cols = plate.rows()[0][0::2]          # A1, A3, ... A11
    waste_cols = waste.rows()[0][0::2]
    elu_cols = elu_plate.rows()[0][0::2]

    beads = reservoir['A2']
    elution_buffer = reservoir['A4']
    ipa = [reservoir['A6'], reservoir['A7']]
    etoh = [reservoir['A9'], reservoir['A10'], reservoir['A11'],
            reservoir['A12']]

    def split(vol):
        n = math.ceil(vol / MAX_TIP_VOL)
        return n, vol / n

    def add_reagent(vol, source_for_col):
        """Dispense vol into every sample column with the currently held tip.
        The tip never enters/aspirates from a sample well."""
        n, chunk = split(vol)
        for i, col in enumerate(sample_cols):
            src = source_for_col(i)
            for _ in range(n):
                p300.aspirate(chunk, src)
                p300.dispense(chunk, col.top(-2))
            p300.blow_out(col.top(-2))

    def remove_liquid(vol):
        """Remove vol from each sample column to waste, fresh tip per column."""
        n, chunk = split(vol)
        for i, col in enumerate(sample_cols):
            p300.pick_up_tip()
            for _ in range(n):
                p300.aspirate(chunk, col.bottom(1))
                p300.dispense(chunk, waste_cols[i].top(-3))
            p300.blow_out(waste_cols[i].top(-3))
            p300.drop_tip()

    # ---------------- step 1: module setup ----------------
    mag.disengage()
    temp.set_temperature(4)

    # ---------------- step 2: magnetic beads ----------------
    p300.pick_up_tip()
    p300.mix(5, 150, beads)
    add_reagent(40, lambda i: beads)
    p300.drop_tip()

    # ---------------- step 3: isopropanol ----------------
    p300.pick_up_tip()
    add_reagent(250, lambda i: ipa[i // 3])
    p300.drop_tip()

    # ---------------- step 4: samples ----------------
    for s in range(48):
        rack = racks[s // 24]
        tube = rack.wells()[s % 24]
        dest = plate.columns()[2 * (s // 8)][s % 8]
        p1000.pick_up_tip()
        p1000.aspirate(250, tube.bottom(3))
        p1000.dispense(250, dest.bottom(5))
        p1000.mix(5, 400, dest.bottom(3))
        p1000.blow_out(dest.top(-2))
        p1000.drop_tip()

    # ---------------- step 5: incubation ----------------
    protocol.delay(minutes=5)

    # ---------------- step 6: magnet ----------------
    mag.engage()
    protocol.delay(minutes=4)

    # ---------------- step 7: remove supernatant ----------------
    p300.flow_rate.aspirate = 50
    remove_liquid(540)

    # ---------------- steps 8-9: ethanol washes ----------------
    for _ in range(2):
        p300.flow_rate.aspirate = 92.86      # default
        p300.pick_up_tip()
        add_reagent(500, lambda i: etoh[i % 4])
        p300.drop_tip()
        p300.flow_rate.aspirate = 50
        remove_liquid(500)
    p300.flow_rate.aspirate = 92.86

    # ---------------- step 10: air dry ----------------
    protocol.delay(minutes=4)

    # ---------------- step 11: elution ----------------
    mag.disengage()
    for col in sample_cols:
        p300.pick_up_tip()
        p300.aspirate(100, elution_buffer)
        p300.dispense(100, col.bottom(2))
        p300.mix(10, 70, col.bottom(1))
        p300.blow_out(col.top(-2))
        p300.drop_tip()

    # ---------------- step 12 ----------------
    protocol.delay(seconds=30)
    mag.engage()
    protocol.delay(seconds=90)

    # ---------------- step 13: transfer eluate ----------------
    p300.flow_rate.aspirate = 30
    for i, col in enumerate(sample_cols):
        p300.pick_up_tip()
        p300.aspirate(80, col.bottom(0.7))
        p300.dispense(80, elu_cols[i].bottom(2))
        p300.drop_tip()
    p300.flow_rate.aspirate = 92.86

    # ---------------- step 14 ----------------
    mag.disengage()
