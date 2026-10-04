from opentrons import protocol_api

metadata = {'protocolName': 'AMPure XP 0.8x PCR cleanup', 'apiLevel': '2.15'}


def run(protocol: protocol_api.ProtocolContext):
    sample = protocol.load_labware('corning_96_wellplate_360ul_flat', 1, label='sample_plate')
    beads = protocol.load_labware('nest_1_reservoir_195ml', 2, label='beads_reservoir')
    ethanol = protocol.load_labware('nest_1_reservoir_195ml', 3, label='ethanol_reservoir')
    water = protocol.load_labware('nest_1_reservoir_195ml', 4, label='water_reservoir')
    waste = protocol.load_labware('nest_1_reservoir_195ml', 5, label='waste')
    elution = protocol.load_labware('corning_96_wellplate_360ul_flat', 6, label='elution_plate')
    tr20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tr300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)
    protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tr20])
    p300 = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tr300])

    wells = [w for col in sample.columns() for w in col]
    ewells = [w for col in elution.columns() for w in col]

    def xfer(vol, src, dst, **kw):
        p300.reset_tipracks()
        p300.transfer(vol, src, dst, new_tip='always', **kw)

    xfer(40, beads['A1'], wells, mix_after=(10, 40))
    protocol.comment('Incubate sample_plate 5 min at room temperature (beads bind DNA)')
    protocol.comment('Engage magnetic module; wait 5 min until solution clears')
    xfer(90, wells, waste['A1'])
    xfer(200, ethanol['A1'], wells)
    xfer(200, wells, waste['A1'])
    xfer(200, ethanol['A1'], wells)
    xfer(200, wells, waste['A1'])
    protocol.comment('Air dry beads 5 min at room temperature (magnet engaged); beads should appear matte not shiny')
    protocol.comment('Disengage magnetic module')
    xfer(50, water['A1'], wells, mix_after=(10, 40))
    protocol.comment('Incubate sample_plate 2 min at room temperature; then re-engage magnetic module 5 min')
    xfer(45, wells, ewells)
