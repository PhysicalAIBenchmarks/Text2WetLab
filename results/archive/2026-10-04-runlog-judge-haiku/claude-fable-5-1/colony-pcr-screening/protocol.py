"""
Colony PCR screening of 96 transformant colonies on the Opentrons OT-2.

Adapted from the Slowpoke colony PCR workflow (Golden Gate cloning and colony
PCR on OT-2/Flex, ACS Synth. Biol., doi:10.1021/acssynbio.5c00629).

Paper (OT-2 workflow, Methods 2.5 / Table S5):
  * a PCR master mix (water + colony PCR primers + 2x PCR master mix) is
    prepared, 9 uL of it is dispensed into every reaction, then 1 uL of colony
    template is added -> 10 uL reaction.
  * Reactions are then sealed and thermocycled (Opentrons thermocycler module
    or benchtop thermocycler), followed by gel electrophoresis.

Adaptation to the reagents loaded here (fixed deck):
  * The "master mix" is split into two sources: a 2x Q5 Hot Start master mix
    (one reservoir) and a plate of per-colony primer pairs. No water is loaded,
    so the paper's 9 uL mix portion is built in-well as
        5 uL Q5 Hot Start 2x master mix  (1x final, as NEB requires)
      + 4 uL primer pair (pre-mixed fwd+rev, pre-diluted by the operator so
        that 4 uL in a 10 uL reaction gives 0.5 uM of each primer, i.e.
        1.25 uM each in the primer plate)
  * followed by 1 uL colony template, exactly as in the paper -> 10 uL total.
  * Order of addition follows the paper (mix components first, template last).
    The template is added with a fresh tip per colony and mixed in.
  * No thermocycler module is on this deck, so the plate is sealed and cycled
    on a benchtop thermocycler, an option the paper explicitly supports.
"""

from opentrons import protocol_api

metadata = {
    'protocolName': 'Slowpoke colony PCR (OT-2) - 96 colonies, Q5 Hot Start 2x',
    'author': 'Adapted from Slowpoke (doi:10.1021/acssynbio.5c00629)',
    'description': 'Set up 96 x 10 uL colony PCR reactions: 5 uL Q5 2x mix, '
                   '4 uL primer pair, 1 uL colony template.',
    'apiLevel': '2.13',
}

# ---------------------------------------------------------------------------
# Reaction recipe (uL). Total = 10 uL per reaction as in the paper's OT-2 run.
# ---------------------------------------------------------------------------
Q5_MIX_VOL = 5.0        # 2x Q5 Hot Start master mix -> 1x in 10 uL
PRIMER_VOL = 4.0        # pre-mixed, pre-diluted primer pair (see docstring)
TEMPLATE_VOL = 1.0      # colony template, as in the paper (1 uL on OT-2)
REACTION_VOL = Q5_MIX_VOL + PRIMER_VOL + TEMPLATE_VOL   # 10 uL
N_REACTIONS = 96


def run(protocol: protocol_api.ProtocolContext):

    # ------------------------------------------------------------------ deck
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

    p20 = protocol.load_instrument('p20_single_gen2', 'left',
                                   tip_racks=[tips20])
    p300 = protocol.load_instrument('p300_single_gen2', 'right',
                                    tip_racks=[tips300])
    # Every per-reaction volume here is <= 20 uL, so the P20 does all the
    # liquid handling; the P300 is loaded (fixed set-up) but not needed.

    q5_mix = master_mix_reservoir['A1']
    colony_wells = colony_plate.wells()[:N_REACTIONS]      # A1..H12, column-wise
    primer_wells = primer_plate.wells()[:N_REACTIONS]
    pcr_wells = pcr_plate.wells()[:N_REACTIONS]

    protocol.comment(
        'Slowpoke colony PCR, OT-2 adaptation: 96 reactions x %.0f uL '
        '(%.0f uL Q5 Hot Start 2x + %.0f uL primer pair + %.0f uL colony template). '
        'Colony i in colony_plate is screened with primer pair i in primer_plate '
        'and ends up in the same well position of pcr_plate.'
        % (REACTION_VOL, Q5_MIX_VOL, PRIMER_VOL, TEMPLATE_VOL))
    protocol.comment(
        'Assumption: primer pairs are pre-mixed fwd+rev and pre-diluted so that '
        '4 uL per 10 uL reaction gives 0.5 uM of each primer (NEB Q5 recommendation).')

    # ------------------------------------------------- 1) Q5 2x master mix
    # Paper: PCR mix is dispensed into every reaction first. The destination
    # plate is empty, so one tip can serve all 96 wells (dispensing into clean
    # wells, no carry-over). Q5 mix is viscous: slow down aspiration slightly
    # and keep a 2 uL disposal volume so each dispense is accurate; the P20
    # fills with up to 3 x 5 uL + 2 uL per trip and blows the excess to trash.
    p20.reset_tipracks()
    p20.flow_rate.aspirate = 5       # uL/s (default 7.56) - viscous 2x mix
    p20.distribute(
        Q5_MIX_VOL, q5_mix, pcr_wells,
        new_tip='once',
        disposal_volume=2,
    )
    p20.flow_rate.aspirate = 7.56    # restore default

    # --------------------------------------------------- 2) primer pairs
    # Each colony gets its own primer pair, so a fresh tip for every well.
    # Dispensing into 5 uL of mix: mix briefly so the primers are not left
    # as a droplet on the wall.
    p20.reset_tipracks()
    p20.transfer(
        PRIMER_VOL, primer_wells, pcr_wells,
        new_tip='always',
        mix_after=(2, 5),
    )

    # ------------------------------------------------ 3) colony template
    # Paper: 1 uL of colony template is added last. Fresh tip for every
    # colony and mix after addition (3 x 5 uL = half the reaction volume) so
    # the template is fully incorporated into the 10 uL reaction.
    p20.reset_tipracks()
    p20.transfer(
        TEMPLATE_VOL, colony_wells, pcr_wells,
        new_tip='always',
        mix_after=(3, 5),
    )

    # ---------------------------------------------------- 4) off-deck steps
    protocol.comment(
        'MANUAL: Seal pcr_plate (PCR film/foil), briefly spin down (e.g. 1 min, '
        '1000 x g) to collect the 10 uL reactions, and transfer the plate to a '
        'benchtop thermocycler (no thermocycler module is on this deck; the paper '
        'uses either the OT-2 thermocycler module or benchtop cyclers).')
    protocol.comment(
        'MANUAL: Thermocycle (Q5 Hot Start 2x, per NEB with the paper\'s '
        'polymerase-specific adjustments): 98 C 3 min initial denaturation '
        '(extended from 30 s to help lyse E. coli colonies); 30 cycles of '
        '98 C 10 s, 60 C 20 s, 72 C 60 s (20-30 s/kb, set for a ~2 kb screening '
        'amplicon - adjust extension time to your amplicon and the annealing '
        'temperature to the NEB Tm calculator value for your primer pair); '
        '72 C 2 min final extension; hold at 4 C.')
    protocol.comment(
        'MANUAL: Analyse the 96 PCR products by agarose gel electrophoresis (as in '
        'the paper, e.g. 1% agarose; load 5 uL of each reaction with loading dye) '
        'and score colonies with the expected amplicon size as positive. Keep the '
        'remaining colony template/culture of positives for plasmid preparation.')

    # Belt and braces: never finish the run holding a tip.
    for pip in (p20, p300):
        if pip.has_tip:
            pip.drop_tip()
