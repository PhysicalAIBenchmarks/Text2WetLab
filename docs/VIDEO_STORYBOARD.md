# Text2WetLab — Video Storyboard

**Total runtime:** 3:30
**Format:** 16:9, 4K render preferred, 1080p minimum
**Style:** Dark cinematic — near-black backgrounds, amber and teal lighting, Source Sans 3 / Source Code Pro titles
**Music:** Slow ambient electronic; builds through Section 4, resolves on CTA

---

## Scene 1 — The Hook (0:00 – 0:15)

**Visual concept:**
A robot arm (OT-2 overhead POV, time-lapse) loads a tip and moves to a well plate.
Intercut with a close-up of a printed journal methods section.

**Shot list:**
| Time | Shot | Description |
|------|------|-------------|
| 0:00 | Wide, slow push in | Dark frame. A single OT-2 pipette descends onto a 96-well plate. Amber spotlighting. |
| 0:04 | Text card (fade in) | White text, Source Sans 3 Light, centred: *"Millions of lab protocols will be executed by AI."* |
| 0:09 | Cut to tight close-up | PDF methods section on a monitor — blurred except the phrase "Transfer 2 µL…" |
| 0:12 | Text card (fade in, amber) | *"How do we know they're right?"* |
| 0:14 | Logo reveal | **Text2WetLab** wordmark fades in. Teal underline sweeps left-to-right. |

**VO / caption:** None. Text cards carry the narration. Music: single piano chord, sustained.

---

## Scene 2 — The Reproducibility Gap (0:15 – 0:45)

**Concept:** Side-by-side split screen — left panel shows a PDF abstract,
right panel shows what an AI model actually wrote as code.
Highlight overlay animates over key protocol sentences.

**Shot list:**
| Time | Shot | Description |
|------|------|-------------|
| 0:15 | Split screen | Left: journal PDF (Synthetic Biology, golden-gate paper). Right: Python code in dark terminal. Both static at first. |
| 0:20 | Amber highlight sweeps | On left, "add 2 µL plasmid DNA" is highlighted. On right, corresponding `p20.transfer(2, …)` line glows. |
| 0:27 | Red highlight (wrong side) | Right panel: `mix_after=(3, 10)` line appears highlighted in red. Left panel has no matching text — the step was hallucinated. |
| 0:33 | Annotation badge | Badge appears: "⚠ Phantom step — not in protocol". Teal border, white text. |
| 0:38 | Text card | *"AI models hallucinate wet-lab steps. The consequences are real."* |
| 0:43 | Transition | Split screen collapses. Fade to pipeline diagram. |

**VO / caption:** Optional whispered VO: *"The AI saw 'transformation.' It added a mix step. The competent cells were already compromised."*

---

## Scene 3 — Pipeline Walkthrough (0:45 – 1:30)

**Concept:** Animated infographic showing the full Text2WetLab pipeline,
with a real protocol (a1-a12-100ul oracle run) rendered as the demonstration.
Nodes appear left-to-right with connecting arrows.

**Shot list:**
| Time | Shot | Description |
|------|------|-------------|
| 0:45 | Black frame | Five pipeline nodes materialise one by one: **PDF → NL Protocol → IR (JSON) → Python → Simulation** |
| 0:53 | Zoom into IR node | A JSON snippet expands: `{"action":"transfer","volume":100,"from":"reservoir.A1","to":"plate.A1:A12"}` in teal monospace. |
| 1:00 | Zoom into Python node | Generated OT-2 code appears, syntax-highlighted: `p300.distribute(100, reservoir['A1'], plate.wells()[:12])` |
| 1:08 | Cross-fade to 3D render | Full 3D MuJoCo simulation — **asset: `assets/examples3d/a1-a12-100ul.mp4`** |
| 1:12 | Picture-in-picture | MuJoCo 3D render plays (full screen). Bottom-right PiP: oracle run frame strip — **asset: `results/a1-a12-100ul/oracle_run_frames.png`** |
| 1:18 | Reward badge animates | In corner: `reward: 1.000 ✓` in green. `sim_pass: true`. `12 commands` |
| 1:23 | Zoom to frame strip | Strip of oracle run frames — **asset: `results/a1-a12-100ul/oracle_run_frames.png`** — steps through the 12 dispense events |
| 1:28 | Text card | *"Every µL tracked. Every tip. Every well."* |

**2D IR visualisation B-roll:** `assets/examples/a1-a12-100ul.gif` — use as PiP overlay during pipeline explanation.

---

## Scene 4 — Three Task Examples (1:30 – 2:30)

### 4a — E. coli Heat Shock: The Phantom Mix (1:30 – 1:50)

**Concept:** Oracle run (correct) vs agent run (phantom mix) side-by-side. Both rendered in MuJoCo 3D.

| Time | Shot | Description |
|------|------|-------------|
| 1:30 | Title card | **"E. coli Heat Shock Transformation"** / subtitle: *"The Phantom Mix"* |
| 1:33 | 3D render (full width) | **`assets/examples3d/ecoli-heat-shock-transformation.mp4`** — the oracle run, pipette adds DNA gently, no mix. |
| 1:38 | Split to two panels | Left: "Oracle — correct" (green border). Right: "Fable / Opus — hallucinated mix" (red border). |
| 1:42 | Red annotation | Right panel: tip re-descends into cells, mixing begins. Red flash. Text: `mix(3, 10)` |
| 1:46 | Score cards | Oracle: `1.000`. Sonnet: `0.857`. Opus/Fable: `0.714`. Animate in. |
| 1:49 | Context badge | *"Mixing competent cells disrupts osmotic conditions. Transformation efficiency drops."* |

**Asset primary:** `assets/examples3d/ecoli-heat-shock-transformation.mp4`
**Asset secondary (L2 scripted):** `assets/examples3d/L2-ecoli-heat-shock-transformation.mp4`

---

### 4b — Golden Gate Assembly: Perfect at 33 Steps (1:50 – 2:10)

**Concept:** The most complex protocol in the benchmark, executed flawlessly by all models.
Show the full 3D render at speed, then a cascade of green check marks.

| Time | Shot | Description |
|------|------|-------------|
| 1:50 | Title card | **"Golden Gate Assembly"** / subtitle: *"Perfect at 33 Steps"* |
| 1:53 | 3D render (wide shot) | **`assets/examples3d/golden-gate-assembly.mp4`** — played at 2× speed, full screen. |
| 1:59 | Cascade check marks | 9 rubric items materialise as green ticks: `deck_and_hardware`, `pcr_setup`, `dpni_and_cleanup`, `assembly_mix`, `thermocycler_program`, `transformation`, `tips_contamination`, `robot_practice`, `fidelity_to_paper` |
| 2:04 | Reward triple stack | Three score cards animate side-by-side: Opus `1.000` / Sonnet `1.000` / Fable `1.000` |
| 2:07 | Text card | *"613 simulation commands. All three models. Zero failures."* |

**Asset primary:** `assets/examples3d/golden-gate-assembly.mp4`
**Asset secondary (L2 scripted):** `assets/examples3d/L2-golden-gate-assembly.mp4`
**2D IR B-roll:** `assets/examples/golden-gate-assembly.gif`

---

### 4c — RNA Extraction: The 20µL That Matters (2:10 – 2:30)

**Concept:** Elution step close-up. All models recover 100µL; the spec says ~80µL.
Visualise the bead pellet left behind — and what that means downstream.

| Time | Shot | Description |
|------|------|-------------|
| 2:10 | Title card | **"Opentrons RNA Extraction"** / subtitle: *"The 20µL That Matters"* |
| 2:13 | Code diff close-up | Red line: `p1000.transfer(ELUTION_VOL, …)  # 100 µL`. Green line: `p1000.transfer(80, …)  # ~80 µL ✓` |
| 2:17 | Colony PCR B-roll | **`assets/examples3d/L2-colony-pcr-screening.mp4`** — pipette approaching eluate well, slow push in |
| 2:21 | Annotation overlay | Arrow points to pellet zone at tip of pipette: "Bead carryover zone". Red highlight. |
| 2:24 | Consequence card | *"In clinical qPCR: beads inhibit polymerase → false negative → missed diagnosis."* |
| 2:27 | Score strip | All three models: `0.889`, `0.833`, `0.833`. `elution_recovery` rubric highlighted in amber. |

**2D IR B-roll:** `assets/examples/ecoli-heat-shock-transformation.gif` — bead wash sequence visualisation

---

## Scene 5 — Results Leaderboard Reveal (2:30 – 3:00)

**Concept:** Animated leaderboard bars grow from left to right, one at a time, with score
numbers counting up. Teal/amber colour coding per model.

| Time | Shot | Description |
|------|------|-------------|
| 2:30 | Black frame | Text: *"How do the models rank overall?"* |
| 2:34 | Leaderboard appears | Dark card, three rows. All bars at 0. |
| 2:37 | Bar 1 grows (amber) | `claude-opus-5-5` bar fills to 93.5%. Counter counts: `0.000 → 0.935`. |
| 2:42 | Bar 2 grows (teal) | `claude-sonnet-5-5` fills to 91.0%. Counter: `0.000 → 0.910`. |
| 2:47 | Bar 3 grows (violet) | `claude-fable-5-1` fills to 88.2%. Counter: `0.000 → 0.882`. |
| 2:52 | Per-task matrix fades in | Small grid — 3 models × 7 tasks. Cells colour from grey to green/amber cell-by-cell. |
| 2:57 | Key insight badge | *"All models exceed 0.88 mean reward. Hardest task: RNA extraction elution. Easiest: simple dispense."* |

**Visual spec:** Bars at 100px height. Font: Source Code Pro. Amber `#f59e0b`, teal `#14b8a6`, violet `#a78bfa`.

---

## Scene 6 — Call to Action (3:00 – 3:30)

**Concept:** Slow zoom out from pipette to full lab, then cut to clean dark card
with GitHub / bioRxiv / HuggingFace links.

| Time | Shot | Description |
|------|------|-------------|
| 3:00 | Zoom out | OT-2 tip retracts, robot arm parks. Lab goes still. |
| 3:05 | Text card | *"Text2WetLab is open source."* |
| 3:08 | Three-up CTA buttons | `★ GitHub`, `📄 bioRxiv`, `🤗 HuggingFace` appear with teal/amber highlight. |
| 3:12 | Repo card | GitHub repository card: `github.com/Tyronita/text2wetlab` — star count animates. |
| 3:18 | HF card | HuggingFace dataset card: `EvanOLeary/text2wetlab` — 7 protocols, simulation logs included. |
| 3:23 | Final text | *"Run it. Break it. Contribute."* — white on black, slow fade. |
| 3:27 | Logo hold | **Text2WetLab** wordmark + teal tagline: *"Because robots don't tolerate protocol errors."* |
| 3:30 | Fade to black | End. |

---

## Asset Index

| Scene | Asset path | Notes |
|-------|-----------|-------|
| 3 (hero 3D) | `assets/examples3d/a1-a12-100ul.mp4` | Oracle run, 12 dispenses |
| 3 (oracle frames) | `results/a1-a12-100ul/oracle_run_frames.png` | Frame strip for PiP overlay |
| 3 (best agent frames) | `results/a1-a12-100ul/best_run_frames.png` | Agent comparison strip |
| 3 (2D IR) | `assets/examples/a1-a12-100ul.gif` | 2D IR visualisation for PiP |
| 4a (ecoli 3D) | `assets/examples3d/ecoli-heat-shock-transformation.mp4` | Oracle run |
| 4a (ecoli L2) | `assets/examples3d/L2-ecoli-heat-shock-transformation.mp4` | Scripted close-up (to record) |
| 4b (golden-gate 3D) | `assets/examples3d/golden-gate-assembly.mp4` | Oracle run |
| 4b (golden-gate L2) | `assets/examples3d/L2-golden-gate-assembly.mp4` | Scripted wide shot (to record) |
| 4b (golden-gate 2D) | `assets/examples/golden-gate-assembly.gif` | 2D IR B-roll |
| 4c (colony-pcr L2) | `assets/examples3d/L2-colony-pcr-screening.mp4` | Elution close-up (to record) |
| 4c (ecoli 2D) | `assets/examples/ecoli-heat-shock-transformation.gif` | B-roll for bead wash |

> **Note:** `L2-*` assets are scripted camera angles intended for the recorded video production and do not yet exist as pre-rendered files. Use the base `assets/examples3d/*.mp4` files as stand-ins during the editing phase.

---

## Style Guide

| Element | Spec |
|---------|------|
| Background | `#07080d` (near-black) |
| Primary accent | Amber `#f59e0b` |
| Secondary accent | Teal `#14b8a6` |
| Error / wrong | Red `#ef4444` |
| Pass / correct | Green `#22c55e` |
| Body font | Source Sans 3, 400/600/700 |
| Code / data font | Source Code Pro, 400/600 |
| Title card timing | 3 s hold, 0.5 s fade in/out |
| Subtitle badge | Rounded rect, 1px border, semi-transparent bg |
| Min safe area | 10% margin all sides for title-safe cropping |
