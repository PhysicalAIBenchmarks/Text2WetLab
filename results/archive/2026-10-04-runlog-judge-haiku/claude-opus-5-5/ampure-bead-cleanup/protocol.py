from opentrons import protocol_api

metadata = {
    'protocolName': 'AMPure XP 0.8x bead cleanup of PCR products',
    'description': '50 uL PCR + 40 uL beads, 2x 80% EtOH wash, elute in 50 uL water, recover 45 uL.',
}
requirements = {'robotType': 'OT-2', 'apiLevel': '2.15'}


def run(protocol: protocol_api.ProtocolContext):
    sample_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 1, label='sample_plate')
    beads_res = protocol.load_labware('nest_1_reservoir_195ml', 2, label='beads_reservoir')
    ethanol_res = protocol.load_labware('nest_1_reservoir_195ml', 3, label='ethanol_reservoir')
    water_res = protocol.load_labware('nest_1_reservoir_195ml', 4, label='water_reservoir')
    waste_res = protocol.load_labware('nest_1_reservoir_195ml', 5, label='waste')
    elution_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 6, label='elution_plate')

    tips20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tips300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)
    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tips20])
    p300 = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tips300])

    tips_used = {id(p20): 0, id(p300): 0}

    def pick_up(pip):
        if tips_used[id(pip)] >= 96:
            pip.reset_tipracks()
            tips_used[id(pip)] = 0
        pip.pick_up_tip()
        tips_used[id(pip)] += 1

    def pip_for(volume):
        return p20 if volume <= 20 else p300

    def move(volume, src, dest, mix_reps=0, mix_vol=None):
        """Move `volume` from src to dest with a fresh tip, in chunks if needed."""
        pip = pip_for(volume)
        pick_up(pip)
        remaining = volume
        while remaining > 0:
            chunk = min(remaining, pip.max_volume)
            pip.aspirate(chunk, src)
            pip.dispense(chunk, dest)
            remaining -= chunk
        if mix_reps:
            pip.mix(mix_reps, mix_vol, dest)
        pip.drop_tip()

    wells = sample_plate.wells()  # A1..H12
    beads = beads_res.wells()[0]
    ethanol = ethanol_res.wells()[0]
    water = water_res.wells()[0]
    waste = waste_res.wells()[0]

    # 1. Add 40 uL beads (0.8x) and mix
    for w in wells:
        move(40, beads, w, mix_reps=10, mix_vol=40)

    # 2-3.
    protocol.comment('Incubate sample_plate 5 min at room temperature (beads bind DNA)')
    protocol.comment('Engage magnetic module; wait 5 min until solution clears')

    # 4. Remove supernatant (50 + 40 = 90 uL)
    for w in wells:
        move(90, w, waste)

    # 5-8. Two ethanol washes
    for _ in range(2):
        for w in wells:
            move(200, ethanol, w)
        for w in wells:
            move(200, w, waste)

    # 9-10.
    protocol.comment('Air dry beads 5 min at room temperature (magnet engaged); beads should appear matte not shiny')
    protocol.comment('Disengage magnetic module')

    # 11. Elute in 50 uL water and mix
    for w in wells:
        move(50, water, w, mix_reps=10, mix_vol=40)

    # 12.
    protocol.comment('Incubate sample_plate 2 min at room temperature; then re-engage magnetic module 5 min')

    # 13. Transfer 45 uL eluate to elution plate
    for src, dest in zip(wells, elution_plate.wells()):
        move(45, src, dest)
