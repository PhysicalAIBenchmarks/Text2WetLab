from opentrons import protocol_api

metadata = {
    'protocolName': 'Colony PCR screening with Q5 Hot Start master mix',
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

    def pick_up(pip):
        try:
            pip.pick_up_tip()
        except Exception:
            pip.reset_tipracks()
            pip.pick_up_tip()

    dests = pcr_plate.wells()  # A1..H12 column-wise
    mm = mm_res.wells_by_name()['A1']

    # Step 1: 18 uL master mix to every well (one tip, same source reagent)
    pick_up(p20)
    for d in dests:
        p20.aspirate(18, mm)
        p20.dispense(18, d)
        p20.blow_out(d.top())
    p20.drop_tip()

    # Step 2: 1 uL colony template, mix 3x after dispensing
    for s, d in zip(colony_plate.wells(), dests):
        pick_up(p20)
        p20.aspirate(1, s)
        p20.dispense(1, d)
        p20.mix(3, 10, d)
        p20.blow_out(d.top())
        p20.drop_tip()

    # Step 3: 1 uL primer pairs
    for s, d in zip(primer_plate.wells(), dests):
        pick_up(p20)
        p20.aspirate(1, s)
        p20.dispense(1, d)
        p20.blow_out(d.top())
        p20.drop_tip()

    protocol.comment('Seal pcr_plate, thermocycle: 98°C 30 s; [98°C 10 s, 60°C 30 s, '
                     '72°C 30 s] x 30; 72°C 2 min; hold 4°C')
