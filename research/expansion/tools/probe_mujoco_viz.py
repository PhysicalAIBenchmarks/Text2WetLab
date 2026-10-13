"""Empirical checks of opentrons-mujoco-viz (run with the interpreter that has it and mujoco installed).

    python probe_mujoco_viz.py <opentrons_simulate> <protocol.py>  >  mujoco_viz_probe.json

Measures rather than reads: which cameras render, whether the gantry reaches the position it is commanded to
(by joint name, within the step budget apply_event uses and after six more seconds), what stops it (gravity and
contacts toggled), what the liquid bookkeeping accepts, and what the package's own log parser gets from real
Opentrons output.
"""
import json, subprocess, sys
import mujoco
from opentrons.visualization import WetLabScene, parse_simulate_output
from opentrons.visualization.scene import SLOT_XY, WORK_Z, SAFE_Z

out = {}
with WetLabScene() as s:
    m, d = s.model, s.data
    q = lambda n: round(float(d.qpos[m.jnt_qposadr[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, n)]]), 4)
    tip = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_GEOM, "pip_tip")
    out["model"] = dict(bodies=int(m.nbody), geoms=int(m.ngeom), joints=int(m.njnt), actuators=int(m.nu), cameras=int(m.ncam),
                        meshes=int(m.nmesh), timestep_s=float(m.opt.timestep),
                        geoms_with_collision_enabled=sum(1 for i in range(m.ngeom) if m.geom_contype[i] or m.geom_conaffinity[i]))
    out["joint_ranges_m"] = {mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_JOINT, i): [round(float(x), 3) for x in m.jnt_range[i]] for i in range(m.njnt)}
    cams = {mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_CAMERA, i): round(float(s.render(mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_CAMERA, i)).mean()), 2)
            for i in range(m.ncam)}
    cams["free (fallback)"] = round(float(s.render("free").mean()), 2)
    out["camera_mean_brightness_0_255"] = cams

    rows = {}
    for slot in range(1, 13):
        sx, sy = SLOT_XY[slot]
        s.move_to_slot(slot, work=True, steps=100)
        budget = [q("j_x"), q("j_y"), q("j_z")]
        for _ in range(3000):
            mujoco.mj_step(m, d)
        tx, ty, tz = (round(float(v), 3) for v in d.geom_xpos[tip])
        rows[slot] = dict(commanded_joint_xyz=[round(sx, 3), round(sy - 0.17, 3), WORK_Z], joint_xyz_after_apply_event_budget=budget,
                          joint_xyz_after_6s_more=[q("j_x"), q("j_y"), q("j_z")], slot_centre_xy=[sx, sy], tip_xy=[tx, ty],
                          tip_error_mm=round(1000 * ((tx - sx) ** 2 + (ty - sy) ** 2) ** 0.5, 1), tip_z=tz, contacts=int(d.ncon))
        s._move_to(d.ctrl[s._ax], d.ctrl[s._ay], SAFE_Z, steps=200)
    out["gantry_by_slot"] = rows

    wells = {}
    for w in ("A1", "H12"):
        s.apply_event({"type": "dispense", "volume": 10, "slot": 2, "well": w})
        s.move_to_slot(2, work=True)
        wells[w] = [q("j_x"), q("j_y"), q("j_z")]
    out["joint_xyz_for_two_wells_in_slot_2"] = wells

    zb = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, "z_column")
    z = {"z_column_mass_kg": round(float(m.body_subtreemass[zb]), 3)}
    for name, target in (("SAFE_Z", SAFE_Z), ("WORK_Z", WORK_Z)):
        s._move_to(0.152, -0.17, target, steps=2000)
        z[name] = dict(commanded=target, j_z=q("j_z"), tip_z=round(float(d.geom_xpos[tip][2]), 4), contacts=int(d.ncon),
                       actuator_force_N=round(float(d.actuator_force[s._az]), 1))
    m.opt.gravity[:] = 0
    s._move_to(0.152, -0.17, SAFE_Z, steps=2000)
    z["SAFE_Z, gravity off"] = dict(commanded=SAFE_Z, j_z=q("j_z"), contacts=int(d.ncon))
    m.opt.disableflags |= mujoco.mjtDisableBit.mjDSBL_CONTACT
    s._move_to(-0.152, -0.17, SAFE_Z, steps=2000)
    z["contacts off"] = dict(commanded_xyz=[-0.152, -0.17, SAFE_Z], joint_xyz=[q("j_x"), q("j_y"), q("j_z")])
    s._move_to(0.152, -0.17, SAFE_Z, steps=100)
    z["contacts off, x after the 100-step budget"] = dict(commanded=0.152, j_x=q("j_x"))
    out["what_stops_the_gantry"] = z

    s.reset()
    s.state.apply_event({"type": "aspirate", "volume": 5000, "slot": 3, "well": "A1"})
    liquid = {"pipette_uL_after_aspirating_5000": s.state.pipette_vol, "source_well_uL_after_aspirating_from_empty": s.state.well_vol(3, "A1")}
    s.state.apply_event({"type": "dispense", "volume": 100, "slot": 5, "well": "C7"})
    liquid["state_tracks_slot5_C7_uL"] = s.state.well_vol(5, "C7")
    liquid["well_geoms_that_change_colour"] = sorted(s._g_wells)
    out["liquid_bookkeeping"] = liquid

r = subprocess.run([sys.argv[1], sys.argv[2]], capture_output=True, text=True)
lines = [l for l in r.stdout.splitlines() if l.strip()]
kinds = {}
for e in parse_simulate_output(r.stdout):
    kinds[e["type"]] = kinds.get(e["type"], 0) + 1
out["own_parser_on_opentrons_7_5"] = dict(log_lines=len(lines), aspirate_lines=sum("Aspirating" in l for l in lines),
                                          dispense_lines=sum("Dispensing" in l for l in lines), events_parsed=kinds,
                                          sample_line=next((l.strip() for l in lines if "Aspirating" in l), ""))
print(json.dumps(out, indent=1))
