"""Build model_comparison.html from rounds.json + errors.json (run collect.py and classify.py first)."""
import json, collections, html, pathlib

HERE = pathlib.Path(__file__).parent
rounds = json.load(open(HERE / "rounds.json"))
errors = json.load(open(HERE / "errors.json"))

MODELS = ["opus-5-5", "sonnet-5-5", "fable-5-1"]
NAMES = {"opus-5-5": "Opus 5.5", "sonnet-5-5": "Sonnet 5.5", "fable-5-1": "Fable 5.1"}
ROUND_IDS = ["R1", "R2", "R3", "R4", "R5", "R6", "R7"]
ROUND_DESC = {r["round"][:2]: r["round"][3:] for r in rounds}
BINARY = ["R3", "R4", "R5", "R6", "R7"]  # rounds with the binary 5-item judge

def m(r): return r["model"].replace("claude-", "")

# mean reward per model per round
trend = {mod: [] for mod in MODELS}
for rid in ROUND_IDS:
    for mod in MODELS:
        xs = [r for r in rounds if r["round"][:2] == rid and m(r) == mod]
        trend[mod].append(round(sum(r["reward"] or 0 for r in xs) / len(xs), 3) if xs else None)

# latest real run = R7
latest = {mod: [r for r in rounds if r["round"][:2] == "R7" and m(r) == mod] for mod in MODELS}
tiles = []
for mod in MODELS:
    xs = latest[mod]
    tiles.append(dict(model=mod, mean=sum(r["reward"] for r in xs) / len(xs), cost=sum(r["cost"] or 0 for r in xs),
                      tok=sum((r["tok_in"] or 0) + (r["tok_out"] or 0) for r in xs), dur=sum(r["dur"] or 0 for r in xs)))

# cost per trial across all 7 multi-model rounds
cost_all = {mod: [r["cost"] for r in rounds if m(r) == mod and r["round"][:2] in ROUND_IDS and r["cost"]] for mod in MODELS}

# error matrix: unique (round, model, task, tag) in binary rounds
seen = {}
for e in errors:
    if e["round"] in BINARY:
        for t in e["tags"]:
            seen.setdefault((t, e["model"]), {})[(e["round"], e["task"])] = e
tags = sorted({t for t, _ in seen}, key=lambda t: -sum(len(seen.get((t, mo), {})) for mo in MODELS))
matrix = [dict(tag=t, cells=[dict(model=mo, n=len(seen.get((t, mo), {})),
                                  ex=[f"{k[0]} {v['task']}: {v['evidence'][:220]}" for k, v in sorted(seen.get((t, mo), {}).items())][:3])
                             for mo in MODELS]) for t in tags]

# task x model mean reward over binary rounds
tasks = sorted({r["task"] for r in rounds if r["round"][:2] in BINARY and r["task"] != "rna-extraction"})
taskgrid = []
for t in tasks:
    row = []
    for mod in MODELS:
        xs = [r["reward"] for r in rounds if r["round"][:2] in BINARY and m(r) == mod
              and (r["task"] == t or (t == "opentrons-rna-extraction" and r["task"] == "rna-extraction"))]
        row.append(round(sum(xs) / len(xs), 2) if xs else None)
    taskgrid.append(dict(task=t, vals=row))

LAYERS = [("Reward-hack trap", lambda r: bool(r["hack"])), ("Agent error / timeout", lambda r: bool(r["exception"])),
          ("Simulator (opentrons_simulate)", lambda r: r["sim_pass"] is not None and r["sim_pass"] < 1),
          ("Deterministic checks", lambda r: r["checks_frac"] is not None and r["checks_frac"] < 1),
          ("Critical-failure cap", lambda r: bool(r["critical"])), ("LLM judge rubric item", lambda r: bool(r["failed_items"]))]
layers = [dict(layer=name, vals=[sum(1 for r in rounds if r["round"][:2] == rid and f(r)) for rid in ROUND_IDS]) for name, f in LAYERS]
layers.append(dict(layer="Trials that lost any points", vals=[sum(1 for r in rounds if r["round"][:2] == rid and (r["reward"] or 0) < 1) for rid in ROUND_IDS]))
n_per_round = [sum(1 for r in rounds if r["round"][:2] == rid) for rid in ROUND_IDS]

table = [dict(round=e["round"], model=NAMES[e["model"]], task=e["task"], item=e["item"], tags=", ".join(e["tags"]), evidence=e["evidence"])
         for e in sorted(errors, key=lambda e: (e["round"], e["model"], e["task"]))]

DATA = dict(models=MODELS, names=NAMES, rounds=ROUND_IDS, round_desc=ROUND_DESC, trend=trend, tiles=tiles,
            cost_all={k: dict(mean=sum(v) / len(v), n=len(v)) for k, v in cost_all.items()},
            matrix=matrix, taskgrid=taskgrid, table=table, layers=layers, n_per_round=n_per_round)

page = (HERE / "template.html").read_text().replace("/*DATA*/null", json.dumps(DATA))
(HERE.parent / "model_comparison.html").write_text(page)
print("wrote", HERE.parent / "model_comparison.html", len(table), "failure rows")
