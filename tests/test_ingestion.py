import csv
import importlib.util
import json
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).parent.parent
spec = importlib.util.spec_from_file_location("build_master_csv", ROOT / "scripts/build_master_csv.py")
bm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bm)


def test_every_source_paper_has_at_least_one_row_and_entry_ids_are_unique():
    rows = bm.build_rows()
    sources = json.loads((ROOT / "ingestion/sources.json").read_text())
    assert {s["slug"] for s in sources} <= {r["slug"] for r in rows}
    ids = [r["entry_id"] for r in rows]
    assert len(ids) == len(set(ids))


def test_a_paper_that_splits_gets_one_row_per_experiment():
    rows = bm.build_rows()
    for d in (ROOT / "data/pipeline_runs").glob("*/experiments.json"):
        raw = json.loads(d.read_text())
        n = len(raw if isinstance(raw, list) else raw["experiments"])
        doi = json.loads((d.parent / "paper.json").read_text())["doi"]   # not the folder name: DOIs hold several slashes
        got = [r for r in rows if r["doi"] == doi or doi in r["other_dois"].split(" | ")]
        assert got and len({r["slug"] for r in got}) == 1
        assert sum(r["experiment_source"] == "paper2protocol identify" for r in got) == n, doi


def test_committed_master_csv_is_current():
    """Fails when records or pipeline outputs changed and nobody rebuilt the CSV."""
    fresh = bm.build_rows()
    committed = list(csv.DictReader(open(ROOT / "ingestion/master.csv")))
    assert [{k: str(r.get(k, "")) for k in bm.COLS} for r in fresh] == committed


def test_nothing_machine_specific_or_third_party_is_committed():
    text = (ROOT / "ingestion/master.csv").read_text()
    assert "/Users/" not in text and str(pathlib.Path.home()) not in text
    tracked = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True).stdout.splitlines()
    assert not [f for f in tracked if f.lower().endswith(".pdf")]
    for r in csv.DictReader(open(ROOT / "ingestion/master.csv")):
        assert r["pdf_cache_file"] == "" or r["pdf_cache_file"].startswith("pdf/")


def test_rerunning_ingest_never_loosens_a_licence_or_drops_curated_fields():
    import sys

    sys.path.insert(0, str(ROOT))
    spec2 = importlib.util.spec_from_file_location("ingest", ROOT / "scripts/ingest.py")
    ing = importlib.util.module_from_spec(spec2)
    spec2.loader.exec_module(ing)
    assert ing.stricter("yes", "no") == "no" and ing.stricter("yes", "unknown") == "yes" and ing.stricter("unknown", "yes") == "unknown"
    prev = {"experiments_hint": [{"id": "exp1"}], "note": "curated", "pdf": {"licence": "cc_no", "redistributable": "no"},
            "code": [{"url": "https://github.com/a/b", "host": "github.com", "status": "cloned", "licence": "AGPL-3.0", "redistributable": "no"},
                     {"url": "https://zenodo.org/x", "host": "zenodo.org", "status": "downloaded", "sha": "abc"}]}
    new = {"pdf": {"licence": "cc by", "redistributable": "yes"},
           "code": [{"url": "https://github.com/a/b", "host": "github.com", "status": "cloned", "licence": "MIT", "redistributable": "yes"},
                    {"url": "https://zenodo.org/x", "host": "zenodo.org", "status": "non-github: needs manual download"}]}
    out = ing.merge_prev(new, prev)
    assert out["experiments_hint"] == [{"id": "exp1"}] and out["note"] == "curated"
    assert out["pdf"]["redistributable"] == "no" and out["pdf"]["licence"] == "cc_no"
    assert out["code"][0]["redistributable"] == "no" and out["code"][0]["licence"] == "AGPL-3.0"
    assert out["code"][1]["status"] == "downloaded" and out["code"][1]["sha"] == "abc"
