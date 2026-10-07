"""Colony PCR screening of 96 transformant colonies on the Opentrons OT-2.

Adapted from the OT-2 colony PCR workflow of the Slowpoke paper:
    Slowpoke: An Automated Golden Gate Cloning Workflow for Opentrons OT-2
    and Flex, ACS Synth. Biol., doi:10.1021/acssynbio.5c00629
    (Materials & Methods 2.5, "Automated Colony PCR").

Paper's OT-2 colony PCR (Section 2.5):
    A master mix (water + colony PCR primers + 2x PCR master mix) is
    dispensed at 9 uL per reaction, then 1 uL of colony template is added,
    giving a 10 uL reaction. Cycling follows the polymerase manufacturer's
    protocol, with annealing temperature and extension time adjusted for
    the primers and amplicon.

Adaptations to the fixed deck of this run (each choice noted below):
  * The 2x master mix (Q5 Hot Start) is already pre-mixed in a 1-well
    reservoir; the robot therefore cannot prepare the paper's master mix
    from separate water/primer/mix stocks and dispenses the 2x mix directly.
  * Each colony has its OWN primer pair in primer_plate (same well position
    as the colony), so primers cannot be part of a common master mix and are
    added individually to each reaction.
  * The reaction stays at the paper's OT-2 volumes: 10 uL total with 1 uL
    of colony template. The paper's 9 uL of master mix is split into
    5 uL of 2x master mix (gives 1x final) + 4 uL of primer pair solution.
    This assumes the primer plate holds each primer pair pre-diluted at a
    working concentration such that 4 uL in 10 uL gives the desired final
    primer concentration (the paper leaves primer concentrations open).
  * No thermocycler module is loaded on this deck, so thermocycling is a
    manual benchtop step, recorded with protocol.comment() at the end (the
    paper ran the OT-2 workflow on the thermocycler module with benchtop
    cyclers added as needed).
"""

metadata = {
    'protocolName': 'Colony PCR screen of 96 colonies (Slowpoke OT-2 workflow, Q5 master mix)',
    'author': 'Generated from doi:10.1021/acssynbio.5c00629',
    'description': 'Set up 96 colony PCR reactions (Q5 Hot Start 2x master mix, '
                   'per-colony primer pairs, 1 uL colony template) following the '
                   'Slowpoke OT-2 colony PCR workflow.',
    'apiLevel': '2.13',
}

# --- Volumes (per 10 uL reaction, paper's OT-2 values) ---------------------
TEMPLATE_VOLUME = 1    # uL colony template (paper, OT-2 platform)
MASTER_MIX_VOLUME = 5  # uL Q5 Hot Start 2x master mix (1x final)
PRIMER_VOLUME = 4      # uL primer pair solution; with the master mix this
                       # replaces the paper's 9 uL premixed master mix
TOTAL_VOLUME = MASTER_MIX_VOLUME + PRIMER_VOLUME + TEMPLATE_VOLUME  # = 10 uL

N_COLONIES = 96


def run(protocol):
    # --- Labware (fixed deck layout) ---------------------------------------
    colony_plate = protocol.load_labware(
        'corning_96_wellplate_360ul_flat', 1, label='colony_plate')
    pcr_plate = protocol.load_labware(
        'corning_96_wellplate_360ul_flat', 2, label='pcr_plate')
    master_mix_reservoir = protocol.load_labware(
        'nest_1_reservoir_195ml', 3, label='master_mix_reservoir')
    primer_plate = protocol.load_labware(
        'corning_96_wellplate_360ul_flat', 4, label='primer_plate')

    tiprack_20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tiprack_300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)

    p20 = protocol.load_instrument(
        'p20_single_gen2', 'left', tip_racks=[tiprack_20])
    p300 = protocol.load_instrument(
        'p300_single_gen2', 'right', tip_racks=[tiprack_300])

    # All liquid volumes in this protocol are 1-20 uL, so only the p20 is
    # used. The p300 is loaded because the deck layout is fixed, but it
    # stays idle.
    del p300

    master_mix_source = master_mix_reservoir.wells_by_name()['A1']

    # One source well per colony, mapped 1:1 by well position:
    # colony_plate[i] -> primer_plate[i] -> pcr_plate[i]
    colony_wells = colony_plate.wells()[:N_COLONIES]
    primer_wells = primer_plate.wells()[:N_COLONIES]
    pcr_wells = pcr_plate.wells()[:N_COLONIES]

    protocol.comment(
        f"Set up {N_COLONIES} colony PCRs of {TOTAL_VOLUME} uL each: "
        f"{MASTER_MIX_VOLUME} uL Q5 Hot Start 2x master mix + "
        f"{PRIMER_VOLUME} uL primer pair (per colony) + "
        f"{TEMPLATE_VOLUME} uL colony template. "
        "Well map: colony_plate well X -> primer_plate well X -> pcr_plate well X.")

    # MANUAL STEP: the robot cannot unseal plates or check reagents.
    protocol.comment(
        "MANUAL STEP before start: remove lids/seals from colony_plate, "
        "primer_plate and pcr_plate; confirm master_mix_reservoir contains "
        "thawed, mixed Q5 Hot Start 2x master mix (>= ~500 uL incl. dead "
        "volume). Q5 Hot Start tolerates room-temperature set-up.")

    # --- Step 1: distribute 2x master mix -----------------------------------
    # Same reagent for every reaction, so one tip is re-used for the whole
    # distribution (as in the paper's master-mix distribution step).
    protocol.comment(
        f"Distributing {MASTER_MIX_VOLUME} uL of Q5 Hot Start 2x master mix "
        f"from master_mix_reservoir A1 to all {N_COLONIES} wells of pcr_plate.")
    p20.distribute(
        MASTER_MIX_VOLUME,
        master_mix_source,
        pcr_wells,
        new_tip='once',
    )

    # One tip per well is used from here on; start each step from a full rack.
    p20.reset_tipracks()

    # --- Step 2: add each colony's primer pair ------------------------------
    protocol.comment(
        f"Adding {PRIMER_VOLUME} uL of each primer pair from primer_plate to "
        "the same well of pcr_plate (fresh tip per well).")
    p20.transfer(
        PRIMER_VOLUME,
        primer_wells,
        pcr_wells,
        new_tip='always',   # different primer pair in every well
        touch_tip=True,
    )

    p20.reset_tipracks()

    # --- Step 3: add colony template (paper: template added last) -----------
    # MANUAL STEP: the robot cannot spin plates.
    protocol.comment(
        "MANUAL STEP: briefly spin down colony_plate so all template is at "
        "the bottom of the wells and colonies are resuspended.")
    protocol.comment(
        f"Adding {TEMPLATE_VOLUME} uL of colony template from colony_plate to "
        "the same well of pcr_plate (fresh tip per well), then mixing.")
    p20.transfer(
        TEMPLATE_VOLUME,
        colony_wells,
        pcr_wells,
        new_tip='always',
        touch_tip=True,
        mix_after=(3, 8),   # gentle mix of the 10 uL reaction after addition
    )

    # --- Manual thermocycling ------------------------------------------------
    # MANUAL STEP: no thermocycler module is loaded on this deck, and the OT-2
    # cannot seal plates or move them to a cycler. The program below follows
    # the NEB Q5 Hot Start 2x master mix protocol with colony-PCR adjustments;
    # the paper likewise leaves cycling to the polymerase manufacturer's
    # protocol with primer/amplicon-specific annealing and extension.
    protocol.comment(
        "MANUAL STEP - thermocycling: seal pcr_plate with an adhesive PCR "
        "seal, spin down, and run it in a benchtop thermocycler "
        "(heated lid ~105 degC):\n"
        "  98 degC  5 min   initial denaturation / colony lysis / hot-start "
        "activation (NEB gives 30 s; extended here because template is crude "
        "colony material)\n"
        "  35 cycles of:\n"
        "    98 degC 10 s   denaturation\n"
        "    60 degC 30 s   annealing (adjust to the primer Tms)\n"
        "    72 degC 30 s   extension (scale to 20-30 s/kb of amplicon)\n"
        "  72 degC  2 min   final extension\n"
        "  hold at 4 degC\n"
        "Then analyse the PCR products by agarose gel electrophoresis to "
        "score the colonies.")
