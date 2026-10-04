# sources/<slug>/code/

Author-published scripts, kept to compare generated protocols against what was actually run at the bench.

**Never an input to `paper2protocol`** (`paper2protocol/guard.py` blocks code hosts and the pipeline never reads
this folder) **and never published to the dataset** (`scripts/deploy_hf.py` is an allowlist).

| Under `sources/` | Upstream | Licence | Simulates on Opentrons 7.5.0? |
|---|---|---|---|
| `dna-bot/code/` | BASIC-DNA-ASSEMBLY/DNA-BOT | MIT | no: needs the removed API v1 |
| `botany/code/` | cvoiniciuc/BOTany | none declared | no: needs API 2.20 and a runtime CSV |
| `transporter-screening/code/` | ljm176/TransporterScreening | none declared | no: needs a labware definition that is not here |
| `hulp-rna-extraction/code/` | HULPopentrons/RNA_extraction_OT2opentrons | none declared | yes (1,895 commands) |
| `slowpoke/code/` | Tom-Ellis-Lab/Slowpoke | MIT | yes, once `assemble.py` binds the shipped CSVs (colony PCR 949 commands (573 pipetting events), cloning 735 (575)) |

Each folder's README pins the upstream commit. `PROVENANCE.csv` records, for every file, the upstream URL and
whether its git blob hash matches upstream exactly (all 45 do). Files without a declared licence are for private
comparison only: do not redistribute them without the authors' permission.
