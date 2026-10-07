# Unstated information in input.nl.txt

Instruction: "Transform competent E. coli with 2 µL plasmid DNA per tube, heat shock at 42°C for 45 seconds, then add 250 µL SOC medium to each tube."

| Given | Not given |
|---|---|
| DNA volume: 2 µL | Competent cell volume (50 µL assumed) |
| Heat shock: 42°C, 45 s | Number of transformations / tube count |
| SOC volume: 250 µL | Plasmid plate layout |
| Source: plasmid plate → tubes | Recovery time and temperature after SOC addition |
| | Whether to mix after DNA addition (no vortex rule) |
| | Tip strategy (fresh tip per tube vs reuse) |
| | Whether robot or operator performs heat shock |

Each row on the right is a point where a model must assume a value or behaviour.
The heat shock step is a hard constraint: the OT-2 cannot perform it;
a correct translation must emit a `manual` pause step.

**Pinned for Harbor grading:** The plasmid is in well A1 of the plasmid plate and goes into the single competent-cell tube.
