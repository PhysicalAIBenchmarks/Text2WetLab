"""README figures for the 2026-10-07 run (all 11 tasks) and the grader validation.

    uv run --no-project --with matplotlib python docs/preprint/make_run_figures.py

Reads results/runs/2026-10-07-openrouter/<model>/<task>/{trial,grader}.json and results/adversarial.json;
writes docs/preprint/figures/run_rewards.png ... grader_validation.png. Same style as make_figures.py.
"""
import collections, json, pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import Patch

ROOT = pathlib.Path(__file__).resolve().parents[2]
RUN = ROOT / "results/runs/2026-10-07-openrouter"
OUT = ROOT / "docs/preprint/figures"
OUT.mkdir(parents=True, exist_ok=True)

MODELS = ["claude-sonnet-5.5", "claude-opus-5.5", "claude-fable-5.1"]
NAME = {"claude-sonnet-5.5": "Sonnet 5.5", "claude-opus-5.5": "Opus 5.5", "claude-fable-5.1": "Fable 5.1"}
COL = {"claude-opus-5.5": "#2a78d6", "claude-sonnet-5.5": "#eb6834", "claude-fable-5.1": "#1baf7a"}  # as make_figures.py
INK, INK2, MUTED, GRID, REFUSE = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#d9d7cf"
SCORE = LinearSegmentedColormap.from_list("score", ["#b8321e", "#eda100", "#f4f1e6", "#7fb8e6", "#2a78d6"])

plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
    "font.size": 9, "axes.edgecolor": "#c3c2b7", "axes.linewidth": 0.8, "axes.labelcolor": INK2,
    "xtick.color": INK2, "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False,
    "axes.titleweight": "bold", "axes.titlesize": 10, "axes.titlelocation": "left", "legend.frameon": False,
    "savefig.dpi": 300, "savefig.bbox": "tight", "savefig.facecolor": "white",
})

def panel(ax, letter): ax.text(-0.14, 1.06, letter, transform=ax.transAxes, fontsize=13, fontweight="bold", va="bottom")
def ygrid(ax): ax.yaxis.grid(True, color=GRID, lw=0.6); ax.set_axisbelow(True)
def xgrid(ax): ax.xaxis.grid(True, color=GRID, lw=0.6); ax.set_axisbelow(True)

trials = {}
for f in RUN.glob("*/*/trial.json"):
    t = json.loads(f.read_text())
    g = f.parent / "grader.json"
    t["grader"] = json.loads(g.read_text()) if g.exists() else {}
    trials[(f.parent.parent.name, f.parent.name)] = t
TASKS = sorted({k for _, k in trials}, key=lambda k: (k.endswith("-hard"), k))
EASY = [k for k in TASKS if not k.endswith("-hard")]
HARD = [k for k in TASKS if k.endswith("-hard")]
refused = lambda m, k: trials[(m, k)]["exception"] == "AgentSafetyRefusalError"
reward = lambda m, k: (trials[(m, k)]["rewards"] or {}).get("reward", 0.0)
answered = {m: [k for k in TASKS if not refused(m, k)] for m in MODELS}
common = [k for k in TASKS if all(k in answered[m] for m in MODELS)]
mean = lambda xs: sum(xs) / len(xs) if xs else float("nan")


# Figure 7: reward per task and model, refusals marked
fig, ax = plt.subplots(figsize=(6.4, 5.0))
rows = EASY + HARD
for i, k in enumerate(rows):
    for j, m in enumerate(MODELS):
        if refused(m, k):
            ax.add_patch(plt.Rectangle((j - .5, i - .5), 1, 1, facecolor=REFUSE, edgecolor="white", lw=2, hatch="////"))
            ax.text(j, i, "refused", ha="center", va="center", fontsize=8, color=INK2, style="italic")
        else:
            r = reward(m, k)
            ax.add_patch(plt.Rectangle((j - .5, i - .5), 1, 1, facecolor=SCORE(r), edgecolor="white", lw=2))
            ax.text(j, i, f"{r:.2f}", ha="center", va="center", fontsize=9, color=INK, fontweight="bold" if r == 1 else None)
ax.axhline(len(EASY) - .5, color=INK, lw=1.2)
ax.set_xlim(-.5, len(MODELS) - .5); ax.set_ylim(len(rows) - .5, -.5)
ax.set_xticks(range(len(MODELS)), [NAME[m] for m in MODELS]); ax.xaxis.tick_top()
ax.set_yticks(range(len(rows)), rows, fontsize=8.5)
ax.tick_params(length=0); [s.set_visible(False) for s in ax.spines.values()]
ax.text(len(MODELS) - .4, (len(EASY) - 1) / 2, "EASY\nstep by step", rotation=90, va="center", ha="left", fontsize=7.5, color=MUTED)
ax.text(len(MODELS) - .4, len(EASY) + (len(HARD) - 1) / 2, "HARD\npaper only", rotation=90, va="center", ha="left", fontsize=7.5, color=MUTED)
foot = "  ·  ".join(f"{NAME[m]}: {mean([reward(m, k) if not refused(m, k) else 0 for k in TASKS]):.3f}" for m in MODELS)
ax.text(1, len(rows) - .1, "Mean, refusals as 0:  " + foot, ha="center", va="top", fontsize=8, color=INK2)
fig.savefig(OUT / "run_rewards.png"); plt.close(fig)


# Figure 8: how the mean depends on refusals, and what it cost
fig, (a, b) = plt.subplots(1, 2, figsize=(9.2, 3.4), gridspec_kw={"width_ratios": [1.35, 1]})
rules = [("Refusals count as 0", lambda m: mean([0 if refused(m, k) else reward(m, k) for k in TASKS])),
         ("Tasks the model answered", lambda m: mean([reward(m, k) for k in answered[m]])),
         (f"The {len(common)} tasks all answered", lambda m: mean([reward(m, k) for k in common]))]
w = .26
for j, m in enumerate(MODELS):
    vals = [f(m) for _, f in rules]
    xs = [i + (j - 1) * w for i in range(len(rules))]
    a.bar(xs, vals, w * .92, color=COL[m], label=NAME[m])
    for x, v in zip(xs, vals):
        a.text(x, v + .012, f"{v:.2f}", ha="center", fontsize=7, color=INK2)
a.set_xticks(range(len(rules)), [r for r, _ in rules], fontsize=8)
a.set_ylim(.5, 1.04); a.set_ylabel("Mean reward"); ygrid(a); a.legend(loc="upper left", ncol=3, fontsize=8)
a.set_title("Ranking flips with how refusals are counted"); panel(a, "a")
for m in MODELS:
    cost = sum(trials[(m, k)].get("cost_usd") or 0 for k in TASKS)
    v = rules[0][1](m)
    b.scatter(cost, v, s=90, color=COL[m], zorder=3)
    nref = sum(refused(m, k) for k in TASKS)
    b.annotate(f"{NAME[m]}\n{nref} refusal{'s' * (nref != 1)}", (cost, v), xytext=(8, -4), textcoords="offset points", fontsize=8, color=INK2)
b.set_xlabel("Agent cost for all 11 tasks (USD)"); b.set_ylabel("Mean reward (refusals as 0)")
b.set_xlim(0, 8); b.set_ylim(.6, .95); ygrid(b); xgrid(b)
b.set_title("Cost against reward"); panel(b, "b")
fig.tight_layout(); fig.savefig(OUT / "run_means_cost.png"); plt.close(fig)


# Figure 9: where points were lost: deterministic risks vs judge rubric items
RISKS = [("simulator_ran", "Runs in the simulator"), ("end_state", "End-state volumes"),
         ("tip_before_aspirate", "Tip before pipetting"), ("no_overdispense", "No overdispense"),
         ("no_aspirate_from_empty_well", "No empty-well draw"), ("tip_dropped_at_end", "Tip dropped at end"),
         ("no_cross_contamination", "No cross-contamination"), ("rna", "RNA run-log checks (16)")]
def risk_of(name):
    base = name.split(":")[0].split("[")[0]       # deck_labware is recorded only when it fails: none did
    return base if base in dict(RISKS) else "rna"
passed, ran = collections.Counter(), collections.Counter()
for (m, k), t in trials.items():
    checks = t["grader"].get("checks") or []
    if isinstance(checks, dict):
        checks = checks.get("checks", [])
    for c in checks:
        passed[(m, risk_of(c["name"]))] += bool(c["pass"]); ran[(m, risk_of(c["name"]))] += 1
fig, (a, b) = plt.subplots(1, 2, figsize=(10, 3.9), gridspec_kw={"width_ratios": [1, 1]})
ys = range(len(RISKS))
for j, m in enumerate(MODELS):
    vals = [passed[(m, r)] / ran[(m, r)] if ran[(m, r)] else None for r, _ in RISKS]
    for y, v, (r, _) in zip(ys, vals, RISKS):
        if v is not None:
            a.barh(y + (j - 1) * .26, v, .24, color=COL[m], label=NAME[m] if y == 0 else None)
            if v < 1:
                a.text(v + .01, y + (j - 1) * .26, f"{passed[(m, r)]}/{ran[(m, r)]}", va="center", fontsize=7, color=INK2)
a.set_yticks(list(ys), [l for _, l in RISKS], fontsize=8); a.invert_yaxis()
a.set_xlim(0, 1.12); a.set_xlabel("Share of checks passed"); xgrid(a)
a.set_title("Deterministic checks: almost nothing fails"); panel(a, "a")
a.legend(loc="lower left", fontsize=7.5, ncol=3, bbox_to_anchor=(0, -.3))
ITEMS = ["fidelity_to_paper", "elution_recovery", "fidelity_to_task", "robot_practice"]
fails = collections.Counter()
for (m, k), t in trials.items():
    for key, v in (t["rewards"] or {}).items():
        if key.startswith("rubric_") and v == 0:
            fails[(m, key.removeprefix("rubric_"))] += 1
left = [0] * len(ITEMS)
for m in MODELS:
    vals = [fails[(m, i)] for i in ITEMS]
    b.barh(range(len(ITEMS)), vals, .6, left=left, color=COL[m], label=NAME[m])
    left = [l + v for l, v in zip(left, vals)]
b.set_yticks(range(len(ITEMS)), ITEMS, fontsize=8.5, family="monospace"); b.invert_yaxis()
b.set_xlabel("Failed rubric items (all 3 models)"); b.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(integer=True)); xgrid(b)
b.set_title("LLM judge: every lost point"); panel(b, "b")
n_other = sum(v for (m, i), v in fails.items() if i not in ITEMS)
b.text(.98, .03, f"{sum(fails.values())} failed items in all; every other item passed" + (f" (+{n_other} other)" if n_other else ""),
       transform=b.transAxes, ha="right", fontsize=7.5, color=MUTED)
fig.tight_layout(); fig.savefig(OUT / "run_where_lost.png"); plt.close(fig)


# Figure 10: grader validation: reference controls and attacks against each IR task's grader
adv = json.loads((ROOT / "results/adversarial.json").read_text())
ATT = list(dict.fromkeys(a for v in adv.values() for a in v))
SHORT = {k: k.replace("control_reference_solution", "reference solution").replace("control_api_", "reference @ API ").replace("_", " ")
         for k in ATT}
SHORT = {k: v.replace("API 2 1", "API 2.1") for k, v in SHORT.items()}
tasks = list(adv)
fig, ax = plt.subplots(figsize=(10, 4.6))
for i, k in enumerate(tasks):
    for j, a_ in enumerate(ATT):
        r = adv[k].get(a_, {"skipped": "-"})
        if "skipped" in r:
            ax.add_patch(plt.Rectangle((j - .5, i - .5), 1, 1, facecolor="#f4f3ee", edgecolor="white", lw=1.5))
            ax.text(j, i, "n/a", ha="center", va="center", fontsize=6, color=MUTED)
            continue
        v = r.get("reward") or 0.0
        ctrl = a_.startswith("control")
        face = ("#2a78d6" if v == 1 else "#b8321e") if ctrl else ("#b8321e" if v == 1 else SCORE(.5 + v * .4) if v > 0 else "#e7e5dc")
        ax.add_patch(plt.Rectangle((j - .5, i - .5), 1, 1, facecolor=face, edgecolor="white", lw=1.5))
        ax.text(j, i, "1" if v == 1 else ("0" if v == 0 else f"{v:.2f}".lstrip("0")), ha="center", va="center", fontsize=6.5,
                color="white" if ctrl or v == 1 else INK)
ax.axvline(2.5, color=INK, lw=1.2)
ax.set_xlim(-.5, len(ATT) - .5); ax.set_ylim(len(tasks) - .5, -.5)
ax.set_xticks(range(len(ATT)), [SHORT[a_] for a_ in ATT], rotation=55, ha="right", fontsize=7.5)
ax.set_yticks(range(len(tasks)), tasks, fontsize=7.5)
ax.tick_params(length=0); [s.set_visible(False) for s in ax.spines.values()]
holes = sum(1 for v in adv.values() for a_, r in v.items() if not a_.startswith("control") and r.get("reward") == 1.0)
ctrl_ok = sum(1 for v in adv.values() for a_, r in v.items() if a_.startswith("control") and r.get("reward") == 1.0)
ctrl_n = sum(1 for v in adv.values() for a_ in v if a_.startswith("control"))
ran = sum(1 for v in adv.values() for a_, r in v.items() if not a_.startswith("control") and "skipped" not in r)
ax.set_title(f"Controls: {ctrl_ok}/{ctrl_n} score 1.0    Attacks: {ran} run, {holes} scored 1.0", loc="left", fontsize=9.5)
ax.legend(handles=[Patch(color="#2a78d6", label="reference scores 1 (must)"), Patch(color="#e7e5dc", label="attack scores 0"),
                   Patch(color=SCORE(.6), label="attack: partial credit"), Patch(color="#b8321e", label="hole (attack scores 1)")],
          loc="upper left", bbox_to_anchor=(0, -.42), ncol=4, fontsize=7.5)
fig.savefig(OUT / "grader_validation.png"); plt.close(fig)
print("wrote", *(OUT / n for n in ("run_rewards.png", "run_means_cost.png", "run_where_lost.png", "grader_validation.png")))
