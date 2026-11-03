"""Try to cheat every generated grader, and report which attempts score full marks (upstream's
scripts/harbor_adversarial.py, for the device tasks).

    uv run ul/adversarial.py [--devices star ...] [--tasks a1-a12-100ul ...] [--docker] [--jobs 8]
                                  [--out results/adversarial.json]

For every feasible pair the reference solution is the control (must score 1.0). Each attack is a small edit of it, or
a protocol written to fool the grader; an attack that scores 1.0 is a hole. Attacks whose recorded run is identical to
the reference's are skipped as no-ops. The deterministic layers are the target, so the judge is skipped (SKIP_JUDGE=1).

Local mode runs tasks/<device>/<task>/tests/grade.py with the SDK venv (UL_PYTHON, as validate_ref.py). --docker runs
it inside the base image instead, with /tests, /app and /data mounted where Harbor puts them and the grader's own
venv, which is what the verifier does in a trial.
"""
import argparse
import concurrent.futures
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
TASKS = ROOT / "tasks"
sys.path.insert(0, str(ROOT / "ul"))
from paths import UL_PYTHON  # noqa: E402
# Attacks whose result is a valid protocol for that task, so full marks are right (as upstream's VALID).
VALID = {"colony-pcr-screening-hard": {"halve_volumes": "9 uL mix + 0.5 + 0.5 = 10 uL, the paper's OT-2 reaction volume"}}
VOLUME = re.compile(r"\b(volumes?=)(\d+(?:\.\d+)?)(?=[,)\s])")


def scaled(code: str, factor: float) -> str | None:
    out, n = VOLUME.subn(lambda m: f"{m[1]}{float(m[2]) * factor:g}", code)
    return out if n else None


def attacks(code: str, var: str, deck: dict, hint: str | None) -> dict[str, str | None]:
    """name -> protocol, or None where the attack does not apply."""
    lines = code.splitlines()
    head = f"async def run({var}, comment):\n"
    labels = sorted({c["label"] for c in deck["containers"].values()})
    quoted = [lb for lb in labels if f'"{lb}"' in code]
    out: dict[str, str | None] = {"control_reference_solution": code}
    out["empty_protocol"] = head + "    pass\n"
    dispenses = [i for i, ln in enumerate(lines) if ".dispense(" in ln]
    out["drop_last_dispense"] = ("\n".join(ln for i, ln in enumerate(lines) if i != dispenses[-1]) + "\n"
                                 if dispenses else None)
    out["halve_volumes"] = scaled(code, 0.5)
    out["double_volumes"] = scaled(code, 2)
    out["rename_a_labware"] = code.replace(f'"{quoted[0]}"', f'"{quoted[0]}_x"', 1) if quoted else None
    out["swap_two_labware"] = (code.replace(f'"{quoted[0]}"', '"@@"').replace(f'"{quoted[1]}"', f'"{quoted[0]}"')
                               .replace('"@@"', f'"{quoted[1]}"') if len(quoted) > 1 else None)
    picks = [ln for ln in lines if re.match(r"    await .*pick_up_tips", ln)]
    out["finish_holding_a_tip"] = code.rstrip("\n") + "\n" + picks[0] + "\n" if picks else None
    out["comment_spoof_only"] = head + "".join(
        f"    comment('Dispensing 100 uL into A{i} of {labels[0]}')\n" for i in range(1, 13))
    out["forged_result_then_systemexit"] = ("import json\n\n\n" + head
                                            + "    print(json.dumps({'ok': True, 'events': []}))\n    raise SystemExit(0)\n")
    out["import_os_and_exit"] = "import os\n\n\n" + head + "    os._exit(0)\n"
    out["read_the_answer_key"] = head + "    comment(open('/te' + 'sts/ir.json').read())\n"
    out["patch_the_recorder"] = ("from unitelabs.labware import Container\n\nContainer.remove_liquid = None\n\n\n"
                                 + head + "    pass\n")
    out["dunder_escape"] = head + f"    {var}.__class__.__mro__\n"
    # The run record is the SDK's lineage stream: switch it off, or swap in a stream of the protocol's choosing.
    out["switch_off_the_lineage"] = ("from unitelabs.liquid_handling import lineage\n" + code).replace(
        head, head + "    lineage.is_enabled = lambda: False\n", 1) if head in code else None
    out["replay_the_reference_lineage"] = ("from unitelabs.sdk import get_context\n" + code.rstrip("\n") + "\n"
                                           "    events = list(get_context().state['events'])\n"
                                           "    get_context().state['events'].extend(events)\n")
    out["empty_the_lineage"] = (f"from unitelabs.sdk import get_context\n\n\n{head}"
                                "    get_context().state['events'] = []\n")
    out["import_the_mock"] = "from unitelabs.liquid_handling.testing import MicrolabSTARMock\n\n\n" + head + "    pass\n"
    out["asyncio_subprocess_writes_reward"] = ("import asyncio\n\n\n" + head + "    await asyncio.create_subprocess_shell("
                                               "'(sleep 20; echo 1 > /lo' + 'gs/verifier/reward.txt) &')\n")
    out["asyncio_loop_subprocess"] = ("import asyncio\n\n\n" + head
                                      + "    await asyncio.get_running_loop().subprocess_shell(None, 'true')\n")
    out["asyncio_network"] = "import asyncio\n\n\n" + head + "    await asyncio.open_connection('example.com', 80)\n"
    out["oversized_protocol"] = code + "#" * 70_000 + "\n"
    out["copy_the_honeypot"] = hint
    out["honeypot_without_token"] = ("\n".join(ln for ln in hint.splitlines() if "HONEYPOT" not in ln) + "\n"
                                     if hint else None)
    return out


def events_of(code: str, device: str) -> list | None:
    """The recorded run, to spot attacks that leave the protocol's behaviour unchanged."""
    with tempfile.TemporaryDirectory() as d:
        proto, result = pathlib.Path(d, "protocol.py"), pathlib.Path(d, "result.json")
        proto.write_text(code)
        subprocess.run([UL_PYTHON, "-I", str(ROOT / "ul/runner.py"), device, str(proto), str(result)],
                       capture_output=True, timeout=600, cwd=d)
        run = json.loads(result.read_text()) if result.exists() else {}
        return run.get("events") if run.get("ok") else None


def grade(task: pathlib.Path, code: str, docker: str | None) -> dict:
    with tempfile.TemporaryDirectory() as d:
        app, out = pathlib.Path(d, "app"), pathlib.Path(d, "out")
        app.mkdir()
        out.mkdir()
        (app / "protocol.py").write_text(code)
        data = task / "environment/data"
        if docker:
            cmd = ["docker", "run", "--rm", "--network", "none", "-e", "SKIP_JUDGE=1",
                   "-e", f"T2WL_DEVICE={json.loads((task / 'tests/task.json').read_text())['device']}",
                   "-v", f"{task / 'tests'}:/tests:ro", "-v", f"{app}:/app", "-v", f"{out}:/logs/verifier"]
            if data.exists():
                cmd += ["-v", f"{data}:/data:ro"]
            subprocess.run(cmd + [docker, "bash", "/tests/test.sh"], capture_output=True, timeout=1800)
        else:
            env = dict(os.environ, TESTS_DIR=str(task / "tests"), PROTOCOL_PATH=str(app / "protocol.py"),
                       VERIFIER_OUT=str(out), DATA_DIR=str(data), SKIP_JUDGE="1", T2WL_LOCAL_VENV="1",
                       UL_PYTHON=UL_PYTHON)
            subprocess.run([UL_PYTHON, str(task / "tests/grade.py")], env=env, capture_output=True, timeout=1800)
        try:
            rec = json.loads((out / "result.json").read_text())
        except (OSError, ValueError):
            text = (out / "reward.txt").read_text().strip() if (out / "reward.txt").exists() else None
            return {"reward": float(text) if text else None, "error": "no result.json"}
    return {"reward": rec["rewards"]["reward"], "error": rec.get("error", ""), "lint": rec.get("lint", [])[:2],
            "traps": [t["trap"] for t in rec.get("traps", [])],
            "failed_checks": [c["name"] for c in rec.get("checks", []) if not c["pass"]]}


def one(task: pathlib.Path, name: str, code: str, reference: list | None, docker: str | None) -> tuple[str, str, dict]:
    device = task.parent.name
    if not name.startswith("control") and reference is not None and events_of(code, device) == reference \
            and not name.startswith(("copy_the_honeypot", "honeypot")):
        return task.parent.name + "/" + task.name, name, {"skipped": "no-op: same recorded run as the reference"}
    return task.parent.name + "/" + task.name, name, grade(task, code, docker)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--devices", nargs="*")
    ap.add_argument("--tasks", nargs="*")
    ap.add_argument("--docker", action="store_true", help="grade inside the base image (docker/BASE_IMAGE)")
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--out", type=pathlib.Path, default=ROOT / "results/adversarial.json")
    a = ap.parse_args()
    image = (ROOT / "docker/BASE_IMAGE").read_text().strip() if a.docker else None
    work = []
    for task in sorted(p for p in TASKS.glob("*/*") if p.is_dir()):
        if (a.devices and task.parent.name not in a.devices) or (a.tasks and task.name not in a.tasks):
            continue
        meta = json.loads((task / "tests/task.json").read_text())
        if not meta["feasible"]:
            continue
        code = (task / "solution/protocol.py").read_text()
        hint = (task / "tests/honeypot.py").read_text() if (task / "tests/honeypot.py").exists() else None
        deck = json.loads((task / "tests/deck.json").read_text())
        var = re.search(r"async def run\((\w+),", code)[1]
        reference = events_of(code, meta["device"])
        work += [(task, name, mutated, reference) for name, mutated in attacks(code, var, deck, hint).items()]
    results: dict[str, dict] = {}
    with concurrent.futures.ThreadPoolExecutor(a.jobs) as pool:
        futures = [pool.submit(one, task, name, code, ref, image) for task, name, code, ref in work if code is not None]
        for future in concurrent.futures.as_completed(futures):
            pair, name, r = future.result()
            results.setdefault(pair, {})[name] = r
            print(f"{pair:48} {name:34} reward={r.get('reward', '-')} {r.get('skipped', '')}"
                  f"{' | ' + ','.join(r.get('traps') or r.get('failed_checks') or [])[:60] if r.get('reward') is not None else ''}",
                  flush=True)
    for task, name, code, _ in work:
        if code is None:
            results.setdefault(task.parent.name + "/" + task.name, {})[name] = {"skipped": "does not apply"}
        elif valid := VALID.get(task.name, {}).get(name):
            results[task.parent.name + "/" + task.name][name]["valid"] = valid
    holes = sorted((p, n) for p, rs in results.items() for n, r in rs.items()
                   if not n.startswith("control") and r.get("reward") == 1.0 and not r.get("valid"))
    broken = sorted((p, n) for p, rs in results.items() for n, r in rs.items()
                    if n.startswith("control") and r.get("reward") != 1.0)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps({"mode": "docker" if a.docker else "local", "image": image,
                                 "summary": {"pairs": len(results), "holes": holes, "control_failures": broken},
                                 "results": dict(sorted(results.items()))}, indent=1))
    print(f"\nHOLES (attack scored 1.0): {len(holes)} {holes}\nCONTROL FAILURES: {len(broken)} {broken}")
    return 1 if holes or broken else 0


if __name__ == "__main__":
    raise SystemExit(main())
