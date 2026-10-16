"""The API loop with repair rounds, for probing docs gaps: can a model write a working protocol from the docs alone?

    uv run ul/run_loop.py [--device star] [--tasks a1-a12-100ul ...] [--models claude-sonnet-5-5 ...]
                               [--attempts 3] [--rounds 3]
    uv run ul/run_loop.py --device bravo --reference    # no API calls: references/<device>/ through the same path

Per (task, model, attempt): the model gets the docs (cached system prompt) and the device brief (brief.render), and
answers with a protocol. It runs on the device mock (runner.py); if it raises, the error goes back to the model, up to
--rounds repairs. The final run is scored with the same deterministic checks as the Harbor task (check.check_run on
the tests/ folder make_tasks.render_task generates). The model only ever sees runtime errors, never the checks.

Everything lands in results/poc-runs/<timestamp>/: per attempt the protocol of every round, the run result, the checks
and the transcript; summary.json and a table at the end. Nothing leaves this machine except the API calls.
"""
import argparse
import datetime
import json
import pathlib
import re
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent                       # backends/unitelabs
UPSTREAM = ROOT.parents[1]              # the benchmark
sys.path.insert(0, str(ROOT / "ul"))
import make_tasks  # noqa: E402
from brief import render  # noqa: E402
from check import check_run  # noqa: E402
from devices import DEVICES  # noqa: E402
from paths import UL_PYTHON  # noqa: E402

DOCS = ROOT.parents[2] / "docs"
DOC_PAGES = [  # deck, labware, liquids, tips and pipetting; the STAR pages are kept for every device (they are short)
    "content/01.get-started/03.liquid-handling-as-code.md",
    "content/04.concepts/03.operate/10.liquid-handling.md",
    "content/04.concepts/03.operate/30.deck.md",
    "content/04.concepts/03.operate/40.labware.md",
    "content/04.concepts/03.operate/50.liquids.md",
    "content/04.concepts/03.operate/70.tips.md",
    "content/06.liquid-handling-and-robots/00.overview.md",
    "content/06.liquid-handling-and-robots/10.deck/10.building-a-deck.md",
    "content/06.liquid-handling-and-robots/20.pipetting/10.basic-pipetting.md",
    "content/06.liquid-handling-and-robots/20.pipetting/20.advanced-pipetting.md",
    "content/06.liquid-handling-and-robots/20.pipetting/30.tip-handling.md",
    "content/06.liquid-handling-and-robots/41.hamilton-star/60.waste-block.md",
    "content/06.liquid-handling-and-robots/41.hamilton-star/66.complex-mixing.md",
    "content/07.labware/00.overview.md",
    "content/07.labware/10.standard-labware.md",
    "content/07.labware/20.plates.md",
    "content/07.labware/30.tips-and-racks.md",
    "content/07.labware/50.troughs.md",
    "content/07.labware/60.carriers-and-adapters.md",
]
TASKS = ["a1-a12-100ul", "split-200ul-two-wells", "ampure-bead-cleanup", "colony-pcr-screening"]
MODELS = ["claude-sonnet-5-5", "claude-opus-5-5"]
PRICES = {  # $/MTok: input, output, cache write (5 min, 1.25x input), cache read
    "claude-sonnet-5-5": (2.0, 10.0, 2.5, 0.20),
    "claude-opus-5-5": (4.0, 20.0, 5.0, 0.20),
}
SYSTEM_INTRO = """You write liquid handling protocols for {device} robots with the UniteLabs liquid handling SDK.
Below is the SDK documentation. It is your only reference for the API: use the classes, methods and arguments it
shows. Code examples in it may show several devices in tabs; this task is for {article} {device}.
"""


API_NOTE = """
## Answering in this run

There is no sandbox here: answer with the complete protocol in a single ```python code block. It is run on the
simulated device for you, and any error comes back so you can send a corrected protocol.
"""


def docs_text(device) -> tuple[str, str]:
    commit = subprocess.run(["git", "-C", str(DOCS), "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    pages = [f'<page path="{p}">\n{(DOCS / p).read_text()}\n</page>' for p in DOC_PAGES]
    intro = SYSTEM_INTRO.format(device=device.name, article="an" if device.name[0] in "AEIOU" else "a")
    return intro + "\n\n" + "\n\n".join(pages), commit


def extract_code(text: str) -> str | None:
    blocks = re.findall(r"```python\n(.*?)```", text, re.S)
    return blocks[-1] if blocks else None


def run_protocol(device_key: str, code: str, timeout: int = 600) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        protocol, result = pathlib.Path(tmp, "protocol.py"), pathlib.Path(tmp, "result.json")
        protocol.write_text(code)
        try:
            subprocess.run([UL_PYTHON, "-I", str(ROOT / "ul/runner.py"), device_key, str(protocol), str(result)],
                           capture_output=True, text=True, timeout=timeout, cwd=tmp)
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": f"TimeoutError: the protocol ran longer than {timeout} s"}
        if result.exists():
            return json.loads(result.read_text())
    return {"ok": False, "error": "the protocol exited before the run finished"}


def cost(model: str, usage: dict) -> float:
    i, o, w, r = PRICES[model]
    return (usage["input_tokens"] * i + usage["output_tokens"] * o + usage["cache_creation_input_tokens"] * w
            + usage["cache_read_input_tokens"] * r) / 1e6


def attempt(client, device, model: str, system: str, brief: str, rounds: int, out: pathlib.Path) -> dict:
    messages = [{"role": "user", "content": brief}]
    usage = {"input_tokens": 0, "output_tokens": 0, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0}
    run, errors = None, []
    for rnd in range(rounds + 1):
        with client.messages.stream(
            model=model, max_tokens=64000,
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            output_config={"effort": "high"},
            messages=messages,
        ) as stream:
            response = stream.get_final_message()
        for k in usage:
            usage[k] += getattr(response.usage, k) or 0
        messages.append({"role": "assistant", "content": response.content})   # full content: keeps thinking blocks valid
        if response.stop_reason == "refusal":
            return {"status": "refused", "rounds": rnd, "usage": usage, "errors": errors}
        text = "".join(b.text for b in response.content if b.type == "text")
        code = extract_code(text)
        if code is None:
            errors.append("no python code block")
            messages.append({"role": "user", "content": "Reply with the complete protocol in a single ```python code block."})
            continue
        (out / f"round_{rnd}.py").write_text(code)
        run = run_protocol(device.key, code)
        if run["ok"]:
            break
        errors.append(run["error"].splitlines()[0][:200])
        messages.append({"role": "user", "content": f"Running your protocol on the simulated {device.name} failed:\n\n```\n"
                         f"{run.get('traceback') or run['error']}\n```\n\nSend the complete corrected protocol."})
    (out / "transcript.json").write_text(json.dumps(
        [{"role": m["role"], "content": m["content"] if isinstance(m["content"], str)
          else [b.model_dump() for b in m["content"]]} for m in messages], indent=1))
    return {"status": "ran" if run and run["ok"] else "failed", "rounds": rnd, "usage": usage, "errors": errors, "run": run}


def score(device, task: str, run: dict | None, out: pathlib.Path) -> dict:
    if not run:
        return {"passed": False, "checks": []}
    (out / "result.json").write_text(json.dumps(run))
    with tempfile.TemporaryDirectory() as tmp:
        tests = pathlib.Path(tmp)
        for rel, content in make_tasks.render_task(task, device, "unused", allow_missing=True).items():
            if rel.startswith("tests/") and rel.count("/") == 1:
                (tests / rel.removeprefix("tests/")).write_bytes(content if isinstance(content, bytes) else content.encode())
        res = check_run(tests, run)
    (out / "checks.json").write_text(json.dumps(res, indent=1))
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", default="star", choices=list(DEVICES))
    ap.add_argument("--tasks", nargs="+", default=TASKS)
    ap.add_argument("--models", nargs="+", default=MODELS)
    ap.add_argument("--attempts", type=int, default=3)
    ap.add_argument("--rounds", type=int, default=3, help="repair rounds after the first answer")
    ap.add_argument("--reference", action="store_true", help="run the reference protocols, no API calls")
    a = ap.parse_args()
    device = DEVICES[a.device]
    root = ROOT / "results/poc-runs" / f"{datetime.datetime.now():%Y-%m-%d-%H%M%S}-{device.key}"
    rows = []
    if a.reference:
        for task in a.tasks:
            out = root / task / "reference"
            out.mkdir(parents=True)
            ref = ROOT / "references" / device.key / f"{task}.py"
            if not ref.exists():
                print(f"{task:24} no reference for {device.key} (infeasible there?)")
                continue
            run = run_protocol(device.key, make_tasks.solution_code(ref.read_text()))
            res = score(device, task, run, out)
            rows.append({"task": task, "model": "reference", "attempt": 0, "status": "ran" if run["ok"] else "failed",
                         "rounds": 0, "passed": res["passed"], "failed_checks": [c["name"] for c in res["checks"] if not c["pass"]],
                         "errors": [] if run["ok"] else [run["error"][:200]], "cost": 0.0})
    else:
        import os

        import anthropic

        env = ROOT / ".env"           # ANTHROPIC_API_KEY=... ; excluded from git, never printed
        if env.exists():
            for line in env.read_text().splitlines():
                key, _, value = line.partition("=")
                if key.strip() and value.strip():
                    os.environ.setdefault(key.strip(), value.strip())
        client = anthropic.Anthropic()
        system, commit = docs_text(device)
        (root).mkdir(parents=True)
        (root / "docs_commit.txt").write_text(commit + "\n" + "\n".join(DOC_PAGES) + "\n")
        for task in a.tasks:
            brief = render(task, device.key) + API_NOTE
            for model in a.models:
                for k in range(a.attempts):
                    out = root / task / model / str(k)
                    out.mkdir(parents=True)
                    (out / "brief.md").write_text(brief)
                    r = attempt(client, device, model, system, brief, a.rounds, out)
                    res = score(device, task, r.get("run") if r["status"] == "ran" else None, out)
                    rows.append({"task": task, "model": model, "attempt": k, "status": r["status"], "rounds": r["rounds"],
                                 "passed": res["passed"], "failed_checks": [c["name"] for c in res["checks"] if not c["pass"]],
                                 "errors": r["errors"], "cost": round(cost(model, r["usage"]), 4), "usage": r["usage"]})
                    print(f"{task:24} {model:18} #{k}  {r['status']:7} rounds={r['rounds']}  "
                          f"{'PASS' if res['passed'] else 'FAIL'}  ${rows[-1]['cost']:.3f}", flush=True)
    (root / "summary.json").write_text(json.dumps(rows, indent=1))
    print(f"\n{'task':24} {'model':18} {'pass':>6} {'ran':>5} {'avg repairs':>12} {'cost':>8}")
    for task in a.tasks:
        for model in sorted({r["model"] for r in rows}):
            rs = [r for r in rows if r["task"] == task and r["model"] == model]
            if rs:
                print(f"{task:24} {model:18} {sum(r['passed'] for r in rs):>3}/{len(rs):<2} "
                      f"{sum(r['status'] == 'ran' for r in rs):>3}/{len(rs):<1} {sum(r['rounds'] for r in rs) / len(rs):>12.1f} "
                      f"${sum(r['cost'] for r in rs):>7.2f}")
    print(f"\n{root}")


if __name__ == "__main__":
    main()
