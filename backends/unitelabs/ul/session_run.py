"""Run the benchmark with in-session Claude Code subagents instead of Harbor: a baseline without an API key.

    uv run ul/session_run.py make  <root> [--devices ...] [--tasks ...] [--model sonnet] [--attempts 1]
    uv run ul/session_run.py grade <root> [--only GLOB]   # after the agents wrote protocol.py / INFEASIBLE.md
    uv run ul/session_run.py judge <root> [--votes 3] [--jobs 4]   # headless Claude Code (claude -p) writes vote*.json (3 votes by default)
    uv run ul/session_run.py score <root>      # after the judge agents wrote vote.json
    uv run ul/session_run.py import-job jobs/<job> <root>   # Harbor agents (SKIP_JUDGE=1), then judge and score here

`make` writes <root>/<device>-<task>-<model>-<k>/ with brief.md, data/ (the paper, if any), ./simulate (the local
runner, prints the run log or the error, never the checks), prompt.txt: the exact prompt for the authoring agent, and
meta.json: the device, task, model and attempt the later steps read (model names may contain hyphens).
Nothing hidden is in the workspace; the prompt forbids reading this repo.

`grade` runs the same grader the Harbor task uses (make_tasks.render_task -> tests/, grade.py, judge skipped) on
each workspace, writes out/result.json, and judge.md: upstream's judge prompt for a judge agent to answer with
vote.json. `score` applies upstream's scoring (weighted rubric, critical cap; infeasibility verdicts as grade.py
records them) and prints the table, writing table.json.

Differences from a Harbor run, for the record: the agent harness is this session's subagent (not Harbor's
claude-code container), there is no sandbox, and the judge votes are in-session agents (JUDGE_VOTES, default 1,
where upstream takes 3). table.json records the vote count, so these rows are never mixed with Harbor's.

`import-job` is the hybrid: the agents ran in Harbor (sandbox, Harbor's claude-code agent) with SKIP_JUDGE=1, and only
the judge runs here. It makes one workspace per trial from the protocol (or INFEASIBLE.md) and result.json that
Harbor's verifier saved, and writes judge.md from that record; the grader is not rerun. Then judge and `score` as
above. table.json records agent "harbor" for these rows; keep them in their own <root>, apart from session-agent ones.

`judge` collects the votes without subagents: one `claude -p` call per judge.md and vote (no tools, the prompt on
stdin, Claude Code's own login, so no API key), checked against the rubric before it is saved as vote.json,
vote2.json, ... A failed or malformed reply is reported and not saved; running `judge` again collects only what is
missing. It writes <root>/judge.json (model, votes), which `score` reads, so the table says how it was judged, and
refuses to add votes from a different model to a run (each vote also records its model).

Why the judge is out here at all: upstream's verifier judges inside the sandbox through the Anthropic SDK, which needs
an API key we do not have; a Claude subscription token works for Claude Code only, and Harbor gives it to the agent,
not the verifier. This keeps the vendored grader untouched and makes the same judge calls from this machine. With an
API key, none of import-job/judge is needed: run Harbor without SKIP_JUDGE and use ul/leaderboard.py.
"""
import argparse
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "ul"))
sys.path.insert(0, str(ROOT.parents[1] / "tasks/a1-a12-100ul/tests"))
import make_tasks  # noqa: E402
from brief import render  # noqa: E402
from devices import DEVICES  # noqa: E402
from judge_text import prompt_for  # noqa: E402
import paths  # noqa: E402
from paths import UL_PYTHON  # noqa: E402

DOCS = paths.DOCS / "content"
JUDGE_VOTES = int(os.environ.get("JUDGE_VOTES", "1"))

SIMULATE = '''#!/bin/bash
# Run ./protocol.py on the simulated {device} and print what the robot did, step by step, or the error.
cd "$(dirname "$0")"
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
{py} -I {runner} {key} protocol.py "$tmp/result.json" >/dev/null 2>"$tmp/stderr"
{py} -I - "$tmp/result.json" <<'EOF'
import json, sys
r = json.load(open(sys.argv[1]))
if not r["ok"]:
    print(r.get("traceback") or r["error"]); raise SystemExit(1)
for e in r["events"]:
    k, ch = e["kind"], e.get("instrument", "").replace("_", " ")
    if k == "comment": print(e["text"])
    elif k == "pick": print(f"Picking up tip ({{ch}})")
    elif k == "drop": print(f"Dropping tip ({{ch}})")
    else:
        verb, prep = ("Aspirating", "from") if k == "aspirate" else ("Dispensing", "into")
        print(f"\\t{{verb}} {{e['volume']:g}} uL {{prep}} {{e['well']}} of {{e['labware']}} ({{ch}})")
print("Run completed.")
EOF
status=$?; tail -n 20 "$tmp/stderr"; exit $status
'''

PROMPT = '''You are writing a liquid handling protocol for a {device} using the UniteLabs liquid handling Python SDK. This is a benchmark run: work only from the documentation and the SDK, as a new user of this SDK would.

Your workspace: {ws}

1. Read `brief.md` in your workspace. It is the full task: the protocol contract, the labware you must provide (by identifier), the starting contents, the steps, the constraints, and what to do if the protocol cannot be run on this device.
2. The SDK documentation is under {docs}/ . Start with 01.get-started/03.liquid-handling-as-code.md, 04.concepts/03.operate/, 06.liquid-handling-and-robots/ (00.overview.md, 10.deck/, 20.pipetting/) and 07.labware/. You may read any other page there and the installed SDK source under {sdk_src}/ (the liquid handling package), {sdk_site}/ (the labware package) and {ulsdk_src}/ (the sdk package) when the docs are not enough.
3. Write your protocol to `protocol.py` in your workspace (or, if the brief's infeasibility clause applies, `INFEASIBLE.md` instead and no protocol.py).
4. Run `./simulate` in your workspace to execute protocol.py on the simulated {device}. It prints the run log or the error. Fix and re-run as often as you need. A completed run does not mean the protocol is correct: check yourself that it does exactly what the brief asks (volumes, wells, order, tips) and that the real instrument could do it.

Rules:
- Do NOT read anything under {repo}/ (the benchmark repo) or under the SDK checkouts ({checkouts}) other than the SDK paths named above. Do not read other workspaces under {root}/.
- Do not modify anything outside your workspace. Do not use the network. Do not run git.

When you are done, reply with:
- STATUS: whether your final protocol.py runs OK in ./simulate (or that you wrote INFEASIBLE.md, and why)
- SIMULATE_RUNS: how many times you ran ./simulate
- ERRORS: one line per distinct error you hit, and what fixed it
- DOCS_FEEDBACK: what in the documentation was missing, wrong or confusing for this task (be concrete). Say whether you had to read SDK source and why.
- FILES_READ: the files and directories you read outside your workspace.'''


def parse(ws: pathlib.Path) -> tuple[str, str, str, int]:
    meta = json.loads((ws / "meta.json").read_text())
    return meta["device"], meta["task"], meta["model"], int(meta["k"])


def make(a) -> None:
    root = pathlib.Path(a.root).resolve()
    for key in a.devices:
        device = DEVICES[key]
        for task in a.tasks:
            if task in make_tasks.SDK_GAPS.get(key, {}):
                continue
            data = ROOT.parents[1] / "tasks" / task / "environment/data"
            for k in range(a.start, a.start + a.attempts):
                ws = root / f"{key}-{task}-{a.model}-{k}"
                ws.mkdir(parents=True, exist_ok=False)
                (ws / "meta.json").write_text(json.dumps({"device": key, "task": task, "model": a.model, "k": k}) + "\n")
                (ws / "brief.md").write_text(render(task, key))
                if data.exists():
                    shutil.copytree(data, ws / "data")
                sim = ws / "simulate"
                sim.write_text(SIMULATE.format(device=device.name, py=UL_PYTHON, runner=ROOT / "ul/runner.py", key=key))
                sim.chmod(0o755)
                (ws / "prompt.txt").write_text(PROMPT.format(device=device.name, ws=ws, docs=DOCS, sdk_src=paths.LHSDK_SRC,
                                                             sdk_site=paths.LABWARE_SRC, ulsdk_src=paths.ULSDK_SRC, repo=ROOT, root=root,
                                                             checkouts=", ".join(f"{c}/" for c in (paths.LHSDK, paths.ULSDK, paths.LABWARE))))
    print(f"{sum(p.is_dir() for p in root.iterdir())} workspaces in {root}")


def judge_prompt(tests: pathlib.Path, ws: pathlib.Path, checks: list[dict], protocol: str) -> str:
    import judge_layer
    rubric = judge_layer.load_rubric(tests)
    task = json.loads((tests / "task.json").read_text())
    hard = rubric["level"] == "hard"
    paper = ws / "data/paper.txt"
    text = prompt_for(judge_layer.PROMPT, task["device_name"]).replace(
        "You must call the submit_grades tool exactly once with your grades, in this shape:",
        "Reply with only this JSON object (no prose around it), in this shape:")
    return text.format(
        end_state_note=judge_layer.HARD_END_STATE_NOTE if hard else "",
        spec_name="THE PAPER" if hard else "THE TASK TEXT" + (" (the paper is background only)" if paper.exists() else ""),
        rubric="\n".join(f"- {r['id']} ({r['weight']:.1%} of the reward): {r['text']}" for r in rubric["items"]),
        task=(tests / "instruction.md").read_text(),
        paper_block=f"\n=== PAPER (text extraction) ===\n{paper.read_text()}\n" if paper.exists() else "",
        reference=(tests / "reference_protocol.py").read_text(),
        checks=json.dumps(checks, indent=1), protocol=protocol)


def write_tests(task: str, device: str, tmp: str) -> pathlib.Path:
    """The Harbor task's tests/ for (device, task), rendered into tmp."""
    for rel, content in make_tasks.render_task(task, DEVICES[device], "unused").items():
        if rel.startswith("tests/"):
            path = pathlib.Path(tmp) / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content if isinstance(content, bytes) else content.encode())
    return pathlib.Path(tmp) / "tests"


def write_judge(ws: pathlib.Path, tests: pathlib.Path, record: dict) -> None:
    if record.get("checks") and (ws / "protocol.py").exists():
        (ws / "judge.md").write_text(judge_prompt(tests, ws, record["checks"], (ws / "protocol.py").read_text()))


def grade(a) -> None:
    root = pathlib.Path(a.root).resolve()
    for ws in sorted(p for p in root.glob(a.only) if p.is_dir()):
        device, task, model, k = parse(ws)
        out = ws / "out"
        shutil.rmtree(out, ignore_errors=True)
        (ws / "judge.md").unlink(missing_ok=True)
        with tempfile.TemporaryDirectory() as tmp:
            tests = write_tests(task, device, tmp)
            env = dict(os.environ, TESTS_DIR=str(tests), PROTOCOL_PATH=str(ws / "protocol.py"), VERIFIER_OUT=str(out),
                       DATA_DIR=str(ws / "data"), SKIP_JUDGE="1", T2WL_LOCAL_VENV="1", UL_PYTHON=UL_PYTHON)
            subprocess.run([UL_PYTHON, str(tests / "grade.py")], env=env, capture_output=True, text=True, timeout=1200)
            record = json.loads((out / "result.json").read_text()) if (out / "result.json").exists() else {"error": "grade.py produced no result"}
            write_judge(ws, tests, record)
        r = record.get("rewards", {})
        print(f"{ws.name:50} det={r.get('deterministic_reward', r.get('reward'))} {record.get('error') or record.get('verdict') or ''}"
              f" failed={[c['name'] for c in record.get('checks', []) if not c['pass']]}")


def import_job(a) -> None:
    from leaderboard import model_of, trials
    root = pathlib.Path(a.root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    metas = [json.loads((ws / "meta.json").read_text()) for ws in root.iterdir() if (ws / "meta.json").exists()]
    taken = {(m["device"], m["task"], m["model"], int(m["k"])) for m in metas}
    imported = {m.get("trial") for m in metas}
    for job in a.jobs:
        for trial, harbor, record in trials(job.resolve()):
            if str(trial) in imported:
                print(f"{trial.name:50} skipped: already imported")
                continue
            device, _, task = (harbor.get("task_name") or "").split("/")[-1].partition(".")
            if device not in DEVICES or not task:
                print(f"{trial.name:50} skipped: task_name {harbor.get('task_name')!r} is not <org>/<device>.<task>")
                continue
            model = model_of(harbor).split("/")[-1]
            k = next(i for i in range(len(taken) + 1) if (device, task, model, i) not in taken)
            taken.add((device, task, model, k))
            ws = root / f"{device}-{task}-{model}-{k}"
            ws.mkdir()
            (ws / "meta.json").write_text(json.dumps({"device": device, "task": task, "model": model, "k": k,
                                                      "agent": "harbor", "trial": str(trial)}) + "\n")
            data = ROOT.parents[1] / "tasks" / task / "environment/data"
            if data.exists():
                shutil.copytree(data, ws / "data")
            for name in ("protocol.py", "INFEASIBLE.md"):
                if (trial / "verifier" / name).exists():
                    shutil.copy(trial / "verifier" / name, ws / name)
            (ws / "out").mkdir()
            if record:
                (ws / "out/result.json").write_text(json.dumps(record, indent=1))
            with tempfile.TemporaryDirectory() as tmp:
                write_judge(ws, write_tests(task, device, tmp), record)
            judged = not (record.get("judge_config") or record.get("judge") or {"skipped": True}).get("skipped")
            r = record.get("rewards", {})
            print(f"{ws.name:50} det={r.get('deterministic_reward', r.get('reward'))} {record.get('error') or record.get('verdict') or ''}"
                  + (" judge.md" if (ws / "judge.md").exists() else "") + (" (Harbor's judge also ran; its votes are ignored)" if judged else "")
                  + ("" if record else " no verifier result: scores 0"))


def rubric_of(ws: pathlib.Path) -> tuple[dict, list[str]]:
    """The rubric for the workspace's device and task, and its item ids."""
    import judge_layer
    device, task, _, _ = parse(ws)
    files = make_tasks.render_task(task, DEVICES[device], "unused")
    with tempfile.TemporaryDirectory() as tmp:
        tests = pathlib.Path(tmp)
        (tests / "rubric.json").write_bytes(files["tests/rubric.json"].encode())
        rubric = judge_layer.load_rubric(tests)
    return rubric, [r["id"] for r in rubric["items"]]


def parse_vote(text: str, ids: list[str]) -> dict:
    """The judge's JSON object out of its reply (fences or prose around it are dropped). ValueError when it is not
    one vote per rubric item with a 0/1 score."""
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("no JSON object in the reply")
    data = json.loads(text[start:end + 1])
    got = sorted(i["id"] for i in data["items"])      # a list: a duplicated id is a defect too
    if got != sorted(ids):
        raise ValueError(f"rubric ids {got} != {sorted(ids)}")
    if any(type(i["score"]) is not int or i["score"] not in (0, 1) for i in data["items"]):   # bools are not scores
        raise ValueError("a score is not 0 or 1")
    return data


JUDGE_CLI = ("--tools", "", "--no-session-persistence", "--output-format", "json")   # no tools: the prompt is all it gets


def ask_judge(claude: str, model: str, prompt: str) -> str:
    """One headless Claude Code call: the reply text. RuntimeError when the call fails."""
    p = subprocess.run([claude, "-p", "--model", model, *JUDGE_CLI], input=prompt, capture_output=True, text=True, timeout=900)
    if p.returncode:
        raise RuntimeError(p.stderr.strip()[-300:] or f"exit {p.returncode}")
    out = json.loads(p.stdout)
    if not isinstance(out, dict) or "result" not in out:
        raise RuntimeError(f"unexpected claude output: {p.stdout[:200]!r}")
    if out.get("is_error"):
        raise RuntimeError(str(out.get("result"))[:300])
    return out["result"]


def vote_files(ws: pathlib.Path, votes: int) -> list[pathlib.Path]:
    """vote.json, vote2.json, ... voteN.json: the names `judge` writes and `score` reads (never a glob)."""
    return [ws / ("vote.json" if n == 1 else f"vote{n}.json") for n in range(1, votes + 1)]


def judge(a) -> int:
    from concurrent.futures import ThreadPoolExecutor
    root = pathlib.Path(a.root).resolve()
    if not root.is_dir():
        raise SystemExit(f"no such run: {root}")
    if not shutil.which(a.claude):
        raise SystemExit(f"{a.claude}: not found; the judge is headless Claude Code (`claude -p`)")
    cfg = {"harness": "claude-cli", "model": a.model, "votes": a.votes}
    previous = json.loads((root / "judge.json").read_text()) if (root / "judge.json").exists() else None
    if previous and previous.get("model") != a.model:   # votes from two models under one label would be a lie
        raise SystemExit(f"{root.name} was judged by {previous.get('model')}; use --model {previous.get('model')}, "
                         f"or delete its vote*.json and judge.json to judge again with {a.model}")
    todo = [(ws, vote) for ws in sorted(p for p in root.iterdir() if (p / "judge.md").exists())
            for vote in vote_files(ws, a.votes) if not vote.exists()]
    (root / "judge.json").write_text(json.dumps(cfg) + "\n")
    print(f"{len(todo)} vote(s) to collect with {a.model}, {a.jobs} at a time")

    def one(item):
        ws, vote = item
        try:
            data = parse_vote(ask_judge(a.claude, a.model, (ws / "judge.md").read_text()), rubric_of(ws)[1])
        except Exception as e:   # every failure is a line to print and a vote to collect next time, never a crash
            return ws, vote, f"FAILED: {type(e).__name__ if not str(e) else ''}{e}"
        data["judge"] = {"model": a.model, "harness": "claude-cli"}   # provenance travels with the vote
        tmp = vote.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, indent=1) + "\n")
        os.replace(tmp, vote)                                       # never a half-written vote
        return ws, vote, f"{sum(i['score'] for i in data['items'])}/{len(data['items'])}"

    failed = 0
    with ThreadPoolExecutor(a.jobs) as pool:
        for ws, vote, msg in pool.map(one, todo):
            failed += msg.startswith("FAILED")
            print(f"{ws.name:50} {vote.name:11} {msg}")
    if failed:
        print(f"{failed} failed: run `judge` again to collect them")
    return 1 if failed else 0


def score_ws(ws: pathlib.Path, votes_wanted: int) -> tuple[float | None, str]:
    """(reward, outcome) with upstream's scoring; None while judge votes are missing."""
    import judge_layer
    result = ws / "out/result.json"
    if not result.exists():
        return 0.0, "not graded"
    record = json.loads(result.read_text())
    if record.get("verdict", "").startswith("correctly declared infeasible"):
        return 1.0, "infeasible_recognized"
    if record.get("verdict", "").startswith("wrote a protocol for a task this device cannot run"):
        return 0.0, "infeasible_missed"
    if record.get("error"):
        labels = {"missing protocol": "no_protocol",   # the labels ul/leaderboard.py uses
                  "protocol uses something a protocol does not need and is not graded": "lint",
                  "reward-hacking trap tripped": "trap", "simulator gate failed": "simulator",
                  "declared infeasible, but": "wrongly_declared_infeasible",
                  "declared infeasible without naming": "infeasible_wrong_reason"}
        return 0.0, next((label for prefix, label in labels.items() if record["error"].startswith(prefix)),
                         record["error"].split(",")[0][:40])
    votes = vote_files(ws, votes_wanted)
    if not all(v.exists() for v in votes):
        return None, "awaiting judge"
    rubric, ids = rubric_of(ws)
    parsed = []
    for v in votes:
        data = json.loads(v.read_text())
        data["scores"] = {i["id"]: float(i["score"]) for i in data["items"]}
        if set(data["scores"]) != set(ids):
            raise SystemExit(f"{v}: rubric ids {sorted(data['scores'])} != {sorted(ids)}")
        parsed.append(data)
    _, scores = judge_layer.majority(parsed, ids)
    s = judge_layer.weighted_score(rubric, scores)
    critical = [c["name"] for c in record["checks"] if not c["pass"] and judge_layer.is_critical(c["name"], rubric["level"])]
    return round(min(s, judge_layer.CRITICAL_CAP) if critical else s, 4), ("critical_check" if critical else "graded")


def score(a) -> None:
    root = pathlib.Path(a.root).resolve()
    if not root.is_dir():
        raise SystemExit(f"no such run: {root}")
    # judge.json: written by `judge`; a run judged by in-session subagents has none (JUDGE_VOTES says how many votes)
    cfg = json.loads((root / "judge.json").read_text()) if (root / "judge.json").exists() else {"harness": "session", "votes": JUDGE_VOTES}
    cfg["votes"] = a.votes or cfg["votes"]
    rows = {}
    for ws in sorted(p for p in root.iterdir() if p.is_dir()):
        device, task, model, k = parse(ws)
        reward, outcome = score_ws(ws, cfg["votes"])
        det = None
        if (ws / "out/result.json").exists():
            det = json.loads((ws / "out/result.json").read_text()).get("rewards", {}).get("deterministic_reward")
        rows[ws.name] = {"device": device, "task": task, "model": model, "k": k, "reward": reward, "deterministic": det,
                         "outcome": outcome, "agent": json.loads((ws / "meta.json").read_text()).get("agent", "session"),
                         "judge": cfg}
    tasks = sorted({r["task"] for r in rows.values()})
    how = "In-session judge" if cfg["harness"] == "session" else f"Judge {cfg.get('model')} via claude -p"
    print(f"{how}, {cfg['votes']} vote(s) per protocol.\n")
    print("| model @ device | mean | " + " | ".join(tasks) + " |")
    print("|---|---|" + "---|" * len(tasks))
    for (model, device) in sorted({(r["model"], r["device"]) for r in rows.values()}):
        cells, means = [], []
        for t in tasks:
            rs = [r for r in rows.values() if r["model"] == model and r["device"] == device and r["task"] == t]
            done = [r["reward"] for r in rs if r["reward"] is not None]
            if done:
                means.append(sum(done) / len(done))
                odd = [r["outcome"] for r in rs if r["outcome"] not in ("graded", "infeasible_recognized")]
                cells.append(f"{sum(done)/len(done):.2f}" + (f" ({odd[0]})" if odd else ""))
            else:
                cells.append("pending" if rs else "–")
        print(f"| {model} @ {device} | {sum(means)/len(means):.3f} | " + " | ".join(cells) + " |" if means else f"| {model} @ {device} | pending | " + " | ".join(cells) + " |")
    (root / "table.json").write_text(json.dumps(rows, indent=1))


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("make")
    m.add_argument("root")
    m.add_argument("--devices", nargs="+", default=list(DEVICES))
    m.add_argument("--tasks", nargs="+", default=make_tasks.DEFAULT_TASKS)
    m.add_argument("--model", default="sonnet")
    m.add_argument("--attempts", type=int, default=1)
    m.add_argument("--start", type=int, default=0)
    g = sub.add_parser("grade")
    g.add_argument("root")
    g.add_argument("--only", default="*", help="regrade only workspaces whose name matches this glob")
    j = sub.add_parser("judge")
    j.add_argument("root")
    j.add_argument("--votes", type=int, default=int(os.environ.get("JUDGE_VOTES") or 3), help="judge calls per protocol (default: JUDGE_VOTES or 3, as upstream)")
    j.add_argument("--jobs", type=int, default=4, help="calls at a time")
    j.add_argument("--model", default=os.environ.get("JUDGE_MODEL") or "claude-sonnet-5-5", help="judge model (upstream's judge_layer.JUDGE_MODEL)")
    j.add_argument("--claude", default="claude", help=argparse.SUPPRESS)   # the Claude Code binary; tests pass a fake
    s = sub.add_parser("score")
    s.add_argument("root")
    s.add_argument("--votes", type=int, help="votes per protocol to score (default: what `judge` collected, else JUDGE_VOTES)")
    i = sub.add_parser("import-job")
    i.add_argument("jobs", nargs="+", type=pathlib.Path, help="Harbor job dirs, run with SKIP_JUDGE=1")
    i.add_argument("root")
    a = ap.parse_args()
    return {"make": make, "grade": grade, "judge": judge, "score": score, "import-job": import_job}[a.cmd](a) or 0


if __name__ == "__main__":
    sys.exit(main())
