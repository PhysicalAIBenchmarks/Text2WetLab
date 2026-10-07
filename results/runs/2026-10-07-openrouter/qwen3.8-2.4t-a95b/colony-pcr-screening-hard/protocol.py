"""
Slowpoke-style colony PCR screening of 96 transformants on the OT-2.

Based on the Slowpoke paper (ACS Synth. Biol., doi:10.1021/acssynbio.5c00629),
"Automated Colony PCR" (OT-2 workflow): a 10 uL total reaction is assembled by
dispensing the master mix into each reaction well first, followed by 1 uL of
colony template; the paper's mix (9 uL of water + primers + 2x PCR master mix,
Phire Plant Direct) is then thermocycled per the manufacturer's protocol, with
annealing temperature and extension time adjusted for the fragment/primers.

Adaptation to the fixed deck loaded here (choices stated per the task brief):
  * Polymerase: Q5 Hot Start 2x master mix (NEB) instead of Phire Plant
    Direct. Q5 is a 2x mix, so it is used at half the final reaction volume:
    5 uL per 10 uL reaction (final 1x, per the manufacturer).
  * No water reservoir and no bulk-primer tube are on this deck; instead each
    well of `primer_plate` holds the (premixed forward + reverse) screening
    primer pair for the matching colony. The water component of the paper's
    9 uL master mix is therefore replaced by primer solution: we transfer
    4 uL of primer pair per reaction. ASSUMPTION: the primer pairs in the
    plate are dilute enough that 4 uL into 10 uL gives the NEB-recommended
    0.5-1 uM final primer concentration each (i.e. ~1.25-2.5 uM each primer
    in the plate). If the plate holds standard 10 uM working stocks, the
    operator must dilute them before loading, since the deck has no water.
  * Colony template: 1 uL per reaction, exactly as the OT-2 workflow in the
    paper (not the 2 uL Flex variant). ASSUMPTION: `colony_plate` holds
    picked colonies resuspended in liquid (water/TE or growth medium), as
    prepared manually in the Slowpoke workflow.
  * Reaction layout (per well of `pcr_plate`, 10 uL total):
        5 uL Q5 Hot Start 2x master mix
        4 uL primer pair (from the matching well of `primer_plate`)
        1 uL colony template (from the matching well of `colony_plate`)
  * Well mapping: well i of `colony_plate` <-> well i of `primer_plate` <->
    well i of `pcr_plate` (A1:H12, all 96 wells screened).
  * All volumes (1-5 uL) fall in the p20_single_gen2 range (1-20 uL), so the
    p20 does all liquid handling; the p300 (min 20 uL) is loaded but unused.
    A fresh tip is used for every aspiration (tips are unlimited; racks are
    reset between phases).
  * No thermocycler module is on this deck, so after reaction setup the plate
    is sealed and moved to a benchtop thermocycler (the paper allows benchtop
    cyclers alongside/instead of the Opentrons module). Cycling follows the
    Q5 Hot Start manufacturer's two-step protocol, adjusted as the paper
    describes for amplicon size and primer Tm (assumed <=1 kb amplicon,
    primers Tm >= 69 C):
        98 C  30 s        initial denaturation / hot-start activation
        30 cycles of:
            98 C  10 s    denaturation
            72 C  30 s    combined anneal/extend (~30 s/kb for <=1 kb)
        72 C  2 min       final extension
        4-10 C hold
"""

metadata = {
    'apiLevel': '2.13',
    'protocolName': 'Slowpoke OT-2 Colony PCR (Q5 2x, 96 colonies)',
    'description': 'Set up 96 x 10 uL colony PCR reactions from a colony '
                   'template plate, a per-colony primer plate and a Q5 Hot '
                   'Start 2x master mix reservoir, following the Slowpoke '
                   'OT-2 colony PCR workflow.',
    'author': 'Claude',
}

# Per-reaction volumes (uL); 10 uL total, matching the paper's OT-2 workflow.
MM_VOL = 5.0        # Q5 Hot Start 2x master mix -> 1x final
PRIMER_VOL = 4.0    # premixed primer pair (replaces the paper's mix water)
COLONY_VOL = 1.0    # colony template, as in the paper's OT-2 workflow
MIX_VOL = 8.0       # pipette-mix volume after template addition (well holds 10 uL)


def run(protocol):
    # ---------------- Deck (fixed) ----------------
    colony_plate = protocol.load_labware(
        'corning_96_wellplate_360ul_flat', 1, label='colony_plate')
    pcr_plate = protocol.load_labware(
        'corning_96_wellplate_360ul_flat', 2, label='pcr_plate')
    mm_reservoir = protocol.load_labware(
        'nest_1_reservoir_195ml', 3, label='master_mix_reservoir')
    primer_plate = protocol.load_labware(
        'corning_96_wellplate_360ul_flat', 4, label='primer_plate')

    tips20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tips300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)

    p20 = protocol.load_instrument(
        'p20_single_gen2', 'left', tip_racks=[tips20])
    # p300 is part of the fixed setup but every volume here (1-5 uL) is below
    # its 20 uL minimum, so the p20 does all of the liquid handling.
    p300 = protocol.load_instrument(
        'p300_single_gen2', 'right', tip_racks=[tips300])

    mm_source = mm_reservoir.wells()[0]

    # Consistent well-to-well mapping: A1:H12 on all three plates.
    colony_wells = colony_plate.wells()
    primer_wells = primer_plate.wells()
    pcr_wells = pcr_plate.wells()
    n_rxns = len(pcr_wells)  # 96

    protocol.comment(
        '=== Slowpoke colony PCR: %d x 10 uL reactions ==='
        'Setup: %s uL Q5 2x master mix + %s uL primer pair + %s uL colony '
        'template. Ensure colony_plate wells contain picked colonies '
        'resuspended in liquid, primer_plate wells contain the premixed '
        'primer pair for the matching colony, and the reservoir holds Q5 Hot '
        'Start 2x master mix on ice-chilled deck as per usual practice.'
        % (n_rxns, MM_VOL, PRIMER_VOL, COLONY_VOL))

    # Gentle handling of the enzyme mix and primers.
    p20.flow_rate.aspirate = 30   # uL/s (below default ~57) for accuracy
    p20.flow_rate.dispense = 30

    # ---------------- Step 1: dispense master mix ----------------
    # Paper: master mix is dispensed into every reaction well first, colony
    # template added last. Uses 96 x 5 uL = 480 uL of the 2x Q5 mix
    # (reservoir is stated to hold plenty).
    protocol.comment('Step 1/3: dispensing %s uL Q5 Hot Start 2x master mix '
                     'into all %d wells of pcr_plate.' % (MM_VOL, n_rxns))
    for dest in pcr_wells:
        p20.pick_up_tip()
        p20.aspirate(MM_VOL, mm_source.bottom(z=5))
        p20.dispense(MM_VOL, dest.bottom(z=1))
        p20.blow_out(dest.top(z=-2))
        p20.drop_tip()
    # Rack (96 tips) exhausted; tips are unlimited -> reset for next phase.
    p20.reset_tipracks()

    # ---------------- Step 2: add per-colony primer pairs ----------------
    # 4 uL of each colony's premixed primer pair; fresh tip per well (pairs
    # differ well-to-well, so no tip may be reused).
    protocol.comment('Step 2/3: adding %s uL of each colony\'s primer pair '
                     'from primer_plate to pcr_plate (fresh tip per well).'
                     % PRIMER_VOL)
    for src, dest in zip(primer_wells, pcr_wells):
        p20.pick_up_tip()
        p20.aspirate(PRIMER_VOL, src.bottom(z=1))
        p20.dispense(PRIMER_VOL, dest.bottom(z=1))
        p20.blow_out(dest.top(z=-2))
        p20.touch_tip()
        p20.drop_tip()
    p20.reset_tipracks()

    # ---------------- Step 3: add colony template ----------------
    # 1 uL per reaction, as in the paper's OT-2 workflow. Fresh tip per well
    # to avoid cross-contaminating colonies.
    protocol.comment('Step 3/3: adding %s uL colony template from colony_plate '
                     'to each reaction.' % COLONY_VOL)
    for src, dest in zip(colony_wells, pcr_wells):
        p20.pick_up_tip()
        p20.aspirate(COLONY_VOL, src.bottom(z=0.5))
        p20.dispense(COLONY_VOL, dest.bottom(z=1))
        # Mix the 10 uL reaction gently with the same tip, then blow out.
        p20.mix(3, MIX_VOL, dest.bottom(z=1))
        p20.blow_out(dest.top(z=-2))
        p20.touch_tip()
        p20.drop_tip()

    # ---------------- Manual steps the robot cannot do ----------------
    protocol.comment(
        'Reaction setup complete (96 x 10 uL). MANUAL STEPS: '
        '1) Seal pcr_plate with an optical/PCR seal and briefly centrifuge. '
        '2) Transfer the sealed plate to a benchtop thermocycler (no '
        'thermocycler module on this deck; the Slowpoke workflow also uses '
        'benchtop cyclers). '
        '3) Run Q5 Hot Start two-step cycling (per NEB manufacturer protocol, '
        'adjusted for fragment size/primer Tm as in the paper; assumes '
        '<=1 kb amplicon, primer Tm >= 69 C): '
        '98 C 30 s initial denaturation; '
        '30 cycles of [98 C 10 s; 72 C 30 s combined anneal/extend]; '
        '72 C 2 min final extension; hold 4-10 C. '
        'For longer amplicons extend the 72 C step (~30 s/kb); for lower-Tm '
        'primers use a 3-step program with an appropriate annealing step. '
        '4) Analyse products by agarose gel electrophoresis to score '
        'positive colonies by expected amplicon size.')
