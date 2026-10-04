"""
In-house OT-2 magnetic-bead SARS-CoV-2 RNA extraction, 48 samples.

Implements the "OT-2 in-house" protocol of
"Automated low-cost SARS-CoV-2 RNA extraction protocols", PLOS ONE 2021,
doi:10.1371/journal.pone.0246302.

Deck
  1      waste deep-well plate (removed supernatant / washes)
  2,3,9  200 uL filter tips (p300 multi)
  4      Magnetic Module GEN1 + usascientific 2.4 mL deep-well
         (samples in odd columns 1,3,5,7,9,11)
  5      nest 12-channel reservoir: col 2 beads, col 4 elution buffer,
         cols 6-7 isopropanol, cols 9-12 70 % ethanol
  6      Temperature Module GEN1 + thermo_96_wellplate_200ul (eluates, 4 C)
  10     samples 1-24  (2 mL tubes)
  7      samples 25-48 (2 mL tubes)
  11     1000 uL filter tips (p1000 single)

Tip policy
  * every tip that aspirates from / mixes in a sample well is used for one
    sample well only (one column of 8 wells with the multi-channel);
  * reagent-only tips (beads, isopropanol, ethanol) dispense from above the
    liquid and never aspirate from a sample well, so one tip is shared.

Tip budget (p300 multi, columns of 8 tips): beads 1 + isopropanol 1 +
supernatant 6 + 2 washes x (1 + 6) + elution 6 + eluate 6 = 34 of 36.
p1000: 48 tips, one per sample.
"""

from opentrons import protocol_api

metadata = {
    "protocolName": "OT-2 in-house magnetic-bead RNA extraction (48 samples)",
    "author": "HULP OT-2 in-house protocol, re-implemented",
    "description": "PLOS ONE 2021 doi:10.1371/journal.pone.0246302, OT-2 in-house",
    "apiLevel": "2.13",
}

# ---------------------------------------------------------------- settings --
NUM_SAMPLES = 48
SAMPLE_COLUMNS = [0, 2, 4, 6, 8, 10]          # odd columns 1,3,5,7,9,11 (0-based)

BEAD_VOL = 40          # uL
ISOPROP_VOL = 250      # uL
SAMPLE_VOL = 250       # uL
SUPERNATANT_VOL = 540  # uL (40 + 250 + 250)
ETOH_VOL = 500         # uL per wash
ELUTION_VOL = 100      # uL
ELUATE_VOL = 80        # uL

INCUBATION_MIN = 5
MAGNET_MIN = 4
AIRDRY_MIN = 4
ELUTION_SOAK_SEC = 30
ELUTION_MAGNET_SEC = 90

ELUTION_TEMP_C = 4

P300_MAX = 200  # 200 uL filter tips limit the p300 multi to 200 uL per stroke


def split_volume(total, max_vol=P300_MAX):
    """Split *total* into equal strokes no larger than *max_vol*."""
    n = int(-(-total // max_vol))  # ceil division
    return [total / n] * n


def run(protocol: protocol_api.ProtocolContext):

    # ---------------------------------------------------------- modules --
    magdeck = protocol.load_module("magnetic module", "4")
    tempdeck = protocol.load_module("tempdeck", "6")

    # ---------------------------------------------------------- labware --
    waste_plate = protocol.load_labware(
        "usascientific_96_wellplate_2.4ml_deep", "1", "waste plate")
    tips200 = [
        protocol.load_labware("opentrons_96_filtertiprack_200ul", slot,
                              "200 uL filter tips")
        for slot in ("2", "3", "9")
    ]
    sample_plate = magdeck.load_labware(
        "usascientific_96_wellplate_2.4ml_deep", "sample/extraction plate")
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", "5",
                                      "reagent reservoir")
    elution_plate = tempdeck.load_labware("thermo_96_wellplate_200ul",
                                          "elution plate")
    tuberack_1 = protocol.load_labware(
        "opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap", "10",
        "samples 1-24")
    tuberack_2 = protocol.load_labware(
        "opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap", "7",
        "samples 25-48")
    tips1000 = protocol.load_labware("opentrons_96_filtertiprack_1000ul",
                                     "11", "1000 uL filter tips")

    # --------------------------------------------------------- pipettes --
    p1000 = protocol.load_instrument("p1000_single_gen2", "left",
                                     tip_racks=[tips1000])
    m300 = protocol.load_instrument("p300_multi_gen2", "right",
                                    tip_racks=tips200)

    # --------------------------------------------------------- reagents --
    beads = [reservoir.wells_by_name()["A2"]]
    elution_buffer = [reservoir.wells_by_name()["A4"]]
    isopropanol = [reservoir.wells_by_name()[w] for w in ("A6", "A7")]
    ethanol_wash1 = [reservoir.wells_by_name()[w] for w in ("A9", "A10")]
    ethanol_wash2 = [reservoir.wells_by_name()[w] for w in ("A11", "A12")]

    # ------------------------------------------------- well bookkeeping --
    # Multi-channel works on the top (A) well of each odd column.
    sample_cols = [sample_plate.columns()[i][0] for i in SAMPLE_COLUMNS]
    waste_cols = [waste_plate.columns()[i][0] for i in SAMPLE_COLUMNS]
    elution_cols = [elution_plate.columns()[i][0] for i in SAMPLE_COLUMNS]

    # Single-channel: 48 individual sample wells, column by column
    # (A1..H1, A3..H3, ..., A11..H11) -> samples 1..48.
    sample_wells = []
    for i in SAMPLE_COLUMNS:
        sample_wells.extend(sample_plate.columns()[i])
    sample_wells = sample_wells[:NUM_SAMPLES]
    sample_tubes = (tuberack_1.wells() + tuberack_2.wells())[:NUM_SAMPLES]

    # ----------------------------------------------------------- helpers --
    def add_reagent(sources, volume, dests, per_source=None,
                    mix_after=None, premix=None):
        """Dispense *volume* of a reagent into every column of *dests*.

        mix_after is None  -> one shared tip; it only aspirates from the
                              reservoir and dispenses from above the liquid,
                              so it never touches a sample well's contents.
        mix_after=(n, vol) -> the tip mixes inside the sample wells, so a
                              fresh tip is used for every column.
        per_source: destination columns served per reservoir well.
        premix=(n, vol):      mix the reservoir well before the first draw
                              (resuspend beads).
        """
        if per_source is None:
            per_source = len(dests)
        shared_tip = mix_after is None
        if shared_tip:
            m300.pick_up_tip()
        for idx, dest in enumerate(dests):
            src = sources[min(idx // per_source, len(sources) - 1)]
            if not shared_tip:
                m300.pick_up_tip()
            if premix is not None and idx == 0:
                m300.mix(premix[0], premix[1], src.bottom(2))
            for vol in split_volume(volume):
                m300.aspirate(vol, src.bottom(2))
                m300.dispense(vol, dest.top(-5))
                m300.blow_out(dest.top(-5))
            if mix_after is not None:
                m300.mix(mix_after[0], mix_after[1], dest.bottom(1.5))
                m300.blow_out(dest.top(-5))
                m300.drop_tip()
        if shared_tip:
            m300.drop_tip()

    def remove_to_waste(volume, aspirate_rate=50):
        """Move *volume* from every sample column to its own waste column.

        The caller has the magnet engaged.  Fresh tip for every column and
        slow aspiration from near the bottom so the pelleted beads stay put.
        """
        default_rate = m300.flow_rate.aspirate
        m300.flow_rate.aspirate = aspirate_rate
        for src, dst in zip(sample_cols, waste_cols):
            m300.pick_up_tip()
            for vol in split_volume(volume):
                m300.aspirate(vol, src.bottom(1))
                m300.dispense(vol, dst.top(-5))
                m300.blow_out(dst.top(-5))
            m300.drop_tip()
        m300.flow_rate.aspirate = default_rate

    def ethanol_wash(sources):
        """Add 500 uL 70 % ethanol to each well, then remove it (magnet on)."""
        protocol.comment("Adding 500 uL 70 % ethanol")
        add_reagent(sources, ETOH_VOL, sample_cols, per_source=3)
        protocol.comment("Removing ethanol to waste (magnet engaged)")
        remove_to_waste(ETOH_VOL)

    # ============================================================ steps ==

    # 1. Magnet off, elution plate to 4 C before anything is eluted.
    magdeck.disengage()
    tempdeck.set_temperature(ELUTION_TEMP_C)

    # 2. 40 uL magnetic beads (reservoir column 2) to every sample well.
    protocol.comment("Step 2: adding 40 uL magnetic beads")
    add_reagent(beads, BEAD_VOL, sample_cols, premix=(5, 150))

    # 3. 250 uL isopropanol (reservoir columns 6-7), 3 sample columns each.
    protocol.comment("Step 3: adding 250 uL isopropanol")
    add_reagent(isopropanol, ISOPROP_VOL, sample_cols, per_source=3)

    # 4. 250 uL of each sample, fresh tip per sample, mix 5x.
    protocol.comment("Step 4: adding 250 uL sample, mixing 5x")
    for tube, well in zip(sample_tubes, sample_wells):
        p1000.pick_up_tip()
        p1000.aspirate(SAMPLE_VOL, tube.bottom(3))
        p1000.dispense(SAMPLE_VOL, well.bottom(5))
        p1000.mix(5, 300, well.bottom(3))
        p1000.blow_out(well.top(-5))
        p1000.drop_tip()

    # 5. Incubate 5 min at room temperature.
    protocol.comment("Step 5: 5 min incubation at room temperature")
    protocol.delay(minutes=INCUBATION_MIN)

    # 6. Engage the magnet, wait 4 min.
    protocol.comment("Step 6: magnet on, 4 min")
    magdeck.engage()
    protocol.delay(minutes=MAGNET_MIN)

    # 7. Remove the supernatant (540 uL) to the waste plate.
    protocol.comment("Step 7: removing 540 uL supernatant to waste")
    remove_to_waste(SUPERNATANT_VOL)

    # 8. First 500 uL 70 % ethanol wash (reservoir columns 9-10).
    protocol.comment("Step 8: ethanol wash 1")
    ethanol_wash(ethanol_wash1)

    # 9. Second 500 uL 70 % ethanol wash (reservoir columns 11-12).
    protocol.comment("Step 9: ethanol wash 2")
    ethanol_wash(ethanol_wash2)

    # 10. Air-dry 4 min with the magnet engaged.
    protocol.comment("Step 10: air-drying beads 4 min")
    protocol.delay(minutes=AIRDRY_MIN)

    # 11. Magnet off, 100 uL elution buffer, resuspend beads by mixing.
    protocol.comment("Step 11: magnet off, adding 100 uL elution buffer")
    magdeck.disengage()
    add_reagent(elution_buffer, ELUTION_VOL, sample_cols, mix_after=(10, 80))

    # 12. 30 s, magnet on, 90 s.
    protocol.comment("Step 12: 30 s, then magnet on for 90 s")
    protocol.delay(seconds=ELUTION_SOAK_SEC)
    magdeck.engage()
    protocol.delay(seconds=ELUTION_MAGNET_SEC)

    # 13. 80 uL eluate to the elution plate at 4 C (same well positions).
    protocol.comment("Step 13: transferring 80 uL eluate to elution plate")
    default_rate = m300.flow_rate.aspirate
    m300.flow_rate.aspirate = 30
    for src, dst in zip(sample_cols, elution_cols):
        m300.pick_up_tip()
        m300.aspirate(ELUATE_VOL, src.bottom(1))
        m300.dispense(ELUATE_VOL, dst.bottom(2))
        m300.blow_out(dst.top(-2))
        m300.drop_tip()
    m300.flow_rate.aspirate = default_rate

    # 14. Magnet off at the end of the run.
    magdeck.disengage()
    protocol.comment("Extraction finished: eluates on the 4 C elution plate")
