from opentrons import protocol_api
from opentrons.protocol_api.labware import OutOfTipsError

metadata = {'protocolName': 'Colony PCR screening with Q5 Hot Start master mix',
            'apiLevel': '2.15'}


def run(protocol: protocol_api.ProtocolContext):
    colony = protocol.load_labware('corning_96_wellplate_360ul_flat', 1, label='colony_plate')
    pcr = protocol.load_labware('corning_96_wellplate_360ul_flat', 2, label='pcr_plate')
    mm = protocol.load_labware('nest_1_reservoir_195ml', 3, label='master_mix_reservoir')
    primers = protocol.load_labware('corning_96_wellplate_360ul_flat', 4, label='primer_plate')
    rack20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    rack300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)
    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[rack20])
    p300 = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[rack300])

    def pick(pip):
        try:
            pip.pick_up_tip()
        except OutOfTipsError:
            pip.reset_tipracks()
            pip.pick_up_tip()

    wells = [w for col in pcr.columns() for w in col]
    idx = range(len(wells))

    # 1. Master mix (18 uL, within p20 range); one tip, dispensed into empty wells
    pick(p20)
    for i in idx:
        p20.aspirate(18, mm['A1'])
        p20.dispense(18, wells[i])
    p20.drop_tip()

    # 2. Colony template, fresh tip per well, mix 3x after dispensing
    for w in wells:
        pick(p20)
        p20.aspirate(1, colony[w.well_name])
        p20.dispense(1, w)
        p20.mix(3, 10, w)
        p20.drop_tip()

    # 3. Primer pairs, fresh tip per well
    for w in wells:
        pick(p20)
        p20.aspirate(1, primers[w.well_name])
        p20.dispense(1, w)
        p20.drop_tip()

    protocol.comment('Seal pcr_plate, thermocycle: 98C 30 s; [98C 10 s, 60C 30 s, 72C 30 s] x 30; '
                     '72C 2 min; hold 4C')
