from opentrons import protocol_api

metadata = {
    'protocolName': 'Colony PCR screening on the OT-2 (Slowpoke)',
    'author': 'Adapted from Slowpoke (ACS Synth. Biol., doi:10.1021/acssynbio.5c00629, CC BY)',
    'description': 'Set up 96 colony PCR reactions: distribute Q5 Hot Start 2x master mix, '
                   'add a per-colony primer pair, then add colony template.',
    'apiLevel': '2.15',
}

# ---------------------------------------------------------------------------
# Reaction setup, adapted from the paper (Methods 2.5, "Automated Colony PCR").
#
# The paper's OT-2 workflow first prepares a single master mix containing water,
# colony PCR primers and 2x PCR master mix, dispenses 9 uL of it into each tube,
# then adds 1 uL of colony template => 10 uL total reaction.
#
# On this deck the reagents are instead provided separately (a Q5 Hot Start 2x
# master mix in the reservoir, and a SEPARATE primer pair per colony in the
# primer plate), and there is no water reservoir. We therefore build each 10 uL
# reaction directly in the PCR plate as:
#
#     5 uL  Q5 Hot Start 2x master mix   (=> 1x final)
#     4 uL  primer pair (forward + reverse)
#     1 uL  colony template
#
# The 4 uL primer pair takes the place of the paper's "water + primers": with the
# primer pairs pre-diluted to 1.25 uM each, 4 uL in a 10 uL reaction gives the
# 0.5 uM final primer concentration recommended for Q5. If a different primer
# stock is used, re-dilute primer_plate before the run — the pipetting volumes
# below stay the same.
# ---------------------------------------------------------------------------

MM_VOL = 5.0        # uL Q5 Hot Start 2x master mix per well
PRIMER_VOL = 4.0    # uL primer pair per well
TEMPLATE_VOL = 1.0  # uL colony template per well


def run(protocol: protocol_api.ProtocolContext):
    # --- Labware (labels are fixed by the operator's deck layout) -------------
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

    # --- Pipettes --------------------------------------------------------------
    # All volumes here are <= 5 uL, within the p20's 1-20 uL range, so the p20
    # does all the work. The p300 is loaded as specified but stays unused.
    p20 = protocol.load_instrument(
        'p20_single_gen2', 'left', tip_racks=[tips20])
    p300 = protocol.load_instrument(
        'p300_single_gen2', 'right', tip_racks=[tips300])

    mm_source = master_mix_reservoir.wells()[0]
    pcr_wells = pcr_plate.wells()        # 96 wells, A1 -> H12
    colony_wells = colony_plate.wells()
    primer_wells = primer_plate.wells()

    # --- 1. Distribute Q5 Hot Start 2x master mix (5 uL / well) ----------------
    # 96 wells x 5 uL = 480 uL, well within the reservoir's supply.
    for well in pcr_wells:
        p20.pick_up_tip()
        p20.aspirate(MM_VOL, mm_source)
        p20.dispense(MM_VOL, well)
        p20.drop_tip()

    # Tip rack (96 tips) is exhausted -> "refill" it per the unlimited-tips setup.
    p20.reset_tipracks()

    # --- 2. Add each colony's own primer pair (4 uL / well) ---------------------
    # Positional 1:1 mapping: colony_plate A1 uses primer_plate A1, and so on.
    for src, dst in zip(primer_wells, pcr_wells):
        p20.pick_up_tip()
        p20.aspirate(PRIMER_VOL, src)
        p20.dispense(PRIMER_VOL, dst)
        p20.drop_tip()

    p20.reset_tipracks()

    # --- 3. Add colony template (1 uL / well) -----------------------------------
    # Source well -> destination well is positional 1:1 (colony_plate A1 -> pcr_plate A1).
    # Each source is mixed briefly first so any settled cells are resuspended.
    for src, dst in zip(colony_wells, pcr_wells):
        p20.pick_up_tip()
        p20.mix(3, 5.0, src)
        p20.aspirate(TEMPLATE_VOL, src)
        p20.dispense(TEMPLATE_VOL, dst)
        p20.drop_tip()

    # --- Off-deck steps the robot cannot perform --------------------------------
    protocol.comment(
        'All 96 reactions are set up (10 uL each). The robot is finished; '
        'the remaining steps are manual:'
    )
    protocol.comment(
        '1. Seal the PCR plate with an adhesive/heat-seal film.'
    )
    protocol.comment(
        '2. Thermocycle off-deck using the NEB Q5 Hot Start protocol '
        '(adjust annealing temp and extension time to primer Tm and amplicon '
        'size):'
    )
    protocol.comment('   - Initial denaturation: 98 C for 30 s')
    protocol.comment('   - 30 cycles: 98 C for 10 s; 60 C for 20 s (anneal); '
                     '72 C for 30 s (extension, ~20-30 s/kb)')
    protocol.comment('   - Final extension: 72 C for 2 min')
    protocol.comment('   - Hold: 4 C')
    protocol.comment('3. Run products on a gel to score positive colonies.')