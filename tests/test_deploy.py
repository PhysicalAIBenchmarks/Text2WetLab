import importlib.util
import pathlib

ROOT = pathlib.Path(__file__).parent.parent
spec = importlib.util.spec_from_file_location("deploy_hf", ROOT / "scripts/deploy_hf.py")
deploy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(deploy)


def staged(tmp_path):
    return deploy.stage(tmp_path)


def test_hidden_grader_and_oracle_files_are_never_published(tmp_path):
    files = staged(tmp_path)
    bad = [f for f in files if f.startswith("tasks/") and ("/private/" in f or "/harbor/" in f)]
    assert not bad, bad


def test_third_party_reference_scripts_are_never_published(tmp_path):
    files = staged(tmp_path)
    assert not [f for f in files if f.startswith(("references/", "data/", ".git"))]


def test_public_task_spec_and_provenance_are_published(tmp_path):
    files = set(staged(tmp_path))
    assert {"README.md", "PROVENANCE.csv", "tasks/split-200ul-two-wells/public/instruction.md",
            "tasks/split-200ul-two-wells/public/ir.json", "tasks/split-200ul-two-wells/task.toml"} <= files
    assert "tasks/opentrons-rna-extraction/public/instruction.md" in files


def test_master_csv_is_published_and_no_pdf_ever_is(tmp_path):
    files = staged(tmp_path)
    assert "ingestion/master.csv" in files and "ingestion/sources.json" in files
    assert not [f for f in files if f.lower().endswith(".pdf")]
