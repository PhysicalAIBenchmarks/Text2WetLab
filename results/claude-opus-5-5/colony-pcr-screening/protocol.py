from opentrons import protocol_api

metadata = {
    'protocolName': 'Colony PCR screening with Q5 Hot Start master mix',
    'description': 'Slowpoke-style colony PCR setup: 18 uL Q5 2x master mix, '
                   '1 uL colony template and 1 uL primer mix per well (20 uL reactions).',
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
    p300 = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tips300])  # noqa: F841 (all volumes <= 20 uL)

    def pick_up(pip):
        try:
            pip.pick_up_tip()
        except protocol_api.labware.OutOfTipsError:
            pip.reset_tipracks()
            pip.pick_up_tip()

    dests = pcr_plate.wells()  # A1..H12, column order
    master_mix = mm_res.wells_by_name()['A1']

    # Step 1: 18 uL Q5 2x master mix into every PCR well (one tip, clean wells)
    protocol.comment('Step 1: dispensing 18 uL Q5 Hot Start 2x master mix to each well')
    pick_up(p20)
    for d in dests:
        p20.aspirate(18, master_mix)
        p20.dispense(18, d.bottom(1))
        p20.blow_out(d.top())
    p20.drop_tip()

    # Step 2: 1 uL colony template, mix 3x, fresh tip per colony
    protocol.comment('Step 2: adding 1 uL colony template to each well and mixing')
    for src, d in zip(colony_plate.wells(), dests):
        pick_up(p20)
        p20.aspirate(1, src)
        p20.dispense(1, d)
        p20.mix(3, 10, d)
        p20.blow_out(d.top())
        p20.drop_tip()

    # Step 3: 1 uL primer pair, fresh tip per well
    protocol.comment('Step 3: adding 1 uL primer pair to each well')
    for src, d in zip(primer_plate.wells(), dests):
        pick_up(p20)
        p20.aspirate(1, src)
        p20.dispense(1, d)
        p20.blow_out(d.top())
        p20.drop_tip()

    # Step 4: off-deck
    protocol.comment('Step 4: Seal pcr_plate and thermocycle: 98C 30 s; '
                     '[98C 10 s, 60C 30 s, 72C 30 s] x 30; 72C 2 min; hold 4C')
