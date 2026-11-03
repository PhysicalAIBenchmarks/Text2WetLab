# Infeasible on the Agilent Bravo (96LT head)

In the paper's workflow, adding the recovery medium (250 µL of LB + 0.2% dextrose from `tubes_15ml_1` A1 into `cells_plate` A1:D1) cannot be done, and the
master-mix, DpnI and assembly water from `tubes_50ml_1` A1 has no clearance margin either.
The Bravo pipettes by lowering the whole head over a deck location. Its Z travel tops out at 161.8 mm above the
labware seat for the nozzles, and a mounted LT tip sticks out 46.6 mm (200 µL tip) or 50.7 mm (250 µL tip) below
the nozzle. That puts the highest the tip end can be raised at 115.2 mm (200 µL) or 111.1 mm (250 µL). A 15 mL
conical tube is 118.6 mm tall, so a tip cannot be carried over its rim and lowered into it. A 50 mL conical tube is
114.65 mm tall: it clears by 0.55 mm with 200 µL tips and not at all with 250 µL tips.
The recovery medium and the water sit in tubes the head cannot reach, so the workflow cannot be run on this instrument
as the labware is prepared.
