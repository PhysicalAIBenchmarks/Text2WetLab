# opentrons-mujoco-viz: source analysis and measured behaviour

Reviewed: `PhysicalAIBenchmarks/opentrons-mujoco-viz` at commit `460169f` (about 1,275 lines: `scene.py` 352,
`event_driver.py` 249, `generate_labware.py` 197, `modules.py` 180, `assets/ot2.xml` 246), with MuJoCo 3.15.
Every number below was measured by `tools/probe_mujoco_viz.py`; raw output is in `mujoco_viz_probe.json`.
Evidence for PR #63, which rendered all tasks and candidates with this package.

## Summary

The package draws a recognisable OT-2 and keeps correct liquid and module state, and it renders a video in about 5 seconds.
But the simulated gantry does not go where it is commanded: the pipette tip ends 17–103 mm from the centre of every slot,
never changes height, and never visits an individual well. The MuJoCo part therefore adds motion that looks plausible but is
not a faithful account of the protocol, and it cannot yet support collision or reach checks.

## How it works

| Part | What it does |
|---|---|
| `assets/ot2.xml` | A hand-built scene of 17 bodies and 82 box/cylinder geoms, no meshes. One fixed deck: tip rack (slot 1), plate (2), trough (3), magnetic module (4), temperature module (6), thermocycler (7/8), heater-shaker (9), trash (12). Three slide joints (x, y, z) with position actuators, plus the thermocycler lid. |
| `modules.py` | `ProtocolState`: pure-Python bookkeeping of pipette volume, tip, per-well volumes and module states, updated by each event. The docstring in `scene.py` says so directly: "Liquid volumes are tracked analytically; MuJoCo handles gantry kinematics only." |
| `scene.py` | `WetLabScene.apply_event` moves the gantry to the event's slot for a fixed number of physics steps, updates the state, recolours geoms, and returns frames. `render_with_hud` overlays step count, tip, pipette volume and module status. |
| `event_driver.py` | Regex parser for `opentrons_simulate` text output and a `render_protocol` wrapper. |
| `generate_labware.py` | Builds OBJ meshes from Opentrons labware definitions. Not used by the bundled scene (0 meshes loaded). |

## Findings

### 1. The gantry does not reach the commanded position

Tip position after `move_to_slot(slot, work=True)` plus six further seconds of simulated time:

| Slots | Row | Tip distance from slot centre |
|---|---|---|
| 1, 2, 3 | front | 102–103 mm |
| 4, 5, 6 | second | 23–44 mm |
| 7, 8, 9 | third | 18–45 mm |
| 10, 11, 12 | back | 17–40 mm |

Three separate causes:

- **Y is out of range for the front half of the deck.** `_slot_ctrl_y` commands `slot_y − 0.17`, which is −0.34 m for slots 1–3
  and −0.255 m for slots 4–6. The joint and actuator range is ±0.24 m, so the command is clamped and the tip stops at y = −0.07 m
  for all six of those slots. The pipette never reaches the front row.
- **X stops 17–45 mm short.** With contacts disabled the x joint reaches its target exactly (−0.152 commanded, −0.152 achieved),
  so the shortfall comes from collisions.
- **Motion is not finished when frames are taken.** `apply_event` allows 100 physics steps (0.2 s) per move. After that budget the
  x joint was still at −0.013 m for a −0.152 m command (slot 1) and at −0.121 m for a 0 m command (slot 2), so rendered frames show
  the gantry part-way to, or still leaving, the previous slot.

### 2. The pipette never changes height

`SAFE_Z` is −0.02 m and `WORK_Z` is −0.17 m, but the z joint sits at −0.354 m and −0.369 m respectively, and the tip is at
z = −0.152 m over every slot. The two heights differ by 15 mm on screen instead of 150 mm. The actuator is pushing with about
2,700 N against 16 active contacts, and turning gravity off does not free it. With contacts off as well the joint goes to −0.517 m,
beyond its stated −0.38 m limit, so the limit is not being enforced either. The cause of the downward drift was not isolated.

### 3. Collisions are on for every geom, and they are the wrong ones

All 82 geoms have collision enabled and there are 12–16 active contacts at all times, including at rest. These are the model's own
parts touching each other, not the tip touching labware. Until they are removed, contact counts say nothing about a protocol.

### 4. Wells are not targeted

`move_to_slot` accepts a `well_offset_x`, but `apply_event` never passes one and there is no y offset at all, so the commanded
target for well A1 and well H12 of the same plate is the same point, the slot centre. Every operation on a plate is aimed at one spot.
(This is read from the code; the measured joint positions for the two wells differ only because the gantry had not settled.)

### 5. Only eight wells show liquid

The state tracks volume for any slot and well (100 µL dispensed into slot 5 C7 is recorded), but the scene only recolours eight
geoms, `w_A1` to `w_H1` in slot 2. Liquid anywhere else on the deck is invisible. This is why the four panels of a
model-versus-oracle grid look the same.

### 6. Liquid bookkeeping accepts impossible volumes

- Aspirating 5,000 µL leaves 5,000 µL in the pipette; `PIPETTE_MAX = 1000.0` is defined but never checked.
- Wells start at 0 and `add_to_well` clamps at 0, so aspirating from a source leaves it at 0. Source volumes are never tracked and
  drawing from an empty well is not detected.
- The tip-liquid indicator saturates at 200 µL regardless of pipette size.

### 7. Four of the five named cameras render black

Mean pixel brightness (0–255): `iso` 0.0, `side` 0.0, `front` 0.0, `deck` 0.03, `top` 87.8, and the built-in fallback free camera 31.0.
`render()` and `apply_event()` default to `iso`, so the documented quick start produces black frames. `scripts/render_run.py`
in this repository already works around this by forcing the fallback camera.

### 8. The package's parser does not read current Opentrons output

On the `a1-a12-100ul` reference protocol under Opentrons 7.5, the log has 12 aspirate and 12 dispense lines; `parse_simulate_output`
returns 2 events (one pick, one drop) and no liquid moves. Its pattern expects `well A1 of <labware> on <slot>`; Opentrons 7.5 prints
`Aspirating 100.0 uL from A1 of reservoir on 1 at 92.86 uL/sec`. `render_run.py` and `tools/mj_render.py` avoid it by converting
events from `eval/runlog.py`.

### 9. The deck is the same for every protocol

The scene has no notion of what a protocol loaded. A protocol with tube racks in slots 1 and 2 is drawn with a tip rack and a
96-well plate there. `generate_labware.py` could supply real geometry but is not wired in.

## What works

- State tracking of pipette, tip, well volumes and module states is straightforward and correct for well-formed logs.
- Module feedback: magnet bar and LED, temperature LED colour, thermocycler lid actuation, heater-shaker latch.
- Speed: about 5 s for a 45 s video, headless, with no browser or GPU.
- The HUD shows step count, tip state, pipette volume and elapsed protocol time.

## Compared with the PyLabRobot replay

| | opentrons-mujoco-viz | PyLabRobot replay (`tools/replay_log.py`) |
|---|---|---|
| Deck | One fixed layout | Built from the labware the protocol loaded |
| Position shown for an operation | 17–103 mm from the slot centre; wells not distinguished | The exact well, from the labware definition |
| Height changes | 15 mm instead of 150 mm | Marker above the well (no z motion modelled) |
| Liquid shown | Eight wells of one plate | Every well and tube |
| Tips | One indicator | Every tip position |
| Faults | None | Marked by `fault_detect.py` |
| Robots | OT-2 | OT-2, and a Hamilton STARlet |
| Physics | Rigid-body dynamics, currently obstructing the motion | None |
| Render time per video | About 5 s | 1–2 min, needs a GPU browser |

Side-by-side videos of all 11 tasks, both driven by the same oracle run log, are in the private Hugging Face dataset
`EvanOLeary/text2wetlab-3d-replays` under `side_by_side/` (built by `tools/side_by_side.sh`).

## What to fix, in order

1. Turn collisions off for the gantry and decorative geoms (`contype="0" conaffinity="0"`), or add contact exclusions, so the
   gantry can move. This alone should fix x tracking.
2. Correct the y mapping or widen the y range so slots 1–6 are reachable.
3. Find why z does not hold its commanded height, and enforce the joint limit.
4. Step until the position error is below a tolerance instead of a fixed 100 steps.
5. Pass per-well offsets from the labware definition into `move_to_slot`.
6. Build the deck from the protocol's labware (wire in `generate_labware.py`) and recolour every well.
7. Fix the named cameras and make a working one the default.
8. Update the parser to the Opentrons 7.x log format, or drop it in favour of `eval/runlog.py`.
9. Enforce pipette capacity and allow starting volumes.

Once 1–5 hold, contacts between the tip and labware become meaningful, and a collision or reach check can be added to
`fault_detect.py` as a new fault type. That is the capability MuJoCo offers that the PyLabRobot replay cannot.

## Limits of this analysis

One commit of the package was examined with one MuJoCo version. The z-axis behaviour was measured but its cause was not isolated.
The tip position is the centre of the `pip_tip` geom; slot centres are the package's own `SLOT_XY` table.
