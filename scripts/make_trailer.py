#!/usr/bin/env python3
"""
Build the Text2WetLab trailer video (~3 minutes).

Uses Pillow to render title cards (avoids ffmpeg drawtext dependency)
then ffmpeg to stitch everything together.

Output: results/trailer.mp4

Usage:
    uv run python scripts/make_trailer.py
    python3 scripts/make_trailer.py
"""
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"
OUT = RESULTS / "trailer.mp4"

W, H = 960, 544
FPS = 12

BG  = (7, 8, 13)
AMBER = (245, 158, 11)
WHITE = (255, 255, 255)
TEAL  = (20, 184, 166)
LGREY = (204, 204, 204)
MGREY = (153, 153, 153)
DGREY = (85, 85, 85)

FONT_PATH = "/System/Library/Fonts/HelveticaNeue.ttc"


def font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT_PATH, size)


def probe_duration(path: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(r.stdout.strip())


def ff(*args):
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "warning"] + [str(a) for a in args]
    print("  ffmpeg " + " ".join(str(a) for a in args[:6]) + " ...")
    subprocess.run(cmd, check=True)


def render_card_image(lines: list) -> Image.Image:
    """
    lines: [(text, size, rgb_color, gap_after_px)]
    Returns a PIL Image at (W, H).
    """
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # Measure total height
    total_h = 0
    rendered = []
    for text, size, color, gap in lines:
        if text:
            f = font(size)
            bbox = draw.textbbox((0, 0), text, font=f)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            rendered.append((text, f, tw, th, color, gap))
            total_h += th + gap
        else:
            rendered.append(("", None, 0, 0, color, gap))
            total_h += gap

    y = (H - total_h) // 2
    for text, f, tw, th, color, gap in rendered:
        if text:
            x = (W - tw) // 2
            draw.text((x, y), text, font=f, fill=color)
            y += th + gap
        else:
            y += gap

    return img


def make_card(out: Path, duration: float, lines: list):
    img = render_card_image(lines)
    png = out.with_suffix(".png")
    img.save(str(png))

    n_frames = max(1, int(duration * FPS))
    ff(
        "-loop", "1",
        "-i", str(png),
        "-vf", f"fps={FPS},scale={W}:{H}",
        "-t", str(duration),
        "-pix_fmt", "yuv420p",
        "-an",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        str(out),
    )
    png.unlink()


def make_label_overlay(base: Image.Image, label: str, detail: str) -> Image.Image:
    """Overlay label text onto a copy of `base` image."""
    img = base.copy().convert("RGB")
    draw = ImageDraw.Draw(img)

    if label:
        f = font(20)
        bbox = draw.textbbox((0, 0), label, font=f)
        pw, ph = bbox[2] + 20, bbox[3] + 14
        draw.rectangle([(10, 10), (10 + pw, 10 + ph)], fill=(0, 0, 0, 180))
        draw.text((20, 17), label, font=f, fill=AMBER)

    if detail:
        f = font(17)
        bbox = draw.textbbox((0, 0), detail, font=f)
        pw, ph = bbox[2] + 20, bbox[3] + 12
        draw.rectangle([(10, H - ph - 22), (10 + pw, H - 10)], fill=(0, 0, 0, 180))
        draw.text((20, H - ph - 16), detail, font=f, fill=TEAL)

    return img


def make_task_clip(
    src: Path, out: Path,
    speed: float = 1.0,
    label: str = "",
    detail: str = "",
    max_out_sec: float = None,
):
    src_dur = probe_duration(src)
    out_dur = src_dur / speed
    if max_out_sec:
        out_dur = min(out_dur, max_out_sec)

    if label or detail:
        # Extract one frame, build overlay PNG, burn it in via overlay filter
        frame_png = out.parent / (out.stem + "_label.png")
        frame_img = Image.new("RGB", (W, H), (0, 0, 0))
        overlay = make_label_overlay(frame_img, label, detail)
        overlay.save(str(frame_png))

        # Use a static overlay image composited onto the sped-up video
        ff(
            "-i", str(src),
            "-i", str(frame_png),
            "-filter_complex",
            f"[0:v]setpts=PTS/{speed:.4f},scale={W}:{H}[v];"
            f"[v][1:v]overlay=0:0",
            "-t", str(out_dur),
            "-an",
            "-pix_fmt", "yuv420p",
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            str(out),
        )
        frame_png.unlink()
    else:
        ff(
            "-i", str(src),
            "-vf", f"setpts=PTS/{speed:.4f},scale={W}:{H}",
            "-t", str(out_dur),
            "-an",
            "-pix_fmt", "yuv420p",
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            str(out),
        )


def concat(segs: list, out: Path):
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        for s in segs:
            f.write(f"file '{s.absolute()}'\n")
        flist = f.name
    ff("-f", "concat", "-safe", "0", "-i", flist, "-c", "copy", str(out))
    Path(flist).unlink()


def main():
    tmp = Path(tempfile.mkdtemp(prefix="t2wl_trailer_"))
    print(f"Scratch: {tmp}\n")
    segs = []

    # ── 1. Title (12s) ──────────────────────────────────────────────
    print("[1/10] Title card")
    s = tmp / "01_title.mp4"
    make_card(s, 12.0, [
        ("Text2WetLab", 68, WHITE, 20),
        ("Benchmarking LLM Agents on OT-2 Protocol Generation", 26, LGREY, 40),
        ("N. O'Leary  E. O'Leary  M. Alshehri  L. Sturdy", 19, DGREY, 0),
    ])
    segs.append(s)

    # ── 2. Reproducibility gap (14s) ────────────────────────────────
    print("[2/10] Reproducibility Gap")
    s = tmp / "02_gap.mp4"
    make_card(s, 14.0, [
        ("The Reproducibility Gap", 52, AMBER, 26),
        ("Frontier LLMs write OT-2 Python that passes simulation.", 25, LGREY, 14),
        ("But tacit lab knowledge escapes them --", 21, MGREY, 10),
        ("tip strategy, thermal timing, bead carry-over.", 21, MGREY, 30),
        ("We built a two-layer benchmark to measure that gap.", 23, TEAL, 0),
    ])
    segs.append(s)

    # ── 3. Pipeline (8s) ────────────────────────────────────────────
    print("[3/10] Pipeline")
    s = tmp / "03_pipeline.mp4"
    make_card(s, 8.0, [
        ("Evaluation Pipeline", 44, WHITE, 30),
        ("PDF / DOI   ->   Protocol IR   ->   OT-2 Python", 27, AMBER, 14),
        ("->   opentrons_simulate   ->   Harbor Sandbox", 27, AMBER, 30),
        ("Deterministic gate  +  LLM rubric judge (claude-sonnet-5-5)", 19, DGREY, 0),
    ])
    segs.append(s)

    # ── 4. Oracle run -- plate transfer (real-time ~13s) ─────────────
    print("[4/10] Oracle run -- plate transfer")
    s = tmp / "04_oracle.mp4"
    make_task_clip(
        RESULTS / "a1-a12-100ul" / "oracle_run.mp4", s,
        speed=1.0,
        label="Oracle -- Plate Transfer (A1->A12, 100 uL each)",
        detail="opentrons-mujoco-viz physics render  |  1 protocol step",
    )
    segs.append(s)

    # ── 4b. Bridge (5s) ─────────────────────────────────────────────
    print("[4b] Bridge")
    s = tmp / "04b_bridge.mp4"
    make_card(s, 5.0, [
        ("3 Frontier Models.   7 Tasks.   21 Trials.", 38, WHITE, 22),
        ("100% passed the Opentrons simulator.", 25, TEAL, 12),
        ("Score variance from the rubric judge only.", 21, MGREY, 0),
    ])
    segs.append(s)

    # ── 5. E. coli -- phantom mix (real-time + insight) ──────────────
    print("[5/10] E. coli transformation")
    s = tmp / "05a_ecoli_label.mp4"
    make_card(s, 4.0, [
        ("E. coli Heat-Shock Transformation", 40, WHITE, 16),
        ("4-step protocol from the APEX published method", 21, MGREY, 0),
    ])
    segs.append(s)

    s = tmp / "05b_ecoli_clip.mp4"
    make_task_clip(
        RESULTS / "ecoli-heat-shock-transformation" / "best_run.mp4", s,
        speed=1.0,
        label="Best agent -- Opus 5.5  (reward 0.714)",
        detail="rubric_dna_addition 0.5  |  rubric_fidelity_to_task 0.5",
    )
    segs.append(s)

    s = tmp / "05c_ecoli_insight.mp4"
    make_card(s, 7.0, [
        ("Phantom Mix Hallucination", 38, AMBER, 24),
        ("Opus 5.5 and Fable 5.1 added unrequested mix_after=(3, 10)", 24, LGREY, 12),
        ("to the competent-cells step -- biologically harmful.", 24, LGREY, 28),
        ("Sonnet 5.5 avoided it:  0.857  vs  0.714.", 23, TEAL, 0),
    ])
    segs.append(s)

    # ── 6. Golden Gate -- perfect score (25x speed) ──────────────────
    print("[6/10] Golden Gate Assembly")
    s = tmp / "06a_gg_label.mp4"
    make_card(s, 4.0, [
        ("Golden Gate Assembly", 44, WHITE, 16),
        ("33-step protocol from AssemblyTron  --  the hardest task", 21, MGREY, 0),
    ])
    segs.append(s)

    s = tmp / "06b_gg_clip.mp4"
    make_task_clip(
        RESULTS / "golden-gate-assembly" / "oracle_run.mp4", s,
        speed=25.0, max_out_sec=10.0,
        label="Oracle -- Golden Gate Assembly  (25x speed)",
        detail="33 liquid-handling steps, thermocycler program, DpnI digestion",
    )
    segs.append(s)

    s = tmp / "06c_gg_insight.mp4"
    make_card(s, 4.0, [
        ("All three models scored 1.000", 40, TEAL, 20),
        ("33 steps, thermocycler, cleanup, transformation -- all correct.", 21, LGREY, 0),
    ])
    segs.append(s)

    # ── 7. RNA extraction -- elution error (60x speed) ───────────────
    print("[7/10] RNA Extraction")
    s = tmp / "07a_rna_label.mp4"
    make_card(s, 4.0, [
        ("RNA Extraction", 44, WHITE, 16),
        ("48-sample protocol from HULP SARS-CoV-2 diagnostic pipeline", 21, MGREY, 0),
    ])
    segs.append(s)

    s = tmp / "07b_rna_clip.mp4"
    make_task_clip(
        RESULTS / "opentrons-rna-extraction" / "oracle_run.mp4", s,
        speed=60.0, max_out_sec=10.0,
        label="Oracle -- RNA Extraction, 48 samples  (60x speed)",
        detail="Bead-based magnetic separation  |  9-item rubric",
    )
    segs.append(s)

    s = tmp / "07c_rna_insight.mp4"
    make_card(s, 6.0, [
        ("Elution Volume Error", 38, AMBER, 24),
        ("All models used 100 uL instead of ~80 uL.", 25, LGREY, 12),
        ("Risks RNA pellet carry-over in clinical diagnostics.", 21, MGREY, 26),
        ("rubric_elution_recovery  0.5  for all three models.", 21, TEAL, 0),
    ])
    segs.append(s)

    # ── 8. Colony PCR -- oracle vs agent ────────────────────────────
    print("[8/10] Colony PCR -- oracle vs agent")
    s = tmp / "08a_cpcr_oracle.mp4"
    make_task_clip(
        RESULTS / "colony-pcr-screening" / "oracle_run.mp4", s,
        speed=80.0, max_out_sec=8.0,
        label="Oracle -- Colony PCR Screening  (80x speed)",
        detail="Opus 5.5: 1.000  |  All 8 rubric items: full marks",
    )
    segs.append(s)

    s = tmp / "08b_cpcr_agent.mp4"
    make_task_clip(
        RESULTS / "colony-pcr-screening" / "best_run.mp4", s,
        speed=80.0, max_out_sec=8.0,
        label="Best agent -- Sonnet 5.5 / Fable 5.1  (reward 0.875)",
        detail="rubric_tips_and_contamination 0.5  -- tip reuse across colonies",
    )
    segs.append(s)

    # ── 9. Results (20s) ────────────────────────────────────────────
    print("[9/10] Results")
    s = tmp / "09_results.mp4"
    make_card(s, 20.0, [
        ("Results  --  pass@1  2026-10-04", 34, WHITE, 38),
        ("claude-opus-5-5        0.935", 30, AMBER, 16),
        ("claude-sonnet-5-5      0.910", 30, LGREY, 16),
        ("claude-fable-5-1       0.882", 30, MGREY, 36),
        ("100% simulator pass rate", 20, TEAL, 10),
        ("Score variation from LLM rubric judge only", 20, TEAL, 10),
        ("Sonnet 5.5  =  97.3% of Opus performance at 33% of cost", 20, TEAL, 0),
    ])
    segs.append(s)

    # ── 10. CTA (10s) ───────────────────────────────────────────────
    print("[10/10] CTA")
    s = tmp / "10_cta.mp4"
    make_card(s, 10.0, [
        ("github.com/PhysicalAIBenchmarks/Text2WetLab", 26, AMBER, 16),
        ("physicalaibenchmarks.github.io/Text2WetLab", 23, TEAL, 30),
        ("Apache 2.0   |   Harbor-compatible   |   HuggingFace dataset", 17, DGREY, 0),
    ])
    segs.append(s)

    # ── Concat ──────────────────────────────────────────────────────
    print(f"\nJoining {len(segs)} segments -> {OUT.name}")
    concat(segs, OUT)

    dur = probe_duration(OUT)
    size_mb = OUT.stat().st_size / 1e6
    print(f"\n  Output : {OUT}")
    print(f"  Length : {int(dur // 60)}:{int(dur % 60):02d}  ({dur:.0f}s)")
    print(f"  Size   : {size_mb:.1f} MB")


if __name__ == "__main__":
    main()
