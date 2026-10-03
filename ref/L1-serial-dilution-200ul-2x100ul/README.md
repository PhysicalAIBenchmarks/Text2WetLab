# L1 · Serial Dilution — 200µL → 2×100µL

**Layer**: L1 (liquid handling)  
**Platform**: Opentrons OT-2 (API v2.16) + PyLabRobot 0.2.2 (sim)  
**Experiment**: Aspirate 200µL from a trough, dispense 100µL to well A1, dispense 100µL to well B1, drop tip.

---

## Natural language input

> "Pick up a tip, aspirate 200 microlitres from the reagent trough,
> dispense 100µL into well A1 then 100µL into well B1, and throw the tip away."

## Deck layout

| Slot | Labware |
|---|---|
| 1 | opentrons_96_tiprack_1000ul |
| 2 | corning_96_wellplate_360ul_flat |
| 3 | agilent_1_reservoir_290ml (trough) |

## Test criteria

The correct translation of this NL instruction must satisfy all five criteria:

| # | Criterion | PyLabRobot result | Opentrons_simulate |
|---|---|---|---|
| T1 | Pick up tip **before** any aspirate | PASS — `NoTipError` | PASS |
| T2 | Aspirate 200µL (enough for 2 dispenses) | PASS | PASS |
| T3 | Two 100µL dispenses from single load | PASS | PASS |
| T4 | Drop tip when finished | PASS | PASS |
| T5 | Overdispense (100µL held, 200µL requested) | **FAIL — silent** | PASS |
| T6 | Over-capacity (1100µL > 1000µL tip max) | **FAIL — silent** | PASS |

**Finding**: PyLabRobot sim validates tip presence (T1) but not volume arithmetic (T5, T6).
Add explicit post-run assertions for T5/T6 when using the ChatterBox backend.

## Files

- `protocol_correct.py` — reference Opentrons API v2 implementation  
  Run with: `opentrons_simulate protocol_correct.py`

- `run_tests.py` — PyLabRobot test harness (all 6 criteria)  
  Run with: `uv run python run_tests.py` (requires `pylabrobot>=0.2.2`)

## Key insight: errors as mistranslations

When an LLM generates a bad protocol, the errors surface as simulation failures.
T1–T4 are caught by both simulators. T5–T6 are **only** caught by `opentrons_simulate`,
not by PyLabRobot's ChatterBox backend — a gap to account for in NL2WetLab evaluation.
