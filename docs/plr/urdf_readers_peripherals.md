# URDF / MJCF / SDF Survey: PLR Peripheral Instruments

**Date:** 2026-10-04  
**Scope:** GitHub and web search for robot description files (URDF, xacro, MJCF, SDF, USD) covering the PLR-supported readers, peripherals, and workcell-level scene descriptions.

---

## Per-Instrument Results

---

### Machine: BMG CLARIOstar (plate reader)
**URDF exists:** NO  
**File/Repo:** —  
**Simulator/API:** —  
**Source library:** —  
**Notes:** No URDF, MJCF, SDF, or mesh found anywhere on GitHub or in vendor repos. BMG Labtech has no public simulation assets. Not referenced in any lab automation digital twin project.

---

### Machine: BioTek / Agilent Synergy H1 / Cytation 5 (plate reader / imager)
**URDF exists:** NO  
**File/Repo:** —  
**Simulator/API:** —  
**Source library:** —  
**Notes:** No simulation files found. Cytation 5 appears in metadata for Cell Painting datasets (broadinstitute/cellpainting-gallery-metadata) as an imaging platform name only, not in any scene description file.

---

### Machine: Tecan Spark (plate reader)
**URDF exists:** NO  
**File/Repo:** —  
**Simulator/API:** —  
**Source library:** —  
**Notes:** Tecan Spark appears extensively in eLife/bioRxiv experimental methods XML, and in PLR driver code, but no URDF, MJCF, or SDF has been published anywhere. Tecan does not release CAD/simulation assets publicly.

---

### Machine: Molecular Devices ImageXpress Pico / Nano (imager)
**URDF exists:** NO  
**File/Repo:** —  
**Simulator/API:** —  
**Source library:** —  
**Notes:** PLR has a gRPC/SiLA 2 backend for the ImageXpress Pico (`pylabrobot/legacy/microscopes/molecular_devices/pico/backend.py`). Fractal analytics and bioio have readers for ImageXpress image formats. No simulation asset found.

---

### Machine: Applied Biosystems QuantStudio 5 (qPCR)
**URDF exists:** NO  
**File/Repo:** —  
**Simulator/API:** —  
**Source library:** —  
**Notes:** No URDF or simulation scene files found. QuantStudio devices appear only in protocol/data context, not in robot description files.

---

### Machine: Thermo Cytomat 2 / 10 (incubator hotel)
**URDF exists:** NO  
**File/Repo:** —  
**Simulator/API:** —  
**Source library:** —  
**Notes:** `smartlab-network/open-cytomat` provides a Python serial/CLI driver for the Cytomat (https://github.com/smartlab-network/open-cytomat). `stefangolas/olaf` has a minimal Python class. Neither contains URDF or meshes. No vendor-published simulation asset found.

---

### Machine: Liconic STX (incubator)
**URDF exists:** NO  
**File/Repo:** —  
**Simulator/API:** —  
**Source library:** —  
**Notes:** Liconic STX88 is listed in the AD-SDL BIO_workcell README as one of 6 instruments, but that repo contains no URDF. No simulation files found anywhere.

---

### Machine: Inheco ODTC / CPAC (thermal cycler / heater)
**URDF exists:** NO  
**File/Repo:** —  
**Simulator/API:** —  
**Source library:** —  
**Notes:** `F9R/ihcpmslib-wrappers` (https://github.com/F9R/ihcpmslib-wrappers) provides SiLA Python wrappers for the Inheco ODTC, but contains no simulation files. No URDF or mesh found anywhere.

---

### Machine: Azenta a4S sealer / XPeel (plate sealer / peeler)
**URDF exists:** NO  
**File/Repo:** —  
**Simulator/API:** —  
**Source library:** —  
**Notes:** Azenta a4S appears in the AD-SDL BIO_workcell instrument list but that repo has no URDF. No simulation asset found elsewhere.

---

### Machine: Formulatrix Mantis (dispenser)
**URDF exists:** NO  
**File/Repo:** —  
**Simulator/API:** —  
**Source library:** —  
**Notes:** `calico/vworks-mantis-plugin` (https://github.com/calico/vworks-mantis-plugin) provides a .NET COM driver for VWorks integration. `jensenlab/PlatePlan` has a worklist generator. No URDF or mesh in either repo. No simulation asset found.

---

### Machine: BTX Gemini X2 (electroporator)
**URDF exists:** NO  
**File/Repo:** —  
**Simulator/API:** —  
**Source library:** —  
**Notes:** BTX Gemini X2 appears only in experimental methods text (monarch-initiative/dismech references cache). No simulation or robot description files found anywhere.

---

### Machine: HighRes Biosolutions / Agilent BenchCel (plate mover / centrifuge loader)
**URDF exists:** NO  
**File/Repo:** —  
**Simulator/API:** —  
**Source library:** —  
**Notes:** PLR has a full driver for the BenchCel 4R (`pylabrobot/agilent/benchcel/`) and a resource model (`stacks.py`), but this is a Python resource geometry description, not a 3D scene file. No URDF, MJCF, or mesh found.

---

## Workcell-Level Scene Files

---

### cccoolll/digital-lab
**URL:** https://github.com/cccoolll/digital-lab  
**URDF exists:** YES — multiple versioned workcell URDFs  
**Simulator:** ROS (Gazebo-compatible URDF, SolidWorks-exported)  
**Files:**
- `Digital_twin_lab-2/urdf/Digital_twin_lab-2.urdf` — Dorna arm + microplate_incubator + squid (open-source microscope)
- `Digital_twin_lab-3/urdf/Digital_twin_lab-3.urdf` — Dorna arm + incubator + squid
- `digital-twin-lab-v4/urdf/digital-twin-lab-v4.urdf` — arm + plate-incubator + plate-microscope
- `SimulatedLab-urdf-no-robotic-arm/urdf/` — static scene without arm

**Instruments included:** Dorna robot arm; generic plate incubator; Squid open-source microscope (not any of the target commercial instruments). No manufacturer names in URDF — all links are generic ("incubator", "squid", "plate-microscope").  
**Notes:** STL meshes are SolidWorks exports. The "squid" refers to the open-source Squid microscope (Hong Lim lab, Berkeley/Stanford), not any commercial imager. This is likely related to the AICell Lab (Wei Ouyang, KTH) biology automation project. The URDFs are static workcell layouts for visualisation/motion planning; no physics properties on instrument bodies.

---

### aicell-lab/web-demo
**URL:** https://github.com/aicell-lab/web-demo  
**URDF exists:** YES — mirrors cccoolll/digital-lab versioned URDFs  
**Simulator:** ROS (same SolidWorks exports)  
**Files:**
- `packages/digital_twin_lab-4/urdf/robot_arm.urdf` — Dorna arm + incubator + squid (v3 layout)
- `packages/digital-twin-lab-v4-no-arm/urdf/` — static scene

**Notes:** Same instrument set as cccoolll/digital-lab above. Web-based viewer demo. No commercial PLR target instruments.

---

### maeloria/incubator_ws
**URL:** https://github.com/maeloria/incubator_ws  
**URDF exists:** YES — custom DIY incubator  
**Simulator:** ROS2  
**Files:** `src/incubator_description/urdf/incubator.urdf.xacro`, `incubator_form.xacro`  
**Notes:** Custom DIY thermal incubator (0.53 × 0.37 × 0.33 m) with fan and heat bed. Not a commercial plate hotel. Appears to be an MS thesis project. Not related to any PLR target instrument.

---

### AccelerationConsortium/Matterix
**URL:** https://github.com/AccelerationConsortium/Matterix  
**URDF exists:** NO (uses USD / Isaac Sim format, not URDF/MJCF)  
**Simulator:** NVIDIA Isaac Sim / Isaac Lab  
**Notes:** Digital twin framework for chemistry lab automation. Asset library (`matterix_assets`) includes Python-defined equipment (only IKA plate shaker found in code), robots (Franka arms), beakers, and infrastructure (tables). Assets are loaded as USD files from an external data submodule, not stored as URDF/SDF/MJCF in the public repo. No PLR target instruments found.

---

### AD-SDL/BIO_workcell
**URL:** https://github.com/AD-SDL/BIO_workcell  
**URDF exists:** NO  
**Simulator:** —  
**Instruments in workcell:** Hudson PlateCrane EX, Hudson SOLO liquid handler, Hidex Sense microplate reader, Azenta a4S plate sealer, Azenta plate seal remover, LiCONiC SToreX STX88 automated incubator  
**Notes:** Repo contains Python control drivers and WEI workflow definitions only. No URDF, SDF, MJCF, or mesh files. Two PLR target instruments listed (Azenta a4S, Liconic STX) but no simulation assets.

---

### AD-SDL/MADSci
**URL:** https://github.com/AD-SDL/MADSci  
**URDF exists:** NO  
**Simulator:** —  
**Notes:** Modular lab automation framework. `examples/example_lab/example_modules/platereader.py` is a **fake/stub** plate reader for testing, no specific model. No simulation scene files found anywhere in repo.

---

### pharmbio/aros and pharmbio/robotlab
**URL:** https://github.com/pharmbio/aros, https://github.com/pharmbio/robotlab  
**URDF exists:** NO  
**Simulator:** —  
**Notes:** AROS is a landing page linking component repos (robot arm, incubator door, plate shaker). `robotlab` contains Python drivers for BioTek dispenser/washer, Squid/Nikon microscopes, fridge, barcode scanner. Cell Painting workcell. No URDF, MJCF, or SDF found anywhere.

---

### Oluwaseun-O-Ajayi/lab-automation-digital-twin
**URL:** https://github.com/Oluwaseun-O-Ajayi/lab-automation-digital-twin  
**URDF exists:** NO  
**Simulator:** Abstract/computational only  
**Notes:** Models lab devices (storage, liquid handlers, incubators, centrifuges, plate readers, transport robots) as abstract computational entities with capacity/processing-time properties. Explicitly does not simulate physical kinematics or collision. No 3D files.

---

## Summary: Key Findings

**Bottom line:** No URDF, MJCF, SDF, or USD scene description exists for any of the 12 target PLR instruments (BMG CLARIOstar, BioTek Synergy/Cytation, Tecan Spark, ImageXpress Pico/Nano, QuantStudio 5, Cytomat 2/10, Liconic STX, Inheco ODTC/CPAC, Azenta a4S/XPeel, Formulatrix Mantis, BTX Gemini X2, HighRes BenchCel).

**Only workcell URDFs found** are from the AICell Lab / cccoolll project, which models a custom biology workcell with a Dorna arm, generic plate incubator, and Squid microscope — not the commercial instruments targeted here.

**Reasons for the gap:**
1. Most lab instrument vendors (BMG, BioTek/Agilent, Tecan, Molecular Devices, Thermo, Liconic, Inheco, Azenta, Formulatrix) do not publish simulation assets.
2. Lab automation SDLs (AD-SDL, pharmbio, MADSci) provide Python drivers and workflow engines but not physics-based scene descriptions.
3. The Acceleration Consortium's Matterix targets Isaac Sim/USD format (not URDF/MJCF) and focuses on beakers + Franka arm, not PLR peripherals.
4. No ROS2 package found that includes scene URDFs for a complete biology workcell with multiple commercial instruments.

**Closest existing resources:**
- cccoolll/digital-lab: real workcell URDFs, wrong instruments (Dorna + Squid microscope)
- Matterix: correct target domain (chemistry), wrong format (USD not URDF), limited instrument set
- AD-SDL/BIO_workcell: correct instruments listed, no simulation files

**Implication for PLR embodiment paper:** There are essentially no ready-made URDF/MJCF assets for the PLR peripheral instruments. New assets would need to be created from scratch (CAD → URDF/MJCF pipeline) or from vendor-supplied CAD files if obtainable under NDA.
