"""Colony PCR screening with Q5 Hot Start 2x master mix (OT-2).

Based on Slowpoke (ACS Synth. Biol., doi:10.1021/acssynbio.5c00629):
18 uL Q5 Hot Start master mix per well, then 1 uL colony template and
1 uL primer pair per well (20 uL reactions), followed by thermocycling.
"""

from opentrons import protocol_api

metadata = {
    'protocolName': 'Colony PCR screening with Q5 Hot Start master mix',
    'author': 'Generated protocol',
    'description': 'Dispense 18 uL Q5 master mix, add 1 uL colony template '
                   'and 1 uL primer mix per well, then thermocycle.',
    'apiLevel': '2.15',
}


def run(protocol: protocol_api.ProtocolContext):
    # ---- Labware -----------------------------------------------------------
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

    # ---- Pipettes ----------------------------------------------------------
    p20 = protocol.load_instrument(
        'p20_single_gen2', 'left', tip_racks=[tips20])
    p300 = protocol.load_instrument(
        'p300_single_gen2', 'right', tip_racks=[tips300])

    # Tip bookkeeping: tips are unlimited, refill the 20 uL rack when empty.
    tip_state = {'p20_used': 0}

    def pick_up_p20():
        if tip_state['p20_used'] >= 96:
            p20.reset_tipracks()
            tip_state['p20_used'] = 0
        p20.pick_up_tip()
        tip_state['p20_used'] += 1

    wells = pcr_plate.wells()[:96]  # A1..H12 (column-major order)
    master_mix = master_mix_reservoir['A1']

    # ---- Step 1: 18 uL Q5 Hot Start master mix 2x into every PCR well -------
    protocol.comment('Step 1: 18 uL Q5 Hot Start master mix (2x) to pcr_plate A1:H12')
    pick_up_p20()
    for dest in wells:
        p20.aspirate(18, master_mix)
        p20.dispense(18, dest.bottom(1))
        p20.blow_out(dest.top(-2))
    p20.drop_tip()

    # ---- Step 2: 1 uL colony template, mix 3x after dispensing --------------
    protocol.comment('Step 2: 1 uL colony template from colony_plate to pcr_plate, '
                     'mix 3x after dispensing (new tip per well)')
    for src, dest in zip(colony_plate.wells()[:96], wells):
        pick_up_p20()
        p20.aspirate(1, src)
        p20.dispense(1, dest.bottom(1))
        p20.mix(3, 10, dest.bottom(1))
        p20.blow_out(dest.top(-2))
        p20.drop_tip()

    # ---- Step 3: 1 uL primer pair per well -----------------------------------
    protocol.comment('Step 3: 1 uL primer pair from primer_plate to pcr_plate '
                     '(new tip per well)')
    for src, dest in zip(primer_plate.wells()[:96], wells):
        pick_up_p20()
        p20.aspirate(1, src)
        p20.dispense(1, dest.bottom(1))
        p20.blow_out(dest.top(-2))
        p20.drop_tip()

    # ---- Step 4: off-deck thermocycling (not simulated) ---------------------
    protocol.comment('Step 4 (manual): Seal pcr_plate and thermocycle: '
                     '98C 30 s; [98C 10 s, 60C 30 s, 72C 30 s] x 30 cycles; '
                     '72C 2 min; hold 4C.')
