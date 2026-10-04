# Unstated information in input.nl.txt

| Given | Not given |
|---|---|
| 100 µL per well | Pipette model and capacity (decides how many times to re-aspirate) |
| Source = a 1-well reservoir | Reservoir volume |
| Destination = wells A1->A12 of a 96-well plate | Whether "A1->A12" is row A or a column-wise run |
| | Tip handling (pick up, drop) |
| | Whether to change tips |

The point of this task: 12 x 100 µL = 1200 µL is more than one load, so a correct protocol must
re-aspirate mid-run. See `tests/fixtures/L1_a1_a12/` for a good and a bad Opentrons run.
