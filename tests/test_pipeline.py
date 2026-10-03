"""End-to-end CLI run against recorded LLM responses (cache-only, offline, free).

If a prompt/schema/model changes, the cache key changes and this fails with a cache miss:
re-record by running the CLI with --cache refresh and copying .cache/llm into the fixture.
"""
import shutil
from pathlib import Path

from paper2protocol import cli, llm

FIX = Path(__file__).parent / "fixtures" / "kdm2b"
DOI = "10.64898/2026.03.26.714448"


def test_list_and_convert_from_cache(tmp_path, monkeypatch, capsys):
    out = tmp_path / "out" / DOI.replace("/", "_")
    out.mkdir(parents=True)
    shutil.copy(FIX / "paper.json", out / "paper.json")
    monkeypatch.setattr(llm, "CACHE_DIR", FIX / "llm_cache")

    cli.main(["--cache", "only", "--out", str(tmp_path / "out"), "list", DOI])
    listed = capsys.readouterr().out
    assert "1. HRE-luciferase reporter assay" in listed
    assert "[Figure 1B]" in listed

    cli.main(["--cache", "only", "--out", str(tmp_path / "out"), "convert", DOI, "-e", "1"])
    text = (out / "exp1" / "protocol.txt").read_text()
    assert "Steps:" in text and "Transfer" in text and "MANUAL:" in text
    assert (out / "exp1" / "critic.json").exists()
