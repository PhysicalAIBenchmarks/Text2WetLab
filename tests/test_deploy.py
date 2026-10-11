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
    assert not [f for f in files if f.startswith(".git") or "/code/" in f or "/pipeline/" in f]


def test_public_task_spec_and_provenance_are_published(tmp_path):
    files = set(staged(tmp_path))
    assert {"README.md", "PROVENANCE.csv", "tasks/split-200ul-two-wells/public/instruction.md",
            "tasks/split-200ul-two-wells/public/ir.json", "tasks/split-200ul-two-wells/task.toml"} <= files
    assert "tasks/opentrons-rna-extraction/public/instruction.md" in files


def test_master_csv_is_published_and_no_pdf_ever_is(tmp_path):
    files = staged(tmp_path)
    assert "sources/master.csv" in files and "sources/sources.json" in files
    assert not [f for f in files if f.lower().endswith(".pdf")]


def test_the_hub_copy_mirrors_the_allowlist():
    # an old layout's grader files and third-party scripts stayed on the Hub because uploads never deleted
    on_hub = {".gitattributes", "README.md", "tasks/harbor/a1-a12-100ul/tests/reference_protocol.py",
              "ref/dna-bot-ysaa010/scripts/1_clip.ot2.py", "tasks/a1-a12-100ul/task.toml"}
    published = {"README.md", "tasks/a1-a12-100ul/task.toml"}
    assert deploy.stale_files(on_hub, published) == ["ref/dna-bot-ysaa010/scripts/1_clip.ot2.py",
                                                     "tasks/harbor/a1-a12-100ul/tests/reference_protocol.py"]


def test_no_grader_or_solution_file_is_staged_for_any_task(tmp_path):
    files = staged(tmp_path)
    hidden = [f for f in files if f.startswith("tasks/") and any(f"/{d}/" in f for d in ("tests", "solution", "environment"))]
    assert not hidden, hidden


def test_the_card_carries_the_latest_results_and_one_licence(tmp_path):
    staged(tmp_path)
    card = (tmp_path / "README.md").read_text()
    assert deploy.RESULTS_MARKER not in card and "| GPT-6.1 Sol |" in card and "tasks all answered" in card
    assert "refusals as 0" not in card and "Refused, not scored" in card
    assert "license: mit" in card and "Apache" not in card
