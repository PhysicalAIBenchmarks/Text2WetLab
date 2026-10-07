"""Slowpoke-style screening of 96 colonies, adapted to the fixed OT-2 deck.

Source: Slowpoke, ACS Synthetic Biology, doi:10.1021/acssynbio.5c00629,
CC BY 4.0, section 2.5 (Automated Colony PCR). The OT-2 method adds
9 uL of PCR premix before 1 uL of colony template, for 10 uL total.

Adaptation: each well has a different primer pair, so assemble its 9 uL
premix in situ: 5 uL Q5 Hot Start 2x master mix + 4 uL aqueous primer pair.
No water source is loaded. Assume each primer-pair solution contains
1.25 uM EACH primer; 4 uL gives 0.5 uM each in the final reaction.
The paper text does not give primer stock concentrations or numerical
PCR cycling settings (and does not include Table S5). These assumptions
and the Q5-compatible example cycling program must be checked before use.

IMPORTANT: the required Corning flat-bottom definition is not a 0.2 mL
semi-skirted PCR plate. Use it only as the on-deck setup plate; manually
transfer reactions to a thermocycler-rated plate. Never substitute a
physical PCR plate under the Corning definition, or heat the Corning plate.
"""

from opentrons import protocol_api

metadata = {
    "protocolName": "Slowpoke OT-2: 96-colony PCR screening with Q5",
    "author": "OpenAI",
    "description": (
        "Prepare 96 matched 10 uL reactions: 5 uL Q5 2x, 4 uL diluted "
        "well-specific primer pair, then 1 uL colony template. "
        "Manual transfer, sealing, thermocycling and gel screening."
    ),
    "apiLevel": "2.15",
}

REACTION_UL = 10
MASTER_MIX_UL = 5
PRIMER_PAIR_UL = 4
TEMPLATE_UL = 1

# Example Q5 program, NOT numerical settings reported by the paper.
# Assume all 96 primer pairs support a Q5 annealing temperature of 65 C
# and all expected amplicons are <= 1 kb. Use 30 s/kb for colony templates.
# For different lengths/primer Tms, revise these settings and, if necessary,
# manually divide the reactions among compatible thermocycler programs.
INITIAL_DENATURATION_C = 98
INITIAL_DENATURATION_S = 30
PCR_CYCLES = 30
DENATURATION_C = 98
DENATURATION_S = 10
ANNEALING_C = 65
ANNEALING_S = 20
EXTENSION_C = 72
EXTENSION_S = 30
FINAL_EXTENSION_C = 72
FINAL_EXTENSION_S = 120
HOLD_C = 4
LID_C = 105


def run(protocol: protocol_api.ProtocolContext):
    colony_plate = protocol.load_labware(
        "corning_96_wellplate_360ul_flat", 1, label="colony_plate"
    )
    pcr_plate = protocol.load_labware(
        "corning_96_wellplate_360ul_flat", 2, label="pcr_plate"
    )
    master_mix_reservoir = protocol.load_labware(
        "nest_1_reservoir_195ml", 3, label="master_mix_reservoir"
    )
    primer_plate = protocol.load_labware(
        "corning_96_wellplate_360ul_flat", 4, label="primer_plate"
    )
    tips20 = protocol.load_labware("opentrons_96_tiprack_20ul", 10)
    tips300 = protocol.load_labware("opentrons_96_tiprack_300ul", 11)
    p20 = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tips20])
    # All liquid operations below are 1-5 uL, so the loaded P300 is unused.
    protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips300])

    assert MASTER_MIX_UL + PRIMER_PAIR_UL + TEMPLATE_UL == REACTION_UL
    tip_count = 0

    def fresh_tip():
        nonlocal tip_count
        if tip_count == 96:
            protocol.comment(
                "MANUAL: Replace the exhausted slot-10 20 uL tip rack with "
                "a full rack of fresh tips before resuming. Do not move plates."
            )
            protocol.pause("Refill slot 10 with 96 fresh 20 uL tips, then resume.")
            p20.reset_tipracks()
            tip_count = 0
        p20.pick_up_tip()
        tip_count += 1

    def add_reagent(volume, source, destination):
        fresh_tip()
        # Source wells/reservoir have ample liquid by the supplied setup.
        # Fresh tips for EVERY transfer prevent carrying primers or template
        # back to any source. Do not aspirate or mix in shallow destinations.
        p20.aspirate(volume, source.bottom(1))
        p20.dispense(volume, destination.bottom(0.5))
        p20.blow_out(destination.top(-2))
        p20.drop_tip()

    protocol.comment(
        "MANUAL PRE-RUN CHECK: Colonies have already been picked and prepared "
        "as pipettable templates in A1:H12. Gently resuspend templates and "
        "homogenize Q5 and primer stocks without foaming before starting. "
        "Keep PCR reagents cold off-deck until loading; this deck has no "
        "temperature module. Confirm calibrated source heights and sufficient "
        "liquid above 1 mm, especially in the large reservoir."
    )
    protocol.comment(
        "RECIPE: Each 10 uL reaction receives 5 uL Q5 Hot Start 2x mix "
        "(final 1x), 4 uL primer-pair solution (1.25 uM each primer; final "
        "0.5 uM each), and 1 uL colony template. This diluted aqueous primer "
        "solution supplies the remaining water because no water labware "
        "is loaded. If stocks differ, prepare the required diluted primer "
        "pairs manually off-deck before running; concentrated primer stocks "
        "must not be dispensed at 4 uL unchanged."
    )
    protocol.comment(
        "DECK CHECK: Slot 2 must physically match the loaded Corning flat-bottom "
        "definition. It is a setup plate, not thermocycler-compatible labware. "
        "Plan a manual well-for-well transfer to an actual 0.2 mL semi-skirted "
        "PCR plate. Do not run with a PCR plate under the Corning definition."
    )
    protocol.comment(
        "CYCLING CHECK: The supplied paper leaves PCR settings to the polymerase, "
        "primers and fragment lengths. The example below assumes Q5-compatible "
        "65 C primer annealing and amplicons <= 1 kb. Verify all 96 primer pairs "
        "and expected lengths; adjust the program or use separate off-deck "
        "programs if needed before starting."
    )
    protocol.pause(
        "Confirm primer concentrations, template readiness, correct physical "
        "labware, low-volume dispensing calibration and Q5 cycling assumptions. "
        "Resume only when these checks are satisfied."
    )

    destinations = pcr_plate.wells()
    master_mix = master_mix_reservoir.wells()[0]

    protocol.comment("STEP 1: Dispense 5 uL Q5 2x mix into each of 96 setup wells.")
    for destination in destinations:
        add_reagent(MASTER_MIX_UL, master_mix, destination)

    protocol.comment(
        "STEP 2: Add 4 uL of the matching primer pair to each well. "
        "Each well now contains the paper's 9 uL pre-template PCR mix."
    )
    for destination in destinations:
        add_reagent(PRIMER_PAIR_UL, primer_plate[destination.well_name], destination)

    protocol.comment(
        "STEP 3: Add 1 uL of the matching colony template last. "
        "Preserve A1->A1 through H12->H12; final volume is 10 uL per well."
    )
    for destination in destinations:
        add_reagent(TEMPLATE_UL, colony_plate[destination.well_name], destination)

    # The flat-bottom plate contains extremely shallow 10 uL reactions.
    # Avoid automated destination mixing, which risks aspirating air here.
    # Mix manually during transfer into the narrower true PCR wells instead.
    protocol.comment(
        "MANUAL STEP 4: Immediately transfer each entire 10 uL reaction "
        "well-for-well into a real thermocycler-rated 0.2 mL semi-skirted PCR "
        "plate using fresh tips for each well. Mix gently by pipetting in "
        "the true PCR wells, avoiding bubbles and preserving colony identities. "
        "The Corning setup plate must NOT enter a thermocycler."
    )
    protocol.comment(
        "MANUAL STEP 5: Seal the true PCR plate with a compatible PCR seal, "
        "briefly centrifuge to collect liquid and remove bubbles, and move "
        "it to a benchtop thermocycler. No heating or cooling module is loaded; "
        "all PCR incubation and thermal cycling occur off-deck."
    )
    protocol.comment(
        f"MANUAL STEP 6: Run the verified Q5 program with heated lid {LID_C} C "
        f"and reaction-volume setting {REACTION_UL} uL: initial denaturation "
        f"{INITIAL_DENATURATION_C} C for {INITIAL_DENATURATION_S} s; "
        f"{PCR_CYCLES} cycles of {DENATURATION_C} C for {DENATURATION_S} s, "
        f"{ANNEALING_C} C for {ANNEALING_S} s, and {EXTENSION_C} C for "
        f"{EXTENSION_S} s; final extension {FINAL_EXTENSION_C} C for "
        f"{FINAL_EXTENSION_S} s; then hold at {HOLD_C} C. These are explicit "
        "Q5 adaptation assumptions, not measured cycling settings from the paper."
    )
    protocol.pause(
        "All robot tips have been discarded. Complete manual transfer, mixing, "
        "sealing, centrifugation and off-deck thermocycling; resume when finished."
    )
    protocol.comment(
        "MANUAL STEP 7: Screen the PCR products by agarose gel electrophoresis "
        "with a suitable DNA ladder, compare each band with its expected "
        "construct-specific amplicon size, and record positive colonies by "
        "their original well positions. Choose gel concentration and run "
        "conditions for the expected size range; these are not specified "
        "in the supplied paper text. No column cleanup is required for "
        "this colony-PCR screening workflow."
    )
    protocol.comment(
        "Setup complete: 96 reactions, 960 uL total (480 uL Q5 2x, "
        "384 uL primer solutions, 96 uL templates); 288 fresh P20 tips used. "
        "The P300 was loaded but not used. Neither pipette is holding a tip."
    )
