"""Grade one reference protocol (or INFEASIBLE.md) for one device locally, without Docker: the same tests/ folder
make_tasks.py generates, upstream's gates, the device mock, the deterministic checks; the judge is skipped.

    uv run ul/validate_ref.py <device> <task> [protocol.py]      default: references/<device>/<task>.py,
                                                                      or <task>.INFEASIBLE.md where there is none

Needs UL_PYTHON pointing at a Python with the SDK installed (default: python-lib/.venv next to the Text2WetLab
checkout, see paths.py).
Prints the reward and every failed check; exit 1 unless deterministic_reward is 1.0.
"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "ul"))
import make_tasks  # noqa: E402
from devices import DEVICES  # noqa: E402
from paths import UL_PYTHON  # noqa: E402



def main() -> int:
    device, task = sys.argv[1], sys.argv[2]
    if gap := make_tasks.SDK_GAPS.get(device, {}).get(task):
        print(f"{device}/{task}: not generated (SDK gap): {gap}")
        return 0
    ref = pathlib.Path(sys.argv[3]) if len(sys.argv) > 3 else ROOT / "references" / device / f"{task}.py"
    if len(sys.argv) <= 3 and not ref.exists():
        ref = ref.with_name(f"{task}.INFEASIBLE.md")      # infeasible pairs have a refusal, not a protocol
    files = make_tasks.render_task(task, DEVICES[device], "unused", allow_missing=True)
    with tempfile.TemporaryDirectory() as tmp:
        folder = pathlib.Path(tmp)
        for rel, content in files.items():
            if rel.startswith("tests/") or rel.startswith("environment/data/"):
                path = folder / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content if isinstance(content, bytes) else content.encode())
        app = folder / "app"
        app.mkdir()
        if ref.exists():
            if ref.suffix == ".md":
                (app / "INFEASIBLE.md").write_text(ref.read_text())
            else:
                (app / "protocol.py").write_text(make_tasks.solution_code(ref.read_text()))   # the oracle, canary-free
        env = dict(os.environ, TESTS_DIR=str(folder / "tests"), PROTOCOL_PATH=str(app / "protocol.py"),
                   VERIFIER_OUT=str(folder / "out"), DATA_DIR=str(folder / "environment/data"), SKIP_JUDGE="1", T2WL_LOCAL_VENV="1",
                   UL_PYTHON=UL_PYTHON)
        proc = subprocess.run([env["UL_PYTHON"], str(folder / "tests/grade.py")], env=env, capture_output=True, text=True)
        result = folder / "out/result.json"
        if not result.exists():
            print(proc.stdout[-2000:], proc.stderr[-3000:])
            return 1
        r = json.loads(result.read_text())
    rewards = r["rewards"]
    print(f"{device}/{task}: deterministic_reward={rewards.get('deterministic_reward', rewards['reward'])} "
          f"error={r.get('error')} verdict={r.get('verdict', '')}")
    for key in ("lint", "traps"):
        if r.get(key):
            print(f"  {key}: {r[key]}")
    if r.get("simulation") and not r["simulation"].get("ok", True):
        print("  simulation:", r["simulation"].get("error"), "\n", (r["simulation"].get("traceback") or "")[-1500:])
    for c in r.get("checks", []):
        if not c["pass"]:
            print(f"  FAIL {c['name']}: {c['detail'][:300]}")
    for n in r.get("not_applicable", []):
        print(f"  n/a  {n}")
    return 0 if rewards.get("deterministic_reward") == 1.0 else 1


if __name__ == "__main__":
    sys.exit(main())
