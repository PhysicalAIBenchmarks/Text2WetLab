# Unstated information in input.nl.txt

Instruction: "Clean up 50 µL PCR products using 0.8× AMPure XP magnetic beads: add 40 µL beads to each well, incubate 5 minutes, engage the magnet and remove the supernatant, wash twice with 200 µL 80% ethanol, dry 5 minutes, then elute in 50 µL nuclease-free water."

| Given | Not given |
|---|---|
| Sample volume: 50 µL | Magnetic engage/wait time (5 min assumed) |
| Bead ratio: 0.8× (40 µL) | Elution incubation time (2 min assumed) |
| Incubation: 5 min | Final eluate transfer volume (45 µL assumed) |
| Two ethanol washes: 200 µL each | Ethanol preparation details (freshly made assumed) |
| Air dry: 5 min | Magnetic module slot on deck |
| Elution: 50 µL water | Supernatant aspiration volume (90 µL = 40+50) |
| | Mix cycles for bead resuspension |
| | Whether a final magnet step precedes eluate transfer |

The aspiration side of the well matters for supernatant removal steps —
a correct translation must aspirate from the bead-free side (opposite the magnet).
The step count (13 steps) makes this the most complex L2 task in the benchmark.

**Pinned for Harbor grading:** Plates are filled across all 96 wells (A1:H12), one sample per well in the same position on every plate, because the instruction says 'each well' and gives no count.
