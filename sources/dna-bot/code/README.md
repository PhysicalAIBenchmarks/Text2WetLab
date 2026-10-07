# Reference · DNA-BOT (Storch et al. 2020) — author-published OT-2 scripts

**Gold standard for comparison only. Not an input to `paper2protocol`.**

These are the authors' own Opentrons scripts for the paper the pipeline was run on, kept so
generated protocols can be scored against what was actually executed at the bench.

## Provenance

- Paper: Storch, Haines & Baldwin, *DNA-BOT: a low-cost, automated DNA assembly platform for
  synthetic biology*, Synthetic Biology 5(1) ysaa010, 2020. doi:10.1093/synbio/ysaa010
- Repo: https://github.com/BASIC-DNA-ASSEMBLY/DNA-BOT branch `oup_synbio`,
  commit `ae9aebbd5833752cad981ecf99a52a6c6e7202e2`
- Licence: MIT (`LICENSE.DNA-BOT`), © 2019 Matthew Haines
- `scripts/` = `examples/construct_csvs/storch_et_al_cons/executed_scripts/` — the scripts
  actually run for the 88-construct experiment in the paper.
- `inputs/` = the construct/linker/part CSVs and the generated well maps for that run.

Scripts 1–3 are identical to the repo's generated versions; `4_transformation.ot2.py` was
hand-modified before execution (the paper notes controls added in wells A12–H12), and
`5_10_ul_spotting.ot2.py` was generated separately to spot 10 µl instead of 5 µl.

## Mapping to the paper and to the pipeline

The paper compresses the whole workflow into methods §2.3, so `identify` returns it as one
experiment. These five scripts are its stages:

| Script | Stage | Paper §2.3 detail |
|---|---|---|
| `1_clip.ot2.py` | clip reactions | 20 µl master mix + linkers + parts + H2O to 30 µl |
| `2_purification.ot2.py` | magnetic bead purification | 54 µl AMPure XP, 150 µl 70% ethanol washes, 38 µl eluate |
| `3_assembly.ot2.py` | assembly | 15 µl, 1.5 µl of each purified clip reaction |
| `4_transformation.ot2.py` | transformation + spotting | heat shock, 125 µl SOC, 1 h 37 °C, 5 µl spots |
| `5_10_ul_spotting.ot2.py` | spotting only | 10 µl spots |

## Why this is kept out of the pipeline

The pipeline's value is that it reconstructs a protocol from the paper's prose; if it could
read these scripts, its output would be a copy rather than evidence that the method is
recoverable. Two things keep them apart:

- The pipeline only ever reads fetched JATS XML and whatever `resolve` retrieves from the
  web. It never reads this repo, and nothing here is on its input path.
- `paper2protocol/guard.py` blocks code-hosting domains (github.com among them) in the web
  tools and flags any URL that looks like author code or supplementary files — this paper's
  §2.2 cites the repo URL in its text, so that check is load-bearing here. See
  `out/10.1093_synbio_ysaa010/exp*/web_access.json` for what each run actually fetched.

Do not use these files to tune pipeline prompts: that would leak the answer key indirectly.
Score against them after a run, and keep the scoring code separate from the pipeline.
