"""Colony PCR screening with Q5 Hot Start master mix (OT-2).

Based on the Slowpoke colony PCR workflow (ACS Synth. Biol.,
doi:10.1021/acssynbio.5c00629): master mix is dispensed first into the PCR
plate, then colony template and primers are added to each reaction.
"""

metadata = {
    'protocolName': 'Colony PCR screening with Q5 Hot Start master mix',
    'author': 'Slowpoke-derived protocol',
    'description': '18 uL Q5 2x master mix + 1 uL colony template + 1 uL primer mix per well',
    'apiLevel': '2.15',
}

MASTER_MIX_VOL = 18   # uL per reaction
TEMPLATE_VOL = 1      # uL per reaction
PRIMER_VOL = 1        # uL per reaction
MIX_REPS = 3
MIX_VOL = 10          # uL, mixing volume after template addition (well holds 19 uL)


def run(protocol):
    # ---- Labware ----
    colony_plate = protocol.load_labware(
        'corning_96_wellplate_360ul_flat', 1, label='colony_plate')
    pcr_plate = protocol.load_labware(
        'corning_96_wellplate_360ul_flat', 2, label='pcr_plate')
    mm_reservoir = protocol.load_labware(
        'nest_1_reservoir_195ml', 3, label='master_mix_reservoir')
    primer_plate = protocol.load_labware(
        'corning_96_wellplate_360ul_flat', 4, label='primer_plate')

    tips20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tips300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)

    # ---- Pipettes ----
    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tips20])
    p300 = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tips300])

    master_mix = mm_reservoir['A1']
    dest_wells = pcr_plate.wells()          # A1..H12, column-major
    colony_wells = colony_plate.wells()
    primer_wells = primer_plate.wells()

    # ---- Step 1: 18 uL Q5 2x master mix into every PCR well ----
    # The PCR plate is empty, so a single tip can serve all 96 wells.
    protocol.comment('Step 1: dispensing 18 uL Q5 Hot Start 2x master mix into pcr_plate A1:H12')
    p20.pick_up_tip()
    for dest in dest_wells:
        p20.aspirate(MASTER_MIX_VOL, master_mix)
        p20.dispense(MASTER_MIX_VOL, dest)
        p20.blow_out(dest.top())
    p20.drop_tip()
    p20.reset_tipracks()

    # ---- Step 2: 1 uL colony template, fresh tip per reaction, mix 3x ----
    protocol.comment('Step 2: adding 1 uL colony template (colony_plate -> pcr_plate, well to well), mixing 3x')
    for src, dest in zip(colony_wells, dest_wells):
        p20.pick_up_tip()
        p20.aspirate(TEMPLATE_VOL, src)
        p20.dispense(TEMPLATE_VOL, dest)
        p20.mix(MIX_REPS, MIX_VOL, dest)
        p20.blow_out(dest.top())
        p20.drop_tip()
    p20.reset_tipracks()

    # ---- Step 3: 1 uL primer pair, fresh tip per reaction ----
    protocol.comment('Step 3: adding 1 uL primer mix (primer_plate -> pcr_plate, well to well)')
    for src, dest in zip(primer_wells, dest_wells):
        p20.pick_up_tip()
        p20.aspirate(PRIMER_VOL, src)
        p20.dispense(PRIMER_VOL, dest)
        p20.blow_out(dest.top())
        p20.drop_tip()
    p20.reset_tipracks()

    # ---- Step 4: off-deck sealing and thermocycling ----
    protocol.comment('Step 4: Seal pcr_plate and transfer to thermocycler.')
    protocol.comment('Thermocycle: 98 C 30 s; [98 C 10 s, 60 C 30 s, 72 C 30 s] x 30 cycles; '
                     '72 C 2 min; hold 4 C.')
    protocol.comment('Each pcr_plate well now holds 20 uL (18 uL master mix + 1 uL template + 1 uL primers).')
