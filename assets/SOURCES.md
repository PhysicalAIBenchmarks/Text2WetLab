# 3D Model Sources

Equipment models used in Text2WetLab simulation.

---

## Opentrons OT-2 Robot

| File | Format | URL | License |
|---|---|---|---|
| OT-2 Reference Model Detailed | STL | [Opentrons/ot2 → reference-model/STL/](https://github.com/Opentrons/ot2/blob/master/reference-model/STL/OT-2%20Reference%20Model%20Detailed.STL) | Apache-2.0 |
| OT-2 Reference Model Basic | STL | [Opentrons/ot2 → reference-model/STL/](https://github.com/Opentrons/ot2/blob/master/reference-model/STL/OT-2%20Reference%20Model%20Basic.STL) | Apache-2.0 |
| OT-2 Full Parametric CAD | STEP | [Opentrons/ot2 → reference-model/STEP/](https://github.com/Opentrons/ot2/blob/master/reference-model/STEP/OT-2%20Reference%20Model%20Detailed.STEP) | Apache-2.0 |

> No official URDF exists. To generate one: STEP → FreeCAD URDF exporter → add arm joints manually.
> The STEP file is the best source for a full articulated URDF.

---

## Opentrons Flex

No public STL/STEP/URDF. Hardware is no longer open-source (software/firmware only).

---

## Hamilton STAR / STARlet

| File | Format | URL | License |
|---|---|---|---|
| STARlet accessories (tip adapters, holders) | OpenSCAD→STL | [21st-BIO/starlet-accessories](https://github.com/21st-BIO/starlet-accessories) | MIT |

> Full robot body: no public model. Proprietary.

---

## Standard Labware (generatable from JSON)

**Key source**: Opentrons `shared-data` JSON definitions encode the full geometry of every supported labware item — outer bounding box, per-well XYZ positions, depth, diameter, shape.

| JSON definitions | URL | License |
|---|---|---|
| All Opentrons labware (v2) | [Opentrons/opentrons → shared-data/labware/definitions/2/](https://github.com/Opentrons/opentrons/tree/edge/shared-data/labware/definitions/2) | Apache-2.0 |

Covers: `corning_96_wellplate_360ul_flat`, `agilent_1_reservoir_290ml`, `opentrons_96_tiprack_1000ul`, `opentrons_96_tiprack_20ul`, and 100+ others.

**The bridge** (`eval/generate_labware_stl.py`): parse these JSON specs → emit OBJ/STL meshes procedurally (~100 lines, trimesh). This is our contribution.

Additional standalone models:

| Item | Format | URL | License |
|---|---|---|---|
| 96-well microplate (SBS standard) | STL | [NIH 3D Print Exchange #3dpx-000303](https://3d.nih.gov/entries/3dpx-000303) | CC0 |
| 96-well plate (Corning dimensions) | STL | [cults3d.com](https://cults3d.com/en/3d-model/various/standard-96-well-microtiter-plate) | CC BY-SA |

---

## Richer Asset Collections (2025–2026 papers)

| Project | Format | URL | Assets | Notes |
|---|---|---|---|---|
| **Pipette** (arxiv 2606.12936) | USDZ | GitHub not yet public | 55 lab consumables, 26 equipment, 3 robot embodiments | Best single source when released; USD = Isaac Sim / Gazebo ready |
| **LabUtopia** (NeurIPS 2025) | USD/mesh | [Rui-li023/LabUtopia](https://github.com/Rui-li023/LabUtopia) | 200+ lab scenes | `git lfs pull` required; chemistry focus |
| **RoboCulture** (arxiv 2505.14941) | STL | [ac-rad/roboculture → cad-models/](https://github.com/ac-rad/roboculture) | tip remover, rack top | Franka setup, not OT-2 |

---

## Download script

```bash
# Pull OT-2 STL
wget -P assets/stl/ \
  "https://github.com/Opentrons/ot2/raw/master/reference-model/STL/OT-2%20Reference%20Model%20Detailed.STL"

# Pull all labware JSON definitions
git clone --depth 1 --filter=blob:none --sparse \
  https://github.com/Opentrons/opentrons.git /tmp/opentrons-shared
cd /tmp/opentrons-shared && git sparse-checkout set shared-data/labware/definitions/2
cp -r /tmp/opentrons-shared/shared-data/labware/definitions/2 assets/labware_defs/
```
