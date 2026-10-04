"""
Headless 3D (MuJoCo) view of any Protocol IR, side by side with the 2D IR view.

    python eval/ir_mujoco.py tasks/L1/example/ir.json -o assets/examples3d/L1-example.mp4
    python eval/ir_mujoco.py --all          # every IR in the repo -> assets/examples3d/

The scene is generated from the IR: one labware model per container on a virtual deck (one
slot per container, so decks with 40+ containers are larger than a real OT-2). A gantry head
travels at a safe height, goes down to the source, aspirates, travels, dispenses, and lifts.
Liquid levels in every well / tube / reservoir follow the same bookkeeping as the 2D view
(ir_viz.timeline, which follows paper2protocol/check.py).

Colour = fill state: blue (low) -> teal -> amber (80%+) -> orange (full), red = above capacity,
magenta = overdrawn (more withdrawn than the source held), green = stock with ample volume.

Physics tracking (strip under the two views, one value per frame): liquid held in the tip vs the
pipette maximum, tip height vs the labware beneath it, fullest container as % of capacity, and
a running count of issues. A lateral move with the tip below labware rim height counts as a
collision and turns the tip red; --no-lift makes the head travel low to show this. A transfer
bigger than one pipette load is flagged with the number of aspirations it needs.

Animation is per IR step, not per pipette stroke: a transfer to many wells is drawn as one
trip to the first well, with all destination wells filling during the dispense.

Outputs: MP4 (full), GIF (half size, subsampled, inline-friendly), PNG contact sheet of
evenly spaced frames. Needs: mujoco, matplotlib, imageio[ffmpeg], pillow, pydantic.
"""

import argparse
import math
import pathlib
import sys

import imageio
import matplotlib
import mujoco
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from PIL import Image, ImageDraw

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "eval"))
sys.path.insert(0, str(ROOT))
from ir_viz import LEGEND, draw, fill_rgb, find_irs, name_for, pairs, ratio, timeline  # noqa: E402
from paper2protocol.check import check, expand_wells  # noqa: E402
from paper2protocol.models import CAPACITY_UL, Protocol  # noqa: E402
from paper2protocol.render import step_line  # noqa: E402

# Optional: use real OT-2 slot positions from the opentrons-mujoco-viz fork
try:
    from opentrons.visualization import SLOT_XY as _OT2_SLOT_XY  # noqa: E402
    _HAS_OT2 = True
except ImportError:
    _HAS_OT2 = False
    _OT2_SLOT_XY: dict = {}

PITCH_X, PITCH_Y = 0.16, 0.12
WELL_PITCH, WELL_R = 0.009, 0.0033
LIQ = "0.18 0.62 1 0.95"
STOCK = "0 0.9 0.5 0.95"
# kind -> (radius or half-x, half-y, height)
TUBES = {"tube_1.5ml": (0.010, 0.040), "tube_15ml": (0.0075 * 2, 0.100), "tube_50ml": (0.014, 0.115)}
SAFE_MARGIN = 0.035
PANEL = (720, 540)


class Deck:
    """MJCF generated from a Protocol, plus helpers to set liquid levels and move the head."""

    def __init__(self, p: Protocol):
        self.p = p
        self.kinds = {c.name: c.kind for c in p.containers}
        n = len(p.containers)
        self.origin = {}  # container -> world (x, y) of its centre
        self.top = {}     # container -> world z of its rim
        self.foot = {}    # container -> (half-x, half-y) footprint
        parts = []
        # Use real OT-2 slot positions when ≤12 containers and fork is available
        self._ot2_mode = _HAS_OT2 and n <= 12
        if self._ot2_mode:
            slot_list = list(_OT2_SLOT_XY.values())  # slots 1–12 in order
            xs = [x for x, y in slot_list]
            ys = [y for x, y in slot_list]
            self.W = (max(xs) - min(xs)) + PITCH_X
            self.H = (max(ys) - min(ys)) + PITCH_Y
            for i, c in enumerate(p.containers):
                sx, sy = slot_list[i] if i < len(slot_list) else (0.0, 0.0)
                self.origin[c.name] = (sx, sy)
                parts.append(self._labware(i, c, sx, sy))
        else:
            self.cols = max(2, math.ceil(math.sqrt(n * 1.3)))
            self.rows = math.ceil(n / self.cols)
            self.W, self.H = self.cols * PITCH_X, self.rows * PITCH_Y
            for i, c in enumerate(p.containers):
                x = -self.W / 2 + PITCH_X * (i % self.cols + 0.5)
                y = self.H / 2 - PITCH_Y * (i // self.cols + 0.5)
                self.origin[c.name] = (x, y)
                parts.append(self._labware(i, c, x, y))
        self.safe_z = max(self.top.values()) + SAFE_MARGIN
        xml = f"""<mujoco model="ir_deck">
  <option gravity="0 0 0"/>
  <visual><global offwidth="{PANEL[0]}" offheight="{PANEL[1]}"/>
    <headlight ambient=".5 .5 .6" diffuse=".8 .8 .85" specular=".2 .2 .2"/><rgba haze=".03 .03 .07 1"/></visual>
  <worldbody>
    <light pos="0 {-self.H} 2.5" dir="0 .3 -1" diffuse=".6 .6 .6"/>
    <geom name="floor" type="plane" size="4 4 .1" rgba=".03 .03 .08 1" contype="0" conaffinity="0"/>
    <geom type="box" pos="0 0 -.006" size="{self.W / 2 + .03} {self.H / 2 + .03} .006" rgba=".16 .20 .32 1" contype="0" conaffinity="0"/>
    {''.join(parts)}
    <body name="bridge" mocap="true" pos="0 0 {self.safe_z + .30}">
      <geom type="box" size="{self.W / 2 + .06} .006 .006" rgba=".6 .68 .8 1" contype="0" conaffinity="0"/></body>
    <body name="head" mocap="true" pos="0 0 {self.safe_z}">
      <geom name="tip_body" type="cylinder" pos="0 0 .025" size=".0022 .025" rgba=".98 .75 .1 1" contype="0" conaffinity="0"/>
      <geom name="tip_liq" type="cylinder" pos="0 0 .02" size=".0014 .02" rgba="{LIQ}" contype="0" conaffinity="0"/>
      <geom type="cylinder" pos="0 0 .075" size=".008 .025" rgba=".3 .72 .85 1" contype="0" conaffinity="0"/>
      <geom type="box" pos="0 0 .22" size=".004 .004 .12" rgba=".6 .68 .8 1" contype="0" conaffinity="0"/>
    </body>
  </worldbody>
</mujoco>"""
        self.model = mujoco.MjModel.from_xml_string(xml)
        self.data = mujoco.MjData(self.model)
        self.renderer = mujoco.Renderer(self.model, PANEL[1], PANEL[0])
        self.cam = mujoco.MjvCamera()
        self.cam.lookat[:] = [0, -self.H * 0.05, 0.04]
        self.cam.azimuth, self.cam.elevation = 90, -52
        self.cam.distance = max(self.W, self.H * 1.6) * 0.95 + 0.12
        # Close camera: 65% of wide distance, shallower angle — liquid fill colours legible
        self.cam_close = mujoco.MjvCamera()
        self.cam_close.lookat[:] = [0, -self.H * 0.05, 0.04]
        self.cam_close.azimuth, self.cam_close.elevation = 180, -30
        self.cam_close.distance = self.cam.distance * 0.65
        gid = lambda n: mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_GEOM, n)
        self.tip_liq = gid("tip_liq")
        self.tip_body = gid("tip_body")
        self.liq = {}   # (container, well) -> (geom id, kind, base_z, max_h)
        for key, (name, kind, base_z, max_h) in self._liq_specs.items():
            self.liq[key] = (gid(name), kind, base_z, max_h)
        self.head_id = self.model.body_mocapid[mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_BODY, "head")]
        self.bridge_id = self.model.body_mocapid[mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_BODY, "bridge")]

    _liq_specs: dict

    def _labware(self, i, c, x, y):
        self._liq_specs = getattr(self, "_liq_specs", {})
        k, nm = c.kind, c.name
        no = 'contype="0" conaffinity="0"'
        if k.startswith("plate_96"):
            h = 0.030 if k == "plate_96_deep" else 0.014
            self.top[nm] = h
            self.foot[nm] = (0.064, 0.043)
            s = f'<geom type="box" pos="{x} {y} {h / 2}" size=".064 .043 {h / 2}" rgba=".35 .2 .6 1" {no}/>'
            for r in range(8):
                for col in range(12):
                    wx = x - 0.0495 + col * WELL_PITCH
                    wy = y + 0.0315 - r * WELL_PITCH
                    s += (f'<geom name="c{i}_w{r}_{col}" type="cylinder" pos="{wx} {wy} {h}" '
                          f'size="{WELL_R} 0.008" rgba="{LIQ}" {no}/>')
                    well = f"{'ABCDEFGH'[r]}{col + 1}"
                    self._liq_specs[(nm, well)] = (f"c{i}_w{r}_{col}", "cyl", h, 0.016)
            return s
        if k in TUBES:
            rad, ht = TUBES[k]
            self.top[nm] = ht
            self.foot[nm] = (rad, rad)
            self._liq_specs[(nm, "")] = (f"c{i}_liq", "cyl", 0.0, ht * 0.95)
            return (f'<geom type="cylinder" pos="{x} {y} {ht / 2}" size="{rad} {ht / 2}" rgba=".8 .85 .95 .12" {no}/>'
                    f'<geom name="c{i}_liq" type="cylinder" pos="{x} {y} {ht / 2}" size="{rad * .85} {ht * .475}" rgba="{LIQ}" {no}/>')
        ht = 0.03  # reservoir / waste
        self.top[nm] = ht
        self.foot[nm] = (0.06, 0.04)
        self._liq_specs[(nm, "")] = (f"c{i}_liq", "box", 0.0, ht * 0.9)
        col = ".35 .1 .1 .35" if k == "waste" else ".8 .9 .85 .25"
        return (f'<geom type="box" pos="{x} {y} {ht / 2}" size=".06 .04 {ht / 2}" rgba="{col}" {no}/>'
                f'<geom name="c{i}_liq" type="box" pos="{x} {y} {ht / 2}" size=".055 .035 {ht * .45}" rgba="{LIQ}" {no}/>')

    # -- liquid -------------------------------------------------------------------------
    def set_level(self, key, r):
        """r = volume / capacity (None = stock). Height uses sqrt so small volumes stay visible."""
        gid, kind, base, max_h = self.liq[key]
        m = self.model
        if r is not None and abs(r) <= 1e-9:
            m.geom_rgba[gid, 3] = 0.0
            return
        frac = 1.0 if r is None else (0.35 if r < 0 else min(r, 1.0))
        h = min(max(0.0006, 0.5 * math.sqrt(frac) * max_h), max_h / 2)
        m.geom_rgba[gid] = [*fill_rgb(0 if r is None else r, r is None), 0.95]
        m.geom_size[gid, 1 if kind == "cyl" else 2] = h
        m.geom_pos[gid, 2] = base + h

    def apply_state(self, before, after, p_src, p_dst, src_keys, dst_keys):
        """Set every liquid geom for the interpolated state. Returns the fullest container ratio."""
        src_keys, dst_keys = set(src_keys), set(dst_keys)
        worst = 0.0
        for key in self.liq:
            kind = self.kinds[key[0]]
            cap = CAPACITY_UL.get(kind) or 1.0
            b, a = before.get(key, 0.0), after.get(key, 0.0)
            t = p_src if key in src_keys else p_dst if key in dst_keys else 1.0
            if b is None or a is None:
                self.set_level(key, None)
                continue
            r = (b + (a - b) * t) / cap
            self.set_level(key, r)
            if kind != "waste":
                worst = max(worst, r)
        return worst

    def set_held(self, f):
        m = self.model
        if f <= 1e-3:
            m.geom_rgba[self.tip_liq, 3] = 0.0
        else:
            m.geom_rgba[self.tip_liq, 3] = 0.95
            m.geom_size[self.tip_liq, 1] = max(0.001, 0.02 * min(f, 1.0))
            m.geom_pos[self.tip_liq, 2] = m.geom_size[self.tip_liq, 1]

    # -- head ---------------------------------------------------------------------------
    def well_xy(self, container, wells):
        x, y = self.origin[container]
        w = expand_wells(wells, self.kinds[container])[0]
        if w:
            r, col = "ABCDEFGH".index(w[0]), int(w[1:]) - 1
            return x - 0.0495 + col * WELL_PITCH, y + 0.0315 - r * WELL_PITCH
        return x, y

    def work_z(self, container):
        return self.top[container] - (0.012 if self.kinds[container].startswith("plate") else 0.02)

    def place(self, pos):
        self.data.mocap_pos[self.head_id] = pos
        self.data.mocap_pos[self.bridge_id] = [0, pos[1], self.safe_z + 0.30]

    def under(self, x, y):
        """Rim height of the labware under (x, y); 0 if none."""
        for nm, (cx, cy) in self.origin.items():
            hx, hy = self.foot[nm]
            if abs(x - cx) <= hx and abs(y - cy) <= hy:
                return self.top[nm]
        return 0.0

    def collides(self, a, b):
        """A lateral move whose tip passes below the rim of labware it crosses is a collision."""
        if math.hypot(b[0] - a[0], b[1] - a[1]) < 1e-4:
            return False
        for k in range(1, 13):
            x, y, z = (a[j] + (b[j] - a[j]) * k / 12 for j in range(3))
            if z < self.under(x, y) + 0.002:
                return True
        return False

    def set_tip_color(self, bad):
        self.model.geom_rgba[self.tip_body] = [1, 0.1, 0.1, 1] if bad else [0.98, 0.75, 0.1, 1]

    def frame(self, close: bool = False):
        mujoco.mj_forward(self.model, self.data)
        self.renderer.update_scene(self.data, self.cam_close if close else self.cam)
        return self.renderer.render()

    def focus_close_cam(self, xy: tuple[float, float]) -> None:
        """Shift the close camera lookat to the given (x, y) position."""
        self.cam_close.lookat[0] = xy[0]
        self.cam_close.lookat[1] = xy[1]


def segment(a, b, n):
    return [tuple(np.array(a) + (np.array(b) - np.array(a)) * (k + 1) / n) for k in range(n)]


def build_frames(p: Protocol, pipette_max=1000.0, lift=True, close_cam=False):
    """Run the animation. Returns (deck, states, touched, issues, frames, frames_close, track).
    frames[k] = (3D image, step index, 2D phase); frames_close is [] when close_cam=False."""
    deck = Deck(p)
    states, touched = timeline(p)
    issues = {}
    for iss in check(p):
        issues.setdefault(iss.step, []).append(iss.message)
    kinds = deck.kinds
    safe = deck.safe_z
    pos = (0.0, 0.0, safe)
    out = []
    out_close = []
    track = {k: [] for k in ("held", "z", "rim", "collision", "maxfill", "issues", "trips")}
    step_issues = {}  # issues known before the animation: checker + pipette capacity
    for i, s in enumerate(p.steps, 1):
        n = len(issues.get(i, []))
        if s.kind == "transfer" and s.volume_ul and s.volume_ul > pipette_max:
            n += 1
        step_issues[i] = n
    state_ = {"cum": len(issues.get(0, []))}  # running issue count, starting with global checker issues

    def emit(step_i, before, after, p_src, p_dst, held, src_k, dst_k, head, moved=0.0, trips=0):
        nonlocal pos
        worst = deck.apply_state(before, after, p_src, p_dst, src_k, dst_k)
        deck.set_held(held)
        hit = deck.collides(pos, head)
        deck.set_tip_color(hit)
        deck.place(head)
        if hit:
            state_["cum"] += 1
        out.append((deck.frame(close=False), step_i, 1 if (p_src >= 1 or p_dst > 0) else 0))
        if close_cam:
            deck.focus_close_cam((head[0], head[1]))
            out_close.append((deck.frame(close=True), step_i, 1 if (p_src >= 1 or p_dst > 0) else 0))
        track["held"].append(held * min(moved, pipette_max))  # a tip never holds more than one load
        track["z"].append(head[2])
        track["rim"].append(deck.under(head[0], head[1]))
        track["collision"].append(hit)
        track["maxfill"].append(worst)
        track["issues"].append(state_["cum"])
        track["trips"].append(trips)
        pos = head

    emit(0, states[0], states[0], 1, 1, 0, [], [], pos)
    for i, s in enumerate(p.steps, 1):
        before, after = states[i - 1], states[i]
        src_k, dst_k = touched[i]
        state_["cum"] += step_issues[i]
        if s.kind == "manual" or s.dest not in kinds or not (src_k or dst_k):
            for _ in range(3):
                emit(i, before, after, 1, 1, 0, [], [], pos)
            continue
        if s.kind == "mix":
            dx, dy = deck.well_xy(s.dest, s.dest_wells)
            dz = deck.work_z(s.dest)
            path = segment(pos, (pos[0], pos[1], safe), 2) + segment((pos[0], pos[1], safe), (dx, dy, safe), 3) \
                + segment((dx, dy, safe), (dx, dy, dz), 2)
            for q in path:
                emit(i, before, before, 1, 1, 0, [], [], q)
            for k in range(4):
                emit(i, before, before, 1, 1, 0, [], [], (dx, dy, dz + 0.006 * (k % 2)))
            for q in segment((dx, dy, dz), (dx, dy, safe), 2):
                emit(i, before, before, 1, 1, 0, [], [], q)
            continue
        sx, sy = deck.well_xy(s.source, s.source_wells)
        dx, dy = deck.well_xy(s.dest, s.dest_wells)
        sz, dz = deck.work_z(s.source), deck.work_z(s.dest)
        moved = s.volume_ul * len(src_k)
        trips = math.ceil(moved / pipette_max) if moved else 0
        tr = dict(moved=moved, trips=trips)
        if lift:
            leg1 = segment(pos, (pos[0], pos[1], safe), 2) + segment((pos[0], pos[1], safe), (sx, sy, safe), 4) \
                + segment((sx, sy, safe), (sx, sy, sz), 2)
            leg2 = segment((sx, sy, sz), (sx, sy, safe), 2) + segment((sx, sy, safe), (dx, dy, safe), 5) \
                + segment((dx, dy, safe), (dx, dy, dz), 2)
        else:  # no lift: drive straight between work heights (shows the collision check)
            leg1 = segment(pos, (sx, sy, sz), 8)
            leg2 = segment((sx, sy, sz), (dx, dy, dz), 8)
        for q in leg1:
            emit(i, before, before, 0, 0, 0, src_k, dst_k, q, **tr)
        for k in range(1, 4):  # aspirate
            emit(i, before, after, k / 3, 0, k / 3, src_k, dst_k, (sx, sy, sz), **tr)
        for q in leg2:
            emit(i, before, after, 1, 0, 1, src_k, dst_k, q, **tr)
        for k in range(1, 4):  # dispense
            emit(i, before, after, 1, k / 3, 1 - k / 3, src_k, dst_k, (dx, dy, dz), **tr)
        if lift:
            for q in segment((dx, dy, dz), (dx, dy, safe), 2):
                emit(i, before, after, 1, 1, 0, src_k, dst_k, q, **tr)
    return deck, states, touched, issues, out, out_close, {k: np.array(v) for k, v in track.items()}


def label(img, text):
    im = Image.fromarray(img)
    d = ImageDraw.Draw(im)
    y0 = im.height - 18
    d.rectangle([0, y0, 8 + 7 * len(text), im.height], fill=(7, 7, 15))
    d.text((4, y0 + 3), text, fill=(0, 212, 255))
    return np.asarray(im)


STRIP_H, HUD_H = 190, 22


def tracker_base(track, pipette_max, width):
    """Static chart image of the whole run plus the pixel x-range of each axes (for the moving cursor)."""
    n = len(track["held"])
    x = np.arange(n)
    fig = plt.figure(figsize=(width / 100, STRIP_H / 100), dpi=100, facecolor="#07070f")
    axes = fig.subplots(1, 4, gridspec_kw=dict(left=0.03, right=0.995, bottom=0.2, top=0.82, wspace=0.16))
    style = dict(facecolor="#0c0c1a")

    def setup(ax, title):
        ax.set_facecolor("#0c0c1a")
        ax.set_title(title, color="#8090c0", fontsize=7, fontfamily="monospace", loc="left", pad=3)
        ax.tick_params(colors="#556", labelsize=6, length=2)
        for sp in ax.spines.values():
            sp.set_color("#1c1c30")
        ax.set_xlim(0, n - 1)

    a1, a2, a3, a4 = axes
    setup(a1, "liquid in tip (uL) vs pipette max")
    a1.plot(x, track["held"], color="#2b9bff", lw=1)
    a1.axhline(pipette_max, color="#ff2626", lw=0.8, ls="--")
    a1.set_ylim(0, max(pipette_max * 1.1, track["held"].max() * 1.05, 1))
    setup(a2, "tip height (cm) vs labware rim (red = collision)")
    a2.fill_between(x, 0, track["rim"] * 100, color="#334", step="mid")
    a2.plot(x, track["z"] * 100, color="#e8eefc", lw=1)
    a2.fill_between(x, a2.get_ylim()[0], np.where(track["collision"], track["z"].max() * 100 * 1.05, np.nan),
                    color="#ff2626", alpha=0.5, step="mid")
    setup(a3, "fullest container (% capacity)")
    mf = track["maxfill"] * 100
    a3.plot(x, mf, color="#ffd23f", lw=1)
    a3.axhline(100, color="#ff2626", lw=0.8, ls="--")
    a3.set_ylim(0, max(110, mf.max() * 1.05))
    setup(a4, "issues so far (checker + capacity + collisions)")
    a4.step(x, track["issues"], color="#ff5252", lw=1.2, where="post")
    a4.set_ylim(0, max(2, track["issues"].max() + 1))
    for ax in axes:
        ax.set_xticks([])
    fig.canvas.draw()
    base = np.asarray(fig.canvas.buffer_rgba())[..., :3].copy()
    boxes = []
    for ax in axes:
        bb = ax.get_window_extent()
        boxes.append((int(bb.x0), int(bb.x1), STRIP_H - int(bb.y1), STRIP_H - int(bb.y0)))
    plt.close(fig)
    return base, boxes


def legend_band(width):
    im = Image.new("RGB", (width, HUD_H), (7, 7, 15))
    d = ImageDraw.Draw(im)
    x = width - 8
    for text, col in reversed(LEGEND):
        w = 8 * len(text) + 22
        x -= w
        d.rectangle([x, 6, x + 12, 16], fill=col)
        d.text((x + 16, 5), text, fill=(150, 165, 200))
    return im


def strip_frame(base, boxes, track, k, i, n, pipette_max, width, legend):
    img = base.copy()
    n_fr = len(track["held"])
    for (x0, x1, y0, y1) in boxes:
        cx = x0 + int((x1 - x0) * k / max(n_fr - 1, 1))
        img[y0:y1, max(cx - 1, 0):cx + 1] = (0, 212, 255)
    hud = legend.copy()
    d = ImageDraw.Draw(hud)
    trips = int(track["trips"][k])
    txt = (f"step {i}/{n}   tip {track['held'][k]:.0f}/{pipette_max:.0f} uL   z {track['z'][k] * 100:.1f} cm   "
           f"fullest {track['maxfill'][k] * 100:.0f}%   issues {int(track['issues'][k])}")
    d.text((4, 5), txt, fill=(0, 212, 255))
    x_after = 4 + 7 * len(txt) + 14
    if track["collision"][k]:
        d.text((x_after, 5), "COLLISION", fill=(255, 60, 60))
        x_after += 80
    if trips > 1:
        d.text((x_after, 5), f"needs {trips} aspirations", fill=(255, 210, 63))
    return np.concatenate([np.asarray(hud), img], axis=0)


def vlm_judge(mp4_path: pathlib.Path, out_path: pathlib.Path) -> None:
    """Extract 5 evenly-spaced frames from mp4, send each to claude-haiku for QC grading."""
    import os, base64, json as _json, tempfile
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        print(f"  [vlm-judge] ANTHROPIC_API_KEY not set — skipping {mp4_path.name}", file=sys.stderr)
        return
    try:
        import anthropic
    except ImportError:
        print("  [vlm-judge] anthropic package not installed — skipping", file=sys.stderr)
        return
    reader = imageio.get_reader(str(mp4_path))
    total = reader.count_frames()
    pcts = [0, 25, 50, 75, 100]
    idxs = [min(int(p / 100 * (total - 1)), total - 1) for p in pcts]
    client = anthropic.Anthropic(api_key=key)
    results = []
    prompt = (
        "Lab automation QC review. In this MuJoCo OT-2 simulation frame: "
        "(1) Is the pipette arm visible and in a plausible position? "
        "(2) Are labware items visible on the deck? "
        "(3) Is liquid fill state colour-coded (blue→teal→amber→orange)? "
        "(4) Any visual artifacts, clipping, or missing elements? "
        "Score: PASS / WARN / FAIL + one-line reason."
    )
    with tempfile.TemporaryDirectory() as td:
        for pct, idx in zip(pcts, idxs):
            frame = reader.get_data(idx)
            img_path = pathlib.Path(td) / f"frame_{pct}.png"
            Image.fromarray(frame).save(img_path)
            img_b64 = base64.standard_b64encode(img_path.read_bytes()).decode()
            try:
                resp = client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=200,
                    messages=[{"role": "user", "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": img_b64}},
                        {"type": "text", "text": prompt},
                    ]}],
                )
                text = resp.content[0].text
                verdict = "PASS" if "PASS" in text else "FAIL" if "FAIL" in text else "WARN"
                results.append({"frame_pct": pct, "verdict": verdict, "reason": text.strip()})
            except Exception as e:
                results.append({"frame_pct": pct, "verdict": "ERROR", "reason": str(e)})
    reader.close()
    out_path.write_text(_json.dumps(results, indent=2))
    verdicts = [r["verdict"] for r in results]
    print(f"  [vlm-judge] {out_path.name}: {verdicts}")


def render(p: Protocol, out_dir: pathlib.Path, name: str, fps=12, pipette_max=1000.0, lift=True,
           close_cam=False, run_vlm_judge=False):
    deck, states, touched, issues, frames3d, frames3d_close, track = build_frames(
        p, pipette_max, lift, close_cam=close_cam)
    kinds = deck.kinds
    n = len(p.steps)
    panels = {}
    for i in range(n + 1):  # 2D panel before/after each step
        cap = f"{p.title[:100]} · start" if i == 0 else f"step {i}/{n} · {step_line(p.steps[i - 1])}"
        bad = "; ".join(issues.get(i, []))
        for phase, st in ((0, states[max(i - 1, 0)]), (1, states[i])):
            tt = touched[i] if i else ([], [])
            panels[(i, phase)] = label(draw(p, kinds, st, tt, cap, bad, PANEL), "2D  IR view")
    width = PANEL[0] * 2
    base, boxes = tracker_base(track, pipette_max, width)
    legend = legend_band(width)
    full = []
    for k, (img, i, phase) in enumerate(frames3d):
        top = np.concatenate([panels[(i, phase)], label(img, "3D  MuJoCo")], axis=1)
        full.append(np.concatenate([top, strip_frame(base, boxes, track, k, i, n, pipette_max, width, legend)], axis=0))
    full += [full[-1]] * fps
    out_dir.mkdir(parents=True, exist_ok=True)
    mp4 = out_dir / f"{name}.mp4"
    imageio.mimsave(mp4, full, fps=fps, macro_block_size=1)
    stride = max(2, math.ceil(len(full) / 150))  # keep the inline GIF to ~150 frames
    small = [np.asarray(Image.fromarray(f).resize((f.shape[1] // 2, f.shape[0] // 2), Image.LANCZOS))
             for f in full[::stride]]
    gif = out_dir / f"{name}.gif"
    imageio.mimsave(gif, small, duration=1000 * stride / fps, loop=0)
    png = out_dir / f"{name}_frames.png"
    Image.fromarray(contact_sheet(full)).save(png)

    # Optional: close-camera mp4 (liquid fill detail)
    if close_cam and frames3d_close:
        full_close = []
        for k, (img, i, phase) in enumerate(frames3d_close):
            top = np.concatenate([panels[(i, phase)], label(img, "3D  close  MuJoCo")], axis=1)
            full_close.append(np.concatenate([top, strip_frame(base, boxes, track, k, i, n, pipette_max, width, legend)], axis=0))
        full_close += [full_close[-1]] * fps
        mp4_close = out_dir / f"{name}_close.mp4"
        imageio.mimsave(mp4_close, full_close, fps=fps, macro_block_size=1)

    if run_vlm_judge:
        vlm_judge(mp4, out_dir / f"{name}_vlm.json")

    summary = dict(frames=len(full), collisions=int(track["collision"].sum()),
                   max_tip_ul=float(track["held"].max()), max_fill_pct=float(track["maxfill"].max() * 100),
                   issues=int(track["issues"].max()))
    return len(full), mp4, gif, png, summary


def contact_sheet(frames, k=12, cols=3):
    idx = np.linspace(0, len(frames) - 1, k).astype(int)
    tiles = [np.asarray(Image.fromarray(frames[j]).resize((640, 330), Image.LANCZOS)) for j in idx]
    rows = [np.concatenate(tiles[r * cols:(r + 1) * cols], axis=1) for r in range(k // cols)]
    return np.concatenate(rows, axis=0)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1].strip())
    ap.add_argument("ir", nargs="?")
    ap.add_argument("-o", "--out", help="output mp4 path (gif and frames png go next to it)")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--no-lift", action="store_true", help="travel at work height to trigger the collision check")
    ap.add_argument("--pipette-max", type=float, default=1000.0, help="pipette capacity in uL (default P1000)")
    ap.add_argument("--close-cam", action="store_true",
                    help="also render a _close.mp4 at 65%% distance / shallower angle for liquid fill detail")
    ap.add_argument("--vlm-judge", action="store_true",
                    help="after rendering, send 5 frames to claude-haiku for QC grading (needs ANTHROPIC_API_KEY)")
    a = ap.parse_args()
    if _HAS_OT2 and a.all is False and a.ir:
        print(f"[ir_mujoco] opentrons-mujoco-viz fork found — OT-2 slot positions active for ≤12 container protocols")
    jobs = [(src, ROOT / "assets/examples3d", name_for(src)) for src in find_irs()] if a.all else \
        [(pathlib.Path(a.ir), pathlib.Path(a.out or "ir3d.mp4").parent, pathlib.Path(a.out or "ir3d.mp4").stem)]
    for src, d, name in jobs:
        proto = Protocol.model_validate_json(src.read_text())
        nfr, mp4, gif, png, info = render(proto, d, name, pipette_max=a.pipette_max, lift=not a.no_lift,
                                           close_cam=a.close_cam, run_vlm_judge=a.vlm_judge)
        print(f"{src.relative_to(ROOT) if src.is_absolute() and ROOT in src.parents else src}: {nfr} frames -> {mp4.name} "
              f"({mp4.stat().st_size / 1e6:.1f} MB), {gif.name} ({gif.stat().st_size / 1e6:.1f} MB), {png.name}  {info}")
