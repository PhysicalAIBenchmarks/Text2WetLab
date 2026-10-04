"""
Visualise any Protocol IR (paper2protocol schema) as a deck of labware that fills and empties.

    python eval/ir_viz.py tasks/split-200ul-two-wells/public/ir.json -o assets/examples/L1.gif
    python eval/ir_viz.py data/pipeline_runs/<doi>/exp1/protocol.json -o assets/examples/paper.gif
    python eval/ir_viz.py --all          # every IR in the repo -> assets/examples/

One panel per container: 96-well plates as 8x12 grids, tubes / reservoirs / waste as a
single bar. Volume bookkeeping follows paper2protocol/check.py (same well expansion and
source/destination pairing), so the picture and the checker agree. Orange border = source
of the current step, cyan = destination. Checker errors for a step show in red.

Needs: matplotlib, imageio, pydantic (no Opentrons, no MuJoCo).
"""

import argparse
import pathlib
import sys

import imageio
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import textwrap  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from paper2protocol.check import check, expand_wells  # noqa: E402
from paper2protocol.timeline import pairs, timeline  # noqa: E402
from paper2protocol.models import CAPACITY_UL, Protocol  # noqa: E402
from paper2protocol.render import step_line  # noqa: E402

BG, PANEL, TEXT = "#07070f", "#0c0c1a", "#8090c0"
SRC, DST, BAD = "#ffa726", "#00d4ff", "#ff5252"
MAX_PANELS_PER_ROW = 8
MIN_COLS = 4  # keeps a 1-2 container deck from stretching panels across the frame


FILL_CMAP = LinearSegmentedColormap.from_list(
    "fill", [(0.0, "#2b6cff"), (0.5, "#18d6c8"), (0.8, "#ffd23f"), (1.0, "#ff9100")])
EMPTY_RGB = (0.04, 0.04, 0.08)
LEGEND = [("0-80%", "#18d6c8"), ("80-100%", "#ffd23f"), ("full", "#ff9100"),
          (">cap", "#ff2626"), ("overdrawn", "#ff00cc"), ("stock", "#00e676")]


def fill_rgb(ratio, stock=False):
    """Colour for a fill ratio (volume / capacity): blue (low) -> teal -> amber (80%+) -> orange (full).
    Red = above capacity, magenta = overdrawn (negative volume), green = stock with ample volume."""
    if stock:
        return (0.0, 0.9, 0.5)
    if ratio < -1e-9:
        return (1.0, 0.0, 0.8)
    if ratio > 1 + 1e-9:
        return (1.0, 0.15, 0.15)
    return tuple(FILL_CMAP(min(ratio, 1.0))[:3])


def ratio(state, key, kind):
    """Volume / capacity for one well or tube; None = stock with ample volume; 0 if never filled."""
    v = state.get(key, 0.0)
    if v is None:
        return None
    return v / (CAPACITY_UL.get(kind) or 1.0)


def draw(p, kinds, state, touched, caption, bad, size=(1280, 720)):
    n = len(p.containers)
    cols = max(MIN_COLS, min(MAX_PANELS_PER_ROW, n))
    rows = -(-n // cols)
    fig = plt.figure(figsize=(size[0] / 100, size[1] / 100), dpi=100, facecolor=BG)
    gs = fig.add_gridspec(rows, cols, left=0.01, right=0.99, top=0.88, bottom=0.02, wspace=0.12, hspace=0.45)
    src_c = {c for c, _ in touched[0]}
    dst_c = {c for c, _ in touched[1]}
    for i, c in enumerate(p.containers):
        ax = fig.add_subplot(gs[i // cols, i % cols])
        ax.set_facecolor(PANEL)
        ax.set_xticks([]); ax.set_yticks([])
        if c.kind.startswith("plate_96"):
            img = np.zeros((8, 12, 3)) + EMPTY_RGB
            for r in range(8):
                for k in range(12):
                    f = ratio(state, (c.name, f"{'ABCDEFGH'[r]}{k + 1}"), c.kind)
                    if f is None:
                        img[r, k] = fill_rgb(0, True)
                    elif abs(f) > 1e-9:
                        img[r, k] = fill_rgb(f)
            ax.imshow(img, aspect="equal")
            for (cn, w) in touched[0] + touched[1]:
                if cn == c.name and w:
                    r, k = "ABCDEFGH".index(w[0]), int(w[1:]) - 1
                    ax.add_patch(plt.Rectangle((k - .5, r - .5), 1, 1, fill=False,
                                               ec=SRC if (cn, w) in touched[0] else DST, lw=1))
        else:
            f = ratio(state, (c.name, ""), c.kind)
            if f is None:
                ax.barh([0], [1.0], color=fill_rgb(0, True), height=0.6)
            elif abs(f) > 1e-9:
                ax.barh([0], [min(max(abs(f), 0.04), 1.0)], color=fill_rgb(f), height=0.6)
            ax.set_xlim(0, 1); ax.set_ylim(-.6, .6)
            if c.kind == "waste":
                ax.set_facecolor("#1a0c0c")
        for sp in ax.spines.values():
            sp.set_color(SRC if c.name in src_c else DST if c.name in dst_c else "#1c1c30")
            sp.set_linewidth(2.2 if c.name in src_c | dst_c else 0.6)
        ax.set_title(c.name[:22], color=TEXT, fontsize=6, fontfamily="monospace", pad=2)
    lines = textwrap.wrap(caption, 125)[:2]
    if len(textwrap.wrap(caption, 125)) > 2:
        lines[1] = lines[1][:121] + " ..."
    fig.text(0.012, 0.955, "\n".join(lines), color="#00d4ff", fontsize=9, fontfamily="monospace", va="center")
    if bad:
        fig.text(0.012, 0.905, "⚠ " + textwrap.shorten(bad, 150), color=BAD, fontsize=8, fontfamily="monospace", va="center")
    fig.canvas.draw()
    frame = np.asarray(fig.canvas.buffer_rgba())[..., :3].copy()
    plt.close(fig)
    return frame


def render(p: Protocol, out: pathlib.Path, fps=3, size=(1280, 720)):
    kinds = {c.name: c.kind for c in p.containers}
    states, touched = timeline(p)
    issues = {}
    for iss in check(p):
        issues.setdefault(iss.step, []).append(iss.message)
    n = len(p.steps)
    frames = [draw(p, kinds, states[0], ([], []), f"{p.title[:100]} · start", "; ".join(issues.get(0, [])), size)]
    for i, s in enumerate(p.steps, 1):
        cap = f"step {i}/{n} · {step_line(s)}"
        frames.append(draw(p, kinds, states[i], touched[i], cap, "; ".join(issues.get(i, [])), size))
    frames += [frames[-1]] * 3  # hold the last frame
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.suffix == ".gif":
        imageio.mimsave(out, frames, duration=1000 / fps, loop=0)
    else:
        imageio.mimsave(out, frames, fps=fps)
    return len(frames), out.stat().st_size


def find_irs():
    found = sorted(ROOT.glob("tasks/*/public/ir.json")) + sorted(ROOT.glob("data/pipeline_runs/*/exp*/protocol.json"))
    return found


def name_for(path: pathlib.Path):
    rel = path.relative_to(ROOT)
    if rel.parts[0] == "tasks":
        return rel.parts[1]
    return f"paper-{rel.parts[2].replace('.', '_')}-{rel.parts[3]}"


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1].strip())
    ap.add_argument("ir", nargs="?", help="Protocol IR json")
    ap.add_argument("-o", "--out", help="output .gif or .mp4")
    ap.add_argument("--all", action="store_true", help="render every IR in the repo to assets/examples/")
    ap.add_argument("--fps", type=int, default=3)
    a = ap.parse_args()
    targets = [(p, ROOT / "assets/examples" / f"{name_for(p)}.gif") for p in find_irs()] if a.all else \
        [(pathlib.Path(a.ir), pathlib.Path(a.out or "ir.gif"))]
    for src, dst in targets:
        proto = Protocol.model_validate_json(src.read_text())
        nframes, size = render(proto, dst, a.fps)
        print(f"{src} -> {dst}  {nframes} frames  {size / 1e6:.1f} MB")
