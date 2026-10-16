# Infeasible on the Tecan Freedom EVO (MCA96)

The first PCR setup step already fails: assembling the PCR master mix in `tubes_1_5ml_1` D1 from the individual reagent tubes and dispensing it into only the seven fragment wells `pcr_plate` A1:G1.
The MCA96 head always picks up and uses all 96 tips and moves the same volume in every tip at once; it cannot aspirate from or dispense into an individual tube, a subset of wells, or different wells with different volumes.
The later steps (per-fragment primers and templates into A1:G1, DpnI digest, backbone and insert fragments into four assembly wells, transformation into four cell wells) have the same problem, so the protocol cannot be run on this head.
