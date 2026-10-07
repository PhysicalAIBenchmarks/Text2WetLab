"""Paper figures for the Text2WetLab preprint (bar, stacked bar, pie, line, scatter).

    uv run --no-project --with matplotlib python docs/preprint/make_figures.py

Reads docs/harbor-results/analysis/{rounds,errors}.json and sources/master.csv; writes docs/preprint/figures/*.png.
"""
import collections, csv, json, pathlib, statistics

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = pathlib.Path(__file__).resolve().parents[2]
A = ROOT / "docs/harbor-results/analysis"
OUT = ROOT / "docs/preprint/figures"
OUT.mkdir(parents=True, exist_ok=True)

rounds = json.load(open(A / "rounds.json"))
errors = json.load(open(A / "errors.json"))
corpus = list(csv.DictReader(open(ROOT / "sources/master.csv")))

MODELS = ["opus-5-5", "sonnet-5-5", "fable-5-1"]
NAME = {"opus-5-5": "Opus 5.5", "sonnet-5-5": "Sonnet 5.5", "fable-5-1": "Fable 5.1"}
COL = {"opus-5-5": "#2a78d6", "sonnet-5-5": "#eb6834", "fable-5-1": "#1baf7a"}   # validated categorical slots 1-3
CAT = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#4a3aa7"]        # slots 1-5, 7 (green skipped: reads as status)
INK, INK2, MUTED, GRID = "#0b0b0b", "#52514e", "#898781", "#e1e0d9"
BINARY = ["R3", "R4", "R5", "R6", "R7"]
ALL = ["R1", "R2", "R3", "R4", "R5", "R6", "R7"]

plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
    "font.size": 9, "axes.edgecolor": "#c3c2b7", "axes.linewidth": 0.8, "axes.labelcolor": INK2,
    "xtick.color": INK2, "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False,
    "axes.titleweight": "bold", "axes.titlesize": 10, "axes.titlelocation": "left", "legend.frameon": False,
    "savefig.dpi": 300, "savefig.bbox": "tight", "savefig.facecolor": "white",
})

def m(r): return r["model"].replace("claude-", "")
def rid(r): return r["round"][:2]
def task(r): return "opentrons-rna-extraction" if r["task"] == "rna-extraction" else r["task"]
def panel(ax, letter): ax.text(-0.14, 1.06, letter, transform=ax.transAxes, fontsize=13, fontweight="bold", va="bottom")
def ygrid(ax): ax.yaxis.grid(True, color=GRID, lw=0.6); ax.set_axisbelow(True)
def xgrid(ax): ax.xaxis.grid(True, color=GRID, lw=0.6); ax.set_axisbelow(True)

SHORT = {"Over-recovers eluate (90-100 uL, not ~80)": "Over-recovers eluate",
         "Adds unrequested step, pause or delay": "Unrequested step or delay",
         "Pipette-mixes competent cells (unrequested)": "Mixes competent cells",
         "Wrong reagent order (sample before beads)": "Wrong reagent order",
         "Hallucinated paper authors in metadata": "Wrong paper authors",
         "Ethanol not labelled 70%": "Other", "No mix at elution": "Other", "(other / style)": "Other"}
ETYPES = ["Over-recovers eluate", "Mixes competent cells", "Wrong reagent order", "Unrequested step or delay", "Wrong paper authors", "Other"]
ECOL = dict(zip(ETYPES, CAT))

# lost points by error type: each failed binary item is 0.2 of the reward, split equally across its tags
lost = collections.defaultdict(float)          # (model, etype) -> points, R3-R7
for e in errors:
    if e["round"] in BINARY:
        tags = sorted({SHORT.get(t, "Other") for t in e["tags"]})
        for t in tags:
            lost[(e["model"], t)] += 0.2 / len(tags)

# ---------------------------------------------------------------- Figure 2: headline
fig, axs = plt.subplots(1, 3, figsize=(10, 3.1), gridspec_kw={"width_ratios": [1, 1, 1.15], "wspace": 0.45})
ax = axs[0]
means, sds, r4 = [], [], []
for mo in MODELS:
    per_round = [statistics.mean(r["reward"] for r in rounds if rid(r) == k and m(r) == mo) for k in BINARY]
    means.append(statistics.mean(per_round)); sds.append(statistics.stdev(per_round))
    r4.append(statistics.mean(r["reward"] for r in rounds if rid(r) == "R4" and m(r) == mo))
x = range(3)
ax.bar(x, means, width=0.55, color=[COL[k] for k in MODELS], yerr=sds, capsize=3, error_kw={"lw": 0.8, "ecolor": INK2})
ax.scatter(x, r4, marker="D", s=22, color="white", edgecolor=INK, lw=0.9, zorder=3, label="R4 (reference round)")
for i, v in enumerate(means): ax.text(i, 0.04, f"{v:.3f}", ha="center", va="bottom", color="white", fontsize=8, fontweight="bold")
ax.set_xticks(list(x), [NAME[k] for k in MODELS]); ax.set_ylim(0, 1.22); ax.set_yticks([0, 0.2, 0.4, 0.6, 0.8, 1.0]); ax.set_ylabel("Mean reward (7 easy tasks)")
ax.set_title("Reward, R3–R7 mean ± SD"); ygrid(ax); ax.legend(loc="upper left", fontsize=7.5); panel(ax, "a")

ax = axs[1]
cost = [statistics.mean(r["cost"] for r in rounds if m(r) == mo and rid(r) in ALL and r["cost"]) for mo in MODELS]
ax.bar(x, cost, width=0.55, color=[COL[k] for k in MODELS])
for i, v in enumerate(cost): ax.text(i, v + 0.008, f"${v:.3f}", ha="center", va="bottom", fontsize=8, color=INK)
ax.set_xticks(list(x), [NAME[k] for k in MODELS]); ax.set_ylabel("Agent cost per trial (USD)"); ax.set_ylim(0, 0.56)
ax.set_title("Cost per trial, R1–R7"); ygrid(ax); panel(ax, "b")

ax = axs[2]
for mo in MODELS:
    pts = [(sum(r["cost"] or 0 for r in rounds if rid(r) == k and m(r) == mo),
            statistics.mean(r["reward"] for r in rounds if rid(r) == k and m(r) == mo)) for k in BINARY]
    ax.scatter([p[0] for p in pts], [p[1] for p in pts], s=34, color=COL[mo], edgecolor="white", lw=1, label=NAME[mo], zorder=3)
ax.set_xlabel("Cost of a 7-task run (USD)"); ax.set_ylabel("Mean reward"); ax.set_ylim(0.85, 1.0); ax.set_xlim(0, 4.2)
ax.set_xticks([0, 1, 2, 3, 4], ["$0", "$1", "$2", "$3", "$4"]); ax.set_title("Cost vs reward, one dot per round"); ygrid(ax); xgrid(ax)
ax.legend(loc="lower right", fontsize=8); panel(ax, "c")
fig.savefig(OUT / "fig2_headline.png"); plt.close(fig)

# ---------------------------------------------------------------- Figure 3: per task
tasks = ["a1-a12-100ul", "split-200ul-two-wells", "ampure-bead-cleanup", "colony-pcr-screening",
         "golden-gate-assembly", "ecoli-heat-shock-transformation", "opentrons-rna-extraction"]
fig, ax = plt.subplots(figsize=(7.2, 3.6))
h = 0.26
for j, mo in enumerate(MODELS):
    vals = [statistics.mean(r["reward"] for r in rounds if rid(r) in BINARY and m(r) == mo and task(r) == t) for t in tasks]
    ys = [i + (j - 1) * h for i in range(len(tasks))]
    ax.barh(ys, vals, height=h * 0.92, color=COL[mo], label=NAME[mo])
    for y, v in zip(ys, vals):
        if v < 0.995: ax.text(v + 0.01, y, f"{v:.2f}", va="center", fontsize=7.5, color=INK)
ax.set_yticks(range(len(tasks)), tasks); ax.invert_yaxis(); ax.set_xlim(0, 1.08); ax.set_xlabel("Mean reward, R3–R7 (5 rounds × 1 attempt)")
xgrid(ax); ax.legend(loc="lower left", ncol=3, fontsize=8, bbox_to_anchor=(0, 1.0))
fig.savefig(OUT / "fig3_per_task.png"); plt.close(fig)

# ---------------------------------------------------------------- Figure 4: errors (stacked bar + pie)
fig, axs = plt.subplots(1, 2, figsize=(10, 3.6), gridspec_kw={"width_ratios": [1.1, 1], "wspace": 0.35})
ax = axs[0]
left = [0.0] * 3
for t in ETYPES:
    vals = [lost[(mo, t)] for mo in MODELS]
    ax.barh(range(3), vals, left=left, height=0.55, color=ECOL[t], edgecolor="white", lw=1.2, label=t)
    left = [a + b for a, b in zip(left, vals)]
for i, v in enumerate(left): ax.text(v + 0.03, i, f"{v:.1f}", va="center", fontsize=8, color=INK)
ax.set_yticks(range(3), [NAME[k] for k in MODELS]); ax.invert_yaxis(); ax.set_xlabel("Reward points lost, R3–R7 (of 35 available)")
ax.set_title("Where each model loses points"); xgrid(ax); ax.set_xlim(0, max(left) * 1.15)
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=3, fontsize=7.5); panel(ax, "a")

ax = axs[1]
tot = [sum(lost[(mo, t)] for mo in MODELS) for t in ETYPES]
wedges, _ = ax.pie(tot, colors=[ECOL[t] for t in ETYPES], startangle=90, counterclock=False,
                   wedgeprops={"width": 0.42, "edgecolor": "white", "linewidth": 2})
s = sum(tot)
ax.legend(wedges, [f"{t}  {v / s:.0%}" for t, v in zip(ETYPES, tot)], loc="center left", bbox_to_anchor=(1.0, 0.5), fontsize=8, handlelength=1)
ax.text(0, 0, f"{s:.1f}\npoints lost", ha="center", va="center", fontsize=9, color=INK)
ax.set_title("Share of all lost points, by error type"); ax.set_aspect("equal"); panel(ax, "b")
fig.savefig(OUT / "fig4_errors.png"); plt.close(fig)

# ---------------------------------------------------------------- Figure 5: grader layers + stability
fig, axs = plt.subplots(1, 3, figsize=(10.5, 3.2), gridspec_kw={"width_ratios": [1.25, 0.9, 1.25], "wspace": 0.45})
ax = axs[0]
perfect = [sum(1 for r in rounds if rid(r) == k and (r["reward"] or 0) >= 1) for k in ALL]
judged = [sum(1 for r in rounds if rid(r) == k and (r["reward"] or 0) < 1) for k in ALL]
ax.bar(ALL, perfect, color="#c3c2b7", width=0.62, label="Full marks")
ax.bar(ALL, judged, bottom=perfect, color="#2a78d6", width=0.62, edgecolor="white", lw=1, label="Lost points to the LLM judge")
for i, (p, j) in enumerate(zip(perfect, judged)): ax.text(i, p + j / 2, str(j), ha="center", va="center", color="white", fontsize=8, fontweight="bold")
ax.set_ylabel("Trials (21 per round)"); ax.set_ylim(0, 21); ax.set_yticks([0, 7, 14, 21]); ax.set_title("Outcome of every trial, by round"); ygrid(ax)
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2, fontsize=7.5); panel(ax, "a")

ax = axs[1]
n_trials = sum(1 for r in rounds if rid(r) in ALL)
n_judge = sum(1 for r in rounds if rid(r) in ALL and (r["reward"] or 0) < 1)
ax.pie([n_trials - n_judge, n_judge], colors=["#c3c2b7", "#2a78d6"], startangle=90, counterclock=False,
       wedgeprops={"width": 0.42, "edgecolor": "white", "linewidth": 2})
ax.text(0, 0, f"{n_trials}\ntrials", ha="center", va="center", fontsize=9)
ax.text(0, -1.42, f"{n_trials - n_judge} full marks · {n_judge} lost points to the judge\n0 to traps, simulator, checks or cap",
        ha="center", va="center", fontsize=7.5, color=INK2)
ax.set_title("Which layer cost points"); ax.set_aspect("equal"); panel(ax, "b")

ax = axs[2]
for mo in MODELS:
    ys = [statistics.mean(r["reward"] for r in rounds if rid(r) == k and m(r) == mo) for k in ALL]
    ax.plot(ALL, ys, color=COL[mo], lw=2, marker="o", ms=4.5, mec="white", mew=1, label=NAME[mo])
ax.set_ylim(0.86, 1.0); ax.set_ylabel("Mean reward"); ax.set_title("Reward as the grader changed"); ygrid(ax)
ax.legend(loc="lower right", fontsize=7.5); panel(ax, "c")
fig.savefig(OUT / "fig5_grader.png"); plt.close(fig)

# ---------------------------------------------------------------- Figure 6: corpus
fig, axs = plt.subplots(1, 3, figsize=(11, 3.3), gridspec_kw={"width_ratios": [1.2, 0.9, 1.0], "wspace": 0.55})
ax = axs[0]
papers = {}
for r in corpus: papers.setdefault(r["slug"], r["year"])
yc = collections.Counter(y for y in papers.values() if y)
years = sorted(yc)
ax.bar(years, [yc[y] for y in years], color="#2a78d6", width=0.62)
for y in years: ax.text(y, yc[y] + 0.15, str(yc[y]), ha="center", fontsize=8)
ax.set_ylabel("Papers"); ax.set_title(f"Source papers by year (n = {len(papers)})"); ygrid(ax); panel(ax, "a")

ax = axs[1]
lh = collections.Counter(r["liquid_handling"] for r in corpus)
keys = ["mostly", "partly", "little"]
w, _ = ax.pie([lh[k] for k in keys], colors=["#2a78d6", "#6da7ec", "#cde2fb"], startangle=90, counterclock=False,
              wedgeprops={"width": 0.42, "edgecolor": "white", "linewidth": 2})
ax.legend(w, [f"{k} ({lh[k]})" for k in keys], loc="upper center", bbox_to_anchor=(0.5, 0.02), ncol=1, fontsize=7.5, handlelength=1)
ax.text(0, 0, f"{len(corpus)}\nexperiments", ha="center", va="center", fontsize=9)
ax.set_title("Liquid handling per experiment"); ax.set_aspect("equal"); panel(ax, "b")

ax = axs[2]
stages = [("not_identified", "Not split"), ("identified", "Identified"), ("rejected", "Rejected"), ("converted", "Converted")]
sc = collections.Counter(r["pipeline_state"] for r in corpus)
ax.barh([s[1] for s in stages], [sc[s[0]] for s in stages], color=["#c3c2b7", "#9ec5f4", "#eb6834", "#2a78d6"], height=0.6)
for i, s in enumerate(stages): ax.text(sc[s[0]] + 0.8, i, str(sc[s[0]]), va="center", fontsize=8)
ax.set_xlabel("Experiments"); ax.set_title("paper2protocol outcome"); xgrid(ax); ax.invert_yaxis(); panel(ax, "c")
fig.savefig(OUT / "fig6_corpus.png"); plt.close(fig)

print("wrote", sorted(p.name for p in OUT.glob("*.png")))
print("lost points by type:", {t: round(v, 2) for t, v in zip(ETYPES, tot)}, "total", round(sum(tot), 2))
