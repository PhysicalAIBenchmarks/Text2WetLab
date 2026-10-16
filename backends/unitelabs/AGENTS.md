# AGENTS.md

Text2WetLab on the UniteLabs liquid handling SDK: the benchmark's tasks, grader layers and Harbor harness, run against
the SDK's simulated liquid handlers (STAR, Vantage, Bravo, Biomek, EVO). See `README.md` for the full picture. Commands
run from `backends/unitelabs/`.

## Layout

- `../../`: the benchmark (tasks, `eval/`, `paper2protocol/`). Generic grader changes go there, with tests in
  `../../tests/`, and must leave every OT-2 oracle reward unchanged (`scripts/check_oracle_rewards.py`).
- `ul/`: our code. `grade.py` is the verifier (lint → traps → simulator → checks → judge); `gate.py`,
  `check.py`, `runner.py`, `lineage_events.py`, `record.py` and `devices.py` are the layers it uses; `make_tasks.py` generates the tasks.
- `references/<device>/<task>.py` or `<task>.INFEASIBLE.md`: the oracle for every generated device and task pair.
- `tasks/<device>/<task>/`: **generated**. Never edit by hand; change the sources and regenerate.
- `docker/`: the base image. `docker/BASE_IMAGE` holds the tag the tasks build `FROM`.
- `EVENTS.md`: the run events the grader reads, and how `lineage_events.py` makes them from the SDK's lineage stream.
- `tests/`: pytest for the gate, checks, lineage adapter, feasibility, honeypots, leaderboard and session_run. The contamination rule
  and the rest of spec_check's backend contract are tested in `../../tests/test_spec_check_backends.py`.
- `jobs/`, `runs/`, `results/`: local Harbor output, session runs and summaries, all git-ignored.

## Commands

```bash
uv run ul/make_tasks.py            # regenerate tasks/ after changing ul/, references/ or the benchmark
uv run ul/make_tasks.py --check    # CI: fails if tasks/ is stale
uv run pytest -q                        # unit tests, no SDK or Docker needed
uv run ul/validate_ref.py <device> <task> [protocol.py]   # grade one protocol locally (needs the SDK venv, see ul/paths.py)
SKIP_JUDGE=1 uvx --from harbor==0.24.0 harbor run -y -p tasks/<device> -a oracle -o jobs   # oracle in Docker
uv run ul/adversarial.py [--docker]   # cheats on every reference; no attack may score 1.0
$UL_PYTHON ul/lineage_fixtures.py [--write]   # SDK lineage + adapter output per reference, pinned
# model run without an API key (subscription token in .env): agents in Harbor, judge here; see README
CLAUDE_FORCE_OAUTH=1 SKIP_JUDGE=1 harbor run --env-file .env -y -p tasks/<device> -a claude-code -m anthropic/<model> -k 2 -o jobs --job-name <name>
uv run ul/session_run.py import-job jobs/<name> runs/<name> && uv run ul/session_run.py judge runs/<name> && uv run ul/session_run.py score runs/<name>
```

## Rules

- After any change under `ul/`, `references/` or the benchmark's `tasks/`, `eval/` or `paper2protocol/`, regenerate
  `tasks/` and commit both together.
- Every reference must keep `deterministic_reward` 1.0 (locally with `validate_ref.py`, and the Harbor oracle on all
  five devices), and `adversarial.py` must report no holes. Grader changes are not done until all three pass.
- Changing `runner.py`, `record.py`, `lineage_events.py`, `devices.py`, `docker/simulate` or `docker/Dockerfile.base` changes the image:
  rebuild with `docker/build_base.sh <python-lib> <python-sdk> <labware> <docs> > docker/BASE_IMAGE`, then regenerate tasks.
- Grader files are vendored into each task's `tests/` and import siblings from their own folder; keep them free of
  repo-relative imports beyond the existing in-repo fallbacks.
- Stay comparable with the OT-2 benchmark: same tasks, rubric, weights and reward scheme. New dimensions (e.g. workflow
  structure) go in a separate score, never into the main reward.
- Infeasible pairs live in `make_tasks.FEASIBILITY` (reason + accepted patterns); keep them in line with the
  reference `INFEASIBLE.md` files. Only hardware limits count: something the SDK can't do yet goes in
  `make_tasks.SDK_GAPS` (the pair is not generated), never in `FEASIBILITY`.
- Anything that loosens a gate (lint whitelist, traps, integrity check) needs a test in `tests/test_gate.py`
  showing the attack it was meant to stop is still refused.
- Secrets (`ANTHROPIC_API_KEY`, `OPENROUTER_API_KEY`, `CLAUDE_CODE_OAUTH_TOKEN`) live in `.env`, which is
  git-ignored. Never print or commit them. `jobs/` and `runs/` hold agent transcripts and the judge prompts (which
  embed the reference solutions): also ignored, never commit them.
- The base image contains the SDK wheel: never push it to a public registry or repo. The docs it snapshots are public
  (docs.unitelabs.io); the SDK packages and registry credentials are not.
