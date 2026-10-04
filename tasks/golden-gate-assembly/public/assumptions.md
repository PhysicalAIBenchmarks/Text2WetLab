# Unstated information in input.nl.txt

Instruction: "Set up Golden Gate assembly reactions: transfer DNA fragments to assembly wells at equimolar ratios, add BsaI-HF v2 and T4 DNA ligase master mix to each well, and top up to 20 µL total with nuclease-free water."

| Given | Not given |
|---|---|
| Equimolar fragment addition | Volume per fragment (depends on concentration) |
| Enzyme: BsaI-HF v2 + T4 ligase | Enzyme + buffer volumes per reaction |
| Total reaction volume: 20 µL | Thermocycler protocol after setup |
| Water used for top-up | Fragment source plate layout |
| | Number of reactions |
| | Whether to mix after final addition |
| | Tip strategy between fragments (carryover risk) |

Each row on the right is a decision point. Fragment volume is the hardest:
a correct translation must either read a design CSV or emit a `null` volume with a note,
not hardcode a single value. The thermocycler step is entirely missing from the NL.
