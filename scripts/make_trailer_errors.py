#!/usr/bin/env python3
"""Build the Text2WetLab submission video: results/trailer_errors.mp4 (1280x720, 24 fps, under 2 minutes).

    uv run python scripts/make_trailer_errors.py [--renders DIR]

Three worked errors from the eval runs, each as:
  original text (task / paper, CC BY page with the passage highlighted) | AI breakdown (Protocol IR)
  -> AI code with the faulty lines boxed in red | the agent's run, replayed in MuJoCo
  -> ground truth (oracle or the authors' own script) next to the agent, with materials cost and impact
The video panels are composited frame by frame from <render>.timeline.json (scripts/render_run.py), so the red
border and the event ticker turn red exactly while the erroneous robot events play.

Inputs: --renders DIR with r7-ecoli-opus, gt-ecoli, r7-rna-opus, gt-rna, r5-rna-sonnet (.mp4 + .timeline.json),
made by scripts/trailer_renders.py. Agent code panels are read from the eval-round commits with git show. Source PDFs are fetched from
sources/<slug>/record.json and checked against its SHA-256; only redistributable (CC BY) papers are used.
A scene-by-scene time split is written to results/trailer_errors_timesplits.md.
Needs ffmpeg and poppler (pdftoppm, pdftotext).
"""
import argparse
import hashlib
import html
import json
import re
import subprocess
import tempfile
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "results"
OUT = RES / "trailer_errors.mp4"
HIST_BRANCH = "backup/l2-outputs-oct04"
CACHE = Path.home() / ".cache/text2wetlab"

W, H, FPS = 1280, 720, 24
BG = (7, 8, 13)
PANEL = (17, 19, 28)
LINE = (40, 44, 60)
WHITE = (240, 242, 248)
LGREY = (190, 194, 205)
MGREY = (130, 135, 150)
DGREY = (80, 84, 98)
AMBER = (245, 158, 11)
TEAL = (20, 184, 166)
RED = (239, 68, 68)
HILITE = (250, 204, 21)

SANS = "/System/Library/Fonts/HelveticaNeue.ttc"
MONO = "/System/Library/Fonts/Menlo.ttc"
MODELS = [("claude-opus-5-5", "Opus 5.5"), ("claude-sonnet-5-5", "Sonnet 5.5"), ("claude-fable-5-1", "Fable 5.1")]


def F(size, mono=False, bold=False):
    return ImageFont.truetype(MONO if mono else SANS, size, index=1 if bold and not mono else 0)


# ── ffmpeg helpers ─────────────────────────────────────────────────────────────

def run(*cmd):
    subprocess.run([str(c) for c in cmd], check=True)


def ff(*args):
    run("ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *args)


def duration(path) -> float:
    r = subprocess.run(["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                        "-of", "default=nw=1:nk=1", str(path)], capture_output=True, text=True, check=True)
    return float(r.stdout.strip())


ENC = ["-pix_fmt", "yuv420p", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-r", str(FPS), "-an"]


def scene(out: Path, dur: float, bg: Image.Image, clips=(), fade=0.35):
    """bg image + clips overlaid. clip = dict(src, box=(x,y,w,h), speed=None|float, ss=0)."""
    png = out.with_suffix(".png")
    bg.save(png)
    args = ["-loop", "1", "-framerate", str(FPS), "-i", str(png)]
    chain, last = [], "[0:v]"
    for i, c in enumerate(clips, 1):
        src = Path(c["src"])
        loop = ["-ignore_loop", "0"] if src.suffix == ".gif" else ["-stream_loop", "-1"]
        args += loop + (["-ss", str(c["ss"])] if c.get("ss") else []) + ["-i", str(src)]
        x, y, w, h = c["box"]
        speed = c.get("speed") or max(1.0, (duration(src) - c.get("ss", 0)) / dur)
        crop = c.get("crop")
        crop_f = f"crop=iw*{crop[2]}:ih*{crop[3]}:iw*{crop[0]}:ih*{crop[1]}," if crop else ""
        chain.append(f"[{i}:v]{crop_f}setpts=(PTS-STARTPTS)/{speed:.4f},fps={FPS},"
                     f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
                     f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=0x07080d[c{i}]")
        chain.append(f"{last}[c{i}]overlay={x}:{y}:shortest=0[o{i}]")
        last = f"[o{i}]"
    chain.append(f"{last}fade=t=in:st=0:d={fade},fade=t=out:st={dur - fade:.3f}:d={fade}[v]")
    ff(*args, "-filter_complex", ";".join(chain), "-map", "[v]", "-t", f"{dur:.3f}", *ENC, str(out))
    png.unlink()
    return out


# ── drawing helpers ────────────────────────────────────────────────────────────

def canvas():
    return Image.new("RGB", (W, H), BG)


def text(d, xy, s, size, color=WHITE, mono=False, bold=False, anchor="la"):
    d.text(xy, s, font=F(size, mono, bold), fill=color, anchor=anchor)


def wrap(d, xy, s, size, width_px, color=LGREY, mono=False, gap=6, highlights=()):
    """Word-wrap s into width_px; phrases in `highlights` get a yellow marker behind them."""
    f = F(size, mono)
    x0, y = xy
    words, line, lines = s.split(), "", []
    for w_ in words:
        t = (line + " " + w_).strip()
        if d.textlength(t, font=f) > width_px and line:
            lines.append(line)
            line = w_
        else:
            line = t
    lines.append(line)
    for ln in lines:
        for ph in highlights:
            for m in re.finditer(re.escape(ph), ln, re.I):
                a = x0 + d.textlength(ln[:m.start()], font=f)
                b = x0 + d.textlength(ln[:m.end()], font=f)
                d.rectangle([a - 2, y - 1, b + 2, y + size + 3], fill=(92, 74, 8))
        d.text((x0, y), ln, font=f, fill=color)
        y += size + gap
    return y


def chrome(img, kicker, caption=""):
    d = ImageDraw.Draw(img)
    text(d, (40, 28), kicker.upper(), 15, AMBER, bold=True)
    d.line([(40, 54), (W - 40, 54)], fill=LINE, width=1)
    if caption:
        text(d, (40, H - 30), caption, 14, DGREY)
    return d


def label(d, xy, s, color=AMBER, size=17):
    x, y = xy
    f = F(size, bold=True)
    w = d.textlength(s, font=f)
    d.rectangle([x, y, x + w + 20, y + size + 14], fill=(0, 0, 0))
    d.text((x + 10, y + 6), s, font=f, fill=color)


# ── source papers ──────────────────────────────────────────────────────────────

def fetch_pdf(slug) -> Path:
    rec = json.loads((ROOT / "sources" / slug / "record.json").read_text())["pdf"]
    assert rec.get("redistributable") == "yes", f"{slug}: licence does not allow reuse ({rec.get('licence')})"
    CACHE.mkdir(parents=True, exist_ok=True)
    p = CACHE / f"{slug}.pdf"
    if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest() != rec["sha256"]:
        req = urllib.request.Request(rec["url"], headers={"User-Agent": "Mozilla/5.0"})
        p.write_bytes(urllib.request.urlopen(req, timeout=60).read())
    assert hashlib.sha256(p.read_bytes()).hexdigest() == rec["sha256"], f"{slug}: SHA-256 mismatch"
    return p


def norm(t):
    return re.sub(r"[^\wμµ]", "", t.lower().replace("µ", "μ"))


def pdf_panel(pdf: Path, page: int, phrases, size, tmp: Path) -> Image.Image:
    """Crop of `page` around the highlighted phrases, scaled to `size`, with a page thumbnail inset."""
    dpi = 200
    stem = tmp / f"{pdf.stem}-p{page}"
    run("pdftoppm", "-r", dpi, "-f", page, "-l", page, "-png", "-singlefile", pdf, stem)
    run("pdftotext", "-bbox-layout", "-f", page, "-l", page, pdf, f"{stem}.html")
    page_img = Image.open(f"{stem}.png").convert("RGB")
    k = dpi / 72
    words = [(html.unescape(m[4]), *(float(v) * k for v in m[:4]))
             for m in re.findall(r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">([^<]*)</word>',
                                 Path(f"{stem}.html").read_text())]
    toks = [norm(w[0]) for w in words]
    over = Image.new("RGBA", page_img.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(over)
    boxes = []
    for ph in phrases:
        ph, nth = ph if isinstance(ph, tuple) else (ph, 0)
        pt = [norm(t) for t in ph.split()]
        hits = [i for i in range(len(toks) - len(pt) + 1) if toks[i:i + len(pt)] == pt]
        for i in hits[nth:nth + 1]:
            for _, x0, y0, x1, y1 in words[i:i + len(pt)]:
                od.rectangle([x0 - 3, y0 - 2, x1 + 3, y1 + 2], fill=HILITE + (110,))
                boxes.append((x0, y0, x1, y1))
            break
        else:
            raise SystemExit(f"phrase not found on {pdf.name} p{page}: {ph!r}")
    page_img = Image.alpha_composite(page_img.convert("RGBA"), over).convert("RGB")
    # crop: the column(s) holding the highlights, padded, at the panel's aspect ratio
    bx0, by0 = min(b[0] for b in boxes), min(b[1] for b in boxes)
    bx1, by1 = max(b[2] for b in boxes), max(b[3] for b in boxes)
    pw, ph_ = size
    cx0, cx1 = max(0, bx0 - 40), min(page_img.width, bx1 + 40)
    cw = cx1 - cx0
    ch = cw * ph_ / pw
    if ch < by1 - by0 + 80:  # highlights span too tall: widen the crop
        ch = by1 - by0 + 80
        cw = ch * pw / ph_
        mid = (bx0 + bx1) / 2
        cx0, cx1 = max(0, mid - cw / 2), min(page_img.width, mid + cw / 2)
    cy0 = max(0, (by0 + by1) / 2 - ch / 2)
    crop = page_img.crop((int(cx0), int(cy0), int(cx1), int(cy0 + ch))).resize(size, Image.LANCZOS)
    thumb = page_img.copy()
    td = ImageDraw.Draw(thumb)
    td.rectangle([cx0, cy0, cx1, cy0 + ch], outline=AMBER, width=10)
    thumb.thumbnail((110, 150))
    crop.paste(thumb, (pw - thumb.width - 10, ph_ - thumb.height - 10))
    ImageDraw.Draw(crop).rectangle([pw - thumb.width - 11, ph_ - thumb.height - 11, pw - 9, ph_ - 9], outline=DGREY)
    return crop


# ── results data ───────────────────────────────────────────────────────────────

def reward(model, task):
    return json.loads((RES / model / task / "reward.json").read_text())


def judge_items(model, task):
    return json.loads((RES / model / task / "judge.json").read_text())["judge"]["items"]


def evidence(model, task, item):
    return next(i["evidence"] for i in judge_items(model, task) if i["id"] == item)


# ── video panel: render + timeline -> zoomed deck, event ticker, red border on errors ───────────────────────────

DECK = (210, 140, 800, 520)  # crop of the 960x544 OT-2 render that holds the deck


def panel_clip(src: Path, t0: float, t1: float, out_dur: float, size, out: Path, names, errors=(), oks=(), title=""):
    """Write a size=(w,h) clip of src between t0 and t1 seconds, stretched to out_dur.

    errors / oks: [(ta, tb, message)] windows in source time. During an error window the border, banner and
    ticker are red; during an ok window they are teal. names(labware, well) -> readable location."""
    import imageio.v2 as iio2
    import imageio.v3 as iio
    tl = json.loads(Path(f"{src}.timeline.json").read_text())
    sf0, sf1 = int(t0 * 12), int(t1 * 12) + 1
    src_frames = []
    for i, fr in enumerate(iio.imiter(src)):
        if i >= sf1:
            break
        if i >= sf0:
            src_frames.append(fr)
    w, h = size
    vh = h - 112
    n = int(out_dur * FPS)
    speed = (t1 - t0) / out_dur
    writer = iio2.get_writer(str(out), fps=FPS, codec="libx264", quality=8, macro_block_size=1)
    fbold, freg, fban = F(15, bold=True), F(15), F(16, bold=True)

    def window(s, wins):
        return next((wn for wn in wins if wn[0] <= s <= wn[1]), None)

    def describe(e):
        v = f"{e['volume']:g} µL " if e.get("volume") else ""
        where = names(e.get("labware") or "", e.get("well") or "")
        k = {"pick": "pick up tip", "drop": "drop tip", "engage": "magnet ON", "disengage": "magnet OFF"}.get(e["kind"], e["kind"])
        if e["kind"] == "delay":
            return f"wait {e.get('seconds') or 0:g} s"
        return f"{k} {v}{('· ' + where) if where and e['kind'] in ('aspirate', 'dispense') else ''}".strip()

    for k in range(n):
        s = t0 + k / FPS * speed
        fr = Image.fromarray(src_frames[min(len(src_frames) - 1, max(0, int(s * 12) - sf0))])
        img = Image.new("RGB", (w, h), (0, 0, 0))
        img.paste(fr.crop(DECK).resize((w, vh), Image.LANCZOS), (0, 0))
        d = ImageDraw.Draw(img)
        err, ok = window(s, errors), window(s, oks)
        col = RED if err else (TEAL if ok else LINE)
        if err or ok:
            msg = (err or ok)[2]
            tw = d.textlength(msg, font=fban)
            d.rectangle([10, 10, 30 + tw, 40], fill=col)
            d.text((20, 15), msg, font=fban, fill=WHITE if err else BG)
        if title:
            d.text((w - 12, vh - 26), title, font=F(13, bold=True), fill=LGREY, anchor="ra")
        d.text((w - 12, vh - 46), f"t = {s:6.1f} s", font=F(13, mono=True), fill=MGREY, anchor="ra")
        past = [e for e in tl if e["t"] <= s][-4:]
        d.rectangle([0, vh, w, h], fill=PANEL)
        for j, e in enumerate(past):
            cur = j == len(past) - 1
            bad, good = window(e["t"], errors), window(e["t"], oks)
            c = RED if bad else (TEAL if good else (WHITE if cur else MGREY))
            d.text((14, vh + 8 + j * 25), ("> " if cur else "  ") + describe(e), font=fbold if cur else freg, fill=c)
        d.rectangle([0, 0, w - 1, h - 1], outline=col, width=6 if (err or ok) else 2)
        writer.append_data(np.asarray(img))
    writer.close()
    return out


# ── static panels ─────────────────────────────────────────────────────────────────────────────────────────────

def code_panel(d, box, path, first, last, marks, head, head_col):
    """Source lines first..last of path with line numbers; marks = [(a, b, color, note)] boxes lines a..b."""
    x0, y0, x1, y1 = box
    d.rectangle(box, fill=PANEL, outline=LINE)
    text(d, (x0 + 16, y0 + 12), head, 13, head_col, bold=True)
    f = F(14, mono=True)
    lines = Path(path).read_text().splitlines()
    y, lh, ys = y0 + 42, 21, {}
    maxw = x1 - x0 - 70
    ye = {}
    for no in range(first, last + 1):
        ln = lines[no - 1].rstrip()
        ys[no] = y
        d.text((x0 + 14, y), f"{no:>3}", font=f, fill=DGREY)
        indent = " " * (len(ln) - len(ln.lstrip()) + 4)
        while True:  # wrap long lines so nothing that matters is cut off
            cut = len(ln)
            while d.textlength(ln[:cut], font=f) > maxw:
                cut -= 1
            d.text((x0 + 54, y), ln[:cut], font=f, fill=WHITE)
            y += lh
            if cut == len(ln):
                break
            ln = indent + ln[cut:]
        ye[no] = y
    ny = y + 10  # notes go under the code, never over it
    for a, b, colr, note in marks:
        d.rectangle([x0 + 48, ys[a] - 3, x1 - 8, ye[b] - 2], outline=colr, width=3)
        if note:
            tw = d.textlength(f"lines {a}-{b}: {note}", font=F(15, bold=True))
            d.rectangle([x0 + 14, ny, x0 + 34 + tw, ny + 28], fill=colr)
            text(d, (x0 + 24, ny + 5), f"lines {a}-{b}: {note}" if a != b else f"line {a}: {note}", 15, WHITE if colr == RED else BG, bold=True)
            ny += 34


def ir_panel(d, box, rows, head):
    """rows = [(step_no, summary, note, color|None)]; colored rows get a box and their note."""
    x0, y0, x1, y1 = box
    d.rectangle(box, fill=PANEL, outline=LINE)
    text(d, (x0 + 16, y0 + 12), head, 13, AMBER, bold=True)
    y = y0 + 44
    for no, summary, note, colr in rows:
        top = y
        text(d, (x0 + 16, y), f"{no:>2}", 15, DGREY, mono=True)
        y = wrap(d, (x0 + 56, y), summary, 17, x1 - x0 - 80, WHITE if colr else LGREY, gap=4)
        if note:
            y = wrap(d, (x0 + 56, y + 2), "note: " + note, 15, x1 - x0 - 80, colr or MGREY, gap=3)
        if colr:
            d.rectangle([x0 + 8, top - 6, x1 - 8, y + 2], outline=colr, width=3)
        y += 14


def strip(d, y, cost, impact):
    d.rectangle([40, y, W - 40, y + 118], fill=PANEL, outline=LINE)
    text(d, (60, y + 14), "MATERIALS AT STAKE", 13, AMBER, bold=True)
    wrap(d, (60, y + 38), cost, 16, 520, LGREY, gap=4)
    text(d, (640, y + 14), "IMPACT IF RUN AS WRITTEN", 13, RED, bold=True)
    wrap(d, (640, y + 38), impact, 16, 580, LGREY, gap=4)


# ── scenes ────────────────────────────────────────────────────────────────────────────────────────────────────

def title_card(out, dur):
    img = canvas()
    d = ImageDraw.Draw(img)
    text(d, (W // 2, 250), "Text2WetLab", 84, WHITE, bold=True, anchor="mm")
    text(d, (W // 2, 330), "Can an AI agent turn a published wet-lab method into a correct robot protocol?", 25, LGREY, anchor="mm")
    text(d, (W // 2, 372), "3 worked errors  ·  Claude agents in Harbor  ·  OT-2 replayed in MuJoCo", 19, MGREY, anchor="mm")
    text(d, (W // 2, 470), "Evan O'Leary  ·  Mohammed Alshehri  ·  Laurence Legon", 17, DGREY, anchor="mm")
    return scene(out, dur, img)


def gap_card(out, dur):
    img = canvas()
    d = chrome(img, "The reproducibility gap")
    text(d, (W // 2, 110), "Papers describe a protocol in prose. The researchers' script is what actually ran on the robot.", 22, WHITE, anchor="mm")
    steps = [("Original text", "task or paper", MGREY), ("AI breakdown", "Protocol IR", AMBER), ("AI code", "OT-2 Python", AMBER),
             ("Robot replay", "simulator + MuJoCo", AMBER), ("Ground truth", "authors' script / oracle", TEAL)]
    bw, y = 200, 210
    gap = (W - 80 - len(steps) * bw) // (len(steps) - 1)
    for i, (h_, sub, col) in enumerate(steps):
        x = 40 + i * (bw + gap)
        d.rectangle([x, y, x + bw, y + 120], fill=PANEL, outline=col, width=2)
        text(d, (x + bw // 2, y + 44), h_, 21, WHITE, bold=True, anchor="mm")
        text(d, (x + bw // 2, y + 80), sub, 15, MGREY, anchor="mm")
        if i < len(steps) - 1:
            ax = x + bw + 6
            d.line([(ax, y + 60), (ax + gap - 12, y + 60)], fill=DGREY, width=3)
            d.polygon([(ax + gap - 12, y + 53), (ax + gap - 4, y + 60), (ax + gap - 12, y + 67)], fill=DGREY)
    text(d, (W // 2, 420), "Graded by a deterministic gate (simulate + end-state checks) and a task rubric judge.", 20, LGREY, anchor="mm")
    text(d, (W // 2, 460), "Red boxes mark where the AI output departs from the ground truth.", 20, RED, anchor="mm")
    return scene(out, dur, img)


def two_col(out, dur, kicker, caption, left_draw, right_draw, clips=()):
    img = canvas()
    d = chrome(img, kicker, caption)
    left_draw(img, d)
    right_draw(img, d)
    return scene(out, dur, img, clips)


def results_card(out, dur):
    img = canvas()
    d = chrome(img, "Latest clean run  ·  R7  ·  21 trials  ·  pass@1", "Every point lost was a judge rubric item: no crash, simulator or end-state failure in any trial.")
    rows = [("Opus 5.5", 0.943, 1.25), ("Sonnet 5.5", 0.943, 0.39), ("Fable 5.1", 0.943, 3.43)]
    text(d, (40, 90), "Mean reward over 7 tasks", 16, MGREY)
    text(d, (760, 90), "Agent cost, all 7 tasks", 16, MGREY)
    for i, (name, r, c) in enumerate(rows):
        y = 125 + i * 56
        text(d, (40, y), name, 24, WHITE, bold=True)
        d.rectangle([210, y + 2, 590, y + 30], fill=PANEL)
        d.rectangle([210, y + 2, 210 + int(380 * r), y + 30], fill=TEAL)
        text(d, (605, y + 2), f"{r:.3f}", 22, WHITE, mono=True)
        d.rectangle([760, y + 2, 760 + int(100 * c), y + 30], fill=AMBER)
        text(d, (770 + int(100 * c), y + 2), f"${c:.2f}", 22, WHITE, mono=True)
    y = 330
    for s in ["All three tie. Only RNA extraction and E. coli heat shock separate the models;",
              "the other 5 tasks score 1.0 for every model.",
              "The 80 µL recovery is missed by every model: it is in the authors' code, not the paper."]:
        text(d, (40, y), s, 20, LGREY)
        y += 34
    text(d, (40, 470), "github.com/PhysicalAIBenchmarks/Text2WetLab", 24, AMBER, mono=True)
    text(d, (40, 508), "physicalaibenchmarks.github.io/Text2WetLab", 20, TEAL, mono=True)
    return scene(out, dur, img)


# ── the three examples ────────────────────────────────────────────────────────────────────────────────────────

def git_file(commit, path, tmp: Path) -> Path:
    """A file as it was at an eval-round commit (R7 = 48836f1, R5 = 8beadb3)."""
    out = tmp / f"{commit}-{path.replace('/', '_')}"
    if not out.exists():
        out.write_bytes(subprocess.run(["git", "-C", str(ROOT), "show", f"{commit}:{path}"], capture_output=True, check=True).stdout)
    return out


def ecoli_names(lw, well):
    for k, v in (("plasmid", "plasmid DNA"), ("tubes", "competent cells"), ("soc", "SOC medium")):
        if k in lw.lower():
            return f"{v} {well}"
    return ""


def rna_names(lw, well):
    slot = lw.rsplit(" ", 1)[-1] if lw else ""
    if slot == "5":
        reag = {"A1": "beads", "A2": "beads", "A4": "elution buffer", "A6": "isopropanol", "A7": "isopropanol"}.get(well, "ethanol")
        return f"reservoir {well} ({reag})"
    return {"4": f"extraction plate {well} (magnet)", "6": f"elution plate {well} (4 °C)", "1": "waste",
            "10": f"sample tube {well}", "7": f"sample tube {well}"}.get(slot, "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--renders", type=Path, default=Path("/tmp/t2wl_renders"))
    a = ap.parse_args()
    R = a.renders
    tmp = Path(tempfile.mkdtemp(prefix="t2wl_trailer_"))
    plan = []  # (name, seconds, description)

    def add(fn, name, dur, desc, *args):
        out = tmp / f"{len(plan):02d}_{name}.mp4"
        fn(out, dur, *args)
        plan.append((out, dur, name, desc))

    L, RT = (40, 72, 620, 560), (660, 72, W - 40, 560)  # left / right column boxes
    VBOX = (660, 72, 580, 488)                            # video panel x, y, w, h

    print("intro")
    add(title_card, "title", 5, "Title: can an AI agent turn a paper into a correct robot protocol?")
    add(gap_card, "gap", 8, "The reproducibility gap: text -> AI breakdown -> AI code -> replay, vs ground truth")

    # ── Example 1: E. coli heat shock (R7, Opus 5.5) ──
    print("example 1")
    ec_task = (ROOT / "tasks/ecoli-heat-shock-transformation/public/instruction.md").read_text().strip()
    ir = json.loads((ROOT / "tasks/ecoli-heat-shock-transformation/public/ir.json").read_text())["steps"]

    def ex1_left(img, d):
        d.rectangle(L, fill=PANEL, outline=LINE)
        text(d, (L[0] + 16, L[1] + 12), "ORIGINAL TASK TEXT (what the agent is given)", 13, MGREY, bold=True)
        wrap(d, (L[0] + 20, L[1] + 56), ec_task, 26, L[2] - L[0] - 40, WHITE, gap=12)

    def ex1_right(img, d):
        ir_panel(d, RT, [(1, "Transfer 2 µL plasmid DNA into the competent cells", ir[0]["note"], TEAL),
                         (2, "Manual: heat shock 42 °C 45 s, then ice 2 min", None, None),
                         (3, "Transfer 250 µL SOC medium", ir[2]["note"], None),
                         (4, "Manual: 37 °C 60 min outgrowth", ir[3]["note"], None)], "AI BREAKDOWN  ·  Protocol IR (tasks/…/public/ir.json)")

    add(lambda o, du: two_col(o, du, "Example 1 / 3  ·  E. coli heat-shock transformation", "The breakdown itself says: flick to mix, no pipetting.", ex1_left, ex1_right),
        "ex1_text", 8, "Ex1 task text | AI breakdown (step 1 note: 'Gently flick to mix, no vortex')")

    ec_agent = R / "r7-ecoli-opus.mp4"
    clip = panel_clip(ec_agent, 0, 6.33, 12, VBOX[2:], tmp / "ex1_agent.mp4", ecoli_names,
                      errors=[(1.4, 4.2, "ERROR: pipette-mixes competent cells 3 × 10 µL")], title="AI run · Opus 5.5 (R7)")
    add(lambda o, du: two_col(o, du, "Example 1 / 3  ·  AI code + robot run", "results/claude-opus-5-5/ecoli-heat-shock-transformation/protocol.py at R7 (48836f1)",
                              lambda img, d: code_panel(d, L, git_file("48836f1", "results/claude-opus-5-5/ecoli-heat-shock-transformation/protocol.py", tmp), 18, 29,
                                                        [(23, 23, RED, "mix_after=(3, 10): not in the task")], "AI CODE  ·  Opus 5.5", AMBER),
                              lambda img, d: None, [dict(src=clip, box=VBOX)]),
        "ex1_code", 12, "Ex1 AI code (line 23 mix_after boxed red) | agent replay, red while it mixes the cells (1.5-4.0 s)")

    gt = panel_clip(R / "gt-ecoli.mp4", 0, 3.33, 9.5, (580, 330), tmp / "ex1_gt.mp4", ecoli_names,
                    oks=[(0.4, 1.1, "2 µL plasmid, no mixing")], title="GROUND TRUTH · oracle")
    ag = panel_clip(ec_agent, 0, 6.33, 9.5, (580, 330), tmp / "ex1_ag.mp4", ecoli_names,
                    errors=[(1.4, 4.2, "3 × 10 µL mix in the cells")], title="AI · Opus 5.5")

    def ex1_gt(img, d):
        strip(d, 440, "One 50 µL competent-cell aliquot, 2 µL plasmid, 250 µL SOC. High-efficiency competent cells list at roughly "
                      "$10-25 per tube (estimate); a 96-tube plate is about $1-2.4k.",
              "Pipetting fragile competent cells lowers transformation efficiency: few or no colonies, and about a day lost to "
              "re-plating. Opus and Fable both made this error at R7; Sonnet did not.")
    add(lambda o, du: two_col(o, du, "Example 1 / 3  ·  ground truth vs AI", "", ex1_gt, lambda i, d: None,
                              [dict(src=gt, box=(40, 80, 580, 330)), dict(src=ag, box=(660, 80, 580, 330))]),
        "ex1_truth", 12, "Ex1 ground-truth oracle (no mix) vs agent (red during mix) + materials and impact")

    # ── Example 2: RNA extraction elution (R7, Opus 5.5; same error in all models) ──
    print("example 2")
    pdf = fetch_pdf("hulp-rna-extraction")
    p4 = pdf_panel(pdf, 4, ["Air dry for 4 min", "add 100μL of Elution Buffer", "collect the supernatant and transfer to a 96-well microtiter plate"], (580, 488), tmp)

    def ex2_left(img, d):
        img.paste(p4, (40, 72))
        d.rectangle([39, 71, 620, 560], outline=LINE)
        label(d, (48, 520), "ORIGINAL TEXT · Lázaro-Perona et al., PLOS ONE 2021, p.4 (CC BY)", MGREY, 13)

    def ex2_right(img, d):
        ir_panel(d, RT, [(32, "Manual: air dry 4 min", None, None),
                         (34, "Transfer 100 µL elution buffer (magnet off)", None, None),
                         (35, "Manual: magnet on after 30 s, wait 90 s", None, None),
                         (36, "Transfer eluted RNA to elution plate: 100 µL", "Transferred volume assumed equal to the 100 µL elution volume.", RED)],
                 "AI BREAKDOWN  ·  paper2protocol IR, sources/hulp-rna-extraction/pipeline/exp2")

    add(lambda o, du: two_col(o, du, "Example 2 / 3  ·  SARS-CoV-2 RNA extraction, 48 samples", "The paper gives no recovery volume. The AI breakdown fills the gap with an assumption.", ex2_left, ex2_right),
        "ex2_text", 9, "Ex2 paper p4 (elution steps highlighted) | AI breakdown (step 36 '100 µL assumed' boxed red)")

    rna_agent = R / "r7-rna-opus.mp4"
    clip = panel_clip(rna_agent, 524.5, 537.7, 13, VBOX[2:], tmp / "ex2_agent.mp4", rna_names,
                      errors=[(527.1, 537.7, "ERROR: recovers 100 µL, beside the bead pellet")], title="AI run · Opus 5.5 (R7)")
    add(lambda o, du: two_col(o, du, "Example 2 / 3  ·  AI code + robot run", "All three models over-recover at R7: Opus 100 µL, Sonnet 100 µL, Fable 90 µL.",
                              lambda img, d: code_panel(d, L, git_file("48836f1", "results/claude-opus-5-5/opentrons-rna-extraction/protocol.py", tmp), 198, 210,
                                                        [(205, 206, RED, "ELUTION_VOL = 100: the whole elution")], "AI CODE  ·  Opus 5.5", AMBER),
                              lambda img, d: None, [dict(src=clip, box=VBOX)]),
        "ex2_code", 13, "Ex2 AI code (recover ELUTION_VOL=100 boxed red) | agent replay cued to recovery (t=527 s), red throughout")

    gt = panel_clip(R / "gt-rna.mp4", 485.5, 498.5, 13, (580, 300), tmp / "ex2_gt.mp4", rna_names,
                    oks=[(486.9, 498.5, "80 µL, tip shifted 2 mm off the pellet")], title="GROUND TRUTH · authors' script")

    def ex2_truth(img, d):
        code_panel(d, (40, 72, 620, 372), ROOT / "sources/hulp-rna-extraction/code/viral_rna_extraction_protocol.py", 363, 373,
                   [(369, 373, TEAL, "80 µL, from the side of the well")], "GROUND TRUTH  ·  authors' viral_rna_extraction_protocol.py", TEAL)
        strip(d, 420, "Per 48-sample run: about 54 € of reagents and labware (paper: 107 € per 96 samples) and about 1 h 45 min "
                      "of robot time (3.5 h per 96).",
              "Drawing the full 100 µL next to the pellet risks bead carry-over into RT-qPCR: shifted Ct values or failed wells, "
              "then re-extraction of 48 patient samples. The paper saw no effect from bead traces in its manual variant, so this is a risk.")
    add(lambda o, du: two_col(o, du, "Example 2 / 3  ·  ground truth: the researchers' code", "", ex2_truth, lambda i, d: None,
                              [dict(src=gt, box=(660, 72, 580, 300))]),
        "ex2_truth", 14, "Ex2 authors' code (transfer 80 µL with side_shift) + their run, teal at recovery (t=487 s) + materials and impact")

    # ── Example 3: RNA extraction reagent order (R5, Sonnet 5.5) ──
    print("example 3")
    p3 = pdf_panel(pdf, 3, [("Dispense in a Deep well plate 40μL of magnetic beads", 1), "250μL of Isopropanol and 250μL of sample per well."], (580, 488), tmp)

    def ex3_left(img, d):
        img.paste(p3, (40, 72))
        d.rectangle([39, 71, 620, 560], outline=LINE)
        label(d, (48, 520), "ORIGINAL TEXT · PLOS ONE 2021, p.3: OT-2 in-house step 1", MGREY, 13)

    def ex3_right(img, d):
        ir_panel(d, RT, [(21, "Transfer 40 µL magnetic beads to the deep-well plate", None, TEAL),
                         (22, "Transfer 250 µL isopropanol", None, TEAL),
                         (23, "Transfer 250 µL inactivated sample", None, TEAL),
                         (24, "Mix 5x, incubate 5 min", None, None)], "AI BREAKDOWN  ·  paper2protocol IR, exp2 steps 21-24")

    add(lambda o, du: two_col(o, du, "Example 3 / 3  ·  same paper, binding step", "The paper and the breakdown agree: beads, then isopropanol, then sample.", ex3_left, ex3_right),
        "ex3_text", 7, "Ex3 paper p3 step 1 (order highlighted) | AI breakdown steps 21-23 in order (teal)")

    ord_agent = R / "r5-rna-sonnet.mp4"
    clip = panel_clip(ord_agent, 0, 9, 10, VBOX[2:], tmp / "ex3_agent.mp4", rna_names,
                      errors=[(1.0, 9, "ERROR: sample goes in first, before beads and isopropanol")], title="AI run · Sonnet 5.5 (R5)")
    add(lambda o, du: two_col(o, du, "Example 3 / 3  ·  AI code + robot run", "Sonnet 5.5 made this reordering in 4 of 5 binary-judge rounds (R3-R6). R5 shown.",
                              lambda img, d: code_panel(d, L, git_file("8beadb3", "results/claude-sonnet-5-5/opentrons-rna-extraction/protocol.py", tmp), 63, 76,
                                                        [(64, 69, RED, "samples first"), (72, 76, AMBER, "beads + isopropanol after")], "AI CODE  ·  Sonnet 5.5", AMBER),
                              lambda img, d: None, [dict(src=clip, box=VBOX)]),
        "ex3_code", 10, "Ex3 AI code (sample-first loop boxed red) | agent replay, red from the first sample transfer (1.2 s)")

    gt = panel_clip(R / "gt-rna.mp4", 0, 7, 8.5, (580, 330), tmp / "ex3_gt.mp4", rna_names,
                    oks=[(0.7, 7, "1st addition: 40 µL beads")], title="GROUND TRUTH · authors' script")
    ag = panel_clip(ord_agent, 0, 7, 8.5, (580, 330), tmp / "ex3_ag.mp4", rna_names,
                    errors=[(1.0, 7, "1st addition: 250 µL sample")], title="AI · Sonnet 5.5")

    def ex3_truth(img, d):
        strip(d, 440, "The same 48-sample run: about 54 € and 1 h 45 min of robot time.",
              "This changes the order the authors validated against the MagMAX kit, so the paper's reported Ct performance no "
              "longer applies. The protocol would need re-validation before clinical use.")
    add(lambda o, du: two_col(o, du, "Example 3 / 3  ·  ground truth vs AI", "", ex3_truth, lambda i, d: None,
                              [dict(src=gt, box=(40, 80, 580, 330)), dict(src=ag, box=(660, 80, 580, 330))]),
        "ex3_truth", 11, "Ex3 authors' run (beads first, teal) vs agent (sample first, red) + materials and impact")

    print("outro")
    add(results_card, "results", 9, "R7 results: all three models 0.943; cost $1.25 / $0.39 / $3.43; links")

    lst = tmp / "concat.txt"
    lst.write_text("".join(f"file '{p}'\n" for p, *_ in plan))
    ff("-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", "-movflags", "+faststart", str(OUT))
    total = duration(OUT)
    rows, t = [], 0.0
    for _, du, name, desc in plan:
        rows.append(f"| {int(t // 60)}:{t % 60:04.1f} - {int((t + du) // 60)}:{(t + du) % 60:04.1f} | {du:g} s | `{name}` | {desc} |")
        t += du
    md = ("# Trailer time splits\n\n`results/trailer_errors.mp4`, built by `scripts/make_trailer_errors.py`. "
          f"Total {int(total // 60)}:{total % 60:04.1f}.\n\n| Time | Length | Scene | On screen |\n|---|---|---|---|\n" + "\n".join(rows) + "\n")
    (RES / "trailer_errors_timesplits.md").write_text(md)
    print(md)
    print(f"{OUT}  {total:.1f} s  {OUT.stat().st_size / 1e6:.1f} MB  (scratch {tmp})")
    assert total <= 120, "trailer is over 2 minutes"


if __name__ == "__main__":
    main()
