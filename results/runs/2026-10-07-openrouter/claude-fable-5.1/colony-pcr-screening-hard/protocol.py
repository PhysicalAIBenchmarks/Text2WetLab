"""
Colony PCR screening of 96 transformant colonies on the Opentrons OT-2.

Adapted from the OT-2 colony PCR workflow of Slowpoke (Golden Gate cloning and
colony PCR on OT-2/Flex, ACS Synth. Biol., doi:10.1021/acssynbio.5c00629):
    * 10 uL reaction per colony: 9 uL PCR master mix (2x PCR mix + primers
      + water) dispensed into each reaction well first, followed by 1 uL of
      colony template from the colony template plate.
    * Reactions are then cycled according to the polymerase manufacturer's
      protocol, with annealing temperature / extension time adjusted to the
      primers and amplicon size.

Adaptation to the reagents on this deck:
    * The paper pre-mixes water, primers and 2x PCR mix into one master mix.
      Here the Q5 Hot Start 2x master mix (reservoir) and a separate primer
      pair per colony (primer_plate) are provided, so the 9 uL "master mix"
      is assembled directly in each PCR well: 5 uL Q5 2x (1x final in 10 uL)
      + 4 uL of the colony-specific primer pair.  No separate water addition
      is needed: the primer pair is assumed to be a pre-mixed working stock
      (1.25 uM each primer) so that 4 uL in 10 uL gives the NEB-recommended
      0.5 uM final concentration of each primer.
    * No thermocycler module is on the deck, so (as the paper allows) the
      plate is cycled in a benchtop thermocycler; that step is recorded
      with protocol.comment().
"""

from opentrons import protocol_api
from opentrons.protocol_api.labware import OutOfTipsError

metadata = {
    'protocolName': 'Colony PCR screening of 96 colonies (Slowpoke OT-2 workflow, Q5 Hot Start)',
    'author': 'Adapted from Slowpoke (doi:10.1021/acssynbio.5c00629)',
    'description': 'Set up 96 x 10 uL Q5 Hot Start colony PCR reactions: '
                   '5 uL Q5 2x master mix + 4 uL primer pair + 1 uL colony template.',
    'apiLevel': '2.15',
}

# ---------------------------------------------------------------------------
# Reaction recipe (uL per well; 10 uL total, as in the paper's OT-2 workflow)
# ---------------------------------------------------------------------------
MASTER_MIX_VOL = 5.0    # Q5 Hot Start 2x master mix -> 1x in 10 uL
PRIMER_VOL = 4.0        # colony-specific primer pair (pre-mixed working stock)
TEMPLATE_VOL = 1.0      # colony template (paper: 1 uL on the OT-2)
REACTION_VOL = MASTER_MIX_VOL + PRIMER_VOL + TEMPLATE_VOL   # 10 uL
NUM_REACTIONS = 96

# Q5 Hot Start cycling parameters (NEB protocol, adjusted for colony PCR).
# Choice: a 3 min initial denaturation is used instead of NEB's 30 s to lyse
# the E. coli cells in the colony template.  Extension time assumes an
# amplicon of up to ~1.5 kb (Q5: 20-30 s/kb); adjust to the actual amplicon.
# Annealing temperature assumes primers with Tm ~ 60-65 C (NEB Tm calculator,
# Q5 anneals at Tm_lower + 3 C); adjust to the actual primer pair.
INITIAL_DENATURATION = (98, '3 min')
CYCLES = 35
DENATURATION = (98, '10 s')
ANNEALING = (62, '20 s')
EXTENSION = (72, '45 s')
FINAL_EXTENSION = (72, '2 min')
HOLD = (4, 'hold')


def run(protocol: protocol_api.ProtocolContext):

    # ---------------------------------------------------------------- deck --
    colony_plate = protocol.load_labware(
        'corning_96_wellplate_360ul_flat', 1, label='colony_plate')
    pcr_plate = protocol.load_labware(
        'corning_96_wellplate_360ul_flat', 2, label='pcr_plate')
    master_mix_reservoir = protocol.load_labware(
        'nest_1_reservoir_195ml', 3, label='master_mix_reservoir')
    primer_plate = protocol.load_labware(
        'corning_96_wellplate_360ul_flat', 4, label='primer_plate')

    tips20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tips300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)

    p20 = protocol.load_instrument(
        'p20_single_gen2', 'left', tip_racks=[tips20])
    # The p300 is mounted per the fixed deck setup, but every transfer in
    # this protocol is <= 20 uL, so only the p20 is used.
    p300 = protocol.load_instrument(
        'p300_single_gen2', 'right', tip_racks=[tips300])

    master_mix = master_mix_reservoir['A1']
    colony_wells = colony_plate.wells()[:NUM_REACTIONS]
    primer_wells = primer_plate.wells()[:NUM_REACTIONS]
    pcr_wells = pcr_plate.wells()[:NUM_REACTIONS]

    # ------------------------------------------------------------- helpers --
    def pick_up(pipette):
        """Pick up a tip; tips are unlimited, so refill the rack when empty."""
        try:
            pipette.pick_up_tip()
        except OutOfTipsError:
            protocol.comment('20 uL tip rack exhausted - replace the rack in '
                             'slot 10 with a fresh one.')
            pipette.reset_tipracks()
            pipette.pick_up_tip()

    # --------------------------------------------------------------- setup --
    protocol.comment(
        'Colony PCR screening of %d colonies (Slowpoke OT-2 workflow). '
        'Reaction: %.0f uL Q5 Hot Start 2x master mix + %.0f uL primer pair '
        '+ %.0f uL colony template = %.0f uL.'
        % (NUM_REACTIONS, MASTER_MIX_VOL, PRIMER_VOL, TEMPLATE_VOL,
           REACTION_VOL))
    protocol.comment(
        'Before starting: colonies were picked by hand into the colony '
        'template plate (slot 1), one colony per well A1:H12, matching the '
        'layout of the primer pairs in slot 4. Keep the Q5 Hot Start master '
        'mix cold until loading.')

    # Step 1 - Q5 Hot Start 2x master mix into every PCR well.
    # One tip is used for the whole distribution: the source is a single
    # reservoir and the destination wells are empty, so there is no risk of
    # cross-contamination.  The paper dispenses the PCR mix into every
    # reaction tube first, before the colony template.
    protocol.comment('Step 1: dispensing %.0f uL Q5 Hot Start 2x master mix '
                     'into each of the %d PCR wells.'
                     % (MASTER_MIX_VOL, NUM_REACTIONS))
    pick_up(p20)
    p20.distribute(
        MASTER_MIX_VOL,
        master_mix,
        pcr_wells,
        disposal_volume=2,
        new_tip='never',
    )
    p20.drop_tip()

    # Step 2 - colony-specific primer pair, fresh tip per pair; completes the
    # 9 uL "master mix" of the paper in each well.
    protocol.comment('Step 2: adding %.0f uL of the colony-specific primer '
                     'pair to each PCR well (fresh tip per pair).'
                     % PRIMER_VOL)
    for src, dest in zip(primer_wells, pcr_wells):
        pick_up(p20)
        p20.aspirate(PRIMER_VOL, src)
        p20.dispense(PRIMER_VOL, dest)
        p20.blow_out(dest.top())
        p20.drop_tip()

    # Step 3 - 1 uL colony template, fresh tip per colony, mixed into the
    # 9 uL reaction mix.
    protocol.comment('Step 3: adding %.0f uL colony template to each PCR '
                     'well and mixing (fresh tip per colony).'
                     % TEMPLATE_VOL)
    for src, dest in zip(colony_wells, pcr_wells):
        pick_up(p20)
        p20.aspirate(TEMPLATE_VOL, src)
        p20.dispense(TEMPLATE_VOL, dest)
        p20.mix(3, 5, dest)
        p20.blow_out(dest.top())
        p20.drop_tip()

    # ------------------------------------------------- off-deck operations --
    protocol.comment(
        'Robot steps complete. Seal the PCR plate (slot 2), briefly spin '
        'down (e.g. 1 min at 1000 x g) to collect the 10 uL reactions.')
    protocol.comment(
        'Off-deck thermocycling in a benchtop thermocycler (no thermocycler '
        'module on this deck; Q5 Hot Start protocol adjusted for colony PCR): '
        '%d C for %s (initial denaturation / cell lysis); %d cycles of '
        '%d C %s, %d C %s, %d C %s; final extension %d C for %s; hold at %d C. '
        'Adjust annealing temperature to the primer Tm and extension time '
        'to 20-30 s per kb of amplicon.'
        % (INITIAL_DENATURATION[0], INITIAL_DENATURATION[1], CYCLES,
           DENATURATION[0], DENATURATION[1], ANNEALING[0], ANNEALING[1],
           EXTENSION[0], EXTENSION[1], FINAL_EXTENSION[0],
           FINAL_EXTENSION[1], HOLD[0]))
    protocol.comment(
        'After cycling: analyse 5 uL of each reaction by agarose gel '
        'electrophoresis to identify colonies with the expected amplicon.')
