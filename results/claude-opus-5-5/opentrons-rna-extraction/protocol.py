"""In-house OT-2 magnetic-bead SARS-CoV-2 RNA extraction, 48 samples.

Based on "Automated low-cost SARS-CoV-2 RNA extraction protocols"
(PLOS ONE 2021, doi:10.1371/journal.pone.0246302).
"""
from opentrons import protocol_api

metadata = {
    'protocolName': 'Magnetic-bead RNA extraction (48 samples)',
    'author': 'Automated from PLOS ONE 2021 in-house protocol',
    'description': 'Isopropanol/bead binding, two 70% EtOH washes, '
                   'elution to 4 C plate.',
    'apiLevel': '2.13',
}

NUM_SAMPLES = 48
SAMPLE_COLS = [1, 3, 5, 7, 9, 11]

BEAD_VOL = 40
ISO_VOL = 250
SAMPLE_VOL = 250
SUPERNATANT_VOL = 540
ETOH_VOL = 500
ELUTION_VOL = 100
ELUATE_VOL = 80


def run(protocol: protocol_api.ProtocolContext):
    # ---------------- labware ----------------
    waste = protocol.load_labware('usascientific_96_wellplate_2.4ml_deep', 1)
    tips200 = [protocol.load_labware('opentrons_96_filtertiprack_200ul', s)
               for s in (2, 3, 9)]
    magdeck = protocol.load_module('magnetic module', 4)
    mag_plate = magdeck.load_labware('usascientific_96_wellplate_2.4ml_deep')
    reservoir = protocol.load_labware('nest_12_reservoir_15ml', 5)
    tempdeck = protocol.load_module('tempdeck', 6)
    elution_plate = tempdeck.load_labware('thermo_96_wellplate_200ul')
    racks = [
        protocol.load_labware(
            'opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', 10),
        protocol.load_labware(
            'opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', 7),
    ]
    tips1000 = [protocol.load_labware('opentrons_96_filtertiprack_1000ul', 11)]

    p1000 = protocol.load_instrument('p1000_single_gen2', 'left',
                                     tip_racks=tips1000)
    m300 = protocol.load_instrument('p300_multi_gen2', 'right',
                                    tip_racks=tips200)

    # ---------------- reagents ----------------
    beads = reservoir['A2']
    elution_buffer = reservoir['A4']
    isopropanol = [reservoir['A6'], reservoir['A7']]
    etoh_wash1 = [reservoir['A9'], reservoir['A10']]
    etoh_wash2 = [reservoir['A11'], reservoir['A12']]

    # column tops (multichannel targets) on the magnetic plate, odd columns
    mag_cols = [mag_plate['A{}'.format(c)] for c in SAMPLE_COLS]
    waste_cols = [waste['A{}'.format(c)] for c in SAMPLE_COLS]
    elution_cols = [elution_plate['A{}'.format(c)] for c in SAMPLE_COLS]

    # individual sample wells (column-wise: A1..H1, A3..H3, ...)
    sample_wells = [w for c in SAMPLE_COLS
                    for w in mag_plate.columns_by_name()[str(c)]]
    sample_tubes = [t for rack in racks for t in rack.wells()]
    assert len(sample_wells) == len(sample_tubes) == NUM_SAMPLES

    def source_for(sources, idx):
        """Split 6 sample columns evenly across reservoir columns."""
        per = len(SAMPLE_COLS) // len(sources)
        return sources[min(idx // per, len(sources) - 1)]

    def split_volume(vol, max_vol=200):
        """Split a volume into equal chunks that fit a 200 uL filter tip."""
        n = -(-vol // max_vol)
        return [vol / n] * n

    def remove_supernatant(vol):
        """Remove liquid from each column to waste; fresh tips per column."""
        m300.flow_rate.aspirate = 50
        for i, (src, dst) in enumerate(zip(mag_cols, waste_cols)):
            m300.pick_up_tip()
            for v in split_volume(vol):
                m300.aspirate(v, src.bottom(1))
                m300.dispense(v, dst.top(-2))
                m300.blow_out(dst.top(-2))
            m300.drop_tip()
        m300.flow_rate.aspirate = 94

    def add_reagent_top(sources, vol):
        """Dispense reagent from the top with one (reagent-only) tip."""
        m300.pick_up_tip()
        for i, dst in enumerate(mag_cols):
            src = source_for(sources, i)
            for v in split_volume(vol):
                m300.aspirate(v, src.bottom(2))
                m300.dispense(v, dst.top(-2))
                m300.blow_out(dst.top(-2))
        m300.drop_tip()

    # ---------------- step 1: module setup ----------------
    magdeck.disengage()
    tempdeck.set_temperature(4)

    # ---------------- step 2: beads ----------------
    m300.pick_up_tip()
    m300.mix(10, 200, beads.bottom(2))
    for dst in mag_cols:
        m300.mix(2, 100, beads.bottom(2))
        m300.aspirate(BEAD_VOL, beads.bottom(2))
        m300.dispense(BEAD_VOL, dst.top(-2))
        m300.blow_out(dst.top(-2))
    m300.drop_tip()

    # ---------------- step 3: isopropanol ----------------
    add_reagent_top(isopropanol, ISO_VOL)

    # ---------------- step 4: samples ----------------
    for tube, well in zip(sample_tubes, sample_wells):
        p1000.pick_up_tip()
        p1000.aspirate(SAMPLE_VOL, tube.bottom(1))
        p1000.dispense(SAMPLE_VOL, well.bottom(2))
        p1000.mix(5, 400, well.bottom(2))
        p1000.blow_out(well.top(-2))
        p1000.drop_tip()

    # ---------------- step 5: binding incubation ----------------
    protocol.delay(minutes=5, msg='Binding: incubate 5 min at RT')

    # ---------------- step 6: magnet ----------------
    magdeck.engage()
    protocol.delay(minutes=4, msg='Bead capture: 4 min on magnet')

    # ---------------- step 7: remove supernatant ----------------
    remove_supernatant(SUPERNATANT_VOL)

    # ---------------- steps 8-9: two ethanol washes ----------------
    for etoh in (etoh_wash1, etoh_wash2):
        add_reagent_top(etoh, ETOH_VOL)
        remove_supernatant(ETOH_VOL)

    # ---------------- step 10: air dry ----------------
    protocol.delay(minutes=4, msg='Air-drying beads 4 min on magnet')

    # ---------------- step 11: elution buffer ----------------
    magdeck.disengage()
    for dst in mag_cols:
        m300.pick_up_tip()
        m300.aspirate(ELUTION_VOL, elution_buffer.bottom(2))
        m300.dispense(ELUTION_VOL, dst.bottom(2))
        m300.mix(10, 80, dst.bottom(1))
        m300.blow_out(dst.bottom(5))
        m300.drop_tip()

    # ---------------- step 12: elution incubation and capture ----------------
    protocol.delay(seconds=30, msg='Elution incubation 30 s')
    magdeck.engage()
    protocol.delay(seconds=90, msg='Bead capture: 90 s on magnet')

    # ---------------- step 13: transfer eluate ----------------
    m300.flow_rate.aspirate = 30
    for src, dst in zip(mag_cols, elution_cols):
        m300.pick_up_tip()
        m300.aspirate(ELUATE_VOL, src.bottom(1))
        m300.dispense(ELUATE_VOL, dst.bottom(1))
        m300.blow_out(dst.top(-2))
        m300.drop_tip()

    # ---------------- step 14: done ----------------
    magdeck.disengage()
