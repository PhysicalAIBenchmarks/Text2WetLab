# Simulating the experimental candidates in Docker (2026-10-13)

Image `t2w-sim` (`docker/sim/`): Opentrons 7.5.0 (the benchmark's grader version) and PyLabRobot 0.2.2.
Protocols ran with `--network none`, read-only code and a non-root user. Each repo's custom labware JSON was passed to the simulator.

**795 Opentrons protocol files in 69 repos: 203 pass `opentrons_simulate`, 592 fail.** 32 repos have at least one passing protocol.

Hamilton: the har1eyk STARlet Automated Protein Extraction protocol (PyLabRobot) runs end to end on PyLabRobot's simulated backend (`docker/sim/hamilton_ape.py`): 936 liquid moves, 164 tip pickups, 10 CoRe-gripper plate moves to the magnet and back.

3D replay videos (not committed) are rendered on the host with `tools/replay_candidate.py` and `tools/hamilton_replay.py`.

| Repo | Pass | Fail |
|---|---|---|
| `tidytron` | 35 | 2 |
| `gfp-codon-burden-ot2` | 21 | 21 |
| `pvlab-solubility-dropcast-ot2` | 15 | 5 |
| `angelovangel-ot2-ngs` | 13 | 9 |
| `evogen-ot-library` | 13 | 12 |
| `opentrons-covid19-dev` | 12 | 40 |
| `nioz-ot2-database` | 11 | 191 |
| `biomationscripter` | 8 | 11 |
| `newcastle-neg-opentrons` | 8 | 26 |
| `ant-cloning` | 7 | 3 |
| `beckham-enzyme-pipeline` | 6 | 15 |
| `dtu-synbio-automation` | 6 | 4 |
| `ecoli-protein-expr-purif-ot2` | 6 | 15 |
| `locost-covid-nanopore-ot2` | 6 | 0 |
| `pudu-synbio-ot2` | 5 | 23 |
| `artic-normalisation-esr` | 4 | 7 |
| `massspecpreppy` | 3 | 7 |
| `amplicon-seq-bisanz` | 2 | 3 |
| `culturomics-isolation` | 2 | 9 |
| `detectr-covid-ot2` | 2 | 0 |
| `imperial-colony-picker` | 2 | 0 |
| `jubiotech-ot2-autoclone` | 2 | 5 |
| `msd-biochem-assays-ot2` | 2 | 0 |
| `trypanosomatid-drug-combo-ot2` | 2 | 1 |
| `ufdutton-16s-flex` | 2 | 15 |
| `worm-food-preference` | 2 | 0 |
| `damplab-taqpath-ot2` | 1 | 1 |
| `exfab-qiaseq-flex` | 1 | 0 |
| `hyrad-adna-capture` | 1 | 0 |
| `labop` | 1 | 2 |
| `openblend-media` | 1 | 1 |
| `prism-protocol-gen` | 1 | 0 |
| `ac-training-lab` | 0 | 1 |
| `ai4pd-flex-protein-purification` | 0 | 7 |
| `aliquot-niaid` | 0 | 13 |
| `blots-ot2` | 0 | 1 |
| `cayman-his-elisa` | 0 | 4 |
| `ester-library-synthesis` | 0 | 3 |
| `evotron-evolver-sampling` | 0 | 2 |
| `exposomics-384-flex` | 0 | 2 |
| `flat-agar-celegans-ot2` | 0 | 3 |
| `flex-genomics-di-omics` | 0 | 10 |
| `formulations-prep-shampoo` | 0 | 1 |
| `greenaway-halogenation` | 0 | 9 |
| `greenaway-mocs` | 0 | 5 |
| `greenaway-pocs` | 0 | 6 |
| `hydrogel-crosslink-ot2` | 0 | 1 |
| `labscriptai-protein-eng` | 0 | 11 |
| `llm-rdf-synthesis` | 0 | 1 |
| `lucks-cellfree-biosensor` | 0 | 1 |
| `lysostaphin-turbidity` | 0 | 1 |
| `metclo-ot2` | 0 | 1 |
| `myrplate-flex-casting` | 0 | 3 |
| `ot2-cherrypick` | 0 | 1 |
| `ot2-proteomics-thesis` | 0 | 12 |
| `ot2-yeast-spot-assay` | 0 | 3 |
| `pac832-galr1-ot2` | 0 | 31 |
| `pasta-spatial` | 0 | 1 |
| `peg-solubility-assay` | 0 | 2 |
| `plant-phenotyping-ot2` | 0 | 2 |
| `polar-sarscov2-ot2` | 0 | 2 |
| `retro-10x-ot2` | 0 | 1 |
| `roboctab` | 0 | 2 |
| `robotic-titration-cv-ot2` | 0 | 3 |
| `roche-pipetting-performance-ot2` | 0 | 2 |
| `rtwizard-antigen-ot2` | 0 | 7 |
| `sapp-dmx-protein-design` | 0 | 1 |
| `tape-organoid-barcoding` | 0 | 7 |
| `vadr-vacuum-miniprep-flex` | 0 | 1 |
