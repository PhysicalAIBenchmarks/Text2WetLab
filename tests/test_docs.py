import pathlib
import re

ROOT = pathlib.Path(__file__).parent.parent
DOCS = [ROOT / "README.md", *sorted((ROOT / "docs").glob("*.md")), ROOT / "references/README.md"]
LINK = re.compile(r"\]\(([^)#\s]+)")


def test_every_relative_link_in_the_docs_resolves():
    broken = []
    for doc in DOCS:
        for target in LINK.findall(doc.read_text()):
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            if not (doc.parent / target).resolve().exists():
                broken.append(f"{doc.relative_to(ROOT)} -> {target}")
    assert not broken, broken


def test_docs_do_not_mention_the_removed_layer_scheme():
    for doc in DOCS:
        text = doc.read_text()
        assert "tasks/L1" not in text and "tasks/L2" not in text and "input.nl.txt" not in text, doc.name
