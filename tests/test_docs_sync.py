"""README.md and manuscript/main.md are the two hand-written documents that report the benchmark. These tests fail when
either drifts from the data or from the other: counts, headline scores, the related-work coverage table, citations,
and a preprint build older than its source."""
import csv
import hashlib
import json
import pathlib
import re
import statistics

ROOT = pathlib.Path(__file__).parent.parent
README = (ROOT / "README.md").read_text()
PAPER = (ROOT / "manuscript/main.md").read_text()
RUN = ROOT / "results/runs/2026-10-07-openrouter"
WORDS = {9: "nine", 11: "11"}


def both(*needles: str) -> None:
    for name, text in (("README.md", README), ("manuscript/main.md", PAPER)):
        missing = [n for n in needles if n not in text]
        assert not missing, f"{name} is missing {missing}"


def test_trap_count_matches_anti_hack():
    traps = set(re.findall(r'hit\("([a-z_]+)"', (ROOT / "tasks/a1-a12-100ul/tests/anti_hack.py").read_text()))
    n = len(traps)
    assert f"{n} traps" in README and f"{n} reward-hacking traps" in README
    assert f"{WORDS.get(n, n)} reward-hacking traps" in PAPER
    for text in (README, PAPER):
        assert not re.search(rf"\b({n + 1}|ten) (reward-hacking )?traps", text, re.I)


def test_task_counts_match_the_task_folders():
    tasks = [d.name for d in (ROOT / "tasks").iterdir() if (d / "task.toml").exists()]
    hard = [t for t in tasks if t.endswith("-hard")]
    assert (len(tasks), len(hard)) == (11, 4), "update both documents, then this test"
    both("11 tasks")
    assert "7 easy and 4 paper-only" in README
    assert "Seven tasks are easy and four are paper-only" in PAPER


def test_attack_count_and_best_attack_match_the_adversarial_results():
    adv = json.loads((ROOT / "results/adversarial.json").read_text())
    attacks = [r for v in adv.values() for k, r in v.items()
               if not k.startswith("control") and "skipped" not in r and not r.get("valid")]
    both(f"{len(attacks)} ", f"{max(r['reward'] for r in attacks):.2f}")
    assert f"{len(attacks)} deliberately broken or cheating" in README and f"{len(attacks)} deliberately broken or cheating" in PAPER


def test_corpus_counts_match_master_csv():
    rows = list(csv.DictReader(open(ROOT / "sources/master.csv")))
    papers, experiments = len({r["slug"] for r in rows}), len(rows)
    assert f"{papers} papers, {experiments} experiments" in README
    assert f"{papers} papers and {experiments} experiments" in PAPER
    assert f"n = {papers})" in README and f"n = {experiments})" in README


def test_headline_scores_match_the_run():
    trials = {}
    for f in RUN.glob("*/*/trial.json"):
        t = json.loads(f.read_text())
        trials.setdefault(f.parent.parent.name, {})[f.parent.name] = t
    answered = {m: {k for k, t in ts.items() if not t.get("exception")} for m, ts in trials.items()}
    common = set.intersection(*answered.values())
    assert len(common) == 8
    for m, ts in trials.items():
        mean = statistics.mean(ts[k]["rewards"]["reward"] for k in common)
        both(f"{mean:.3f}")


def test_coverage_table_is_identical_in_both_documents():
    def table(text: str) -> list[str]:
        start = text.index("<!-- coverage-table:")
        lines = text[start:].splitlines()[1:]
        rows = []
        for line in lines:
            if not line.startswith("|"):
                break
            rows.append(re.sub(r" \[@[^\]]+\]", "", line))
        return rows

    readme, paper = table(README), table(PAPER)
    assert len(readme) >= 3 and readme == paper


def test_every_citation_is_in_refs_bib():
    keys = set(re.findall(r"^@\w+\{([^,]+),", (ROOT / "manuscript/refs.bib").read_text(), re.M))
    cited = set(re.findall(r"@([A-Za-z0-9_]+)", " ".join(re.findall(r"\[@[^\]]+\]", PAPER))))
    assert cited <= keys, cited - keys


def test_no_document_points_at_superseded_artefacts():
    for name, text in (("README.md", README), ("manuscript/main.md", PAPER)):
        for stale in ("docs/harbor-results", "paper/main.tex", "results/paper.html"):
            assert stale not in text, (name, stale)


def test_preprint_outputs_were_built_from_the_current_source():
    src = ROOT / "manuscript"
    digest = hashlib.sha256(b"".join((src / f).read_bytes() for f in ("main.md", "refs.bib", "preprint.css"))).hexdigest()
    assert (src / ".source.sha256").read_text().strip() == digest, "run: bash manuscript/build.sh"
    assert (src / "main.tex").exists() and (ROOT / "docs/preprint/preprint.html").exists()
