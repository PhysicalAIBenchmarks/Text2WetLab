# Text2WetLab: benchmark analysis and expansion plan

## How tasks are classified

Every task gets three discrete labels instead of a numeric score.

- **Structure** is what the robot has to coordinate, read from the protocol:
  **S1** single transfer (one source to some wells) · **S2** plate set-up (several reagents added to the same wells) ·
  **S3** wash cycles (liquid added then removed again) · **S4** module-coordinated (pipetting interleaved with magnet,
  temperature or thermocycler steps and timed waits) · **S5** multi-reaction workflow (one reaction's product is the next reaction's input).
- **Specification** is what the model has to work out: **E** explicit (every step and volume given) ·
  **P** paper-assisted (steps given, paper fills gaps) · **D** paper-derived (the protocol must be extracted from the paper).
- **Observed** is how models did in Harbor (pass@1, 2026-10-04): solved by all · split · unsolved · not run.

A fourth, expert-labelled tag records why failures happen: **bench-ready**, **needs training** (bead handling, magnet timing),
or **needs domain judgement** (rules a paper does not state, such as not pipette-mixing competent cells).

Non-liquid-handling candidates have no pipetting structure, so they get a **family** instead: **PL** protocol program
(XDL, LabOP, Autoprotocol) · **IM** microscope acquisition · **BR** closed-loop culture control · **OR** workcell
orchestration and scheduling · **SD** self-driving lab campaign · **OT** other.

## 1. The 11 current tasks

| Task | Structure | Spec | Observed | Opus / Sonnet / Fable | Tag | Description |
|---|---|---|---|---|---|---|
| `split-200ul-two-wells` | S1 | E | Solved by all | 1 / 1 / 1 | Bench-ready | Calibration task: split one reservoir volume equally into two wells. Checks labware loading, pipette choice and a single transfer. |
| `a1-a12-100ul` | S1 | E | Solved by all | 1 / 1 / 1 | Bench-ready | Calibration task: dispense the same volume into every well of one plate row. Checks well addressing and repeated dispensing. |
| `ecoli-heat-shock-transformation` | S2 | E | Split | 0.8 / 1 / 1 | Domain judgement | Introduce a plasmid into competent E. coli in one tube and add recovery medium; the heat shock and incubation are operator steps. The pipetting is trivial; the catch is handling fragile cells gently. |
| `ecoli-heat-shock-transformation-hard` | S4 | D | Not run | – | Domain judgement | The same transformation for eight plasmids on the thermocycler module, with volumes and the temperature program taken from the APEX paper. |
| `colony-pcr-screening` | S2 | P | Solved by all | 1 / 1 / 1 | Bench-ready | Set up 96 colony PCR reactions to find which colonies carry the right plasmid: master mix, one colony and its primers per well, a fresh tip for every colony. |
| `colony-pcr-screening-hard` | S2 | D | Not run | – | Training | The same 96-well colony PCR with quantities and order worked out from the Slowpoke paper and adapted to the deck's reagents. |
| `ampure-bead-cleanup` | S3 | E | Solved by all | 1 / 1 / 1 | Training | Clean 96 PCR products with magnetic beads: bind, remove supernatant, two ethanol washes, dry, elute into a fresh plate. The largest task by robot actions. |
| `golden-gate-assembly` | S5 | P | Solved by all | 1 / 1 / 1 | Training | AssemblyTron's DNA assembly: PCR seven fragments, remove template, join fragments into four plasmids by Golden Gate, then transform. Each stage's product feeds the next. |
| `golden-gate-assembly-hard` | S5 | D | Not run | – | Training | The same AssemblyTron workflow with reaction quantities and fragment ratios derived from the paper. |
| `opentrons-rna-extraction` | S4 | P | Split | 0.6 / 0.4 / 0.8 | Domain judgement | Extract viral RNA from 48 samples with magnetic beads, washes and a chilled elution plate, using two pipettes and two modules. All models recovered more eluate than the method specifies; Sonnet also added samples before the beads. |
| `opentrons-rna-extraction-hard` | S4 | D | Not run | – | Domain judgement | The same extraction with volumes, order and timings taken from the paper. |

### Current tasks on the grid

| | E Explicit | P Paper-assisted | D Paper-derived |
|---|---|---|---|
| **S1** Single transfer | split ✅, a1-a12 ✅ | – | – |
| **S2** Plate set-up | heat shock ⚠️ | colony PCR ✅ | colony PCR hard ◻ |
| **S3** Wash cycles | AMPure ✅ | – | – |
| **S4** Module-coordinated | – | RNA extraction ⚠️ | RNA hard ◻, heat shock hard ◻ |
| **S5** Multi-reaction workflow | – | Golden Gate ✅ | Golden Gate hard ◻ |

✅ solved by all · ⚠️ split · ◻ not run. Every paper-derived task is unrun, and nothing at S1–S3 is paper-derived.
Failures come from domain judgement, not size: all models pass Golden Gate (S5) and AMPure (over 5,000 liquid moves).

## 2. The new candidates

All 210 new candidates are listed with a plain-English description in [`CANDIDATES.md`](CANDIDATES.md)
(also posted below as follow-up comments). Structure and family are assigned by the same keyword rules for every candidate,
so they are estimates until each task is built.

### New liquid-handling candidates by structure and readiness

| Structure | Ready | Partial | No usable code | Total |
|---|---|---|---|---|
| **S1** Single transfer | 1 | 3 | 2 | 6 |
| **S2** Plate set-up | 13 | 32 | 18 | 63 |
| **S3** Wash cycles | 4 | 9 | 1 | 14 |
| **S4** Module-coordinated | 1 | 2 | 4 | 7 |
| **S5** Multi-reaction workflow | 6 | 12 | 0 | 18 |

### New non-liquid-handling candidates by family and readiness

| Family | Ready | Partial | No usable code | Total |
|---|---|---|---|---|
| **PL** Protocol program (XDL, LabOP, Autoprotocol) | 5 | 5 | 0 | 10 |
| **IM** Microscope acquisition | 7 | 8 | 0 | 15 |
| **BR** Closed-loop culture control | 1 | 5 | 2 | 8 |
| **OR** Workcell orchestration / scheduling | 3 | 6 | 2 | 11 |
| **SD** Self-driving lab campaign | 3 | 14 | 4 | 21 |
| **OT** Other automation | 0 | 12 | 25 | 37 |

### Which specification levels the new candidates can support

| Specification | Candidates |
|---|---|
| P + D | 138 |
| D (needs a written oracle) | 51 |
| E only (no paper) | 21 |

Every candidate with both a paper and code (138) can become a paper-assisted **and** a paper-derived task, which fills the
empty D column above. The largest gains are in S2 plate set-ups (13 ready) and S5 multi-reaction workflows (6 ready);
S4 module-coordinated work stays thin (1 ready), so it needs hand-built tasks.

## 3. Where the models go wrong

A deterministic diff of each model's run log against the oracle's (`tools/fault_detect.py`, `fault_report.md`) agrees with the judge on every task:

| Task | Opus 5.5 | Sonnet 5.5 | Fable 5.1 |
|---|---|---|---|
| Heat shock | mixes the competent cells | clean | mixes the competent cells |
| RNA extraction | recovers 100 µL eluate (oracle 80) | samples before beads; 100 µL eluate; 5% extra waste removed | 100 µL eluate |

- **Judge inconsistency:** Opus and Fable do the same thing on heat shock but score 0.8 and 1.0. Make this a deterministic check.
- **The RNA oracle is the authors' script, not the task spec:** it waits longer and uses the magnet more than the task asks, and scores 0.6 itself.
- **The simulator does not track liquid**, so over-aspiration and harm to fragile cells pass simulation.

## 4. Size of the expanded benchmark

| Scenario | Tasks |
|---|---|
| Today | 11 |
| + 12 corpus papers that already have IR but no task | ~61 |
| + new ready candidates (2 tasks each) | ~149 |
| + all new paper + code candidates | ~340–410 |
| Theoretical ceiling (incl. partial, ACRA, AEGIS) | ~500–600 |

Simulator check (`VERIFIED.md`): of 128 protocol files in the 25 ready liquid-handling repos, 30 pass `opentrons_simulate` unchanged (10 repos).
The 98 failures are setup issues: labware files on the author's disk (43), newer API (24), extra packages (15), missing inputs (5), other (11).

## 5. Recommendations

1. Run the four `-hard` variants in Harbor; they fill the D column and are the most demanding tasks.
2. Turn domain-rule judge items (gentle cell handling, elution volume) into deterministic checks; add a spec oracle for RNA extraction.
3. Build next from the 12 corpus papers with IR and the 10 repos that already simulate, prioritising D variants at S1–S3.
4. Re-run verification with labware vendored and a newer Opentrons release.
5. Add new grader families only where hardware-free execution exists: PL (Cronin ACRA, 100+ executed literature→XDL pairs), IM, OR.
