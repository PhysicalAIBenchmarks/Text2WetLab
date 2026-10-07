"""Four four-fragment chromoprotein Golden Gate assemblies on an OT-2.

Source: AssemblyTron, Synth. Biol. (2022), doi:10.1093/synbio/ysac032,
sections 2.1, 2.3, 2.4 and 3.2 (CC BY 4.0).

All listed deck positions are preserved. Thermal steps, column purification,
gel QC and plating require an operator; comments AND pauses enforce handoffs.
The fixed flat plates are liquid-handling staging plates, not PCR labware.
"""

from opentrons import protocol_api

metadata = {
    "protocolName": "AssemblyTron: four chromoprotein Golden Gate plasmids",
    "author": "OpenAI",
    "description": "Seven PCRs, DpnI, column cleanup, four assemblies, TOP10 transformation.",
    "apiLevel": "2.13",
}

# The supplied design has neither primer Tms nor fragment lengths. It is not
# possible to reconstruct the AssemblyTron gradient or extension calculation.
# These MUST be obtained from the actual j5/AssemblyTron design before running;
# the PCR handoff explicitly requires the operator to enter those parameters.
# Choosing an arbitrary uniform annealing temperature would not reproduce the
# paper. Of its two supported cycle counts, we choose 34 cycles.
PCR_CYCLES = 34

# Standard Q5 choices where the paper does not specify reagent quantities:
# 1X Q5 buffer, 200 uM each dNTP (stock 10 mM EACH), 0.25 uL Q5 enzyme
# (standard 2 U/uL stock), 0.1 uM each primer and 0.5 ng template / 25 uL.
PCR_MM_REACTIONS = 8  # Seven PCRs plus one reaction's dispensing allowance.
PCR_MM_PER_WELL = 19.0
PCR_MM_COMPONENTS = (
    ("water", 13.25),
    ("q5_buffer", 5.0),
    ("dntp", 0.5),
    ("q5_pol", 0.25),
)

# Chosen because the paper does not report its GG reagent recipe or thermal
# program: 20 uL total, 1X T4 buffer, 1 uL BsaI-HFv2/T4 ligase enzyme mix.
# The fixed fragment additions total 10 uL; 7 + 2 + 10 + 1 = 20 uL.
GG_WATER = 7.0
GG_BUFFER = 2.0
GG_ENZYME = 1.0
GG_CYCLES = 30
GG_PROGRAM = (
    "30 cycles of 37 C for 5 min then 16 C for 5 min; "
    "60 C for 5 min; hold at 4 C (heated lid approximately 85 C)."
)
# This is a conventional chosen Golden Gate program, not an exact cycling
# program stated by the article; confirm compatibility with the supplied mix.

# Fragment elution volume is our choice; 20 uL covers each shared backbone's
# 12/8/12 uL consumption with a residual volume. Final 10 uL elution is from
# the paper. Its 'other 5 uL' for NanoDrop implies 5 uL for transformation.
FRAGMENT_ELUTION = 20.0
ASSEMBLY_ELUTION = 10.0
TRANSFORM_DNA = 5.0

FRAGMENTS = (
    # fragment, PCR well, forward primer, reverse primer, template
    (1, "A1", "A1", "A2", "A1"),
    (2, "B1", "B1", "B2", "A1"),
    (3, "C1", "C1", "C2", "B1"),
    (4, "D1", "D1", "D2", "C1"),
    (5, "E1", "E1", "E2", "A1"),
    (6, "F1", "F1", "F2", "A1"),
    (7, "G1", "G1", "G2", "D1"),
)
ASSEMBLIES = (
    # assembly/cell well, reporter, (fragment, cleaned volume in uL)
    ("A1", "tsPurple", ((2, 3.0), (5, 2.0), (6, 3.0), (1, 2.0))),
    ("B1", "YukonOFP", ((2, 3.0), (5, 2.0), (6, 3.0), (3, 2.0))),
    ("C1", "aeBlue", ((2, 3.0), (5, 2.0), (6, 3.0), (4, 2.0))),
    ("D1", "fuGFP", ((2, 3.0), (5, 2.0), (6, 3.0), (7, 2.0))),
)


def run(protocol: protocol_api.ProtocolContext):
    tubes_50ml_1 = protocol.load_labware(
        "opentrons_6_tuberack_falcon_50ml_conical", 1, label="tubes_50ml_1"
    )
    tubes_1_5ml_1 = protocol.load_labware(
        "opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap", 2,
        label="tubes_1_5ml_1"
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
    tips20 = protocol.load_labware("opentrons_96_tiprack_20ul", 10)
    tips300 = protocol.load_labware("opentrons_96_tiprack_300ul", 11)
    p20 = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tips20])
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips300])

    reagents = {
        "water": tubes_50ml_1["A1"],
        "q5_buffer": tubes_1_5ml_1["A1"],
        "dntp": tubes_1_5ml_1["B1"],
        "q5_pol": tubes_1_5ml_1["C1"],
        "pcr_mm": tubes_1_5ml_1["D1"],
        "rcutsmart": tubes_1_5ml_1["A2"],
        "dpni": tubes_1_5ml_1["B2"],
        "t4_buffer": tubes_1_5ml_1["C2"],
        "gg_enzyme": tubes_1_5ml_1["D2"],
        "lb_dextrose": tubes_15ml_1["A1"],
    }
    fragment_wells = {number: pcr_plate[well] for number, well, _, _, _ in FRAGMENTS}

    # Track finite inputs and operator-replaced volumes. None denotes the
    # supplied 'plenty' stocks, not an empty well. Every aspirate and mix is
    # checked before execution; no untracked well can be used as a source.
    volumes = {well: None for name, well in reagents.items() if name != "pcr_mm"}
    volumes[reagents["pcr_mm"]] = 0.0
    for _, well, forward, reverse, _ in FRAGMENTS:
        volumes[pcr_plate[well]] = 0.0
        volumes[primer_plate[forward]] = 50.0
        volumes[primer_plate[reverse]] = 50.0
    for well in ("A1", "B1", "C1", "D1"):
        volumes[template_plate[well]] = 20.0
        volumes[assembly_plate[well]] = 0.0
        volumes[cells_plate[well]] = 50.0

    tips_used = {p20: 0, p300: 0}

    def manual(message):
        protocol.comment(message)
        protocol.pause("OPERATOR ACTION REQUIRED: " + message)

    def pick_up(pipette):
        if pipette.has_tip:
            raise RuntimeError("A previous operation left a tip attached.")
        if tips_used[pipette] == 96:
            slot = 10 if pipette is p20 else 11
            manual(
                "Replace the exhausted {} tip rack in slot {} with a full, "
                "sterile rack of the same type, then resume.".format(pipette.name, slot)
            )
            pipette.reset_tipracks()
            tips_used[pipette] = 0
        pipette.pick_up_tip()
        tips_used[pipette] += 1

    def choose_pipette(volume):
        # Never split a >20 uL transfer across the P20 or use the P300 below
        # its stated 20 uL minimum. At exactly 20 uL we choose the P20.
        if 1.0 <= volume <= 20.0:
            return p20
        if 20.0 < volume <= 300.0:
            return p300
        raise ValueError("Volume outside the available pipette ranges: {}".format(volume))

    def check_source(well, volume):
        if well not in volumes:
            raise RuntimeError("Untracked source: {}".format(well))
        available = volumes[well]
        if available is not None and available + 1e-6 < volume:
            raise RuntimeError("Insufficient liquid in {}: {} < {}".format(well, available, volume))

    def move(volume, source, destination):
        pipette = choose_pipette(volume)
        check_source(source, volume)
        if destination not in volumes or volumes[destination] is None:
            raise RuntimeError("Destination must have a known starting volume.")
        if volumes[destination] + volume > destination.max_volume + 1e-6:
            raise RuntimeError("Destination capacity exceeded: {}".format(destination))
        pick_up(pipette)
        # Flat wells contain shallow pools at 5-20 uL: use 0.1 mm for plate
        # aspiration rather than 0.5 mm, which can lie above the liquid surface.
        # Confirm offsets/clearance experimentally before running. The fixed
        # plates are proxies, not optimal low-volume PCR/assembly vessels.
        source_height = 0.1 if source.parent in (
            primer_plate, template_plate, pcr_plate, assembly_plate, cells_plate
        ) else 0.5
        pipette.aspirate(volume, source.bottom(source_height))
        pipette.dispense(volume, destination.bottom(0.5))
        # No air gaps, prewetting losses, or shared destination-contact tips.
        pipette.drop_tip()
        if volumes[source] is not None:
            volumes[source] -= volume
        volumes[destination] += volume

    def mix(well, volume, repetitions=3, gentle=False):
        pipette = choose_pipette(volume)
        check_source(well, volume)
        pick_up(pipette)
        old_aspirate = pipette.flow_rate.aspirate
        old_dispense = pipette.flow_rate.dispense
        if gentle:
            pipette.flow_rate.aspirate = 3.0
            pipette.flow_rate.dispense = 3.0
        height = 0.1 if well.parent in (
            pcr_plate, assembly_plate, cells_plate
        ) else 0.5
        pipette.mix(repetitions, volume, well.bottom(height))
        pipette.flow_rate.aspirate = old_aspirate
        pipette.flow_rate.dispense = old_dispense
        pipette.drop_tip()

    protocol.comment(
        "Source: AssemblyTron, doi:10.1093/synbio/ysac032. "
        "Sequence: PCR -> DpnI -> fragment cleanup -> Golden Gate -> "
        "assembly cleanup -> TOP10 transformation -> recovery -> selective plating."
    )
    manual(
        "Before starting, verify the actual j5/AssemblyTron per-fragment annealing "
        "temperatures, gradient tube positions and calculated extension time are "
        "available. They are NOT supplied in the fixed fragment table. Verify "
        "the assumed standard Q5 stocks (10 mM each dNTP, 2 U/uL polymerase) and "
        "that the Golden Gate mix is compatible with 1X T4 buffer and the chosen "
        "program. Calibrate deck/labware offsets. Keep enzyme stocks cold using "
        "compatible passive cooling. Move cells_plate to ice off deck now; keep "
        "its four 50 uL TOP10 aliquots cold until the transformation handoff."
    )
    protocol.comment(
        "Deck constraint: an OT-2 thermocycler normally occupies slots 7, 8, 10 "
        "and 11, which are occupied here. Do NOT load a module or move the fixed "
        "labware. The slot-6 assembly plate cannot actually be on that module. "
        "Use the paper's manual thermocycler alternative. Corning flat plates "
        "are staging labware: use labeled, sealed PCR tubes for all thermal "
        "steps, then quantitatively return each reaction to its original well."
    )

    # 1. Prepare 152 uL PCR master mix in the initially empty D1 tube.
    protocol.comment(
        "PCR master mix for 8 x 25 uL reactions: 106 uL water, 40 uL 5X Q5 "
        "buffer, 4 uL 10 mM dNTPs, 2 uL Q5 polymerase. Standard Q5 reagent "
        "quantities are chosen; the paper specifies the primer/template targets."
    )
    for reagent, per_reaction in PCR_MM_COMPONENTS:
        move(per_reaction * PCR_MM_REACTIONS, reagents[reagent], reagents["pcr_mm"])
    mix(reagents["pcr_mm"], 100.0, repetitions=5)

    # 2. Seven independent PCRs, 25 uL each; template A1 is used four times.
    for _, well, forward, reverse, template in FRAGMENTS:
        destination = pcr_plate[well]
        move(PCR_MM_PER_WELL, reagents["pcr_mm"], destination)
        move(2.5, primer_plate[forward], destination)
        move(2.5, primer_plate[reverse], destination)
        move(1.0, template_plate[template], destination)
        mix(destination, 15.0)
        assert abs(volumes[destination] - 25.0) < 1e-6

    manual(
        "PCR: transfer the seven complete 25 uL reactions from pcr_plate A1:G1 "
        "to labeled PCR tubes (fragments 1-7), seal, briefly spin, and load the "
        "Bio-Rad C100 gradient thermocycler in the AssemblyTron-calculated tube "
        "positions. Run 98 C 30 s; {} cycles of 98 C 10 s, the actual "
        "AssemblyTron/j5 per-fragment gradient annealing temperatures for 30 s, "
        "and 72 C for the AssemblyTron-calculated extension time; then 72 C "
        "5 min and hold 4 C (hold temperature chosen). Do not use arbitrary "
        "annealing/extension settings. Return each entire product to the matching "
        "pcr_plate well in slot 5. Take exactly 1 uL from each for manual gel QC "
        "(1% agarose, 1X TAE, GelRed, 1 kb plus ladder); confirm a band of the "
        "design's expected size. Resume only with 24 uL in each A1:G1 and "
        "successful QC; failed PCRs must be repeated before proceeding.".format(PCR_CYCLES)
    )
    for destination in fragment_wells.values():
        volumes[destination] = 24.0
        # The paper does not specify the QC aliquot volume. We choose 1 uL and
        # replace it with water so the stated digestion remains 50 uL / 1X.
        move(1.0, reagents["water"], destination)

    # 3. Paper's DpnI recipe: add 19 + 5 + 1 uL to each 25 uL PCR.
    protocol.comment(
        "Replace the chosen 1 uL gel-QC aliquot with 1 uL water per PCR. "
        "Then add the paper's 19 uL water, 5 uL rCutSmart, and 1 uL DpnI: "
        "50 uL digestion, 1X rCutSmart, per fragment."
    )
    for destination in fragment_wells.values():
        move(19.0, reagents["water"], destination)
        move(5.0, reagents["rcutsmart"], destination)
        move(1.0, reagents["dpni"], destination)
        mix(destination, 30.0)
        assert abs(volumes[destination] - 50.0) < 1e-6
    manual(
        "DpnI digestion: move each full 50 uL reaction to its labeled PCR tube, "
        "seal and incubate off deck at 37 C for 30 min, then 65 C for 20 min "
        "to inactivate DpnI. Cool and briefly spin. Proceed to fragment "
        "purification; do not assemble untreated PCR products."
    )

    # 4. Polymerase removal is essential for the paper's GG workflow.
    manual(
        "Purify each of the seven 50 uL digested PCR products separately with "
        "a Zymo DNA Clean & Concentrator-5 column to remove Q5 polymerase and "
        "digestion reagents. Follow the current kit instructions (binding, "
        "centrifugation, two washes and thorough removal of ethanol); these "
        "details are not stated in the paper. A standard dsDNA cleanup choice "
        "is 5:1 binding buffer:sample (250 uL per 50 uL), with 2 x 200 uL "
        "wash buffer. Elute each in 20 uL nuclease-free water (chosen volume). "
        "Empty/rinse and dry the original pcr_plate wells, then return the "
        "ENTIRE 20 uL cleaned eluate to its original A1:G1 well in slot 5. "
        "Do not pool fragments. Resume only after all seven wells contain "
        "their cleaned fragment, without residual unpurified reaction."
    )
    for destination in fragment_wells.values():
        volumes[destination] = FRAGMENT_ELUTION

    # 5. Four assemblies: use exactly the fixed, length-proportional volumes.
    protocol.comment(
        "Prepare four 20 uL Golden Gate reactions in assembly_plate A1:D1. "
        "Chosen recipe: 7 uL water + 2 uL 10X T4 buffer + 10 uL cleaned "
        "fragments + 1 uL Golden Gate enzyme mix, added last. The length-based "
        "fragment ratios use the paper's equal-PCR-yield assumption."
    )
    for well, reporter, parts in ASSEMBLIES:
        destination = assembly_plate[well]
        protocol.comment("Assemble {} in {}.".format(reporter, well))
        move(GG_WATER, reagents["water"], destination)
        move(GG_BUFFER, reagents["t4_buffer"], destination)
        for number, volume in parts:
            move(volume, fragment_wells[number], destination)
        move(GG_ENZYME, reagents["gg_enzyme"], destination)
        mix(destination, 15.0, repetitions=5)
        assert abs(volumes[destination] - 20.0) < 1e-6
    manual(
        "Golden Gate thermal step: move each complete 20 uL assembly to "
        "a separate labeled PCR tube, seal and briefly spin. Use an off-deck "
        "thermocycler (or an independently operated off-deck Opentrons "
        "thermocycler). Chosen program, since the paper does not give timings: "
        + GG_PROGRAM + " Keep A1 tsPurple, B1 YukonOFP, C1 aeBlue and D1 fuGFP "
        "identities throughout. Resume only after cycling has completed."
    )

    # 6. Final column concentration before transformation (paper: 10 uL).
    manual(
        "Purify each complete 20 uL Golden Gate assembly separately using a "
        "Zymo DNA Clean & Concentrator-5 column, following the current kit "
        "instructions. The chosen 5:1 binding ratio requires 100 uL binding "
        "buffer per assembly; wash twice (standard choice: 200 uL per wash) "
        "and remove residual ethanol. Elute each in exactly 10 uL molecular "
        "grade water, as in the paper. Empty/rinse and dry assembly_plate "
        "A1:D1; return the entire matching 10 uL eluate to each original well "
        "in slot 6. Immediately before resuming, return cells_plate to slot 7 "
        "with its four cold 50 uL TOP10 aliquots. Minimize time off ice."
    )
    for well, _, _ in ASSEMBLIES:
        volumes[assembly_plate[well]] = ASSEMBLY_ELUTION

    # 7. Use 5 uL per 50 uL cells; reserve the 'other 5 uL' for NanoDrop.
    protocol.comment(
        "Transform 5 uL purified assembly into each matching 50 uL TOP10 "
        "aliquot; 5 uL remains for the paper's DNA concentration measurement. "
        "Cells are mixed gently with slow pipetting; never vortex."
    )
    for well, _, _ in ASSEMBLIES:
        move(TRANSFORM_DNA, assembly_plate[well], cells_plate[well])
        mix(cells_plate[well], 10.0, repetitions=2, gentle=True)
    manual(
        "Immediately move cells_plate off deck to ice. Incubate each 55 uL "
        "DNA/cell mix on ice for 30 min. Transfer each complete mixture into "
        "a separate chilled, labeled transformation tube and heat shock at "
        "42 C for 60 s in a calibrated water bath; return to ice for 2 min "
        "(the post-shock ice step is a chosen standard practice, not specified "
        "in the paper). Return each entire 55 uL mix to its original cells_plate "
        "well A1:D1 in slot 7 and resume promptly for medium addition. While "
        "the mixtures incubate, use the reserved 5 uL of each assembly eluate "
        "for NanoDrop-2000c DNA quantification and record concentration for "
        "CFU/ug calculations. Do not remove cells for DNA quantification."
    )
    # The remaining assembly eluates have been consumed/reserved off deck;
    # no subsequent robotic operation aspirates from those wells.
    for well, _, _ in ASSEMBLIES:
        volumes[assembly_plate[well]] = 0.0

    # 8. Recovery medium is exactly 250 uL, not 300 uL (final well = 305 uL).
    for well, _, _ in ASSEMBLIES:
        move(250.0, reagents["lb_dextrose"], cells_plate[well])
        assert abs(volumes[cells_plate[well]] - 305.0) < 1e-6
    manual(
        "Recovery: gently mix and transfer each entire 305 uL recovery to a "
        "separate labeled sterile culture tube. Incubate at 37 C for 60 min. "
        "Use gentle aeration/shaking (250 rpm chosen; the paper does not "
        "specify agitation). Medium is LB + 0.2% (w/v) dextrose."
    )
    for well, _, _ in ASSEMBLIES:
        volumes[cells_plate[well]] = 0.0
    manual(
        "Plate each recovered culture separately on LB agar containing "
        "kanamycin 50 ug/mL (backbone contains KanR). The paper allows "
        "50-200 uL neat or a 10-fold dilution, depending on expected yield; "
        "choose 100 uL neat initially and, if needed, an additional 100 uL "
        "of a 1:10 dilution on a separate plate. Incubate at 37 C overnight. "
        "Count colonies and score purple/orange/blue/green expression for "
        "tsPurple/YukonOFP/aeBlue/fuGFP, respectively. For efficiency use "
        "CFU/ug = colonies / [(5 uL x measured ng/uL / 1000) x "
        "(plated uL / 305 uL) x dilution fraction]; neat fraction = 1 and "
        "1:10 fraction = 0.1. Verify representative plasmids by sequencing."
    )

    # Each liquid operation discards its tip; leave both mounts tip-free.
    assert not p20.has_tip and not p300.has_tip
    protocol.comment(
        "Complete: all four assemblies transformed, recovered and handed off "
        "for selective plating. Intermediate cleaned fragment volumes remain "
        "in pcr_plate A1:G1: 18, 8, 18, 18, 12, 8, 18 uL, respectively. "
        "PCR master mix D1 has 19 uL remaining. Neither pipette holds a tip."
    )
