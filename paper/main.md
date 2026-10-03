# Text2WetLab: A Benchmark for Natural Language to Wet Lab Protocol Translation

*Authors: TODO*

## Abstract
TODO

## 1. Introduction (observation)
TODO: why NL -> protocol matters, and why we want the model to harbour an understanding of lab state, not just emit code.

## 2. Hypotheses
TODO: e.g. models drop implicit state (tip, re-aspirate) when the NL is underspecified.

## 3. Method (experiment)
- Pipeline: NL -> IR -> Python -> optional visualisation
- Vagueness levels L0-L2, tasks in `tasks/`
- Simulators: Opentrons simulate, PyLabRobot

## 4. Risk taxonomy
R1 physics (IR -> code), R2 translation (NL -> IR), R3-R15 TODO (see project notes).

## 5. Results (analysis)
TODO

## 6. Conclusion
TODO
