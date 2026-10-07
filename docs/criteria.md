# Evaluation criteria

What is judged, by which code, on which tasks, and how well it works. Everything below was measured:
`python scripts/criteria_matrix.py` regenerates the tables (needs the Opentrons 7.5.0 / Python 3.10 stack,
see the README). Nothing here depends on an LLM except the one item marked as not run.

## The criteria sets

| Set | Code | Judges | Applies to |
|---|---|---|---|
| Simulator gate | `eval/spec_check.py` -> `simulator_ran` | the protocol runs on Opentrons 7.5.0 at all (real tip, volume and labware errors) | any protocol |
| Generic rules | `eval/spec_check.py` | tip before aspirate, no overdispense, no draw from an empty non-stock well, tip dropped at the end | any protocol with an IR |
| End state | `eval/spec_check.py` + `paper2protocol/timeline.py` | every mapped container holds what the IR says when the run ends | tasks whose containers map to unique labware (3 of 7 today: `split-200ul-two-wells`, `a1-a12-100ul`, `ecoli-heat-shock-transformation`) |
| Harbor checks | `tasks/opentrons-rna-extraction/harbor/tests/checks.py` | 16 measured facts about the RNA extraction (volumes, order, timings, magnet, temperature, tips) plus a 0.3 reward cap if a critical one fails | that task |
| Harbor LLM judge | `tests/grade.py` | 9 rubric items scored 0 / 0.5 / 1 by a model | that task. **Not run in this repo** (needs an API key) |
| IR bookkeeping | `paper2protocol/check.py` | the IR itself: volumes drawn exist, wells fit capacity, pairing is valid | every IR |
| IR review | `paper2protocol/critic.py`, `resolve.py` | the IR against the paper text; whether the paper has enough detail | pipeline outputs |
| Viewer tracking | `eval/ir_mujoco.py` | tip load, tip height against labware rims (collision), fullest container, running issue count | any IR, visual only, not a gate |

An earlier set of six hard-coded criteria (T1-T6) judged one task, "aspirate 200 uL once, dispense 100 uL twice".
It is deleted. Section 2 shows why.

## 1. Spec acceptance criteria (docs/agent-spec.md): what is implemented

| # | Criterion | Status | By |
|---|---|---|---|
| AC1 | pick up a tip before aspirating | **done** | `tip_before_aspirate`, and the simulator itself |
| AC2 | aspirate more liquid after dispensing | **done indirectly** | `end_state` and `no_overdispense`: a protocol that does not re-aspirate cannot fill 12 wells |
| AC3 | aspirate enough for several dispenses | **not separately checked** | only visible through the end state |
| AC4 | drop the tip when finished | **done** | `tip_dropped_at_end` |
| AC5 | does not crash | **partly** | `simulator_ran`. The geometric z-height check exists only in the viewer |
| AC6 | lifts before moving (force a collision and see an error) | **not on traces** | Opentrons' motion planner always lifts. The viewer's `--no-lift` shows the check firing (11 collision frames on the 1-step task) but it judges nothing |
| AC7 | no cross-contamination | **one task only** | Harbor's `fresh_tip_per_sample_no_cross_contact` tracks what each tip touched. There is no generic version |

## 2. Does it judge correctly? 21 deliberately broken or alternative protocols

Each protocol was simulated on Opentrons 7.5.0 and judged. Ground truth: is it a correct solution to the
instruction? "Legacy" is the deleted T1-T6 set plus WetLabEnv's generic errors.

| Task | Protocols | Legacy misjudged | `spec_check` misjudged |
|---|---:|---:|---:|
| `split-200ul-two-wells` | 11 | 3 | **0** |
| `a1-a12-100ul` | 10 | 4 | **0** |

What legacy got wrong, and why:

| Protocol | Truth | Legacy | Reason |
|---|---|---|---|
| `transfer()` instead of aspirate/dispense | valid | rejected | T2 demanded one aspirate of exactly 200 uL |
| `distribute()` | valid | rejected | same: it aspirates extra disposal volume |
| both 100 uL into the **same** well | invalid | **accepted** | T3 only summed volume across the plate |
| A1-A12 task: fills row B, only 11 wells, 50 uL wells, never drops the tip | invalid | **accepted (4 of 4)** | no criterion applied beyond tip and overdispense |

`spec_check` first misjudged one protocol: `distribute()` on a P300 was rejected for exceeding pipette capacity,
because the log has no blow-out event and the replayed tip never emptied. Capacity is the simulator's job (an
over-capacity aspirate crashes it), so that check was deleted instead of patched.

How each fault was caught (all by `spec_check`):

| Fault | Caught by |
|---|---|
| no tip pickup, aspirate above pipette max | `simulator_ran` (the simulator rejects it) |
| tip never dropped | `tip_dropped_at_end` |
| dispense more than the tip holds | `no_overdispense` |
| draw from an empty plate well | `no_aspirate_from_empty_well` |
| both halves into one well, wrong row, 11 wells, 50 uL | `end_state:plate` |

Valid alternatives that pass: two different wells (the instruction never names them, so `task.toml` sets
`free_wells = ["plate"]`), `transfer()`, `distribute()`, 150 uL re-aspirations, extra mix and touch-tip.

## 3. Harbor RNA extraction: do the 16 checks notice what they claim to?

Nine variants of the authors' script, each with one fault, simulated and scored by `checks.py`:

| Variant | Passed | Failed check | Critical (reward capped at 0.3) |
|---|---:|---|---|
| baseline | 16/16 | | |
| incubation 5 -> 1 min | 15 | `incubation_5min_before_magnet` | |
| magnet separation 4 -> 1 min | 15 | `magnet_4min_before_first_removal` | |
| first magnet never engaged | 13 | incubation, separation, `magnet_engaged_for_all_removals` | |
| elution plate at 25 C | 15 | `elution_plate_4C_before_recovery` | |
| air-dry 4 min -> 5 s | 15 | `air_dry_4min` | |
| ethanol wash 167 -> 67 uL | 15 | `two_500ul_ethanol_washes` | yes |
| one tip for all 48 samples | 15 | `fresh_tip_per_sample_no_cross_contact` | yes |
| supernatant removal 175 -> 70 uL | 15 | `supernatant_removed_each_step` | yes |

Every injected fault was caught by the check named for it, and the three that should hit the cap do.
One of my own early mutants "passed" 16/16 because I had edited the wrong line (the staggered elution delay,
not the air-dry): the check was right and my fault was not a fault. Not tested: the mixing check
(`mix_5x_after_sample`), the volume checks for beads, isopropanol and sample, `48_samples_to_odd_columns`,
and the 9-item LLM judge.

The Harbor solution and the authors' script produce identical simulator traces (1,895 commands each), because
`solution/protocol.py` is the authors' script re-saved.

## 4. Pipeline-side criteria (12 outputs, 514 steps)

| Measure | Result |
|---|---|
| IR bookkeeping (`check.py`) | errors in 4 of 12 outputs: 5 and 5 (antibiotics exp 1, 2: wells above deep-plate capacity), 1 and 1 (antibiotics exp 3, DNA-BOT exp 1) |
| Critic verdict | 9 major issues, 3 minor |
| Sufficiency verdict | 11 proceed-with-assumptions, 1 reject (DNA-BOT exp 1) |
| Steps marked `assumed` | 70% |
| Manual (non-pipetting) steps | 18% |

An IR where 70% of steps rest on an assumption can pass bookkeeping and still be a poor specification.
`checks.py`-style measured checks only exist for the one task with a hidden grader.

## 5. Which tasks can be judged today

| Task | Simulator + generic rules | End state | Hidden grader |
|---|---|---|---|
| `split-200ul-two-wells`, `a1-a12-100ul` | yes | yes | `spec_check` |
| `ampure-bead-cleanup`, `colony-pcr-screening`, `golden-gate-assembly` | yes (generic only) | **no**: several plates (or tubes) of one kind, so the labware match is ambiguous and the check reports "not applicable" | none, and no reference solution to run |
| `ecoli-heat-shock-transformation` | yes | would map (one plate, one tube rack, one reservoir) | none, and no reference solution to run |
| `opentrons-rna-extraction` | yes | n/a | 16 checks + LLM judge |

Real scripts that simulate here: the authors' HULP script (the RNA task's oracle) and the two Slowpoke OT-2 workflows
(`sources/slowpoke/code/`, MIT) once their shipped CSV inputs are bound. None of them has the numbers of a handwritten task:
Slowpoke colony PCR is 9 uL mix + 1 uL colony per 10 uL reaction (the task says 18 + 1 + 1), and Slowpoke cloning is a
different Golden Gate design from the AssemblyTron paper. Scripts that do not simulate: DNA-BOT (5) needs the removed
Opentrons API v1, BOTany (8) needs API 2.20 and a runtime CSV, TransporterScreening (2) needs a labware definition that
is not in the repo.

## Known limits

- The end-state check needs each IR container to map to one run labware. To judge multi-plate tasks, a task has
  to publish its deck (slots and labware) and `task.toml` needs a `[deck]` table. The one-line instructions do not.
- Replay does not see blow-outs, mixes or air gaps, so it cannot track how much liquid the tip holds.
- Liquid identity is not tracked outside Harbor, so there is no generic contamination check (AC7).
- Only two tasks have been judged by `spec_check`, over 21 protocols. The generalisation to others is untested.
