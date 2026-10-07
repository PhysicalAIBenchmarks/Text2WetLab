"""Four four-fragment chromoprotein assemblies using the fixed OT-2 deck.

Only liquid handling is automated. Thermal programs, column purifications,
DNA measurements, and cell handling are recorded as operator instructions.
The fixed deck has no thermocycler module; use an external thermocycler.
"""

from opentrons import protocol_api

metadata = {
    "protocolName": "AssemblyTron: four four-fragment chromoprotein assemblies",
    "author": "OpenAI",
    "description": (
        "Seven Q5 PCRs, DpnI digestion, four Golden Gate assemblies, and "
        "TOP10 transformation, with manual thermal and purification steps."
    ),
    "apiLevel": "2.15",
}


def run(protocol: protocol_api.ProtocolContext):
    tubes_50ml_1 = protocol.load_labware(
        "opentrons_6_tuberack_falcon_50ml_conical", 1, label="tubes_50ml_1"
    )
    tubes_1_5ml_1 = protocol.load_labware(
        "opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap",
        2,
        label="tubes_1_5ml_1",
    )
    primer_plate = protocol.load_labware(
        "corning_96_wellplate_360ul_flat", 3, label="primer_plate"
    )
    template_plate = protocol.load_labware(
        "corning_96_wellplate_360ul_flat", 4, label="template_plate"
    )
    pcr_plate = protocol.load_labware(
        "corning_96_wellplate_360ul_flat", 5, label="pcr_plate"
    )
    assembly_plate = protocol.load_labware(
        "corning_96_wellplate_360ul_flat", 6, label="assembly_plate"
    )
    cells_plate = protocol.load_labware(
        "corning_96_wellplate_360ul_flat", 7, label="cells_plate"
    )
    tubes_15ml_1 = protocol.load_labware(
        "opentrons_15_tuberack_falcon_15ml_conical", 8, label="tubes_15ml_1"
    )
    tips_20 = protocol.load_labware(
        "opentrons_96_tiprack_20ul", 10, label="tips_20"
    )
    tips_300 = protocol.load_labware(
        "opentrons_96_tiprack_300ul", 11, label="tips_300"
    )
    p20 = protocol.load_instrument(
        "p20_single_gen2", "left", tip_racks=[tips_20]
    )
    p300 = protocol.load_instrument(
        "p300_single_gen2", "right", tip_racks=[tips_300]
    )

    tip_counts = {p20: 0, p300: 0}

    def pick_up(pipette):
        if tip_counts[pipette] == 96:
            message = (
                f"Replace the exhausted {pipette.name} tip rack with fresh tips "
                "in its original slot, then resume."
            )
            protocol.comment(message)
            protocol.pause(message)
            pipette.reset_tipracks()
            tip_counts[pipette] = 0
        pipette.pick_up_tip()
        tip_counts[pipette] += 1

    def transfer(volume, source, destination, mix_after=None):
        pipette = p20 if volume <= 20 else p300
        pick_up(pipette)
        pipette.aspirate(volume, source)
        pipette.dispense(volume, destination)
        if mix_after is not None:
            repetitions, mix_volume = mix_after
            pipette.mix(repetitions, mix_volume, destination)
        pipette.drop_tip()

    def mix(repetitions, volume, well):
        pipette = p20 if volume <= 20 else p300
        pick_up(pipette)
        pipette.mix(repetitions, volume, well)
        pipette.drop_tip()

    def manual(message, pause=False):
        protocol.comment(message)
        if pause:
            protocol.pause(message)

    water = tubes_50ml_1["A1"]
    q5_buffer = tubes_1_5ml_1["A1"]
    dntp = tubes_1_5ml_1["B1"]
    q5_pol = tubes_1_5ml_1["C1"]
    pcr_mm = tubes_1_5ml_1["D1"]
    rcutsmart = tubes_1_5ml_1["A2"]
    dpni = tubes_1_5ml_1["B2"]
    t4_buffer = tubes_1_5ml_1["C2"]
    gg_enzyme = tubes_1_5ml_1["D2"]
    lb_dextrose = tubes_15ml_1["A1"]

    fragment_names = ("A1", "B1", "C1", "D1", "E1", "F1", "G1")
    fragment_wells = [pcr_plate[name] for name in fragment_names]
    reaction_names = ("A1", "B1", "C1", "D1")
    assembly_wells = [assembly_plate[name] for name in reaction_names]
    cell_wells = [cells_plate[name] for name in reaction_names]

    # 1-5: Prepare 152 uL of PCR master mix for eight reactions.
    transfer(106, water, pcr_mm)
    transfer(40, q5_buffer, pcr_mm)
    transfer(4, dntp, pcr_mm)
    transfer(2, q5_pol, pcr_mm)
    mix(5, 100, pcr_mm)

    # 6-10: Set up seven 25 uL PCRs; each primer is 0.1 uM final.
    for destination in fragment_wells:
        transfer(19, pcr_mm, destination)
    for name, destination in zip(fragment_names, fragment_wells):
        transfer(2.5, primer_plate[name], destination)
    reverse_names = ("A2", "B2", "C2", "D2", "E2", "F2", "G2")
    for name, destination in zip(reverse_names, fragment_wells):
        transfer(2.5, primer_plate[name], destination)
    template_names = ("A1", "A1", "B1", "C1", "A1", "A1", "D1")
    for name, destination in zip(template_names, fragment_wells):
        transfer(1, template_plate[name], destination)
    for well in fragment_wells:
        mix(3, 15, well)

    # 11: The fixed flat plates stand in for thermocycler-compatible tubes.
    manual(
        "STEP 11 — Seal the PCR reactions or move them to compatible PCR "
        "tubes and transfer manually to the Bio-Rad C100 gradient thermocycler. "
        "Run 98 C for 30 s; 34 cycles of 98 C for 10 s, annealing for 30 s at "
        "the AssemblyTron/j5 optimal-gradient temperature for each fragment, "
        "and 72 C extension for the AssemblyTron-set time (about 20-30 s/kb); "
        "then 72 C for 5 min and hold at 4 C. Use the actual j5 design values; "
        "fragment-specific temperatures and lengths are not supplied here. "
        "Take a sample of each reaction for gel electrophoresis. Return the "
        "reactions to pcr_plate A1:G1 in their original order, unseal for "
        "pipetting, and resume.",
        pause=True,
    )

    # 12-15: Bring each reaction to 50 uL for DpnI digestion.
    for destination in fragment_wells:
        transfer(19, water, destination)
    for destination in fragment_wells:
        transfer(5, rcutsmart, destination)
    for destination in fragment_wells:
        transfer(1, dpni, destination)
    for well in fragment_wells:
        mix(3, 30, well)

    manual(
        "STEP 16 — Incubate pcr_plate A1:G1 (in compatible PCR tubes on a "
        "thermocycler block) at 37 C for 30 min, then 65 C for 20 min to "
        "inactivate DpnI. Return to the original deck positions and resume.",
        pause=True,
    )
    manual(
        "STEP 17 — Pause for manual fragment purification with seven Zymo "
        "DNA Clean & Concentrator-5 columns. Add DNA Binding Buffer at 5:1 "
        "buffer:sample (250 uL per 50 uL sample), load and spin 30 s, wash "
        "twice with 200 uL DNA Wash Buffer with 30 s spins, then elute each "
        "fragment in 20 uL water after 1 min at room temperature and a 30 s "
        "spin. Replace the contents of pcr_plate A1:G1 with the corresponding "
        "20 uL eluates (fragments 1-7); do not add eluates to the old reactions. "
        "Resume only after all seven purified fragments have been returned.",
        pause=True,
    )

    # 18-24: Four 20 uL Golden Gate reactions; prescribed length-based volumes.
    for destination in assembly_wells:
        transfer(7, water, destination)
    for destination in assembly_wells:
        transfer(2, t4_buffer, destination)
    for destination in assembly_wells:
        transfer(3, pcr_plate["B1"], destination)
    for destination in assembly_wells:
        transfer(2, pcr_plate["E1"], destination)
    for destination in assembly_wells:
        transfer(3, pcr_plate["F1"], destination)
    chromoprotein_names = ("A1", "C1", "D1", "G1")
    for name, destination in zip(chromoprotein_names, assembly_wells):
        transfer(2, pcr_plate[name], destination)
    for destination in assembly_wells:
        transfer(1, gg_enzyme, destination, mix_after=(5, 15))

    manual(
        "STEP 25 — Run the Golden Gate program using compatible reaction "
        "vessels on the Opentrons thermocycler module if separately available: "
        "30 cycles of 37 C for 5 min and 16 C for 5 min, then 60 C for 5 min "
        "and hold at 4 C; lid about 85 C. No module is loaded on this fixed "
        "deck, so pause and move the reactions to an external thermocycler. "
        "Return the reactions to assembly_plate A1:D1 in their original order "
        "and resume.",
        pause=True,
    )
    manual(
        "STEP 26 — Clean and concentrate each assembly using a separate Zymo "
        "DNA Clean & Concentrator-5 column: DNA Binding Buffer at 5:1 "
        "buffer:sample (100 uL per 20 uL reaction), load and spin 30 s, wash "
        "twice with 200 uL DNA Wash Buffer with 30 s spins, and elute in "
        "10 uL molecular grade water after 1 min at room temperature and a "
        "30 s spin. Replace the contents of assembly_plate A1:D1 with the "
        "corresponding 10 uL eluates, not the unpurified reactions. Return "
        "cells_plate A1:D1 containing 50 uL TOP10 competent cells each from "
        "cold storage immediately before transformation; keep the cells cold "
        "during setup. Resume when the eluates and cells are ready.",
        pause=True,
    )

    # 27: Separate fresh tips avoid cross-contamination between assemblies.
    for source, destination in zip(assembly_wells, cell_wells):
        transfer(5, source, destination)

    manual(
        "STEP 28 — Measure DNA concentration of the remaining 5 uL of each "
        "assembly eluate with a NanoDrop-2000c for the CFU/ug calculation. "
        "Record concentrations and keep the competent-cell mixtures cold.",
        pause=True,
    )
    manual(
        "STEP 29 — Incubate cells_plate A1:D1 for 30 min on ice, heat shock "
        "at 42 C for 60 s using suitable vessels, then return to ice for about "
        "2 min. Return mixtures to cells_plate A1:D1 and resume for recovery "
        "medium addition.",
        pause=True,
    )

    # 30: Each cell well now contains 305 uL, below its 360 uL capacity.
    for destination in cell_wells:
        transfer(250, lb_dextrose, destination)

    manual(
        "STEP 31 — Recover the cells at 37 C for 60 min with shaking at "
        "about 250 rpm.",
        pause=True,
    )
    manual(
        "STEP 32 — Plate 50-200 uL of each recovery, neat or at a 10x "
        "dilution depending on predicted efficiency, onto separate LB agar "
        "plates containing kanamycin at 50 ug/mL. Keep identities: A1 purple "
        "(tsPurple), B1 orange (YukonOFP), C1 blue (aeBlue), D1 green (fuGFP). "
        "Incubate at 37 C overnight.",
        pause=True,
    )
    manual(
        "STEP 33 — Manually count colonies and score the fraction showing "
        "the expected purple, orange, blue, or green colour. Report CFU/ug "
        "of DNA plated. DNA input is concentration (ng/uL) x 5 uL / 1000; "
        "the plated fraction is plated volume / 305 uL, divided by 10 for "
        "a 10x dilution. CFU/ug = colonies / (DNA input in ug x plated fraction)."
    )
