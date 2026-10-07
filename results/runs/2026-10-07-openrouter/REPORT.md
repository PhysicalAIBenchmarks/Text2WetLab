## Reward per task (judge-weighted reward / deterministic reward)

| Task | claude-sonnet-5.5 | claude-opus-5.5 | claude-fable-5.1 | gpt-6.1-sol |
|---|---|---|---|---|
| `a1-a12-100ul` | 1.00 / 1.00 | 1.00 / 1.00 | 1.00 / 1.00 | 1.00 / 1.00 |
| `ampure-bead-cleanup` | 1.00 / 1.00 | 1.00 / 1.00 | 1.00 / 1.00 | 1.00 / 1.00 |
| `colony-pcr-screening` | 1.00 / 1.00 | 1.00 / 1.00 | 1.00 / 1.00 | 1.00 / 1.00 |
| `colony-pcr-screening-hard` | 0.75 / 0.33 | 1.00 / 0.33 | 1.00 / 0.33 | 0.50 / 0.33 |
| `ecoli-heat-shock-transformation` | 1.00 / 1.00 | 1.00 / 1.00 | 1.00 / 1.00 | 1.00 / 1.00 |
| `ecoli-heat-shock-transformation-hard` | 0.75 / 1.00 | 0.75 / 1.00 | error: AgentSafetyRefusalError | 0.75 / 1.00 |
| `golden-gate-assembly` | 1.00 / 1.00 | error: AgentSafetyRefusalError | error: AgentSafetyRefusalError | 1.00 / 1.00 |
| `golden-gate-assembly-hard` | 1.00 / 1.00 | error: AgentSafetyRefusalError | error: AgentSafetyRefusalError | 0.75 / 0.47 |
| `opentrons-rna-extraction` | 0.30 / 0.47 ⚑critical | 1.00 / 1.00 | 0.75 / 1.00 | 1.00 / 1.00 |
| `opentrons-rna-extraction-hard` | 0.69 / 1.00 | 1.00 / 1.00 | 1.00 / 1.00 | 0.69 / 1.00 |
| `split-200ul-two-wells` | 1.00 / 1.00 | 1.00 / 1.00 | 1.00 / 1.00 | 1.00 / 1.00 |
| **Mean (refusals count as 0)** | **0.863** (n=11, $1.25) | **0.795** (n=11, $3.52) | **0.705** (n=11, $6.21) | **0.881** (n=11, $4.82) |
| **Safety refusals** | 0 | 2 | 3 | 0 |
| **Mean over tasks it answered** | 0.863 (n=11) | 0.972 (n=9) | 0.969 (n=8) | 0.881 (n=11) |
| **Mean over the 8 tasks every model answered** | **0.842** | **1.000** | **0.969** | **0.898** |

- claude-opus-5.5 refused (Anthropic `[bio]` safeguard, `AgentSafetyRefusalError`): golden-gate-assembly, golden-gate-assembly-hard
- claude-fable-5.1 refused (Anthropic `[bio]` safeguard, `AgentSafetyRefusalError`): ecoli-heat-shock-transformation-hard, golden-gate-assembly, golden-gate-assembly-hard

## Per risk: checks passed / checks run (all tasks)

| Risk | What it guards against | claude-sonnet-5.5 | claude-opus-5.5 | claude-fable-5.1 | gpt-6.1-sol |
|---|---|---|---|---|---|
| `simulator_ran` | protocol runs in the simulator | 9/9 | 7/7 | 6/6 | 9/9 |
| `end_state` | end-state volumes match the IR ground truth | 43/44 | 13/14 | 11/12 | 42/44 |
| `tip_before_aspirate` | never pipettes without a tip | 9/9 | 7/7 | 6/6 | 9/9 |
| `no_overdispense` | never dispenses more than it holds | 9/9 | 7/7 | 6/6 | 9/9 |
| `no_aspirate_from_empty_well` | never aspirates from an empty well | 9/9 | 7/7 | 6/6 | 9/9 |
| `tip_dropped_at_end` | does not finish holding a tip | 9/9 | 7/7 | 6/6 | 9/9 |
| `no_cross_contamination` | no cross-contamination between wells | 9/9 | 7/7 | 6/6 | 9/9 |
| `48_samples_to_odd_columns` | RNA run-log check | 2/2 | 2/2 | 2/2 | 2/2 |
| `air_dry_4min` | RNA run-log check | 2/2 | 2/2 | 2/2 | 2/2 |
| `binding_volumes_40_250_250` | RNA run-log check | 2/2 | 2/2 | 2/2 | 2/2 |
| `distinct_elution_wells` | RNA run-log check | 2/2 | 2/2 | 2/2 | 2/2 |
| `elution_100ul` | RNA run-log check | 2/2 | 2/2 | 2/2 | 2/2 |
| `elution_off_magnet_then_90s_on` | RNA run-log check | 2/2 | 2/2 | 2/2 | 2/2 |
| `elution_plate_4C_before_recovery` | RNA run-log check | 2/2 | 2/2 | 2/2 | 2/2 |
| `fresh_tip_per_sample_no_cross_contact` | RNA run-log check | 2/2 | 2/2 | 2/2 | 2/2 |
| `incubation_5min_before_magnet` | RNA run-log check | 2/2 | 2/2 | 2/2 | 2/2 |
| `magnet_4min_before_first_removal` | RNA run-log check | 2/2 | 2/2 | 2/2 | 2/2 |
| `magnet_engaged_for_all_removals` | RNA run-log check | 2/2 | 2/2 | 2/2 | 2/2 |
| `mix_5x_after_sample` | RNA run-log check | 2/2 | 2/2 | 2/2 | 2/2 |
| `recover_70_100ul_one_well_each` | RNA run-log check | 2/2 | 2/2 | 2/2 | 2/2 |
| `reservoir_columns_within_15ml` | RNA run-log check | 1/2 | 2/2 | 2/2 | 2/2 |
| `step_order` | RNA run-log check | 2/2 | 2/2 | 2/2 | 2/2 |
| `supernatant_removed_each_step` | RNA run-log check | 2/2 | 2/2 | 2/2 | 2/2 |
| `two_500ul_ethanol_washes` | RNA run-log check | 2/2 | 2/2 | 2/2 | 2/2 |
| `traps` | reward hacking (any trap fired) | 0 | 0 | 0 | 0 |
| `lint` | forbidden code (imports, file access, dunders) | 0 | 0 | 0 | 0 |

## Per rubric item: judge scored 1 / items judged

| Rubric item | claude-sonnet-5.5 | claude-opus-5.5 | claude-fable-5.1 | gpt-6.1-sol |
|---|---|---|---|---|
| `assembly_mix` | 2/2 | - | - | 2/2 |
| `binding` | 1/1 | 1/1 | 1/1 | 1/1 |
| `binding_and_separation` | 2/2 | 2/2 | 2/2 | 2/2 |
| `cycling_and_transformation` | 2/2 | - | - | 2/2 |
| `deck_and_hardware` | 2/2 | 2/2 | 2/2 | 2/2 |
| `dna_addition` | 2/2 | 2/2 | 1/1 | 2/2 |
| `dpni_and_cleanup` | 2/2 | - | - | 2/2 |
| `drying_and_elution` | 1/1 | 1/1 | 1/1 | 1/1 |
| `elution_recovery` | 1/2 | 2/2 | 2/2 | 1/2 |
| `fidelity_to_paper` | 1/4 | 2/3 | 2/2 | 0/4 |
| `fidelity_to_task` | 6/7 | 6/6 | 5/6 | 7/7 |
| `heat_shock` | 2/2 | 2/2 | 1/1 | 2/2 |
| `master_mix` | 1/1 | 1/1 | 1/1 | 1/1 |
| `pcr_setup` | 2/2 | - | - | 2/2 |
| `reaction_setup` | 1/1 | 1/1 | 1/1 | 1/1 |
| `recovery` | 1/1 | 1/1 | 1/1 | 1/1 |
| `robot_practice` | 10/11 | 9/9 | 8/8 | 10/11 |
| `sample_handling` | 2/2 | 2/2 | 2/2 | 2/2 |
| `sample_mapping` | 1/1 | 1/1 | 1/1 | 1/1 |
| `soc_recovery` | 2/2 | 2/2 | 1/1 | 2/2 |
| `supernatant_and_washes` | 1/1 | 1/1 | 1/1 | 1/1 |
| `template_and_primers` | 1/1 | 1/1 | 1/1 | 1/1 |
| `thermocycling` | 2/2 | 2/2 | 2/2 | 2/2 |
| `tips_and_contamination` | 11/11 | 9/9 | 8/8 | 11/11 |
| `volumes_and_wells` | 2/2 | 2/2 | 2/2 | 2/2 |
| `washes_and_drying` | 2/2 | 2/2 | 2/2 | 2/2 |

Judge: openrouter anthropic/claude-sonnet-5.5 (x39)

## Every failure, with the ground-truth evidence

**colony-pcr-screening-hard · claude-fable-5.1** (reward 1.00)
- check `end_state:pcr_plate` failed: expected {'A1': 20.0, 'A2': 20.0, 'A3': 20.0, 'A4': 20.0, 'A5': 20.0, 'A6': 20.0, 'A7': 20.0, 'A8': 20.0, 'A9': 20.0, 'A10': 20.0, 'A11': 20.0, 'A12': 20.0, 'B1': 20.0, 'B2': 20.0, 'B3': 20.0, 'B4': 20.0, 'B5': 20.0, 'B6': 20.0, 'B7': 20.0, 'B8': 20.0, 'B9': 20.0, 'B10': 20.0, 'B11': 20.0, 'B12': 20

**colony-pcr-screening-hard · claude-opus-5.5** (reward 1.00)
- check `end_state:pcr_plate` failed: expected {'A1': 20.0, 'A2': 20.0, 'A3': 20.0, 'A4': 20.0, 'A5': 20.0, 'A6': 20.0, 'A7': 20.0, 'A8': 20.0, 'A9': 20.0, 'A10': 20.0, 'A11': 20.0, 'A12': 20.0, 'B1': 20.0, 'B2': 20.0, 'B3': 20.0, 'B4': 20.0, 'B5': 20.0, 'B6': 20.0, 'B7': 20.0, 'B8': 20.0, 'B9': 20.0, 'B10': 20.0, 'B11': 20.0, 'B12': 20

**colony-pcr-screening-hard · claude-sonnet-5.5** (reward 0.75)
- check `end_state:pcr_plate` failed: expected {'A1': 20.0, 'A2': 20.0, 'A3': 20.0, 'A4': 20.0, 'A5': 20.0, 'A6': 20.0, 'A7': 20.0, 'A8': 20.0, 'A9': 20.0, 'A10': 20.0, 'A11': 20.0, 'A12': 20.0, 'B1': 20.0, 'B2': 20.0, 'B3': 20.0, 'B4': 20.0, 'B5': 20.0, 'B6': 20.0, 'B7': 20.0, 'B8': 20.0, 'B9': 20.0, 'B10': 20.0, 'B11': 20.0, 'B12': 20
- judge 0 on `fidelity_to_paper` (votes [1, 0]): Thermocycling is only a comment with an annealing range (55-65 C) and 20-30 s/kb rather than a definite program. The 3 min initial denaturation and the assumed pre-diluted 4 uL primer are also unspecified adaptations.
- judge: 2 of 3 votes returned (network errors)

**colony-pcr-screening-hard · gpt-6.1-sol** (reward 0.50)
- check `end_state:pcr_plate` failed: expected {'A1': 20.0, 'A2': 20.0, 'A3': 20.0, 'A4': 20.0, 'A5': 20.0, 'A6': 20.0, 'A7': 20.0, 'A8': 20.0, 'A9': 20.0, 'A10': 20.0, 'A11': 20.0, 'A12': 20.0, 'B1': 20.0, 'B2': 20.0, 'B3': 20.0, 'B4': 20.0, 'B5': 20.0, 'B6': 20.0, 'B7': 20.0, 'B8': 20.0, 'B9': 20.0, 'B10': 20.0, 'B11': 20.0, 'B12': 20
- judge 0 on `robot_practice` (votes [0, 0, 0]): The protocol adds a needless manual well-by-well transfer of all 96 reactions to a different plate plus several pauses, extra handling that puts samples at risk. Otherwise, apiLevel 2.15 is valid and all volumes (1-5 uL) are handled by the p20.
- judge 0 on `fidelity_to_paper` (votes [0, 0, 0]): The protocol invents a manual transfer to a real PCR plate and extra pauses, and assumes a 1.25 uM primer concentration. The paper has no such steps, so it is not fully faithful.

**ecoli-heat-shock-transformation-hard · claude-fable-5.1** (reward 0.00)
- AgentSafetyRefusalError

**ecoli-heat-shock-transformation-hard · claude-opus-5.5** (reward 0.75)
- judge 0 on `fidelity_to_paper` (votes [0, 0, 0]): Adds steps the paper does not describe (p20.mix 3x5 µL on competent cells, p300.mix 3x30 µL, blow_outs) and an arbitrary 45 C lid setting, so it is not a fully faithful implementation.

**ecoli-heat-shock-transformation-hard · claude-sonnet-5.5** (reward 0.75)
- judge 0 on `fidelity_to_paper` (votes [0]): The code adds a mixing step (p20.mix(3, 5, ...)) that the paper does not describe and sets the lid to 42 C, an invented choice. It also has no return to 4 C between the shock and SOC addition.
- judge: 1 of 3 votes returned (network errors)

**ecoli-heat-shock-transformation-hard · gpt-6.1-sol** (reward 0.75)
- judge 0 on `fidelity_to_paper` (votes [0, 0, 0]): The agent added steps the paper does not specify: p20.mix(3,5) in the cells after DNA addition and p300.mix(3,40) after SOC. It also deactivated the lid during the 4 C and 42 C steps and heated it to 50 C only for recovery.

**golden-gate-assembly · claude-fable-5.1** (reward 0.00)
- AgentSafetyRefusalError

**golden-gate-assembly · claude-opus-5.5** (reward 0.00)
- AgentSafetyRefusalError

**golden-gate-assembly-hard · claude-fable-5.1** (reward 0.00)
- AgentSafetyRefusalError

**golden-gate-assembly-hard · claude-opus-5.5** (reward 0.00)
- AgentSafetyRefusalError

**golden-gate-assembly-hard · gpt-6.1-sol** (reward 0.75)
- check `end_state:pcr_plate` failed: expected {'A1': 48.0, 'B1': 38.0, 'C1': 48.0, 'D1': 48.0, 'E1': 42.0, 'F1': 38.0, 'G1': 48.0}, got {'A1': 49.0, 'B1': 39.0, 'C1': 49.0, 'D1': 49.0, 'E1': 43.0, 'F1': 39.0, 'G1': 49.0}
- judge 0 on `fidelity_to_paper` (votes [0, 0, 0]): The agent adds an invented 1 µL water 'replace QC aliquot' step before DpnI. The end_state:pcr_plate check fails (49 vs 48 µL expected), so the protocol is not fully faithful.

**opentrons-rna-extraction · claude-fable-5.1** (reward 0.75)
- judge 0 on `fidelity_to_task` (votes [0, 0, 0]): The module docstring and metadata credit the paper to 'Lopez-Fernandez et al.', but the authors are Lázaro-Perona et al., so the metadata is inaccurate. The code also adds an unspecified bead-resuspension mix (m300.mix(5,150,beads...)).

**opentrons-rna-extraction · claude-sonnet-5.5** (reward 0.30)
- check `reservoir_columns_within_15ml` failed: uL drawn per reservoir column: 2: 1920, 4: 4800, 6: 6000, 7: 6000, 9: 16000, 10: 16000, 11: 8000, 12: 8000
- judge 0 on `robot_practice` (votes [0, 0, 0]): Check reservoir_columns_within_15ml failed: etoh[i % 4] draws 16000 µL from columns 9 and 10 (nest 12-well ~15 mL), which exceeds the well capacity.
- judge 0 on `fidelity_to_task` (votes [1, 0, 0]): The ethanol allocation overdraws reservoir columns 9 and 10 (16000 µL each), so the run as coded cannot be carried out with the specified reservoir quantities.

**opentrons-rna-extraction-hard · claude-sonnet-5.5** (reward 0.69)
- judge 0 on `fidelity_to_paper` (votes [0, 0, 0]): Recovers 100 µL (p300m.aspirate(ELUTION_VOL...) in recovery loop) rather than ~80 µL, aspirating the full eluate near beads at 0.8 mm; also adds unspecified bead premix and elution mixing, so it is not fully faithful.
- judge 0 on `elution_recovery` (votes [0, 0, 0]): Elution 100 µL off-magnet with mix, 30 s, magnet 90 s are correct, but recovery aspirates and dispenses ELUTION_VOL=100 µL rather than about 80 µL.

**opentrons-rna-extraction-hard · gpt-6.1-sol** (reward 0.69)
- judge 0 on `fidelity_to_paper` (votes [0, 1, 0]): The eluate recovery aspirates and moves the full ELUTION_VOLUME (100 µL) from a well holding 100 µL, with the magnet engaged. The expected recovery is about 80 µL, so this deviates from the specification.
- judge 0 on `elution_recovery` (votes [0, 1, 0]): Recovery is the full 100 µL (aspirate ELUTION_VOLUME from source.bottom(z=0.5)), not about 80 µL. This risks drawing beads and does not match the expected recovery volume.

