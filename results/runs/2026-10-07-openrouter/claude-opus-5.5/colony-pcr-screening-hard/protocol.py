"""
Colony PCR screening of 96 transformants on the OT-2.

Based on Slowpoke (ACS Synth. Biol., doi:10.1021/acssynbio.5c00629), section 2.5
"Automated Colony PCR", OT-2 workflow: 9 uL of PCR mix (2x master mix + primers
+ water) is dispensed into each reaction well first, then 1 uL of colony
template is added -> 10 uL reaction. Thermocycling follows the polymerase
manufacturer's protocol, with annealing temperature / extension time adjusted
to the primers and amplicon size.

Adaptation to this deck:
  * Polymerase is Q5 Hot Start 2x master mix (instead of Phire Plant Direct).
    In a 10 uL reaction it is used at 1x -> 5 uL per well.
  * Each colony has its own primer pair (primer_plate well == colony well), so
    the primers cannot be premixed into one master mix. The 9 uL "mix" is
    therefore assembled in the well: 5 uL Q5 2x + 4 uL primer pair.
    Assumption: the primer-plate wells hold each primer pair at 1.25 uM each
    (pre-diluted in water), giving the Q5-recommended 0.5 uM each in 10 uL.
    This 4 uL also replaces the water of the paper's mix (no water on deck).
  * Colony template (1 uL, as in the paper's OT-2 workflow) is added last and
    mixed in.
"""
from opentrons import protocol_api

metadata = {
    'protocolName': 'Slowpoke colony PCR (OT-2) - Q5 Hot Start, per-colony primers',
    'description': '96 colony PCR reactions: 5 uL Q5 2x + 4 uL primer pair + 1 uL colony',
    'apiLevel': '2.15',
}

MASTER_MIX_VOL = 5.0   # uL Q5 Hot Start 2x -> 1x in 10 uL
PRIMER_VOL = 4.0       # uL primer pair -> completes the paper's 9 uL PCR mix
COLONY_VOL = 1.0       # uL colony template (paper, OT-2 workflow)
REACTION_VOL = MASTER_MIX_VOL + PRIMER_VOL + COLONY_VOL  # 10 uL (paper, OT-2)


def run(protocol: protocol_api.ProtocolContext):
    # ---- labware (fixed deck) ----
    colony_plate = protocol.load_labware(
        'corning_96_wellplate_360ul_flat', 1, label='colony_plate')
    pcr_plate = protocol.load_labware(
        'corning_96_wellplate_360ul_flat', 2, label='pcr_plate')
    mm_res = protocol.load_labware(
        'nest_1_reservoir_195ml', 3, label='master_mix_reservoir')
    primer_plate = protocol.load_labware(
        'corning_96_wellplate_360ul_flat', 4, label='primer_plate')

    tips20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tips300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)

    # All volumes are 1-20 uL, so only the P20 does liquid handling. The P300
    # is loaded because it is mounted on the robot, but is never used.
    p20 = protocol.load_instrument(
        'p20_single_gen2', 'left', tip_racks=[tips20])
    protocol.load_instrument(
        'p300_single_gen2', 'right', tip_racks=[tips300])

    tips_per_rack = len(tips20.wells())
    tips_used = [0]

    def pick_up():
        # Tips are unlimited: refill the rack (reset) when it is exhausted.
        if tips_used[0] >= tips_per_rack:
            protocol.comment('20 uL tip rack used up - resetting tip rack.')
            p20.reset_tipracks()
            tips_used[0] = 0
        p20.pick_up_tip()
        tips_used[0] += 1

    master_mix = mm_res['A1']
    dests = pcr_plate.wells()          # A1..H12, column-wise
    colonies = colony_plate.wells()
    primers = primer_plate.wells()

    protocol.comment(
        'Before starting: colonies have been picked manually into colony_plate '
        '(A1:H12) and the matching primer pairs are in primer_plate (A1:H12). '
        'Keep the Q5 Hot Start 2x master mix cold until loading.')

    # ---- Step 1: 5 uL Q5 Hot Start 2x master mix into every well ----
    # The paper dispenses the PCR mix first. Destination wells are empty and
    # the source is shared, so one tip is reused for all 96 wells. Each
    # dispense goes to an empty well, so the tip never touches sample.
    protocol.comment('Step 1: dispensing 5 uL Q5 Hot Start 2x master mix to 96 wells.')
    pick_up()
    for dest in dests:
        p20.aspirate(MASTER_MIX_VOL, master_mix)
        p20.dispense(MASTER_MIX_VOL, dest.bottom(1))
        p20.blow_out(dest.bottom(3))
    p20.drop_tip()

    # ---- Step 2: 4 uL of the matching primer pair (completes the 9 uL mix) ----
    # Each primer pair is different, so use a fresh tip per well.
    protocol.comment('Step 2: adding 4 uL of each colony-specific primer pair.')
    for src, dest in zip(primers, dests):
        pick_up()
        p20.aspirate(PRIMER_VOL, src)
        p20.dispense(PRIMER_VOL, dest.bottom(1))
        p20.mix(2, 5, dest.bottom(1))
        p20.blow_out(dest.bottom(3))
        p20.drop_tip()

    # ---- Step 3: 1 uL colony template, added last, then mix ----
    protocol.comment('Step 3: adding 1 uL colony template to each reaction and mixing.')
    for src, dest in zip(colonies, dests):
        pick_up()
        p20.aspirate(COLONY_VOL, src)
        p20.dispense(COLONY_VOL, dest.bottom(1))
        p20.mix(3, 5, dest.bottom(1))   # 5 uL mix in 10 uL reaction
        p20.blow_out(dest.bottom(3))
        p20.drop_tip()

    # ---- Off-deck steps ----
    protocol.comment(
        'MANUAL: seal pcr_plate (adhesive PCR seal), spin down briefly and '
        'place it in the thermocycler (OT-2 thermocycler module or a benchtop '
        'thermocycler).')
    # Q5 programme per the NEB manufacturer protocol, adapted for colony PCR
    # (paper: follow the manufacturer's protocol and adjust annealing / extension
    # to the primers and fragment size). Chosen values: initial denaturation
    # extended from 30 s to 3 min so the cells lyse; Ta 60 C (set it to the
    # primers' Q5 Tm + 3 C); extension 30 s, i.e. 20-30 s/kb for amplicons
    # up to ~1 kb (lengthen it for longer inserts).
    protocol.comment(
        'MANUAL: thermocycle (lid 105 C, 10 uL): 98 C 3 min; 30 cycles of '
        '[98 C 10 s, 60 C 20 s, 72 C 30 s]; 72 C 2 min; hold 4 C.')
    protocol.comment(
        'MANUAL: analyse the PCR products by agarose gel electrophoresis to '
        'identify colonies with the expected amplicon size.')
