from opentrons import protocol_api

metadata = {
    'protocolName': 'Colony PCR screening of 96 colonies (Slowpoke OT-2 workflow, Q5 adaptation)',
    'apiLevel': '2.15',
}

# Paper (OT-2 colony PCR): 9 uL master mix per reaction + 1 uL colony template = 10 uL reaction.
# Adaptation to the deck: the 9 uL "mix" is built in the plate as
#   5 uL Q5 Hot Start 2x master mix (-> 1x in 10 uL)
# + 4 uL primer-pair working solution from primer_plate (assumed pre-diluted in water so that 4 uL
#   in 10 uL gives the final primer concentration, ~0.5 uM each; no water is on the deck).
# + 1 uL colony template.
MM_VOL = 5
PRIMER_VOL = 4
TEMPLATE_VOL = 1


def run(protocol: protocol_api.ProtocolContext):
    colony_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 1, label='colony_plate')
    pcr_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 2, label='pcr_plate')
    mm_res = protocol.load_labware('nest_1_reservoir_195ml', 3, label='master_mix_reservoir')
    primer_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 4, label='primer_plate')
    tips20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tips300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)

    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tips20])
    protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tips300])
    # All volumes are 1-5 uL, so only the p20 is used; the p300 is loaded as specified.

    dest = pcr_plate.wells()
    p20.flow_rate.aspirate = 7.56
    p20.flow_rate.dispense = 7.56

    # 1) Q5 2x master mix: one tip, dispensed into the empty wells without touching,
    #    refilled every 3 wells (3 x 5 uL = 15 uL, within the 20 uL tip).
    protocol.comment('Step 1: dispense 5 uL Q5 Hot Start 2x master mix into each of 96 PCR wells.')
    p20.pick_up_tip()
    per_asp = 3
    for i in range(0, len(dest), per_asp):
        group = dest[i:i + per_asp]
        p20.aspirate(MM_VOL * len(group), mm_res.wells()[0].bottom(2))
        for w in group:
            p20.dispense(MM_VOL, w.top(-2))
        p20.blow_out(mm_res.wells()[0].top())
    p20.drop_tip()

    # 2) Primer pair for each colony (fresh tip per well to avoid cross-contamination).
    p20.reset_tipracks()
    protocol.comment('Step 2: add 4 uL of the matching primer pair to each well (new tip each).')
    for src, dst in zip(primer_plate.wells(), dest):
        p20.pick_up_tip()
        p20.aspirate(PRIMER_VOL, src.bottom(1))
        p20.dispense(PRIMER_VOL, dst.bottom(1))
        p20.mix(2, 8, dst.bottom(1))
        p20.blow_out(dst.top())
        p20.drop_tip()

    # 3) Colony template, 1 uL, as in the paper's OT-2 workflow.
    p20.reset_tipracks()
    protocol.comment('Step 3: add 1 uL colony template to each well (new tip each); total 10 uL.')
    for src, dst in zip(colony_plate.wells(), dest):
        p20.pick_up_tip()
        p20.aspirate(TEMPLATE_VOL, src.bottom(1))
        p20.dispense(TEMPLATE_VOL, dst.bottom(1))
        p20.mix(3, 6, dst.bottom(1))
        p20.blow_out(dst.top())
        p20.drop_tip()
    p20.reset_tipracks()

    protocol.comment('Manual step: seal the PCR plate (adhesive seal), briefly spin down.')
    protocol.comment(
        'Off-deck thermocycling (Q5 Hot Start; paper leaves cycling to the polymerase manufacturer, '
        'adjusted for amplicon size/primers): 98 C 3 min (longer initial denaturation to lyse cells); '
        '30 cycles of 98 C 10 s, annealing at primer Tm (typically 55-65 C, per NEB Tm calculator) 20 s, '
        '72 C 20-30 s/kb; final extension 72 C 2 min; hold 4 C. Lid at 105 C.')
    protocol.comment('Manual step: analyse products by agarose gel electrophoresis to score correct assemblies.')
