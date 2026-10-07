# Opentrons Protocol Agent: Spec, Acceptance Criteria & Risks

> **Status:** which of AC1-AC7 are implemented, and measured evidence for each, is in [`criteria.md`](criteria.md). The spec below is the design intent.


## Pipeline

```
NL  →  IR (decomposed steps)  →  Python (Opentrons API)  →  Simulate  →  Checks  →  (Optional) Visualisation
```

**Core principle:** checks run on the **simulated command trace**, not on the Python source.
- `opentrons.simulate` returns a run log of the real commands that would execute.
- Replay that log while tracking state: tip on/off, volume in the tip, what each tip has touched, and the contents of each well.
- Every acceptance check below is a deterministic function over that state trace.
- This stops the model passing by writing `distribute()`, which refills and handles tips for it, without understanding the task.

---

## Test Case 1 (original)

> Add 100 µL of liquid from a 1-well reservoir to wells A1→A12 in a 96-well plate.

**Expected behaviour:** the model realises it must aspirate more liquid partway through the run. 12 × 100 µL = 1,200 µL, which is more than the pipette holds.

**System parameters (fixed, given to the model):**
- Pipette model and max volume (e.g. P300 = 300 µL)
- Tip rack, reservoir and plate load names and deck slots
- All plates are 96-well for testing (per R13)

---

## Acceptance Criteria

| # | Criterion | Check on the state trace |
|---|---|---|
| AC1 | Pick up a tip before aspirating any liquid | No `aspirate` while tip state = none |
| AC2 | Aspirate more liquid after dispensing | Never dispense more than the tip currently holds; number of aspirates ≥ ceil(total ÷ usable capacity) |
| AC3 | Aspirate enough for several dispenses | Each aspirate ≥ 2 × the per-well volume, where capacity allows |
| AC4 | Drop the tip when finished | Last liquid command is followed by `drop_tip`; no tip left attached at the end |
| AC5 | **(Critical)** Doesn't crash | Simulation completes without error **and** passes the geometric / z-height check |
| AC6 | Lifts before moving | No `force_direct=True`; no travel between locations below safe height. Test by forcing a collision and confirming the checker flags it. |
| AC7 | **No cross-contamination** | Change tips whenever the tip touches something that must not go into the next well. |

**AC7 check:** each tip keeps a "touched" set.
- Dispensing into a non-empty well adds that well's contents to the set. This assumes contact, which is the conservative choice.
- Violation if a contaminated tip (a) aspirates from a shared source, or (b) dispenses into a well whose contents differ from what it has touched.
- Per R11, the check is about **what is added to what, and in what order**, not exact well positions.

---

## Risks

### NL → IR (translation)

| ID | Risk | Decision / Mitigation |
|---|---|---|
| R2 | Translation needs ground truth for discrete steps | Reference IR = basic steps (pick_up, aspirate, dispense, drop), scored step by step |
| R3 | Implicit state is dropped (tip needed, pipette capacity, discard at end) | Give the model **parameters for our Opentrons system** and have it infer the implicit steps from them |
| R4 | Spec ambiguity (A1→A12 as a row or a column?) | Convention: **letters always mean rows, numbers always mean columns** |
| R5 | Wrong step count or order (missing re-aspirate, tip pickup after aspirate, off-by-one) | Caught by the acceptance criteria checks |

### IR → Python (code generation)

| ID | Risk | Decision / Mitigation |
|---|---|---|
| R6 | API / version mismatch (hallucinated methods, v1 vs v2 API) | Deterministic check (pin apiLevel, check method calls against the API); prompt the model to focus on the top-level API |
| R7 | Wrong labware definitions (load names, slots, well naming); may pass simulation but not match the real deck | Deterministic check against the allowed labware and slot list |
| R8 | IR and Python drift apart (Python valid on its own but doesn't implement the IR) | Check that the simulated trace matches the IR step sequence |

### Physics & hardware

| ID | Risk | Decision / Mitigation |
|---|---|---|
| R1 | Physical incompatibilities: collisions (IR → code phase) | See R10 |
| R9 | Liquid handling effects: capacity overflow, tip contact / contamination, wrong height, air gaps, viscosity | Static checks for capacity, height and contamination. **Viscosity ignored** (no practical way to check) |
| R10 | Simulator vs reality gap: the Opentrons simulator catches API errors, probably not true collisions. The OT-2 has **no contact sensors**. | The checker needs **object sizes** (from labware definitions) to judge collisions as the pipette moves. **First test:** run a protocol with `move_to(plate['A1'].bottom(), force_direct=True)` through `opentrons.simulate` and confirm whether it errors |

### Evaluation & methodology

| ID | Risk | Decision / Mitigation |
|---|---|---|
| R11 | Oracle problem: several valid protocols exist for one task | Checks focus on **what is added to what, and the order**, not exact well locations |
| R12 | Test brittleness | Use state-trace checks rather than text matching |
| R13 | Overfitting to one task | For testing, **assume everything is in 96-well plates**; vary well count and volumes |
| R14 | Non-determinism: LLM output varies between runs | Report pass@k over repeated runs |
| R15 | Silent partial success: runs without error but dispenses wrong volumes | Check **final well volumes** from the trace, not just "no error" |

**R12 explained:** the naive way to test is to search the Python text, e.g. "does `pick_up_tip` appear before `aspirate` in the file?" That breaks both ways:
- *Fails correct code:* the model uses `transfer()`, which picks up tips internally, so `pick_up_tip` never appears.
- *Passes wrong code:* `pick_up_tip` sits in the file but inside a branch that never runs.

Fix: don't read the code. Replay the simulator's command log and check the state at each step (tip attached? volume in tip? what has it touched?).

### Reward hacking

Ways an agent could pass checks without doing the task, each blocked by a static check:
- `try/except` blocks that swallow errors
- branching on `protocol.is_simulating()` so the simulated run differs from the real one
- `distribute()` / `transfer()` auto-behaviour standing in for understanding
- quietly lowering volumes so everything fits in one aspiration
