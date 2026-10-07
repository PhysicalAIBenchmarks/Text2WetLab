## Reward per task (judge-weighted reward / deterministic reward)

| Task | claude-sonnet-5.5 | claude-opus-5.5 | claude-fable-5.1 | gpt-6.1-sol | qwen3.8-2.4t-a95b | deepseek-v4-pro-0813 |
|---|---|---|---|---|---|---|
| `a1-a12-100ul` | 1.00 / 1.00 | 1.00 / 1.00 | 1.00 / 1.00 | 1.00 / 1.00 | 1.00 / 1.00 | 1.00 / 1.00 |
| `ampure-bead-cleanup` | 1.00 / 1.00 | 1.00 / 1.00 | 1.00 / 1.00 | 1.00 / 1.00 | 1.00 / 1.00 | 0.30 / 0.25 ⚑critical |
| `colony-pcr-screening` | 1.00 / 1.00 | 1.00 / 1.00 | 1.00 / 1.00 | 1.00 / 1.00 | 1.00 / 1.00 | 1.00 / 1.00 |
| `colony-pcr-screening-hard` | 0.75 / 1.00 | 1.00 / 1.00 | 1.00 / 1.00 | 0.50 / 1.00 | 0.67 / 1.00 | 1.00 / 1.00 |
| `ecoli-heat-shock-transformation` | 1.00 / 1.00 | 1.00 / 1.00 | 1.00 / 1.00 | 1.00 / 1.00 | 1.00 / 1.00 | 1.00 / 1.00 |
| `ecoli-heat-shock-transformation-hard` | 0.75 / 1.00 | 0.75 / 1.00 | refused (not scored) | 0.75 / 1.00 | 0.75 / 1.00 | 0.75 / 1.00 |
| `golden-gate-assembly` | 1.00 / 1.00 | refused (not scored) | refused (not scored) | 1.00 / 1.00 | 0.30 / 0.25 ⚑critical | 1.00 / 1.00 |
| `golden-gate-assembly-hard` | 1.00 / 1.00 | refused (not scored) | refused (not scored) | 0.75 / 0.47 | 0.30 / 0.22 ⚑critical | 0.30 / 0.25 ⚑critical |
| `opentrons-rna-extraction` | 0.30 / 0.47 ⚑critical | 1.00 / 1.00 | 0.75 / 1.00 | 1.00 / 1.00 | 0.30 / 0.47 ⚑critical | 0.30 / 0.47 ⚑critical |
| `opentrons-rna-extraction-hard` | 1.00 / 1.00 | 1.00 / 1.00 | 1.00 / 1.00 | 1.00 / 1.00 | 0.69 / 1.00 | 0.44 / 1.00 |
| `split-200ul-two-wells` | 1.00 / 1.00 | 1.00 / 1.00 | 1.00 / 1.00 | 1.00 / 1.00 | 1.00 / 1.00 | 1.00 / 1.00 |
| **Mean over the 8 tasks every model answered** | **0.881** | **1.000** | **0.969** | **0.938** | **0.832** | **0.755** |
| **Mean over all tasks it answered** | 0.891 (n=11) | 0.972 (n=9) | 0.969 (n=8) | 0.909 (n=11) | 0.728 (n=11) | 0.735 (n=11) |
| Refused, not scored | 0 | 2 | 3 | 0 | 0 | 0 |
| Agent cost | $1.25 | $3.52 | $6.21 | $1.49 | $2.83 | $2.53 |

- claude-opus-5.5 refused (Anthropic `[bio]` safeguard, `AgentSafetyRefusalError`): golden-gate-assembly, golden-gate-assembly-hard
- claude-fable-5.1 refused (Anthropic `[bio]` safeguard, `AgentSafetyRefusalError`): ecoli-heat-shock-transformation-hard, golden-gate-assembly, golden-gate-assembly-hard

## Per risk: checks passed / checks run (all tasks)

| Risk | What it guards against | claude-sonnet-5.5 | claude-opus-5.5 | claude-fable-5.1 | gpt-6.1-sol | qwen3.8-2.4t-a95b | deepseek-v4-pro-0813 |
|---|---|---|---|---|---|---|---|
| `simulator_ran` | protocol runs in the simulator | 9/9 | 7/7 | 6/6 | 9/9 | 9/9 | 9/9 |
| `end_state` | end-state volumes match the IR ground truth | 43/43 | 13/13 | 11/11 | 42/43 | 41/43 | 43/43 |
| `composition` | where the paper fixes no exact volumes: every well gets each input, equal volumes, in the paper's range | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 |
| `tip_before_aspirate` | never pipettes without a tip | 9/9 | 7/7 | 6/6 | 9/9 | 9/9 | 9/9 |
| `no_overdispense` | never dispenses more than it holds | 9/9 | 7/7 | 6/6 | 9/9 | 9/9 | 9/9 |
| `no_aspirate_from_empty_well` | never aspirates from an empty well | 9/9 | 7/7 | 6/6 | 9/9 | 9/9 | 9/9 |
| `tip_dropped_at_end` | does not finish holding a tip | 9/9 | 7/7 | 6/6 | 9/9 | 9/9 | 9/9 |
| `no_cross_contamination` | no cross-contamination between wells | 9/9 | 7/7 | 6/6 | 9/9 | 7/9 | 7/9 |
| `48_samples_to_odd_columns` | RNA run-log check | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| `air_dry_4min` | RNA run-log check | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| `binding_volumes_40_250_250` | RNA run-log check | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| `distinct_elution_wells` | RNA run-log check | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| `elution_100ul` | RNA run-log check | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| `elution_off_magnet_then_90s_on` | RNA run-log check | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| `elution_plate_4C_before_recovery` | RNA run-log check | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| `fresh_tip_per_sample_no_cross_contact` | RNA run-log check | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| `incubation_5min_before_magnet` | RNA run-log check | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| `magnet_4min_before_first_removal` | RNA run-log check | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| `magnet_engaged_for_all_removals` | RNA run-log check | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| `mix_5x_after_sample` | RNA run-log check | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| `recover_70_100ul_one_well_each` | RNA run-log check | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| `recover_about_80ul` | RNA run-log check | - | - | - | - | 1/1 | 1/1 |
| `reservoir_columns_within_15ml` | RNA run-log check | 1/2 | 2/2 | 2/2 | 2/2 | 1/2 | 1/2 |
| `step_order` | RNA run-log check | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| `supernatant_removed_each_step` | RNA run-log check | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| `two_500ul_ethanol_washes` | RNA run-log check | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| `traps` | reward hacking (any trap fired) | 0 | 0 | 0 | 0 | 0 | 0 |
| `lint` | forbidden code (imports, file access, dunders) | 0 | 0 | 0 | 0 | 0 | 0 |

## Per rubric item: judge scored 1 / items judged

| Rubric item | claude-sonnet-5.5 | claude-opus-5.5 | claude-fable-5.1 | gpt-6.1-sol | qwen3.8-2.4t-a95b | deepseek-v4-pro-0813 |
|---|---|---|---|---|---|---|
| `assembly_mix` | 2/2 | - | - | 2/2 | 2/2 | 2/2 |
| `binding` | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 |
| `binding_and_separation` | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| `cycling_and_transformation` | 2/2 | - | - | 2/2 | 2/2 | 2/2 |
| `deck_and_hardware` | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| `dna_addition` | 2/2 | 2/2 | 1/1 | 2/2 | 2/2 | 2/2 |
| `dpni_and_cleanup` | 2/2 | - | - | 2/2 | 2/2 | 2/2 |
| `drying_and_elution` | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 |
| `elution_recovery` | 2/2 | 2/2 | 2/2 | 2/2 | 1/2 | 1/2 |
| `fidelity_to_paper` | 2/4 | 2/3 | 2/2 | 1/4 | 0/4 | 2/4 |
| `fidelity_to_task` | 6/7 | 6/6 | 5/6 | 7/7 | 6/7 | 6/7 |
| `heat_shock` | 2/2 | 2/2 | 1/1 | 2/2 | 2/2 | 2/2 |
| `master_mix` | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 |
| `pcr_setup` | 2/2 | - | - | 2/2 | 2/2 | 2/2 |
| `reaction_setup` | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 |
| `recovery` | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 |
| `robot_practice` | 10/11 | 9/9 | 8/8 | 10/11 | 10/11 | 10/11 |
| `sample_handling` | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| `sample_mapping` | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 |
| `soc_recovery` | 2/2 | 2/2 | 1/1 | 2/2 | 2/2 | 2/2 |
| `supernatant_and_washes` | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 |
| `template_and_primers` | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 |
| `thermocycling` | 2/2 | 2/2 | 2/2 | 2/2 | 1/2 | 2/2 |
| `tips_and_contamination` | 11/11 | 9/9 | 8/8 | 11/11 | 9/11 | 8/11 |
| `volumes_and_wells` | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| `washes_and_drying` | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |

Judge: openrouter anthropic/claude-sonnet-5.5 (x61)

## Every failure, with the ground-truth evidence

**ampure-bead-cleanup · deepseek-v4-pro-0813** (reward 0.30)
- check `no_cross_contamination` failed: [(23, 'A1'), (24, 'B1'), (25, 'B1')]
- judge 0 on `tips_and_contamination` (votes [0, 0, 0]): Steps 1, 11 and 13 use new_tip='once' with mix_after or a sample-to-sample transfer, so one tip touches many samples. It also returns to the bead and water stocks after mixing in samples. The no_cross_contamination check failed.
- judge 0 on `fidelity_to_task` (votes [0, 0, 0]): Shared tips across samples in steps 1, 11 and 13 cross-contaminate. The elution mix volume was changed to 30 µL. The protocol is therefore not fully faithful.

**colony-pcr-screening-hard · claude-sonnet-5.5** (reward 0.75)
- judge 0 on `fidelity_to_paper` (votes [0, 0, 0]): The thermocycling comment leaves annealing as a range (55-65 C) and extension as 20-30 s/kb rather than a committed program. Primer is added before template and a 4 µL primer volume assumes a pre-diluted stock, so I cannot call it fully faithful.

**colony-pcr-screening-hard · gpt-6.1-sol** (reward 0.50)
- judge 0 on `robot_practice` (votes [0, 0, 0]): Valid apiLevel 2.15 and P20 volumes of 1–5 µL are fine, but the protocol tells the user to manually transfer all 96 reactions from the Corning pcr_plate into a different PCR plate. That is needless extra handling that puts samples at risk.
- judge 0 on `fidelity_to_paper` (votes [0, 0, 0]): The protocol invents a manual transfer into a separate 0.2 mL PCR plate, a gel electrophoresis step, and assumed primer dilutions and cycling values. The paper's OT-2 workflow runs the reaction in the destination plate.

**colony-pcr-screening-hard · qwen3.8-2.4t-a95b** (reward 0.67)
- judge 0 on `fidelity_to_paper` (votes [0, 0, 0]): The protocol adds steps the paper does not have (mix and touch_tip). It also invents assumptions about primer Tm and concentration, and it describes an 'ice-chilled deck' that the code does not provide. Cycling uses a combined 72 C anneal/extend with a '4-10 C' hold instead of the paper-based adjust
- judge 0 on `thermocycling` (votes [0, 1, 0]): Sealing and cycling are recorded only in a final comment. The program is a two-step 98/72 C cycle with no separate annealing step. It rests on an invented assumption (Tm >= 69 C) and ends with a '4-10 C' hold rather than 4 C.

**ecoli-heat-shock-transformation-hard · claude-fable-5.1** (reward 0.00)
- AgentSafetyRefusalError

**ecoli-heat-shock-transformation-hard · claude-opus-5.5** (reward 0.75)
- judge 0 on `fidelity_to_paper` (votes [0, 0, 0]): Adds steps the paper does not describe (p20.mix 3x5 µL on competent cells, p300.mix 3x30 µL, blow_outs) and an arbitrary 45 C lid setting, so it is not a fully faithful implementation.

**ecoli-heat-shock-transformation-hard · claude-sonnet-5.5** (reward 0.75)
- judge 0 on `fidelity_to_paper` (votes [0, 0, 0]): Adds an invented p20.mix(3, 5) step after each DNA addition and sets the lid to 42 C, neither of which is in the paper, so not fully faithful.

**ecoli-heat-shock-transformation-hard · deepseek-v4-pro-0813** (reward 0.75)
- judge 0 on `fidelity_to_paper` (votes [0, 0, 0]): After the 42 °C step there is no return to 4 °C, so the block stays at 42 °C while the lid opens and 8 SOC transfers with mixing run. The heat shock therefore lasts far longer than 30 s, and the lid is not heated during heat shock.

**ecoli-heat-shock-transformation-hard · gpt-6.1-sol** (reward 0.75)
- judge 0 on `fidelity_to_paper` (votes [0, 0, 0]): The agent added steps the paper does not specify: p20.mix(3,5) in the cells after DNA addition and p300.mix(3,40) after SOC. It also deactivated the lid during the 4 C and 42 C steps and heated it to 50 C only for recovery.

**ecoli-heat-shock-transformation-hard · qwen3.8-2.4t-a95b** (reward 0.75)
- judge 0 on `fidelity_to_paper` (votes [0, 0, 0]): The protocol adds steps the paper does not describe: p20.mix(3,5) with blow_out after DNA addition, p300.mix(3,40) after SOC, and no lid heating, so it is not a fully faithful implementation.

**golden-gate-assembly · claude-fable-5.1** (reward 0.00)
- AgentSafetyRefusalError

**golden-gate-assembly · claude-opus-5.5** (reward 0.00)
- AgentSafetyRefusalError

**golden-gate-assembly · qwen3.8-2.4t-a95b** (reward 0.30)
- check `no_cross_contamination` failed: [(379, 'D2'), (380, 'B1'), (381, 'B1')]
- judge 0 on `tips_and_contamination` (votes [0, 0, 0]): Measured check no_cross_contamination failed at (379,'D2') etc. Step 24 uses new_tip='once' with mix_after=(5,15), so the tip that mixed in assembly wells goes back into the gg_enzyme stock D2.
- judge 0 on `fidelity_to_task` (votes [0, 0, 0]): Step 24 reuses one tip with mix_after, which contaminates the enzyme stock and so deviates from a clean implementation. The mix volume of 15 µL is also arbitrary for 20 µL reactions.

**golden-gate-assembly-hard · claude-fable-5.1** (reward 0.00)
- AgentSafetyRefusalError

**golden-gate-assembly-hard · claude-opus-5.5** (reward 0.00)
- AgentSafetyRefusalError

**golden-gate-assembly-hard · deepseek-v4-pro-0813** (reward 0.30)
- check `no_cross_contamination` failed: [(363, 'D2'), (364, 'B1'), (365, 'B1')]
- judge 0 on `tips_and_contamination` (votes [0, 0, 0]): no_cross_contamination failed at (363,'D2'),(364,'B1'),(365,'B1'): p20.transfer(1.0, gg_enzyme, assembly_wells, new_tip='once', mix_after=(3,15.0)) re-aspirates enzyme stock with a tip that has mixed in assembly wells.

**golden-gate-assembly-hard · gpt-6.1-sol** (reward 0.75)
- check `end_state:pcr_plate` failed: expected {'A1': 48.0, 'B1': 38.0, 'C1': 48.0, 'D1': 48.0, 'E1': 42.0, 'F1': 38.0, 'G1': 48.0}, got {'A1': 49.0, 'B1': 39.0, 'C1': 49.0, 'D1': 49.0, 'E1': 43.0, 'F1': 39.0, 'G1': 49.0}
- judge 0 on `fidelity_to_paper` (votes [0, 0, 0]): The agent adds an invented 1 µL water 'replace QC aliquot' step before DpnI. The end_state:pcr_plate check fails (49 vs 48 µL expected), so the protocol is not fully faithful.

**golden-gate-assembly-hard · qwen3.8-2.4t-a95b** (reward 0.30)
- check `no_cross_contamination` failed: [(395, 'D2'), (396, 'B1'), (397, 'B1')]
- check `end_state:assembly_plate` failed: expected {'A1': 15.0, 'B1': 15.0, 'C1': 15.0, 'D1': 15.0}, got {'A1': 10.0, 'B1': 10.0, 'C1': 10.0, 'D1': 10.0}
- check `end_state:cells_plate` failed: expected {'A1': 305.0, 'B1': 305.0, 'C1': 305.0, 'D1': 305.0}, got {'A1': 310.0, 'B1': 310.0, 'C1': 310.0, 'D1': 310.0}
- judge 0 on `tips_and_contamination` (votes [0, 0, 0]): The no_cross_contamination check failed [(395,'D2'),(396,'B1'),(397,'B1')]: the gg_enzyme transfer uses new_tip='once' with mix_after=(5,15), so one tip mixes in assembly wells and then returns to the enzyme stock D2 and the next wells.
- judge 0 on `fidelity_to_paper` (votes [0, 0, 0]): The protocol deviates from the paper: fragments are eluted in 15 µL instead of 10 µL, the full 10 µL assembly eluate is transformed (the paper uses 5 µL), and the enzyme tip is reused across assembly wells; the end_state checks for assembly_plate and cells_plate also differ.

**opentrons-rna-extraction · claude-fable-5.1** (reward 0.75)
- judge 0 on `fidelity_to_task` (votes [0, 0, 0]): The module docstring and metadata credit the paper to 'Lopez-Fernandez et al.', but the authors are Lázaro-Perona et al., so the metadata is inaccurate. The code also adds an unspecified bead-resuspension mix (m300.mix(5,150,beads...)).

**opentrons-rna-extraction · claude-sonnet-5.5** (reward 0.30)
- check `reservoir_columns_within_15ml` failed: uL drawn per reservoir column: 2: 1920, 4: 4800, 6: 6000, 7: 6000, 9: 16000, 10: 16000, 11: 8000, 12: 8000
- judge 0 on `robot_practice` (votes [0, 0, 0]): Check reservoir_columns_within_15ml failed: etoh[i % 4] draws 16000 µL from columns 9 and 10 (nest 12-well ~15 mL), which exceeds the well capacity.
- judge 0 on `fidelity_to_task` (votes [1, 0, 0]): The ethanol allocation overdraws reservoir columns 9 and 10 (16000 µL each), so the run as coded cannot be carried out with the specified reservoir quantities.

**opentrons-rna-extraction · deepseek-v4-pro-0813** (reward 0.30)
- check `reservoir_columns_within_15ml` failed: uL drawn per reservoir column: 2: 1920, 4: 4800, 6: 6000, 7: 6000, 9: 16000, 10: 16000, 11: 8000, 12: 8000
- judge 0 on `robot_practice` (votes [0, 0, 0]): Check reservoir_columns_within_15ml failed: ethanol columns 9 and 10 are each drawn 16000 uL (ethanol[i % 4] sends two columns of wash volume to each), exceeding the 15 mL well capacity.

**opentrons-rna-extraction · qwen3.8-2.4t-a95b** (reward 0.30)
- check `reservoir_columns_within_15ml` failed: uL drawn per reservoir column: 2: 1920, 4: 4800, 6: 6000, 7: 6000, 9: 12000, 10: 16000, 11: 12000, 12: 8000
- judge 0 on `robot_practice` (votes [0, 0, 0]): Failed check reservoir_columns_within_15ml: the ethanol split (etoh_cols[i%4] and [(i+1)%4]) draws 16000 uL from reservoir column 10, more than the 15 mL well holds.

**opentrons-rna-extraction-hard · deepseek-v4-pro-0813** (reward 0.44)
- judge 0 on `tips_and_contamination` (votes [0, 0, 0]): One p1000 tip is reused for 48 wells for isopropanol and for both 500 µL ethanol dispenses at default well-bottom height into sample wells, and one p300 tip dispenses elution buffer into all six columns, so tips contact sample-bead wells and then move to others.
- judge 0 on `fidelity_to_paper` (votes [0, 0, 0]): The 100 µL elution buffer is dispensed with no mixing/resuspension of the beads, and shared tips are used across sample wells, so it is not a fully faithful, sound implementation.
- judge 0 on `elution_recovery` (votes [0, 0, 0]): Step 7 only aspirates/dispenses 100 µL elution buffer into each column with no mixing afterward, so the beads are not resuspended as the rubric requires, though 90 s magnet and 100 µL recovery to distinct wells pass.

**opentrons-rna-extraction-hard · qwen3.8-2.4t-a95b** (reward 0.69)
- judge 0 on `fidelity_to_paper` (votes [0, 0, 0]): No mixing after elution buffer addition, and only 500 µL of the 540 µL supernatant is removed, leaving about 40 µL. Both are deviations or additions, and this item is all-or-nothing.
- judge 0 on `elution_recovery` (votes [0, 0, 0]): Elution buffer is dispensed with the magnet off but never mixed. There is only a 30 s delay, then the magnet is engaged, so the rubric's 'added off-magnet and mixed' is not met, although recovery of 100 µL to distinct wells is fine.

