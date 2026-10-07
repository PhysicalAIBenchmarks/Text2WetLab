import pathlib
import re

ROOT = pathlib.Path(__file__).parent.parent
DOCS = [ROOT / "README.md", *sorted((ROOT / "docs").glob("*.md")), ROOT / "sources/CODE.md", ROOT / "sources/README.md", ROOT / "paper2protocol/README.md",
        *sorted((ROOT / "tasks").glob("*/harbor/README.md"))]  # task READMEs hold the commands people actually run
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
        assert not any(old in text for old in ("tasks/L1", "tasks/L2", "input.nl.txt", "data/pipeline_runs", "references/", "ingestion/")), doc.relative_to(ROOT)


def test_slowpoke_assembler_builds_both_protocols_without_a_gui_or_simulator():
    import importlib.util

    spec = importlib.util.spec_from_file_location("slowpoke_assemble", ROOT / "sources/slowpoke/code/assemble.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    colony, cloning = mod.build("colony_pcr.py"), mod.build("cloning.py")
    assert colony.startswith("pcr_deck_colony_template_maps_dict = ") and "\npcr_recipe_to_make = " in colony and "def run(protocol" in colony
    assert cloning.startswith("dna_plate_map_dict = ") and "\ncombinations_to_make = " in cloning and "def run(protocol" in cloning
