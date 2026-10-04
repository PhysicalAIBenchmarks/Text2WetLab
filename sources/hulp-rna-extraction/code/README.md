# Reference · HULP SARS-CoV-2 RNA extraction (author-published OT-2 script)

**Comparison only. Not an input to `paper2protocol`, and not published in the dataset.**

- Paper: "Automated low-cost SARS-CoV-2 RNA extraction protocols", PLOS ONE 2021,
  doi:10.1371/journal.pone.0246302
- Repo: https://github.com/HULPopentrons/RNA_extraction_OT2opentrons
  commit `8703f8930b648c101c7dac6c9efc58fd01bc2358` (2020-07-12), `viral_rna_extraction_protocol.py` at the repo root
- Licence: **none declared** in the repo. Kept for private comparison only; do not redistribute
  without the authors' permission.
- `viral_rna_extraction_protocol.py` is byte-identical to that upstream blob. It was committed by
  lLegon in `dd91b7c` inside `out/10.1371_journal.pone.0246302/`, which holds generated output only,
  so it now lives here.

## Copies elsewhere in the repo

`tasks/L2/opentrons-rna-extraction/solution/protocol.py` and `.../tests/reference_protocol.py`
(commit `e1f87ca`, Mohammed Alshehri) are this same script with CRLF line endings converted to LF.
They are the Harbor task's oracle and hidden reference, so they are not an independent
re-implementation. See `PROVENANCE.csv`.
