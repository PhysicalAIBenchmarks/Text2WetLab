# Text2WetLab on the UniteLabs SDK

Which models write working liquid-handling protocols with the UniteLabs liquid handling SDK, on which instruments?
This backend runs the Text2WetLab benchmark (this repository) against the SDK's
simulated liquid handlers (Hamilton STAR and Vantage, Agilent Bravo, Beckman Biomek, Tecan Freedom EVO) with the
same tasks, the same verifier layers and the same agent harness ([Harbor](https://github.com/laude-institute/harbor) +
Claude Code) as upstream, so scores compare like for like with its OT-2 leaderboard. The output is the table on the
website: the models we recommend for use with UniteLabs, per device.

**Reproducing the scores needs UniteLabs registry credentials**, as a closed model needs an API key: the code, tasks,
references and grader are all here, but the SDK packages are not on PyPI. The Docker image contains the SDK wheel, so it
is never pushed to a public registry. The docs it snapshots are public (docs.unitelabs.io).

Every command below runs from `backends/unitelabs/`.

## The idea

The task is the same on every device. A brief gives the goal, the labware as roles ("a 96-well plate `plate`, a
reservoir `reservoir` holding 10 mL water"), the starting contents and the steps, and names the device. The agent
chooses labware classes and carriers, arranges the deck, and writes `async def run(<device>, comment)` against the
SDK, working from the shared documentation and whatever device pages or SDK source it decides to read. The grader
matches labware by identifier and kind, never by position. If the instrument cannot do the protocol (the EVO's MCA96
cannot pipette into two wells), the right answer is `/app/INFEASIBLE.md`, and the harness knows which tasks those are.

Nine of upstream's eleven tasks are used, on five devices: 44 pairs (`make_tasks.DEFAULT_TASKS`). The two RNA
extraction tasks have no IR (their grader is task-specific OT-2 run-log checks), so porting them means writing a new
task. A pair the hardware could run but the SDK cannot (Bravo heat shock: the SDK's Bravo head cannot pipette tubes)
is not generated at all (`make_tasks.SDK_GAPS`); an agent is never scored on an SDK gap.

## Layout

```
../../           the benchmark: tasks, IR, verifier (eval/), paper2protocol
ul/              the UniteLabs backend
  devices.py       one profile per device: mock, setup, modules taken away, how a deck position is named
  lineage_events.py  the backend adapter: the SDK's lineage stream (pick/drop/aspirate/dispense/mix per channel or
                   nozzle, with the physical tip, requested and moved volume) -> the events upstream's checks read;
                   no SDK import (contract: EVENTS.md)
  record.py        the deck those events refer to: labware names and geometry, the SDK's entity ids mapped to them,
                   comments, and efficiency (commands, tips, est. time)
  runner.py        runs a protocol on the device mock under `Audit.capture()` -> events (the shape upstream's checks read)
  lineage_fixtures.py  pins every reference's lineage stream and adapter output; checks it against the SDK contract
  check.py         loads a task's ir.json, deck.json and checks.json and runs eval/spec_check on the run (tip state
                   per channel, contamination per physical tip, labware matched by identifier + geometry all live there)
  gate.py          upstream's lint and reward-hacking traps, translated to the SDK (asyncio limited to scheduling)
  judge_text.py    upstream's rubric and judge prompt with the OT-2 phrases swapped for the device
  grade.py         the verifier in the sandbox: lint → traps → simulator → checks → LLM judge → reward.json;
                   checks /app/INFEASIBLE.md against the reason in tests/task.json
  brief.py         the device-agnostic brief rendered from upstream's IR (easy and paper-only tasks)
  make_tasks.py    generates tasks/<device>/<task>/ (Harbor tasks) for every device; holds the feasibility matrix,
                   the SDK gaps, and upstream's honeypot (a wrong answer key planted in /app) per pair
  validate_ref.py  grades one reference locally, no Docker
  adversarial.py   upstream's adversarial suite: cheats on every reference must not score 1.0 (local or --docker)
  leaderboard.py   jobs/ → the table, per model and device
  run_loop.py      the API loop with repair rounds, for probing docs gaps (--device, --reference)
  session_run.py   a baseline with in-session Claude Code subagents instead of Harbor (no API key; --only GLOB);
                   import-job: Harbor trials run with SKIP_JUDGE=1; judge: votes via `claude -p`
  paths.py         where the local tools find the SDK checkouts, its venv and the docs (UL_PYTHON overrides)
references/<device>/<task>.py        hand-written oracle per device (or <task>.INFEASIBLE.md where it cannot run)
EVENTS.md        the run events the grader reads (the backend contract) and how the lineage stream maps to them
tasks/<device>/<task>/               GENERATED Harbor tasks (committed; `make_tasks.py --check` in CI)
tests/           unit tests: gate, checks, lineage adapter (fixtures/lineage/), feasibility, honeypots, leaderboard,
                 session_run (`uv run pytest`; the contamination rule and the rest of spec_check's backend
                 contract: ../../tests/test_spec_check_backends.py)
docker/          the base image: SDK wheel + deps (SDK uv.lock) from the UL index, docs snapshot, claude-code,
                 `simulate`; the simulator venv /opt/ul and the grader venv /opt/grader are separate
jobs/, runs/, results/   local Harbor output, session runs and summaries (git-ignored)
```

## Run it

```bash
# 1. Base image (needs ~/.netrc for gitlab.com, the liquid-handling SDK checkout with its .venv, the unitelabs-sdk and
#    unitelabs-labware checkouts (or - for the versions the liquid-handling SDK locks), and the docs checkout)
docker/build_base.sh <python-lib> <python-sdk | -> <labware | -> <docs> > docker/BASE_IMAGE

# 2. Tasks (re-run after changing anything under ul/, references/, or the benchmark's tasks/, eval/ or paper2protocol/)
uv run ul/make_tasks.py

# 3. Oracle per device: every reference must get deterministic_reward 1.0 (no API key needed); then the cheats
SKIP_JUDGE=1 uvx --from harbor==0.24.0 harbor run -y -p tasks/star -a oracle -o jobs
uv run ul/adversarial.py --docker          # no attack may score 1.0; writes results/adversarial.json

# 4. Models (ANTHROPIC_API_KEY for the agent and the judge; ~$1–3 per trial. No key? See "Harbor agents, judged here")
for d in star vantage bravo biomek evo; do
  uvx --from harbor==0.24.0 harbor run -y -p tasks/$d -a claude-code -m anthropic/claude-sonnet-5-5 -n 3 -o jobs --ak max_budget_usd=3
done

# 5. Table (one row per model, device and judge configuration; judge errors are listed for re-judging). The oracle
#    job is the efficiency baseline.
uv run ul/leaderboard.py jobs/<job> jobs/<job> --reference jobs/<oracle job> --out results/leaderboard.json
```

Published scores use the Anthropic endpoint for the judge (`ANTHROPIC_API_KEY`). With only `OPENROUTER_API_KEY` the
same model is reached through OpenRouter; the leaderboard keeps those trials in a row of their own.

The leaderboard leads with two numbers per model and device: the judged mean (upstream's reward) and the
deterministic mean (checks only, no LLM). A Claude judge scoring Claude models is the obvious objection to a vendor's
model recommendation; the deterministic mean doesn't depend on it. It also reports infeasible pairs recognised,
efficiency (estimated run time over the reference's, for trials that passed every check), cost and outcomes. Neither
efficiency nor the deterministic mean is part of the reward.

Grading a reference or any protocol locally, without Docker:

```bash
uv run ul/validate_ref.py bravo colony-pcr-screening [path/to/protocol.py]
```

### Without Docker: in-session subagents

A baseline with no Docker and no API key: the agents and judges are Claude Code subagents launched from your own
session, and grading is the Harbor task's grader run locally. It needs the liquid-handling SDK checkout with its `.venv`
at `python-lib/` next to the Text2WetLab checkout (its unitelabs-sdk installed editable from `python-sdk/`; `UL_PYTHON`
overrides the interpreter, see `ul/paths.py`) and the docs checkout at `docs/`, next to it too.

```bash
# 1. Workspaces: one per device, task and attempt, each with brief.md, ./simulate and prompt.txt
uv run ul/session_run.py make runs/<name> --devices star bravo --tasks colony-pcr-screening --model sonnet --attempts 3

# 2. In Claude Code: one subagent per workspace, on the model named in --model, given its prompt.txt verbatim.
#    Each writes protocol.py (or INFEASIBLE.md) in its workspace and reports status, errors and docs feedback.

# 3. Grade (lint, traps, simulator, checks; no judge). Writes out/result.json and judge.md per workspace
uv run ul/session_run.py grade runs/<name> [--only '<glob>']

# 4. Judge: one headless Claude Code call (`claude -p`, no tools, your own login) per judge.md and vote, each checked
#    against the rubric and saved as vote.json, vote2.json, ... (three votes by default, as upstream). Failed replies
#    are not saved; run it again for them. A run keeps one judge model: it refuses to add votes from another.
#    (Or, by hand: one judge subagent per judge.md writing vote.json, and JUDGE_VOTES=<count> when scoring.)
uv run ul/session_run.py judge runs/<name> [--votes 3] [--jobs 4]

# 5. Table with upstream's scoring; writes runs/<name>/table.json
uv run ul/session_run.py score runs/<name>
```

`runs/` is git-ignored. These rows are not comparable with Harbor's: there is no sandbox (the prompt forbids reading
the repo, but nothing enforces it), the harness is your session's subagent, and the judge usually has fewer than
upstream's three votes. `table.json` records the harness and vote count so the two are never mixed.

### Harbor agents, judged here: a leaderboard run on a Claude subscription

**Why this exists.** Upstream's verifier calls the judge through the Anthropic SDK with an API key, inside the
sandbox. We have no API key, only a Claude subscription, and a subscription token (`claude setup-token`) is honoured
for Claude Code alone, not for the API; Harbor also hands it only to the agent, never to the verifier. Rather than
change the vendored grader (CI keeps it identical to upstream's), the judge call is moved out of the sandbox: the
agents run in Harbor on the token, the verifier runs with the judge skipped, and `judge` makes the same calls (same
model, three votes, upstream's prompt) as headless Claude Code on this machine, against the protocol the verifier
saved. Once an API key exists, drop `SKIP_JUDGE=1` and the two commands below; `ul/leaderboard.py jobs/<job>` then
reads the job directly.

Needs Harbor 0.24.0 (the subscription token is not in 0.23.0's `claude-code` agent) and the token as
`CLAUDE_CODE_OAUTH_TOKEN=...` in `.env` (git-ignored).

```bash
# 1. Agents in Harbor, judge skipped: the verifier records lint, traps, simulator and checks only
CLAUDE_FORCE_OAUTH=1 SKIP_JUDGE=1 harbor run --env-file .env -p tasks/vantage \
  -a claude-code -m anthropic/claude-sonnet-5-5 -k 2 -n 2 -y -o jobs --job-name vantage-sonnet

# 2. One workspace per trial, from the protocol and result.json Harbor's verifier saved (the grader is not rerun),
#    with judge.md where a judge is due. Re-importing a job skips the trials already there.
uv run ul/session_run.py import-job jobs/vantage-sonnet runs/vantage-sonnet

# 3. Three judge votes per protocol (the default, as upstream); then the table
uv run ul/session_run.py judge runs/vantage-sonnet
uv run ul/session_run.py score runs/vantage-sonnet
```

These rows have a real sandbox, Harbor's agent harness and upstream's judge model and vote count; what differs from a
keyed Harbor run is only where the judge call is made. `table.json` records `"agent": "harbor"` and the judge
(`judge.json`: model, votes). Keep them in their own `runs/<name>`, apart from session-agent runs.

## How a task is graded

Same six layers as the OT-2 benchmark (`../../README.md` §3), on the device:

1. **Lint** (`protocol_lint.py` with the `unitelabs` import whitelist): reaching into SDK internals or the mock,
   `asyncio` beyond scheduling (subprocesses, sockets), or a protocol over 64 KB → 0.
2. **Traps** (`gate.py`): canary, judge-aimed text, network, `/data` edits, integrity of both venvs (every
   RECORD hash, no added `.pth`), and upstream's honeypot: `/app/solution_hint.py` is the reference with every volume
   20% too high, and copying it (or anything over 90% similar) → 0.
3. **Simulator**: the protocol must run on the device mock (`runner.py`, 300 s, no API keys in its environment) → 0 if
   it raises. What the robot did is the SDK's own lineage stream, which the protocol cannot reach (gate) and must not
   empty: pipetting commands with no aspirate or dispense recorded fail the run.
4. **Deterministic checks** (`check.py` → `eval/spec_check.py`): every labware present by identifier and of the right
   kind (by geometry: family, well count, well volume), end-state volume of every well, tip before aspirate, no
   overdispense, no aspirate from empty, no tip left on, no cross-contamination; per channel or nozzle.
   Contamination follows the physical tip, so a used tip put back in its rack and picked up again still carries what
   it touched (without tip identities, every pick is a fresh tip). Two exceptions to the rule: dispensing into the task's waste is
   never contamination, and a tip whose only destination so far is one well may move that well's contents (adding
   water and then moving the eluate with the same tip).
5. **LLM judge** (upstream `judge_layer`, Sonnet 5.5, majority of 3): the rubric with device wording; 75% core, 25% task.
   As upstream, the judge reads the reference protocol as "one valid implementation" and is told not to reward
   resemblance to it; kept unchanged for comparability, including on paper-only tasks.
6. **Critical cap**: a failed critical check caps the reward at 0.3.

Infeasible pairs (`make_tasks.FEASIBILITY`): an `/app/INFEASIBLE.md` that names the limitation scores 1.0; an empty
one or one giving another reason scores 0; a protocol for a task the device cannot run scores 0 (still graded, for
the record); declaring a feasible task infeasible scores 0. The leaderboard reports infeasible pairs in their own
column, apart from the protocol mean.

`result.json` records the image's SDK and docs commits, every installed package in both venvs, and the judge
configuration, so every score says what it measured and how.

## What the agent sees

`instruction.md` (the brief), `/docs/content/` (the full docs snapshot; the brief points only at the shared pages),
the installed SDK source, `simulate /app/protocol.py`, which prints the run log or the error, never the checks, and
the planted `/app/solution_hint.py`.
`tests/` is copied in only after the agent stops.
