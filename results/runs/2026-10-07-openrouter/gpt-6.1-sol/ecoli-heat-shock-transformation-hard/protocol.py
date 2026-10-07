"""APEX Protocol 1: eight low-volume DH5alpha heat shock transformations.

Source: Kasprzyk, Herrera and Stracquadanio (2024), APEX,
doi:10.1101/2024.08.13.607171, Protocol 1 and Figure 4 legend.
The selected LV condition is 1 uL DNA + 10 uL cells + 50 uL SOC.
The operator has already loaded the cells on the pre-chilled block.
No competent-cell preparation, dilution, or agar spotting is performed.
"""

from opentrons import protocol_api

metadata = {
    "protocolName": "APEX Protocol 1 - eight heat shock transformations",
    "author": "OpenAI",
    "description": (
        "Transform pEX01-pEX08 into preloaded DH5alpha cells using the "
        "paper's low-volume condition and thermocycler temperature steps."
    ),
    "apiLevel": "2.15",
}

WELL_NAMES = ("A1", "B1", "C1", "D1", "E1", "F1", "G1", "H1")
DNA_VOLUME = 1
CELL_VOLUME = 10
SOC_VOLUME = 50
TRANSFORMATION_VOLUME = CELL_VOLUME + DNA_VOLUME  # 11 uL
RECOVERY_VOLUME = TRANSFORMATION_VOLUME + SOC_VOLUME  # 61 uL


def run(protocol: protocol_api.ProtocolContext):
    plasmid_plate = protocol.load_labware(
        "biorad_96_wellplate_200ul_pcr", 1, label="plasmid_plate"
    )
    soc_reservoir = protocol.load_labware(
        "nest_12_reservoir_15ml", 2, label="soc_reservoir"
    )
    tips20 = protocol.load_labware(
        "opentrons_96_tiprack_20ul", 4, label="p20_tips"
    )
    tips300 = protocol.load_labware(
        "opentrons_96_tiprack_300ul", 5, label="p300_tips"
    )
    tc = protocol.load_module("thermocycler")
    transformation_plate = tc.load_labware(
        "biorad_96_wellplate_200ul_pcr", label="transformation_plate"
    )
    p20 = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tips20])
    p300 = protocol.load_instrument(
        "p300_single_gen2", "right", tip_racks=[tips300]
    )

    # The paper leaves mixing, lid heating, and the final holding temperature
    # unspecified. Use gentle mixing and keep the lid unheated for the cold
    # incubation and brief heat shock. Heat the lid to 50 C only for recovery
    # to limit condensation; this is not an additional sample-temperature step.
    p20.flow_rate.aspirate = 2
    p20.flow_rate.dispense = 2
    p300.flow_rate.aspirate = 20
    p300.flow_rate.dispense = 20

    tc.open_lid()
    tc.deactivate_lid()
    tc.set_block_temperature(4, block_max_volume=CELL_VOLUME)

    protocol.comment("Add 1 uL of each plasmid to its matching 10 uL cell aliquot.")
    for name in WELL_NAMES:
        source = plasmid_plate.wells_by_name()[name]
        destination = transformation_plate.wells_by_name()[name]
        p20.pick_up_tip()
        p20.aspirate(DNA_VOLUME, source.bottom(0.5))
        p20.dispense(DNA_VOLUME, destination.bottom(0.5))
        # Three slow 5 uL cycles mix the 11 uL sample without vigorous agitation.
        p20.mix(3, 5, destination.bottom(0.5))
        p20.drop_tip()

    tc.close_lid()
    protocol.comment("Incubate DNA and cells at 4 C for 30 minutes.")
    tc.set_block_temperature(
        4, hold_time_minutes=30, block_max_volume=TRANSFORMATION_VOLUME
    )
    protocol.comment("Heat shock at 42 C for 30 seconds.")
    tc.set_block_temperature(
        42, hold_time_seconds=30, block_max_volume=TRANSFORMATION_VOLUME
    )

    # The paper does not specify a post-shock ice incubation. Return the block
    # immediately to 4 C for SOC addition, with no extra timed cold incubation.
    tc.set_block_temperature(4, block_max_volume=TRANSFORMATION_VOLUME)
    tc.open_lid()
    protocol.comment("Add 50 uL SOC per well; the recovery volume is 61 uL.")
    soc = soc_reservoir.wells_by_name()["A1"]
    for name in WELL_NAMES:
        destination = transformation_plate.wells_by_name()[name]
        # A fresh tip per well prevents transformed cells reaching bulk SOC.
        p300.pick_up_tip()
        p300.aspirate(SOC_VOLUME, soc.bottom(1))
        p300.dispense(SOC_VOLUME, destination.bottom(1))
        p300.mix(3, 40, destination.bottom(1))
        p300.drop_tip()

    # Only eight tips from each 96-tip rack are used: neither rack is depleted,
    # so no rack replacement or reset_tipracks() is needed for these eight runs.
    tc.close_lid()
    tc.set_lid_temperature(50)
    protocol.comment("Recover in SOC at 37 C for 1 hour, on the thermocycler.")
    tc.set_block_temperature(
        37, hold_time_minutes=60, block_max_volume=RECOVERY_VOLUME
    )

    # End-of-run choice: hold recovered cells at 4 C for collection rather than
    # leave them growing indefinitely. All tips have already been discarded.
    tc.deactivate_lid()
    tc.set_block_temperature(4, block_max_volume=RECOVERY_VOLUME)
    tc.open_lid()
    protocol.comment(
        "Recovery complete: A1-H1 each contain 61 uL, held at 4 C. "
        "Collect the plate; agar spotting (APEX Protocol 2) is out of scope."
    )
