"""48-sample OT-2 in-house extraction, PLOS ONE doi:10.1371/journal.pone.0246302.

Input tubes contain already-inactivated samples; no on-deck inactivation is done.
Number tubes column-major (A1, B1, C1, D1, A2, ... D6), slot 10 then slot 7.
Samples and eluates are column-major in A1:H1, A3:H3, ... A11:H11.

Reservoir loading, including working-volume/dead-volume allowances:
  A2: 3.5 mL well-suspended magnetic beads (1.92 mL consumed).
  A4: 6 mL elution buffer (4.8 mL consumed).
  A6, A7: 8 mL isopropanol EACH (6 mL consumed from each).
  A9, A10, A11, A12: 14 mL freshly prepared 70% ethanol EACH
                   (12 mL consumed from each; A9/A10 wash 1, A11/A12 wash 2).
Waste and elution plates must start empty. All tip racks must start full.

The paper does not specify pipetting rates, mixing volumes, or magnet height.
These are implementation settings, not additional chemical incubation steps.
"""

from opentrons import protocol_api

metadata = {
    "protocolName": "48-sample in-house magnetic-bead RNA extraction",
    "author": "OpenAI",
    "description": "OT-2 in-house method from PLOS ONE e0246302; inactivated samples.",
    "apiLevel": "2.13",
}

SAMPLE_VOLUME = 250
ISOPROPANOL_VOLUME = 250
BEAD_VOLUME = 40
WASH_VOLUME = 500
ELUTION_VOLUME = 100
ODD_COLUMN_INDICES = (0, 2, 4, 6, 8, 10)
# GEN1 uses its own height scale; this is NOT a GEN2 height setting.
MAGNET_HEIGHT_GEN1 = 18
MULTI_TRANSFER_LIMIT = 200  # Physical filter tips, despite the p300's name.


def run(protocol: protocol_api.ProtocolContext):
    waste = protocol.load_labware("usascientific_96_wellplate_2.4ml_deep", "1")
    multi_tips = [
        protocol.load_labware("opentrons_96_filtertiprack_200ul", slot)
        for slot in ("2", "3", "9")
    ]
    mag = protocol.load_module("magnetic module", "4")
    extraction = mag.load_labware("usascientific_96_wellplate_2.4ml_deep")
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", "5")
    temperature = protocol.load_module("tempdeck", "6")
    elution = temperature.load_labware("thermo_96_wellplate_200ul")
    tubes_1_24 = protocol.load_labware(
        "opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap", "10"
    )
    tubes_25_48 = protocol.load_labware(
        "opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap", "7"
    )
    single_tips = protocol.load_labware("opentrons_96_filtertiprack_1000ul", "11")
    single = protocol.load_instrument(
        "p1000_single_gen2", "left", tip_racks=[single_tips]
    )
    multi = protocol.load_instrument(
        "p300_multi_gen2", "right", tip_racks=multi_tips
    )

    # Leave the temperature module active at 4 C, including after recovery.
    temperature.set_temperature(4)
    mag.disengage()
    single.flow_rate.aspirate = 100
    single.flow_rate.dispense = 150
    single.flow_rate.blow_out = 150
    multi.flow_rate.aspirate = 40
    multi.flow_rate.dispense = 80
    multi.flow_rate.blow_out = 80

    sample_columns = [extraction.columns()[i][0] for i in ODD_COLUMN_INDICES]
    waste_columns = [waste.columns()[i][0] for i in ODD_COLUMN_INDICES]
    elution_columns = [elution.columns()[i][0] for i in ODD_COLUMN_INDICES]
    sample_wells = [
        well for i in ODD_COLUMN_INDICES for well in extraction.columns()[i]
    ]
    input_tubes = tubes_1_24.wells() + tubes_25_48.wells()
    beads = reservoir.wells_by_name()["A2"]
    elution_buffer = reservoir.wells_by_name()["A4"]
    isopropanol = [reservoir.wells_by_name()[name] for name in ("A6", "A7")]
    ethanol_washes = [
        [reservoir.wells_by_name()[name] for name in names]
        for names in (("A9", "A10"), ("A11", "A12"))
    ]

    def strokes(volume):
        """Per-channel strokes, each within a 200 uL filter tip's capacity."""
        remaining = volume
        while remaining > 0:
            amount = min(remaining, MULTI_TRANSFER_LIMIT)
            yield amount
            remaining -= amount

    def add_noncontact(volume, source, destination):
        # Only clean, reagent-dedicated tips may use this helper. The tips stay
        # just inside the well mouth, far above the liquid, and never touch it.
        # Thus a reagent tip set can safely serve all six sample columns.
        for amount in strokes(volume):
            multi.aspirate(amount, source.bottom(z=1))
            multi.dispense(amount, destination.top(z=-2))

    def remove_to_waste(volume):
        # Fresh tips for each column and each removal stage. Keep the magnet
        # engaged, do not mix, and aspirate at the centre, away from side beads.
        # Waste is dispensed near the mouth, never into accumulated waste;
        # the same column's tips can therefore make multiple removal strokes.
        for source, destination in zip(sample_columns, waste_columns):
            multi.pick_up_tip()
            for amount in strokes(volume):
                multi.aspirate(amount, source.bottom(z=0.5))
                multi.dispense(amount, destination.top(z=-2))
                multi.blow_out(destination.top(z=-2))
            multi.drop_tip()

    protocol.comment("Step 1: 40 uL beads, 250 uL isopropanol, 250 uL sample.")
    # Load reagents before any samples. Remix the bead stock immediately before
    # each eight-well aliquot; these tips never contact a sample.
    multi.pick_up_tip()
    for destination in sample_columns:
        multi.mix(5, 100, beads.bottom(z=1))
        multi.aspirate(BEAD_VOLUME, beads.bottom(z=1))
        multi.dispense(BEAD_VOLUME, destination.bottom(z=2))
    multi.drop_tip()

    multi.pick_up_tip()
    for index, destination in enumerate(sample_columns):
        add_noncontact(ISOPROPANOL_VOLUME, isopropanol[index // 3], destination)
    multi.drop_tip()

    # A single-channel pipette preserves tube-to-well identity. One fresh tip
    # per sample, also used for that well's five initial mixing repetitions.
    for source, destination in zip(input_tubes, sample_wells):
        single.pick_up_tip()
        single.aspirate(SAMPLE_VOLUME, source.bottom(z=1))
        single.dispense(SAMPLE_VOLUME, destination.bottom(z=1))
        single.mix(5, 400, destination.bottom(z=1))
        single.blow_out(destination.top(z=-2))
        single.drop_tip()
    protocol.delay(minutes=5, msg="Bind RNA to beads for 5 minutes at room temperature.")

    protocol.comment("Steps 2-3: engage GEN1 magnet for 4 minutes; discard supernatant.")
    mag.engage(height=MAGNET_HEIGHT_GEN1)
    protocol.delay(minutes=4, msg="Initial magnetic separation: 4 minutes.")
    remove_to_waste(SAMPLE_VOLUME + ISOPROPANOL_VOLUME + BEAD_VOLUME)

    # The published washes are performed with the magnet continuously engaged;
    # neither a bead-resuspension step nor an extra wash incubation is specified.
    for wash_number, sources in enumerate(ethanol_washes, start=1):
        protocol.comment(f"Wash {wash_number}: add and discard 500 uL 70% ethanol.")
        multi.pick_up_tip()
        for index, destination in enumerate(sample_columns):
            add_noncontact(WASH_VOLUME, sources[index // 3], destination)
        multi.drop_tip()
        remove_to_waste(WASH_VOLUME)

    protocol.delay(minutes=4, msg="Step 6: air-dry beads for 4 minutes at room temperature.")

    protocol.comment("Step 7: disengage magnet; add 100 uL elution buffer and resuspend.")
    mag.disengage()
    for destination in sample_columns:
        multi.pick_up_tip()
        multi.aspirate(ELUTION_VOLUME, elution_buffer.bottom(z=1))
        multi.dispense(ELUTION_VOLUME, destination.bottom(z=0.5))
        multi.mix(5, 80, destination.bottom(z=0.5))
        multi.drop_tip()
    protocol.delay(seconds=30, msg="Step 8: elute for 30 seconds off-magnet.")
    mag.engage(height=MAGNET_HEIGHT_GEN1)
    protocol.delay(seconds=90, msg="Step 9: separate beads for 90 seconds.")

    for source, destination in zip(sample_columns, elution_columns):
        multi.pick_up_tip()
        multi.aspirate(ELUTION_VOLUME, source.bottom(z=0.5))
        multi.dispense(ELUTION_VOLUME, destination.bottom(z=1))
        multi.blow_out(destination.top(z=-2))
        multi.drop_tip()

    mag.disengage()
    protocol.comment(
        "Complete: 48 individual eluates in odd columns of slot 6, held at 4 C. "
        "Waste: 1540 uL/well in the corresponding odd columns of slot 1. "
        "Tips used: 48 single tips and 34 multi-channel sets (272 tips); no refill."
    )
