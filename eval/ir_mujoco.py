"""
Headless 3D (MuJoCo) view of any Protocol IR, side by side with the 2D IR view.

    python eval/ir_mujoco.py tasks/L1/example/ir.json -o assets/examples3d/L1-example.mp4
    python eval/ir_mujoco.py --all          # every IR in the repo -> assets/examples3d/

The scene is generated from the IR: one labware model per container on a virtual deck (one
slot per container, so decks with 40+ containers are larger than a real OT-2). A gantry head
travels at a safe height, goes down to the source, aspirates, travels, dispenses, and lifts.
Liquid levels in every well / tube / reservoir follow the same bookkeeping as the 2D view
(ir_viz.timeline, which follows paper2protocol/check.py).

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
import mujoco
import numpy as np
from PIL import Image, ImageDraw

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "eval"))
sys.path.insert(0, str(ROOT))
from ir_viz import draw, find_irs, name_for, pairs, timeline  # noqa: E402
from paper2protocol.check import check, expand_wells  # noqa: E402
from paper2protocol.models import CAPACITY_UL, Protocol  # noqa: E402
from paper2protocol.render import step_line  # noqa: E402

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
        self.cols = max(2, math.ceil(math.sqrt(n * 1.3)))
        self.rows = math.ceil(n / self.cols)
        self.W, self.H = self.cols * PITCH_X, self.rows * PITCH_Y
        self.origin = {}  # container -> world (x, y) of its centre
        self.top = {}     # container -> world z of its rim
        parts = []
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
      <geom type="cylinder" pos="0 0 .025" size=".0022 .025" rgba=".98 .75 .1 1" contype="0" conaffinity="0"/>
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
        gid = lambda n: mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_GEOM, n)
        self.tip_liq = gid("tip_liq")
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
            self._liq_specs[(nm, "")] = (f"c{i}_liq", "cyl", 0.0, ht * 0.95)
            return (f'<geom type="cylinder" pos="{x} {y} {ht / 2}" size="{rad} {ht / 2}" rgba=".8 .85 .95 .12" {no}/>'
                    f'<geom name="c{i}_liq" type="cylinder" pos="{x} {y} {ht / 2}" size="{rad * .85} {ht * .475}" rgba="{LIQ}" {no}/>')
        ht = 0.03  # reservoir / waste
        self.top[nm] = ht
        self._liq_specs[(nm, "")] = (f"c{i}_liq", "box", 0.0, ht * 0.9)
        col = ".35 .1 .1 .35" if k == "waste" else ".8 .9 .85 .25"
        return (f'<geom type="box" pos="{x} {y} {ht / 2}" size=".06 .04 {ht / 2}" rgba="{col}" {no}/>'
                f'<geom name="c{i}_liq" type="box" pos="{x} {y} {ht / 2}" size=".055 .035 {ht * .45}" rgba="{LIQ}" {no}/>')

    # -- liquid -------------------------------------------------------------------------
    def set_level(self, key, frac, stock=False):
        gid, kind, base, max_h = self.liq[key]
        m = self.model
        if frac <= 1e-9:
            m.geom_rgba[gid, 3] = 0.0
            return
        h = max(0.0006, 0.5 * math.sqrt(frac) * max_h)  # half-height; sqrt so small volumes stay visible
        m.geom_rgba[gid] = [float(v) for v in (STOCK if stock else LIQ).split()]
        m.geom_size[gid, 1 if kind == "cyl" else 2] = h
        m.geom_pos[gid, 2] = base + h

    def apply_state(self, before, after, p_src, p_dst, src_keys, dst_keys):
        src_keys, dst_keys = set(src_keys), set(dst_keys)
        for key in self.liq:
            kind = self.kinds[key[0]]
            cap = CAPACITY_UL.get(kind) or 1.0
            b, a = before.get(key, 0.0), after.get(key, 0.0)
            if key in src_keys:
                t = p_src
            elif key in dst_keys:
                t = p_dst
            else:
                t = 1.0
            if b is None or a is None:
                self.set_level(key, 1.0, stock=True)
                continue
            self.set_level(key, float(np.clip((b + (a - b) * t) / cap, 0, 1)))

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

    def frame(self):
        mujoco.mj_forward(self.model, self.data)
        self.renderer.update_scene(self.data, self.cam)
        return self.renderer.render()


def segment(a, b, n):
    return [tuple(np.array(a) + (np.array(b) - np.array(a)) * (k + 1) / n) for k in range(n)]


def build_frames(p: Protocol, fps_hint=12):
    deck = Deck(p)
    states, touched = timeline(p)
    issues = {}
    for iss in check(p):
        issues.setdefault(iss.step, []).append(iss.message)
    kinds = deck.kinds
    safe = deck.safe_z
    pos = (0.0, 0.0, safe)
    out = []  # (3d frame, step index, phase 0/1 for 2D before/after)

    def emit(step_i, before, after, p_src, p_dst, held, src_k, dst_k, head):
        deck.apply_state(before, after, p_src, p_dst, src_k, dst_k)
        deck.set_held(held)
        deck.place(head)
        out.append((deck.frame(), step_i, 1 if (p_src >= 1 or p_dst > 0) else 0))

    deck.place(pos)
    emit(0, states[0], states[0], 1, 1, 0, [], [], pos)
    for i, s in enumerate(p.steps, 1):
        before, after = states[i - 1], states[i]
        src_k, dst_k = touched[i]
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
                q = (dx, dy, dz + 0.006 * (k % 2))
                emit(i, before, before, 1, 1, 0, [], [], q)
            pos = (dx, dy, safe)
            for q in segment((dx, dy, dz), pos, 2):
                emit(i, before, before, 1, 1, 0, [], [], q)
            continue
        sx, sy = deck.well_xy(s.source, s.source_wells)
        dx, dy = deck.well_xy(s.dest, s.dest_wells)
        sz, dz = deck.work_z(s.source), deck.work_z(s.dest)
        leg1 = segment(pos, (pos[0], pos[1], safe), 2) + segment((pos[0], pos[1], safe), (sx, sy, safe), 4) \
            + segment((sx, sy, safe), (sx, sy, sz), 2)
        for q in leg1:
            emit(i, before, before, 0, 0, 0, src_k, dst_k, q)
        for k in range(1, 4):  # aspirate
            emit(i, before, after, k / 3, 0, k / 3, src_k, dst_k, (sx, sy, sz))
        leg2 = segment((sx, sy, sz), (sx, sy, safe), 2) + segment((sx, sy, safe), (dx, dy, safe), 5) \
            + segment((dx, dy, safe), (dx, dy, dz), 2)
        for q in leg2:
            emit(i, before, after, 1, 0, 1, src_k, dst_k, q)
        for k in range(1, 4):  # dispense
            emit(i, before, after, 1, k / 3, 1 - k / 3, src_k, dst_k, (dx, dy, dz))
        pos = (dx, dy, safe)
        for q in segment((dx, dy, dz), pos, 2):
            emit(i, before, after, 1, 1, 0, src_k, dst_k, q)
    return deck, states, touched, issues, out


def label(img, text):
    im = Image.fromarray(img)
    d = ImageDraw.Draw(im)
    y0 = im.height - 18
    d.rectangle([0, y0, 8 + 7 * len(text), im.height], fill=(7, 7, 15))
    d.text((4, y0 + 3), text, fill=(0, 212, 255))
    return np.asarray(im)


def render(p: Protocol, out_dir: pathlib.Path, name: str, fps=12):
    deck, states, touched, issues, frames3d = build_frames(p)
    kinds = deck.kinds
    n = len(p.steps)
    panels = {}
    for i in range(n + 1):  # 2D panel before/after each step
        cap = f"{p.title[:100]} · start" if i == 0 else f"step {i}/{n} · {step_line(p.steps[i - 1])}"
        bad = "; ".join(issues.get(i, []))
        for phase, st in ((0, states[max(i - 1, 0)]), (1, states[i])):
            tt = touched[i] if i else ([], [])
            panels[(i, phase)] = label(draw(p, kinds, st, tt, cap, bad, PANEL), "2D  IR view")
    full = []
    for img, i, phase in frames3d:
        full.append(np.concatenate([panels[(i, phase)], label(img, "3D  MuJoCo")], axis=1))
    full += [full[-1]] * fps
    out_dir.mkdir(parents=True, exist_ok=True)
    mp4 = out_dir / f"{name}.mp4"
    imageio.mimsave(mp4, full, fps=fps, macro_block_size=1)
    stride = max(2, math.ceil(len(full) / 150))  # keep the inline GIF to ~150 frames
    small = [np.asarray(Image.fromarray(f).resize((f.shape[1] // 2, f.shape[0] // 2), Image.LANCZOS))
             for f in full[::stride]]
    gif = out_dir / f"{name}.gif"
    imageio.mimsave(gif, small, duration=1000 * stride / fps, loop=0)
    sheet = contact_sheet(full)
    png = out_dir / f"{name}_frames.png"
    Image.fromarray(sheet).save(png)
    return len(full), mp4, gif, png


def contact_sheet(frames, k=12, cols=3):
    idx = np.linspace(0, len(frames) - 1, k).astype(int)
    tiles = [np.asarray(Image.fromarray(frames[j]).resize((640, 240), Image.LANCZOS)) for j in idx]
    rows = [np.concatenate(tiles[r * cols:(r + 1) * cols], axis=1) for r in range(k // cols)]
    return np.concatenate(rows, axis=0)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1].strip())
    ap.add_argument("ir", nargs="?")
    ap.add_argument("-o", "--out", help="output mp4 path (gif and frames png go next to it)")
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args()
    jobs = [(src, ROOT / "assets/examples3d", name_for(src)) for src in find_irs()] if a.all else \
        [(pathlib.Path(a.ir), pathlib.Path(a.out or "ir3d.mp4").parent, pathlib.Path(a.out or "ir3d.mp4").stem)]
    for src, d, name in jobs:
        proto = Protocol.model_validate_json(src.read_text())
        nfr, mp4, gif, png = render(proto, d, name)
        print(f"{src.relative_to(ROOT) if src.is_absolute() and ROOT in src.parents else src}: {nfr} frames -> {mp4.name} "
              f"({mp4.stat().st_size / 1e6:.1f} MB), {gif.name} ({gif.stat().st_size / 1e6:.1f} MB), {png.name}")
