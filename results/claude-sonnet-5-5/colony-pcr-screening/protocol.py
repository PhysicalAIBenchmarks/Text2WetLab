from opentrons import protocol_api

metadata = {'protocolName': 'Colony PCR screening of 96 colonies (Slowpoke OT-2 workflow)',
            'apiLevel': '2.15'}

# Paper (OT-2 colony PCR): 9 uL master mix per reaction + 1 uL colony template
# = 10 uL reaction. Adaptation: the 9 uL "mix" is built in the PCR well from
# 5 uL Q5 2x master mix (1x final in 10 uL) + 4 uL of the colony's primer pair
# (no water is on the deck; ASSUMPTION: primer-pair stock is at 2.5x so 4 uL
# gives ~0.5 uM each primer in 10 uL). Then 1 uL colony template is added.
MM_UL = 5
PRIMER_UL = 4
TEMPLATE_UL = 1


def run(protocol: protocol_api.ProtocolContext):
    colony = protocol.load_labware('corning_96_wellplate_360ul_flat', 1, label='colony_plate')
    pcr = protocol.load_labware('corning_96_wellplate_360ul_flat', 2, label='pcr_plate')
    mm_res = protocol.load_labware('nest_1_reservoir_195ml', 3, label='master_mix_reservoir')
    primers = protocol.load_labware('corning_96_wellplate_360ul_flat', 4, label='primer_plate')
    tips20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tips300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)
    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tips20])
    protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tips300])

    wells = pcr.wells()

    protocol.comment('Keep Q5 master mix, primers and colony template on ice/cold until use.')

    # 1. Master mix (5 uL) into every well; one tip, dispensed into empty wells
    #    without touching liquid, so no cross-contamination.
    p20.pick_up_tip()
    for w in wells:
        p20.aspirate(MM_UL, mm_res['A1'])
        p20.dispense(MM_UL, w.top(-1))
        p20.blow_out(w.top(-1))
    p20.drop_tip()
    p20.reset_tipracks()

    # 2. Colony-specific primer pair (4 uL), fresh tip each
    for i, w in enumerate(wells):
        p20.pick_up_tip()
        p20.aspirate(PRIMER_UL, primers.wells()[i])
        p20.dispense(PRIMER_UL, w)
        p20.drop_tip()
        if i % 90 == 89:
            p20.reset_tipracks()
    p20.reset_tipracks()

    # 3. Colony template (1 uL), fresh tip, mix to combine
    for i, w in enumerate(wells):
        p20.pick_up_tip()
        p20.aspirate(TEMPLATE_UL, colony.wells()[i])
        p20.dispense(TEMPLATE_UL, w)
        p20.mix(3, 8, w)
        p20.drop_tip()
        if i % 90 == 89:
            p20.reset_tipracks()
    p20.reset_tipracks()

    protocol.comment('Seal the PCR plate with an adhesive/heat seal, briefly spin down (10 uL reactions).')
    protocol.comment('Off-deck thermocycling (Q5 Hot Start; times/temps are choices where paper is open): '
                     '98 C 2 min initial denaturation/colony lysis; 30 cycles of 98 C 10 s, '
                     '~55-65 C 30 s (set by primer Tm), 72 C 30 s/kb (adjust to amplicon size); '
                     'final extension 72 C 2 min; hold 4 C.')
    protocol.comment('Analyse products by agarose gel electrophoresis to identify correct assemblies.')
