# Results

Harbor trials on Docker (colima), Claude Code agent, pass@1 (single attempt per task), grader as committed.

| Task | Grader | Oracle | sonnet-5-5 mean (n) | Attacks that scored 1.0 |
|---|---|---|---|---|
| `a1-a12-100ul` | deterministic end-state checker | 1.0 | 1.000 (1) | 0 |
| `ampure-bead-cleanup` | deterministic end-state checker | 1.0 | 0.000 (1) | 0 |
| `colony-pcr-screening` | deterministic end-state checker | 1.0 | 1.000 (1) | 0 |
| `ecoli-heat-shock-transformation` | deterministic end-state checker | 1.0 | 1.000 (1) | 0 |
| `golden-gate-assembly` | deterministic end-state checker | 1.0 | 0.433 (1) | 0 |
| `opentrons-rna-extraction` | LLM judge + 16 checks | 0.9444 | 0.889 (1) | n/a |
| `split-200ul-two-wells` | deterministic end-state checker | - | 1.000 (1) | 0 |

**All tasks:** sonnet-5-5 mean 0.760 over 7 trials

