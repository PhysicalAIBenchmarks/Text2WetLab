# Benchmark expansion: merged candidate search (2026-10-12)

Four research passes looked for (paper, public robot code, reported wet-lab results) triples:
web deep research (Europe PMC full text + GitHub), Amass BioMedCore full-text search (1,850 credits),
a GitHub code sweep (2,271 repos, PyLabRobot first), and a non-liquid-handling pass (imaging,
protocol languages, bioreactors, schedulers, arms). Per-source files: `*_candidates.jsonl`, `*_notes.md`.
Merged and de-duplicated by DOI and GitHub repo: `merged_candidates.jsonl` (`found_by` lists the sources).

## Counts

| | Candidates |
|---|---|
| Raw rows across the 4 sources | 328 |
| Unique after merging | 263 |
| Already in the corpus (`docs/task-sources.md`) | 53 |
| **New** | **210** |
| New, ready | **44** (25 liquid handling, 19 non-liquid-handling) |
| New, partial | 108 |
| New, no usable code | 58 |
| New and found by more than one source | 38 |

"Ready" = open paper text + public code that should run in a simulator or dry-run as-is or with labware
fixes + reported wet-lab results. It was judged from reading code; none of the new protocols has been run
in `opentrons_simulate` yet. 9 of the 44 ready candidates have no or unclear code licence (reference-only).

## How much bigger the benchmark could be

Counting an easy + hard variant per experiment (2 tasks per candidate, conservative; the agents' own
per-paper estimates are higher because many papers contain several experiments):

| Scenario | Tasks | vs today |
|---|---|---|
| Today | 11 | 1x |
| + 12 corpus papers that already have pipeline IR but no task (25 experiments) | ~61 | 5.5x |
| + 44 new ready candidates | ~149 (agents' estimate ~251) | 14x (23x) |
| + 108 new partial candidates | ~365 (agents' estimate ~458) | 33x (42x) |

**Ready to execute on today's grader:** the 25 liquid-handling ready candidates (24 OT-2, 1 Flex) fit the
existing Opentrons simulator + run-log grader, about 50 tasks. The 19 non-liquid-handling ready candidates
(imaging, protocol languages such as XDL/LabOP, scheduling) need new graders.

## Findings worth knowing

- Code, not papers, is the bottleneck: Amass returned 4,019 papers, but most published robot protocols
  never release the script. Recall levelled off (the last 20 queries added 4 papers).
- PyLabRobot: about 50 public repos use it, but only one has a paper with wet-lab results
  (Chory lab turbidostat, custom hardware, no licence). PLR tasks would need porting Opentrons/PyHamilton triples.
- The Opentrons Protocol Library (833 protocols) cites no research papers, so it is not a source of triples.
- Closest existing benchmark: AEGIS (24 MIT OT-2 protocols with injected bugs). LabScript-AI and the
  KAISA-LSE GPT-generated-protocol study are related work.
- Highest-value single find: Cronin lab ACRA, 100+ literature-to-XDL pairs executed on the Chemputer.
