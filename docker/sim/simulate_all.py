"""Inside the container: simulate every Opentrons protocol in /work/<candidate>/... and write run logs to /out.

usage (entrypoint): simulate_all.py <candidate>[,<candidate>...] | all
Each candidate folder is a cloned repo mounted read-only. For every .py with `def run` and an Opentrons
marker, writes /out/<candidate>/<file-slug>.json (events + labware, or the error), using eval/runlog.py
plus comment events (mylog.py). Custom labware JSON anywhere in the repo is passed to the simulator.
"""
import json, os, re, subprocess, sys

WORK, OUT = "/work", "/out"
MARK = re.compile(r"apiLevel|from opentrons|import opentrons")


def labware_dirs(repo):
    dirs = set()
    for root, _, files in os.walk(repo):
        if ".git" in root:
            continue
        for f in files:
            if f.endswith(".json"):
                try:
                    if '"wellOrdering"' in open(os.path.join(root, f), errors="replace").read(200000):
                        dirs.add(root)
                except OSError:
                    pass
    return sorted(dirs)


def main(sel):
    names = sorted(os.listdir(WORK)) if sel == "all" else sel.split(",")
    for name in names:
        repo = os.path.join(WORK, name)
        lw = labware_dirs(repo)
        lwdir = "/tmp/lw_" + name
        os.makedirs(lwdir, exist_ok=True)
        for d in lw:  # runlog.py takes one labware dir: merge them
            for f in os.listdir(d):
                if f.endswith(".json"):
                    src = os.path.join(d, f)
                    try:
                        open(os.path.join(lwdir, f), "w").write(open(src).read())
                    except OSError:
                        pass
        for root, dirs, files in os.walk(repo):
            dirs[:] = [d for d in dirs if d not in (".git", "node_modules", ".venv", "venv")]
            for f in sorted(files):
                if not f.endswith(".py"):
                    continue
                path = os.path.join(root, f)
                text = open(path, errors="replace").read()
                if "def run" not in text or not MARK.search(text):
                    continue
                rel = os.path.relpath(path, repo)
                slug = re.sub(r"[^A-Za-z0-9]+", "_", rel)[:120]
                os.makedirs(os.path.join(OUT, name), exist_ok=True)
                out = os.path.join(OUT, name, slug + ".json")
                try:
                    p = subprocess.run([sys.executable, "/t2w/mylog.py", path, lwdir, out, "/t2w"],
                                       capture_output=True, text=True, timeout=180, cwd="/tmp")
                    ok = os.path.exists(out) and json.load(open(out)).get("ok")
                except subprocess.TimeoutExpired:
                    json.dump({"ok": False, "error": "timed out after 180 s"}, open(out, "w"))
                    ok = False
                print(f"{name}/{rel}: {'ok' if ok else 'FAIL'}", flush=True)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "all")
