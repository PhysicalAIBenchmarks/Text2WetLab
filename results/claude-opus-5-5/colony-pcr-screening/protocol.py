from opentrons import protocol_api

metadata = {
    'protocolName': 'Colony PCR screening with Q5 Hot Start master mix',
    'description': 'Slowpoke colony PCR setup: 18 uL Q5 master mix + 1 uL colony '
                   'template + 1 uL primer mix per well of a 96-well PCR plate.',
    'apiLevel': '2.15',
}


def run(protocol: protocol_api.ProtocolContext):
    colony_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 1, label='colony_plate')
    pcr_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 2, label='pcr_plate')
    mm_res = protocol.load_labware('nest_1_reservoir_195ml', 3, label='master_mix_reservoir')
    primer_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 4, label='primer_plate')

    tips20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tips300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)
    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tips20])
    p300 = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tips300])

    tips_used = {p20: 0, p300: 0}

    def pick_up(pip):
        if tips_used[pip] >= 96:
            pip.reset_tipracks()
            tips_used[pip] = 0
        pip.pick_up_tip()
        tips_used[pip] += 1

    dest = pcr_plate.wells()  # A1..H12, column order

    # Step 1: 18 uL Q5 master mix 2x into every PCR well (one tip, same reagent,
    # dispensed into empty wells so no cross-contamination).
    pick_up(p20)
    for well in dest:
        p20.aspirate(18, mm_res['A1'])
        p20.dispense(18, well.bottom(2))
        p20.blow_out(well.top(-2))
    p20.drop_tip()

    # Step 2: 1 uL colony template, fresh tip per well, mix 3x after dispensing.
    for src, well in zip(colony_plate.wells(), dest):
        pick_up(p20)
        p20.aspirate(1, src)
        p20.dispense(1, well)
        p20.mix(3, 10, well)
        p20.blow_out(well.top(-2))
        p20.drop_tip()

    # Step 3: 1 uL primer pair, fresh tip per well.
    for src, well in zip(primer_plate.wells(), dest):
        pick_up(p20)
        p20.aspirate(1, src)
        p20.dispense(1, well)
        p20.blow_out(well.top(-2))
        p20.drop_tip()

    # Step 4: off-deck thermocycling.
    protocol.comment('Seal pcr_plate and thermocycle: 98°C 30 s; '
                     '[98°C 10 s, 60°C 30 s, 72°C 30 s] x 30; 72°C 2 min; hold 4°C')
