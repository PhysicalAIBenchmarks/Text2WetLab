"""Colony PCR screening with Q5 Hot Start master mix (OT-2).

Adapted from the Slowpoke colony PCR workflow (ACS Synth. Biol.,
doi:10.1021/acssynbio.5c00629): dispense PCR master mix into a 96-well PCR
plate, then add colony template and the matching primer pair to each well.
"""

from opentrons import protocol_api

metadata = {
    'protocolName': 'Colony PCR screening with Q5 Hot Start master mix',
    'author': 'Slowpoke-derived OT-2 protocol',
    'description': ('18 uL Q5 Hot Start 2x master mix + 1 uL colony template '
                    '+ 1 uL primer pair per well, 96 reactions'),
    'apiLevel': '2.15',
}

MASTER_MIX_VOL = 18   # uL per reaction
TEMPLATE_VOL = 1      # uL per reaction
PRIMER_VOL = 1        # uL per reaction
TEMPLATE_MIX_REPS = 3
TEMPLATE_MIX_VOL = 10  # uL, within the 19 uL present after template addition


def run(protocol: protocol_api.ProtocolContext):
    # ---------------- Labware ----------------
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

    # ---------------- Pipettes ----------------
    p20 = protocol.load_instrument(
        'p20_single_gen2', 'left', tip_racks=[tips20])
    p300 = protocol.load_instrument(  # noqa: F841 - loaded per deck setup
        'p300_single_gen2', 'right', tip_racks=[tips300])

    master_mix = master_mix_reservoir['A1']
    dest_wells = pcr_plate.wells()          # A1..H12, column-major
    colony_wells = colony_plate.wells()
    primer_wells = primer_plate.wells()

    # ---------------- Step 1: master mix ----------------
    # 18 uL is below the p300 minimum, so the p20 is used. The destination
    # wells are empty, so one tip is used for the whole plate; dispensing is
    # done just above the well bottom so the tip never touches dispensed mix.
    protocol.comment('Step 1: 18 uL Q5 Hot Start 2x master mix to each '
                     'pcr_plate well (A1:H12).')
    p20.pick_up_tip()
    for dest in dest_wells:
        p20.aspirate(MASTER_MIX_VOL, master_mix)
        p20.dispense(MASTER_MIX_VOL, dest.bottom(2))
        p20.blow_out(dest.bottom(2))
    p20.drop_tip()
    p20.reset_tipracks()

    # ---------------- Step 2: colony template ----------------
    # Fresh tip per well to avoid cross-contaminating colonies; mix 3x after
    # dispensing to combine template with the master mix.
    protocol.comment('Step 2: 1 uL colony template from colony_plate to the '
                     'matching pcr_plate well, mixing 3x after dispensing.')
    for src, dest in zip(colony_wells, dest_wells):
        p20.pick_up_tip()
        p20.aspirate(TEMPLATE_VOL, src)
        p20.dispense(TEMPLATE_VOL, dest)
        p20.mix(TEMPLATE_MIX_REPS, TEMPLATE_MIX_VOL, dest)
        p20.blow_out(dest.top(-2))
        p20.drop_tip()
    p20.reset_tipracks()

    # ---------------- Step 3: primer pairs ----------------
    protocol.comment('Step 3: 1 uL primer pair from primer_plate to the '
                     'matching pcr_plate well.')
    for src, dest in zip(primer_wells, dest_wells):
        p20.pick_up_tip()
        p20.aspirate(PRIMER_VOL, src)
        p20.dispense(PRIMER_VOL, dest)
        p20.blow_out(dest.top(-2))
        p20.drop_tip()
    p20.reset_tipracks()

    # ---------------- Step 4: off-deck thermocycling ----------------
    protocol.comment('Step 4 (manual): seal pcr_plate and thermocycle: '
                     '98 C 30 s; [98 C 10 s, 60 C 30 s, 72 C 30 s] x 30; '
                     '72 C 2 min; hold at 4 C.')
