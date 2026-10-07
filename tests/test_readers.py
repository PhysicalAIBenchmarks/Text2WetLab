import json
import pathlib

import pytest

from paper2protocol import cli
from paper2protocol.layout import slug_for_doi
from paper2protocol.readers import read_file, text_to_paper

ROOT = pathlib.Path(__file__).parent.parent

ARTICLE = """A tiny automated assay
Abstract
We automate an assay on an OT-2.
1 Introduction
Assays are slow.
2 Materials and methods
2.1 Plate setup
Add 50 µL buffer to each well of a 96-well plate.
Fig. 1 Plate layout. Columns 1-6 hold samples.
3 Results
It worked.
References
1. Someone et al. 2020.
"""


def test_plain_text_is_split_into_sections_with_methods_marked():
    p = text_to_paper(ARTICLE, doi="10.1/x", source="t")
    assert p.title == "A tiny automated assay" and p.abstract.startswith("We automate")
    heads = [s.heading for s in p.sections]
    assert "2.1 Plate setup" in heads and "References" not in heads
    setup = next(s for s in p.sections if s.heading == "2.1 Plate setup")
    assert setup.kind == "methods" and "50 µL buffer" in setup.text and "Plate layout" not in setup.text
    assert [lg.label for lg in p.legends] == ["Figure 1"]
    assert len({s.id for s in p.sections}) == len(p.sections)


def test_markdown_headings_work_too():
    p = text_to_paper("# Title\n\n## Methods\nMix 10 uL.\n", doi="", source="t")
    assert p.sections[0].heading == "Methods" and p.sections[0].kind == "methods"


def test_files_are_dispatched_by_suffix_and_hashed(tmp_path):
    f = tmp_path / "paper.txt"
    f.write_text(ARTICLE)
    p = read_file(f, doi="10.1/x")
    assert p.source.startswith("file:paper.txt sha256:") and p.doi == "10.1/x"
    with pytest.raises(ValueError, match="unsupported input"):
        read_file(tmp_path / "paper.docx", doi="")


def test_a_jats_file_goes_through_the_same_reader(tmp_path):
    f = tmp_path / "a.xml"
    f.write_text("<article><front><article-meta><title-group><article-title>T</article-title></title-group></article-meta></front>"
                 "<body><sec><title>Methods</title><p>Add 5 uL.</p></sec></body></article>")
    p = read_file(f, doi="10.1/x")
    assert p.title == "T" and p.sections[0].text == "Add 5 uL." and p.source.startswith("file:a.xml")


def test_outputs_go_to_the_papers_slug_folder(tmp_path):
    (tmp_path / "sources.json").write_text(json.dumps([{"slug": "hulp", "dois": ["10.1371/journal.pone.0246302"]}]))
    assert slug_for_doi(tmp_path, "10.1371/journal.pone.0246302") == "hulp"
    assert slug_for_doi(tmp_path, "10.9/new.paper") == "10.9_new.paper"      # unknown DOI: filesystem-safe DOI


def test_a_file_input_writes_paper_json_under_its_slug(tmp_path, capsys):
    f = tmp_path / "my paper.txt"
    f.write_text(ARTICLE)
    args = cli.argparse.Namespace(paper=str(f), doi=None, slug=None, out=str(tmp_path / "out"), refetch=False, source=None)
    paper, out = cli.load_paper(args)
    assert out == tmp_path / "out/my_paper.txt".replace(".txt", "") / "pipeline" and (out / "paper.json").exists()
    assert paper.sections


def test_a_failing_input_does_not_stop_the_rest_of_a_batch(tmp_path, monkeypatch, capsys):
    good = tmp_path / "good.txt"
    good.write_text(ARTICLE)
    seen = []
    monkeypatch.setattr(cli, "_list_one", lambda a: (seen.append(a.paper), (_ for _ in ()).throw(RuntimeError("no full text")) if a.paper == "bad.docx" else None)[1])
    args = cli.argparse.Namespace(paper=["bad.docx", str(good)], slug=None)
    with pytest.raises(SystemExit, match="1 of 2 inputs failed"):
        cli.cmd_list(args)
    assert seen == ["bad.docx", str(good)]
