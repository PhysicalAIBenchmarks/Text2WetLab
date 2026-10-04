"""
Colony PCR screening of 96 transformant colonies on the OT-2.

Adapted from the Slowpoke OT-2 colony PCR workflow (ACS Synth. Biol.,
doi:10.1021/acssynbio.5c00629). In the paper, 9 uL of a reaction mix
(water + colony PCR primers + 2x PCR master mix) is dispensed into each
reaction well, followed by 1 uL of colony template, giving a 10 uL reaction.

Adaptation to this deck: the primers are not premixed with the master mix, but
supplied as a separate primer pair per colony (primer_plate, same well as the
colony). The 9 uL reaction mix is therefore assembled in the PCR well:
    5 uL Q5 Hot Start 2x master mix  (-> 1x in 10 uL, per NEB's protocol)
    4 uL primer pair                  (assumed to be supplied at 1.25 uM each
                                       primer in water, i.e. 0.5 uM final each,
                                       the NEB Q5 recommendation; the 4 uL also
                                       replaces the water of the paper's mix)
    1 uL colony template              (added last, as in the paper)
  = 10 uL reaction
"""
from opentrons import protocol_api

metadata = {
    'protocolName': 'Slowpoke colony PCR (OT-2) - 96 colonies, Q5 Hot Start',
    'author': 'Adapted from Slowpoke (ACS Synth. Biol. 2025)',
    'description': 'Sets up 96 x 10 uL colony PCRs: 5 uL Q5 2x master mix + '
                   '4 uL primer pair + 1 uL colony template per well.',
    'apiLevel': '2.15',
}

MASTER_MIX_VOL = 5.0   # uL of 2x Q5 Hot Start master mix -> 1x in 10 uL
PRIMER_VOL = 4.0       # uL primer pair (9 uL "reaction mix" total with MM)
COLONY_VOL = 1.0       # uL colony template (paper, OT-2 workflow)
REACTION_VOL = MASTER_MIX_VOL + PRIMER_VOL + COLONY_VOL  # 10 uL


def run(protocol: protocol_api.ProtocolContext):
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

    # All volumes are 1-20 uL, so only the p20 is used; the p300 is loaded
    # because it is mounted on the robot.
    p20 = protocol.load_instrument('p20_single_gen2', 'left',
                                   tip_racks=[tips20])
    p300 = protocol.load_instrument('p300_single_gen2', 'right',  # noqa: F841
                                    tip_racks=[tips300])

    master_mix = mm_res.wells()[0]
    dests = pcr_plate.wells()          # A1..H12, column-wise
    primers = primer_plate.wells()
    colonies = colony_plate.wells()
    n = 96

    tips_used = {'n': 0}

    def pick_up():
        if tips_used['n'] >= 96:
            p20.reset_tipracks()
            tips_used['n'] = 0
        p20.pick_up_tip()
        tips_used['n'] += 1

    protocol.comment('Colony PCR setup: {} reactions of {} uL '
                     '({} uL Q5 2x MM + {} uL primers + {} uL colony).'.format(
                         n, REACTION_VOL, MASTER_MIX_VOL, PRIMER_VOL,
                         COLONY_VOL))
    protocol.comment('Keep Q5 Hot Start master mix, primers and PCR plate '
                     'cold (on ice) until thermocycling.')

    # Step 1: master mix into every reaction well first (paper: the mix is
    # dispensed first, colony template added after). One tip is reused since
    # the destination wells are still empty (no contamination risk). Multi-
    # dispense 3 x 5 uL per 15 uL aspiration plus a 1 uL disposal volume that
    # is returned to the reservoir, for accurate dispensing of the viscous mix.
    pick_up()
    for i in range(0, n, 3):
        chunk = dests[i:i + 3]
        p20.aspirate(MASTER_MIX_VOL * len(chunk) + 1, master_mix)
        for d in chunk:
            p20.dispense(MASTER_MIX_VOL, d.bottom(1))
        p20.blow_out(master_mix.top())
    p20.drop_tip()

    # Step 2: primer pair specific to each colony (fresh tip each well, so
    # primer pairs never cross-contaminate).
    for src, d in zip(primers[:n], dests):
        pick_up()
        p20.aspirate(PRIMER_VOL, src)
        p20.dispense(PRIMER_VOL, d.bottom(1))
        p20.blow_out(d.bottom(3))
        p20.drop_tip()

    # Step 3: 1 uL colony template last, mixed into the 9 uL reaction mix
    # (fresh tip per colony).
    for src, d in zip(colonies[:n], dests):
        pick_up()
        p20.aspirate(COLONY_VOL, src)
        p20.dispense(COLONY_VOL, d.bottom(1))
        p20.mix(3, 5, d.bottom(1))
        p20.blow_out(d.bottom(3))
        p20.drop_tip()

    # Off-deck steps. The paper runs the plate in the Opentrons thermocycler
    # module (or benchtop thermocyclers); no thermocycler is on this deck, so
    # cycling is done off-deck. The paper follows the polymerase
    # manufacturer's protocol, adjusting annealing temperature and extension
    # time to the primers / amplicon size; the NEB Q5 Hot Start program is
    # used here, with an extended initial denaturation to lyse the cells.
    protocol.comment('Seal the PCR plate (user step), spin down briefly.')
    protocol.comment('Transfer the sealed plate to a thermocycler (off-deck), '
                     'lid 105 C, 10 uL reaction volume.')
    protocol.comment('Thermocycling (Q5 Hot Start): 98 C 3 min (initial '
                     'denaturation / colony lysis); 30 cycles of 98 C 10 s, '
                     'annealing 50-72 C 20 s (Ta = primer Tm + 3 C, NEB Tm '
                     'calculator; adjust to primers), 72 C 30 s/kb extension; '
                     'final extension 72 C 2 min; hold 4 C.')
    protocol.comment('Analyse the PCR products by agarose gel electrophoresis '
                     'to identify colonies with the expected amplicon size.')
