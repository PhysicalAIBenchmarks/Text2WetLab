# Text2WetLab: benchmark analysis and expansion plan

## 1. Task breakdown

Counts come from each task's `ir.json` / `deck.json` and from simulating its reference protocol with `opentrons_simulate` (Opentrons 7.5.0).
"Robot liquid ops" = aspirate + dispense commands in the oracle's run log. Scores are the Harbor pass@1 results from 2026-10-04 (hard variants have not been run).

| Task | What it does | Source | Steps (manual) | Reagents | Labware / modules | Robot liquid ops | Tips | Spec | Opus / Sonnet / Fable |
|---|---|---|---|---|---|---|---|---|---|
| `a1-a12-100ul` | Dispense 100 µL into a row of 12 wells | handwritten | 1 (0) | 1 | 2 / 0 | 24 | 1 | explicit steps | 1 / 1 / 1 |
| `ampure-bead-cleanup` | 0.8× AMPure bead clean-up of 96 PCR products | handwritten | 13 (5) | 4 | 6 / 0 | 5,376 | 388 | explicit steps | 1 / 1 / 1 |
| `colony-pcr-screening` | Set up 96 colony PCRs (Q5) | handwritten | 4 (1) | 3 | 4 / 0 | 1,152 | 193 | explicit steps + paper | 1 / 1 / 1 |
| `colony-pcr-screening-hard` | Colony PCR, steps derived from the Slowpoke paper | handwritten | 4 (1) | 3 | 4 / 0 | 1,152 | 193 | derive from paper | not run |
| `ecoli-heat-shock-transformation` | Heat-shock transformation, one tube | handwritten | 4 (2) | 3 | 3 / 0 | 4 | 2 | explicit steps | 0.8 / 1 / 1 |
| `ecoli-heat-shock-transformation-hard` | APEX transformation of 8 plasmids on the thermocycler | paper | 4 (2) | 3 | 3 / 1 | 32 | 16 | derive from paper | not run |
| `golden-gate-assembly` | AssemblyTron: PCR → DpnI → Golden Gate → transform (4 plasmids) | paper2protocol | 33 (10) | 16 | 8 / 0 | 312 | 59 | explicit steps + paper | 1 / 1 / 1 |
| `golden-gate-assembly-hard` | AssemblyTron, quantities derived from the paper | paper2protocol | 33 (10) | 16 | 8 / 0 | 312 | 62 | derive from paper | not run |
| `opentrons-rna-extraction` | Magnetic-bead SARS-CoV-2 RNA extraction, 48 samples | paper | 14 (6) | 5 | 8 / 2 + 8-ch | 1,056 | 280 | explicit steps + paper | 0.6 / 0.4 / 0.8 |
| `opentrons-rna-extraction-hard` | RNA extraction, volumes/timings derived from the paper | paper | 14 (6) | 5 | 8 / 2 + 8-ch | 1,056 | 280 | derive from paper | not run |
| `split-200ul-two-wells` | Split 200 µL into two wells | handwritten | 1 (0) | 1 | 2 / 0 | 4 | 1 | explicit steps | 1 / 1 / 1 |

## 2. Experiment complexity

Each task is rated 1–5 on five axes; reasoning counts double because it is what the benchmark is meant to test.

| Axis | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|
| Scale (robot liquid ops) | ≤10 | ≤100 | ≤500 | ≤2,000 | >2,000 |
| Depth (protocol steps) | 1 | ≤4 | ≤10 | ≤20 | >20 |
| Deck & hardware (labware + 2×modules + 2 if 8-channel) | ≤2 | ≤4 | ≤6 | ≤9 | >9 |
| Reagent diversity | 1 | ≤3 | ≤5 | ≤10 | >10 |
| Reasoning | explicit steps | steps + paper fills gaps | — | most quantities from the paper | whole workflow from the paper |

| Task | Scale | Depth | Deck & hardware | Reagents | Reasoning (×2) | **Overall (1–5)** | Rating |
|---|---|---|---|---|---|---|---|
| `split-200ul-two-wells` | 1 | 1 | 1 | 1 | 1 | **1.0** | Trivial |
| `a1-a12-100ul` | 2 | 1 | 1 | 1 | 1 | **1.2** | Trivial |
| `ecoli-heat-shock-transformation` | 1 | 2 | 2 | 2 | 1 | **1.5** | Simple |
| `colony-pcr-screening` | 4 | 2 | 2 | 2 | 2 | **2.3** | Simple |
| `ampure-bead-cleanup` | 5 | 4 | 3 | 3 | 1 | **2.8** | Moderate |
| `ecoli-heat-shock-transformation-hard` | 2 | 2 | 3 | 2 | 4 | **2.8** | Moderate |
| `colony-pcr-screening-hard` | 4 | 2 | 2 | 2 | 4 | **3.0** | Moderate |
| `opentrons-rna-extraction` | 4 | 4 | 5 | 3 | 2 | **3.3** | Moderate |
| `golden-gate-assembly` | 3 | 5 | 4 | 5 | 2 | **3.5** | Complex |
| `opentrons-rna-extraction-hard` | 4 | 4 | 5 | 3 | 4 | **4.0** | Complex |
| `golden-gate-assembly-hard` | 3 | 5 | 4 | 5 | 5 | **4.5** | Very complex |

**What the ratings show**

- **The benchmark is bottom-heavy.** 4 of the 7 evaluated tasks are rated Trivial or Simple, and every model scores 1.0 on 5 of the 7.
- **Complexity is not what makes a task hard for models.** Golden Gate (3.5, the most complex evaluated task) and AMPure (5,376 liquid ops) are passed by all three models. The points are lost on heat shock (1.5) and RNA extraction (3.3), where the failures are domain judgement: pipette-mixing competent cells, eluting 100 µL instead of 80 µL, adding samples before beads.
- **The hard variants are the most complex tasks and have never been run.** Running them in Harbor is the cheapest way to make the benchmark discriminate.

## 3. Where the models go wrong

A deterministic diff of each model's run log against the oracle's (`research/expansion/tools/fault_detect.py`, report in `research/expansion/fault_report.md`) matches the judge on every task:

| Task | Opus 5.5 | Sonnet 5.5 | Fable 5.1 |
|---|---|---|---|
| Heat shock | mixes the competent cells | clean | mixes the competent cells |
| RNA extraction | elutes 100 µL (oracle 80) | samples before beads; elutes 100 µL; removes 5% more waste | elutes 100 µL |

- **Judge inconsistency:** Opus and Fable perform identical robot actions on heat shock (three 10 µL mix strokes in the cell tube) but score 0.8 and 1.0. "Do not pipette-mix competent cells" should be a deterministic check.
- **The RNA oracle is the authors' script, not the task spec.** It waits 28 min and engages the magnet 7 times; the task asks for about 15 min and 2 engagements, and the oracle itself scores 0.6.
- **The simulator does not track liquid**, so over-aspiration and biological harm (mixing fragile cells) pass simulation.

## 4. Expansion

Four searches (web/Europe PMC, Amass full text, a 2,271-repo GitHub sweep, and non-liquid-handling automation) found 263 unique candidates, 210 of them new. See `research/expansion/SUMMARY.md`.

| | Candidates |
|---|---|
| New, paper + code | 138 (111 report wet-lab results, 94 openly licensed) |
| New, ready | 44 (25 liquid handling, 19 non-liquid-handling) |
| New, partial | 108 |

| Scenario | Tasks |
|---|---|
| Today | 11 |
| + 12 corpus papers that already have IR but no task | ~61 |
| + new ready candidates | ~149 |
| + all new paper + code candidates | ~340–410 |
| Theoretical ceiling (incl. partial, ACRA, AEGIS) | ~500–600 |

**Simulator check** (`research/expansion/VERIFIED.md`): of 128 protocol files in the 25 ready liquid-handling repos, 30 pass `opentrons_simulate` unchanged (10 repos). All 98 failures are setup, not logic: custom labware on the author's disk (43), API newer than 7.5 (24), extra packages (15), missing input files (5), other (11).

## 5. Recommendations

1. Run the four `-hard` variants in Harbor; they are the only tasks rated Complex or above.
2. Turn judge items that encode domain rules (cell mixing, elution volume) into deterministic checks, and add a spec oracle next to the authors' script for RNA extraction.
3. Build the next tasks from the 12 corpus papers with IR and the 10 repos that already simulate (MSD assays, HyRAD, ExFAB Flex QIAseq, AntCloning, GFP codon burden, MassSpecPreppy, OT-2 autoclone, culturomics, Beckham).
4. Re-run verification with the repos' labware vendored and a newer Opentrons release.
5. Add new grader families only where hardware-free execution exists: XDL (Cronin ACRA, 100+ executed literature→XDL pairs), microscope acquisition, workcell schedulers.
