"""End-to-end CLI run against recorded LLM responses (cache-only, offline, free).

If a prompt/schema/model changes, the cache key changes and this fails with a cache miss:
re-record by running the CLI with --cache refresh and copying .cache/llm into the fixture.
"""
import json
import shutil
from pathlib import Path

from paper2protocol import cli, llm

FIX = Path(__file__).parent / "fixtures" / "plos_rna"
DOI = "10.1371/journal.pone.0246302"


def test_list_and_convert_from_cache(tmp_path, monkeypatch, capsys):
    out = tmp_path / "out" / DOI.replace("/", "_") / "pipeline"
    out.mkdir(parents=True)
    shutil.copy(FIX / "paper.json", out / "paper.json")
    monkeypatch.setattr(llm, "CACHE_DIR", FIX / "llm_cache")

    cli.main(["--cache", "only", "--out", str(tmp_path / "out"), "list", DOI])
    listed = capsys.readouterr().out
    assert "2. RNA extraction from clinical" in listed
    assert "Figure 1, Figure 2" in listed

    cli.main(["--cache", "only", "--out", str(tmp_path / "out"), "convert", DOI, "-e", "2"])
    text = (out / "exp2" / "protocol.txt").read_text()
    assert "Steps:" in text and "Transfer" in text and "MANUAL:" in text
    assert (out / "exp2" / "critic.json").exists()
    assert (out / "exp2" / "sufficiency.json").exists()
    assert json.loads((out / "exp2" / "web_access.json").read_text())["flags"] == []


def test_convert_stops_on_reject(tmp_path, monkeypatch):
    from paper2protocol.models import Gap, Sufficiency

    out = tmp_path / "out" / DOI.replace("/", "_") / "pipeline"
    out.mkdir(parents=True)
    shutil.copy(FIX / "paper.json", out / "paper.json")
    monkeypatch.setattr(llm, "CACHE_DIR", FIX / "llm_cache")
    reject = Sufficiency(verdict="reject", summary="x", retrieved_details="", gaps=[
        Gap(detail="antibody", why_needed="y", status="missing", resolution="", source="")])
    monkeypatch.setattr(cli, "resolve", lambda *a, **k: reject)
    monkeypatch.setattr(cli, "extract", lambda *a, **k: (_ for _ in ()).throw(AssertionError("extract ran")))

    try:
        cli.main(["--cache", "only", "--out", str(tmp_path / "out"), "convert", DOI, "-e", "1"])
    except SystemExit as e:
        assert "Rejected" in str(e.code)
    else:
        raise AssertionError("convert did not stop")
    assert (out / "exp1" / "sufficiency.json").exists()
    assert not (out / "exp1" / "protocol.json").exists()
