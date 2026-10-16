# Infeasible on the Tecan Freedom EVO (MCA96)

Step 1 (2 µL of plasmid DNA from `plasmid_plate` A1 into the single competent-cell tube `tubes_1_5ml_1` A1) cannot be
done, and neither can step 3 (250 µL SOC into that one tube).
The MCA96 head always picks up and uses all 96 tips and moves the same volume in every tip at once; there is no
partial-tip pickup. It cannot aspirate from one well or dispense into one tube without the other 95 tips doing the
same, so every transfer here would hit 95 other positions.
