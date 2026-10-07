from opentrons import protocol_api

metadata = {
    "protocolName": "APEX Protocol 1 - Heat Shock Transformation (8 plasmids)",
    "author": "APEX (Kasprzyk, Herrera & Stracquadanio, 2024)",
    "description": (
        "Automated heat shock transformation of 8 plasmids (pEX01-pEX08) into "
        "chemically competent E. coli DH5alpha using the OT-2 thermocycler "
        "(APEX Protocol 1, Low Volume configuration)."
    ),
    "apiLevel": "2.15",
}

# ---------------------------------------------------------------------------
# Transform parameters - APEX Protocol 1 "Low Volume" (LV) configuration.
# The paper's Figure 4 legend states the automated LV run uses:
#   1 uL DNA (at 1.5e-4 pmol/uL), 10 uL competent cells, 50 uL SOC medium.
# The resulting 61 uL total/well sits comfortably inside a 200 uL PCR plate.
# ---------------------------------------------------------------------------
DNA_VOLUME_UL = 1.0       # 1 uL plasmid DNA per transformation
CELL_VOLUME_UL = 10.0     # competent cells, pre-loaded by the operator
SOC_VOLUME_UL = 50.0      # recovery medium added after heat shock

INCUBATE_ON_ICE_TEMP = 4   # degC
INCUBATE_ON_ICE_MIN = 30   # min   (DNA + cells pre-incubation)
HEAT_SHOCK_TEMP = 42       # degC
HEAT_SHOCK_SEC = 30        # s     (heat shock)
RECOVERY_TEMP = 37         # degC
RECOVERY_MIN = 60          # min   (SOC outgrowth, 1 hour)


def run(protocol: protocol_api.ProtocolContext):
    # ----- Labware (deck as set up by the operator) -----
    # Column 1 of each plate holds the 8 transformations, row-n matched:
    # plasmid well n -> competent-cell well n (A1->A1 ... H1->H1).
    plasmid_plate = protocol.load_labware(
        "biorad_96_wellplate_200ul_pcr", 1, label="plasmid_plate"
    )
    soc_reservoir = protocol.load_labware(
        "nest_12_reservoir_15ml", 2, label="soc_reservoir"
    )

    # Pipettes (single-channel) and their tip racks.
    tiprack_20 = protocol.load_labware("opentrons_96_tiprack_20ul", 4)
    tiprack_300 = protocol.load_labware("opentrons_96_tiprack_300ul", 5)
    p20 = protocol.load_instrument(
        "p20_single_gen2", "left", tip_racks=[tiprack_20]
    )
    p300 = protocol.load_instrument(
        "p300_single_gen2", "right", tip_racks=[tiprack_300]
    )

    # Thermocycler module (GEN1) holding the transformation plate. The operator
    # has pre-loaded 10 uL competent cells per well onto a pre-chilled block.
    tc = protocol.load_module("thermocycler")
    transformation_plate = tc.load_labware(
        "biorad_96_wellplate_200ul_pcr", label="transformation_plate"
    )

    # Wells referenced below.
    plasmid_wells = plasmid_plate.columns()[0]       # A1..H1 (plasmids pEX01..pEX08)
    cell_wells = transformation_plate.columns()[0]   # A1..H1 (the competent cells)
    soc_source = soc_reservoir["A1"]                 # SOC medium, plenty

    # Max liquid a well ever holds = DNA + cells + SOC = 61 uL; used as a hint
    # so the thermocycler heats the block appropriately for the liquid volume.
    max_well_volume_ul = DNA_VOLUME_UL + CELL_VOLUME_UL + SOC_VOLUME_UL

    # ----- 1. Confirm the block is held at 4 C before adding DNA -----
    # The operator pre-chilled the block; this is a no-op if it is already at
    # 4 C, and otherwise cools it down so DNA is always added on ice.
    tc.close_lid()
    tc.set_block_temperature(INCUBATE_ON_ICE_TEMP)

    # ----- 2. Add 1 uL plasmid DNA to each well of cells -----
    tc.open_lid()  # the lid must be open for the robot to reach the plate
    p20.transfer(
        DNA_VOLUME_UL,
        plasmid_wells,
        cell_wells,
        new_tip="always",
    )
    # 8 tips used (one per well); well within the first 20 uL rack (96 tips),
    # so no reset_tipracks() is needed for the p20.
    tc.close_lid()

    # ----- 3. Incubate on ice: 4 C for 30 min -----
    # Lid left unheated here (heating it would counteract the cold incubation).
    tc.set_block_temperature(
        INCUBATE_ON_ICE_TEMP,
        hold_time_minutes=INCUBATE_ON_ICE_MIN,
        block_max_volume=max_well_volume_ul,
    )

    # ----- 4. Heat shock: 42 C for 30 s -----
    # Default (maximum) ramp rate is used for the rapid temperature change the
    # method requires.
    tc.set_block_temperature(
        HEAT_SHOCK_TEMP,
        hold_time_seconds=HEAT_SHOCK_SEC,
        block_max_volume=max_well_volume_ul,
    )

    # ----- 5. Add 50 uL SOC recovery medium -----
    tc.open_lid()
    p300.transfer(
        SOC_VOLUME_UL,
        soc_source,
        cell_wells,
        new_tip="always",
        mix_after=(3, 40),  # gentle resuspension of cells into SOC (sound choice)
    )
    # 8 tips used; within the first 300 uL rack, no reset_tipracks() needed.
    tc.close_lid()
    # Heated lid keeps condensation/evaporation off the samples during the 1 h
    # recovery at 37 C (the paper notes evaporation is a concern on a bare
    # temperature module, which is why the thermocycler is used).
    tc.set_lid_temperature(RECOVERY_TEMP)

    # ----- 6. Recover at 37 C for 1 hour -----
    tc.set_block_temperature(
        RECOVERY_TEMP,
        hold_time_minutes=RECOVERY_MIN,
        block_max_volume=max_well_volume_ul,
    )

    # ----- 7. Hold recovered cells on ice for downstream spotting (Protocol 2) -----
    # Recovery is complete; keep the transformants cold for the operator. This
    # final 4 C hold is a sound choice - the paper does not specify the block
    # state between Protocol 1 and the agar spotting in Protocol 2.
    tc.deactivate_lid()  # turn off the heated lid
    tc.set_block_temperature(INCUBATE_ON_ICE_TEMP)