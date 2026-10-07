"""
Automated low-cost SARS-CoV-2 RNA extraction on the Opentrons OT-2.

Implements the in-house OT-2 magnetic-bead protocol ("OT-2in-house") for 48
samples, as described in:

    Lazaro-Perona F, Rodriguez-Antolin C, Alguacil-Guillen M, et al.
    "Evaluation of two automated low-cost RNA extraction protocols for
    SARS-CoV-2 detection." PLoS ONE 16(2): e0246302 (2021).
    https://doi.org/10.1371/journal.pone.0246302

Per-sample reagent volumes (paper, Table 1 - OT-2in-house row):
    sample 250 uL, isopropanol 250 uL, magnetic beads 40 uL,
    wash 1 (ethanol 70%) 500 uL, wash 2 (ethanol 70%) 500 uL,
    elution buffer 100 uL.

Step order and timing (paper, "OT-2in-house protocol", steps 1-9):
    1. Dispense 40 uL magnetic beads, 250 uL isopropanol and 250 uL sample
       per well. Mix by pipetting five times. Incubate 5 min at room
       temperature.
    2. Activate the GEN1 magnetic module for 4 min.
    3. Collect the supernatant and discard.
    4. Add 500 uL ethanol 70%, collect and discard.
    5. Add 500 uL ethanol 70%, collect and discard.
    6. Air dry for 4 min.
    7. Turn off the magnetic module and add 100 uL elution buffer.
    8. After 30 s turn on the magnetic module.
    9. After 90 s collect the supernatant and transfer it to the elution
       plate (kept at 4 degC on the temperature module).

Deck layout (fixed):
    slot 1  : waste plate for removed supernatant/washes (deep well)
    slot 2/3/9 : 200 uL filter tip racks
    slot 4  : Magnetic Module GEN1 with the extraction (deep well) plate
    slot 5  : nest_12_reservoir_15ml reagent reservoir
              col 2 = magnetic beads, col 4 = elution buffer,
              cols 6-7 = isopropanol, cols 9-12 = ethanol 70%
    slot 6  : Temperature Module GEN1 with the elution plate
              (thermo_96_wellplate_200ul, custom labware), held at 4 degC
    slot 7  : samples 25-48 (2 mL tubes)
    slot 10 : samples 1-24 (2 mL tubes)
    slot 11 : 1000 uL filter tip rack
    slot 12 : fixed trash

The 48 samples occupy the odd columns (1, 3, 5, 7, 9, 11) of the plate on
the magnetic module; each eluate is recovered into the corresponding well of
the elution plate on the temperature module.
"""

from opentrons import protocol_api

metadata = {
    'protocolName': 'SARS-CoV-2 RNA extraction - OT-2 in-house magnetic beads (48 samples)',
    'author': 'After Lazaro-Perona et al., PLoS ONE 2021 (doi:10.1371/journal.pone.0246302)',
    'description': 'In-house OT-2 magnetic-bead RNA extraction, 48 samples',
    'apiLevel': '2.11',
}

# ---------------------------------------------------------------------------
# Protocol parameters (volumes in uL, taken from the paper)
# ---------------------------------------------------------------------------
BEADS_VOL = 40          # magnetic beads (Mag-Bind TotalPure NGS)
ISOPROPAVOL = 250       # isopropanol
SAMPLE_VOL = 250        # inactivated sample
WASH_VOL = 500          # ethanol 70%, per wash (two washes)
ELUTION_VOL = 100       # elution buffer
ELUATE_VOL = 90         # eluate recovered per well after the final pull

BIND_MIX_REPS = 5       # "mix by pipetting five times"
BIND_MIX_VOL = 300      # mix volume during binding (total 540 uL in well)
ELUTION_MIX_REPS = 10   # resuspend the dried beads in elution buffer
ELUTION_MIX_VOL = 80

INCUBATION_MIN = 5      # binding incubation, room temperature
MAGNET_MIN = 4          # magnet engagement before supernatant removal
DRYING_MIN = 4          # air-dry with magnets engaged
ELUTION_WAIT_S = 30     # paper step 8: magnet on 30 s after buffer
SEPARATION_S = 90       # paper step 9: collect 90 s after magnet on

# Odd columns of the extraction/elution plates holding the 48 samples.
SAMPLE_COLUMNS = ['1', '3', '5', '7', '9', '11']


def run(protocol: protocol_api.ProtocolContext):
    # -----------------------------------------------------------------------
    # Equipment
    # -----------------------------------------------------------------------
    # slot 1: waste plate for all removed supernatants and washes
    waste_plate = protocol.load_labware(
        'usascientific_96_wellplate_2.4ml_deep', '1')

    # slots 2, 3, 9: 200 uL filter tips (multichannel)
    tipracks_200 = [
        protocol.load_labware('opentrons_96_filtertiprack_200ul', slot)
        for slot in ('2', '3', '9')
    ]

    # slot 4: Magnetic Module GEN1 with the extraction plate
    mag_mod = protocol.load_module('magnetic module', '4')
    extraction_plate = mag_mod.load_labware(
        'usascientific_96_wellplate_2.4ml_deep')

    # slot 5: reagent reservoir
    reservoir = protocol.load_labware('nest_12_reservoir_15ml', '5')

    # slot 6: Temperature Module GEN1 with the elution plate (custom labware)
    temp_mod = protocol.load_module('tempdeck', '6')
    elution_plate = temp_mod.load_labware('thermo_96_wellplate_200ul')

    # slots 7 and 10: inactivated samples in 2 mL tubes
    tuberack_7 = protocol.load_labware(
        'opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', '7')
    tuberack_10 = protocol.load_labware(
        'opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', '10')

    # slot 11: 1000 uL filter tips (single channel)
    tiprack_1000 = [
        protocol.load_labware('opentrons_96_filtertiprack_1000ul', '11')]

    # pipettes
    p1000 = protocol.load_instrument(
        'p1000_single_gen2', 'left', tip_racks=tiprack_1000)
    p300 = protocol.load_instrument(
        'p300_multi_gen2', 'right', tip_racks=tipracks_200)

    # -----------------------------------------------------------------------
    # Reagent positions in the reservoir (slot 5)
    # -----------------------------------------------------------------------
    beads_source = reservoir.columns_by_name()['2']
    elution_buffer_source = reservoir.columns_by_name()['4']
    # isopropanol: columns 6-7; ethanol 70%: columns 9-12.
    # The six sample columns draw from two troughs each: plate columns
    # 1/3/5 from the first trough, plate columns 7/9/11 from the second.
    isopropanol_sources = {
        '1': reservoir.columns_by_name()['6'],
        '3': reservoir.columns_by_name()['6'],
        '5': reservoir.columns_by_name()['6'],
        '7': reservoir.columns_by_name()['7'],
        '9': reservoir.columns_by_name()['7'],
        '11': reservoir.columns_by_name()['7'],
    }
    ethanol_wash1_sources = {
        '1': reservoir.columns_by_name()['9'],
        '3': reservoir.columns_by_name()['9'],
        '5': reservoir.columns_by_name()['9'],
        '7': reservoir.columns_by_name()['10'],
        '9': reservoir.columns_by_name()['10'],
        '11': reservoir.columns_by_name()['10'],
    }
    ethanol_wash2_sources = {
        '1': reservoir.columns_by_name()['11'],
        '3': reservoir.columns_by_name()['11'],
        '5': reservoir.columns_by_name()['11'],
        '7': reservoir.columns_by_name()['12'],
        '9': reservoir.columns_by_name()['12'],
        '11': reservoir.columns_by_name()['12'],
    }

    # -----------------------------------------------------------------------
    # Sample layout: 48 samples in the odd columns of the extraction plate.
    # Samples 1-24 in tuberack slot 10, samples 25-48 in tuberack slot 7
    # (column-major tube order), mapped to plate columns 1,3,5 and 7,9,11.
    # -----------------------------------------------------------------------
    sample_sources = tuberack_10.wells()[:24] + tuberack_7.wells()[:24]
    sample_dests = []
    for col_name in SAMPLE_COLUMNS:
        sample_dests += extraction_plate.columns_by_name()[col_name]

    # -----------------------------------------------------------------------
    # Startup: magnets down, elution plate cooling to 4 degC
    # -----------------------------------------------------------------------
    mag_mod.disengage()
    temp_mod.set_temperature(4)  # keep the elution plate at 4 degC

    # -----------------------------------------------------------------------
    # Paper step 1a: 40 uL magnetic beads per well
    # -----------------------------------------------------------------------
    protocol.comment('Step 1: 40 uL magnetic beads per well')
    p300.well_bottom_clearance.aspirate = 2
    p300.well_bottom_clearance.dispense = 25
    p300.pick_up_tip()
    for col_name in SAMPLE_COLUMNS:
        p300.transfer(
            BEADS_VOL,
            beads_source,
            extraction_plate.columns_by_name()[col_name],
            new_tip='never',
            blow_out=True,
        )
    p300.drop_tip()

    # -----------------------------------------------------------------------
    # Paper step 1b: 250 uL isopropanol per well
    # -----------------------------------------------------------------------
    protocol.comment('Step 1: 250 uL isopropanol per well')
    p300.pick_up_tip()
    for col_name in SAMPLE_COLUMNS:
        p300.transfer(
            ISOPROPAVOL,
            isopropanol_sources[col_name],
            extraction_plate.columns_by_name()[col_name],
            new_tip='never',
            blow_out=True,
        )
    p300.drop_tip()

    # -----------------------------------------------------------------------
    # Paper step 1c: 250 uL of each inactivated sample, mix five times
    # (fresh tip per sample to avoid cross-contamination)
    # -----------------------------------------------------------------------
    protocol.comment('Step 1: 250 uL sample per well, mix by pipetting 5x')
    p1000.flow_rate.aspirate = 200
    p1000.flow_rate.dispense = 200
    for source, dest in zip(sample_sources, sample_dests):
        p1000.pick_up_tip()
        p1000.transfer(
            SAMPLE_VOL,
            source,
            dest,
            new_tip='never',
            mix_after=(BIND_MIX_REPS, BIND_MIX_VOL),
        )
        p1000.blow_out(dest.top(z=-5))
        p1000.drop_tip()

    # -----------------------------------------------------------------------
    # Paper step 1 (cont.): incubate 5 min at room temperature
    # -----------------------------------------------------------------------
    protocol.comment('Step 1: incubate 5 min at room temperature')
    protocol.delay(minutes=INCUBATION_MIN,
                   msg='Incubating 5 min at room temperature')

    # -----------------------------------------------------------------------
    # Paper step 2: activate the GEN1 magnetic module for 4 min
    # -----------------------------------------------------------------------
    protocol.comment('Step 2: engage magnetic module for 4 min')
    mag_mod.engage()
    protocol.delay(minutes=MAGNET_MIN,
                   msg='Magnets engaged for 4 min')

    # -----------------------------------------------------------------------
    # Paper step 3: collect the supernatant and discard to the waste plate
    # -----------------------------------------------------------------------
    protocol.comment('Step 3: remove supernatant (~540 uL) to waste')
    p300.well_bottom_clearance.aspirate = 0.5
    p300.well_bottom_clearance.dispense = 25
    p300.flow_rate.aspirate = 50     # aspirate slowly to keep pellets intact
    p300.flow_rate.dispense = 200
    for col_name in SAMPLE_COLUMNS:
        p300.pick_up_tip()
        for _ in range(2):
            p300.transfer(
                250,
                extraction_plate.columns_by_name()[col_name],
                waste_plate.columns_by_name()[col_name],
                new_tip='never',
            )
        p300.drop_tip()

    # -----------------------------------------------------------------------
    # Paper step 4: first wash - add 500 uL ethanol 70%, collect and discard
    # -----------------------------------------------------------------------
    protocol.comment('Step 4: wash 1 with 500 uL ethanol 70%')
    p300.well_bottom_clearance.aspirate = 2
    p300.well_bottom_clearance.dispense = 25
    p300.flow_rate.aspirate = 94
    p300.flow_rate.dispense = 200
    p300.pick_up_tip()
    for col_name in SAMPLE_COLUMNS:
        for _ in range(2):
            p300.transfer(
                250,
                ethanol_wash1_sources[col_name],
                extraction_plate.columns_by_name()[col_name],
                new_tip='never',
            )
    p300.drop_tip()

    protocol.comment('Step 4: remove wash 1 to waste')
    p300.well_bottom_clearance.aspirate = 0.5
    p300.flow_rate.aspirate = 50
    for col_name in SAMPLE_COLUMNS:
        p300.pick_up_tip()
        for _ in range(2):
            p300.transfer(
                250,
                extraction_plate.columns_by_name()[col_name],
                waste_plate.columns_by_name()[col_name],
                new_tip='never',
            )
        p300.drop_tip()

    # -----------------------------------------------------------------------
    # Paper step 5: second wash - add 500 uL ethanol 70%, collect and discard
    # -----------------------------------------------------------------------
    protocol.comment('Step 5: wash 2 with 500 uL ethanol 70%')
    p300.well_bottom_clearance.aspirate = 2
    p300.well_bottom_clearance.dispense = 25
    p300.flow_rate.aspirate = 94
    p300.flow_rate.dispense = 200
    p300.pick_up_tip()
    for col_name in SAMPLE_COLUMNS:
        for _ in range(2):
            p300.transfer(
                250,
                ethanol_wash2_sources[col_name],
                extraction_plate.columns_by_name()[col_name],
                new_tip='never',
            )
    p300.drop_tip()

    protocol.comment('Step 5: remove wash 2 to waste')
    p300.well_bottom_clearance.aspirate = 0.5
    p300.flow_rate.aspirate = 50
    for col_name in SAMPLE_COLUMNS:
        p300.pick_up_tip()
        for _ in range(2):
            p300.transfer(
                250,
                extraction_plate.columns_by_name()[col_name],
                waste_plate.columns_by_name()[col_name],
                new_tip='never',
            )
        p300.drop_tip()

    # -----------------------------------------------------------------------
    # Paper step 6: air dry the beads for 4 min (magnets stay engaged)
    # -----------------------------------------------------------------------
    protocol.comment('Step 6: air dry beads for 4 min')
    protocol.delay(minutes=DRYING_MIN,
                   msg='Air drying beads for 4 min (magnets engaged)')

    # -----------------------------------------------------------------------
    # Paper step 7: turn off the magnet and add 100 uL elution buffer;
    # resuspend the beads in each column with a fresh tip.
    # -----------------------------------------------------------------------
    protocol.comment('Step 7: disengage magnets, add 100 uL elution buffer')
    mag_mod.disengage()
    p300.well_bottom_clearance.aspirate = 2
    p300.well_bottom_clearance.dispense = 5
    p300.flow_rate.aspirate = 94
    p300.flow_rate.dispense = 94
    for col_name in SAMPLE_COLUMNS:
        p300.pick_up_tip()
        p300.transfer(
            ELUTION_VOL,
            elution_buffer_source,
            extraction_plate.columns_by_name()[col_name],
            new_tip='never',
        )
        # resuspend the beads in elution buffer
        p300.mix(
            ELUTION_MIX_REPS,
            ELUTION_MIX_VOL,
            extraction_plate.columns_by_name()[col_name][0].bottom(z=1),
        )
        p300.blow_out(
            extraction_plate.columns_by_name()[col_name][0].top(z=-5))
        p300.drop_tip()

    # -----------------------------------------------------------------------
    # Paper step 8: after 30 s turn on the magnetic module
    # -----------------------------------------------------------------------
    protocol.comment('Step 8: wait 30 s, then engage magnets')
    protocol.delay(seconds=ELUTION_WAIT_S,
                   msg='30 s before engaging magnets')
    mag_mod.engage()

    # -----------------------------------------------------------------------
    # Paper step 9: after 90 s collect the supernatant (eluted viral RNA)
    # and transfer it to the elution plate on the temperature module (4 degC)
    # -----------------------------------------------------------------------
    protocol.comment('Step 9: wait 90 s, then recover eluate')
    protocol.delay(seconds=SEPARATION_S,
                   msg='90 s for bead separation before eluate recovery')

    p300.well_bottom_clearance.aspirate = 0.5
    p300.well_bottom_clearance.dispense = 5
    p300.flow_rate.aspirate = 50     # slow aspiration, avoid bead carry-over
    p300.flow_rate.dispense = 94
    for col_name in SAMPLE_COLUMNS:
        p300.pick_up_tip()
        p300.transfer(
            ELUATE_VOL,
            extraction_plate.columns_by_name()[col_name],
            elution_plate.columns_by_name()[col_name],
            new_tip='never',
        )
        p300.blow_out(elution_plate.columns_by_name()[col_name][0].top(z=-5))
        p300.drop_tip()

    # -----------------------------------------------------------------------
    # End: release magnets; elution plate stays at 4 degC with the eluates.
    # -----------------------------------------------------------------------
    protocol.comment('Protocol complete - eluates on the 4 degC elution plate')
    mag_mod.disengage()
