"""Colony PCR screening with Q5 Hot Start 2x master mix (OT-2).

Adapted from the Slowpoke colony PCR workflow (Golden Gate cloning and colony
PCR on OT-2/Flex, ACS Synth. Biol., doi:10.1021/acssynbio.5c00629).

Per PCR well (96 reactions, pcr_plate A1:H12):
    18 uL Q5 Hot Start 2x master mix   (master_mix_reservoir A1)
     1 uL colony template              (colony_plate, well-for-well)
     1 uL primer pair                  (primer_plate, well-for-well)
    -----
    20 uL total, then seal and thermocycle off-deck.
"""

metadata = {
    'protocolName': 'Colony PCR screening with Q5 Hot Start master mix',
    'author': 'Slowpoke-derived protocol',
    'description': ('Dispense 18 uL Q5 HS 2x master mix, then 1 uL colony '
                    'template and 1 uL primer pair per well of a 96-well '
                    'PCR plate.'),
    'apiLevel': '2.15',
}

MASTER_MIX_VOL = 18   # uL per reaction
TEMPLATE_VOL = 1      # uL per reaction
PRIMER_VOL = 1        # uL per reaction
MIX_VOL = 10          # uL used when mixing after template addition
MIX_REPS = 3
N_REACTIONS = 96      # full plate, A1:H12


def run(protocol):
    # ------------------------------------------------------------------ deck
    colony_plate = protocol.load_labware(
        'corning_96_wellplate_360ul_flat', 1, label='colony_plate')
    pcr_plate = protocol.load_labware(
        'corning_96_wellplate_360ul_flat', 2, label='pcr_plate')
    master_mix_reservoir = protocol.load_labware(
        'nest_1_reservoir_195ml', 3, label='master_mix_reservoir')
    primer_plate = protocol.load_labware(
        'corning_96_wellplate_360ul_flat', 4, label='primer_plate')

    tips20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tips300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)

    p20 = protocol.load_instrument(
        'p20_single_gen2', 'left', tip_racks=[tips20])
    p300 = protocol.load_instrument(  # noqa: F841 - loaded per deck setup
        'p300_single_gen2', 'right', tip_racks=[tips300])

    master_mix = master_mix_reservoir.wells_by_name()['A1']
    pcr_wells = pcr_plate.wells()[:N_REACTIONS]
    colony_wells = colony_plate.wells()[:N_REACTIONS]
    primer_wells = primer_plate.wells()[:N_REACTIONS]

    # ---------------------------------------------- 1. master mix, 18 uL/well
    # Master mix is the only liquid in the plate at this point, so a single
    # tip can be reused for all 96 wells (dispensed from above the liquid so
    # the tip never touches the destination).
    protocol.comment('Step 1: 18 uL Q5 Hot Start 2x master mix -> pcr_plate '
                     'A1:H12 (single tip).')
    p20.pick_up_tip()
    for dest in pcr_wells:
        p20.aspirate(MASTER_MIX_VOL, master_mix)
        p20.dispense(MASTER_MIX_VOL, dest.bottom(2))
        p20.blow_out(dest.top())
    p20.drop_tip()

    # ------------------------------------------ 2. colony template, 1 uL/well
    # Fresh tip per colony; mix 3x after dispensing to disperse the template.
    protocol.comment('Step 2: 1 uL colony template colony_plate -> pcr_plate, '
                     'well-for-well, mix 3x after dispense (fresh tip each).')
    p20.reset_tipracks()
    for src, dest in zip(colony_wells, pcr_wells):
        p20.pick_up_tip()
        p20.aspirate(TEMPLATE_VOL, src)
        p20.dispense(TEMPLATE_VOL, dest)
        p20.mix(MIX_REPS, MIX_VOL, dest)
        p20.blow_out(dest.top())
        p20.drop_tip()

    # --------------------------------------------- 3. primer pairs, 1 uL/well
    # Fresh tip per primer pair to avoid cross-contaminating primer stocks.
    protocol.comment('Step 3: 1 uL primer pair primer_plate -> pcr_plate, '
                     'well-for-well (fresh tip each).')
    p20.reset_tipracks()
    for src, dest in zip(primer_wells, pcr_wells):
        p20.pick_up_tip()
        p20.aspirate(PRIMER_VOL, src)
        p20.dispense(PRIMER_VOL, dest)
        p20.blow_out(dest.top())
        p20.drop_tip()

    # ------------------------------------------ 4. off-deck seal + thermocycle
    protocol.comment('Step 4 (manual, off-deck): seal pcr_plate and run '
                     'thermocycler program: 98 C 30 s; [98 C 10 s, 60 C 30 s, '
                     '72 C 30 s] x 30 cycles; 72 C 2 min; hold at 4 C.')
    protocol.comment('Final volume per PCR well: 20 uL '
                     '(18 uL master mix + 1 uL template + 1 uL primers).')
