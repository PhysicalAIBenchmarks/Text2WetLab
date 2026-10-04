"""
OT-2 in-house magnetic-bead SARS-CoV-2 RNA extraction, 48 samples.

Based on: Automated low-cost SARS-CoV-2 RNA extraction protocols.
PLOS ONE 2021, doi:10.1371/journal.pone.0246302 ("OT-2in-house" protocol).

Per sample (deep-well plate on the GEN1 magnetic module):
  1. 40 uL magnetic beads + 250 uL isopropanol + 250 uL inactivated sample,
     mix by pipetting 5 times, incubate 5 min at room temperature.
  2. Engage the magnetic module for 4 min.
  3. Collect the supernatant and discard.
  4. Add 500 uL ethanol 70%, collect and discard.
  5. Add 500 uL ethanol 70%, collect and discard.
  6. Air dry 4 min.
  7. Disengage the magnet and add 100 uL elution buffer.
  8. After 30 s engage the magnet.
  9. After 90 s collect the eluate and transfer it to the elution plate (4 C).
"""
from opentrons import protocol_api

metadata = {
    'protocolName': 'OT-2 in-house magnetic bead RNA extraction (48 samples)',
    'author': 'Implemented from Ambrosi et al., PLOS ONE 2021',
    'description': 'Isopropanol/magnetic-bead RNA extraction, 2x ethanol '
                   '70% washes, elution in 100 uL elution buffer.',
    'apiLevel': '2.13',
}

NUM_SAMPLES = 48

BEAD_VOL = 40
ISOPROPANOL_VOL = 250
SAMPLE_VOL = 250
BINDING_VOL = BEAD_VOL + ISOPROPANOL_VOL + SAMPLE_VOL  # 540 uL
WASH_VOL = 500
ELUTION_VOL = 100

MIX_REPS = 5
BINDING_INCUBATION_MIN = 5
MAGNET_BINDING_MIN = 4
AIR_DRY_MIN = 4
ELUTION_RESUSPEND_SEC = 30
ELUTION_MAGNET_SEC = 90

P300_MAX = 180  # working volume per trip with 200 uL filter tips (air gap room)


def run(protocol: protocol_api.ProtocolContext):
    # ---------------- Labware ----------------
    waste_plate = protocol.load_labware(
        'usascientific_96_wellplate_2.4ml_deep', '1', 'Waste plate')
    tips200 = [protocol.load_labware('opentrons_96_filtertiprack_200ul', s)
               for s in ['2', '3', '9']]
    tips1000 = [protocol.load_labware('opentrons_96_filtertiprack_1000ul', '11')]

    magdeck = protocol.load_module('magnetic module', '4')
    mag_plate = magdeck.load_labware(
        'usascientific_96_wellplate_2.4ml_deep', 'Extraction plate')
    magdeck.disengage()

    reservoir = protocol.load_labware('nest_12_reservoir_15ml', '5', 'Reagents')

    tempdeck = protocol.load_module('tempdeck', '6')
    elution_plate = tempdeck.load_labware('thermo_96_wellplate_200ul',
                                          'Elution plate')
    tempdeck.set_temperature(4)

    tube_racks = [
        protocol.load_labware(
            'opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', '10',
            'Samples 1-24'),
        protocol.load_labware(
            'opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', '7',
            'Samples 25-48'),
    ]

    # ---------------- Pipettes ----------------
    p1000 = protocol.load_instrument('p1000_single_gen2', 'left',
                                     tip_racks=tips1000)
    m300 = protocol.load_instrument('p300_multi_gen2', 'right',
                                    tip_racks=tips200)

    # ---------------- Reagents ----------------
    beads = reservoir.wells_by_name()['A2']
    elution_buffer = reservoir.wells_by_name()['A4']
    isopropanol = [reservoir.wells_by_name()[w] for w in ['A6', 'A7']]
    ethanol_wash1 = [reservoir.wells_by_name()[w] for w in ['A9', 'A10']]
    ethanol_wash2 = [reservoir.wells_by_name()[w] for w in ['A11', 'A12']]

    # ---------------- Sample layout ----------------
    # 48 samples in the odd columns (1, 3, 5, 7, 9, 11) of the extraction plate.
    sample_cols = [1, 3, 5, 7, 9, 11]
    num_cols = NUM_SAMPLES // 8
    mag_cols = [mag_plate.columns_by_name()[str(c)] for c in sample_cols][:num_cols]
    mag_heads = [col[0] for col in mag_cols]  # A-row wells for the multichannel
    waste_heads = [waste_plate.columns_by_name()[str(c)][0]
                   for c in sample_cols][:num_cols]
    elution_heads = [elution_plate.columns_by_name()[str(c)][0]
                     for c in sample_cols][:num_cols]

    sample_tubes = [tube for rack in tube_racks for tube in rack.wells()]
    dest_wells = [well for col in mag_cols for well in col]

    def reservoir_for(source_list, col_idx):
        # each reservoir column feeds three plate columns (24 samples)
        return source_list[col_idx * len(source_list) // num_cols]

    def split(vol, max_vol=P300_MAX):
        n = -(-vol // max_vol)
        base = vol / n
        return [base] * n

    def remove_supernatant(vol, source, dest):
        m300.flow_rate.aspirate = 30
        for v in split(vol):
            m300.aspirate(v, source.bottom(1))
            m300.air_gap(10)
            m300.dispense(v + 10, dest.top(-5))
            m300.blow_out(dest.top(-5))
        m300.flow_rate.aspirate = 94

    # ===== Step 1: binding mix =====
    # 40 uL magnetic beads (resuspend beads first)
    protocol.comment('Step 1: dispensing 40 uL magnetic beads')
    m300.pick_up_tip()
    m300.mix(5, 150, beads.bottom(1))
    for dest in mag_heads:
        m300.aspirate(BEAD_VOL, beads.bottom(1))
        m300.dispense(BEAD_VOL, dest.bottom(2))
        m300.blow_out(dest.top(-2))
    m300.drop_tip()

    # 250 uL isopropanol
    protocol.comment('Step 1: dispensing 250 uL isopropanol')
    m300.pick_up_tip()
    for i, dest in enumerate(mag_heads):
        src = reservoir_for(isopropanol, i)
        for v in split(ISOPROPANOL_VOL):
            m300.aspirate(v, src.bottom(1))
            m300.dispense(v, dest.top(-2))
            m300.blow_out(dest.top(-2))
    m300.drop_tip()

    # 250 uL inactivated sample, mix 5 times
    protocol.comment('Step 1: adding 250 uL sample and mixing 5 times')
    for tube, dest in zip(sample_tubes, dest_wells):
        p1000.pick_up_tip()
        p1000.aspirate(SAMPLE_VOL, tube.bottom(2))
        p1000.dispense(SAMPLE_VOL, dest.bottom(2))
        p1000.mix(MIX_REPS, 400, dest.bottom(2))
        p1000.blow_out(dest.top(-2))
        p1000.drop_tip()

    protocol.comment('Incubating 5 min at room temperature')
    protocol.delay(minutes=BINDING_INCUBATION_MIN)

    # ===== Step 2: magnet 4 min =====
    magdeck.engage()
    protocol.delay(minutes=MAGNET_BINDING_MIN)

    # ===== Step 3: discard supernatant =====
    protocol.comment('Step 3: removing supernatant')
    for src, dest in zip(mag_heads, waste_heads):
        m300.pick_up_tip()
        remove_supernatant(BINDING_VOL, src, dest)
        m300.drop_tip()

    # ===== Steps 4-5: two 70% ethanol washes (magnet engaged) =====
    for wash_num, ethanol in enumerate([ethanol_wash1, ethanol_wash2], 1):
        protocol.comment(f'Step {wash_num + 3}: ethanol 70% wash {wash_num}')
        m300.pick_up_tip()
        for i, dest in enumerate(mag_heads):
            src = reservoir_for(ethanol, i)
            for v in split(WASH_VOL):
                m300.aspirate(v, src.bottom(1))
                m300.dispense(v, dest.top(-2))
                m300.blow_out(dest.top(-2))
        m300.drop_tip()
        for src, dest in zip(mag_heads, waste_heads):
            m300.pick_up_tip()
            remove_supernatant(WASH_VOL, src, dest)
            m300.drop_tip()

    # ===== Step 6: air dry =====
    protocol.comment('Step 6: air drying beads 4 min')
    protocol.delay(minutes=AIR_DRY_MIN)

    # ===== Step 7: magnet off, add 100 uL elution buffer =====
    magdeck.disengage()
    protocol.comment('Step 7: adding 100 uL elution buffer')
    for dest in mag_heads:
        m300.pick_up_tip()
        m300.aspirate(ELUTION_VOL, elution_buffer.bottom(1))
        m300.dispense(ELUTION_VOL, dest.bottom(1))
        m300.mix(5, 80, dest.bottom(1))
        m300.blow_out(dest.bottom(5))
        m300.drop_tip()

    # ===== Step 8: after 30 s engage magnet =====
    protocol.delay(seconds=ELUTION_RESUSPEND_SEC)
    magdeck.engage()

    # ===== Step 9: after 90 s transfer eluate to elution plate (4 C) =====
    protocol.delay(seconds=ELUTION_MAGNET_SEC)
    protocol.comment('Step 9: transferring eluate to elution plate')
    m300.flow_rate.aspirate = 20
    for src, dest in zip(mag_heads, elution_heads):
        m300.pick_up_tip()
        m300.aspirate(ELUTION_VOL, src.bottom(0.5))
        m300.dispense(ELUTION_VOL, dest.bottom(1))
        m300.blow_out(dest.top(-2))
        m300.drop_tip()
    m300.flow_rate.aspirate = 94

    magdeck.disengage()
    protocol.comment('Extraction finished. Eluates are held at 4 C on the '
                     'temperature module (slot 6).')
