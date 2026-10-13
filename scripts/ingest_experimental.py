"""
Ingest the experimental expansion candidates (research/expansion/merged_candidates.jsonl) with scripts/ingest.py.

    python scripts/ingest_experimental.py [--registry-only] [--only ID ...] [--force]

Experimental sources live apart from the curated corpus so its counts and scripts are unchanged:
sources/experimental/sources.json is their registry and sources/experimental/<id>/record.json their records
(scripts that glob sources/*/record.json or read sources/sources.json do not see them). Each record is tagged
"experimental": true with the search that found it and its readiness, structure level and simulator status.
PDFs and clones go to the same cache outside the repo as ingest.py ($INGEST_CACHE). Never spends API credit.
Resumable: a candidate with a record is skipped unless --force, so it can be re-run after a dropped connection.
"""
import argparse
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
EXP = ROOT / "research/expansion"
DEST = ROOT / "sources/experimental"
# Code links the searches got wrong, resolved by hand (2026-10-13): an organisation link or a renamed repository.
CODE_FIXES = {
    "archemist": "https://github.com/cooper-group-uol-robotics/archemist",
    "takahashi-turbidostat": "https://github.com/Flexostat/Flexostat-interface",
    "synthetic-cells-robotics": "https://github.com/IdoGalil/syn-cells-classification",
}
FETCHED = ("cloned", "downloaded", "not code", "no public code")


def candidates():
    rows = [json.loads(l) for l in (EXP / "merged_candidates.jsonl").read_text().splitlines() if l.strip()]
    ver = {}
    if (EXP / "verification.jsonl").exists():
        ver = {r["id"]: r for r in (json.loads(l) for l in (EXP / "verification.jsonl").read_text().splitlines() if l.strip())}
    out = []
    for r in rows:
        if r.get("duplicate_of_existing"):
            continue
        doi = (r.get("doi") or "").strip().removeprefix("https://doi.org/").removeprefix("doi:") or None
        if not doi and not r.get("code_url"):
            continue
        out.append({
            "slug": r["id"], "dois": [doi] if doi else [], "title": r.get("title") or "", "paper_url": r.get("paper_url"),
            "known_code": [CODE_FIXES.get(r["id"]) or r["code_url"]] if r.get("code_url") else [], "found_by": r.get("found_by", []),
            "readiness": r.get("readiness"), "robot_platform": r.get("robot_platform") or r.get("task_type"),
            "code_licence": r.get("code_license"), "simulator": (ver.get(r["id"]) or {}).get("status", "not run"),
            "origin": ["expansion search 2026-10-12 (experimental)"],
        })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry-only", action="store_true")
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--refetch-code", action="store_true",
                    help="re-run only candidates whose code was not fetched, keeping their PDF (no PDF re-download)")
    a = ap.parse_args()
    cands = candidates()
    DEST.mkdir(parents=True, exist_ok=True)
    (DEST / "sources.json").write_text(json.dumps(cands, indent=1, ensure_ascii=False) + "\n")
    print(f"registry: {len(cands)} experimental sources -> {DEST.relative_to(ROOT)}/sources.json")
    if a.registry_only:
        return
    for c in cands:
        if a.only and c["slug"] not in a.only:
            continue
        rec_path = DEST / c["slug"] / "record.json"
        if a.refetch_code:
            if not rec_path.exists():
                continue
            old = json.loads(rec_path.read_text())
            if all(str(x.get("status", "")).startswith(FETCHED) for x in old.get("code", [])) and c["slug"] not in CODE_FIXES:
                continue
            old["code"] = [x for x in old.get("code", []) if str(x.get("status", "")).startswith(FETCHED)]
            rec_path.write_text(json.dumps(old, indent=1, ensure_ascii=False, sort_keys=True) + "\n")
        elif rec_path.exists() and not a.force:
            continue
        cmd = [sys.executable, str(ROOT / "scripts/ingest.py"), f"experimental/{c['slug']}", "--title", c["title"]]
        for d in c["dois"]:
            cmd += ["--doi", d]
        for u in c["known_code"]:
            cmd += ["--code-url", u]
        if not c["dois"] or a.refetch_code:
            cmd += ["--no-pdf"]
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
            print((p.stdout.strip().splitlines() or [p.stderr.strip()[-300:]])[-1], flush=True)
        except subprocess.TimeoutExpired:
            print(f"experimental/{c['slug']}: timed out (re-run to resume)", flush=True)
            continue
        if rec_path.exists():
            rec = json.loads(rec_path.read_text())
            rec.update({"experimental": True, "origin": c["origin"], "found_by": c["found_by"], "readiness": c["readiness"],
                        "robot_platform": c["robot_platform"], "simulator": c["simulator"]})
            rec_path.write_text(json.dumps(rec, indent=1, ensure_ascii=False, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
