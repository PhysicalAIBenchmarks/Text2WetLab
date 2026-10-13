"""Render a run log (eval/runlog.py event format) in the opentrons-mujoco-viz scene.

usage: mj_render.py <events.json> <out.mp4> [target_seconds=45]
Every event updates the scene state; only a sample of events is animated and rendered, so a
6,000-event protocol and a 10-event one both come out near the target length (12 fps).
"""
import json, re, sys, time
import imageio
import numpy as np
from PIL import Image, ImageDraw, ImageFont

try:
    FONT = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
except Exception:
    FONT = ImageFont.load_default()


def caption(frame, text):
    img = Image.fromarray(frame).convert("RGB")
    d = ImageDraw.Draw(img, "RGBA")
    w, h = img.size
    d.rectangle([8, h - 44, w - 8, h - 8], fill=(0, 0, 0, 190))
    d.text((18, h - 38), text[:100], font=FONT, fill=(255, 255, 255, 255))
    return np.asarray(img)


def describe(e):
    k = e["kind"]
    if k in ("aspirate", "dispense"):
        return f"{k} {e['volume'] * e.get('channels', 1):g} uL  {e['well']} of {e['labware']}"
    if k == "delay":
        return f"delay {e['seconds']:.0f} s"
    return {"pick": "pick up tip", "drop": "drop tip", "engage": "magnet engaged", "disengage": "magnet disengaged"}.get(k, k)
from opentrons.visualization import WetLabScene

FPS = 12


def convert(e):
    k = e["kind"]
    if k in ("aspirate", "dispense"):
        m = re.search(r" on (?:slot )?(\d+)$", e["labware"])
        return {"type": k, "volume": e["volume"] * e.get("channels", 1), "well": e["well"], "slot": int(m[1]) if m else None}
    if k in ("pick", "drop"):
        return {"type": k}
    if k == "delay":
        return {"type": "delay", "minutes": int(e["seconds"] // 60), "seconds": e["seconds"] % 60}
    if k == "engage":
        return {"type": "engage", "height": 13.0}
    if k == "disengage":
        return {"type": "disengage"}
    if k == "temp":
        return {"type": "temp_set", "celsius": e["celsius"]}
    return None


def main(src, out, target=45.0, label=""):
    raw = json.load(open(src))["events"]
    pairs, note = [], ""
    for e in raw:
        if e["kind"] == "comment":
            note = e["text"][:60]
            continue
        c = convert(e)
        if c:
            pairs.append((c, f"{label} | " + (note + " | " if note else "") + describe(e)))
    evs = [c for c, _ in pairs]
    budget = max(24, int(float(target) * FPS))
    per = 3                                   # frames per animated event
    stride = max(1, -(-len(evs) * per // budget))
    t0 = time.time()
    with WetLabScene() as s:
        frames = [caption(s.render_with_hud("free"), f"{label}: start")] * 6
        for i, e in enumerate(evs):
            if i % stride:
                s.state.apply_event(e)        # state only: no gantry motion, no render
                continue
            s.apply_event(e, motion_steps=40)
            f = caption(s.render_with_hud("free"), pairs[i][1])
            frames.extend([f] * per)
        s._sync_visuals()
        frames.extend([caption(s.render_with_hud("free"), f"{label}: finished ({len(evs)} robot events)")] * (FPS * 2))
        imageio.mimsave(out, frames, fps=FPS, macro_block_size=1)
    print(f"{len(evs)} events, stride {stride}, {len(frames)} frames, {time.time() - t0:.0f}s -> {out}")


if __name__ == "__main__":
    main(*sys.argv[1:5])
