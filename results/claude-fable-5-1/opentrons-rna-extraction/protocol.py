"""
In-house magnetic-bead SARS-CoV-2 RNA extraction on the Opentrons OT-2
(48 samples per run).

Implements the "OT-2 in-house" protocol of:
    Lazaro-Perona F, Rodriguez-Antolin C, et al. (2021) Evaluation of two
    automated low-cost RNA extraction protocols for SARS-CoV-2 detection.
    PLoS ONE 16(2): e0246302. doi:10.1371/journal.pone.0246302

Per well (Table 1 / "OT-2 in-house protocol" of the paper):
  1. 40 uL magnetic beads (Mag-Bind TotalPure NGS), 250 uL isopropanol and
     250 uL inactivated sample.  Mix by pipetting five times, 5 min at RT.
  2. Engage the GEN1 magnetic module, 4 min.
  3. Collect and discard the supernatant.
  4. Add 500 uL 70 % ethanol, collect and discard.
  5. Add 500 uL 70 % ethanol, collect and discard.
  6. Air dry 4 min.
  7. Disengage the magnet, add 100 uL elution buffer (resuspend beads).
  8. After 30 s engage the magnet.
  9. After 90 s collect the eluate and transfer it to the 96-well elution plate
     kept at 4 C on the temperature module.

Deck layout (fixed):
  1   waste deep-well plate                 usascientific_96_wellplate_2.4ml_deep
  2,3,9  200 uL filter tips (p300 multi)    opentrons_96_filtertiprack_200ul
  4   Magnetic Module GEN1 + extraction     usascientific_96_wellplate_2.4ml_deep
  5   reagent reservoir                     nest_12_reservoir_15ml
        col 2  magnetic beads        (>= 2.0 mL)
        col 4  elution buffer        (>= 5.0 mL)
        col 6  isopropanol           (>= 6.5 mL, sample columns 1,3,5)
        col 7  isopropanol           (>= 6.5 mL, sample columns 7,9,11)
        col 9  70 % ethanol, wash 1  (>= 12.5 mL, sample columns 1,3,5)
        col 10 70 % ethanol, wash 1  (>= 12.5 mL, sample columns 7,9,11)
        col 11 70 % ethanol, wash 2  (>= 12.5 mL, sample columns 1,3,5)
        col 12 70 % ethanol, wash 2  (>= 12.5 mL, sample columns 7,9,11)
  6   Temperature Module GEN1 + elution     thermo_96_wellplate_200ul (custom)
  10  samples 1-24  (2 mL safe-lock tubes)  opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap
  7   samples 25-48 (2 mL safe-lock tubes)  opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap
  11  1000 uL filter tips (p1000 single)    opentrons_96_filtertiprack_1000ul
  12  fixed trash

Pipettes: p1000_single_gen2 (left) for the samples; p300_multi_gen2 (right)
for all reagent additions, supernatant/wash removal and eluate recovery.

Sample mapping: tubes are read column-wise (A1, B1, C1, D1, A2, ...).  Sample 1
goes to extraction-plate A1, sample 2 to B1, ... sample 8 to H1, sample 9 to A3
and so on through the odd columns 1, 3, 5, 7, 9, 11 (48 wells).  Each eluate is
recovered into the SAME well position of the elution plate on the temperature
module (sample 1 -> A1, sample 9 -> A3, ...).  Supernatant and washes go to the
same well position of the waste plate in slot 1 (1 540 uL per waste well).
"""

import math

from opentrons import protocol_api
from opentrons.types import Point

metadata = {
    "protocolName": "SARS-CoV-2 RNA extraction, magnetic beads, OT-2 in-house (48 samples)",
    "author": "Implementation of Lazaro-Perona et al. 2021, PLoS ONE 16(2):e0246302",
    "description": "Mag-Bind TotalPure NGS / isopropanol binding, 2x 70% ethanol "
                   "washes, 100 uL elution; 48 samples in the odd columns of a "
                   "deep-well plate on a GEN1 magnetic module.",
    "apiLevel": "2.13",
}

# ---------------------------------------------------------------- volumes (uL)
NUM_SAMPLES = 48
BEAD_VOL = 40           # magnetic beads per well
ISO_VOL = 250           # isopropanol per well
SAMPLE_VOL = 250        # inactivated sample per well
BINDING_VOL = BEAD_VOL + ISO_VOL + SAMPLE_VOL   # 540 uL supernatant to discard
WASH_VOL = 500          # 70 % ethanol per wash
ELUTION_VOL = 100       # elution buffer
SAMPLE_MIX_REPS = 5     # "Mix by pipetting five times"
SAMPLE_MIX_VOL = 400

# ---------------------------------------------------------------- timings
BINDING_INCUBATION_MIN = 5    # room temperature, after mixing
MAGNET_BINDING_MIN = 4        # magnet on before removing the supernatant
AIR_DRY_MIN = 4               # after the second ethanol wash
ELUTION_RESUSPEND_SEC = 30    # magnet off, beads in elution buffer
ELUTION_MAGNET_SEC = 90       # magnet on before recovering the eluate
ELUTION_PLATE_TEMP_C = 4

MAX_TIP_VOL = 200             # p300 multi with 200 uL filter tips

# Columns of the extraction plate that hold samples (1-based 1,3,5,7,9,11)
SAMPLE_COLUMN_INDICES = [0, 2, 4, 6, 8, 10]


def run(protocol: protocol_api.ProtocolContext):

    # ------------------------------------------------------------ labware
    waste_plate = protocol.load_labware(
        "usascientific_96_wellplate_2.4ml_deep", "1", "waste plate")
    tips200 = [
        protocol.load_labware("opentrons_96_filtertiprack_200ul", slot,
                              "200 uL filter tips")
        for slot in ("2", "3", "9")
    ]
    mag_mod = protocol.load_module("magnetic module", "4")
    mag_plate = mag_mod.load_labware(
        "usascientific_96_wellplate_2.4ml_deep", "extraction plate")
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", "5",
                                      "reagent reservoir")
    temp_mod = protocol.load_module("tempdeck", "6")
    elution_plate = temp_mod.load_labware("thermo_96_wellplate_200ul",
                                          "elution plate")
    rack_1_24 = protocol.load_labware(
        "opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap", "10",
        "samples 1-24")
    rack_25_48 = protocol.load_labware(
        "opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap", "7",
        "samples 25-48")
    tips1000 = protocol.load_labware("opentrons_96_filtertiprack_1000ul", "11",
                                     "1000 uL filter tips")

    # ------------------------------------------------------------ pipettes
    p1000 = protocol.load_instrument("p1000_single_gen2", "left",
                                     tip_racks=[tips1000])
    m300 = protocol.load_instrument("p300_multi_gen2", "right",
                                    tip_racks=tips200)

    # ------------------------------------------------------------ reagents
    beads = reservoir["A2"]
    elution_buffer = reservoir["A4"]
    isopropanol = [reservoir["A6"], reservoir["A7"]]        # 3 columns each
    ethanol_wash_1 = [reservoir["A9"], reservoir["A10"]]    # 3 columns each
    ethanol_wash_2 = [reservoir["A11"], reservoir["A12"]]   # 3 columns each

    def source_for(col_number, sources):
        """Split the six sample columns over two reservoir columns."""
        return sources[0] if col_number < 3 else sources[1]

    # ------------------------------------------------------------ wells
    sample_tubes = rack_1_24.wells() + rack_25_48.wells()           # 48 tubes
    sample_wells = [
        well for i in SAMPLE_COLUMN_INDICES for well in mag_plate.columns()[i]
    ]                                                               # 48 wells
    assert len(sample_tubes) == len(sample_wells) == NUM_SAMPLES
    # Top wells of each sample column for the 8-channel pipette
    mag_cols = [mag_plate.columns()[i][0] for i in SAMPLE_COLUMN_INDICES]
    waste_cols = [waste_plate.columns()[i][0] for i in SAMPLE_COLUMN_INDICES]
    elution_cols = [elution_plate.columns()[i][0] for i in SAMPLE_COLUMN_INDICES]

    # GEN1 magnets sit between the plate columns: in the odd (1-based) columns
    # the bead pellet forms on the +x side of the well, so aspirate on the -x
    # side and mix on the +x side.
    PELLET_SIDE = 1

    def away_from_pellet(well, z=0.5, x=2.0):
        return well.bottom(z).move(Point(x=-PELLET_SIDE * x))

    def on_pellet(well, z=0.5, x=2.0):
        return well.bottom(z).move(Point(x=PELLET_SIDE * x))

    def split_volume(total, max_vol=MAX_TIP_VOL):
        """Split `total` into the fewest equal aliquots <= max_vol."""
        n = int(math.ceil(total / max_vol))
        return [round(total / n, 2)] * n

    default_asp = m300.flow_rate.aspirate
    default_disp = m300.flow_rate.dispense

    # ------------------------------------------------------------ helpers
    def add_reagent(vol, sources, label, dispense_height=-5):
        """Distribute `vol` uL per well to all sample columns with ONE tip,
        dispensing from above the liquid so the tip never touches the wells."""
        protocol.comment(f"Adding {vol} uL {label} to every sample well")
        m300.pick_up_tip()
        for i, dest in enumerate(mag_cols):
            src = source_for(i, sources)
            for aliquot in split_volume(vol):
                m300.aspirate(aliquot, src)
                m300.dispense(aliquot, dest.top(dispense_height))
                m300.blow_out(dest.top(dispense_height))
        m300.drop_tip()

    def remove_supernatant(vol, label):
        """Aspirate `vol` uL from each sample column (magnet engaged) and
        discard it in the matching column of the waste plate. New tip per
        column."""
        protocol.comment(f"Removing {vol} uL {label} to the waste plate")
        m300.flow_rate.aspirate = 40     # slow: do not disturb the pellet
        for src, waste in zip(mag_cols, waste_cols):
            m300.pick_up_tip()
            for aliquot in split_volume(vol):
                m300.aspirate(aliquot, away_from_pellet(src))
                m300.dispense(aliquot, waste.top(-5))
                m300.blow_out(waste.top(-5))
            m300.drop_tip()
        m300.flow_rate.aspirate = default_asp

    # ============================================================ protocol
    protocol.comment(
        "OT-2 in-house magnetic-bead RNA extraction, 48 samples "
        "(Lazaro-Perona et al. 2021, PLoS ONE 16(2):e0246302)")

    # Elution plate is kept at 4 C; start cooling now so it is cold by elution.
    temp_mod.start_set_temperature(ELUTION_PLATE_TEMP_C)
    mag_mod.disengage()

    # -------- Step 1: beads + isopropanol + sample, mix 5x, 5 min RT --------
    # 1a. 40 uL magnetic beads (resuspend them in the reservoir first).
    protocol.comment(f"Step 1: adding {BEAD_VOL} uL magnetic beads per well")
    m300.pick_up_tip()
    m300.mix(10, 150, beads.bottom(2))      # resuspend settled beads
    m300.blow_out(beads.top())
    for dest in mag_cols:
        m300.aspirate(BEAD_VOL, beads.bottom(1))
        m300.dispense(BEAD_VOL, dest.bottom(2))    # wells are still empty
        m300.blow_out(dest.top(-5))
    m300.drop_tip()

    # 1b. 250 uL isopropanol per well.
    add_reagent(ISO_VOL, isopropanol, "isopropanol")

    # 1c. 250 uL inactivated sample per well with the p1000, one tip per
    #     sample, then mix the beads/isopropanol/sample five times.
    protocol.comment(
        f"Step 1: transferring {SAMPLE_VOL} uL of each of the {NUM_SAMPLES} "
        f"samples and mixing {SAMPLE_MIX_REPS} times")
    for n, (tube, well) in enumerate(zip(sample_tubes, sample_wells), start=1):
        p1000.pick_up_tip()
        p1000.aspirate(SAMPLE_VOL, tube.bottom(3))
        p1000.dispense(SAMPLE_VOL, well.bottom(5))
        p1000.mix(SAMPLE_MIX_REPS, SAMPLE_MIX_VOL, well.bottom(3))
        p1000.blow_out(well.top(-5))
        p1000.drop_tip()

    protocol.comment(
        f"Step 1: binding, {BINDING_INCUBATION_MIN} min at room temperature")
    protocol.delay(minutes=BINDING_INCUBATION_MIN)

    # -------- Step 2: magnet on for 4 min --------
    protocol.comment(f"Step 2: magnetic module engaged, {MAGNET_BINDING_MIN} min")
    mag_mod.engage()                  # default height for this deep-well plate
    protocol.delay(minutes=MAGNET_BINDING_MIN)

    # -------- Step 3: collect and discard the supernatant --------
    protocol.comment("Step 3: discarding the binding supernatant")
    remove_supernatant(BINDING_VOL, "binding supernatant")

    # -------- Step 4: wash 1, 500 uL 70 % ethanol, collect and discard --------
    protocol.comment("Step 4: wash 1 with 70 % ethanol (magnet engaged)")
    add_reagent(WASH_VOL, ethanol_wash_1, "70 % ethanol (wash 1)")
    remove_supernatant(WASH_VOL, "70 % ethanol (wash 1)")

    # -------- Step 5: wash 2, 500 uL 70 % ethanol, collect and discard --------
    protocol.comment("Step 5: wash 2 with 70 % ethanol (magnet engaged)")
    add_reagent(WASH_VOL, ethanol_wash_2, "70 % ethanol (wash 2)")
    remove_supernatant(WASH_VOL, "70 % ethanol (wash 2)")

    # -------- Step 6: air dry 4 min --------
    protocol.comment(f"Step 6: air drying the beads, {AIR_DRY_MIN} min")
    protocol.delay(minutes=AIR_DRY_MIN)

    # -------- Step 7: magnet off, 100 uL elution buffer, resuspend --------
    protocol.comment(
        f"Step 7: magnet off, adding {ELUTION_VOL} uL elution buffer and "
        "resuspending the beads")
    mag_mod.disengage()
    for dest in mag_cols:
        m300.pick_up_tip()
        m300.aspirate(ELUTION_VOL, elution_buffer)
        m300.dispense(ELUTION_VOL, on_pellet(dest, z=1.0))
        m300.mix(10, 80, on_pellet(dest, z=0.5))   # resuspend the pellet
        m300.blow_out(dest.top(-5))
        m300.drop_tip()

    # -------- Step 8: after 30 s magnet on --------
    protocol.comment(f"Step 8: {ELUTION_RESUSPEND_SEC} s elution, then magnet on")
    protocol.delay(seconds=ELUTION_RESUSPEND_SEC)
    mag_mod.engage()

    # -------- Step 9: after 90 s transfer the eluate to the elution plate ----
    protocol.comment(f"Step 9: {ELUTION_MAGNET_SEC} s on the magnet")
    protocol.delay(seconds=ELUTION_MAGNET_SEC)
    temp_mod.await_temperature(ELUTION_PLATE_TEMP_C)   # elution plate at 4 C
    protocol.comment(
        f"Step 9: transferring {ELUTION_VOL} uL eluate to the elution plate "
        f"({ELUTION_PLATE_TEMP_C} C)")
    m300.flow_rate.aspirate = 25
    m300.flow_rate.dispense = 50
    for src, dest in zip(mag_cols, elution_cols):
        m300.pick_up_tip()
        m300.aspirate(ELUTION_VOL, away_from_pellet(src, z=0.5, x=2.0))
        m300.dispense(ELUTION_VOL, dest.bottom(1))
        m300.blow_out(dest.top(-2))
        m300.drop_tip()
    m300.flow_rate.aspirate = default_asp
    m300.flow_rate.dispense = default_disp

    mag_mod.disengage()
    protocol.comment(
        "Extraction finished. Eluates are in the odd columns of the elution "
        f"plate (slot 6), held at {ELUTION_PLATE_TEMP_C} C. Remove the "
        "extraction plate and waste plate; the temperature module stays on.")
