from opentrons import protocol_api

metadata = {'protocolName': 'In-house OT-2 magnetic-bead RNA extraction (48 samples)',
            'apiLevel': '2.13'}

N_COLS = 6
MAX = 190


def run(protocol: protocol_api.ProtocolContext):
    waste = protocol.load_labware('usascientific_96_wellplate_2.4ml_deep', 1)
    tr200 = [protocol.load_labware('opentrons_96_filtertiprack_200ul', s) for s in (2, 3, 9)]
    mag = protocol.load_module('magnetic module', 4)
    plate = mag.load_labware('usascientific_96_wellplate_2.4ml_deep')
    temp = protocol.load_module('tempdeck', 6)
    elplate = temp.load_labware('thermo_96_wellplate_200ul')
    res = protocol.load_labware('nest_12_reservoir_15ml', 5)
    rack1 = protocol.load_labware('opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', 10)
    rack2 = protocol.load_labware('opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', 7)
    tr1000 = protocol.load_labware('opentrons_96_filtertiprack_1000ul', 11)

    p1000 = protocol.load_instrument('p1000_single_gen2', 'left', tip_racks=[tr1000])
    m300 = protocol.load_instrument('p300_multi_gen2', 'right', tip_racks=tr200)

    cols = [plate.rows()[0][2 * i] for i in range(N_COLS)]
    wcols = [waste.rows()[0][2 * i] for i in range(N_COLS)]
    ecols = [elplate.rows()[0][2 * i] for i in range(N_COLS)]
    beads = res.rows()[0][1]
    elbuf = res.rows()[0][3]
    iso = [res.rows()[0][5], res.rows()[0][6]]
    etoh = [res.rows()[0][8 + i] for i in range(4)]

    def dispense_vol(src, dst, vol, top=True):
        """Reagent dispense with a tip that never touches samples."""
        n = -(-vol // MAX)
        each = vol / n
        for _ in range(n):
            m300.aspirate(each, src)
            m300.dispense(each, dst.top(-2))
            m300.touch_tip(dst, v_offset=-2) if False else None

    def remove(vol, i):
        n = -(-vol // MAX)
        each = vol / n
        for _ in range(n):
            m300.aspirate(each, cols[i].bottom(1.0), rate=0.3)
            m300.dispense(each, wcols[i].top(-2))
        m300.blow_out(wcols[i].top(-2))

    # 1
    mag.disengage()
    temp.start_set_temperature(4)
    temp.await_temperature(4)

    # 2 beads
    m300.pick_up_tip()
    for i in range(N_COLS):
        m300.mix(3, 150, beads) if i == 0 else None
        m300.aspirate(40, beads)
        m300.dispense(40, cols[i].top(-2))
    m300.drop_tip()

    # 3 isopropanol
    m300.pick_up_tip()
    for i in range(N_COLS):
        dispense_vol(iso[i % 2], cols[i], 250)
    m300.drop_tip()

    # 4 samples
    for s in range(48):
        rack = rack1 if s < 24 else rack2
        src = rack.wells()[s % 24]
        dst = plate.rows()[s % 8][2 * (s // 8)]
        p1000.pick_up_tip()
        p1000.aspirate(250, src.bottom(2))
        p1000.dispense(250, dst)
        p1000.mix(5, 400, dst)
        p1000.blow_out(dst.top(-2))
        p1000.drop_tip()

    # 5
    protocol.delay(minutes=5)
    # 6
    mag.engage()
    protocol.delay(minutes=4)

    # 7
    for i in range(N_COLS):
        m300.pick_up_tip()
        remove(540, i)
        m300.drop_tip()

    # 8, 9
    for w in range(2):
        m300.pick_up_tip()
        for i in range(N_COLS):
            dispense_vol(etoh[i % 4], cols[i], 500)
        m300.drop_tip()
        for i in range(N_COLS):
            m300.pick_up_tip()
            remove(500, i)
            m300.drop_tip()

    # 10
    protocol.delay(minutes=4)

    # 11
    mag.disengage()
    m300.pick_up_tip()
    for i in range(N_COLS):
        dispense_vol(elbuf, cols[i], 100)
    m300.drop_tip()
    for i in range(N_COLS):
        m300.pick_up_tip()
        m300.mix(10, 80, cols[i].bottom(1))
        m300.drop_tip()

    # 12
    protocol.delay(seconds=30)
    mag.engage()
    protocol.delay(seconds=90)

    # 13
    for i in range(N_COLS):
        m300.pick_up_tip()
        m300.aspirate(80, cols[i].bottom(1.0), rate=0.3)
        m300.dispense(80, ecols[i])
        m300.drop_tip()

    # 14
    mag.disengage()
