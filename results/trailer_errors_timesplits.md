# Trailer time splits

`results/trailer_errors.mp4`, built by `scripts/make_trailer_errors.py`. Total 1:58.0.

| Time | Length | Scene | On screen |
|---|---|---|---|
| 0:00.0 - 0:05.0 | 5 s | `title` | Title: can an AI agent turn a paper into a correct robot protocol? |
| 0:05.0 - 0:13.0 | 8 s | `gap` | The reproducibility gap: text -> AI breakdown -> AI code -> replay, vs ground truth |
| 0:13.0 - 0:21.0 | 8 s | `ex1_text` | Ex1 task text | AI breakdown (step 1 note: 'Gently flick to mix, no vortex') |
| 0:21.0 - 0:33.0 | 12 s | `ex1_code` | Ex1 AI code (line 23 mix_after boxed red) | agent replay, red while it mixes the cells (1.5-4.0 s) |
| 0:33.0 - 0:45.0 | 12 s | `ex1_truth` | Ex1 ground-truth oracle (no mix) vs agent (red during mix) + materials and impact |
| 0:45.0 - 0:54.0 | 9 s | `ex2_text` | Ex2 paper p4 (elution steps highlighted) | AI breakdown (step 36 '100 µL assumed' boxed red) |
| 0:54.0 - 1:07.0 | 13 s | `ex2_code` | Ex2 AI code (recover ELUTION_VOL=100 boxed red) | agent replay cued to recovery (t=527 s), red throughout |
| 1:07.0 - 1:21.0 | 14 s | `ex2_truth` | Ex2 authors' code (transfer 80 µL with side_shift) + their run, teal at recovery (t=487 s) + materials and impact |
| 1:21.0 - 1:28.0 | 7 s | `ex3_text` | Ex3 paper p3 step 1 (order highlighted) | AI breakdown steps 21-23 in order (teal) |
| 1:28.0 - 1:38.0 | 10 s | `ex3_code` | Ex3 AI code (sample-first loop boxed red) | agent replay, red from the first sample transfer (1.2 s) |
| 1:38.0 - 1:49.0 | 11 s | `ex3_truth` | Ex3 authors' run (beads first, teal) vs agent (sample first, red) + materials and impact |
| 1:49.0 - 1:58.0 | 9 s | `results` | R7 results: all three models 0.943; cost $1.25 / $0.39 / $3.43; links |
