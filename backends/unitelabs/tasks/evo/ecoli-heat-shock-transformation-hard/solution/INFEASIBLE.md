# Infeasible on the Tecan Freedom EVO (MCA96)

The first transfer already fails: 1 µL of each plasmid from `plasmid_plate` A1:H1 into only the eight cell wells
`transformation_plate` A1:H1, and later 50 µL SOC into those same eight wells.
The MCA96 head always picks up and uses all 96 tips and moves the same volume in every tip at once; there is no
partial-tip pickup, so it cannot address a single column. Every dispense would also land in columns 2-12, which hold
no cells.
