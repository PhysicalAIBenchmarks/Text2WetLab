"""
Automated in-house magnetic-bead RNA extraction of 48 samples on an Opentrons OT-2.

Reimplementation of the "OT-2 in-house" protocol of:

    Lazaro-Perona F, Rodriguez-Antolin C, Alguacil-Guillen M, Gutierrez-Arroyo A,
    Mingorance J, Garcia-Rodriguez J, et al. "Evaluation of two automated low-cost
    RNA extraction protocols for SARS-CoV-2 detection." PLoS ONE 2021;16(2):e0246302.
    doi:10.1371/journal.pone.0246302

Recipe per sample ("OT-2 in-house protocol" steps 1-9 and Table 1 of the paper):

    1. 40 uL magnetic beads + 250 uL isopropanol + 250 uL inactivated sample;
       mix by pipetting five times; incubate 5 min at room temperature
    2. engage the GEN1 magnetic module for 4 min
    3. collect the supernatant and discard it
    4. wash 1: add 500 uL ethanol 70%, collect and discard
    5. wash 2: add 500 uL ethanol 70%, collect and discard
    6. air dry for 4 min (magnets engaged)
    7. disengage the magnets and add 100 uL elution buffer
    8. after 30 s engage the magnets again
    9. after 90 s collect the supernatant (eluted RNA) into the elution plate

The binding mixture is 40 + 250 + 250 = 540 uL per well; at step 3, 500 uL of
supernatant is removed so that the bead pellet, held against the wall by the magnet,
is never aspirated (the paper: "magnetic beads are pulled to one side of the tubes
with a magnet and supernatant is discarded").  The washes at steps 4 and 5 add and
remove 500 uL each.

Deck (fixed by the operator)
----------------------------
    1   waste plate (supernatant + washes)   usascientific_96_wellplate_2.4ml_deep
    2   200 uL filter tips                   opentrons_96_filtertiprack_200ul
    3   200 uL filter tips                   opentrons_96_filtertiprack_200ul
    4   Magnetic Module GEN1 + extraction plate (usascientific_96_wellplate_2.4ml_deep)
    5   reagent reservoir                    nest_12_reservoir_15ml
            column 2      magnetic beads
            column 4      elution buffer
            columns 6-7   isopropanol
            columns 9-12  ethanol 70%
    6   Temperature Module GEN1 + elution plate (thermo_96_wellplate_200ul), 4 C
    7   samples 25-48 (2 mL tubes)           opentrons_24_tuberack_..._snapcap
    9   200 uL filter tips                   opentrons_96_filtertiprack_200ul
    10  samples 1-24 (2 mL tubes)            opentrons_24_tuberack_..._snapcap
    11  1000 uL filter tips                  opentrons_96_filtertiprack_1000ul
    12  fixed trash

Pipettes: p1000_single_gen2 (left), p300_multi_gen2 (right).

The 48 samples occupy the odd columns (1, 3, 5, 7, 9, 11) of the extraction plate,
one sample per well, and each eluate is recovered into the matching odd column of
the elution plate.  The 8-channel pipette is used for everything that happens in a
plate (the 200 uL filter tips cap it at 200 uL per aspiration, so larger volumes are
split); the single-channel p1000 is used for the tube -> plate sample transfer, with
a fresh tip per sample.

Tip budget: 8-channel 256 of the 288 available 200 uL tips, single-channel 48 of the
96 available 1000 uL tips.
"""

from opentrons import protocol_api
from opentrons.types import Point

metadata = {
    'protocolName': 'SARS-CoV-2 RNA extraction - in-house magnetic beads - 48 samples',
    'author': 'Hospital Universitario La Paz, Madrid (reimplemented)',
    'source': 'PLoS ONE 2021;16(2):e0246302 - OT-2 in-house protocol',
    'apiLevel': '2.13',
}


# ----------------------------------------------------------------------------
# Protocol constants (values as described in the paper)
# ----------------------------------------------------------------------------

SAMPLE_COUNT = 48
CHANNELS = 8
# Odd columns of the extraction / waste / elution plates hold the samples.
PLATE_COLUMNS = ['1', '3', '5', '7', '9', '11']

# Reagent volumes per sample, uL (paper Table 1, "OT-2 in-house" column).
BEADS_VOLUME = 40.0             # magnetic beads, Mag-Bind TotalPure NGS
ISOPROPANOL_VOLUME = 250.0      # isopropanol absolute
SAMPLE_VOLUME = 250.0           # inactivated sample
SUPERNATANT_VOLUME = 500.0      # removed after binding (540 uL mix, pellet spared)
WASH_VOLUME = 500.0             # ethanol 70%, per wash
WASH_COUNT = 2                  # two washes
ELUTION_VOLUME = 100.0          # elution buffer, recovered in full

# Mixing, "mix by pipetting five times".
MIX_REPETITIONS = 5
MIX_VOLUME = 250.0

# Incubation / magnet / drying times.
BIND_INCUBATION_MIN = 5         # step 1: 5 min at room temperature
MAGNET_SEPARATION_MIN = 4       # step 2: magnetic module activated 4 min
AIR_DRY_MIN = 4                 # step 6: air dry 4 min
ELUTION_INCUBATION_SEC = 30     # step 8: 30 s off the magnet
ELUTION_SEPARATION_SEC = 90     # step 9: 90 s on the magnet

ELUTION_TEMPERATURE = 4.0       # temperature module set point, C

# Liquid-handling parameters.
MULTI_TIP_VOLUME = 200.0        # 8-channel runs 200 uL filter tips
RESERVOIR_ASPIRATE_Z = 1.5      # mm above the reservoir bottom
PLATE_DISPENSE_Z = 5.0          # mm above the well bottom when dispensing reagents
SUPER_ASPIRATE_START_Z = 3.0    # first supernatant aspiration, mm above the bottom
SUPER_ASPIRATE_END_Z = 0.5      # last supernatant aspiration, mm above the bottom
BEAD_SIDE_OFFSET_X = 0.0        # mm: lateral offset for supernatant aspiration.
                                # On the GEN1 module the magnets sit at the
                                # interstices between wells and hold the pellet
                                # against the wall(s), so the tip aspirates from
                                # the centre of the well.  Set to +/- a couple of
                                # mm if your module pellets the beads on one side
                                # only, to move the tip away from the pellet.
WASTE_DISPENSE_Z = -5.0         # top(z=-5) of the waste well
SLOW_RATE = 0.4                 # flow-rate multiplier for supernatant removal
BLOWOUT_Z = -5.0                # top(z=-5) for blow outs

# Nominal volumes the operator has loaded into each reagent column of the
# reservoir, uL.  Isopropanol and ethanol are spread over several columns; the
# protocol empties one column before moving to the next.
BEADS_COLUMNS = ([2], [2200.0])                     # 48 x 40 = 1920 uL needed
ELUTION_COLUMNS = ([4], [5000.0])                   # 48 x 100 = 4800 uL needed
ISOPROPANOL_COLUMNS = ([6, 7], [6200.0, 6200.0])    # 48 x 250 = 12000 uL needed
ETHANOL_COLUMNS = ([9, 10, 11, 12], [12500.0] * 4)  # 48 x 500 x 2 = 48000 uL needed


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------

def split_volume(total, max_per_aspiration):
    """Split ``total`` uL into chunks that fit in one tip (8-channel: 200 uL)."""
    chunks = []
    remaining = float(total)
    while remaining > max_per_aspiration + 1e-6:
        chunks.append(max_per_aspiration)
        remaining -= max_per_aspiration
    if remaining > 1e-6:
        chunks.append(round(remaining, 6))
    return chunks


class ReagentSource:
    """A reagent that occupies one or more columns of the reservoir.

    Tracks what has been aspirated from each column and always returns a column
    that still holds the requested volume, so a column is never run dry.
    """

    def __init__(self, reservoir, columns, volumes, name):
        self.name = name
        self._wells = [reservoir.wells_by_name()['A{}'.format(c)] for c in columns]
        self._remaining = [float(v) for v in volumes]

    def take(self, volume):
        """Book ``volume`` uL and return the well it should be aspirated from."""
        for index, remaining in enumerate(self._remaining):
            if remaining + 1e-6 >= volume:
                self._remaining[index] = remaining - volume
                return self._wells[index]
        raise RuntimeError(
            'Not enough {} left in the reservoir ({} uL requested).'.format(
                self.name, volume))

    @property
    def current_well(self):
        """The first column that still holds reagent (for resuspending)."""
        for well, remaining in zip(self._wells, self._remaining):
            if remaining > 1e-6:
                return well
        raise RuntimeError('The {} reservoir is empty.'.format(self.name))


def dispense_to_column(pip, volume_per_well, source, dest_well):
    """Dispense ``volume_per_well`` uL of reagent into each well of a column.

    ``source`` is a ReagentSource; ``dest_well`` is the top (row A) well of the
    destination column - the 8 tips cover the remaining seven wells.  Volumes
    larger than the 200 uL tip are split over several aspirations.
    """
    for chunk in split_volume(volume_per_well, MULTI_TIP_VOLUME):
        source_well = source.take(chunk * CHANNELS)
        pip.aspirate(chunk, source_well.bottom(z=RESERVOIR_ASPIRATE_Z))
        pip.dispense(chunk, dest_well.bottom(z=PLATE_DISPENSE_Z))
    pip.blow_out(dest_well.top(z=BLOWOUT_Z))


def remove_from_column(pip, volume_per_well, source_well, dest_well):
    """Aspirate ``volume_per_well`` uL from each well of a column and discard it.

    Used with the magnets engaged: the bead pellet is held against the well wall,
    so every aspiration is done slowly from the centre of the well (see
    BEAD_SIDE_OFFSET_X) and the tip follows the falling liquid level, leaving the
    pellet undisturbed.
    """
    chunks = split_volume(volume_per_well, MULTI_TIP_VOLUME)
    last = len(chunks) - 1
    for index, chunk in enumerate(chunks):
        z = SUPER_ASPIRATE_START_Z + (
            (SUPER_ASPIRATE_END_Z - SUPER_ASPIRATE_START_Z) * index / last
            if last else 0.0)
        pip.aspirate(
            chunk,
            source_well.bottom(z=z).move(Point(x=BEAD_SIDE_OFFSET_X)),
            rate=SLOW_RATE)
        pip.dispense(chunk, dest_well.top(z=WASTE_DISPENSE_Z))
        pip.blow_out(dest_well.top(z=WASTE_DISPENSE_Z))


def run(protocol: protocol_api.ProtocolContext):
    # ------------------------------------------------------------------ deck
    waste_plate = protocol.load_labware(
        'usascientific_96_wellplate_2.4ml_deep', '1',
        label='Waste plate (supernatant and washes)')
    tipracks_200 = [
        protocol.load_labware('opentrons_96_filtertiprack_200ul', '2'),
        protocol.load_labware('opentrons_96_filtertiprack_200ul', '3'),
        protocol.load_labware('opentrons_96_filtertiprack_200ul', '9'),
    ]
    magdeck = protocol.load_module('magnetic module', '4')
    extraction_plate = magdeck.load_labware(
        'usascientific_96_wellplate_2.4ml_deep', label='Extraction plate')
    reservoir = protocol.load_labware(
        'nest_12_reservoir_15ml', '5', label='Reagent reservoir')
    tempdeck = protocol.load_module('tempdeck', '6')
    elution_plate = tempdeck.load_labware(
        'thermo_96_wellplate_200ul', label='Elution plate')
    sample_tubes_25_48 = protocol.load_labware(
        'opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', '7',
        label='Samples 25-48')
    sample_tubes_1_24 = protocol.load_labware(
        'opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', '10',
        label='Samples 1-24')
    tiprack_1000 = protocol.load_labware('opentrons_96_filtertiprack_1000ul', '11')

    p1000 = protocol.load_instrument(
        'p1000_single_gen2', 'left', tip_racks=[tiprack_1000])
    p300m = protocol.load_instrument(
        'p300_multi_gen2', 'right', tip_racks=tipracks_200)

    # --------------------------------------------------------- module set-up
    # The elution plate is kept at 4 C for the whole run and the magnets start
    # retracted.
    magdeck.disengage()
    tempdeck.set_temperature(ELUTION_TEMPERATURE)
    protocol.comment('Cooling the elution plate on the Temperature Module to '
                     '{:.0f} C.'.format(ELUTION_TEMPERATURE))
    tempdeck.await_temperature(ELUTION_TEMPERATURE)

    # --------------------------------------------------------- reagent map
    beads = ReagentSource(reservoir, BEADS_COLUMNS[0], BEADS_COLUMNS[1],
                          'magnetic beads')
    elution_buffer = ReagentSource(reservoir, ELUTION_COLUMNS[0], ELUTION_COLUMNS[1],
                                   'elution buffer')
    isopropanol = ReagentSource(reservoir, ISOPROPANOL_COLUMNS[0],
                                ISOPROPANOL_COLUMNS[1], 'isopropanol')
    ethanol = ReagentSource(reservoir, ETHANOL_COLUMNS[0], ETHANOL_COLUMNS[1],
                            'ethanol 70%')

    # Sample routing: extraction-plate column k takes the four tubes of column k
    # of the slot-10 rack (samples 1-24) and the four tubes of column k of the
    # slot-7 rack (samples 25-48), one sample per well, rows A-H.
    sample_routes = []
    for index, column in enumerate(PLATE_COLUMNS):
        tubes = sample_tubes_1_24.columns()[index] + sample_tubes_25_48.columns()[index]
        wells = extraction_plate.columns_by_name()[column]
        sample_routes += list(zip(tubes, wells))
    if len(sample_routes) != SAMPLE_COUNT:
        raise RuntimeError('Expected {} sample routes, built {}.'.format(
            SAMPLE_COUNT, len(sample_routes)))

    waste_columns = {c: waste_plate.columns_by_name()[c][0] for c in PLATE_COLUMNS}
    elution_columns = {c: elution_plate.columns_by_name()[c][0] for c in PLATE_COLUMNS}
    extraction_columns = {c: extraction_plate.columns_by_name()[c][0]
                          for c in PLATE_COLUMNS}

    # ==================================================================
    # Step 1a - 40 uL of magnetic beads into every sample well.
    # Beads and isopropanol are dispensed before the samples, so the tips
    # only ever touch shared reagent: one tip set serves all six columns.
    # ==================================================================
    protocol.comment('Step 1a: {} uL of magnetic beads per well.'.format(
        int(BEADS_VOLUME)))
    p300m.pick_up_tip()
    for column in PLATE_COLUMNS:
        # Keep the bead suspension homogeneous before aspirating from it.
        p300m.mix(3, 100.0,
                  beads.current_well.bottom(z=RESERVOIR_ASPIRATE_Z + 1.0))
        dispense_to_column(p300m, BEADS_VOLUME, beads, extraction_columns[column])
    p300m.drop_tip()

    # ==================================================================
    # Step 1b - 250 uL of isopropanol into every sample well.
    # ==================================================================
    protocol.comment('Step 1b: {} uL of isopropanol per well.'.format(
        int(ISOPROPANOL_VOLUME)))
    p300m.pick_up_tip()
    for column in PLATE_COLUMNS:
        dispense_to_column(p300m, ISOPROPANOL_VOLUME, isopropanol,
                           extraction_columns[column])
    p300m.drop_tip()

    # ==================================================================
    # Step 1c - 250 uL of each inactivated sample, then mix by pipetting
    # five times.  Fresh 1000 uL filter tip for every sample.
    # ==================================================================
    protocol.comment('Step 1c: {} uL of each of the {} samples, mixed {} times '
                     'with {} uL.'.format(int(SAMPLE_VOLUME), SAMPLE_COUNT,
                                          MIX_REPETITIONS, int(MIX_VOLUME)))
    p1000.flow_rate.aspirate = 150.0
    p1000.flow_rate.dispense = 150.0
    for number, (tube, well) in enumerate(sample_routes, start=1):
        p1000.pick_up_tip()
        p1000.aspirate(SAMPLE_VOLUME, tube.bottom(z=1.0))
        p1000.dispense(SAMPLE_VOLUME, well.bottom(z=PLATE_DISPENSE_Z))
        p1000.blow_out(well.top(z=BLOWOUT_Z))
        p1000.mix(MIX_REPETITIONS, MIX_VOLUME, well.bottom(z=2.0))
        p1000.blow_out(well.top(z=BLOWOUT_Z))
        p1000.touch_tip(well, v_offset=BLOWOUT_Z)
        p1000.drop_tip()
        if number % 8 == 0:
            protocol.comment('  {}/{} samples loaded.'.format(number, SAMPLE_COUNT))

    # ==================================================================
    # Step 1d - incubate 5 min at room temperature.
    # ==================================================================
    protocol.comment('Step 1d: incubating {} min at room temperature.'.format(
        BIND_INCUBATION_MIN))
    protocol.delay(minutes=BIND_INCUBATION_MIN,
                   msg='Binding incubation, {} min at room temperature'.format(
                       BIND_INCUBATION_MIN))

    # ==================================================================
    # Step 2 - engage the magnetic module for 4 min.
    # ==================================================================
    protocol.comment('Step 2: engaging the Magnetic Module for {} min.'.format(
        MAGNET_SEPARATION_MIN))
    magdeck.engage()
    protocol.delay(minutes=MAGNET_SEPARATION_MIN,
                   msg='Magnetic separation, {} min'.format(MAGNET_SEPARATION_MIN))

    # ==================================================================
    # Step 3 - collect the supernatant and discard it (500 uL per well).
    # Fresh tips: the supernatant carries the sample.
    # ==================================================================
    protocol.comment('Step 3: removing {} uL of supernatant per well.'.format(
        int(SUPERNATANT_VOLUME)))
    for column in PLATE_COLUMNS:
        p300m.pick_up_tip()
        remove_from_column(p300m, SUPERNATANT_VOLUME, extraction_columns[column],
                           waste_columns[column])
        p300m.drop_tip()

    # ==================================================================
    # Steps 4 and 5 - two washes with 500 uL of ethanol 70%: add, collect
    # and discard.  Each column gets a fresh tip set, which is used both to
    # dispense the ethanol and to remove it (same wells, so no carry-over).
    # ==================================================================
    for wash in range(1, WASH_COUNT + 1):
        protocol.comment('Step {}: ethanol 70% wash - {} uL in, {} uL out, per '
                         'well.'.format(wash + 3, int(WASH_VOLUME),
                                        int(WASH_VOLUME)))
        for column in PLATE_COLUMNS:
            p300m.pick_up_tip()
            dispense_to_column(p300m, WASH_VOLUME, ethanol,
                               extraction_columns[column])
            remove_from_column(p300m, WASH_VOLUME, extraction_columns[column],
                               waste_columns[column])
            p300m.drop_tip()

    # ==================================================================
    # Step 6 - air dry for 4 min with the magnets engaged.
    # ==================================================================
    protocol.comment('Step 6: air drying the beads for {} min, magnets '
                     'engaged.'.format(AIR_DRY_MIN))
    protocol.delay(minutes=AIR_DRY_MIN,
                   msg='Air dry, {} min'.format(AIR_DRY_MIN))

    # ==================================================================
    # Step 7 - disengage the magnets and add 100 uL of elution buffer.
    # Fresh tips per column: the tips touch the beads.
    # ==================================================================
    protocol.comment('Step 7: disengaging the magnets and adding {} uL of elution '
                     'buffer per well.'.format(int(ELUTION_VOLUME)))
    magdeck.disengage()
    for column in PLATE_COLUMNS:
        p300m.pick_up_tip()
        dispense_to_column(p300m, ELUTION_VOLUME, elution_buffer,
                           extraction_columns[column])
        p300m.drop_tip()

    # ==================================================================
    # Step 8 - after 30 s, engage the magnets again.
    # ==================================================================
    protocol.comment('Step 8: {} s off the magnets, then engaging for {} s.'.format(
        ELUTION_INCUBATION_SEC, ELUTION_SEPARATION_SEC))
    protocol.delay(seconds=ELUTION_INCUBATION_SEC,
                   msg='Elution incubation, {} s, magnets disengaged'.format(
                       ELUTION_INCUBATION_SEC))
    magdeck.engage()

    # ==================================================================
    # Step 9 - after 90 s, collect the supernatant and transfer it to the
    # elution plate on the Temperature Module (4 C), one well per sample.
    # ==================================================================
    protocol.delay(seconds=ELUTION_SEPARATION_SEC,
                   msg='Magnetic separation of the eluate, {} s'.format(
                       ELUTION_SEPARATION_SEC))
    protocol.comment('Step 9: recovering {} uL of eluate per sample into the '
                     'elution plate at {:.0f} C.'.format(int(ELUTION_VOLUME),
                                                         ELUTION_TEMPERATURE))
    tempdeck.set_temperature(ELUTION_TEMPERATURE)
    for column in PLATE_COLUMNS:
        p300m.pick_up_tip()
        for chunk in split_volume(ELUTION_VOLUME, MULTI_TIP_VOLUME):
            p300m.aspirate(
                chunk,
                extraction_columns[column].bottom(z=SUPER_ASPIRATE_END_Z).move(
                    Point(x=BEAD_SIDE_OFFSET_X)),
                rate=SLOW_RATE)
            p300m.dispense(chunk, elution_columns[column].bottom(z=2.0))
        p300m.blow_out(elution_columns[column].top(z=-2.0))
        p300m.drop_tip()

    # ------------------------------------------------------------------ end
    magdeck.disengage()
    protocol.comment('Run finished: {} eluates in the odd columns of the elution '
                     'plate on the Temperature Module (kept at {:.0f} C), magnets '
                     'disengaged. Remove the elution plate when ready.'.format(
                         SAMPLE_COUNT, ELUTION_TEMPERATURE))
