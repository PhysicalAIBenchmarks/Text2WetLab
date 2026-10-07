"""
OT-2 in-house magnetic-bead SARS-CoV-2 RNA extraction, 48 samples.

Based on Lazaro-Perona et al., "Automated low-cost SARS-CoV-2 RNA extraction
protocols", PLOS ONE 2021 (doi:10.1371/journal.pone.0246302), OT-2in-house
protocol:

 1. 40 uL magnetic beads + 250 uL isopropanol + 250 uL inactivated sample per
    well, mix by pipetting 5 times, incubate 5 min at room temperature.
 2. Engage the GEN1 magnetic module for 4 min.
 3. Collect the supernatant and discard.
 4. Add 500 uL 70% ethanol, collect and discard.
 5. Add 500 uL 70% ethanol, collect and discard.
 6. Air dry 4 min.
 7. Disengage the magnet and add 100 uL elution buffer.
 8. After 30 s engage the magnet.
 9. After 90 s collect the supernatant (eluate) into a 96-well plate.

Sample n (1-48) is taken from tube rack slot 10 (samples 1-24) or slot 7
(samples 25-48), in rack order A1, B1, C1, D1, A2, ...  It goes to the n-th
well of the odd columns (1, 3, 5, 7, 9, 11) of the magnetic-module plate, in
column order A1..H1, A3..H3, ...  Its eluate goes to the same well position on
the elution plate (slot 6, kept at 4 C).
"""
import math

from opentrons import protocol_api
from opentrons.types import Point

metadata = {
    'protocolName': 'SARS-CoV-2 RNA extraction - OT-2 in-house magnetic beads (48 samples)',
    'description': 'Magnetic-bead RNA extraction (Lazaro-Perona et al., PLOS ONE 2021)',
    'apiLevel': '2.13',
}

NUM_SAMPLES = 48
SAMPLE_COLUMNS = [1, 3, 5, 7, 9, 11]

# Volumes (uL), Table 1 of the paper
BEADS_VOL = 40
ISOPROPANOL_VOL = 250
SAMPLE_VOL = 250
ETHANOL_VOL = 500
ELUTION_VOL = 100
BINDING_VOL = BEADS_VOL + ISOPROPANOL_VOL + SAMPLE_VOL  # 540 uL supernatant

# Times
BINDING_INCUBATION_MIN = 5
MAGNET_BINDING_MIN = 4
AIR_DRY_MIN = 4
ELUTION_BEFORE_MAGNET_SEC = 30
ELUTION_MAGNET_SEC = 90

SAMPLE_MIX_REPS = 5
ELUTION_MIX_REPS = 10

TIP_200_MAX = 200


def run(protocol: protocol_api.ProtocolContext):
    # ---------------------------------------------------------------- labware
    waste_plate = protocol.load_labware(
        'usascientific_96_wellplate_2.4ml_deep', '1', 'waste plate')
    tips200 = [protocol.load_labware('opentrons_96_filtertiprack_200ul', slot)
               for slot in ['2', '3', '9']]
    tips1000 = [protocol.load_labware('opentrons_96_filtertiprack_1000ul', '11')]

    magdeck = protocol.load_module('magnetic module', '4')
    mag_plate = magdeck.load_labware(
        'usascientific_96_wellplate_2.4ml_deep', 'extraction plate')

    reservoir = protocol.load_labware('nest_12_reservoir_15ml', '5', 'reagents')

    tempdeck = protocol.load_module('tempdeck', '6')
    elution_plate = tempdeck.load_labware(
        'thermo_96_wellplate_200ul', 'elution plate')

    rack_1_24 = protocol.load_labware(
        'opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', '10',
        'samples 1-24')
    rack_25_48 = protocol.load_labware(
        'opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', '7',
        'samples 25-48')

    p1000 = protocol.load_instrument(
        'p1000_single_gen2', 'left', tip_racks=tips1000)
    m300 = protocol.load_instrument(
        'p300_multi_gen2', 'right', tip_racks=tips200)
    default_aspirate = m300.flow_rate.aspirate
    default_dispense = m300.flow_rate.dispense

    # --------------------------------------------------------------- reagents
    beads = reservoir['A2']
    elution_buffer = reservoir['A4']
    isopropanol = [reservoir['A6'], reservoir['A7']]   # 3 sample columns each
    ethanol_wash_1 = [reservoir['A9'], reservoir['A10']]
    ethanol_wash_2 = [reservoir['A11'], reservoir['A12']]

    def source_for(column_index, sources):
        """Split the 6 sample columns evenly over the reservoir columns."""
        per_source = math.ceil(len(SAMPLE_COLUMNS) / len(sources))
        return sources[column_index // per_source]

    # ---------------------------------------------------------- sample layout
    sample_tubes = (rack_1_24.wells() + rack_25_48.wells())[:NUM_SAMPLES]
    mag_wells = [well for col in SAMPLE_COLUMNS
                 for well in mag_plate.columns_by_name()[str(col)]][:NUM_SAMPLES]
    num_cols = math.ceil(NUM_SAMPLES / 8)
    mag_cols = [mag_plate.columns_by_name()[str(c)][0]
                for c in SAMPLE_COLUMNS[:num_cols]]
    elution_cols = [elution_plate.columns_by_name()[str(c)][0]
                    for c in SAMPLE_COLUMNS[:num_cols]]
    # supernatant of plate column c -> waste column c; washes -> column c + 1
    waste_binding = [waste_plate.columns_by_name()[str(c)][0]
                     for c in SAMPLE_COLUMNS[:num_cols]]
    waste_washes = [waste_plate.columns_by_name()[str(c + 1)][0]
                    for c in SAMPLE_COLUMNS[:num_cols]]

    def split(volume, max_vol=TIP_200_MAX):
        n = math.ceil(volume / max_vol)
        return [volume / n] * n

    def pellet_side(well, z=1.0):
        """Aspiration point at the bottom, offset away from the bead pellet."""
        return well.bottom(z).move(Point(x=-1, y=0, z=0))

    def remove_liquid(volume, waste_wells):
        """Discard `volume` uL from every sample column, fresh tip per column."""
        m300.flow_rate.aspirate = 40
        m300.flow_rate.dispense = 150
        for src, dest in zip(mag_cols, waste_wells):
            m300.pick_up_tip()
            for vol in split(volume):
                m300.aspirate(vol, pellet_side(src))
                m300.dispense(vol, dest.top(-5))
                m300.blow_out(dest.top(-5))
            m300.drop_tip()
        m300.flow_rate.aspirate = default_aspirate
        m300.flow_rate.dispense = default_dispense

    def add_ethanol(sources):
        """Add 500 uL 70% ethanol from the top of the wells, one tip."""
        m300.pick_up_tip()
        for i, dest in enumerate(mag_cols):
            src = source_for(i, sources)
            for vol in split(ETHANOL_VOL):
                m300.aspirate(vol, src.bottom(1))
                m300.dispense(vol, dest.top(-3))
                m300.blow_out(dest.top(-3))
        m300.drop_tip()

    # ---------------------------------------------------------------- startup
    magdeck.disengage()
    protocol.comment('Cooling elution plate to 4 C')
    tempdeck.set_temperature(4)

    # ---------------------------------------------- 1. binding mix: 40 uL beads
    protocol.comment('Step 1a: 40 uL magnetic beads per well')
    m300.pick_up_tip()
    m300.mix(10, 100, beads.bottom(1))  # resuspend settled beads
    for dest in mag_cols:
        m300.mix(2, 100, beads.bottom(1))
        m300.aspirate(BEADS_VOL, beads.bottom(1))
        m300.dispense(BEADS_VOL, dest.bottom(2))
        m300.blow_out(dest.top(-5))
    m300.drop_tip()

    # ---------------------------------------- 1. binding mix: 250 uL isopropanol
    protocol.comment('Step 1b: 250 uL isopropanol per well')
    m300.pick_up_tip()
    for i, dest in enumerate(mag_cols):
        src = source_for(i, isopropanol)
        for vol in split(ISOPROPANOL_VOL):
            m300.aspirate(vol, src.bottom(1))
            m300.dispense(vol, dest.top(-5))
            m300.blow_out(dest.top(-5))
    m300.drop_tip()

    # -------------------------------------- 1. binding mix: 250 uL sample + mix
    protocol.comment('Step 1c: 250 uL inactivated sample per well, mix 5 times')
    for tube, dest in zip(sample_tubes, mag_wells):
        p1000.pick_up_tip()
        p1000.aspirate(SAMPLE_VOL, tube.bottom(2))
        p1000.dispense(SAMPLE_VOL, dest.bottom(3))
        p1000.mix(SAMPLE_MIX_REPS, 400, dest.bottom(3))
        p1000.blow_out(dest.top(-5))
        p1000.drop_tip()

    protocol.comment('Step 1d: incubate 5 min at room temperature')
    protocol.delay(minutes=BINDING_INCUBATION_MIN)

    # ------------------------------------------------------- 2. magnet 4 min
    protocol.comment('Step 2: engage magnetic module, 4 min')
    magdeck.engage()  # labware default engage height for this deep-well plate
    protocol.delay(minutes=MAGNET_BINDING_MIN)

    # ------------------------------------------------- 3. discard supernatant
    protocol.comment('Step 3: discard supernatant')
    remove_liquid(BINDING_VOL, waste_binding)

    # ------------------------------------------------------------ 4. wash 1
    protocol.comment('Step 4: wash 1, 500 uL 70% ethanol')
    add_ethanol(ethanol_wash_1)
    remove_liquid(ETHANOL_VOL, waste_washes)

    # ------------------------------------------------------------ 5. wash 2
    protocol.comment('Step 5: wash 2, 500 uL 70% ethanol')
    add_ethanol(ethanol_wash_2)
    remove_liquid(ETHANOL_VOL, waste_washes)

    # ------------------------------------------------------------ 6. air dry
    protocol.comment('Step 6: air dry beads, 4 min')
    protocol.delay(minutes=AIR_DRY_MIN)

    # ------------------------------------- 7. magnet off, 100 uL elution buffer
    protocol.comment('Step 7: disengage magnet, add 100 uL elution buffer')
    magdeck.disengage()
    for dest in mag_cols:
        m300.pick_up_tip()
        m300.aspirate(ELUTION_VOL, elution_buffer.bottom(1))
        m300.dispense(ELUTION_VOL, dest.bottom(1))
        m300.mix(ELUTION_MIX_REPS, 80, dest.bottom(1))  # resuspend beads
        m300.blow_out(dest.top(-5))
        m300.drop_tip()

    # ------------------------------------------------- 8. after 30 s, magnet
    protocol.comment('Step 8: wait 30 s, engage magnetic module')
    protocol.delay(seconds=ELUTION_BEFORE_MAGNET_SEC)
    magdeck.engage()

    # ----------------------------------------- 9. after 90 s, recover eluate
    protocol.comment('Step 9: wait 90 s, transfer eluate to the elution plate')
    protocol.delay(seconds=ELUTION_MAGNET_SEC)
    m300.flow_rate.aspirate = 20
    m300.flow_rate.dispense = 50
    for src, dest in zip(mag_cols, elution_cols):
        m300.pick_up_tip()
        m300.aspirate(ELUTION_VOL, pellet_side(src, z=0.5))
        m300.dispense(ELUTION_VOL, dest.bottom(2))
        m300.blow_out(dest.top(-2))
        m300.drop_tip()

    magdeck.disengage()
    protocol.comment('Done. Eluates are held at 4 C on the temperature module.')
