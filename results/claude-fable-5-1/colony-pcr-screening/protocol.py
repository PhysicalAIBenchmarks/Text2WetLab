"""Colony PCR screening with Q5 Hot Start 2x master mix (OT-2).

Based on the Slowpoke colony PCR workflow (Golden Gate cloning and colony PCR
on OT-2/Flex, ACS Synth. Biol., doi:10.1021/acssynbio.5c00629).

Per well of the 96-well PCR plate (20 uL reaction):
  18 uL Q5 Hot Start 2x master mix
   1 uL colony template (mixed 3x after dispensing)
   1 uL primer pair
"""

from opentrons import protocol_api

metadata = {
    'protocolName': 'Colony PCR screening with Q5 Hot Start master mix',
    'author': 'Slowpoke-derived OT-2 protocol',
    'description': ('Distribute 18 uL Q5 Hot Start 2x master mix, then add '
                    '1 uL colony template and 1 uL primer mix to each well '
                    'of a 96-well PCR plate for colony PCR screening.'),
    'apiLevel': '2.15',
}

# Quantities (uL)
MASTER_MIX_VOL = 18.0
TEMPLATE_VOL = 1.0
PRIMER_VOL = 1.0
MIX_REPS = 3
MIX_VOL = 10.0  # mix volume after template addition (within p20 range)


def run(protocol: protocol_api.ProtocolContext):
    # ---------------------------------------------------------------- labware
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

    # --------------------------------------------------------------- pipettes
    p20 = protocol.load_instrument(
        'p20_single_gen2', 'left', tip_racks=[tips20])
    p300 = protocol.load_instrument(
        'p300_single_gen2', 'right', tip_racks=[tips300])

    # Tips are unlimited: reset racks whenever one is exhausted.
    def pick_up(pipette):
        try:
            pipette.pick_up_tip()
        except protocol_api.labware.OutOfTipsError:
            pipette.reset_tipracks()
            pipette.pick_up_tip()

    master_mix = master_mix_reservoir['A1']
    dest_wells = pcr_plate.wells()          # A1..H12, column-major order
    colony_wells = colony_plate.wells()
    primer_wells = primer_plate.wells()

    # ------------------------------------------------- 1. Q5 master mix 18 uL
    # 18 uL is within the p20 range (1-20 uL); the p300 cannot pipette below
    # 20 uL, so the p20 is used. The destination plate is empty, so a single
    # tip is used for the whole distribution (no cross-contamination risk).
    protocol.comment('Step 1: Adding %.0f uL Q5 Hot Start 2x master mix '
                     'to pcr_plate A1:H12.' % MASTER_MIX_VOL)
    pick_up(p20)
    for dest in dest_wells:
        p20.aspirate(MASTER_MIX_VOL, master_mix)
        p20.dispense(MASTER_MIX_VOL, dest.bottom(2))
        p20.blow_out(dest.top(-2))
        p20.touch_tip(dest, v_offset=-2)
    p20.drop_tip()

    # ------------------------------------------- 2. Colony template 1 uL, mix
    protocol.comment('Step 2: Adding %.0f uL colony template from '
                     'colony_plate to pcr_plate (A1 -> A1, ...), mixing %d '
                     'times after dispensing. Fresh tip for each colony.'
                     % (TEMPLATE_VOL, MIX_REPS))
    for src, dest in zip(colony_wells, dest_wells):
        pick_up(p20)
        p20.aspirate(TEMPLATE_VOL, src.bottom(1))
        p20.dispense(TEMPLATE_VOL, dest.bottom(1))
        p20.mix(MIX_REPS, MIX_VOL, dest.bottom(1))
        p20.blow_out(dest.top(-2))
        p20.touch_tip(dest, v_offset=-2)
        p20.drop_tip()

    # ------------------------------------------------- 3. Primer pairs 1 uL
    protocol.comment('Step 3: Adding %.0f uL primer pair from primer_plate '
                     'to pcr_plate (A1 -> A1, ...). Fresh tip for each primer '
                     'pair.' % PRIMER_VOL)
    for src, dest in zip(primer_wells, dest_wells):
        pick_up(p20)
        p20.aspirate(PRIMER_VOL, src.bottom(1))
        p20.dispense(PRIMER_VOL, dest.bottom(1))
        p20.blow_out(dest.top(-2))
        p20.touch_tip(dest, v_offset=-2)
        p20.drop_tip()

    # ------------------------------------------- 4. Off-deck thermocycling
    protocol.comment('Step 4 (manual, off-deck): Seal pcr_plate and run the '
                     'colony PCR in a thermocycler: 98 C 30 s; '
                     '[98 C 10 s, 60 C 30 s, 72 C 30 s] x 30 cycles; '
                     '72 C 2 min; hold at 4 C.')
    protocol.comment('Protocol complete. Each pcr_plate well holds 20 uL '
                     '(18 uL master mix + 1 uL template + 1 uL primers).')
