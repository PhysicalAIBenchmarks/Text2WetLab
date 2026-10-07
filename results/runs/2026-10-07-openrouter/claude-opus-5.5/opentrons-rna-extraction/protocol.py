"""OT-2 in-house magnetic-bead SARS-CoV-2 RNA extraction, 48 samples.

Based on: "Automated low-cost SARS-CoV-2 RNA extraction protocols",
PLOS ONE 2021, doi:10.1371/journal.pone.0246302 (OT-2 in-house protocol).
"""
import math

from opentrons import protocol_api

metadata = {
    'protocolName': 'SARS-CoV-2 RNA extraction - OT-2 in-house magnetic beads (48 samples)',
    'source': 'PLOS ONE 2021, doi:10.1371/journal.pone.0246302',
    'apiLevel': '2.13',
}

NUM_SAMPLES = 48
SAMPLE_COLUMNS = [1, 3, 5, 7, 9, 11]  # odd columns of the magnetic-module plate

BEAD_VOL = 40
ISOPROPANOL_VOL = 250
SAMPLE_VOL = 250
SUPERNATANT_VOL = BEAD_VOL + ISOPROPANOL_VOL + SAMPLE_VOL  # 540 uL
ETHANOL_VOL = 500
ELUTION_VOL = 100
ELUATE_VOL = 80

MULTI_MAX = 180  # working volume per stroke with 200 uL filter tips


def split_volume(total, max_vol=MULTI_MAX):
    """Split a volume into equal strokes no larger than max_vol."""
    n = math.ceil(total / max_vol)
    return [total / n] * n


def run(protocol: protocol_api.ProtocolContext):
    # ---------------------------------------------------------------- labware
    waste_plate = protocol.load_labware('usascientific_96_wellplate_2.4ml_deep', '1')
    tips200 = [protocol.load_labware('opentrons_96_filtertiprack_200ul', slot)
               for slot in ['2', '3', '9']]
    mag_mod = protocol.load_module('magnetic module', '4')
    mag_plate = mag_mod.load_labware('usascientific_96_wellplate_2.4ml_deep')
    reservoir = protocol.load_labware('nest_12_reservoir_15ml', '5')
    temp_mod = protocol.load_module('tempdeck', '6')
    elution_plate = temp_mod.load_labware('thermo_96_wellplate_200ul')
    tubes_1_24 = protocol.load_labware(
        'opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', '10')
    tubes_25_48 = protocol.load_labware(
        'opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', '7')
    tips1000 = [protocol.load_labware('opentrons_96_filtertiprack_1000ul', '11')]

    # --------------------------------------------------------------- pipettes
    p1000 = protocol.load_instrument('p1000_single_gen2', 'left', tip_racks=tips1000)
    m300 = protocol.load_instrument('p300_multi_gen2', 'right', tip_racks=tips200)

    # ---------------------------------------------------------------- liquids
    beads = reservoir['A2']
    elution_buffer = reservoir['A4']
    isopropanol = [reservoir['A6'], reservoir['A7']]   # 3 plate columns each (6 mL)
    ethanol_wash1 = [reservoir['A9'], reservoir['A10']]  # 3 plate columns each (12 mL)
    ethanol_wash2 = [reservoir['A11'], reservoir['A12']]

    def source_for(sources, col_index):
        # first three sample columns from the first trough, the rest from the second
        return sources[0] if col_index < 3 else sources[1]

    # column heads (row A) for the multichannel
    mag_cols = [mag_plate['A{}'.format(c)] for c in SAMPLE_COLUMNS]
    waste_cols = [waste_plate['A{}'.format(c)] for c in SAMPLE_COLUMNS]
    elution_cols = [elution_plate['A{}'.format(c)] for c in SAMPLE_COLUMNS]

    # single-well routing for the samples: sample i -> i-th well of the odd columns
    sample_tubes = (tubes_1_24.wells() + tubes_25_48.wells())[:NUM_SAMPLES]
    sample_wells = [w for c in SAMPLE_COLUMNS
                    for w in mag_plate.columns_by_name()[str(c)]][:NUM_SAMPLES]

    def add_reagent(source, volume, sources_per_col=None):
        """Dispense a reagent to every sample column with one tip, from above
        the liquid (the tip never enters liquid in or aspirates from sample wells)."""
        m300.pick_up_tip()
        for i, dest in enumerate(mag_cols):
            src = sources_per_col(i) if sources_per_col else source
            for vol in split_volume(volume):
                m300.aspirate(vol, src.bottom(1))
                m300.dispense(vol, dest.top(-2))
                m300.blow_out(dest.top(-2))
        m300.drop_tip()

    def remove_to_waste(volume):
        """Remove liquid from each sample column (magnet engaged) to the waste
        plate with a fresh tip per column."""
        m300.flow_rate.aspirate = 30
        for src, dest in zip(mag_cols, waste_cols):
            m300.pick_up_tip()
            for vol in split_volume(volume):
                m300.aspirate(vol, src.bottom(1))
                m300.dispense(vol, dest.top(-2))
                m300.blow_out(dest.top(-2))
            m300.drop_tip()
        m300.flow_rate.aspirate = 94

    # ---------------------------------------------------------------- step 1
    protocol.comment('Step 1: disengage magnet, set temperature module to 4 C')
    mag_mod.disengage()
    temp_mod.set_temperature(4)

    # ---------------------------------------------------------------- step 2
    protocol.comment('Step 2: 40 uL magnetic beads per well')
    m300.pick_up_tip()
    m300.mix(5, 150, beads.bottom(1))
    for dest in mag_cols:
        m300.aspirate(BEAD_VOL, beads.bottom(1))
        m300.dispense(BEAD_VOL, dest.top(-2))
        m300.blow_out(dest.top(-2))
    m300.drop_tip()

    # ---------------------------------------------------------------- step 3
    protocol.comment('Step 3: 250 uL isopropanol per well')
    add_reagent(None, ISOPROPANOL_VOL, lambda i: source_for(isopropanol, i))

    # ---------------------------------------------------------------- step 4
    protocol.comment('Step 4: 250 uL sample per well, mix 5 times')
    for tube, well in zip(sample_tubes, sample_wells):
        p1000.pick_up_tip()
        p1000.aspirate(SAMPLE_VOL, tube.bottom(1))
        p1000.dispense(SAMPLE_VOL, well.bottom(2))
        p1000.mix(5, 400, well.bottom(2))
        p1000.blow_out(well.top(-2))
        p1000.drop_tip()

    # ---------------------------------------------------------------- step 5
    protocol.comment('Step 5: incubate 5 min at room temperature')
    protocol.delay(minutes=5)

    # ---------------------------------------------------------------- step 6
    protocol.comment('Step 6: engage magnet, wait 4 min')
    mag_mod.engage()
    protocol.delay(minutes=4)

    # ---------------------------------------------------------------- step 7
    protocol.comment('Step 7: remove supernatant to waste')
    remove_to_waste(SUPERNATANT_VOL)

    # ------------------------------------------------------------ steps 8, 9
    for n, ethanol in enumerate([ethanol_wash1, ethanol_wash2], start=1):
        protocol.comment('Wash {}: add 500 uL 70% ethanol'.format(n))
        add_reagent(None, ETHANOL_VOL, lambda i, e=ethanol: source_for(e, i))
        protocol.comment('Wash {}: remove ethanol to waste'.format(n))
        remove_to_waste(ETHANOL_VOL)

    # --------------------------------------------------------------- step 10
    protocol.comment('Step 10: air-dry beads 4 min (magnet engaged)')
    protocol.delay(minutes=4)

    # --------------------------------------------------------------- step 11
    protocol.comment('Step 11: disengage magnet, add 100 uL elution buffer and mix')
    mag_mod.disengage()
    for dest in mag_cols:
        m300.pick_up_tip()
        m300.aspirate(ELUTION_VOL, elution_buffer.bottom(1))
        m300.dispense(ELUTION_VOL, dest.bottom(1))
        m300.mix(10, 80, dest.bottom(1))
        m300.blow_out(dest.top(-2))
        m300.drop_tip()

    # --------------------------------------------------------------- step 12
    protocol.comment('Step 12: wait 30 s, engage magnet, wait 90 s')
    protocol.delay(seconds=30)
    mag_mod.engage()
    protocol.delay(seconds=90)

    # --------------------------------------------------------------- step 13
    protocol.comment('Step 13: transfer 80 uL eluate to the 4 C elution plate')
    m300.flow_rate.aspirate = 20
    for src, dest in zip(mag_cols, elution_cols):
        m300.pick_up_tip()
        m300.aspirate(ELUATE_VOL, src.bottom(1))
        m300.dispense(ELUATE_VOL, dest.bottom(2))
        m300.blow_out(dest.top(-2))
        m300.drop_tip()
    m300.flow_rate.aspirate = 94

    # --------------------------------------------------------------- step 14
    protocol.comment('Step 14: disengage magnet')
    mag_mod.disengage()
