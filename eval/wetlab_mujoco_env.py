"""
Text2WetLab — MuJoCo Gymnasium Environment
End-to-end 3D simulation of OT-2 liquid handling.

Physics:  MuJoCo 3.x (Cartesian XYZ gantry, position-controlled)
Liquid:   Tracked analytically on top of MuJoCo (no fluid sim)
Render:   mujoco.Renderer offscreen — returns numpy RGB array
Record:   env.record_episode(policy_fn) → MP4

Usage:
    pip install mujoco gymnasium numpy imageio[ffmpeg]
    python eval/wetlab_mujoco_env.py          # reference episode → episode_mujoco.mp4
"""

import os, pathlib
import numpy as np
import mujoco
import gymnasium as gym
from gymnasium import spaces

XML_PATH = pathlib.Path(__file__).parent / "ot2.xml"

# ── Cartesian waypoints (x, y, z in metres) ──────────────────────────────────
# OT-2 deck: slots at x=-.152/0/.152, y=-.085, labware heights ~0.01–0.03m above deck
SAFE_Z   = -0.02    # safe travel height (above all labware)
WORK_Z   = -0.17    # working depth (tip into well)

WAYPOINTS = {
    "home":       ( 0.000,  0.000, SAFE_Z),
    "tip_A1":     (-0.152, -0.047, SAFE_Z),   # tiprack slot 1, well A1
    "trough_A1":  ( 0.152, -0.085, SAFE_Z),   # trough slot 3
    "plate_A1":   ( 0.000, -0.054, SAFE_Z),   # plate slot 2, well A1
    "plate_B1":   ( 0.000, -0.063, SAFE_Z),   # plate slot 2, well B1
}

# Protocol step definitions
STEPS = [
    {"label": "READY",               "detail": "L1 · 200µL → A1 + B1",              "wp": "home",      "work": False, "action": None},
    {"label": "PICK UP TIP",         "detail": "slot 1 · A1 · T1 criterion",         "wp": "tip_A1",    "work": True,  "action": "pick_tip"},
    {"label": "ASPIRATE 200µL",      "detail": "slot 3 · trough · T2 + T6",          "wp": "trough_A1", "work": True,  "action": "aspirate"},
    {"label": "DISPENSE 100µL → A1", "detail": "slot 2 · well A1 · 100µL left",      "wp": "plate_A1",  "work": True,  "action": "disp_A1"},
    {"label": "DISPENSE 100µL → B1", "detail": "slot 2 · well B1 · T3 + T5",         "wp": "plate_B1",  "work": True,  "action": "disp_B1"},
    {"label": "DROP TIP",            "detail": "slot 1 · A1 returned · T4",           "wp": "tip_A1",    "work": True,  "action": "drop_tip"},
    {"label": "COMPLETE ✓",          "detail": "T1 T2 T3 T4 T5 T6 — all pass",       "wp": "home",      "work": False, "action": "done"},
]


class WetLabMuJoCoEnv(gym.Env):
    """OT-2 liquid handling gym — MuJoCo physics, headless rendering."""

    metadata = {"render_modes": ["rgb_array"], "render_fps": 12}

    PIPETTE_MAX = 1000.0
    MAX_STEPS   = 20
    RENDER_W, RENDER_H = 960, 540

    def __init__(self, render_mode="rgb_array", camera="iso"):
        super().__init__()
        self.render_mode = render_mode
        self.camera      = camera

        # Load model once
        self.model = mujoco.MjModel.from_xml_path(str(XML_PATH))
        self.data  = mujoco.MjData(self.model)
        self._renderer = mujoco.Renderer(self.model, self.RENDER_H, self.RENDER_W)

        # Actuator indices
        self._ax = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_ACTUATOR, "act_x")
        self._ay = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_ACTUATOR, "act_y")
        self._az = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_ACTUATOR, "act_z")

        # Geom indices for rgba toggling
        def gid(name): return mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_GEOM, name)
        self._g_tip    = gid("pip_tip")
        self._g_liquid = gid("pip_liquid")
        self._g_tipA1  = gid("tip_A1")
        self._g_wA1    = gid("w_A1")
        self._g_wB1    = gid("w_B1")

        self.observation_space = spaces.Dict({
            "pipette_pos":     spaces.Box(-1, 1, (3,), dtype=np.float32),
            "pipette_volume":  spaces.Box(0, 1000, (1,), dtype=np.float32),
            "pipette_has_tip": spaces.Discrete(2),
            "plate_A1_vol":    spaces.Box(0, 360, (1,), dtype=np.float32),
            "plate_B1_vol":    spaces.Box(0, 360, (1,), dtype=np.float32),
            "trough_vol":      spaces.Box(0, 50000, (1,), dtype=np.float32),
        })
        self.action_space = spaces.Dict({
            "type":   spaces.Discrete(4),
            "slot":   spaces.Discrete(3),
            "row":    spaces.Discrete(8),
            "col":    spaces.Discrete(12),
            "volume": spaces.Box(0, 1000, (1,), dtype=np.float32),
        })

        self._reset_liquid()

    # ── Liquid state ─────────────────────────────────────────────────────────
    def _reset_liquid(self):
        self.pip_vol     = 0.0
        self.has_tip     = False
        self.trough_vol  = 10_000.0
        self.plate_A1    = 0.0
        self.plate_B1    = 0.0
        self.criteria    = {f"T{i}": False for i in range(1, 7)}
        self.steps_taken = 0

    def _sync_visuals(self):
        """Push liquid state into MuJoCo geom rgba."""
        # Tip on pipette
        a = 1.0 if self.has_tip else 0.0
        self.model.geom_rgba[self._g_tip][:] = [.95, .80, .10, a]
        # Tip A1 in rack (disappears when picked up)
        ta = 0.0 if self.has_tip else 1.0
        self.model.geom_rgba[self._g_tipA1][:] = [.95, .58, .05, ta]
        # Liquid column in tip
        la = min(self.pip_vol / 200.0, 1.0) if self.pip_vol > 0 else 0.0
        self.model.geom_rgba[self._g_liquid][:] = [.00, .62, .92, la]
        # Well fill
        fA = min(self.plate_A1 / 100.0, 1.0)
        fB = min(self.plate_B1 / 100.0, 1.0)
        self.model.geom_rgba[self._g_wA1][:] = [.02, .40 + .30*fA, .90, max(.3*fA, .0)] if fA>0 else [.06,.04,.13,1]
        self.model.geom_rgba[self._g_wB1][:] = [.02, .40 + .30*fB, .90, max(.3*fB, .0)] if fB>0 else [.06,.04,.13,1]

    # ── Cartesian motion ──────────────────────────────────────────────────────
    def _move_to(self, x, y, z, steps=120):
        """Drive actuators to XYZ target, integrate physics."""
        self.data.ctrl[self._ax] = x
        self.data.ctrl[self._ay] = y
        self.data.ctrl[self._az] = z
        for _ in range(steps):
            mujoco.mj_step(self.model, self.data)

    def _execute_step(self, step_def):
        """Execute one protocol step: rise → move → [descend → action → ascend]."""
        wp_name = step_def["wp"]
        tx, ty, tz = WAYPOINTS[wp_name]

        # Rise to safe Z first
        cx = self.data.ctrl[self._ax]
        cy = self.data.ctrl[self._ay]
        self._move_to(cx, cy, SAFE_Z, steps=80)

        # Move laterally
        self._move_to(tx, ty, SAFE_Z, steps=150)

        if step_def["work"]:
            # Descend
            self._move_to(tx, ty, WORK_Z, steps=80)
            # Perform liquid action
            self._do_action(step_def["action"])
            # Ascend
            self._move_to(tx, ty, SAFE_Z, steps=80)
        elif step_def["action"]:
            self._do_action(step_def["action"])

    def _do_action(self, action):
        if action == "pick_tip":
            self.has_tip = True; self.pip_vol = 0.0
            self.criteria["T1"] = True
        elif action == "aspirate":
            vol = 200.0
            self.pip_vol += vol; self.trough_vol -= vol
            self.criteria["T2"] = True; self.criteria["T6"] = True
        elif action == "disp_A1":
            self.plate_A1 += 100.0; self.pip_vol -= 100.0
        elif action == "disp_B1":
            self.plate_B1 += 100.0; self.pip_vol -= 100.0
            self.criteria["T3"] = True; self.criteria["T5"] = True
        elif action == "drop_tip":
            self.has_tip = False; self.pip_vol = 0.0
            self.criteria["T4"] = True
        self._sync_visuals()

    # ── Gym interface ─────────────────────────────────────────────────────────
    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        mujoco.mj_resetData(self.model, self.data)
        self._reset_liquid()
        self._sync_visuals()
        # Park at home
        self._move_to(*WAYPOINTS["home"], steps=200)
        return self._obs(), self._info()

    def _obs(self):
        pos = np.array([self.data.ctrl[self._ax],
                        self.data.ctrl[self._ay],
                        self.data.ctrl[self._az]], dtype=np.float32)
        return {
            "pipette_pos":     pos,
            "pipette_volume":  np.array([self.pip_vol], dtype=np.float32),
            "pipette_has_tip": int(self.has_tip),
            "plate_A1_vol":    np.array([self.plate_A1], dtype=np.float32),
            "plate_B1_vol":    np.array([self.plate_B1], dtype=np.float32),
            "trough_vol":      np.array([self.trough_vol], dtype=np.float32),
        }

    def _info(self):
        return {"criteria": self.criteria.copy(), "steps": self.steps_taken,
                "n_pass": sum(self.criteria.values())}

    def step(self, action):
        atype  = int(action["type"])
        slot   = int(action.get("slot", 0))
        row    = int(action.get("row", 0))
        col    = int(action.get("col", 0))
        vol    = float(np.asarray(action.get("volume", [0])).flat[0])
        reward = 0.0
        self.steps_taken += 1

        if atype == 0:   # pick_up_tip
            if not self.has_tip:
                self.has_tip = True; self.criteria["T1"] = True
                self._sync_visuals(); reward += 1.0
        elif atype == 1: # aspirate
            if self.has_tip and vol <= self.PIPETTE_MAX and self.trough_vol >= vol:
                self.pip_vol += vol; self.trough_vol -= vol
                self.criteria["T2"] = (vol == 200.0); self.criteria["T6"] = True
                self._sync_visuals(); reward += 1.0
            else:
                reward -= 1.0
        elif atype == 2: # dispense
            if self.has_tip and vol <= self.pip_vol:
                if row == 0: self.plate_A1 += vol
                elif row == 1: self.plate_B1 += vol
                self.pip_vol -= vol
                if self.plate_A1 >= 100 and self.plate_B1 >= 100:
                    self.criteria["T3"] = True; self.criteria["T5"] = True
                self._sync_visuals(); reward += 0.5
            else:
                reward -= 1.0
        elif atype == 3: # drop_tip
            if self.has_tip:
                self.has_tip = False; self.pip_vol = 0.0
                self.criteria["T4"] = True
                self._sync_visuals(); reward += 1.0

        n_pass = sum(self.criteria.values())
        if n_pass == 6: reward += 5.0
        terminated = n_pass == 6
        truncated  = self.steps_taken >= self.MAX_STEPS
        return self._obs(), reward, terminated, truncated, self._info()

    # ── Render ────────────────────────────────────────────────────────────────
    def render(self):
        # Use free camera with explicit lookat so we always see the deck
        cam = mujoco.MjvCamera()
        cam.type = mujoco.mjtCamera.mjCAMERA_FREE
        cam.lookat[:] = [0.0, -0.05, 0.06]   # deck centre + a bit up
        cam.distance   = 0.85
        cam.azimuth    = 140.0   # degrees: front-right view
        cam.elevation  = -28.0  # degrees: looking slightly down
        self._renderer.update_scene(self.data, camera=cam)
        pixels = self._renderer.render()
        return self._overlay_hud(pixels)

    def _overlay_hud(self, pixels):
        """Blit a minimal text HUD onto the render."""
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            import matplotlib.patches as mp

            fig, ax = plt.subplots(figsize=(self.RENDER_W/100, self.RENDER_H/100),
                                   dpi=100, facecolor='none')
            ax.axis('off')
            ax.imshow(pixels)

            # Criteria strip (bottom-left)
            labels = ["T1·tip", "T2·asp", "T3·2x", "T4·drop", "T5·nodump", "T6·nocap"]
            for i, (k, lab) in enumerate(zip([f"T{j}" for j in range(1,7)], labels)):
                col = "#00e676" if self.criteria[k] else "#1a1a2a"
                ax.text(12 + i*140, self.RENDER_H-22, lab,
                        color=col, fontsize=8, fontfamily="monospace",
                        transform=ax.transData)

            # Volume + step (top-left)
            ax.text(12, 22, f"step {self.steps_taken}  tip={'ON' if self.has_tip else 'OFF'}  {self.pip_vol:.0f}µL",
                    color="#00d4ff", fontsize=9, fontfamily="monospace",
                    transform=ax.transData)

            fig.tight_layout(pad=0)
            fig.canvas.draw()
            w, h = fig.canvas.get_width_height()
            frame = np.frombuffer(fig.canvas.buffer_rgba(), dtype=np.uint8).reshape(h, w, 4)[..., :3]
            plt.close(fig)
            return frame
        except Exception:
            return pixels

    def close(self):
        self._renderer.close()

    # ── Episode recorder ──────────────────────────────────────────────────────
    def record_protocol(self, output_path="episode_mujoco.mp4", camera="iso"):
        """Execute the full reference L1 protocol step-by-step, recording frames."""
        import imageio
        self.camera = camera
        mujoco.mj_resetData(self.model, self.data)
        self._reset_liquid(); self._sync_visuals()
        self._move_to(*WAYPOINTS["home"], steps=200)

        frames = []
        frames.append(self.render())

        for step in STEPS:
            print(f"  {step['label']:<28} {step['detail']}")
            self._execute_step(step)
            # Capture several frames per step for smooth video
            for _ in range(6):
                mujoco.mj_step(self.model, self.data)
                frames.append(self.render())

        imageio.mimsave(output_path, frames, fps=self.metadata["render_fps"])
        n_pass = sum(self.criteria.values())
        print(f"\nSaved {len(frames)} frames → {output_path}")
        print(f"Criteria: {self.criteria}")
        print(f"Pass: {n_pass}/6")
        return self.criteria


# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    env = WetLabMuJoCoEnv(render_mode="rgb_array", camera="iso")
    print("Recording reference L1 protocol...")
    criteria = env.record_protocol("episode_mujoco.mp4", camera="iso")
    env.close()
    print("Done. Open: episode_mujoco.mp4")
