"""
Write PROVENANCE.csv: one row per task, reference file, pipeline output, render and code file.

    python scripts/make_provenance_csv.py [--out FILE]

"Discovered by" = the author of the first commit, on any branch, that added the path (git history
cannot say how something was found; `candidate_source` is filled only when the DOI is listed in
references/candidates.json). GitHub logins come from the commits API. Reference files are checked
byte for byte (git blob hash) against the upstream repo at the commit their README pins.

Paths moved during the refactor, so the lookup tries every former location of a path (RULES) and
takes the earliest commit, which keeps the original discoverer.
"""

import argparse
import csv
import hashlib
import json
import pathlib
import subprocess
from urllib.parse import quote

ROOT = pathlib.Path(__file__).resolve().parent.parent
REPO = "PhysicalAIBenchmarks/Text2WetLab"
GH = f"https://github.com/{REPO}"

# (current path or folder, a former path or folder). Applied repeatedly, so a path moved twice is found.
L2_TASKS = ["ampure-bead-cleanup", "colony-pcr-screening", "ecoli-heat-shock-transformation", "golden-gate-assembly"]
RULES = (
    [("data/pipeline_runs", "out"), ("references", "ref"), ("manuscript", "paper"),
     ("tasks/split-200ul-two-wells", "tasks/serial-dilution-200ul"),
     ("tasks/serial-dilution-200ul", "tasks/L1/serial-dilution-200ul"),
     ("tasks/a1-a12-100ul", "tasks/L1/a1-a12-100ul"),
     ("tasks/opentrons-rna-extraction", "tasks/L2/opentrons-rna-extraction"),
     ("tasks/L2/opentrons-rna-extraction", "tasks/opentrons-rna-extraction"),
     ("references/hulp-rna-extraction/viral_rna_extraction_protocol.py", "out/10.1371_journal.pone.0246302/viral_rna_extraction_protocol.py"),
     ("tasks/serial-dilution-200ul/solution/protocol.py", "ref/L1-serial-dilution-200ul-2x100ul/protocol_correct.py")]
    + [(f"tasks/{t}", f"tasks/L2/{t}") for t in L2_TASKS]
)


def history_paths(path):
    """Every path `path` was ever known by, current first."""
    seen, todo = [path], [path]
    while todo:
        p = todo.pop()
        alts = [old + p[len(new):] for new, old in RULES if p == new or p.startswith(new + "/")]
        if p.endswith("/instruction.md"):
            alts.append(p[: -len("instruction.md")] + "input.nl.txt")
        for a in alts:
            if a not in seen:
                seen.append(a)
                todo.append(a)
    return seen


ap = argparse.ArgumentParser()
ap.add_argument("--out", default=None, help="output CSV (default: PROVENANCE.csv in the repo root)")
args = ap.parse_args()


def run(*cmd, cwd=ROOT):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True).stdout.strip()


def git(*a):
    return run("git", *a)


_intro = {}


def introduced(path):
    """(commit, author, iso date, co-authors, path at that commit) of the earliest commit adding `path`."""
    if path in _intro:
        return _intro[path]
    best = None
    for p in history_paths(path):
        # --full-history: after a rename inside a merge, default simplification prunes the side that added the old path
        for line in git("log", "--all", "--full-history", "--diff-filter=A", "--format=%H|%an|%cI", "--", p).splitlines():
            h, an, d = line.split("|", 2)
            if best is None or d < best[2]:
                best = (h, an, d, p)
    if best is None:
        _intro[path] = ("", "", "", "", "")
        return _intro[path]
    co = git("log", "-1", "--format=%(trailers:key=Co-Authored-By,valueonly,separator=; )", best[0]).replace("\n", "")
    _intro[path] = (best[0], best[1], best[2][:10], co, best[3])
    return _intro[path]


_login, _branches = {}, {}


def login(sha):
    if sha not in _login:
        out = run("gh", "api", f"repos/{REPO}/commits/{sha}", "--jq", ".author.login // empty")
        _login[sha] = "" if out.startswith("{") else out  # an API error body means the commit is not on GitHub yet
    return _login[sha]


def branches(sha):
    if sha not in _branches:
        names = [b.strip().replace("origin/", "") for b in git("branch", "-r", "--contains", sha).splitlines() if "HEAD" not in b]
        _branches[sha] = ", ".join(sorted(set(names)))
    return _branches[sha]


def sha256(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def loc(p):
    t = p.read_bytes()
    return t.count(b"\n") + (1 if t and not t.endswith(b"\n") else 0)


_trees, _lic = {}, {}


def tree(repo, commit):
    if (repo, commit) not in _trees:
        r = subprocess.run(["gh", "api", f"repos/{repo}/git/trees/{commit}?recursive=1"], capture_output=True, text=True)
        _trees[(repo, commit)] = {t["sha"]: t["path"] for t in json.loads(r.stdout)["tree"] if t["type"] == "blob"} if r.returncode == 0 else {}
    return _trees[(repo, commit)]


def licence(repo):
    if repo not in _lic:
        out = run("gh", "api", f"repos/{repo}/license", "--jq", ".license.spdx_id")
        _lic[repo] = out if out and not out.startswith("{") else "none"
    return _lic[repo]


COLS = ["record_id", "record_type", "path", "previous_path", "name", "paper_doi", "paper_url", "experiment",
        "ir_source", "candidate_source", "discovered_by_git_author", "discovered_by_github_login", "co_authors",
        "introduced_commit", "introduced_date", "branches_with_commit", "github_url", "loc", "sha256",
        "upstream_repo", "upstream_commit", "upstream_path", "upstream_url", "upstream_licence",
        "verified_vs_upstream", "notes"]
rows = []


def add(**kw):
    r = {c: "" for c in COLS}
    r.update(kw)
    path = r["path"]
    c, an, d, co, found = introduced(path)
    if c:
        is_file = (ROOT / path).is_file()
        r.update(previous_path=found if found != path else "", introduced_commit=c[:7], introduced_date=d,
                 discovered_by_git_author=an, discovered_by_github_login=login(c) or "(no GitHub account matched)",
                 co_authors=co, branches_with_commit=branches(c),
                 github_url=f"{GH}/{'blob' if is_file else 'tree'}/{c[:7]}/{quote(found)}")
    else:
        r["notes"] = (r["notes"] + " NOT IN GIT HISTORY (untracked)").strip()
    if r["paper_doi"]:
        r["paper_url"] = f"https://doi.org/{r['paper_doi']}"
    if (ROOT / path).is_file():
        r["loc"], r["sha256"] = loc(ROOT / path), sha256(ROOT / path)
    rows.append(r)


candidates = {}
for src in (ROOT / "references/candidates.json", pathlib.Path.home() / "Desktop/Text2WetLab/ref/candidates.json"):
    if src.exists():
        for c in json.loads(src.read_text()):
            candidates[(c.get("doi") or "").lower()] = "Amass BiomedCore sweep 2026-10-03 (candidates.json)"
        break

# ---- pipeline outputs ------------------------------------------------------------------
RUNS = ROOT / "data/pipeline_runs"
pipeline = {}  # sha256 of protocol.json -> (doi, exp)
for p in sorted(RUNS.glob("*/exp*/protocol.json")):
    pipeline[sha256(p)] = (json.loads((p.parent.parent / "paper.json").read_text())["doi"], p.parent.name)
for p in sorted(RUNS.glob("*/exp*/protocol.json")):
    d = p.parent
    paper = json.loads((d.parent / "paper.json").read_text())
    crit = json.loads((d / "critic.json").read_text()).get("verdict", "") if (d / "critic.json").exists() else ""
    suff = json.loads((d / "sufficiency.json").read_text()).get("verdict", "") if (d / "sufficiency.json").exists() else ""
    add(record_id=f"run:{paper['doi']}#{d.name}", record_type="pipeline_output", path=str(p.relative_to(ROOT)),
        name=paper["title"][:90], paper_doi=paper["doi"], experiment=d.name, ir_source="paper2protocol (LLM)",
        candidate_source=candidates.get(paper["doi"].lower(), ""),
        notes=f"{len(json.loads(p.read_text())['steps'])} steps; critic={crit}; sufficiency={suff}")

# ---- tasks -----------------------------------------------------------------------------
HULP = "10.1371/journal.pone.0246302"
for d in sorted(p for p in (ROOT / "tasks").iterdir() if p.is_dir()):
    ir = d / "ir.json"
    doi, exp, src, notes = "", "", "handwritten", ""
    if ir.exists():
        notes = f"{len(json.loads(ir.read_text())['steps'])} steps"
        if sha256(ir) in pipeline:
            doi, exp = pipeline[sha256(ir)]
            src = f"paper2protocol (byte-identical to data/pipeline_runs/{doi.replace('/', '_')}/{exp}/protocol.json)"
    else:
        src, doi = "Harbor task (not a paper2protocol IR)", HULP
        notes = "hidden grader tests/ + solution/ inside the task folder"
    add(record_id=f"task:{d.name}", record_type="task", path=str(d.relative_to(ROOT)), name=d.name, paper_doi=doi,
        experiment=exp, ir_source=src, candidate_source=candidates.get(doi.lower(), ""), notes=notes)

harbor = "tasks/opentrons-rna-extraction"
hulp_local = ROOT / "references/hulp-rna-extraction/viral_rna_extraction_protocol.py"

# ---- references ------------------------------------------------------------------------
SETS = {"references/dna-bot-ysaa010": ("BASIC-DNA-ASSEMBLY/DNA-BOT", "ae9aebbd5833752cad981ecf99a52a6c6e7202e2", "10.1093/synbio/ysaa010"),
        "references/botany-kiag066": ("cvoiniciuc/BOTany", "c7588d321a59b0d9078c288504e63598b0f60b5e", "10.1093/plphys/kiag066"),
        "references/transporter-screening-antibiotics11081129": ("ljm176/TransporterScreening", "455fc2e569ad4a873ab415186a29e3e396e8cc4e", "10.3390/antibiotics11081129"),
        "references/slowpoke": ("Tom-Ellis-Lab/Slowpoke", "62648d2bf390c28af061d68cee71075e27c251a6", "10.1021/acssynbio.5c00629")}
for base, (repo, commit, doi) in SETS.items():
    up = tree(repo, commit)
    for p in sorted(ROOT / f for f in git("ls-files", base).splitlines()):  # tracked files only, never stray caches
        if not p.is_file() or (p.name in ("README.md", "COMPARISON.md", "REPO_README.md", "assemble.py") and p.parent == ROOT / base):
            continue
        rel = str(p.relative_to(ROOT))
        hit = up.get(git("hash-object", rel))
        add(record_id=f"ref:{rel}", record_type="reference", path=rel, name=p.name, paper_doi=doi, ir_source="author script",
            candidate_source=candidates.get(doi.lower(), ""), upstream_repo=repo, upstream_commit=commit[:7],
            upstream_path=hit or "", upstream_url=f"https://github.com/{repo}/blob/{commit[:7]}/{quote(hit)}" if hit else "",
            upstream_licence=licence(repo), verified_vs_upstream="byte-identical" if hit else "NO MATCH")

repo, found = "HULPopentrons/RNA_extraction_OT2opentrons", None
blob = git("hash-object", str(hulp_local.relative_to(ROOT)))
for c in json.loads(run("gh", "api", f"repos/{repo}/commits?per_page=30") or "[]"):
    t = tree(repo, c["sha"])
    if blob in t:
        found = (c["sha"], t[blob])
        break
rel = str(hulp_local.relative_to(ROOT))
add(record_id=f"ref:{rel}", record_type="reference", path=rel, name=hulp_local.name, paper_doi=HULP, ir_source="author script",
    candidate_source=candidates.get(HULP, ""), upstream_repo=repo, upstream_commit=found[0][:7] if found else "",
    upstream_path=found[1] if found else "",
    upstream_url=f"https://github.com/{repo}/blob/{found[0][:7]}/{found[1]}" if found else "",
    upstream_licence=licence(repo), verified_vs_upstream="byte-identical" if found else "NO MATCH",
    notes="originally committed under out/ (generated outputs); upstream commit pinned in references/hulp-rna-extraction/README.md")
for f in ("solution/protocol.py", "tests/reference_protocol.py"):
    p = ROOT / harbor / f
    same = p.read_bytes().replace(b"\r\n", b"\n") == hulp_local.read_bytes().replace(b"\r\n", b"\n")
    add(record_id=f"task_file:{harbor}/{f}", record_type="task_file", path=f"{harbor}/{f}", name=f, paper_doi=HULP,
        ir_source="author script (re-saved)", upstream_repo=repo, upstream_commit=found[0][:7] if found else "",
        upstream_licence=licence(repo), verified_vs_upstream="identical apart from line endings" if same else "differs",
        notes="hidden grader/oracle file")
p = ROOT / "tasks/split-200ul-two-wells/solution/protocol.py"
add(record_id="task_file:tasks/split-200ul-two-wells/solution/protocol.py", record_type="task_file", path=str(p.relative_to(ROOT)),
    name="solution/protocol.py", ir_source="handwritten", verified_vs_upstream="n/a", notes="hidden oracle file; no upstream")


# ---- renders: experiment id + the IR each was drawn from -------------------------------
def render_stem(ir):
    parts = ir.relative_to(ROOT).parts
    return parts[1] if parts[0] == "tasks" else f"paper-{parts[2].replace('.', '_')}-{parts[3]}"


for ir in sorted(ROOT.glob("tasks/*/ir.json")) + sorted(RUNS.glob("*/exp*/protocol.json")):
    stem = render_stem(ir)
    from_paper = ir.name == "protocol.json"
    doi = json.loads((ir.parent.parent / "paper.json").read_text())["doi"] if from_paper else ""
    exp = ir.parent.name if from_paper else ""
    for variant in (stem, f"{stem}-NO-LIFT-collision"):
        mp4 = ROOT / f"assets/examples3d/{variant}.mp4"
        if mp4.exists():
            add(record_id=f"render:{variant}", record_type="render", path=str(mp4.relative_to(ROOT)),
                name=f"doi:{doi}#{exp}" if from_paper else f"task:{ir.parent.name}", paper_doi=doi, experiment=exp,
                ir_source=str(ir.relative_to(ROOT)),
                notes="same IR, drives at work height (collision demo)" if "NO-LIFT" in variant else "")

# ---- code ------------------------------------------------------------------------------
for pat in ("paper2protocol/*.py", "eval/*.py", "scripts/*.py", "tests/*.py", f"{harbor}/tests/*.py"):
    for p in sorted(ROOT.glob(pat)):
        add(record_id=f"code:{p.relative_to(ROOT)}", record_type="code", path=str(p.relative_to(ROOT)), name=p.name)

OUT_CSV = pathlib.Path(args.out) if args.out else ROOT / "PROVENANCE.csv"
with open(OUT_CSV, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=COLS)
    w.writeheader()
    w.writerows(rows)
print(len(rows), "rows ->", OUT_CSV)
