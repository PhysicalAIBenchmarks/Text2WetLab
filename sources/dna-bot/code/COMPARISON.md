# Comparison · generated protocol vs author scripts

Run of 2026-10-03, `paper2protocol` on 10.1093/synbio/ysaa010 experiment 1
(`out/10.1093_synbio_ysaa010/exp1/`), Sonnet 5.5 at the per-stage settings in `llm.STAGES`.
Scored by hand after the run; nothing here was fed back into the pipeline.

## Headline: the detail check was right

`resolve` returned **reject**, with one `missing` gap: *"volume and concentration of each
Biolegio half-linker added per clip reaction, and the volume of each 200 ng/µl part"*. The
reference scripts confirm those numbers exist only in the code, not in the paper:

| Quantity | Paper §2.3 | `scripts/1_clip.ot2.py` | Generated (forced) |
|---|---|---|---|
| Clip master mix per reaction | 20 µl | `MASTER_MIX_VOLUME = 20` | 20 µl ✓ |
| Master mix recipe per 20 µl | 3 µl ligase buffer, 1 µl BsaI-HF v2, 0.5 µl T4 ligase | prepared manually (not in script) | matches ✓ |
| Prefix half-linker | "plus Biolegio BASIC linkers" | `transfer(1, ...)` → **1 µl** | 2 µl ✗ (marked assumed) |
| Suffix half-linker | as above | `transfer(1, ...)` → **1 µl** | 2 µl ✗ (marked assumed) |
| DNA part | "and DNA parts" | `parts_vols` → **1 µl** | 1 µl ✓ (marked assumed) |
| Water per clip | "sufficient H2O to give 30 µl" | `water_vols` → **7 µl** | 5 µl ✗ (consistent with its own 2 µl linkers) |
| Clip total | 30 µl | 20+1+1+1+7 = 30 ✓ | 20+2+2+1+5 = 30 ✓ |

So the pipeline got the total right and the split wrong, which is exactly what the reject
predicted. The paper constrains the sum but not the terms.

Stages the paper *does* specify came out right:

| Quantity | Paper §2.3 | Reference script | Generated |
|---|---|---|---|
| Thermocycling | 20× (37 °C 2 min, 20 °C 1 min), then 60 °C 5 min | — (off-deck) | matches ✓ |
| AMPure XP beads | 54 µl | `2_purification.ot2.py` | 54 µl ✓ |
| Ethanol wash | 150 µl 70% | `2_purification.ot2.py` | 150 µl ✓ |
| Eluate transferred | 38 µl | `sample_number=38` wells, 38 µl elution | 38 µl ✓ |
| Assembly total | 15 µl | `TOTAL_VOL = 15` | 15 µl ✓ |
| Purified clip per assembly | 1.5 µl | `PART_VOL = 1.5` | 1.5 µl ✓ |
| SOC after heat shock | 125 µl, 1 h 37 °C lids off | `4_transformation.ot2.py` | matches ✓ |
| Spot volume | 5 µl (script 4), 10 µl (script 5) | both | 5 µl ✓ |

## Other gaps worth noting

- **Clips per construct.** The generated protocol assumed 7 (its critic flagged this as an
  assumption). `inputs/storch_et_al_cons_final_assembly_run_info.csv` shows **5** per
  construct, and `storch_et_al_cons.csv` has 10 linker/part columns used as 5 linker-part
  pairs. The 4.5 µl of assembly buffer it derived is therefore wrong (should be 15 − 5×1.5
  = 7.5 µl).
- **Plate layout.** The generated protocol used a 48-clip placeholder on A1:H6 with 1:1
  part/linker pairing. The real run has 38 unique clips with explicit per-clip source wells
  across two source plates. The layout lives in the CSVs, which the pipeline correctly
  refused to consult.
- **Heat shock.** `resolve` recovered 10 s at 42 °C for the C2987P 96-well plate from NEB's
  site; the paper only says "according to the manufacturer's instructions". Worth checking
  against `4_transformation.ot2.py`, which runs the heat shock off-deck.

## Guard check

`out/10.1093_synbio_ysaa010/exp*/web_access.json` has `flags: []` and zero github events for
both experiments, although §2.2 of the paper prints the repo URL. `resolve`'s own assessment
says the CSVs and `DNA-BOT_instructions_v1.0.0` "are deferred supplementary files and were
deliberately not consulted".
