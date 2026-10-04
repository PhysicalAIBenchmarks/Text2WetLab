# URDF / MJCF Survey — PLR-Supported Machines and Lab-Context Arms

Survey date: 2026-10-04. All links verified via direct GitHub page fetch. "NO" means a systematic search of GitHub repository search (by name + urdf/xacro/mjcf terms), ROS index, and known organisation pages found nothing.

---

## Hamilton STAR / STARlet / VANTAGE

```
Machine: Hamilton STAR / STARlet / VANTAGE (liquid handler gantry)
URDF exists: NO
File/Repo: —
  File path: —
Simulator/API: —
Source library: —
Notes: GitHub repository search for "hamilton star urdf", "hamilton star mjcf", and
       "hamilton liquid handler simulation ROS" all returned 0 results. Neither the
       pyhamilton/pyhamilton repo nor any related community repo ships a URDF or MJCF.
       No ROS description package found on index.ros.org. As of survey date, no public
       kinematic model exists for the STAR-line gantry.
```

---

## Opentrons OT-2

```
Machine: Opentrons OT-2
URDF exists: NO
File/Repo: —
  File path: —
Simulator/API: —
Source library: —
Notes: The official opentrons/opentrons repo (edge branch) has no URDF, xacro, MJCF,
       or SDF files. The hardware/ subdirectory covers CAN-bus firmware communication
       only. The hypothetical repo "opentrons/ot2_description" returns HTTP 404.
       GitHub searches for "ot2 urdf", "opentrons OT-2 urdf", "opentrons OT-2 robot
       description ROS", and "opentrons mujoco/pybullet/isaac" all returned 0 results.
       No ROS package indexed.
```

---

## Opentrons Flex

```
Machine: Opentrons Flex
URDF exists: NO
File/Repo: —
  File path: —
Simulator/API: —
Source library: —
Notes: GitHub searches for "opentrons flex urdf OR xacro" and "opentrons flex ros2
       description" both returned 0 results. The opentrons/opentrons repo covers both
       OT-2 and Flex in its software stack but contains no robot kinematic model files.
       No MJCF or SDF alternative found.
```

---

## Tecan Freedom EVO

```
Machine: Tecan Freedom EVO
URDF exists: NO
File/Repo: —
  File path: —
Simulator/API: —
Source library: —
Notes: GitHub searches for "tecan freedom evo urdf" and "tecan evo ROS robot description"
       both returned 0 results. No manufacturer-provided or community URDF, MJCF, or SDF
       found for the EVO liquid handler.
```

---

## Brooks PreciseFlex 400

```
Machine: Brooks PreciseFlex 400 (SCARA robotic arm)
URDF exists: YES
File/Repo: https://github.com/RoboDrop/pf400_description
  File paths:
    urdf/pf400_standard_400.urdf       (400 mm reach, compiled URDF)
    urdf/pf400_standard_750.urdf       (750 mm reach)
    urdf/pf400_standard_1160.urdf      (1160 mm reach)
    urdf/pf400_extended_400.urdf       (extended variant, 400 mm)
    urdf/pf400_extended_750.urdf
    urdf/pf400_extended_1160.urdf
    urdf/pf400.urdf.xacro              (parameterised entrypoint)
    urdf/pf400_macro.xacro             (shared macro)
Simulator/API: Simulator-agnostic (portable URDF — no ROS dependency required).
               Compatible with any standard URDF importer. Xacro wrappers available
               for ROS composition but not mandatory. Includes SRDF files for MoveIt.
Source library: RoboDrop/pf400_description (third-party, not Brooks/Precise Robotics
                official). Repo notes "legacy meshes, documented approximations" for
                PF400; the PF400 entrypoints under urdf/ are kept for backward
                compatibility. The repo also bundles UR, Stäubli, KUKA, ABB GoFa,
                and FANUC CRX descriptions.
Notes: The PF400 entrypoints remain under urdf/ (legacy location). Variants cover
       Standard and Extended reach in 400/750/1160 mm travel. Mesh accuracy is
       described as approximate. No manufacturer-official URDF package was found
       (search "preciseflex ros description" returned 0 results).
```

---

## UFACTORY xArm 6

```
Machine: UFACTORY xArm 6 (6-axis collaborative arm)
URDF exists: YES
File/Repo (ROS2): https://github.com/xArm-Developer/xarm_ros2
  Package: xarm_description
  File path: xarm_description/urdf/xarm6/xarm6.urdf.xacro
  Also present:
    xarm_description/urdf/xarm6/xarm6.gazebo.xacro
    xarm_description/urdf/xarm6/xarm6.ros2_control.xacro
    xarm_description/urdf/xarm6/xarm6.transmission.xacro
    xarm_description/urdf/xarm6/xarm6_robot_macro.xacro
    xarm_description/urdf/xarm_device.urdf.xacro   (top-level single-arm entrypoint)
    xarm_description/urdf/dual_xarm_device.urdf.xacro
Simulator/API (ROS2): ROS2 + Gazebo + MoveIt2 + RViz2

File/Repo (ROS1): https://github.com/xArm-Developer/xarm_ros
  Package: xarm_description
  File path: xarm_description/urdf/xarm6/xarm6.urdf.xacro
  (identical sub-package structure to ROS2 repo)
Simulator/API (ROS1): ROS1 + Gazebo + MoveIt + RViz

Source library: xArm-Developer (official UFACTORY organisation on GitHub)
Notes: The xacro files use a macro pattern (xarm6_robot_macro.xacro) that the
       top-level xarm_device.urdf.xacro instantiates. Gazebo-specific properties
       are split into xarm6.gazebo.xacro. ros2_control interface defined in
       xarm6.ros2_control.xacro. Both repos are actively maintained by UFACTORY.
```

---

## Universal Robots UR3 / UR5 / UR10

```
Machine: Universal Robots UR3 / UR5 / UR10 (collaborative arms)
URDF exists: YES
File/Repo (ROS2 — official): https://github.com/UniversalRobots/Universal_Robots_ROS2_Description
  Package: ur_description
  File paths:
    urdf/ur.urdf.xacro          (single parameterised entrypoint — pass ur_type:=ur3/ur5/ur10)
    urdf/ur_macro.xacro         (macro definitions imported by above)
    urdf/ur_mocked.urdf.xacro   (mock-hardware variant)
    urdf/inc/ur_common.xacro
    urdf/inc/ur_joint_control.xacro
    urdf/inc/ur_sensors.xacro
    urdf/inc/ur_transmissions.xacro
  Supported ur_type values: ur3, ur5, ur10, ur3e, ur5e, ur7e, ur10e, ur12e, ur16e,
                             ur8long, ur15, ur18, ur20, ur30
Simulator/API (ROS2): ROS2 + RViz2 + Gazebo. Model-specific kinematics and limits
                      loaded from YAML config files at instantiation time.

File/Repo (ROS1 — ros-industrial): https://github.com/ros-industrial/universal_robot
  Package: ur_description (branch melodic-devel)
  File paths (per-model xacro, not parameterised):
    ur_description/urdf/ur3.xacro
    ur_description/urdf/ur5.xacro
    ur_description/urdf/ur10.xacro
    ur_description/urdf/ur3e.xacro
    ur_description/urdf/ur5e.xacro
    ur_description/urdf/ur10e.xacro
    ur_description/urdf/ur16e.xacro
    ur_description/urdf/ur.xacro   (shared base)
Simulator/API (ROS1): ROS1 + Gazebo + MoveIt + RViz

Source library (ROS2): UniversalRobots organisation — official Universal Robots.
                       Mesh files under manufacturer "Terms and Conditions."
Source library (ROS1): ros-industrial/universal_robot — community maintained,
                       de facto official; referenced by Universal Robots documentation.
Notes: The ROS2 package is single-file parameterised (ur_type argument); the ROS1
       package has one xacro file per model variant. Neither OT-2 nor Hamilton
       appears alongside these; this entry is included as a lab-context collaborative
       arm relevant to PyLabRobot integration scenarios.
```

---

## Summary Table

| Machine | URDF/MJCF | Repo | Simulator | Source |
|---|---|---|---|---|
| Hamilton STAR/STARlet/VANTAGE | NO | — | — | — |
| Opentrons OT-2 | NO | — | — | — |
| Opentrons Flex | NO | — | — | — |
| Tecan Freedom EVO | NO | — | — | — |
| Brooks PreciseFlex 400 | YES (URDF) | RoboDrop/pf400_description | Agnostic / any URDF importer | Third-party |
| UFACTORY xArm 6 | YES (xacro) | xArm-Developer/xarm_ros2 (ROS2), xArm-Developer/xarm_ros (ROS1) | ROS2+Gazebo+MoveIt2 / ROS1+Gazebo+MoveIt | Official UFACTORY |
| UR3 / UR5 / UR10 | YES (xacro) | UniversalRobots/Universal_Robots_ROS2_Description (ROS2), ros-industrial/universal_robot (ROS1) | ROS2+Gazebo / ROS1+Gazebo | Official UR / ros-industrial |

---

## Key Finding for PLR Embodiment Gap

The four PLR-native liquid handlers (Hamilton STAR, Opentrons OT-2, Opentrons Flex, Tecan Freedom EVO) have **zero public URDF/MJCF/SDF representations** as of October 2026. The robotic arms either already supported by PLR (xArm 6, PreciseFlex 400) or commonly paired with PLR workcells (UR3/5/10) all have official or well-maintained community URDF packages. This creates a clear gap: any embodied simulation of a PLR-driven workcell must either (a) author a novel URDF for the liquid handler deck geometry or (b) use a proxy geometry (box + gantry joint approximation).
