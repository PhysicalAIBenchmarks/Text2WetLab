# Unstated information in input.nl.txt (where a translation can go wrong)

The instruction only says: "200 uL was aliquoted".

| Given | Not given |
|---|---|
| Total volume (200 uL) | Concentration of the reagent |
| Source = "the reservoir" | Dilution (none specified) |
| Destination = "two wells on the plate" | Which two wells (A1/B1? A1/A2?) |
| | Per-well volume (100/100 is assumed, not stated) |
| | Where it was moved from and to, exactly |
| | Storage of the plate/reagent afterwards |
| | Tip handling (pick up, drop) |

Each row on the right is a point where a model must assume a value. Score assumptions
separately from the code.
