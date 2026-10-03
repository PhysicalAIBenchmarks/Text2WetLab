---
language:
- en
license: apache-2.0
task_categories:
- text-generation
- translation
tags:
- biology
- lab-automation
- robotics
- liquid-handling
- opentrons
- benchmark
pretty_name: Text2WetLab
size_categories:
- n<1K
---

# Text2WetLab

**Natural language → wet lab robot protocol benchmark**

Evaluates whether language models can translate plain-English lab instructions
into correct, safe, executable liquid-handling protocols for the Opentrons OT-2.

## Task

Given a natural language instruction (at varying levels of specificity),
generate a valid Opentrons Python API v2 protocol that passes all 6 evaluation criteria:

| # | Criterion |
|---|---|
| T1 | Pick up tip before any aspirate |
| T2 | Aspirate correct volume |
| T3 | Two dispenses from single tip load |
| T4 | Drop tip when finished |
| T5 | No overdispense |
| T6 | No over-capacity aspirate |

## NL Vagueness Levels

| Level | Example |
|---|---|
| L0 (fully specified) | "Pick up a tip, aspirate 200µL from the reagent trough, dispense 100µL into A1 then 100µL into B1, throw the tip away." |
| L1 (volume only) | "Move 200 microlitres from the reservoir into two wells on the plate." |
| L2 (intent only) | "Aliquot the reagent into two wells." |

## Simulation

Protocols are evaluated using PyLabRobot 0.2.2 (ChatterBox backend) with
explicit volume assertions for T2–T6, and optionally `opentrons_simulate` for full validation.

## Citation

```
@misc{text2wetlab2026,
  title  = {Text2WetLab: A Benchmark for Natural Language to Wet Lab Protocol Translation},
  author = {O'Leary, Evan},
  year   = {2026},
  url    = {https://github.com/Tyronita/Text2WetLab}
}
```
