# Infeasible on the Tecan Freedom EVO (MCA96)

Step 1 (100 µL from `reservoir` into `plate` wells A1:A12 only) cannot be done as specified.
The MCA96 head always picks up and uses all 96 tips and moves the same volume in every tip at once; there is no partial-tip (single row/column) pickup.
Any dispense into the plate therefore fills all 96 wells, so rows B-H would also receive 100 µL instead of staying empty.
