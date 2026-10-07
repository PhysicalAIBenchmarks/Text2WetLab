"""In-house magnetic-bead RNA extraction for 48 inactivated samples.

Based on the OT-2 method in doi:10.1371/journal.pone.0246302 and the
specified 48-sample workflow. Use the fixed deck layout below.

Load each tube rack column-wise (A1, B1, C1, D1, A2, ...): samples
1-24 in slot 10, followed by samples 25-48 in slot 7. Extraction and
elution wells are A-H in columns 1, 3, 5, 7, 9, and 11, in that order.
The waste plate must initially be empty.

Suggested reservoir loading, including excess for aspiration:
    A2: 3.5 mL magnetic-bead suspension
    A4: 6 mL elution buffer
    A6, A7: 7 mL isopropanol each
    A9, A10, A11, A12: 13.5 mL 70% ethanol each
Keep the other reservoir wells empty. Premix the bead suspension.

Consumes 48 single-channel 1000 uL tips and 34 columns (272 tips) of
200 uL tips. No tip reloads or tip reuse after disposal are needed.
"""

from opentrons import protocol_api

metadata = {
    "protocolName": "48-sample in-house magnetic-bead RNA extraction",
    "author": "OpenAI",
    "description": (
        "OT-2 in-house RNA extraction: two ethanol washes, 100 uL elution, "
        "and 80 uL recovery into a plate held at 4 C."
    ),
    "apiLevel": "2.13",
}


def run(protocol: protocol_api.ProtocolContext):
    waste_plate = protocol.load_labware(
        "usascientific_96_wellplate_2.4ml_deep", "1", "Liquid waste"
    )
    small_tips = [
        protocol.load_labware("opentrons_96_filtertiprack_200ul", slot)
        for slot in ("2", "3", "9")
    ]
    magnet = protocol.load_module("magnetic module", "4")
    extraction_plate = magnet.load_labware(
        "usascientific_96_wellplate_2.4ml_deep", "Extraction plate"
    )
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", "5")
    temperature = protocol.load_module("tempdeck", "6")
    elution_plate = temperature.load_labware(
        "thermo_96_wellplate_200ul", "Recovered RNA"
    )
    sample_racks = [
        protocol.load_labware(
            "opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap",
            slot,
            label,
        )
        for slot, label in (("10", "Samples 1-24"), ("7", "Samples 25-48"))
    ]
    large_tips = protocol.load_labware("opentrons_96_filtertiprack_1000ul", "11")
    single = protocol.load_instrument(
        "p1000_single_gen2", "left", tip_racks=[large_tips]
    )
    multi = protocol.load_instrument(
        "p300_multi_gen2", "right", tip_racks=small_tips
    )

    odd_columns = (0, 2, 4, 6, 8, 10)
    extraction_columns = [extraction_plate.columns()[i] for i in odd_columns]
    extraction_wells = [well for column in extraction_columns for well in column]
    column_sources = [column[0] for column in extraction_columns]
    waste_columns = [waste_plate.columns()[i][0] for i in odd_columns]
    elution_columns = [elution_plate.columns()[i][0] for i in odd_columns]
    samples = [well for rack in sample_racks for well in rack.wells()]

    beads = reservoir.wells_by_name()["A2"]
    elution_buffer = reservoir.wells_by_name()["A4"]
    isopropanol_sources = [
        reservoir.wells_by_name()["A6"] if i < 3
        else reservoir.wells_by_name()["A7"]
        for i in range(6)
    ]
    ethanol_sources = [
        [reservoir.wells_by_name()[name] for name in names]
        for names in (("A9", "A10"), ("A11", "A12"))
    ]

    # All multichannel volumes are per channel, with a 200 uL tip limit.
    def add_reagent(sources, volumes, resuspend_source=False):
        """Share clean tips only for non-contact dispensing above wells."""
        multi.pick_up_tip()
        for source, destination in zip(sources, column_sources):
            if resuspend_source:
                multi.mix(5, 150, source.bottom(1))
            for volume in volumes:
                multi.aspirate(volume, source.bottom(1))
                multi.dispense(volume, destination.top(2))
                multi.blow_out(destination.top(2))
        multi.drop_tip()

    def remove_to_waste(volumes):
        """Use one fresh tip per sample throughout each removal step."""
        for source, destination in zip(column_sources, waste_columns):
            multi.pick_up_tip()
            for volume in volumes:
                multi.aspirate(volume, source.bottom(0.5), rate=0.25)
                # Stay above accumulated waste, including on repeat washes.
                multi.dispense(volume, destination.top(2))
                multi.blow_out(destination.top(2))
            multi.drop_tip()

    protocol.comment("Disengage the magnet and cool the elution plate to 4 C.")
    magnet.disengage()
    # set_temperature waits for the target; leave the module active at the end.
    temperature.set_temperature(4)

    protocol.comment("Add 40 uL beads per well; remix the stock between columns.")
    add_reagent([beads] * 6, (40,), resuspend_source=True)

    protocol.comment("Add 250 uL isopropanol per well, using A6 then A7.")
    add_reagent(isopropanol_sources, (125, 125))

    protocol.comment("Add each 250 uL sample with a fresh tip and mix five times.")
    for sample, destination in zip(samples, extraction_wells):
        single.pick_up_tip()
        single.aspirate(250, sample.bottom(2))
        single.dispense(250, destination.bottom(1))
        single.mix(5, 400, destination.bottom(1))
        single.blow_out(destination.top(-2))
        single.drop_tip()

    protocol.delay(minutes=5, msg="Bind RNA for 5 minutes at room temperature.")
    # Use the plate definition's default engagement height for the GEN1 module.
    magnet.engage()
    protocol.delay(minutes=4, msg="Collect beads on the magnet for 4 minutes.")

    protocol.comment("Remove 540 uL binding supernatant from each well.")
    remove_to_waste((180, 180, 180))

    for wash_number, sources in enumerate(ethanol_sources, start=1):
        protocol.comment(f"Ethanol wash {wash_number}: add and remove 500 uL.")
        # Each reservoir well supplies 24 samples (12 mL) for this wash.
        add_reagent([sources[0]] * 3 + [sources[1]] * 3, (200, 200, 100))
        remove_to_waste((200, 200, 100))

    protocol.delay(minutes=4, msg="Air-dry beads for 4 minutes with magnet engaged.")
    magnet.disengage()

    protocol.comment("Add 100 uL elution buffer and resuspend beads with fresh tips.")
    for destination in column_sources:
        multi.pick_up_tip()
        multi.aspirate(100, elution_buffer.bottom(1))
        multi.dispense(100, destination.bottom(0.5))
        multi.mix(10, 80, destination.bottom(0.5))
        multi.blow_out(destination.top(-2))
        # Never return these sample-contact tips to the reagent reservoir.
        multi.drop_tip()

    protocol.delay(seconds=30, msg="Incubate for 30 seconds before recapturing beads.")
    magnet.engage()
    protocol.delay(seconds=90, msg="Collect beads for 90 seconds before recovery.")

    protocol.comment("Recover 80 uL RNA eluate into matching wells at 4 C.")
    for source, destination in zip(column_sources, elution_columns):
        multi.pick_up_tip()
        multi.aspirate(80, source.bottom(0.5), rate=0.25)
        multi.dispense(80, destination.bottom(1))
        multi.blow_out(destination.top(-2))
        multi.drop_tip()

    magnet.disengage()
    protocol.comment("Extraction complete. Eluates remain on the active 4 C module.")
