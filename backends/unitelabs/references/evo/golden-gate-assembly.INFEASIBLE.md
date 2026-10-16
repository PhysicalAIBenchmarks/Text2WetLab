# Infeasible on the Tecan Freedom EVO (MCA96)

Steps 1-6 already fail: building the PCR master mix in `tubes_1_5ml_1` D1 (106 µL water, 40 µL buffer, 4 µL dNTPs, 2 µL polymerase from individual tubes) and dispensing 19 µL into only `pcr_plate` A1:G1.
The MCA96 head always picks up and uses all 96 tips and moves the same volume in every tip at once; it cannot aspirate from or dispense into an individual tube, a subset of wells, or different wells with different volumes.
Later steps have the same problem (2.5 µL primers into A1:G1 only, 1 µL template from A1, A1, B1, C1, A1, A1, D1, single-fragment transfers from B1/E1/F1 into A1:D1, 250 µL LB into four wells), so the protocol cannot be run on this head.
