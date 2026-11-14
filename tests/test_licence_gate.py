"""Licence gate: nothing from an upstream with no declared licence can enter the publish set (#13, #26).

PROVENANCE.csv records each third-party file's licence and sha256, so the gate catches a renamed copy as well as the
original path.
"""
import csv
import hashlib
import importlib.util
import pathlib
import shutil

ROOT = pathlib.Path(__file__).parent.parent
spec = importlib.util.spec_from_file_location("deploy_hf", ROOT / "scripts/deploy_hf.py")
deploy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(deploy)

UNLICENSED = [r for r in csv.DictReader((ROOT / "PROVENANCE.csv").open()) if r["upstream_licence"] == "none"]


def unlicensed_in(staged_dir: pathlib.Path, files: list[str]) -> list[str]:
    """The staged files that are licence-less upstream files, by path or by content."""
    paths = {r["path"] for r in UNLICENSED}
    hashes = {r["sha256"] for r in UNLICENSED if r["sha256"]}
    return [f for f in files
            if f in paths or hashlib.sha256((staged_dir / f).read_bytes()).hexdigest() in hashes]


def test_provenance_lists_licence_less_files():
    assert UNLICENSED, "no licence-less rows in PROVENANCE.csv: the gate below would check nothing"


def test_no_licence_less_file_is_published(tmp_path):
    assert not unlicensed_in(tmp_path, deploy.stage(tmp_path))


def test_gate_catches_a_renamed_copy(tmp_path):
    original = next((ROOT / r["path"] for r in UNLICENSED if r["sha256"] and (ROOT / r["path"]).exists()), None)
    assert original, "no licence-less file with a recorded hash is on disk to copy"
    shutil.copy(original, tmp_path / "renamed.py")
    assert unlicensed_in(tmp_path, ["renamed.py"]) == ["renamed.py"]
