# qte77's lab-automation projects: research notes and how they meet Text2WetLab

Four public repositories by Andre Slavik ([qte77](https://github.com/qte77) on GitHub), read on 2026-10-11 at their `main` heads, with their test suites run locally. Together
they are the pieces of one planned system: an open, sub-$1k self-driving lab that runs a closed
*perceive → decide → act → record* loop. The plan is set out in the write-up
[Building a Trustworthy Agent Loop for a Physical Lab](https://qte77.github.io/open-self-driving-lab-agent-loop/).
Text2WetLab measures one link in that loop, an agent turning a protocol into robot code, so these notes ask what each
project is, how mature it is, and where it and this benchmark can use each other.

| Project | Role in the loop | Size | Tests (run here) | Maturity |
|---|---|---|---|---|
| [i3mega-pipettebot](https://github.com/qte77/i3mega-pipettebot) | **Act**: a stock 3D printer turned into a 3-axis pipetting gantry | 134 commits, v0.2.0 (2026-09-17), ~1.3k lines of library code | 208 passed, 9 skipped (hardware-gated) | Shipped and run on hardware |
| [so101-biolab-automation](https://github.com/qte77/so101-biolab-automation) | **Act** (arms, tool changes, fridge) + **Record** (eLabFTW client) | 110 commits, v0.2.0, ~2.5k lines in `src/so101/` | 321 passed, 1 skipped | Software runs in stub mode; README marks the hardware untested |
| [CellPlateVision-Prototype](https://github.com/qte77/CellPlateVision-Prototype) | **Perceive**: confluence and growth from images of Petri dishes | 14 commits, v0.1.0, ~0.9k lines | 34 passed | Prototype; milestones M0–M4 merged, M5 (real-lab validation) open |
| [agentic-cax-gauge](https://github.com/qte77/agentic-cax-gauge) | Checks the CAD that agents write for the printed parts the rigs use | 35 commits, v0.1.0, M2 in progress | 55 passed, 3 deselected | Preflight and viewer exist; the CLI is a stub that exits non-zero |

All four are Apache-2.0, use `uv`, a `make validate` gate, CodeQL, Dependabot, and the same agent-facing scaffolding
(`AGENTS.md`, `AGENT_LEARNINGS.md`, `.claude/` rules and skills). Each one documents what it does not yet do, which made
these notes easier to write.

## 1. i3mega-pipettebot: the motion layer

**What it is.** An Anycubic i3 Mega (or Geeetech A30) with the hotend and its PCB taken off the carriage. Stock Marlin
or Smartto firmware drives it as a bare XYZ gantry, and a DLAB dPette+ electronic pipette is clamped to the carriage. A
PC hosts both over two USB-serial links: G-code at 250000 baud to the printer and a 6-byte protocol at 9600 baud to the
pipette, through [`dpette-usb-driver`](https://github.com/Lambda-Biolab/dpette-usb-driver). The build costs about $150,
against $15,950 for an OT-2 and roughly $900 for a Science Jubilee with a pipette tool.

**Architecture.** `gantry.py` wraps G-code send/ack. `devices.py` reads the firmware family from `M115` and dispatches
`safe_home`: plain `G28` on Marlin and a polled-Z descent on Smartto, whose `G28 Z` is broken on stock A30 builds
([ADR 0004](https://github.com/qte77/i3mega-pipettebot/blob/main/docs/adr/0004-printer-firmware-policy-and-safe-home.md)).
`motion_profile.py` bundles SLOW/MID/FAST acceleration and jerk sets. `experiment_profile.py` loads TOML experiment
profiles that set per-cycle volumes. `bot.py` composes move-then-pipette. `so101/orchestrator.py` hands the used-tip
bin to an SO-101 arm after the gantry homes. Five ADRs record the design. The one that matters most for portability is
[ADR 0005](https://github.com/qte77/i3mega-pipettebot/blob/main/docs/adr/0005-pc-as-host.md): firmware stays stock, and
everything goes through G-code from the host.

**What it does not do (by its own docs).** It has no deck library, no software soft limits and no calibration storage:
callers pass raw `(x, y, z)`. Aspiration is open-loop, with no pressure sensing; the TADM-style options are surveyed in
`docs/research/aspirate-monitoring.md`. `docs/deck-layout.md` is marked STALE. The README's version badge says 0.0.1,
but `pyproject.toml` and the tags are at 0.2.0. The mounted pipette is the **8-channel** dPette+: its eight channels
share one piston, so every aspirate and dispense hits a whole column at once (`bot.py`, `COLUMN_PITCH_MM`).

**The constraint that matters for code generation.** An LLM writing for this rig has to think in columns, not wells,
and has to pick one of four volume ranges (0.5–10, 5–50, 15–300, 30–300 µL) because changing range means remounting the
pipette by hand. The OT-2 API hides both concerns. §5 measures what that does to the benchmark's tasks.

## 2. so101-biolab-automation: arms, tool changes and the notebook

**What it is.** It has two paths. The first is two SO-101 follower arms plus a leader arm on LeRobot ($350–$650) for
manipulation: fridge door, plate moves and a three-tool magnetic dock (pipette, gripper, fridge hook). The second is a
$60–$80 XZ gantry for dedicated pipetting. Pipette backends sit behind a `PipetteProtocol`: the DIY
[digital-pipette-v2](https://github.com/ac-rad/digital-pipette-v2) syringe, or the AELAB/DLAB electronic pipettes. A
Bento Lab PCR unit, an eLabFTW ELN client and a FastAPI dashboard with WebSocket e-stop and heartbeat complete the
stack. A build123d CAD pipeline, with OpenSCAD as fallback, writes STL, STEP and SVG for every printed part and slices
them headless to check printability.

**Architecture.** `workflow.py` composes use cases UC1–UC7 (single well, row/column/plate fill, fridge retrieval, tool
cycling, gantry pipetting, ELN-logged experiment, Cartesian pipetting) from the module layer. Every hardware module
degrades to a **stub mode** when its dependency is missing, so the whole workflow and its 321 tests run without
hardware. `safety.py` adds a watchdog that parks the arms when heartbeats stop, plus joint limits.
`pylabrobot_backend.py` subclasses PyLabRobot's `MachineBackend` when PLR is installed.

**Gaps that matter downstream.**
- *No inverse kinematics.* `send_to_well()` goes to a taught `well_approach` pose, and the named poses in
  `configs/arms.yaml` are placeholders (architecture.md, "Key Design Decisions"). Per-well addressing on the arm path
  does not exist yet.
- *Tip pickup is a no-op* in the PLR backend (`pick_up_tip()` is a placeholder). Any multi-step protocol therefore
  reuses one tip, which is exactly the cross-contamination class Text2WetLab's verifier penalises.
- The PLR backend exposes `aspirate(volume)` and `move_to(arm, joints)` without labware resources, so PLR protocols
  written against wells and resources will not run through it as they stand.
- The roadmap is ambitious and candid: closed-loop printing, "autonomous tool genesis" (detect a missing tool, design
  it, print it, mount it), and VLM phases. It names RobotSmith, VLMgineer and Ringwald et al. as the nearest prior art.

## 3. CellPlateVision-Prototype: the perceive step

**What it is.** Image → dish detection (OpenCV Hough circles) → segmentation → confluence (cell pixels / dish pixels)
→ growing / not growing / low confidence → eLabFTW upload. Segmentation is tiered. Otsu with morphological cleanup is
the default. When the Otsu step flags low contrast (P20–P80 spread below 0.15, i.e. near-empty or near-confluent), the
pipeline escalates to Cellpose `cyto3` on CPU, or `cpsam_v2` on GPU behind a flag. LandingLens is a documented stub.
CI uses only synthetic fixtures; AGAR, a 2023 *Scientific Data* colony set and LIVECell are listed for tuning.

**Assessment.** The code is small, clean and honest about confidence: there is an explicit `low_confidence` label
rather than a forced binary. Two mismatches stand out:
- **Dishes, not plates.** It targets round 35/60/100 mm Petri dishes. The agent-loop write-up wants a dye signal *per
  well of a 96-well plate*, and the `MultiWellFinder` (SBS grid) is deferred to the outlook. Until that exists, the
  perceive step cannot read what the act step produces.
- **Unvalidated thresholds.** The 0.20 growth threshold and the Hough parameters are uncalibrated defaults. M5
  (5–100 real images, a GPU decision, production credentials) is where they get checked.

The repo also duplicates so101's eLabFTW client (`elab_client.py` versus `so101/eln_client.py`, both on
`elabapi-python`, API v2). One shared client would keep the Record step consistent across the stack.

## 4. agentic-cax-gauge: verifying agent-written CAD

**What it is.** A verification harness for CAD that agents generate. It has three layers in order of trust: (1) a
cheap deterministic preflight (file integrity, watertight/manifold, bounding box against an envelope, volume against a
band); (2) an automatic multi-view render as the *primary* gate, so a human decides at a glance; (3) a VLM that may
annotate but never gates. The motivation is evidence that VLMs are near chance on 3D spatial reasoning (the README cites
BLINK: humans 95.7%, best VLM 51.3%). Its stated rule is **"Green means not obviously broken, never correct"**, and the
code enforces it: `Status.SKIP` never counts towards green, an unsupplied bound reports `SKIP` rather than `PASS`, and a
browser load that captured console errors cannot be a pass (`verify/types.py`).

**State.** M1 (scaffold) has shipped. M2 has types, preflight with fixtures for silent feature loss in boolean fusion,
a static three.js viewer, multi-view PNG capture and a headless browser load check. The report and the CLI remain; the
handoff also notes a Y-up/Z-up swap in the viewer. M3 is adoption by so101 and i3mega, its named first consumers. A
BIM/IFC milestone stays dormant until a real BIM user's data arrives.

**Why it is relevant here.** It is the same design problem as Text2WetLab's verifier, in a different domain. Both
layer a cheap deterministic check, a trustworthy executor (the Opentrons simulator here, the renderer there) and an
advisory or majority-vote model. Both treat "nothing was checked" as distinct from "passed". The gauge's §3.1 red-team
of its own "authoritative oracle" framing is worth reading next to this repo's reward-hacking traps.

## 5. What the benchmark's IR needs from these rigs

Every Text2WetLab task with an IR states its ground truth as containers, wells and volumes, with nothing OT-2
specific. That makes a direct question possible: *could the rigs above run the same protocol?*
[`eval/embodiment_fit.py`](../eval/embodiment_fit.py) answers it statically. It describes each rig from its repo
(volume ranges, channel count, what the deck holds, whether tips change automatically) and checks every IR step against
it. It does not simulate reach, collisions or timing; a pass means "not obviously impossible". Rerun it with
`uv run python eval/embodiment_fit.py --markdown`.

The nine tasks with an IR, at the four rigs' current specs:

| Task | OT-2 (p20 + p300) | i3 Mega + dPette+ 8-channel | i3 Mega + dPette single-channel (untested) | SO-101 + digital-pipette-v2 |
|---|---|---|---|---|
| `a1-a12-100ul` | runs · 1/1 | partial · 0/1 | runs · 1/1 | runs · 1/1 |
| `ampure-bead-cleanup` | runs · 8/8 | blocked · 8/8 | blocked · 8/8 | blocked · 1/8 |
| `colony-pcr-screening` | runs · 3/3 | blocked · 3/3 | blocked · 3/3 | blocked · 1/3 |
| `colony-pcr-screening-hard` | runs · 3/3 | blocked · 3/3 | blocked · 3/3 | blocked · 1/3 |
| `ecoli-heat-shock-transformation` | runs · 2/2 | blocked · 0/2 | blocked · 2/2 | blocked · 1/2 |
| `ecoli-heat-shock-transformation-hard` | runs · 2/2 | blocked · 2/2 | blocked · 2/2 | blocked · 1/2 |
| `golden-gate-assembly` | runs · 23/23 | blocked · 1/23 | blocked · 23/23 | blocked · 4/23 |
| `golden-gate-assembly-hard` | runs · 23/23 | blocked · 1/23 | blocked · 23/23 | blocked · 4/23 |
| `split-200ul-two-wells` | runs · 1/1 | partial · 0/1 | runs · 1/1 | runs · 1/1 |

Each cell gives a verdict and the robot steps that pass out of all robot steps; manual steps such as incubations are
excluded. *Blocked* means a deck-level problem stops the run even when every step passes. The two RNA-extraction tasks
have no IR and are not scored here.

**What the matrix says.**
1. **Deck size is the first wall, not the pipette.** The printed i3 deck holds one reservoir and one plate next to the
   tip box. Every multi-labware task is blocked there, even where each step is fine.
2. **Several real protocols are already column-wise.** All of `ampure-bead-cleanup`'s and `colony-pcr-screening`'s
   steps fit the 8-channel head. Rerunning with a larger deck: at **4** labware positions, with range swaps allowed,
   the 8-channel gantry runs both colony-PCR tasks and the hard heat-shock task. At **6**, it adds AMPure, and AMPure
   needs no range swap. A printed deck plate with more SBS positions is therefore the cheapest change that opens the
   most tasks, and it is exactly the kind of part agentic-cax-gauge exists to check.
3. **Row fills are the 8-channel's blind spot.** `a1-a12-100ul` (row A) and `split-200ul-two-wells` fill single
   wells; a shared-piston head cannot do either without wetting seven more tips. Text2WetLab's easiest tasks are
   therefore the gantry's hardest.
4. **Golden Gate needs tubes.** It uses 1.5, 15 and 50 mL tube racks and eight labware positions. That needs printed
   tube holders plus single-channel work; the 8-channel can do one of its 23 robot steps.
5. **Low volumes force a remount.** Colony PCR (1 µL template and primer, 18 µL master mix) and heat shock (1–2 µL
   plasmid) span two dPette ranges. On the OT-2 that is p20 versus p300 on two mounts; on the gantry it is a human
   swapping pipettes mid-run.
6. **The SO-101 path fails on tips first.** Without tip pickup, every transfer after the first reuses a tip. Even
   `a1-a12-100ul` only "runs" because it is a single transfer from one reservoir.

## 6. Where Text2WetLab and these projects can use each other

**Into Text2WetLab**
- **An embodiment track.** The same IR, compiled for a different robot, asks whether a model can respect a cheaper
  rig's constraints: column-only dispensing, range remounts, two deck positions. Tasks whose IR is column-wise
  (AMPure, colony PCR) are natural first candidates. The grader would need a pipettebot executor in place of
  `opentrons_simulate`. The gantry showcases already tee their G-code stream to a file for replay; a dry-run executor
  that replays that file against a deck model would be the counterpart of the simulator layer.
- **A shared event log for the viewer.** The MuJoCo viewer
  ([opentrons-mujoco-viz](https://github.com/PhysicalAIBenchmarks/opentrons-mujoco-viz)) is driven by a robot-neutral
  event list (`pick`, `aspirate`, `dispense`, `mix`, …). A pipettebot run that emitted the same events could be
  rendered next to the OT-2 version of the same task.
- **Verifier design.** agentic-cax-gauge's honesty rules (SKIP is not PASS; a check that ran without a bound checked
  nothing) are a checklist worth running over every reward layer here: does a layer that could not run report that, or
  score as if it passed? The README records eight grader faults that model runs exposed; this is one more lens.

**Into qte77's stack**
- **A test bed for the decide step.** The agent-loop write-up names the decide step as the part that does not exist
  yet. Text2WetLab's verifier (lint gate, reward-hacking traps, simulator, IR checks, rubric) is a ready-made scorer for
  the protocol an agent decides to run, before it touches a real gantry.
- **paper2protocol as a protocol source.** It extracts a liquid-handling IR from a paper. With an i3 compile target,
  published protocols become runnable gantry jobs, and `embodiment_fit.py` already reports which ones fit.
- **PLR coverage.** Text2WetLab's [PLR embodiment pairs](https://physicalaibenchmarks.github.io/Text2WetLab/plr_embodiment_pairs.html)
  map PyLabRobot instruments to papers with code. so101's `SO101Backend` is a PLR `MachineBackend`; completing it with
  tip pickup and resource-addressed wells would let PLR-level protocols, and PLR-level benchmark tasks, target it.

## 7. Risks and open questions

- **No measured accuracy anywhere yet.** The gantry write-up reports no volumetric accuracy or precision, and the
  vision prototype has no real-image validation. A gravimetric check (dispense into a tared plate, weigh) on the
  gantry is the cheapest first number, and would make any embodiment-track result interpretable.
- **Open-loop aspiration.** With no pressure sensing, a failed aspiration looks like a success to the controller.
  Text2WetLab's simulator layer has the same blind spot; the agent-loop write-up names "measurement trust" as a design
  goal.
- **Spec drift.** The rig specs in `embodiment_fit.py` are copied from READMEs and code that change weekly (the i3
  deck doc is already marked STALE). A machine-readable capability file in each rig repo would remove the copy.
- **Safety envelope.** The gantry has no software soft limits, and the demos require removing tips before homing. An
  agent-generated G-code program needs a host-side bounds check before it reaches hardware. That is the same idea as
  Text2WetLab's lint gate, applied to motion.
