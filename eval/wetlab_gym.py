"""
Text2WetLab Gymnasium environment — headless, recordable.

Observation: well volumes, tiprack state, pipette volume + tip flag
Actions:     pick_up_tip | aspirate | dispense | drop_tip
Reward:      +1 per T-criterion first pass, +5 bonus on full completion
Render:      rgb_array → numpy array (matplotlib, always headless)
Record:      env.record_episode(policy_fn) → MP4 via imageio+ffmpeg

Usage:
    pip install gymnasium numpy matplotlib imageio[ffmpeg]
    python eval/wetlab_gym.py          # runs reference policy, saves episode.mp4
"""

import numpy as np
import gymnasium as gym
from gymnasium import spaces


class WetLabEnv(gym.Env):
    metadata = {"render_modes": ["rgb_array", "human"], "render_fps": 8}

    # Deck: slot 0 = tiprack, slot 1 = 96-well plate, slot 2 = trough
    PIPETTE_MAX_VOL = 1000.0
    MAX_STEPS       = 20

    def __init__(self, render_mode=None, task="L1_serial_dilution"):
        super().__init__()
        self.render_mode = render_mode
        self.task = task

        self.observation_space = spaces.Dict({
            "plate_volumes":   spaces.Box(0, 360,  (8, 12), dtype=np.float32),
            "tiprack_tips":    spaces.Box(0, 1,    (8, 12), dtype=np.float32),
            "pipette_volume":  spaces.Box(0, 1000, (1,),    dtype=np.float32),
            "pipette_has_tip": spaces.Discrete(2),
        })

        # (type, slot, row, col, volume_ul)
        self.action_space = spaces.Dict({
            "type":   spaces.Discrete(4),              # 0=pick_tip 1=aspirate 2=dispense 3=drop_tip
            "slot":   spaces.Discrete(3),
            "row":    spaces.Discrete(8),
            "col":    spaces.Discrete(12),
            "volume": spaces.Box(0, 1000, (1,), dtype=np.float32),
        })

        self._reset_state()

    # ── State ────────────────────────────────────────────────────────────────
    def _reset_state(self):
        # well_volumes[slot, row, col] in µL
        self.well_volumes = np.zeros((3, 8, 12), dtype=np.float32)
        self.well_volumes[2, 0, 0] = 10_000.0  # trough A1 pre-filled

        self.tiprack_tips    = np.ones((8, 12), dtype=np.float32)
        self.pipette_volume  = 0.0
        self.pipette_has_tip = False
        self.steps_taken     = 0
        self.criteria        = {f"T{i}": False for i in range(1, 7)}
        self._errors         = []
        self._history        = []          # list of (action_dict, reward)

    def _obs(self):
        return {
            "plate_volumes":   self.well_volumes[1].copy(),
            "tiprack_tips":    self.tiprack_tips.copy(),
            "pipette_volume":  np.array([self.pipette_volume], dtype=np.float32),
            "pipette_has_tip": int(self.pipette_has_tip),
        }

    def _info(self):
        return {
            "criteria": self.criteria.copy(),
            "errors":   self._errors.copy(),
            "steps":    self.steps_taken,
            "n_pass":   sum(self.criteria.values()),
        }

    # ── Gym interface ─────────────────────────────────────────────────────────
    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self._reset_state()
        return self._obs(), self._info()

    def step(self, action):
        atype = int(action["type"])
        slot  = int(action.get("slot", 0))
        row   = int(action.get("row",  0))
        col   = int(action.get("col",  0))
        vol   = float(np.asarray(action.get("volume", [0])).flat[0])

        reward = 0.0
        self._errors = []
        self.steps_taken += 1

        if atype == 0:   # pick_up_tip
            if self.pipette_has_tip:
                self._errors.append("already_has_tip"); reward -= 0.5
            elif not self.tiprack_tips[row, col]:
                self._errors.append("no_tip_at_pos"); reward -= 0.5
            else:
                self.pipette_has_tip = True
                self.tiprack_tips[row, col] = 0.0
                if not self.criteria["T1"]:
                    self.criteria["T1"] = True; reward += 1.0
                else:
                    reward += 0.1

        elif atype == 1: # aspirate
            if not self.pipette_has_tip:
                self._errors.append("NoTipError"); reward -= 1.0
            elif vol > self.PIPETTE_MAX_VOL:
                self._errors.append("over_capacity"); reward -= 1.0
            elif self.well_volumes[slot, row, col] < vol:
                self._errors.append("insufficient_source"); reward -= 0.5
            else:
                self.pipette_volume += vol
                self.well_volumes[slot, row, col] -= vol
                if vol == 200.0 and not self.criteria["T2"]:
                    self.criteria["T2"] = True; reward += 1.0
                if vol <= self.PIPETTE_MAX_VOL and not self.criteria["T6"]:
                    self.criteria["T6"] = True; reward += 0.5
                else:
                    reward += 0.2

        elif atype == 2: # dispense
            if not self.pipette_has_tip:
                self._errors.append("NoTipError"); reward -= 1.0
            elif vol > self.pipette_volume:
                self._errors.append("overdispense"); reward -= 1.0
            else:
                self.pipette_volume -= vol
                self.well_volumes[slot, row, col] += vol
                if vol == 100.0 and self.criteria["T2"]:
                    # count 100µL dispenses into plate
                    n = int(self.well_volumes[1].sum() // 100)
                    if n >= 2 and not self.criteria["T3"]:
                        self.criteria["T3"] = True; reward += 1.0
                    if not self.criteria["T5"]:
                        self.criteria["T5"] = True; reward += 0.5
                    else:
                        reward += 0.3

        elif atype == 3: # drop_tip
            if not self.pipette_has_tip:
                self._errors.append("no_tip_to_drop"); reward -= 0.5
            else:
                self.pipette_has_tip = False
                self.pipette_volume  = 0.0
                if not self.criteria["T4"]:
                    self.criteria["T4"] = True; reward += 1.0
                else:
                    reward += 0.1

        n_pass = sum(self.criteria.values())
        if n_pass == 6:
            reward += 5.0

        self._history.append({"action": action, "reward": round(reward, 3), "criteria": self.criteria.copy()})

        terminated = n_pass == 6
        truncated  = self.steps_taken >= self.MAX_STEPS

        if self.render_mode == "human":
            self.render()

        return self._obs(), reward, terminated, truncated, self._info()

    # ── Render ────────────────────────────────────────────────────────────────
    def render(self):
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.gridspec as gridspec

        fig = plt.figure(figsize=(14, 5), facecolor="#07070f")
        gs  = gridspec.GridSpec(1, 4, figure=fig, wspace=0.35)

        tip_ax    = fig.add_subplot(gs[0])
        plate_ax  = fig.add_subplot(gs[1])
        trough_ax = fig.add_subplot(gs[2])
        crit_ax   = fig.add_subplot(gs[3])

        header = (
            f"WetLabEnv · step {self.steps_taken}/{self.MAX_STEPS} · "
            f"tip {'ON' if self.pipette_has_tip else 'OFF'} · "
            f"{self.pipette_volume:.0f}µL · "
            f"{sum(self.criteria.values())}/6 criteria"
        )
        fig.suptitle(header, color="#00d4ff", fontsize=10, fontfamily="monospace")

        # Tiprack
        tip_ax.imshow(self.tiprack_tips, cmap="YlOrBr", vmin=0, vmax=1, aspect="auto")
        tip_ax.set_title("Tiprack", color="#8090c0", fontsize=8, fontfamily="monospace")
        tip_ax.set_facecolor("#0a0a14")
        tip_ax.tick_params(colors="#445", labelsize=6)

        # Plate
        plate_data = self.well_volumes[1] / 360.0
        plate_ax.imshow(plate_data, cmap="Blues", vmin=0, vmax=1, aspect="auto")
        plate_ax.set_title("Plate (slot 2)", color="#8090c0", fontsize=8, fontfamily="monospace")
        plate_ax.set_facecolor("#0a0a14")
        plate_ax.tick_params(colors="#445", labelsize=6)
        # label filled wells
        for r in range(8):
            for c in range(12):
                v = self.well_volumes[1, r, c]
                if v > 0:
                    plate_ax.text(c, r, f"{v:.0f}", ha="center", va="center",
                                  fontsize=5, color="white", fontfamily="monospace")

        # Trough
        trough_data = np.clip(self.well_volumes[2] / 10000.0, 0, 1)
        trough_ax.imshow(trough_data, cmap="Greens", vmin=0, vmax=1, aspect="auto")
        trough_ax.set_title("Trough (slot 3)", color="#8090c0", fontsize=8, fontfamily="monospace")
        trough_ax.set_facecolor("#0a0a14")
        trough_ax.tick_params(colors="#445", labelsize=6)

        # Criteria
        crit_ax.set_facecolor("#07070f"); crit_ax.axis("off")
        descriptions = {
            "T1": "tip before aspirate",
            "T2": "aspirate 200µL",
            "T3": "2×100µL dispense",
            "T4": "drop tip",
            "T5": "no overdispense",
            "T6": "no over-capacity",
        }
        for j, (k, v) in enumerate(self.criteria.items()):
            crit_ax.text(0.05, 0.88 - j * 0.14,
                         f"{'✓' if v else '·'} {k} {descriptions[k]}",
                         color="#00e676" if v else "#2a2a3a",
                         fontsize=8, fontfamily="monospace",
                         transform=crit_ax.transAxes)

        fig.canvas.draw()
        w, h = fig.canvas.get_width_height()
        frame = np.frombuffer(fig.canvas.buffer_rgba(), dtype=np.uint8).reshape(h, w, 4)[..., :3]
        plt.close(fig)
        return frame

    def record_episode(self, policy_fn, output_path="episode.mp4"):
        """Run a full episode with policy_fn(obs)->action, save as MP4."""
        import imageio
        obs, info = self.reset()
        frames = [self.render()]

        for _ in range(self.MAX_STEPS):
            action = policy_fn(obs, info)
            obs, reward, terminated, truncated, info = self.step(action)
            frames.append(self.render())
            if terminated or truncated:
                break

        imageio.mimsave(output_path, frames, fps=self.metadata["render_fps"])
        print(f"Saved {len(frames)} frames → {output_path}")
        return info


# ── Reference policy (correct L1 protocol) ───────────────────────────────────
def reference_policy(obs, info):
    step = info["steps"]
    ACTIONS = [
        {"type": 0, "slot": 0, "row": 0, "col": 0, "volume": np.array([0.0])},    # pick tip A1
        {"type": 1, "slot": 2, "row": 0, "col": 0, "volume": np.array([200.0])},  # aspirate 200µL
        {"type": 2, "slot": 1, "row": 0, "col": 0, "volume": np.array([100.0])},  # dispense → A1
        {"type": 2, "slot": 1, "row": 1, "col": 0, "volume": np.array([100.0])},  # dispense → B1
        {"type": 3, "slot": 0, "row": 0, "col": 0, "volume": np.array([0.0])},    # drop tip
    ]
    return ACTIONS[step] if step < len(ACTIONS) else ACTIONS[-1]


if __name__ == "__main__":
    env  = WetLabEnv(render_mode="rgb_array")
    info = env.record_episode(reference_policy, "reference_episode.mp4")
    print(f"\nCriteria: {info['criteria']}")
    print(f"All pass: {all(info['criteria'].values())}")
    print(f"Steps:    {info['steps']}")
