"""
Write PROVENANCE.csv: one row per task, reference file, pipeline output and code file.

    python scripts/make_provenance_csv.py [--extra-out DIR]

"Discovered by" = the author of the first commit, on any branch, that added the path (git
history cannot say how something was found; `candidate_source` is filled only when the DOI is
listed in ref/candidates.json). GitHub logins come from the commits API. Reference files are
checked byte-for-byte (git blob hash) against the upstream repo at the commit their README
pins. `--extra-out` points at another checkout's untracked out/ so task IRs can be matched to
pipeline output that is not committed yet.
"""

import argparse
import csv
import hashlib
import json
import pathlib
import re
import subprocess
from urllib.parse import quote

ROOT = pathlib.Path(__file__).resolve().parent.parent
REPO = "PhysicalAIBenchmarks/Text2WetLab"
GH = f"https://github.com/{REPO}"
DEVIN = "origin/devin/1791063775-opentrons-rna-extraction-only"
# current path (file or folder prefix) -> where git first saw it. Keeps the original discoverer after a move.
MOVED = {
    "tasks/L2/opentrons-rna-extraction": "tasks/opentrons-rna-extraction",
    "ref/hulp-rna-extraction/viral_rna_extraction_protocol.py": "out/10.1371_journal.pone.0246302/viral_rna_extraction_protocol.py",
    "tasks/L1/serial-dilution-200ul/solution/protocol.py": "ref/L1-serial-dilution-200ul-2x100ul/protocol_correct.py",
    "tasks/L1/serial-dilution-200ul/tests/run_tests.py": "ref/L1-serial-dilution-200ul-2x100ul/run_tests.py",
    "manuscript": "paper",
}


def origin_path(path):
    for new, old in MOVED.items():
        if path == new or path.startswith(new + "/"):
            return old + path[len(new):]
    return path

ap = argparse.ArgumentParser()
ap.add_argument("--extra-out", default=None)
ap.add_argument("--out", default=None, help="output CSV (default: PROVENANCE.csv in the repo root)")
args = ap.parse_args()


def run(*cmd, cwd=ROOT):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True).stdout.strip()


def git(*a):
    return run("git", *a)


_intro = {}


def introduced(path):
    """(commit, git author, iso date, co-authors) of the earliest commit adding `path` on any branch."""
    if path in _intro:
        return _intro[path]
    best = None
    for p in dict.fromkeys([path, origin_path(path)]):
        for line in git("log", "--all", "--diff-filter=A", "--format=%H|%an|%cI", "--", p).splitlines():
            h, an, d = line.split("|", 2)
            if best is None or d < best[2]:
                best = (h, an, d)
    if best is None:
        _intro[path] = ("", "", "", "")
        return _intro[path]
    co = git("log", "-1", "--format=%(trailers:key=Co-Authored-By,valueonly,separator=; )", best[0]).replace("\n", "")
    _intro[path] = (best[0], best[1], best[2][:10], co)
    return _intro[path]


_login, _branches = {}, {}


def login(sha):
    if sha not in _login:
        out = run("gh", "api", f"repos/{REPO}/commits/{sha}", "--jq", ".author.login // empty")
        _login[sha] = "" if out.startswith("{") else out  # an API error body means the commit is not on GitHub yet
    return _login[sha]


def branches(sha):
    if sha not in _branches:
        names = [b.strip().replace("origin/", "") for b in git("branch", "-r", "--contains", sha).splitlines()
                 if "HEAD" not in b]
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


COLS = ["record_id", "record_type", "layer", "path", "name", "paper_doi", "paper_url", "experiment",
        "ir_source", "candidate_source", "discovered_by_git_author", "discovered_by_github_login",
        "previous_path", "co_authors", "introduced_commit", "introduced_date", "branches_with_commit", "github_url", "loc",
        "sha256", "upstream_repo", "upstream_commit", "upstream_path", "upstream_url", "upstream_licence",
        "verified_vs_upstream", "notes"]
rows = []


def add(**kw):
    r = {c: "" for c in COLS}
    r.update(kw)
    path = r["path"]
    r["previous_path"] = origin_path(path) if origin_path(path) != path else ""
    c, an, d, co = introduced(path)
    if c:
        r.update(introduced_commit=c[:7], introduced_date=d, discovered_by_git_author=an,
                 discovered_by_github_login=login(c) or "(no GitHub account matched)", co_authors=co,
                 branches_with_commit=branches(c),
                 github_url=f"{GH}/blob/{c[:7]}/{quote(origin_path(path))}" if (ROOT / path).is_file() else
                 f"{GH}/tree/{c[:7]}/{quote(origin_path(path))}")
    else:
        r["notes"] = (r["notes"] + " NOT IN GIT HISTORY (untracked)").strip()
    if r["paper_doi"]:
        r["paper_url"] = f"https://doi.org/{r['paper_doi']}"
    if (ROOT / path).is_file():
        r["loc"], r["sha256"] = loc(ROOT / path), sha256(ROOT / path)
    rows.append(r)


candidates = {}
cj = ROOT / "ref/candidates.json"
for src in (cj, pathlib.Path.home() / "Desktop/Text2WetLab/ref/candidates.json"):
    if src.exists():
        for c in json.loads(src.read_text()):
            candidates[(c.get("doi") or "").lower()] = "Amass BiomedCore sweep 2026-10-03 (ref/candidates.json)"
        break

# ---- pipeline outputs ------------------------------------------------------------------
pipeline = {}
out_roots = [ROOT / "out"] + ([pathlib.Path(args.extra_out)] if args.extra_out else [])
for root in out_roots:
    for p in sorted(root.glob("*/exp*/protocol.json")):
        paper = json.loads((p.parent.parent / "paper.json").read_text())
        pipeline[sha256(p)] = (paper["doi"], p.parent.name, root != ROOT / "out")
for p in sorted((ROOT / "out").glob("*/exp*/protocol.json")):
    d = p.parent
    paper = json.loads((d.parent / "paper.json").read_text())
    crit = json.loads((d / "critic.json").read_text()).get("verdict", "") if (d / "critic.json").exists() else ""
    suff = json.loads((d / "sufficiency.json").read_text()).get("verdict", "") if (d / "sufficiency.json").exists() else ""
    n = len(json.loads(p.read_text())["steps"])
    add(record_id=f"out:{paper['doi']}#{d.name}", record_type="pipeline_output", path=str(p.relative_to(ROOT)),
        name=paper["title"][:90], paper_doi=paper["doi"], experiment=d.name, ir_source="paper2protocol (LLM)",
        candidate_source=candidates.get(paper["doi"].lower(), ""), notes=f"{n} steps; critic={crit}; sufficiency={suff}")

# ---- tasks -----------------------------------------------------------------------------
for d in sorted(list((ROOT / "tasks").glob("L*/*"))):
    rel = str(d.relative_to(ROOT))
    layer = d.parent.name
    ir = d / "ir.json"
    doi, exp, src, notes = "", "", "handwritten", ""
    if ir.exists():
        steps = len(json.loads(ir.read_text())["steps"])
        notes = f"{steps} steps"
        if sha256(ir) in pipeline:
            doi, exp, untracked = pipeline[sha256(ir)]
            src = f"paper2protocol (byte-identical to out/{doi.replace('/', '_')}/{exp}/protocol.json)"
            notes += "; source protocol.json " + ("untracked in another checkout" if untracked else "tracked")
    else:
        src, doi = "Harbor task (not paper2protocol IR)", "10.1371/journal.pone.0246302"
        notes = "hidden grader tests/ + solution/ inside the task folder"
    add(record_id=f"task:{rel[6:]}", record_type="task", layer=layer, path=rel, name=d.name, paper_doi=doi,
        experiment=exp, ir_source=src, candidate_source=candidates.get(doi.lower(), ""), notes=notes)

harbor = "tasks/L2/opentrons-rna-extraction"
hulp = "viral_rna_extraction_protocol.py"
hulp_local = ROOT / "ref/hulp-rna-extraction" / hulp

# ---- references ------------------------------------------------------------------------
SETS = {"ref/dna-bot-ysaa010": ("BASIC-DNA-ASSEMBLY/DNA-BOT", "ae9aebbd5833752cad981ecf99a52a6c6e7202e2", "10.1093/synbio/ysaa010"),
        "ref/botany-kiag066": ("cvoiniciuc/BOTany", "c7588d321a59b0d9078c288504e63598b0f60b5e", "10.1093/plphys/kiag066"),
        "ref/transporter-screening-antibiotics11081129": ("ljm176/TransporterScreening", "455fc2e569ad4a873ab415186a29e3e396e8cc4e", "10.3390/antibiotics11081129")}
for base, (repo, commit, doi) in SETS.items():
    up = tree(repo, commit)
    for p in sorted((ROOT / base).rglob("*")):
        if not p.is_file() or p.parent.name in ("",) or p.name in ("README.md", "COMPARISON.md", "REPO_README.md") and p.parent == ROOT / base:
            continue
        rel = str(p.relative_to(ROOT))
        blob = git("hash-object", rel)
        hit = up.get(blob)
        add(record_id=f"ref:{rel}", record_type="reference", path=rel, name=p.name, paper_doi=doi, ir_source="author script",
            candidate_source=candidates.get(doi.lower(), ""), upstream_repo=repo, upstream_commit=commit[:7],
            upstream_path=hit or "", upstream_url=f"https://github.com/{repo}/blob/{commit[:7]}/{quote(hit)}" if hit else "",
            upstream_licence=licence(repo), verified_vs_upstream="byte-identical" if hit else "NO MATCH")

if hulp_local.exists():
    blob = git("hash-object", str(hulp_local.relative_to(ROOT)))
    repo, found = "HULPopentrons/RNA_extraction_OT2opentrons", None
    for c in json.loads(run("gh", "api", f"repos/{repo}/commits?per_page=30") or "[]"):
        t = tree(repo, c["sha"])
        if blob in t:
            found = (c["sha"], t[blob])
            break
    rel = str(hulp_local.relative_to(ROOT))
    add(record_id=f"ref:{rel}", record_type="reference", path=rel, name=hulp, paper_doi="10.1371/journal.pone.0246302",
        ir_source="author script", candidate_source=candidates.get("10.1371/journal.pone.0246302", ""), upstream_repo=repo,
        upstream_commit=found[0][:7] if found else "", upstream_path=found[1] if found else "",
        upstream_url=f"https://github.com/{repo}/blob/{found[0][:7]}/{found[1]}" if found else "",
        upstream_licence=licence(repo), verified_vs_upstream="byte-identical" if found else "NO MATCH",
        notes="originally committed under out/ (generated outputs); upstream commit now pinned in ref/hulp-rna-extraction/README.md")
    for f in ("solution/protocol.py", "tests/reference_protocol.py"):
        p = ROOT / harbor / f
        if p.exists():
            same = p.read_bytes().replace(b"\r\n", b"\n") == hulp_local.read_bytes().replace(b"\r\n", b"\n")
            add(record_id=f"harbor:{f}", record_type="task_file", layer="L2", path=f"{harbor}/{f}", name=f,
                paper_doi="10.1371/journal.pone.0246302", ir_source="author script (re-saved)",
                upstream_repo=repo, upstream_commit=found[0][:7] if found else "", upstream_licence=licence(repo),
                verified_vs_upstream="identical apart from line endings" if same else "differs",
                notes="hidden grader/oracle file")

for f in ("solution/protocol.py", "tests/run_tests.py"):
    p = ROOT / "tasks/L1/serial-dilution-200ul" / f
    if p.exists():
        add(record_id=f"l1:{f}", record_type="task_file", layer="L1", path=str(p.relative_to(ROOT)), name=f,
            ir_source="handwritten (ours)", verified_vs_upstream="n/a", notes="hidden grader/oracle file; no upstream")

# ---- code ------------------------------------------------------------------------------
for pat in ("paper2protocol/*.py", "eval/*.py", "scripts/*.py", "tests/*.py", f"{harbor}/tests/*.py"):
    for p in sorted(ROOT.glob(pat)):
        add(record_id=f"code:{p.relative_to(ROOT)}", record_type="code", path=str(p.relative_to(ROOT)), name=p.name,
            ir_source="handwritten/Claude-assisted", notes="")

OUT_CSV = pathlib.Path(args.out) if args.out else ROOT / "PROVENANCE.csv"
with open(OUT_CSV, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=COLS)
    w.writeheader()
    w.writerows(rows)
print(len(rows), "rows ->", OUT_CSV)
