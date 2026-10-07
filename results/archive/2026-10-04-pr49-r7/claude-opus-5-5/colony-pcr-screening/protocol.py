from opentrons import protocol_api

metadata = {
    'protocolName': 'Slowpoke colony PCR setup (Q5 Hot Start)',
    'author': 'Slowpoke (Tom Ellis Lab), adapted',
    'description': 'Dispense Q5 master mix, colony template and primers into a 96-well PCR plate.',
    'apiLevel': '2.15',
}

MM_VOL = 18
TEMPLATE_VOL = 1
PRIMER_VOL = 1


def run(protocol: protocol_api.ProtocolContext):
    colony_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 1, label='colony_plate')
    pcr_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 2, label='pcr_plate')
    mm_res = protocol.load_labware('nest_1_reservoir_195ml', 3, label='master_mix_reservoir')
    primer_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 4, label='primer_plate')

    tips20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tips300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)
    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tips20])
    protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tips300])

    tip_count = {'n': 0}

    def pick_up():
        if tip_count['n'] >= 96:
            p20.reset_tipracks()
            tip_count['n'] = 0
        p20.pick_up_tip()
        tip_count['n'] += 1

    mm = mm_res.wells_by_name()['A1']
    dests = pcr_plate.wells()

    # 1. Q5 Hot Start 2x master mix, 18 uL per well (one tip, same reagent)
    protocol.comment('Step 1: dispensing 18 uL Q5 Hot Start master mix to each PCR well')
    pick_up()
    for d in dests:
        p20.aspirate(MM_VOL, mm)
        p20.dispense(MM_VOL, d.bottom(2))
        p20.blow_out(d.top())
    p20.drop_tip()

    # 2. Colony template, 1 uL per well, fresh tip each, mix 3x
    protocol.comment('Step 2: adding 1 uL colony template to each PCR well')
    for src, d in zip(colony_plate.wells(), dests):
        pick_up()
        p20.aspirate(TEMPLATE_VOL, src)
        p20.dispense(TEMPLATE_VOL, d)
        p20.mix(3, 10, d)
        p20.blow_out(d.top())
        p20.drop_tip()

    # 3. Primer pairs, 1 uL per well, fresh tip each
    protocol.comment('Step 3: adding 1 uL primer pair to each PCR well')
    for src, d in zip(primer_plate.wells(), dests):
        pick_up()
        p20.aspirate(PRIMER_VOL, src)
        p20.dispense(PRIMER_VOL, d)
        p20.blow_out(d.top())
        p20.drop_tip()

    # 4. Off-deck
    protocol.comment('Seal pcr_plate and thermocycle: 98C 30 s; 30 cycles of '
                     '[98C 10 s, 60C 30 s, 72C 30 s]; 72C 2 min; hold 4C')
