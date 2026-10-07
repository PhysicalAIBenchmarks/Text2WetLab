"""Magnetic-bead SARS-CoV-2 RNA extraction on the OT-2 (48 samples).

In-house OT-2 protocol from "Automated low-cost SARS-CoV-2 RNA extraction
protocols" (PLOS ONE 2021, doi:10.1371/journal.pone.0246302).

Samples 1-48 go to the odd columns (1, 3, 5, 7, 9, 11) of the deep-well
plate on the magnetic module, column-wise (sample 1 -> A1 ... sample 8 -> H1,
sample 9 -> A3 ...). Each eluate ends up in the same well position of the
elution plate on the 4 C temperature module.
"""

metadata = {
    'protocolName': 'In-house magnetic-bead RNA extraction (48 samples)',
    'author': 'Automated from Lopez-Fernandez et al., PLOS ONE 2021',
    'description': 'Beads + isopropanol binding, 2x 70% ethanol washes, '
                   '100 uL elution; 48 samples in the odd columns of the '
                   'magnetic-module plate.',
    'apiLevel': '2.9',
}

NUM_SAMPLES = 48
SAMPLE_COLUMNS = [0, 2, 4, 6, 8, 10]      # odd columns 1, 3, 5, 7, 9, 11

BEAD_VOL = 40
ISOPROP_VOL = 250
SAMPLE_VOL = 250
SUPERNATANT_VOL = 540
ETHANOL_VOL = 500
ELUTION_VOL = 100
ELUATE_VOL = 80

MULTI_MAX = 200          # 200 uL filter tips on the p300 multi


def split_volume(total, max_vol=MULTI_MAX):
    """Split a per-well volume into equal chunks that fit in one tip."""
    n = -(-total // max_vol)
    chunk = total / n
    return [chunk] * n


def run(protocol):
    # ---------------------------------------------------------------- deck
    waste_plate = protocol.load_labware(
        'usascientific_96_wellplate_2.4ml_deep', '1', 'waste plate')
    tips200 = [protocol.load_labware('opentrons_96_filtertiprack_200ul', s)
               for s in ['2', '3', '9']]
    tips1000 = [protocol.load_labware('opentrons_96_filtertiprack_1000ul', '11')]

    mag_mod = protocol.load_module('magnetic module', '4')
    mag_plate = mag_mod.load_labware(
        'usascientific_96_wellplate_2.4ml_deep', 'sample plate')

    reservoir = protocol.load_labware('nest_12_reservoir_15ml', '5', 'reagents')

    temp_mod = protocol.load_module('tempdeck', '6')
    elution_plate = temp_mod.load_labware(
        'thermo_96_wellplate_200ul', 'elution plate')

    rack_1_24 = protocol.load_labware(
        'opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', '10',
        'samples 1-24')
    rack_25_48 = protocol.load_labware(
        'opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', '7',
        'samples 25-48')

    p1000 = protocol.load_instrument('p1000_single_gen2', 'left',
                                     tip_racks=tips1000)
    m300 = protocol.load_instrument('p300_multi_gen2', 'right',
                                    tip_racks=tips200)

    # ------------------------------------------------------------ reagents
    beads = reservoir.wells()[1]                       # column 2
    elution_buffer = reservoir.wells()[3]              # column 4
    isopropanol = reservoir.wells()[5:7]               # columns 6-7
    ethanol = reservoir.wells()[8:12]                  # columns 9-12

    # -------------------------------------------------------------- wells
    sample_tubes = rack_1_24.wells() + rack_25_48.wells()
    sample_wells = [mag_plate.columns()[c][r]
                    for c in SAMPLE_COLUMNS for r in range(8)]
    assert len(sample_tubes) >= NUM_SAMPLES and len(sample_wells) == NUM_SAMPLES

    mag_cols = [mag_plate.columns()[c][0] for c in SAMPLE_COLUMNS]
    waste_cols = [waste_plate.columns()[c][0] for c in SAMPLE_COLUMNS]
    elution_cols = [elution_plate.columns()[c][0] for c in SAMPLE_COLUMNS]

    # ------------------------------------------------------------ helpers
    def add_reagent_one_tip(sources, volume, per_source):
        """Dispense `volume` into every sample column using a single tip.

        The tip only ever aspirates from the reservoir and dispenses above
        the liquid, so it never touches sample material. `sources` are used
        in order, `per_source` columns each.
        """
        m300.pick_up_tip()
        for i, dest in enumerate(mag_cols):
            src = sources[i // per_source]
            for vol in split_volume(volume):
                m300.aspirate(vol, src.bottom(2))
                m300.dispense(vol, dest.top(-3))
                m300.blow_out(dest.top(-3))
        m300.drop_tip()

    def remove_to_waste(volume):
        """Pull `volume` off the pelleted beads into the waste plate.

        Fresh tip per sample column; slow aspiration from just above the
        well bottom so the bead pellet is not disturbed.
        """
        m300.flow_rate.aspirate = 40
        for src, dst in zip(mag_cols, waste_cols):
            m300.pick_up_tip()
            for vol in split_volume(volume):
                m300.aspirate(vol, src.bottom(0.8))
                m300.dispense(vol, dst.top(-5))
                m300.blow_out(dst.top(-5))
            m300.drop_tip()
        m300.flow_rate.aspirate = 94

    # ====================================================== 1. module setup
    mag_mod.disengage()
    temp_mod.set_temperature(4)

    # ================================================ 2. magnetic beads
    protocol.comment('Adding %d uL magnetic beads to each sample well'
                     % BEAD_VOL)
    m300.pick_up_tip()
    m300.mix(5, 150, beads.bottom(2))           # resuspend the bead slurry
    m300.blow_out(beads.top())
    for dest in mag_cols:
        m300.aspirate(BEAD_VOL, beads.bottom(2))
        m300.dispense(BEAD_VOL, dest.top(-3))
        m300.blow_out(dest.top(-3))
    m300.drop_tip()

    # ==================================================== 3. isopropanol
    protocol.comment('Adding %d uL isopropanol to each sample well'
                     % ISOPROP_VOL)
    add_reagent_one_tip(isopropanol, ISOPROP_VOL, per_source=3)

    # ======================================================== 4. samples
    protocol.comment('Transferring %d uL of each sample (fresh tip each)'
                     % SAMPLE_VOL)
    for tube, well in zip(sample_tubes[:NUM_SAMPLES], sample_wells):
        p1000.pick_up_tip()
        p1000.aspirate(SAMPLE_VOL, tube.bottom(2))
        p1000.dispense(SAMPLE_VOL, well.bottom(5))
        p1000.mix(5, SAMPLE_VOL, well.bottom(3))
        p1000.blow_out(well.top(-3))
        p1000.drop_tip()

    # ================================================= 5. bind (5 min RT)
    protocol.delay(minutes=5, msg='Binding: 5 min at room temperature')

    # ============================================== 6. magnet, 4 minutes
    mag_mod.engage()
    protocol.delay(minutes=4, msg='Magnet engaged: pulling beads 4 min')

    # ============================================= 7. remove supernatant
    protocol.comment('Removing supernatant to waste plate')
    remove_to_waste(SUPERNATANT_VOL)

    # ======================================== 8-9. two 70% ethanol washes
    for wash in range(2):
        protocol.comment('70%% ethanol wash %d: adding %d uL'
                         % (wash + 1, ETHANOL_VOL))
        # wash 1 draws from columns 9-10, wash 2 from columns 11-12
        add_reagent_one_tip(ethanol[2 * wash:2 * wash + 2], ETHANOL_VOL,
                            per_source=3)
        protocol.comment('70%% ethanol wash %d: removing to waste'
                         % (wash + 1))
        remove_to_waste(ETHANOL_VOL)

    # ===================================================== 10. air dry
    protocol.delay(minutes=4, msg='Air-drying beads 4 min (magnet engaged)')

    # ==================================================== 11. elution
    mag_mod.disengage()
    protocol.comment('Adding %d uL elution buffer and resuspending beads'
                     % ELUTION_VOL)
    for dest in mag_cols:
        m300.pick_up_tip()
        m300.aspirate(ELUTION_VOL, elution_buffer.bottom(2))
        m300.dispense(ELUTION_VOL, dest.bottom(1))
        m300.mix(10, 80, dest.bottom(1))
        m300.blow_out(dest.top(-3))
        m300.drop_tip()

    # ============================================ 12. 30 s, magnet, 90 s
    protocol.delay(seconds=30, msg='Elution: 30 s')
    mag_mod.engage()
    protocol.delay(seconds=90, msg='Magnet engaged: 90 s')

    # ============================================ 13. recover the eluate
    protocol.comment('Transferring %d uL eluate to the elution plate (4 C)'
                     % ELUATE_VOL)
    m300.flow_rate.aspirate = 40
    for src, dst in zip(mag_cols, elution_cols):
        m300.pick_up_tip()
        m300.aspirate(ELUATE_VOL, src.bottom(0.8))
        m300.dispense(ELUATE_VOL, dst.bottom(2))
        m300.blow_out(dst.top(-2))
        m300.drop_tip()
    m300.flow_rate.aspirate = 94

    # ============================================================ 14. end
    mag_mod.disengage()
    protocol.comment('Extraction complete. Eluates are on the 4 C '
                     'temperature module.')
