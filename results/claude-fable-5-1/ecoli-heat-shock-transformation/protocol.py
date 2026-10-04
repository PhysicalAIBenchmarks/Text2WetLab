"""E. coli heat shock transformation with SOC recovery (Opentrons OT-2)."""

metadata = {
    'protocolName': 'E. coli heat shock transformation with SOC recovery',
    'author': 'OT-2 protocol',
    'description': ('Add 2 uL plasmid DNA to competent cells, heat shock at 42 C '
                    'for 45 s (off-deck), then add 250 uL SOC and recover.'),
    'apiLevel': '2.15',
}


def run(protocol):
    # ---- Labware -----------------------------------------------------------
    plasmid_plate = protocol.load_labware(
        'corning_96_wellplate_360ul_flat', 1, label='plasmid_plate')
    tubes = protocol.load_labware(
        'opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', 2,
        label='tubes_1_5ml_1')
    soc_reservoir = protocol.load_labware(
        'nest_1_reservoir_195ml', 3, label='soc_reservoir')

    tips_20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tips_300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)

    # ---- Pipettes ----------------------------------------------------------
    p20 = protocol.load_instrument(
        'p20_single_gen2', 'left', tip_racks=[tips_20])
    p300 = protocol.load_instrument(
        'p300_single_gen2', 'right', tip_racks=[tips_300])

    # ---- Wells -------------------------------------------------------------
    plasmid = plasmid_plate['A1']
    cells = tubes['A1']          # competent cells, 50 uL
    soc = soc_reservoir['A1']

    # ---- Step 1: 2 uL plasmid DNA -> competent cells ----------------------
    protocol.comment('Step 1: Transfer 2 uL plasmid DNA to competent cells.')
    p20.pick_up_tip()
    p20.aspirate(2, plasmid)
    p20.dispense(2, cells)
    p20.mix(3, 10, cells)
    p20.blow_out(cells.top())
    p20.drop_tip()

    # ---- Step 2: heat shock (off-deck, not simulated) ---------------------
    protocol.pause('Step 2: Heat shock cells_rack at 42 C for 45 s, then '
                   'transfer immediately to ice for 2 min. Return rack to '
                   'slot 2 and resume.')
    protocol.comment('Heat shock cells_rack 42 C 45 s, then transfer '
                     'immediately to ice 2 min')

    # ---- Step 3: 250 uL SOC -> cells --------------------------------------
    protocol.comment('Step 3: Transfer 250 uL SOC medium to transformed cells.')
    p300.pick_up_tip()
    p300.aspirate(250, soc)
    p300.dispense(250, cells)
    p300.blow_out(cells.top())
    p300.drop_tip()

    # ---- Step 4: outgrowth (off-deck, not simulated) ----------------------
    protocol.comment('Step 4: Incubate cells_rack 37 C 60 min at 250 rpm for '
                     'outgrowth recovery')
