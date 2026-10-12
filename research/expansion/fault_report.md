### ecoli-heat-shock-transformation
- **Opus 5.5**: 
  - FAULT `mix` pipette-mixes tubes_1_5ml_1 A1 (oracle never mixes here)
- **Sonnet 5.5**: no faults vs oracle
- **Fable 5.1**: 
  - FAULT `mix` pipette-mixes tubes_1_5ml_1 A1 (oracle never mixes here)
### opentrons-rna-extraction
- **Opus 5.5**: 
  - FAULT `volume` 100 uL Extraction plate (slot 4) -> Elution plate per well; oracle 80 uL
  - note `timing` total waits 15 min vs oracle 28 min
  - note `magnet` magnet engaged 2x vs oracle 7x
- **Sonnet 5.5**: 
  - FAULT `order` adds samples 1-24 (slot 10) to sample plate before NEST 12 Well Reservoir 15 mL A2 (slot 5) (oracle order differs)
  - FAULT `volume` 79,680 uL total sample plate (slot 4) -> waste plate; oracle 75,600 uL (+5%)
  - FAULT `volume` 100 uL sample plate (slot 4) -> elution plate per well; oracle 80 uL
  - note `timing` total waits 15 min vs oracle 28 min
  - note `magnet` magnet engaged 2x vs oracle 7x
- **Fable 5.1**: 
  - FAULT `volume` 100 uL extraction plate (slot 4) -> elution plate per well; oracle 80 uL
  - note `timing` total waits 15 min vs oracle 28 min
  - note `magnet` magnet engaged 2x vs oracle 7x
### split-200ul-two-wells
- **Opus 5.5**: no faults vs oracle
- **Sonnet 5.5**: no faults vs oracle
- **Fable 5.1**: no faults vs oracle
### a1-a12-100ul
- **Opus 5.5**: no faults vs oracle
- **Sonnet 5.5**: no faults vs oracle
- **Fable 5.1**: no faults vs oracle
### colony-pcr-screening
- **Opus 5.5**: no faults vs oracle
- **Sonnet 5.5**: no faults vs oracle
- **Fable 5.1**: no faults vs oracle
### golden-gate-assembly
- **Opus 5.5**: no faults vs oracle
- **Sonnet 5.5**: no faults vs oracle
- **Fable 5.1**: no faults vs oracle
### ampure-bead-cleanup
- **Opus 5.5**: no faults vs oracle
- **Sonnet 5.5**: no faults vs oracle
- **Fable 5.1**: no faults vs oracle
