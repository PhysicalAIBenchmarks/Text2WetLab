"""session_run.py import-job on a synthetic Harbor job: one workspace per trial, judge.md only where a judge is due."""
import json
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
CHECKS = [{"name": "end_state", "pass": True, "expected": 100, "measured": 100}]


def trial(job: pathlib.Path, name: str, task: str, record: dict | None, files: dict[str, str]) -> None:
    d = job / name
    (d / "verifier").mkdir(parents=True)
    (d / "result.json").write_text(json.dumps({"task_name": f"text2wetlab-ul/{task}",
                                               "agent_info": {"model_info": {"name": "anthropic/claude-sonnet-5-5"}}}))
    if record is not None:
        (d / "verifier/result.json").write_text(json.dumps(record))
    for rel, text in files.items():
        (d / "verifier" / rel).write_text(text)


def import_job(job: pathlib.Path, root: pathlib.Path) -> str:
    return subprocess.run([sys.executable, str(ROOT / "ul/session_run.py"), "import-job", str(job), str(root)],
                          check=True, capture_output=True, text=True).stdout


def test_import_job(tmp_path):
    job, root = tmp_path / "job", tmp_path / "runs"
    protocol = (ROOT / "references/vantage/split-200ul-two-wells.py").read_text()
    graded = {"feasible": True, "judge_config": {"skipped": True}, "checks": CHECKS, "rewards": {"reward": 1.0}}
    trial(job, "a", "vantage.split-200ul-two-wells", graded, {"protocol.py": protocol})
    trial(job, "b", "vantage.split-200ul-two-wells", graded, {"protocol.py": protocol})
    trial(job, "c", "evo.split-200ul-two-wells", {"verdict": "correctly declared infeasible", "rewards": {"reward": 1.0}},
          {"INFEASIBLE.md": "MCA96: all 96 tips"})
    trial(job, "d", "vantage.a1-a12-100ul", None, {})                    # verifier crashed
    trial(job, "e", "star-a1-a12-100ul", None, {})                       # old task name: not <device>.<task>
    out = import_job(job, root)

    ws = root / "vantage-split-200ul-two-wells-claude-sonnet-5-5-0"
    meta = json.loads((ws / "meta.json").read_text())
    assert meta | {"trial": None} == {"device": "vantage", "task": "split-200ul-two-wells", "model": "claude-sonnet-5-5",
                                      "k": 0, "agent": "harbor", "trial": None}
    assert (ws / "protocol.py").read_text() == protocol
    assert json.loads((ws / "out/result.json").read_text()) == graded
    assert "Reply with only this JSON object" in (ws / "judge.md").read_text()
    assert (root / "vantage-split-200ul-two-wells-claude-sonnet-5-5-1/judge.md").exists()   # second attempt: k=1

    infeasible = root / "evo-split-200ul-two-wells-claude-sonnet-5-5-0"
    assert (infeasible / "INFEASIBLE.md").exists() and not (infeasible / "judge.md").exists()
    crashed = root / "vantage-a1-a12-100ul-claude-sonnet-5-5-0"
    assert not (crashed / "out/result.json").exists() and "no verifier result" in out
    assert "skipped: task_name" in out and len(list(root.iterdir())) == 4

    again = import_job(job, root)                                        # importing twice adds nothing
    assert again.count("already imported") == 4 and len(list(root.iterdir())) == 4


FAKE_CLAUDE = f'''#!{sys.executable}
"""A stand-in for `claude -p`: answers every rubric item from FAKE_IDS with 1, inside a code fence; FAKE_MODE picks
a way to misbehave instead."""
import json, os, sys
assert sys.argv[1:3] == ["-p", "--model"] and "--tools" in sys.argv, sys.argv
prompt = sys.stdin.read()
assert "Reply with only this JSON object" in prompt
with open(os.environ["FAKE_LOG"], "a") as f:
    f.write(sys.argv[3] + "\\n")                    # the model asked for
ids = os.environ["FAKE_IDS"].split(",")
mode = os.environ.get("FAKE_MODE", "")
def reply(obj): print(json.dumps({{"result": obj if isinstance(obj, str) else json.dumps(obj), "is_error": False}}))
if mode == "prose": reply("I would rather not grade this.")
elif mode == "exit-1": print("rate limited", file=sys.stderr); sys.exit(1)
elif mode == "is-error": print(json.dumps({{"result": "Not logged in", "is_error": True}}))
elif mode == "not-object": print("null")
elif mode == "ids-wrong": reply({{"items": [{{"id": i, "score": 1, "evidence": "x"}} for i in ids[:-1] + ["bogus"]]}})
elif mode == "ids-dup": reply({{"items": [{{"id": i, "score": 1, "evidence": "x"}} for i in ids + ids[:1]]}})
elif mode == "score-2": reply({{"items": [{{"id": i, "score": 2, "evidence": "x"}} for i in ids]}})
elif mode == "score-bool": reply({{"items": [{{"id": i, "score": True, "evidence": "x"}} for i in ids]}})
else:
    items = [{{"id": i, "score": 1, "evidence": "fake"}} for i in ids]
    reply("```json\\n" + json.dumps({{"items": items, "summary": "fake"}}) + "\\n```")
'''


def run(*args, env=None, check=True):
    return subprocess.run([sys.executable, str(ROOT / "ul/session_run.py"), *map(str, args)],
                          check=check, capture_output=True, text=True, env=env)


def test_judge_and_score(tmp_path):
    import session_run
    job, root = tmp_path / "job", tmp_path / "runs"
    protocol = (ROOT / "references/vantage/split-200ul-two-wells.py").read_text()
    graded = {"feasible": True, "judge_config": {"skipped": True}, "checks": CHECKS, "rewards": {"reward": 1.0, "deterministic_reward": 1.0}}
    trial(job, "a", "vantage.split-200ul-two-wells", graded, {"protocol.py": protocol})
    trial(job, "b", "vantage.split-200ul-two-wells", graded, {"protocol.py": protocol})
    trial(job, "c", "evo.split-200ul-two-wells", {"verdict": "correctly declared infeasible", "rewards": {"reward": 1.0}},
          {"INFEASIBLE.md": "MCA96: all 96 tips"})
    trial(job, "d", "bravo.golden-gate-assembly", {"feasible": False, "declared_infeasible": True, "rewards": {"reward": 0.0},
                                                   "error": "declared infeasible without naming the limitation: tube height, ..."},
          {"INFEASIBLE.md": "the head cannot pipette tubes"})
    import_job(job, root)
    ws = root / "vantage-split-200ul-two-wells-claude-sonnet-5-5-0"
    _, ids = session_run.rubric_of(ws)
    fake = tmp_path / "claude"
    fake.write_text(FAKE_CLAUDE)
    fake.chmod(0o755)
    env = dict(os.environ, FAKE_IDS=",".join(ids), FAKE_LOG=str(tmp_path / "calls"))

    out = run("judge", root, "--votes", "2", "--jobs", "2", "--claude", fake, env=env).stdout
    assert "4 vote(s) to collect" in out and out.count(f"{len(ids)}/{len(ids)}") == 4
    for w in ("vantage-split-200ul-two-wells-claude-sonnet-5-5-0", "vantage-split-200ul-two-wells-claude-sonnet-5-5-1"):
        for vote in ("vote.json", "vote2.json"):
            data = json.loads((root / w / vote).read_text())
            assert {i["id"] for i in data["items"]} == set(ids)
            assert data["judge"] == {"model": "claude-sonnet-5-5", "harness": "claude-cli"}   # provenance in the vote
    assert not (root / "evo-split-200ul-two-wells-claude-sonnet-5-5-0/vote.json").exists()   # no judge.md: no judge
    assert not list(root.glob("*/*.tmp"))
    assert json.loads((root / "judge.json").read_text()) == {"harness": "claude-cli", "model": "claude-sonnet-5-5", "votes": 2}

    out = run("score", root).stdout                                     # the vote count comes from judge.json
    assert out.startswith("Judge claude-sonnet-5-5 via claude -p, 2 vote(s) per protocol.")
    rows = json.loads((root / "table.json").read_text())
    assert rows[ws.name]["reward"] == 1.0 and rows[ws.name]["judge"] == {"harness": "claude-cli", "model": "claude-sonnet-5-5", "votes": 2}
    assert rows[ws.name]["agent"] == "harbor"
    wrong = rows["bravo-golden-gate-assembly-claude-sonnet-5-5-0"]              # leaderboard.py's label, not a 40-char cut
    assert (wrong["reward"], wrong["outcome"]) == (0.0, "infeasible_wrong_reason")

    # Every way a reply can be wrong is reported and not saved
    for mode, msg in [("prose", "no JSON object"), ("exit-1", "rate limited"), ("is-error", "Not logged in"),
                      ("not-object", "unexpected claude output"), ("ids-wrong", "rubric ids"), ("ids-dup", "rubric ids"),
                      ("score-2", "a score is not 0 or 1"), ("score-bool", "a score is not 0 or 1")]:
        bad = run("judge", root, "--votes", "3", "--claude", fake, env=env | {"FAKE_MODE": mode}, check=False)
        assert bad.returncode == 1 and bad.stdout.count(f"FAILED: {msg}") == 2, (mode, bad.stdout)
        assert not (ws / "vote3.json").exists() and not list(root.glob("*/*.tmp")), mode
    assert "| pending |" in run("score", root).stdout                    # judge.json now says 3 votes; two are missing

    (tmp_path / "calls").write_text("")
    good = run("judge", root, "--votes", "3", "--claude", fake, env=env).stdout
    assert "2 vote(s) to collect" in good and (tmp_path / "calls").read_text().count("\n") == 2   # only the missing ones
    assert (ws / "vote3.json").exists()
    assert "pending" not in run("score", root).stdout

    other = run("judge", root, "--votes", "3", "--claude", fake, "--model", "claude-opus-5-5", env=env, check=False)
    assert other.returncode and "was judged by claude-sonnet-5-5" in other.stderr    # no mixing models in one run
    assert json.loads((root / "judge.json").read_text())["model"] == "claude-sonnet-5-5"

    default = run("judge", root, "--claude", fake, env=env | {"JUDGE_VOTES": "4"}).stdout   # JUDGE_VOTES sets the default
    assert "2 vote(s) to collect" in default and (ws / "vote4.json").exists()
    assert "no such run" in run("score", tmp_path / "nope", check=False).stderr
