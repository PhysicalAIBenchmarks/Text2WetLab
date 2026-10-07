from opentrons import protocol_api

metadata = {
    'protocolName': 'OT-2 in-house magnetic bead RNA extraction (48 samples)',
    'description': 'Automated low-cost SARS-CoV-2 RNA extraction, OT-2 in-house protocol '
                   '(PLOS ONE 2021, doi:10.1371/journal.pone.0246302)',
    'apiLevel': '2.13',
}

N_SAMPLES = 48
SAMPLE_VOL = 250
IPA_VOL = 250
BEAD_VOL = 40
WASH_VOL = 500
ELUTION_VOL = 100


def run(ctx: protocol_api.ProtocolContext):
    waste = ctx.load_labware('usascientific_96_wellplate_2.4ml_deep', 1, 'waste plate')
    tips200 = [ctx.load_labware('opentrons_96_filtertiprack_200ul', s) for s in (2, 3, 9)]
    tips1000 = ctx.load_labware('opentrons_96_filtertiprack_1000ul', 11)
    mag = ctx.load_module('magnetic module', 4)
    plate = mag.load_labware('usascientific_96_wellplate_2.4ml_deep', 'sample plate')
    res = ctx.load_labware('nest_12_reservoir_15ml', 5, 'reagents')
    temp = ctx.load_module('tempdeck', 6)
    elu = temp.load_labware('thermo_96_wellplate_200ul', 'elution plate')
    racks = [ctx.load_labware('opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', 10, 'samples 1-24'),
             ctx.load_labware('opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', 7, 'samples 25-48')]

    p1000 = ctx.load_instrument('p1000_single_gen2', 'left', tip_racks=[tips1000])
    m300 = ctx.load_instrument('p300_multi_gen2', 'right', tip_racks=tips200)

    temp.start_set_temperature(4)

    beads = res['A2']
    elbuf = res['A4']
    ipa = [res['A6'], res['A7']]
    etoh = [res['A9'], res['A10'], res['A11'], res['A12']]

    cols = [1, 3, 5, 7, 9, 11]
    sample_wells = [plate.rows()[r][c - 1] for c in cols for r in range(8)]
    tubes = [t for rk in racks for t in rk.wells()]

    def big_transfer(pip, vol, src, dst, **kw):
        """Move vol in chunks of at most the tip capacity."""
        while vol > 0:
            v = min(vol, 190)
            pip.aspirate(v, src)
            pip.dispense(v, dst, **kw)
            vol -= v

    def remove_supernatant(pip, well, vol, dest):
        left = vol + 40  # small excess to clear the well
        while left > 0:
            v = min(left, 190)
            pip.aspirate(v, well.bottom(0.8), rate=0.5)
            pip.dispense(v, dest.top(-2))
            left -= v
        pip.blow_out(dest.top(-2))

    temp.await_temperature(4)
    mag.disengage()

    # 1. samples (250 uL) into odd columns of the plate
    for tube, well in zip(tubes[:N_SAMPLES], sample_wells):
        p1000.pick_up_tip()
        p1000.aspirate(SAMPLE_VOL, tube.bottom(2))
        p1000.dispense(SAMPLE_VOL, well.bottom(2))
        p1000.blow_out(well.top(-2))
        p1000.drop_tip()

    # 2. isopropanol 250 uL + beads 40 uL per sample, mix 5x, one tip per column
    for i, c in enumerate(cols):
        well = plate.rows()[0][c - 1]
        m300.pick_up_tip()
        src = ipa[i % 2]
        big_transfer(m300, IPA_VOL, src, well.top(-2), )
        m300.mix(3, 150, beads)
        m300.aspirate(BEAD_VOL, beads)
        m300.dispense(BEAD_VOL, well.top(-2))
        m300.mix(5, 190, well.bottom(2))
        m300.blow_out(well.top(-2))
        m300.drop_tip()

    # incubate 5 min at room temperature
    ctx.delay(minutes=5, msg='Binding incubation')

    # 3. magnet 4 min, discard supernatant
    mag.engage(height_from_base=6)
    ctx.delay(minutes=4, msg='Magnetic separation')
    for c in cols:
        m300.pick_up_tip()
        remove_supernatant(m300, plate.rows()[0][c - 1], SAMPLE_VOL + IPA_VOL + BEAD_VOL,
                           waste.rows()[0][c - 1])
        m300.drop_tip()

    # 4-5. two 70% ethanol washes, 500 uL each, collect and discard
    for w in range(2):
        for i, c in enumerate(cols):
            well = plate.rows()[0][c - 1]
            m300.pick_up_tip()
            src = etoh[(i + 2 * w) % 4]
            big_transfer(m300, WASH_VOL, src, well.top(-2))
            remove_supernatant(m300, well, WASH_VOL, waste.rows()[0][c - 1])
            m300.drop_tip()

    # 6. air dry 4 min
    ctx.delay(minutes=4, msg='Air dry beads')

    # 7. magnet off, 100 uL elution buffer, resuspend
    mag.disengage()
    for c in cols:
        well = plate.rows()[0][c - 1]
        m300.pick_up_tip()
        m300.aspirate(ELUTION_VOL, elbuf)
        m300.dispense(ELUTION_VOL, well.bottom(2))
        m300.mix(10, 80, well.bottom(1))
        m300.blow_out(well.top(-2))
        m300.drop_tip()

    # 8. after 30 s, magnet on
    ctx.delay(seconds=30)
    mag.engage(height_from_base=6)

    # 9. after 90 s, collect eluate into the elution plate
    ctx.delay(seconds=90)
    for c in cols:
        m300.pick_up_tip()
        m300.aspirate(ELUTION_VOL, plate.rows()[0][c - 1].bottom(0.8), rate=0.5)
        m300.dispense(ELUTION_VOL, elu.rows()[0][c - 1].bottom(1))
        m300.drop_tip()

    mag.disengage()
