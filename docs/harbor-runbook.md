# Harbor runbook: running Text2WetLab tasks with an Anthropic API key

Status: research only. Nothing below was executed against a task, an agent, the Anthropic API or a paid sandbox.
Harbor 0.23.0 was run via `uvx --from harbor` only to read `--help`, read its source (uv cache), and run `--dry-run` preflights that exited at the "Docker not installed" / "Daytona key missing" checks.

Sources:
- Harbor repo: https://github.com/laude-institute/harbor
- Docs index: https://docs.harborframework.com/llms.txt
- Quick start: https://docs.harborframework.com/getting-started/quick-start.md
- Env-var flow: https://docs.harborframework.com/jobs/environment-variables.md
- Sandboxes: https://docs.harborframework.com/sandboxes/pre-integrated-sandboxes.md
- Task config / verifier / environment: https://docs.harborframework.com/tasks/configuration.md, /tasks/verifier.md, /tasks/environment.md
- "(src)" below = Harbor 0.23.0 Python source read locally.

## 1. Decision summary

- Only `tasks/opentrons-rna-extraction/harbor/` is Harbor-runnable today. The other six tasks are not Harbor tasks (see section 7); they need a wrapper before Harbor can run them.
- Harbor does not need local Docker: the default is Docker, but `-e daytona|modal|e2b|runloop|vercel|...` run in cloud sandboxes. Recommended path from this Mac: Daytona or Modal (both support the task's network allowlist), with `harbor[daytona]` or `harbor[modal]` installed. Alternative: install Docker (Colima or Docker Desktop) and use the default environment, which is free of sandbox fees and the simplest to debug.
- Setup cost: install Harbor (minutes, `uv tool install`), one sandbox account + key (Daytona/Modal), image build of about 1 GB (Dockerfile pulls apt, npm, pip; `build_timeout_sec = 1200`). No code changes needed for the RNA task.
- Order of work: dry-run, then oracle (costs one judge call, about one Sonnet request), then one model trial with a budget cap, then more.
- The Anthropic key is needed by the agent (claude-code) and by the verifier (LLM judge). Oracle runs need it only for the judge.

## 2. Step-by-step commands (from docs and `--help`; NOT executed)

Install (Harbor requires Python >=3.12; uv manages that):

```bash
uv tool install harbor                  # local Docker or Apple container
uv tool install "harbor[daytona]"       # + Daytona SDK
uv tool install "harbor[modal]"         # + Modal SDK
uv tool install "harbor[cloud]"         # all pre-integrated sandboxes
harbor --version                        # 0.23.0 seen via uvx
```

Isolated, no install: `uvx --from harbor harbor <args>` (for cloud extras: `uvx --from "harbor[daytona]" harbor ...`).

Load the key into the Harbor process without printing it. Either `export ANTHROPIC_API_KEY=...` in the shell, or `--env-file <path>` (flag exists in `harbor run --help`: "Path to a .env file to load into environment"). Do not commit or echo the file.

(a) Validate the task with the oracle (runs solution/solve.sh, then the verifier):

```bash
harbor run -p tasks/opentrons-rna-extraction/harbor -a oracle                 # Docker
harbor run -p tasks/opentrons-rna-extraction/harbor -a oracle -e daytona      # cloud
```

Task README expects the oracle reward to be about 0.94. The README path matches this repo (`tasks/opentrons-rna-extraction/harbor`).

(b) Model agent (claude-code with a Claude model; model string is `provider/model`):

```bash
harbor run -p tasks/opentrons-rna-extraction/harbor -a claude-code \
  -m anthropic/claude-sonnet-5-5 -e daytona \
  --ak max_turns=40 --ak max_budget_usd=3 -k 1 -n 1
```

claude-code agent kwargs seen in src (`harbor agent schema claude-code` prints them): `max_turns`, `max_budget_usd`, `reasoning_effort`, `max_thinking_tokens`, `allowed_tools`, `disallowed_tools`, `permission_mode` (default `bypassPermissions`). Whether `--ak max_budget_usd=...` is passed through as `--max-budget-usd` was read in source, not run.

(c) Whole directory as a dataset: `-p` accepts a task dir or a directory of task dirs.

```bash
harbor run -p tasks -a claude-code -m anthropic/claude-sonnet-5-5 -e daytona -n 2
# filters: -i/--include-task-name GLOB, -x/--exclude-task-name GLOB, -l/--n-tasks N
```

Today `-p tasks` would find only one valid task (directories without `environment/` are skipped by `Task.is_valid_dir`, src; skipping behaviour not run).

(d) Dry-run, config echo, and reading results:

```bash
harbor run -p tasks/opentrons-rna-extraction/harbor -a claude-code -m anthropic/claude-sonnet-5-5 --print-config
harbor run ... --dry-run          # validates config and preflight; no trials. Verified to stop at the env preflight here.
harbor view ./jobs                # web UI over trajectories
harbor job resume <job_dir>       # resume an interrupted job
harbor job regrade <job_dir>      # re-run verification only (re-calls the judge: costs money)
ls jobs/<job>/<trial>/verifier/   # reward.json, judge.json, events.json, protocol.py, test-stdout
cat jobs/<job>/<trial>/verifier/reward.json
```

Results go to `./jobs` by default (`-o/--jobs-dir`). Each trial dir holds `result.json`, agent logs (claude-code writes `agent/` logs and session trajectory) and `verifier/`. Exact file names other than the four the task README lists were not verified.

Static task checks without any model or Docker (safe, free):

```bash
uvx --from harbor harbor task schema        # task.toml JSON schema
```

Warning: `harbor check <task>` launches claude-code (default model claude-sonnet-4-6) in a sandbox to review the task. That spends API money; do not run it casually.

## 3. Environment options

Names from `harbor run --help` (`-e`). Credentials were read from src; cost models are generic provider knowledge, not verified.

| `-e` value | Needs | Task allowlist supported (src) | Mac without Docker? | Cost model |
|---|---|---|---|---|
| `docker` (default) | Docker daemon | yes (egress control, src) | No (not installed here) | Free; local CPU/RAM (task asks 4 CPU, 8 GB) |
| `apple-container` | Apple silicon, `container` CLI from github.com/apple/container | not declared in src; unverified | Yes (arm64 Mac, no Docker) | Free; macOS version requirements unverified |
| `podman` | podman | unverified | Needs podman | Free |
| `daytona` | `harbor[daytona]`, `DAYTONA_API_KEY` (or JWT + org id) in the Harbor process | yes (allowlist hostnames) | Yes | Usage-based sandbox billing; account signup, free credits possible (unverified) |
| `modal` | `harbor[modal]`, `modal token new` or `MODAL_TOKEN_ID` + `MODAL_TOKEN_SECRET` | yes | Yes | Usage-based; free monthly credit tier exists (unverified) |
| `e2b` | `harbor[e2b]`, `E2B_API_KEY` | yes | Yes | Usage-based per sandbox-second |
| `runloop` | `harbor[runloop]`, `RUNLOOP_API_KEY` | yes | Yes | Usage-based |
| `vercel` | `harbor[vercel]`, Vercel credentials | yes | Yes | Usage-based |
| others (`ec2`, `gke`, `skypilot`, `islo`, `beam`, `blaxel`, ...) | cloud accounts | varies | Yes | varies |

The choice is passed with `-e <name>`; provider-specific options with `--ek key=value`. Provider credentials stay in the Harbor process; the docs say not to forward them into the sandbox.
Our task uses `network_mode = "allowlist"`, so pick an environment whose capability list includes the allowlist; if the chosen one lacks it, Harbor should refuse or warn (behaviour not tested).

## 4. API-key flow (text diagram)

```
Mac shell:  export ANTHROPIC_API_KEY  (or harbor ... --env-file .env)
     |
     v
[Harbor process on the Mac]  also holds DAYTONA_API_KEY / MODAL_* (never forwarded to the sandbox)
     |
     |-- agent phase ----------------------------------------------------------
     |     claude-code agent reads ANTHROPIC_API_KEY from: --ae/--agent-env  >  host os.environ   (src: agents/base.py _env_sources)
     |     -> injected into the `claude` process env inside the sandbox
     |     -> reaches api.anthropic.com (allowlisted). Agent can read its own env (bypassPermissions).
     |     optional: --ae ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}   ANTHROPIC_BASE_URL honored too
     |
     |-- agent finishes; /tests uploaded to the same sandbox (hidden until now)
     |
     `-- verifier phase -------------------------------------------------------
           task.toml [verifier] env = { ANTHROPIC_API_KEY = "${ANTHROPIC_API_KEY}" }
           -> resolve_env_vars() reads the HOST env (error if unset: "not found in host environment")
           -> set only on the `bash /tests/test.sh` exec
           -> grade.py's anthropic client reads ANTHROPIC_API_KEY (judge call)
           -> grade.py runs the agent's protocol with a scrubbed env (PATH, HOME, LANG, LC_ALL only), so protocol.py cannot see the key
```

- Exact names: `ANTHROPIC_API_KEY` (also accepts `ANTHROPIC_AUTH_TOKEN`, `ANTHROPIC_BASE_URL`, `CLAUDE_CODE_OAUTH_TOKEN` with `CLAUDE_FORCE_OAUTH=1`). Flags: `--ae KEY=VALUE` (agent only), `--ve KEY=VALUE` (verifier only), `--env-file`.
- Because the task.toml already declares the verifier env, you do not need `--ve`. The host variable must exist when Harbor starts, even for the oracle agent.
- What leaks where: the agent holds the real key in its process env and could exfiltrate it to any allowlisted host (only `api.anthropic.com` and `registry.npmjs.org`, so the main channel is the Anthropic API itself or an npm publish, which would need credentials). Trial logs and the claude-code session transcript may record tool output; Harbor persists sensitive env as `${VAR}` or redacts (src: `templatize_sensitive_env`), but file contents or command output the agent prints (e.g. `env`) are not redacted. Review `jobs/` before sharing or `harbor upload`.
- `[environment] network_mode = "allowlist"` with `allowed_hosts` limits sandbox egress to those hosts (applied by the provider: Docker egress control, Daytona, Modal, E2B, Runloop). The verifier inherits the same allowlist unless `[verifier]` overrides it, which is why the judge can reach `api.anthropic.com`. `--allow-agent-host` and `--allow-environment-host` extend it per run.
- `[verifier] env` only affects the verifier exec; `[environment] env` or `--ae` affect other phases.

## 5. Cost and safety controls

| Control | How |
|---|---|
| Agent wall-clock | task.toml `[agent] timeout_sec = 2400`; scale with `--agent-timeout-multiplier` or `--timeout-multiplier` |
| Verifier wall-clock | `[verifier] timeout_sec = 1200`; `--verifier-timeout-multiplier` |
| Build | `build_timeout_sec = 1200`; `--environment-build-timeout-multiplier` |
| Turns / spend (claude-code) | `--ak max_turns=N`, `--ak max_budget_usd=X` (src: ClaudeCodeOptions) |
| Reasoning cost | `--ak reasoning_effort=low|medium|high|xhigh|max`, `--ak max_thinking_tokens=N` |
| Concurrency | `-n/--n-concurrent` (default 4; set 1 at first); `--n-concurrent-agents` (local only) |
| Attempts / retries | `-k/--n-attempts` (default 1), `-r/--max-retries` (default 0). Retries re-spend; keep 0 |
| Sandbox cleanup | `--delete` is the default; leave it on so cloud sandboxes stop billing |
| Dry run | `--dry-run`, `--print-config` (no trials) |
| Cost estimate | No built-in dollar estimate found. Approach: run 1 trial with `max_budget_usd` set, read token usage from the trial `result.json`/agent logs, multiply by Anthropic list price, then scale by trials. Budget per trial is bounded by `max_budget_usd` + one judge call (up to 3 retries of a prompt containing paper + reference + protocol, 4000 max output tokens each) |
| Verification-only reruns | `harbor job regrade` re-calls the judge: not free |

The task README reports a 27-trial sweep over 9 models; its per-trial cost is not stated.

## 6. Pre-flight checklist

1. `uv tool install "harbor[daytona]"` (or modal) succeeds; `harbor --version` prints.
2. Decide the environment. Docker: install Colima/Docker Desktop and `docker info` works. Cloud: key exported in the Harbor shell only.
3. `ANTHROPIC_API_KEY` exported in the same shell (or `--env-file`); never print it; confirm with a free `count_tokens` call, as done earlier.
4. `harbor run -p tasks/opentrons-rna-extraction/harbor -a oracle <env flags> --dry-run` passes preflight.
5. Set a spend cap on the Anthropic console key/workspace in addition to `--ak max_budget_usd`.
6. Start with `-n 1 -k 1 -r 0`, then oracle, then one model trial.
7. Check the judge model id `claude-sonnet-5-5` is available to the key (grade.py hard-codes it; a bad id gives `judge_error=1` and reward 0, not a crash).
8. Confirm the sandbox gets deleted afterwards (provider dashboard).
9. After the run, grep `jobs/` for the key prefix before sharing logs.

## 7. What a Harbor task needs, and what our tasks lack

Required by `Task.is_valid_dir` / loader (src: models/task/task.py):
- `task.toml` that validates as `TaskConfig`, with `[task] name` in `org/name` format.
- `instruction.md`.
- `environment/` directory (Dockerfile or `docker_image` in `[environment]`).
- `tests/test.sh` (verifier entry point) that writes `/logs/verifier/reward.txt` (one float) or `reward.json` (numeric values only).
- Optional: `solution/solve.sh` (for oracle).

Verified locally with Harbor's own `TaskConfig` parser:
- `tasks/opentrons-rna-extraction/harbor/task.toml` parses; baseline = allowlist [api.anthropic.com, registry.npmjs.org]; verifier env keys = [ANTHROPIC_API_KEY].
- `tasks/ecoli-heat-shock-transformation/task.toml` FAILS validation: `task.name` must be `org/name`, got `ecoli-heat-shock-transformation`. With the name fixed to `x/...`, the extra `[checks]` table and `[metadata]` did not fail.

Our six other tasks (`a1-a12-100ul`, `ampure-bead-cleanup`, `colony-pcr-screening`, `ecoli-heat-shock-transformation`, `golden-gate-assembly`, `split-200ul-two-wells`; I inspected two of them) contain only `instruction.md`, `ir.json`, `assumptions.md`, `task.toml`. Missing:
- `environment/` (Dockerfile with Opentrons 7.5.0 on Python 3.10, plus a place for the agent to write output)
- `tests/test.sh` (+ a grader; for the two with `eval/spec_check.py`, a copy or mount of `eval/` and the IR, and a reward writer)
- `solution/solve.sh` (optional, for oracle)
- `task.toml` with `org/name` and `[verifier]`/`[agent]` timeouts
- Their `instruction.md` presumably does not say where to write the output, since the RNA task uses `/app/protocol.py`.
The grader can be deterministic (no API key in the verifier) for the tasks that have `spec_check.py`. Not designed here.

## 8. Findings specific to tasks/opentrons-rna-extraction/harbor/

- Pins exist: `@anthropic-ai/claude-code@2.1.288`, `node@22.22.0` on npm and `anthropic==0.72.0` and `opentrons==7.5.0` on PyPI (checked with read-only registry queries). Dockerfile uses `python:3.10-slim-bookworm`; Opentrons 7.5.0 is a pure-Python wheel, matching our simulator requirement. Its dependencies (e.g. `pydantic<2`, numpy, jsonschema) building on arm64 Linux was not verified; a Mac arm64 Docker build will pull arm64 images, a cloud sandbox is usually amd64.
- Harbor will see claude-code 2.1.288 already installed; it only reinstalls if the version Harbor requests differs. Harbor 0.23.0 may request a different or unpinned version, in which case it runs `npm install -g` inside the sandbox (registry.npmjs.org is allowlisted, which is why). Not verified.
- `allowed_hosts` has only two hosts. Claude Code may try telemetry/update hosts, which will be blocked; normally non-fatal. If a trial hangs at startup, try `--allow-agent-host` or env `DISABLE_TELEMETRY`/`DISABLE_AUTOUPDATER` via `--ae` (unverified).
- `instruction.md` says no internet except the model API: consistent with the allowlist. Agent cannot fetch Opentrons docs; this is intended.
- `grade.py`: key read from `ANTHROPIC_API_KEY` via `anthropic.Anthropic()`; model `claude-sonnet-5-5`; 3 retries; any judge failure yields `judge_error=1` and `reward=0` with no exception, so a missing/blocked key looks like a score of 0 (check `judge.json` `judge.error`). `reward.json` contains only numeric values, which satisfies Harbor's reader.
- `grade.py` reads `/tests/instruction.md`, which Harbor does not upload (it uploads `tests/`); the fallback string "(see paper)" is used, so the judge never sees the task text unless `tests/instruction.md` exists. Not present in `tests/`. Surprise, mild.
- `test.sh` calls `python /tests/grade.py`; in the image the default `python` is 3.10 with `anthropic` installed system-wide. The simulator is in `/opt/ot` (separate venv), invoked via `/opt/ot/bin/python`. Fine, but a different base image would break this.
- Verifier shares the agent's sandbox (no separate verifier environment configured), so `/app/protocol.py` is whatever the agent left, and the agent's other processes are finished. Suspicious tokens only set a flag (`suspicious_code`), not a penalty.
- `/tests/__pycache__` exists in the repo tree; harmless.
- Oracle reward is documented as 0.94, not 1.0, because the judge is stochastic; do not treat other values as failure without reading `judge.json`.
- The task README run example sets `-e modal` and `-n 3 -k 3` (9 model sessions at once). Do not copy that initially.
- README says Python 3.12+ is needed: that is Harbor's own requirement (host side), not the image's.

## 9. Risks of running agents with a real key

1. The agent runs with `bypassPermissions` and has the real key in env; it can print it into logs/transcripts. Use a dedicated, spend-capped key/workspace for benchmark runs.
2. Egress is limited only if the provider enforces the allowlist; confirm the sandbox provider supports it, otherwise the agent has open internet with the key.
3. Runaway spend: default `max_turns`/budget are unset; default concurrency is 4; `-k` and `-r` multiply cost. Always set `--ak max_budget_usd`, `-n 1`, and an Anthropic-side limit.
4. Judge cost is per verification, including oracle runs and `harbor job regrade`.
5. Leaving a cloud sandbox running if Harbor is killed; check the provider dashboard.
6. Sharing: `--upload`, `harbor upload` or committing `jobs/` publishes transcripts; they may hold the key or the hidden grader.
7. A model that games the grader: grade.py flags some tokens but the agent runs before `/tests` are uploaded, so it cannot read `reference_protocol.py` (as designed).
8. The simulator gate runs agent-written Python in the sandbox with a scrubbed env, but with the allowlisted network; no key exposure, but it is code execution of model output.
9. Do not `harbor check` or `harbor analyze` casually; they invoke LLMs.

## 10. What I could not verify

- Any real run: oracle score, model score, per-trial cost, time to build the image, whether the image builds on arm64 or amd64.
- Whether Daytona/Modal/E2B actually enforce the allowlist for this task, and their prices/free tiers (generic knowledge only; credential names are from source).
- Whether `--ak max_budget_usd=...` is honored end to end, and where cost/token usage is recorded in `result.json`.
- Whether Harbor 0.23.0's requested Claude Code version matches the Dockerfile pin (could trigger an install at trial start).
- Whether blocked Claude Code telemetry hosts cause hangs under the two-host allowlist.
- Whether `claude-sonnet-5-5` and `anthropic/claude-opus-5-5` model ids are valid for this key (only count_tokens was verified, per the brief).
- Behaviour of `apple-container` with an allowlist task (not declared in source; likely unsupported).
- `harbor run -p tasks` skipping invalid directories without error.
- Docs pages for `tasks/configuration.md`, `tasks/verifier.md`, `jobs/run-a-job.md` were not read in full; claims come from `--help` and source.
- Where Harbor writes each file in `jobs/<job>/<trial>/` beyond what the task README says.
