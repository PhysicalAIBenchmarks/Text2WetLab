"""
Build ingestion/master.csv: ONE ROW PER (PAPER, EXPERIMENT).

    python scripts/build_master_csv.py [--out FILE]

A paper that splits into several liquid-handling workflows gets several rows, each with its own pipeline state
and task relation; the PDF and code columns repeat on every row of the paper, so any row is self-contained.

Experiment source, in order of authority:
  1. paper2protocol `identify`   data/pipeline_runs/<doi>/experiments.json   (ids exp1.. = list position + 1)
  2. hand-read split             ingestion/records/<slug>.json -> experiments_hint
  3. none                        one row, experiment_id blank, pipeline_state "not_identified"

Reads only committed files plus the record JSONs; never touches the network or an API.
"""
import argparse
import csv
import json
import pathlib
import tomllib

ROOT = pathlib.Path(__file__).resolve().parent.parent
RUNS = ROOT / "data/pipeline_runs"

# How a paper relates to a benchmark task. "derived" = the task IR is byte-identical to that experiment's IR.
# The task folder is the authority: each tasks/<task>/task.toml lists its [[source]] (slug, experiment, relation).
# An experiment can feed several tasks, so a key maps to a list.
DROPPED = {("copick", "exp2"): [("colony-picking-96well", "dropped (vision-guided, not liquid handling)")]}


def task_links():
    exp, paper = {}, {}
    for f in sorted((ROOT / "tasks").glob("*/task.toml")):
        for s in tomllib.loads(f.read_text()).get("source", []):
            if s.get("experiment"):
                exp.setdefault((s["slug"], s["experiment"]), []).append((f.parent.name, s["relation"]))
            else:
                paper.setdefault(s["slug"], []).append((f.parent.name, s["relation"]))
    for k, v in DROPPED.items():
        exp.setdefault(k, []).extend(v)
    return exp, paper


RUNNABLE = {  # slug -> whether its code simulates on Harbor's stack (Opentrons 7.5.0), from scripts/reproduce.py
    "dna-bot": "no: needs removed Opentrons API v1", "botany": "no: needs API 2.20 and a runtime CSV",
    "transporter-screening": "no: needs a custom labware definition that is not in the repo",
    "hulp-rna-extraction": "yes (1,895 commands)", "slowpoke": "yes, once references/slowpoke/assemble.py binds its CSVs",
}
VENDORED = {"dna-bot": "references/dna-bot-ysaa010", "botany": "references/botany-kiag066",
            "transporter-screening": "references/transporter-screening-antibiotics11081129",
            "hulp-rna-extraction": "references/hulp-rna-extraction", "slowpoke": "references/slowpoke"}

COLS = ["entry_id", "slug", "doi", "other_dois", "title", "journal", "year", "origin",
        "experiment_id", "experiment_title", "experiment_goal", "figure_refs", "liquid_handling", "experiment_source",
        "pipeline_state", "sufficiency_verdict", "critic_verdict", "ir_steps", "ir_check_errors",
        "task_slug", "task_relation",
        "paper_open_access", "paper_licence", "fulltext_source", "fulltext_sections",
        "pdf_status", "pdf_url", "pdf_sha256", "pdf_bytes", "pdf_pages", "pdf_licence", "pdf_redistributable", "pdf_cache_file",
        "code_status", "code_urls", "code_commits", "code_licences", "code_redistributable", "opentrons_py_files", "api_levels",
        "code_runnable_on_harbor_stack", "code_vendored_in_repo", "notes"]


def load(p):
    return json.loads(p.read_text()) if p.exists() else None


def pipeline_experiments(dois):
    for d in dois:
        f = RUNS / d.replace("/", "_") / "experiments.json"
        raw = load(f)
        if raw is not None:
            return d, (raw if isinstance(raw, list) else raw.get("experiments", [])), f.parent
    return None, [], None


def stage_info(run_dir, n):
    d = run_dir / f"exp{n}"
    if not d.is_dir():
        return {"state": "identified", "suff": "", "critic": "", "steps": "", "errs": ""}
    suff, crit = load(d / "sufficiency.json"), load(d / "critic.json")
    proto, chk = load(d / "protocol.json"), load(d / "check.json")
    state = "converted" if proto else ("assessed" if suff else "identified")
    if suff and suff.get("verdict") == "reject" and not proto:
        state = "rejected"
    return {"state": state, "suff": (suff or {}).get("verdict", ""), "critic": (crit or {}).get("verdict", ""),
            "steps": len(proto["steps"]) if proto else "", "errs": sum(i["severity"] == "error" for i in chk) if chk is not None and proto else ""}


def join(items):
    return " | ".join(str(i) for i in items if i not in (None, ""))


def paper_cols(src, rec):
    rec = rec or {}
    pdf, ft = rec.get("pdf", {}), rec.get("fulltext", {})
    code, seen = [], set()
    for c in rec.get("code", []):  # a repo named twice in a paper is one codebase
        key = c.get("repo") or c.get("url")
        if key not in seen:
            seen.add(key)
            code.append(c)
    cloned = [c for c in code if c.get("status") == "cloned" or c.get("status") == "downloaded"]
    return {
        "doi": rec.get("doi_primary") or (src["dois"][0] if src["dois"] else ""),
        "other_dois": join([d for d in src["dois"] if d != (rec.get("doi_primary") or (src["dois"] or [""])[0])]),
        "title": rec.get("title") or src["title"], "journal": rec.get("journal", ""), "year": rec.get("year", ""),
        "origin": join(src["origin"]),
        "paper_open_access": rec.get("open_access", ""), "paper_licence": rec.get("paper_licence", ""),
        "fulltext_source": ft.get("source") or "", "fulltext_sections": ft.get("sections", ""),
        "pdf_status": pdf.get("status", "not_ingested"), "pdf_url": pdf.get("url", ""), "pdf_sha256": pdf.get("sha256", ""),
        "pdf_bytes": pdf.get("bytes", ""), "pdf_pages": pdf.get("pages", ""), "pdf_licence": pdf.get("licence", ""),
        "pdf_redistributable": pdf.get("redistributable", ""),
        "pdf_cache_file": f"pdf/{src['slug']}.pdf" if pdf.get("status") == "downloaded" else "",
        "code_status": (f"{len(cloned)} of {len(code)} obtained: " + join(sorted({c.get('status', '') for c in code}))) if code else "none known",
        "code_urls": join(c.get("url") for c in code), "code_commits": join((c.get("commit") or "")[:10] for c in code),
        "code_licences": join(c.get("licence") for c in code),
        "code_redistributable": ("yes" if code and all(c.get("redistributable") == "yes" for c in code) else ("no" if code else "")),
        "opentrons_py_files": sum(c.get("opentrons_py_files", 0) or 0 for c in code) if code else "",
        "api_levels": join(sorted({a for c in code for a in c.get("api_levels", [])})),
        "code_runnable_on_harbor_stack": RUNNABLE.get(src["slug"], "not tested" if code else ""),
        "code_vendored_in_repo": VENDORED.get(src["slug"], ""),
        "notes": join([src.get("note"), rec.get("note")]),
    }


def build_rows():
    sources = json.loads((ROOT / "ingestion/sources.json").read_text())
    rows = []
    exp_links, paper_links = task_links()
    for src in sources:
        rec = load(ROOT / f"ingestion/records/{src['slug']}.json")
        base = {c: "" for c in COLS}
        base.update(paper_cols(src, rec), slug=src["slug"])
        d, exps, run_dir = pipeline_experiments(src["dois"] + (rec or {}).get("dois", []))
        entries = []
        if exps:
            for i, e in enumerate(exps, 1):
                s = stage_info(run_dir, i)
                entries.append({"experiment_id": f"exp{i}", "experiment_title": e["title"], "experiment_goal": e["goal"],
                                "figure_refs": join(e.get("figure_refs", [])), "liquid_handling": e["liquid_handling"],
                                "experiment_source": "paper2protocol identify", "pipeline_state": s["state"],
                                "sufficiency_verdict": s["suff"], "critic_verdict": s["critic"], "ir_steps": s["steps"], "ir_check_errors": s["errs"]})
        elif (rec or {}).get("experiments_hint"):
            for e in rec["experiments_hint"]:
                entries.append({"experiment_id": e.get("id", ""), "experiment_title": e.get("title", ""), "experiment_goal": e.get("goal", ""),
                                "figure_refs": e.get("evidence", ""), "liquid_handling": e.get("liquid_handling", ""),
                                "experiment_source": "hand-read split (not yet run through identify)", "pipeline_state": "not_identified"})
        else:
            entries.append({"experiment_id": "", "experiment_source": "none: paper not yet split", "pipeline_state": "not_identified"})
        for e in entries:
            row = dict(base, **e)
            links = exp_links.get((src["slug"], e["experiment_id"])) or paper_links.get(src["slug"]) or []
            if links:
                row["task_slug"] = " | ".join(t for t, _ in links)
                row["task_relation"] = " | ".join(r for _, r in links)
            row["entry_id"] = f"{src['slug']}#{e['experiment_id']}" if e["experiment_id"] else src["slug"]
            rows.append(row)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "ingestion/master.csv"))
    a = ap.parse_args()
    rows = build_rows()
    with open(a.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)
    papers = {r["slug"] for r in rows}
    print(f"{len(rows)} rows for {len(papers)} papers -> {a.out}")


if __name__ == "__main__":
    main()
