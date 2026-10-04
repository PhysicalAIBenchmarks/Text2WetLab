# Reference · Slowpoke (author-published OT-2 workflows)

**Comparison only. Not an input to `paper2protocol`, and not published in the dataset.**

- Paper: Slowpoke, ACS Synthetic Biology, doi:10.1021/acssynbio.5c00629
- Repo: https://github.com/Tom-Ellis-Lab/Slowpoke
  commit `62648d2bf390c28af061d68cee71075e27c251a6` (2026-02-09)
- Licence: MIT (`LICENSE`)
- `Colony_PCR/` and `Cloning/` are the OT-2 workflow templates, their generators and their example CSV
  inputs, verbatim. `PROVENANCE.csv` records that each file is byte-identical to upstream.
- `assemble.py` is ours: it binds the CSVs into the templates the same way the authors' generators do,
  without the GUI. Both assembled protocols simulate on Opentrons 7.5.0 (colony PCR 949 commands (573 pipetting events), cloning 735 (575)).

What they do, from the simulator trace of the shipped example inputs:

| Workflow | Reactions | Main volumes |
|---|---:|---|
| Colony PCR | 96 | 9 µL mix + 1 µL colony template per reaction (10 µL, Green Taq) |
| Cloning (Golden Gate) | 14 combinations | 4.5 µL and 1 µL parts and enzyme, 25 µL and 50 µL stocks |

Neither matches the numbers of `tasks/colony-pcr-screening` (18 µL Q5 + 1 + 1) or of
`tasks/golden-gate-assembly` (AssemblyTron design). See `docs/criteria.md` and the task READMEs.
