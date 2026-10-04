"""
Colony PCR screening of 96 transformant colonies on the Opentrons OT-2.

Adapted from the OT-2 colony PCR workflow of Slowpoke (Golden Gate cloning and
colony PCR on OT-2/Flex, ACS Synth. Biol., doi:10.1021/acssynbio.5c00629).

Paper (OT-2 workflow, Methods 2.5, Table S5):
  * 10 uL reaction per colony = 9 uL PCR master mix (water + colony PCR primers
    + 2x PCR master mix) dispensed into each reaction well, followed by 1 uL of
    colony template from the colony template plate.
  * Reactions set up per the polymerase manufacturer's protocol, with annealing
    temperature / extension time adjusted to the primers and amplicon size.
  * Thermocycling, sealing and gel electrophoresis are done off the pipetting
    deck (here: a benchtop thermocycler, since no thermocycler module is loaded).

Adaptation to the reagents on this deck (fixed by the operator):
  * The 2x mix is Q5 Hot Start High-Fidelity 2x Master Mix (NEB), in a reservoir.
  * Each colony has its own primer pair in `primer_plate` (same well as the
    colony), so the paper's single pre-mixed "water + primers + 2x mix" master
    mix cannot be pre-made; instead the 9 uL is assembled in-well as
        5 uL Q5 2x master mix  (1x final, as NEB requires)
      + 4 uL primer pair       (replaces the paper's water + primer share)
      + 1 uL colony template   (as in the paper)
      = 10 uL, identical to the paper's OT-2 reaction volume.
    There is no water on the deck, so the primer pairs are assumed to be
    supplied pre-diluted in water at 1.25 uM each (-> 0.5 uM each final, NEB's
    recommended Q5 primer concentration). This is stated as an assumption.
"""

from opentrons import protocol_api

metadata = {
    'protocolName': 'Colony PCR screening of 96 colonies (Slowpoke OT-2 workflow, Q5 Hot Start)',
    'author': 'Adapted from Slowpoke (doi:10.1021/acssynbio.5c00629)',
    'description': ('Assemble 96 x 10 uL Q5 Hot Start colony PCRs: 5 uL 2x master mix, '
                    '4 uL colony-specific primer pair, 1 uL colony template; then '
                    'seal and thermocycle off-deck.'),
    'apiLevel': '2.15',
}

# ---------------------------------------------------------------- volumes (uL)
MASTER_MIX_VOL = 5.0   # Q5 Hot Start 2x master mix -> 1x in 10 uL
PRIMER_VOL = 4.0       # pre-diluted primer pair (1.25 uM each -> 0.5 uM each final)
TEMPLATE_VOL = 1.0     # colony template, as in the paper's OT-2 workflow
REACTION_VOL = MASTER_MIX_VOL + PRIMER_VOL + TEMPLATE_VOL   # 10 uL, as in the paper
MIX_VOL = 5.0          # mixing volume after each addition (half the final reaction)

# ------------------------------------------------- thermocycling (off-deck)
# Q5 Hot Start manufacturer's programme, adjusted for colony PCR: the initial
# 98 C denaturation is lengthened from 30 s to 3 min to lyse the E. coli cells
# (a choice the paper leaves to the user, "according to the manufacturer's
# protocol with adjustments"). Annealing temperature and extension time are
# primer-/amplicon-specific (paper) -> set here for a ~1.5 kb Golden Gate
# transcription-unit amplicon at 20-30 s/kb; edit for your primers/amplicon.
INITIAL_DENATURATION = '98 C for 3 min'
CYCLES = 30
DENATURATION = '98 C for 10 s'
ANNEALING = '60 C for 20 s'     # use NEB Tm calculator value for your primer pair
EXTENSION = '72 C for 45 s'     # ~30 s/kb for a ~1.5 kb amplicon
FINAL_EXTENSION = '72 C for 2 min'
HOLD = '4 C hold'


def run(protocol: protocol_api.ProtocolContext):

    # ------------------------------------------------------------- labware
    colony_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 1,
                                         label='colony_plate')
    pcr_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 2,
                                      label='pcr_plate')
    master_mix_reservoir = protocol.load_labware('nest_1_reservoir_195ml', 3,
                                                 label='master_mix_reservoir')
    primer_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 4,
                                         label='primer_plate')

    tips20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tips300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)

    # ------------------------------------------------------------ pipettes
    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tips20])
    # The p300 is loaded as mounted but is not used: every transfer in this
    # protocol is 1-5 uL, which is below its 20 uL minimum.
    p300 = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tips300])

    master_mix = master_mix_reservoir.wells()[0]
    n_reactions = 96
    reaction_wells = pcr_plate.wells()[:n_reactions]

    # Tips are unlimited: refill the 20 uL rack whenever it runs out.
    tips_used = [0]

    def pick_up_20():
        if tips_used[0] > 0 and tips_used[0] % 96 == 0:
            protocol.comment('20 uL tip rack exhausted - replace with a fresh rack '
                             '(tips are unlimited); resetting tip tracking.')
            p20.reset_tipracks()
        p20.pick_up_tip()
        tips_used[0] += 1

    # ----------------------------------------------------------- preamble
    protocol.comment(
        'Before this run (manual, as in the paper): pick 96 transformant colonies '
        'into the colony_plate wells A1-H12 (one colony per well, resuspended in '
        'sterile water) to make the colony template plate. Each well of '
        'primer_plate holds the primer pair for the colony in the same well, '
        'pre-diluted in water to 1.25 uM each (assumption: no water on the deck).')
    protocol.comment(
        'Keep the Q5 Hot Start 2x master mix and the pcr_plate cold where possible; '
        'Q5 Hot Start is aptamer-inhibited, so room-temperature set-up on the deck '
        'is tolerated (reason for choosing a hot-start mix).')

    # ------------------------------------------ step 1: 2x master mix, 5 uL
    # One tip for all wells: the mix is dispensed into empty wells from a
    # height above the liquid (no contact), as in the paper's "dispense the
    # master mix into each reaction tube" step. distribute() aspirates a few
    # aliquots per tip with a disposal volume to keep 5 uL dispenses accurate.
    protocol.comment('Step 1: dispense %.0f uL Q5 Hot Start 2x master mix into 96 wells of pcr_plate.'
                     % MASTER_MIX_VOL)
    pick_up_20()
    p20.distribute(MASTER_MIX_VOL,
                   master_mix,
                   [well.top(-2) for well in reaction_wells],
                   new_tip='never',
                   disposal_volume=2,
                   blow_out=True,
                   blowout_location='source well')
    p20.drop_tip()

    # ------------------------------------ step 2: colony-specific primers, 4 uL
    # Fresh tip for every primer pair (cross-contamination between colony
    # reactions would create false positives). Mixed into the master mix.
    protocol.comment('Step 2: add %.0f uL of each colony-specific primer pair (primer_plate -> same well of pcr_plate), fresh tip each.'
                     % PRIMER_VOL)
    for i in range(n_reactions):
        pick_up_20()
        p20.aspirate(PRIMER_VOL, primer_plate.wells()[i])
        p20.dispense(PRIMER_VOL, reaction_wells[i])
        p20.mix(2, MIX_VOL, reaction_wells[i])
        p20.blow_out(reaction_wells[i].top())
        p20.drop_tip()

    # ---------------------------------------- step 3: colony template, 1 uL
    # Last addition, as in the paper (template added after the master mix).
    protocol.comment('Step 3: add %.0f uL colony template (colony_plate -> same well of pcr_plate), fresh tip each, mix.'
                     % TEMPLATE_VOL)
    for i in range(n_reactions):
        pick_up_20()
        p20.aspirate(TEMPLATE_VOL, colony_plate.wells()[i])
        p20.dispense(TEMPLATE_VOL, reaction_wells[i])
        p20.mix(3, MIX_VOL, reaction_wells[i])
        p20.blow_out(reaction_wells[i].top())
        p20.drop_tip()

    # ------------------------------------------------- off-deck steps
    protocol.comment(
        'Manual: seal pcr_plate (%d x %.0f uL reactions) with an adhesive PCR seal and '
        'spin briefly to collect the liquid (as the paper notes, sealing is a user step).'
        % (n_reactions, REACTION_VOL))
    protocol.comment(
        'Manual: transfer pcr_plate to a benchtop thermocycler (no thermocycler module '
        'on this deck; the paper uses the OT-2 module or benchtop cyclers). Q5 Hot Start '
        'colony PCR programme: %s (cell lysis + activation); %d cycles of [%s, %s, %s]; '
        '%s; %s. Adjust annealing/extension to your primers and amplicon size.'
        % (INITIAL_DENATURATION, CYCLES, DENATURATION, ANNEALING, EXTENSION,
           FINAL_EXTENSION, HOLD))
    protocol.comment(
        'Manual: analyse 5 uL of each reaction by agarose gel electrophoresis against '
        'a DNA ladder and score colonies with the expected amplicon size as positive.')
