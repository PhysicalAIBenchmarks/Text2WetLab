"""
Colony PCR screening of 96 transformants on the OT-2 (Slowpoke workflow,
ACS Synth. Biol., doi:10.1021/acssynbio.5c00629, section 2.5 "Automated Colony PCR").

Paper (OT-2 workflow): 9 uL of PCR master mix (2x polymerase mix + primers +
water) is dispensed into each reaction well, then 1 uL of colony template is
added -> 10 uL reactions, set up per the polymerase manufacturer's protocol,
then thermocycled.

Adaptation to the reagents on this deck (2x Q5 Hot Start master mix in a
reservoir, and a separate primer pair per colony in primer_plate):
  - 5.0 uL Q5 Hot Start 2x master mix  -> 1x final in 10 uL (NEB protocol)
  - 4.0 uL primer pair (well-matched to the colony well), so that
    master mix + primers = the paper's 9 uL "master mix" portion.
    ASSUMPTION: the primer plate holds pre-diluted primer pairs (forward +
    reverse at 1.25 uM each, in water) so 4 uL gives the NEB-recommended
    0.5 uM of each primer in 10 uL; no separate water is needed.
  - 1.0 uL colony template (paper's OT-2 value), added last, then mixed.
All volumes are <= 20 uL, so the p20 single GEN2 is used throughout; the p300
is loaded as part of the fixed deck but is not needed.
"""
from opentrons import protocol_api

metadata = {
    'protocolName': 'Slowpoke colony PCR (OT-2) - Q5 Hot Start, per-colony primers',
    'author': 'Adapted from Slowpoke (ACS Synth. Biol. 2025)',
    'description': '96 x 10 uL colony PCR set-up: 5 uL Q5 2x MM + 4 uL primer pair '
                   '+ 1 uL colony template',
    'apiLevel': '2.15',
}

MM_VOL = 5.0        # uL Q5 Hot Start 2x master mix per reaction
PRIMER_VOL = 4.0    # uL primer pair per reaction
TEMPLATE_VOL = 1.0  # uL colony template per reaction (paper, OT-2)
REACTION_VOL = MM_VOL + PRIMER_VOL + TEMPLATE_VOL  # 10 uL (paper, OT-2)


def run(protocol: protocol_api.ProtocolContext):
    # ---- Deck (fixed) ----
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

    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tips20])
    p300 = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tips300])  # noqa: F841

    tips_used = {'p20': 0}

    def pick_up():
        # Tips are unlimited: reset the rack once all 96 have been used.
        if tips_used['p20'] == 96:
            p20.reset_tipracks()
            tips_used['p20'] = 0
        p20.pick_up_tip()
        tips_used['p20'] += 1

    master_mix = mm_res.wells()[0]
    dest_wells = pcr_plate.wells()          # A1..H1, A2..H2, ... (96 reactions)
    primer_wells = primer_plate.wells()
    colony_wells = colony_plate.wells()

    protocol.comment('Keep the Q5 Hot Start master mix and primers cold; the '
                     'destination PCR plate should be on ice/cold block if possible.')

    # ---- Step 1: Q5 2x master mix, 5 uL per well ----
    # One tip for all wells (dispensing into empty wells, no contamination
    # risk). Multi-dispense 3 wells (15 uL) per aspiration, within p20 capacity.
    protocol.comment('Step 1: dispensing 5 uL Q5 Hot Start 2x master mix to each well.')
    pick_up()
    per_asp = int(p20.max_volume // MM_VOL)  # 4 x 5 uL = 20 uL
    per_asp = min(per_asp, 3)                # keep 5 uL headroom, 15 uL per trip
    for i in range(0, len(dest_wells), per_asp):
        chunk = dest_wells[i:i + per_asp]
        p20.aspirate(MM_VOL * len(chunk), master_mix.bottom(1))
        for w in chunk:
            p20.dispense(MM_VOL, w.bottom(1))
        p20.blow_out(master_mix.top())
    p20.drop_tip()

    # ---- Step 2: primer pair, 4 uL per well (well-to-well, fresh tip) ----
    # Together with step 1 this forms the paper's 9 uL reaction master mix.
    protocol.comment('Step 2: adding 4 uL of the matching primer pair to each well.')
    for src, dst in zip(primer_wells, dest_wells):
        pick_up()
        p20.aspirate(PRIMER_VOL, src.bottom(1))
        p20.dispense(PRIMER_VOL, dst.bottom(1))
        p20.blow_out(dst.top(-2))
        p20.drop_tip()

    # ---- Step 3: colony template, 1 uL per well, then mix (fresh tip) ----
    protocol.comment('Step 3: adding 1 uL colony template to each well and mixing.')
    for src, dst in zip(colony_wells, dest_wells):
        pick_up()
        p20.aspirate(TEMPLATE_VOL, src.bottom(1))
        p20.dispense(TEMPLATE_VOL, dst.bottom(1))
        p20.mix(3, 5, dst.bottom(1))
        p20.blow_out(dst.top(-2))
        p20.drop_tip()

    # ---- Off-deck steps ----
    protocol.comment('MANUAL: seal the PCR plate (adhesive film), spin down briefly. '
                     '(The paper requires the user to seal PCR plates.)')
    protocol.comment('MANUAL: thermocycle off-deck (no thermocycler module on this deck; '
                     'paper used the OT-2 thermocycler module or benchtop cyclers). '
                     'Q5 Hot Start colony PCR program (NEB, adjusted for colony lysis), '
                     'lid 105 C, 10 uL: 98 C 3 min (initial denaturation/cell lysis); '
                     '30 cycles of 98 C 10 s, Ta (Tm+3 C, NEB Tm calculator; typically '
                     '55-72 C) 20 s, 72 C 30 s/kb; final extension 72 C 2 min; hold 4 C. '
                     'Adjust Ta and extension time to the primers and amplicon size, '
                     'as stated in the paper.')
    protocol.comment('MANUAL: analyse the PCR products by agarose gel electrophoresis '
                     'to identify colonies with the expected amplicon size.')
