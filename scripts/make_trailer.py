#!/usr/bin/env python3
"""Build the Text2WetLab submission video (1280x720, 24 fps).

    uv run python scripts/make_trailer.py --cut 2min   # results/trailer.mp4, under 2:00 (challenges 1-2, 3 result figures)
    uv run python scripts/make_trailer.py --cut 3min   # results/trailer_3min.mp4 (all 3 challenges, 5 figures, scenes x1.2)

Scene time splits go to results/<output>_timesplits.md.

Teaser, title, sourced stats, model / hardware / standard, workflow, the reproducibility gap, then each challenge as:
  paper (CC BY PDF page, passages the task uses highlighted) | task instruction / code
  -> historical MuJoCo replay of the Protocol IR
  -> rubric verdict with the judge's own words (round R7, commit 48836f1, read with git show)
then Results (preprint figures from PR #50, commit 817e453, each with its discussion) and a Discussion slide.

Inputs:
  - source PDFs: fetched from sources/<slug>/record.json and checked against its SHA-256
    (only papers whose record says redistributable=yes are used)
  - historical renders: read from the backup/l2-outputs-oct04 branch with `git show`
Needs ffmpeg, pdftoppm and pdftotext (poppler). Text is drawn with Pillow, so ffmpeg needs no drawtext.
"""
import argparse
import hashlib
import html
import json
import re
import subprocess
import tempfile
import textwrap
import urllib.request
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "results"
OUT = RES / "trailer.mp4"
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


N_CHALLENGES = 3
SCALE = 1.0  # every scene's length is multiplied by this (the 2min cut uses 0.8)


def scene(out: Path, dur: float, bg: Image.Image, clips=(), fade=0.35):
    """bg image + clips overlaid. clip = dict(src, box=(x,y,w,h), speed=None|float, ss=0)."""
    dur = round(dur * SCALE, 2)
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


def wrap(d, xy, s, size, width_px, color=LGREY, mono=False, gap=6, highlights=(), bold=False):
    """Word-wrap s into width_px; phrases in `highlights` get a yellow marker behind them."""
    f = F(size, mono, bold)
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
        pt = [norm(t) for t in ph.split()]
        for i in range(len(toks) - len(pt) + 1):
            if toks[i:i + len(pt)] == pt:
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


# ── data: eval round R7 (clean re-run, 21 trials) and the preprint figures, read from git ─────────────────────

R7 = "48836f1"       # results/<model>/<task>/{reward,judge,result}.json for the latest clean run
PREPRINT = "817e453"  # docs/preprint/figures/*.png (PR #50)


def git_bytes(commit, path):
    r = subprocess.run(["git", "-C", str(ROOT), "show", f"{commit}:{path}"], capture_output=True)
    return r.stdout if r.returncode == 0 else None


def git_json(commit, path):
    b = git_bytes(commit, path)
    return json.loads(b) if b and b.strip() else None


def reward(model, task):
    return git_json(R7, f"results/{model}/{task}/reward.json")


def judge_items(model, task):
    j = git_json(R7, f"results/{model}/{task}/judge.json") or git_json(R7, f"results/{model}/{task}/result.json") or {}
    return (j.get("judge") or {}).get("items", [])


def evidence(model, task, item):
    return next(i["evidence"] for i in judge_items(model, task) if i["id"] == item)


# ── icons (drawn, so they scale and stay on-palette) ───────────────────────────────────────────────────────────

def icon_paper(d, cx, cy, s, col):
    w, h, f = s * 0.72, s, s * 0.22
    x0, y0 = cx - w / 2, cy - h / 2
    d.polygon([(x0, y0), (x0 + w - f, y0), (x0 + w, y0 + f), (x0 + w, y0 + h), (x0, y0 + h)], outline=col, width=3)
    d.polygon([(x0 + w - f, y0), (x0 + w - f, y0 + f), (x0 + w, y0 + f)], outline=col, width=3)
    text(d, (cx, y0 + h * 0.3), "PDF", int(s * 0.16), col, bold=True, anchor="mm")
    for k in range(4):
        y = y0 + h * (0.48 + k * 0.12)
        d.line([(x0 + w * 0.16, y), (x0 + w * (0.84 if k < 3 else 0.6), y)], fill=col, width=3)


def icon_list(d, cx, cy, s, col):
    for k in range(3):
        y = cy - s * 0.32 + k * s * 0.32
        text(d, (cx - s * 0.38, y), str(k + 1), int(s * 0.2), col, bold=True, anchor="mm")
        d.line([(cx - s * 0.2, y), (cx + s * 0.42, y)], fill=col, width=4)


def icon_code(d, cx, cy, s, col):
    d.rounded_rectangle([cx - s * 0.5, cy - s * 0.4, cx + s * 0.5, cy + s * 0.4], radius=int(s * 0.1), outline=col, width=3)
    text(d, (cx, cy), "</>", int(s * 0.34), col, mono=True, bold=True, anchor="mm")


def icon_robot(d, cx, cy, s, col):
    # an OT-2 seen from the front: frame, gantry, pipette, deck with a plate
    x0, x1, y0, y1 = cx - s * 0.5, cx + s * 0.5, cy - s * 0.45, cy + s * 0.45
    d.line([(x0, y1), (x0, y0), (x1, y0), (x1, y1)], fill=col, width=4)
    d.line([(x0 - s * 0.08, y1), (x1 + s * 0.08, y1)], fill=col, width=5)
    px = cx + s * 0.12
    d.rectangle([px - s * 0.07, y0, px + s * 0.07, y0 + s * 0.3], outline=col, width=3)
    d.line([(px, y0 + s * 0.3), (px, y0 + s * 0.52)], fill=col, width=3)
    d.rectangle([cx - s * 0.36, y1 - s * 0.16, cx + s * 0.02, y1 - s * 0.02], outline=col, width=3)
    for k in range(4):
        d.ellipse([cx - s * 0.32 + k * s * 0.09 - 3, y1 - s * 0.1 - 3, cx - s * 0.32 + k * s * 0.09 + 3, y1 - s * 0.1 + 3], fill=col)


def icon_check(d, cx, cy, s, col):
    icon_code(d, cx, cy, s, col)
    r = s * 0.2
    bx, by = cx + s * 0.42, cy + s * 0.34
    d.ellipse([bx - r, by - r, bx + r, by + r], fill=col)
    d.line([(bx - r * 0.5, by), (bx - r * 0.1, by + r * 0.4), (bx + r * 0.55, by - r * 0.4)], fill=BG, width=4)


# ── opening ────────────────────────────────────────────────────────────────────────────────────────────────────

def stats_card(out):
    img = canvas()
    d = chrome(img, "Why this matters", "Sources: Baker, Nature 533:452 (2016) · Freedman et al., PLOS Biol 13:e1002165 (2015) · opentrons.com/robots/ot-2 · Boiko et al., Nature 624:570 (2023)")
    text(d, (W // 2, 106), "The next generation of experiments will be run by AI, through code.", 34, WHITE, bold=True, anchor="mm")
    text(d, (W // 2, 152), "At millions of experiments, even a rare mistranslation costs reagents, equipment, patients and progress.", 20, LGREY, anchor="mm")
    tiles = [("70%", AMBER, "of 1,576 researchers have failed to", "reproduce another lab's experiment", "Nature, 2016"),
             ("$28B", AMBER, "a year spent on irreproducible", "preclinical research, US alone", "PLOS Biology, 2015"),
             ("40+", TEAL, "countries where thousands of labs", "automate with the Opentrons OT-2", "Opentrons"),
             ("2023", TEAL, "an LLM agent first wrote and ran", "OT-2 liquid-handling code itself", "Coscientist, Nature 2023")]
    n, gap = len(tiles), 20
    tw = (W - 80 - gap * (n - 1)) // n
    for k, (big, col, l1, l2, src) in enumerate(tiles):
        x = 40 + k * (tw + gap)
        d.rectangle([x, 215, x + tw, 520], fill=PANEL, outline=LINE)
        d.rectangle([x, 215, x + tw, 219], fill=col)
        text(d, (x + tw // 2, 310), big, 72, col, bold=True, anchor="mm")
        text(d, (x + tw // 2, 395), l1, 17, LGREY, anchor="mm")
        text(d, (x + tw // 2, 421), l2, 17, LGREY, anchor="mm")
        text(d, (x + tw // 2, 480), src, 14, DGREY, anchor="mm")
    text(d, (W // 2, 572), "Text2WetLab closes the text-to-lab-code gap for future science,", 23, WHITE, bold=True, anchor="mm")
    text(d, (W // 2, 606), "and adds an evidence layer around past science.", 23, AMBER, bold=True, anchor="mm")
    return scene(out, 9, img)


def standard_card(out):
    img = canvas()
    d = chrome(img, "Text2WetLab  ·  model  ·  hardware  ·  standard", "Corpus and trial counts: docs/preprint (PR #50), computed from the committed results.")
    text(d, (W // 2, 105), "A benchmark for the text-to-lab-code gap", 36, WHITE, bold=True, anchor="mm")
    cols = [("MODEL", AMBER, icon_code, ["Claude Opus 5.5, Sonnet 5.5, Fable 5.1", "as Claude Code agents.", "Any agent plugs in through Harbor."]),
            ("HARDWARE", AMBER, icon_robot, ["Opentrons OT-2 liquid handler,", "in thousands of labs worldwide.", "Every run replayed in MuJoCo."]),
            ("STANDARD", TEAL, icon_check, ["Opentrons Python Protocol API,", "checked by opentrons_simulate.", "Harbor tasks, graders hidden."])]
    gap, cw = 24, (W - 80 - 48) // 3
    for k, (head, col, icon, lines) in enumerate(cols):
        x = 40 + k * (cw + gap)
        d.rectangle([x, 150, x + cw, 420], fill=PANEL, outline=LINE)
        icon(d, x + 70, 218, 70, col)
        text(d, (x + 130, 205), head, 20, col, bold=True)
        y = 290
        for ln in lines:
            text(d, (x + 26, y), ln, 18, LGREY)
            y += 34
    nums = [("36", "papers"), ("123", "experiments"), ("29", "converted to protocols"), ("147", "graded agent trials")]
    nw = (W - 80) // len(nums)
    for k, (v, lbl) in enumerate(nums):
        cx = 40 + k * nw + nw // 2
        text(d, (cx, 488), v, 46, WHITE, bold=True, anchor="mm")
        text(d, (cx, 534), lbl, 17, MGREY, anchor="mm")
    return scene(out, 8, img)


def workflow_card(out):
    img = canvas()
    d = chrome(img, "How it works", "The model never sees the researchers' code. It is the ground truth the run is judged against.")
    steps = [("Paper", "methods in prose", icon_paper, MGREY), ("AI breakdown", "ordered Protocol IR", icon_list, AMBER),
             ("AI code", "OT-2 Python", icon_code, AMBER), ("Real world", "simulator + robot", icon_robot, AMBER)]
    n, bw = len(steps), 230
    gap = (W - 80 - n * bw) // (n - 1)
    for k, (h_, sub, icon, col) in enumerate(steps):
        x = 40 + k * (bw + gap)
        d.rectangle([x, 110, x + bw, 340], fill=PANEL, outline=col, width=2)
        icon(d, x + bw // 2, 190, 90, col)
        text(d, (x + bw // 2, 278), h_, 23, WHITE, bold=True, anchor="mm")
        text(d, (x + bw // 2, 310), sub, 16, MGREY, anchor="mm")
        if k < n - 1:
            ax = x + bw + 6
            d.line([(ax, 225), (ax + gap - 14, 225)], fill=DGREY, width=3)
            d.polygon([(ax + gap - 14, 217), (ax + gap - 4, 225), (ax + gap - 14, 233)], fill=DGREY)
    d.rectangle([40, 390, W - 40, 560], fill=PANEL, outline=TEAL, width=2)
    icon_check(d, 130, 475, 90, TEAL)
    text(d, (220, 425), "GROUND TRUTH", 16, TEAL, bold=True)
    text(d, (220, 455), "The researchers' own written and tested code, hidden from the model.", 22, WHITE)
    text(d, (220, 495), "Graded twice: a deterministic gate (simulate + end-state checks), then a task rubric judge.", 17, LGREY)
    text(d, (220, 525), "Each reproduced PDF becomes runnable code with proof: an evidence layer around past science.", 17, LGREY)
    return scene(out, 7, img)


def result_fig(out, png, n, title, bullets, dur, crop=None, total=3):
    """Results scene: figure on a paper card (left) and its discussion (right)."""
    im = Image.open(png).convert("RGB")
    if crop:
        im = im.crop(crop)
    ground = Image.new("RGB", im.size, im.getpixel((5, 5)))
    im = im.crop(ImageChops.difference(im, ground).convert("L").point(lambda v: 255 if v > 12 else 0).getbbox())
    img = canvas()
    d = chrome(img, f"Results  ·  {n} / {total}", "Figures: docs/preprint (PR #50). 3 Claude models x 7 tasks x 5 eval rounds (R3-R7), 105 trials, pass@1 per round.")
    fx0, fy0, fx1, fy1 = 40, 72, 800, 664
    pad = 24
    im.thumbnail((fx1 - fx0 - 2 * pad, fy1 - fy0 - 2 * pad), Image.LANCZOS)
    d.rounded_rectangle([fx0, fy0, fx1, fy1], radius=10, fill=(255, 255, 255))
    img.paste(im, (fx0 + (fx1 - fx0 - im.width) // 2, fy0 + (fy1 - fy0 - im.height) // 2))
    x, w = 830, W - 40 - 830
    y = wrap(d, (x, 84), title, 27, w, WHITE, gap=8, bold=True) + 22
    d.line([(x, y), (x + 60, y)], fill=AMBER, width=3)
    y += 24
    for b in bullets:
        d.ellipse([x, y + 8, x + 8, y + 16], fill=AMBER)
        y = wrap(d, (x + 22, y), b, 18, w - 22, LGREY, gap=6) + 16
    return scene(out, dur, img)


def discussion_card(out, dur):
    img = canvas()
    d = chrome(img, "Discussion")
    text(d, (40, 82), "Frontier models write lab code that runs. Faithfulness is the open problem.", 30, WHITE, bold=True)
    pts = [("Execution is solved.", "No trial failed the simulator, the end-state checks or the reward-hack traps. Every lost point came from the rubric judge."),
           ("Fidelity is not.", "The errors are parameters that live only in the researchers' code (the 80 µL recovery), steps nobody asked for, and reagent order."),
           ("Researchers' code is the right ground truth.", "Grading against the authors' tested script exposes the gap between what a paper says and what the robot must do."),
           ("Limits.", "7 tasks, one attempt per round, an LLM judge. Next: more of the 123 extracted experiments, and runs on real OT-2 hardware.")]
    y = 150
    for head, body in pts:
        text(d, (40, y), head, 21, AMBER, bold=True)
        y = wrap(d, (40, y + 32), body, 19, W - 80, LGREY, gap=6) + 22
    text(d, (40, H - 90), "github.com/PhysicalAIBenchmarks/Text2WetLab", 22, AMBER, mono=True)
    text(d, (40, H - 58), "physicalaibenchmarks.github.io/Text2WetLab", 18, TEAL, mono=True)
    return scene(out, dur, img)


def title_card(out):
    img = canvas()
    d = ImageDraw.Draw(img)
    text(d, (W // 2, 250), "Text2WetLab", 84, WHITE, bold=True, anchor="mm")
    text(d, (W // 2, 330), "From published wet-lab papers to executable OT-2 robot protocols", 26, LGREY, anchor="mm")
    text(d, (W // 2, 372), "A benchmark for LLM agents, with simulation and rubric grading", 20, MGREY, anchor="mm")
    text(d, (W // 2, 470), "Evan O'Leary  ·  Mohammed Alshehri  ·  Laurence Legon", 18, DGREY, anchor="mm")
    return scene(out, 4, img)


def cold_open(out, hist):
    img = canvas()
    d = ImageDraw.Draw(img)
    label(d, (40, H - 92), "Golden Gate Assembly  ·  33 steps  ·  Protocol IR replayed in MuJoCo", AMBER, 20)
    text(d, (50, H - 40), "AssemblyTron (Synthetic Biology 2023), ingested by paper2protocol", 15, MGREY)
    return scene(out, 4, img, [dict(src=hist / "L2-golden-gate-assembly.mp4", box=(0, 0, W, H - 100), ss=6, speed=3)])


def gap_card(out):
    img = canvas()
    d = chrome(img, "The reproducibility gap")
    text(d, (W // 2, 100), "Papers describe protocols in prose. The researchers' code is what actually ran.", 24, WHITE, anchor="mm")
    cols = [("PAPER (prose)", MGREY, '"After 90 sec collect the\nsupernatant and transfer to a\n96-well microtiter plate."', "PLOS ONE 2021, p.4"),
            ("RESEARCHERS' CODE (ground truth)", TEAL, "p300multi.transfer(80, ...\n  .bottom(z=0)\n  .move(Point(x=-2)), ...)", "viral_rna_extraction_protocol.py:373"),
            ("AGENT (read only the paper)", RED, "m300.aspirate(ELUTION_VOL,\n             src.bottom(0.8))\n# ELUTION_VOL = 100", "Opus 5.5, round R7: protocol.py:205")]
    x, cw = 40, (W - 80 - 40) // 3
    for head, col, body, src in cols:
        d.rectangle([x, 150, x + cw, 520], fill=PANEL, outline=LINE)
        d.rectangle([x, 150, x + cw, 154], fill=col)
        text(d, (x + 20, 178), head, 15, col, bold=True)
        mono = "PAPER" not in head
        y = 230
        for ln in body.split("\n"):
            text(d, (x + 20, y), ln, 19 if mono else 21, WHITE, mono=mono)
            y += 34
        text(d, (x + 20, 480), src, 13, DGREY)
        x += cw + 20
    text(d, (W // 2, 575), "The 80 µL recovery volume and the side-shift away from the pellet appear only in the code.", 20, LGREY, anchor="mm")
    text(d, (W // 2, 612), "Text2WetLab treats the researchers' executable protocol as ground truth.", 22, AMBER, anchor="mm")
    return scene(out, 8, img)


def sim_card(out, hist):
    img = canvas()
    d = chrome(img, "Why replay in 3D", "Same one-step transfer, rendered by opentrons-mujoco-viz from the run log")
    cw, chh = 600, 330
    label(d, (40, 90), "With a lift between wells", TEAL)
    label(d, (640, 90), "Without the lift: tip drags through the labware", RED)
    text(d, (W // 2, 560), "A log line can look valid while the motion is physically wrong.", 22, WHITE, anchor="mm")
    text(d, (W // 2, 595), "The replay shows the motion that actually happened, step by step, with telemetry.", 18, MGREY, anchor="mm")
    return scene(out, 7, img, [dict(src=hist / "L1-example.mp4", box=(40, 140, cw, chh), speed=0.6),
                               dict(src=hist / "L1-example-NO-LIFT-collision.mp4", box=(640, 140, cw, chh), speed=0.6)])


def chapter(out, n, name, cite, lic, blurb):
    img = canvas()
    d = ImageDraw.Draw(img)
    text(d, (W // 2, 230), f"CHALLENGE {n} / {N_CHALLENGES}", 20, AMBER, bold=True, anchor="mm")
    text(d, (W // 2, 300), name, 58, WHITE, bold=True, anchor="mm")
    text(d, (W // 2, 370), cite, 20, LGREY, anchor="mm")
    text(d, (W // 2, 405), lic, 15, DGREY, anchor="mm")
    text(d, (W // 2, 480), blurb, 22, TEAL, anchor="mm")
    return scene(out, 3, img)


def side_by_side(out, kicker, paper_img, paper_head, right_head, right_draw, caption):
    img = canvas()
    d = chrome(img, kicker, caption)
    text(d, (40, 72), "SIDE A  ·  " + paper_head, 15, MGREY, bold=True)
    text(d, (680, 72), "SIDE B  ·  " + right_head, 15, MGREY, bold=True)
    img.paste(paper_img, (40, 100))
    d.rectangle([39, 99, 40 + paper_img.width, 100 + paper_img.height], outline=LINE)
    d.rectangle([680, 100, W - 40, 100 + paper_img.height], fill=PANEL, outline=LINE)
    right_draw(d, 700, 120, W - 40 - 720)
    return scene(out, 8, img)


def replay(out, kicker, src, ss, speed, head, sub, caption):
    img = canvas()
    d = chrome(img, kicker, caption)
    label(d, (40, H - 112), head, AMBER, 19)
    text(d, (50, H - 62), sub, 15, LGREY)
    return scene(out, 6, img, [dict(src=src, box=(40, 64, W - 80, H - 190), ss=ss, speed=speed)])


def verdict(out, task, kicker, headline, quote_model, quote_items, takeaway):
    img = canvas()
    d = chrome(img, kicker, f"Round R7 (binary rubric, commit {R7})  ·  scores and quotes: results/<model>/{task}/ reward.json, judge")
    text(d, (40, 80), headline, 30, WHITE, bold=True)
    items = [k[7:] for k in reward(MODELS[0][0], task) if k.startswith("rubric_")]
    y = 140
    MX = 400
    cell = min(72, (W - 80 - MX) // len(items))
    for k, it in enumerate(items):
        d.text((MX + k * cell + cell // 2, y), it.replace("_", "\n")[:28], font=F(10), fill=MGREY, anchor="ma", align="center")
    y += 50
    for m, name in MODELS:
        r = reward(m, task)
        text(d, (40, y + 8), name, 20, WHITE, bold=True)
        bx = 150
        d.rectangle([bx, y + 6, bx + 160, y + 26], fill=PANEL)
        d.rectangle([bx, y + 6, bx + int(160 * r["reward"]), y + 26], fill=TEAL if r["reward"] >= 0.95 else AMBER)
        text(d, (bx + 168, y + 8), f"{r['reward']:.3f}", 16, LGREY, mono=True)
        for k, it in enumerate(items):
            s = r.get("rubric_" + it, 1.0)
            col = TEAL if s == 1 else (AMBER if s == 0.5 else RED)
            d.rectangle([MX + k * cell + 4, y + 2, MX + (k + 1) * cell - 4, y + 30], fill=col if s < 1 else (14, 60, 56))
            if s < 1:
                text(d, (MX + k * cell + cell // 2, y + 16), f"{s:g}", 14, BG, bold=True, anchor="mm")
        y += 44
    y += 16
    for item in quote_items:
        q = evidence(quote_model, task, item)
        d.rectangle([40, y, W - 40, y + 4], fill=AMBER)
        text(d, (40, y + 14), f"{dict(MODELS)[quote_model]}  ·  {item}", 14, AMBER, bold=True)
        y = wrap(d, (40, y + 38), "“" + q + "”", 17, W - 80, LGREY) + 14
    text(d, (40, H - 70), takeaway, 19, TEAL, bold=True)
    return scene(out, 8, img)


def git_media_at(commit, path, dest: Path) -> Path:
    out = dest / Path(path).name
    if not out.exists():
        out.write_bytes(git_bytes(commit, path))
    return out


def git_media(path, dest: Path) -> Path:
    out = dest / Path(path).name
    if not out.exists():
        out.write_bytes(subprocess.run(["git", "-C", str(ROOT), "show", f"{HIST_BRANCH}:{path}"],
                                       capture_output=True, check=True).stdout)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cut", choices=["2min", "3min"], default="2min")
    a = ap.parse_args()
    global SCALE, OUT, N_CHALLENGES
    if a.cut == "2min":
        N_CHALLENGES = 2
    else:
        SCALE, OUT = 1.2, RES / "trailer_3min.mp4"
    tmp = Path(tempfile.mkdtemp(prefix="t2wl_trailer_"))
    hist = tmp / "hist"
    hist.mkdir()
    for p in ["assets/examples3d/L2-golden-gate-assembly.mp4", "assets/examples3d/L2-colony-pcr-screening.mp4",
              "assets/examples3d/L1-example.mp4", "assets/examples3d/L1-example-NO-LIFT-collision.mp4"]:
        git_media(p, hist)
    segs = []
    S = lambda name: tmp / f"{len(segs):02d}_{name}.mp4"  # noqa: E731

    print("intro")
    segs.append(cold_open(S("cold"), hist))
    segs.append(title_card(S("title")))
    segs.append(stats_card(S("stats")))
    segs.append(standard_card(S("standard")))
    segs.append(workflow_card(S("workflow")))
    segs.append(gap_card(S("gap")))
    if a.cut == "3min":
        segs.append(sim_card(S("sim"), hist))

    # ── Challenge 1: Golden Gate (AssemblyTron) ──
    print("challenge 1: golden gate")
    gg, ggm = "golden-gate-assembly", "claude-opus-5-5"
    segs.append(chapter(S("c1"), 1, "Golden Gate Assembly", "Bryant Jr. et al., AssemblyTron, Synthetic Biology 8(1) 2023  ·  doi:10.1093/synbio/ysac032",
                        "CC BY 4.0", "33 steps: gradient PCR, DpnI digest, clean-up, assembly, transformation"))
    pdf = pdf_panel(fetch_pdf("assemblytron"), 6, ["formed a Dpn1 digestion to eliminate residual template DNA",
                                                   "cleaned and concentrated to remove polymerase",
                                                   "a volume proportional to the fragment length for each"], (620, 520), tmp)
    instr = (ROOT / "tasks" / gg / "public/instruction.md").read_text().strip()
    segs.append(side_by_side(S("c1ab"), "Challenge 1  ·  paper vs task", pdf, "AssemblyTron, p.6", "task instruction (paper2protocol output)",
                             lambda d, x, y, w: wrap(d, (x, y), instr, 19, w, LGREY, gap=9,
                                                     highlights=["DpnI digestion to remove residual template", "clean and concentrate the fragments",
                                                                 "volumes proportional to fragment length"]),
                             "Highlighted: the sentences paper2protocol turned into the instruction. The inset shows where the crop sits on the page."))
    segs.append(replay(S("c1ir"), "Challenge 1  ·  Protocol IR to MuJoCo", hist / "L2-golden-gate-assembly.mp4", 0, 4.5,
                       "Protocol IR replay  ·  2D deck state + 3D arm + telemetry",
                       "Each of the 33 IR steps is replayed. Tip height, pipette volume and container fill are logged per frame.",
                       f"Historical render, 3 Oct 2026 ({HIST_BRANCH}: assets/examples3d/L2-golden-gate-assembly.mp4)"))
    segs.append(verdict(S("c1v"), gg, "Challenge 1  ·  verdict", "All three models: 1.000 on the longest protocol",
                        ggm, ["dpni_and_cleanup", "assembly_mix"], "33 steps from a paper, with no deductions from simulator or judge."))

    # ── Challenge 2: RNA extraction (HULP, PLOS ONE) ──
    print("challenge 2: rna extraction")
    rna, rnam = "opentrons-rna-extraction", "claude-opus-5-5"
    segs.append(chapter(S("c2"), 2, "SARS-CoV-2 RNA Extraction", "Lázaro-Perona et al., PLOS ONE 16(2) 2021  ·  doi:10.1371/journal.pone.0246302",
                        "CC BY 4.0  ·  authors' OT-2 script: github.com/HULPopentrons/RNA_extraction_OT2opentrons",
                        "48 samples, magnetic beads, two ethanol washes, elution into a 4 °C plate"))
    pdf = pdf_panel(fetch_pdf("hulp-rna-extraction"), 4, ["Air dry for 4 min", "add 100μL of Elution Buffer",
                                                          "collect the supernatant and transfer to a 96-well microtiter plate"], (620, 520), tmp)

    def rna_right(d, x, y, w):
        y = wrap(d, (x, y), "Task: implement the paper's in-house OT-2 magnetic-bead protocol for 48 samples, using the reagent volumes, "
                            "step order, incubation, magnet and drying times described in the paper.", 17, w, LGREY, gap=7,
                 highlights=["described in the paper"])
        y += 18
        text(d, (x, y), "AUTHORS' CODE  ·  viral_rna_extraction_protocol.py:363-373", 13, TEAL, bold=True)
        y += 26
        for ln in ["# 15.3) 80 ul recover eluted viral RNA", "p300multi.flow_rate.aspirate = 50", "side_shift = -2",
                   "p300multi.transfer(80, ...bottom(z=0)", "    .move(Point(x=side_shift)), ...)"]:
            text(d, (x, y), ln, 14, WHITE, mono=True)
            y += 22
        y += 18
        text(d, (x, y), "AGENT  ·  Opus 5.5  ·  round R7, protocol.py:202-205", 13, RED, bold=True)
        y += 26
        for ln in ["m300.flow_rate.aspirate = 20", "m300.aspirate(ELUTION_VOL, src.bottom(0.8))", "# ELUTION_VOL = 100"]:
            text(d, (x, y), ln, 14, WHITE, mono=True)
            y += 22

    segs.append(side_by_side(S("c2ab"), "Challenge 2  ·  paper vs researchers' code", pdf, "PLOS ONE 2021, p.4 (methods)", "task + code",
                             rna_right, "The paper gives no recovery volume. The authors' code recovers 80 µL with a side-shift away from the pellet."))
    segs.append(replay(S("c2ir"), "Challenge 2  ·  Protocol IR to MuJoCo",
                       ROOT / "assets/examples3d/paper-10_1371_journal_pone_0246302-exp2.mp4", 0, None,
                       "paper2protocol IR for the same paper  ·  91 steps",
                       "Lysis/binding, beads, two 70% ethanol washes, air dry, elution, transfer to the 4 °C plate.",
                       "Render: assets/examples3d/paper-10_1371_journal_pone_0246302-exp2.mp4"))
    segs.append(verdict(S("c2v"), rna, "Challenge 2  ·  verdict", "Every model over-recovered the eluate (90-100 µL); the 80 µL is only in the code.",
                        rnam, ["elution_recovery"], "The reproducibility gap: the parameter is in the researchers' code, not the paper."))

    if a.cut == "3min":  # the 2min cut omits challenge 3 (colony PCR)
        # ── Challenge 3: Colony PCR (Slowpoke) ──
        print("challenge 3: colony pcr")
        cp, cpm = "colony-pcr-screening", "claude-sonnet-5-5"
        segs.append(chapter(S("c3"), 3, "Colony PCR Screening", "Malcı et al., Slowpoke, ACS Synth. Biol. 15, 511-521 (2026)  ·  doi:10.1021/acssynbio.5c00629",
                            "CC BY 4.0  ·  task instruction is hand-written, modelled on this workflow", "96 wells: 18 µL master mix + 1 µL colony + 1 µL primer"))
        pdf = pdf_panel(fetch_pdf("slowpoke"), 4, ["For the colony PCR step, the deck layout includes",
                                                    "mix plate for dispensing the master mix",
                                                    "a tube rack for reagents, a source plate for colonies, and a PCR"], (620, 520), tmp)
        instr = (ROOT / "tasks" / cp / "public/instruction.md").read_text().strip()
        segs.append(side_by_side(S("c3ab"), "Challenge 3  ·  workflow vs task", pdf, "Slowpoke, p.4", "task instruction (hand-written)",
                                 lambda d, x, y, w: wrap(d, (x, y), instr, 21, w, LGREY, gap=10,
                                                         highlights=["master mix", "colony template", "primer mix", "18 µL", "1 µL"]),
                                 "The 1 µL additions are where practice matters: tip choice, dispense height, touch-tip, blow-out."))
        segs.append(replay(S("c3ir"), "Challenge 3  ·  Protocol IR to MuJoCo", hist / "L2-colony-pcr-screening.mp4", 0, 0.9,
                           "Protocol IR replay  ·  master mix, then colony template, then primers",
                           "Telemetry shows the tip height cycling once per well across all 96 wells.",
                           f"Historical render, 3 Oct 2026 ({HIST_BRANCH}: assets/examples3d/L2-colony-pcr-screening.mp4)"))
        segs.append(verdict(S("c3v"), cp, "Challenge 3  ·  verdict", "All three models: 1.000 under the binary rubric",
                            cpm, ["tips_and_contamination"], "96 wells, 1 µL additions, fresh tips per colony: no model loses a point here."))


    print("results")
    fig = lambda name: git_media_at(PREPRINT, f"docs/preprint/figures/{name}.png", tmp)  # noqa: E731
    nres = 3 if a.cut == "2min" else 5
    segs.append(result_fig(S("res_reward"), fig("fig2_headline"), 1, "All three models score within 0.04 of each other",
                           ["Mean reward over rounds R3-R7: Fable 5.1 0.954, Opus 5.5 0.931, Sonnet 5.5 0.920.",
                            "Every trial passed the simulator and every end-state check; all lost points came from the rubric judge."],
                           7, crop=(0, 0, 742, 1016), total=nres))
    segs.append(result_fig(S("res_per_task"), fig("fig3_per_task"), 2, "Five tasks are solved; two separate the models",
                           ["Every model scores 1.0 on 5 of 7 tasks in every round, including the 33-step Golden Gate assembly.",
                            "E. coli heat shock: Sonnet 1.00, Fable 0.84, Opus 0.80.",
                            "RNA extraction: Fable 0.84, Opus 0.72, Sonnet 0.44."], 7, total=nres))
    segs.append(result_fig(S("res_errors"), fig("fig4_errors"), 3, "The errors are fidelity errors, not crashes",
                           ["47% of lost points: recovering 90-100 µL of eluate where the authors' code takes 80 µL (14 of 15 trials).",
                            "16%: Sonnet adds the sample before beads and isopropanol.",
                            "15%: Opus and Fable pipette-mix the competent cells."], 7, total=nres))
    if a.cut == "3min":
        segs.append(result_fig(S("res_grader"), fig("fig5_grader"), 4, "Only the rubric judge catches these errors",
                               ["Of 147 trials (R1-R7), 108 got full marks and 39 lost points.",
                                "All 39 lost them to the LLM judge: none to the reward-hack traps, simulator, end-state checks or cap."], 7, total=nres))
        segs.append(result_fig(S("res_corpus"), fig("fig6_corpus"), 5, "A corpus to grow the benchmark",
                               ["36 papers (2020-2026) yield 123 experiments; 85 are mostly liquid handling.",
                                "29 are already converted to protocols by paper2protocol."], 6, total=nres))
    segs.append(discussion_card(S("discussion"), 8))

    lst = tmp / "concat.txt"
    lst.write_text("".join(f"file '{s}'\n" for s in segs))
    ff("-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", "-movflags", "+faststart", str(OUT))
    d = duration(OUT)
    rows, t = [], 0.0
    for sg in segs:
        du = duration(sg)
        rows.append(f"| {int(t // 60)}:{t % 60:04.1f} - {int((t + du) // 60)}:{(t + du) % 60:04.1f} | {du:.1f} s | `{sg.stem[3:]}` |")
        t += du
    md = (f"# Trailer time splits ({a.cut} cut)\n\n`results/{OUT.name}`, built by `scripts/make_trailer.py --cut {a.cut}`. "
          f"Total {int(d // 60)}:{d % 60:04.1f}.\n\n| Time | Length | Scene |\n|---|---|---|\n" + "\n".join(rows) + "\n")
    (RES / f"{OUT.stem}_timesplits.md").write_text(md)
    print(md)
    print(f"{OUT}  {int(d // 60)}:{int(d % 60):02d}  {OUT.stat().st_size / 1e6:.1f} MB  ({len(segs)} scenes, scratch {tmp})")
    if a.cut == "2min":
        assert d <= 120, "2min cut is over 2 minutes"


if __name__ == "__main__":
    main()
