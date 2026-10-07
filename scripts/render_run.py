"""Render what a protocol actually does on the OT-2: simulate it, then drive the opentrons-mujoco-viz scene with the events.

    python scripts/render_run.py protocol.py out.mp4 [--labware DIR]

Two interpreters are involved: Opentrons 7.5.0 simulates (OT_VENV) and the viz fork renders (VIZ_VENV, which has mujoco and
opentrons-mujoco-viz). The events come from eval/runlog.py, not from the fork's own text parser, because that parser
expects an older log format ("well A1 of ...") and finds nothing in Opentrons 7.5 output. It also uses the fork's
fallback 'free' camera: the fork's named cameras (iso, side, front, deck) render black.
"""
import argparse
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "eval"))
sys.path.insert(0, str(ROOT))
from spec_check import simulate  # noqa: E402

VIZ_VENV = pathlib.Path(os.environ.get("VIZ_VENV", ROOT / ".venv-viz"))


RENDERED = {"aspirate", "dispense", "pick", "drop", "delay", "engage", "disengage", "temp"}


def fork_events(events: list[dict]) -> list[dict]:
    out = []
    for e in events:
        k = e["kind"]
        if k in ("aspirate", "dispense"):
            slot = re.search(r" on (?:slot )?(\d+)$", e["labware"])
            out.append({"type": k, "volume": e["volume"], "well": e["well"], "slot": int(slot[1]) if slot else None})
        elif k in ("pick", "drop"):
            out.append({"type": k})
        elif k == "delay":
            out.append({"type": "delay", "minutes": int(e["seconds"] // 60), "seconds": e["seconds"] % 60})
        elif k == "engage":
            out.append({"type": "engage", "height": 13.0})
        elif k == "disengage":
            out.append({"type": "disengage"})
        elif k == "temp":
            out.append({"type": "temp_set", "celsius": e["celsius"]})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("protocol")
    ap.add_argument("out")
    ap.add_argument("--labware")
    a = ap.parse_args()
    sim = simulate(a.protocol, a.labware)
    if not sim["ok"]:
        sys.exit(f"does not simulate: {sim['error'][:200]}")
    with tempfile.TemporaryDirectory() as d:
        ev = pathlib.Path(d, "events.json")
        ev.write_text(json.dumps(fork_events(sim["events"])))
        # Same loop as the fork's render_protocol (4 frames per event, 12 fps), but it also records the frame each
        # event starts on, so <out>.timeline.json maps every simulator event to a time in the video.
        code = ("import json,sys,imageio; from opentrons.visualization import WetLabScene; "
                "WetLabScene.render.__defaults__ = ('free',); "      # apply_event renders with the default camera, which is black
                "evs=json.load(open(sys.argv[1]));\n"
                "with WetLabScene() as s:\n"
                "    fr=[s.render_with_hud('free')]; start=[]\n"
                "    for e in evs:\n"
                "        start.append(len(fr)); fr.extend(s.apply_event(e)); fr.extend(s.render_with_hud('free') for _ in range(3))\n"
                "    imageio.mimsave(sys.argv[2], fr, fps=12)\n"
                "json.dump(start, open(sys.argv[3],'w'))")
        tl = pathlib.Path(d, "start.json")
        subprocess.run([str(VIZ_VENV / "bin/python"), "-c", code, str(ev), a.out, str(tl)], check=True, capture_output=True, timeout=1800)
        starts = json.loads(tl.read_text())
    timeline = [{"t": round(f / 12, 3), **{k: e.get(k) for k in ("kind", "volume", "well", "labware", "seconds", "text")}}
                for f, e in zip(starts, [e for e in sim["events"] if e["kind"] in RENDERED])]
    pathlib.Path(a.out + ".timeline.json").write_text(json.dumps(timeline))
    print(f"{len(sim['events'])} events -> {a.out} (+ .timeline.json)")


if __name__ == "__main__":
    main()
