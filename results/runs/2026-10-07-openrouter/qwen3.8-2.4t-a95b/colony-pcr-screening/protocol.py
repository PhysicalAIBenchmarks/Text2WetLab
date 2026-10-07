"""Colony PCR screening with Q5 Hot Start master mix (Slowpoke workflow).

OT-2 protocol: add 18 uL Q5 Hot Start master mix to each well of a PCR
plate, then 1 uL colony template (mixed), then 1 uL primer mix per well.
Based on Slowpoke: Golden Gate cloning and colony PCR on OT-2/Flex
(ACS Synth. Biol., doi:10.1021/acssynbio.5c00629).
"""

from opentrons import protocol_api

metadata = {
    'protocolName': 'Colony PCR screening with Q5 Hot Start master mix',
    'author': 'Slowpoke workflow',
    'description': 'Screen transformant colonies by PCR on the OT-2.',
    'apiLevel': '2.13',
}


def run(protocol: protocol_api.ProtocolContext):
    # ------------------------------------------------------------------
    # Labware (fixed deck layout)
    # ------------------------------------------------------------------
    colony_plate = protocol.load_labware(
        'corning_96_wellplate_360ul_flat', 1, label='colony_plate')
    pcr_plate = protocol.load_labware(
        'corning_96_wellplate_360ul_flat', 2, label='pcr_plate')
    master_mix_reservoir = protocol.load_labware(
        'nest_1_reservoir_195ml', 3, label='master_mix_reservoir')
    primer_plate = protocol.load_labware(
        'corning_96_wellplate_360ul_flat', 4, label='primer_plate')

    tips_20 = protocol.load_labware(
        'opentrons_96_tiprack_20ul', 10)
    tips_300 = protocol.load_labware(
        'opentrons_96_tiprack_300ul', 11)

    p20 = protocol.load_instrument(
        'p20_single_gen2', 'left', tip_racks=[tips_20])
    p300 = protocol.load_instrument(
        'p300_single_gen2', 'right', tip_racks=[tips_300])

    # All 96 wells, A1..H12, in order
    wells = [f'{row}{col}' for row in 'ABCDEFGH' for col in range(1, 13)]

    # ------------------------------------------------------------------
    # Step 1: 18 uL Q5 master mix 2x from reservoir A1 -> pcr_plate A1:H12
    # (18 uL is within the p20 range: 1-20 uL)
    # ------------------------------------------------------------------
    protocol.comment('Step 1: Dispensing 18 uL Q5 Hot Start master mix '
                     'into pcr_plate wells A1:H12.')
    p20.reset_tipracks()
    mm_source = master_mix_reservoir['A1']
    for name in wells:
        p20.pick_up_tip()
        p20.aspirate(18, mm_source)
        p20.dispense(18, pcr_plate[name])
        p20.drop_tip()

    # ------------------------------------------------------------------
    # Step 2: 1 uL colony template colony_plate A1:H12 -> pcr_plate A1:H12,
    # mix 3x after dispensing
    # ------------------------------------------------------------------
    protocol.comment('Step 2: Adding 1 uL colony template to pcr_plate '
                     'wells A1:H12, mixing 3 times after dispensing.')
    p20.reset_tipracks()
    for name in wells:
        p20.pick_up_tip()
        p20.aspirate(1, colony_plate[name])
        p20.dispense(1, pcr_plate[name])
        # mix 3 times (well holds 19 uL at this point)
        p20.mix(3, 10, pcr_plate[name])
        p20.drop_tip()

    # ------------------------------------------------------------------
    # Step 3: 1 uL primer mix primer_plate A1:H12 -> pcr_plate A1:H12
    # ------------------------------------------------------------------
    protocol.comment('Step 3: Adding 1 uL primer mix to pcr_plate '
                     'wells A1:H12.')
    p20.reset_tipracks()
    for name in wells:
        p20.pick_up_tip()
        p20.aspirate(1, primer_plate[name])
        p20.dispense(1, pcr_plate[name])
        p20.drop_tip()

    # ------------------------------------------------------------------
    # Step 4: seal and thermocycle (manual, not simulated)
    # ------------------------------------------------------------------
    protocol.comment('Step 4: Seal pcr_plate and thermocycle: '
                     '98C for 30 s; 30 cycles of [98C 10 s, 60C 30 s, '
                     '72C 30 s]; 72C for 2 min; hold at 4C.')
