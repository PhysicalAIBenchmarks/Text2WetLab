#!/usr/bin/env python3
"""Render every robot run scripts/make_trailer_errors.py uses (make_trailer.py needs none: its 3D comes from git).

    uv run python scripts/trailer_renders.py [--out /tmp/t2wl_renders] [--only NAME ...]

Each protocol is read from git (a fixed eval-round commit, or the working tree when commit is None) and rendered
with scripts/render_run.py, which writes <name>.mp4 and <name>.mp4.timeline.json. Needs VIZ_VENV and OT_VENV
as for render_run.py.
"""
import argparse
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RNA_LABWARE = "tasks/opentrons-rna-extraction/environment/data/labware"

# name: (commit or None for the working tree, protocol path, labware dir or None)
RENDERS = {
    # make_trailer_errors.py: R7 = 48836f1 (clean re-run, 21 trials), R5 = 8beadb3 (run-log judge)
    "r7-ecoli-opus": ("48836f1", "results/claude-opus-5-5/ecoli-heat-shock-transformation/protocol.py", None),
    "r7-rna-opus": ("48836f1", "results/claude-opus-5-5/opentrons-rna-extraction/protocol.py", RNA_LABWARE),
    "r5-rna-sonnet": ("8beadb3", "results/claude-sonnet-5-5/opentrons-rna-extraction/protocol.py", RNA_LABWARE),
    "gt-ecoli": (None, "tasks/ecoli-heat-shock-transformation/solution/protocol.py", None),
    "gt-rna": (None, "tasks/opentrons-rna-extraction/solution/protocol.py", RNA_LABWARE),  # the authors' HULP script
}


def protocol_file(commit, path, dest: Path) -> Path:
    if commit is None:
        return ROOT / path
    dest.write_bytes(subprocess.run(["git", "-C", str(ROOT), "show", f"{commit}:{path}"], capture_output=True, check=True).stdout)
    return dest


def render(name, out: Path):
    commit, path, labware = RENDERS[name]
    proto = protocol_file(commit, path, out / f"{name}.py")
    cmd = [sys.executable, str(ROOT / "scripts/render_run.py"), str(proto), str(out / f"{name}.mp4")]
    if labware:
        cmd += ["--labware", str(ROOT / labware)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return name, r.returncode, (r.stdout + r.stderr).strip().splitlines()[-1:] or [""]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=Path("/tmp/t2wl_renders"))
    ap.add_argument("--only", nargs="*", choices=list(RENDERS))
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(4) as pool:
        for name, rc, last in pool.map(lambda n: render(n, a.out), a.only or list(RENDERS)):
            print(f"{'ok ' if rc == 0 else 'ERR'} {name}: {last[0]}")


if __name__ == "__main__":
    main()
