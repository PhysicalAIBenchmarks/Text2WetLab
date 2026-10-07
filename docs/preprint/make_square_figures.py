"""Standalone square figures: one chart per PNG (1500 x 1500 px), same data and styling as make_figures.py.

    uv run --no-project --with matplotlib python docs/preprint/make_square_figures.py

Writes docs/preprint/figures/square/NN_<name>.png.
"""
import collections, statistics, sys, pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import make_figures as F   # reuses the data, palette and lost-points attribution (also rebuilds the composites)

plt.rcParams["savefig.bbox"] = "standard"   # make_figures.py crops tightly; squares keep the full 5 x 5 in canvas
OUT = F.OUT / "square"
OUT.mkdir(exist_ok=True)
M, NAME, COL, rounds, rid, m = F.MODELS, F.NAME, F.COL, F.rounds, F.rid, F.m
SIZE = (5, 5)


def square(name, draw):
    fig, ax = plt.subplots(figsize=SIZE)
    draw(ax)
    fig.tight_layout()
    fig.savefig(OUT / f"{name}.png", dpi=300, bbox_inches=None)
    plt.close(fig)


def reward(ax):
    means, sds, r4 = [], [], []
    for mo in M:
        pr = [statistics.mean(r["reward"] for r in rounds if rid(r) == k and m(r) == mo) for k in F.BINARY]
        means.append(statistics.mean(pr)); sds.append(statistics.stdev(pr))
        r4.append(statistics.mean(r["reward"] for r in rounds if rid(r) == "R4" and m(r) == mo))
    x = range(3)
    ax.bar(x, means, width=0.6, color=[COL[k] for k in M], yerr=sds, capsize=4, error_kw={"lw": 1, "ecolor": F.INK2})
    ax.scatter(x, r4, marker="D", s=40, color="white", edgecolor=F.INK, lw=1, zorder=3, label="R4 (reference round)")
    for i, v in enumerate(means): ax.text(i, 0.04, f"{v:.3f}", ha="center", color="white", fontsize=10, fontweight="bold")
    ax.set_xticks(list(x), [NAME[k] for k in M]); ax.set_ylim(0, 1.2); ax.set_yticks([0, .2, .4, .6, .8, 1])
    ax.set_ylabel("Mean reward, 7 easy tasks"); ax.set_title("Reward per model (R3–R7, mean ± SD)"); F.ygrid(ax); ax.legend(loc="upper left")


def cost(ax):
    c = [statistics.mean(r["cost"] for r in rounds if m(r) == mo and rid(r) in F.ALL and r["cost"]) for mo in M]
    ax.bar(range(3), c, width=0.6, color=[COL[k] for k in M])
    for i, v in enumerate(c): ax.text(i, v + 0.01, f"${v:.3f}", ha="center", fontsize=10)
    ax.set_xticks(range(3), [NAME[k] for k in M]); ax.set_ylim(0, 0.56); ax.set_ylabel("Agent cost per trial (USD)")
    ax.set_title("Cost per trial (R1–R7, 49 trials each)"); F.ygrid(ax)


def cost_vs_reward(ax):
    for mo in M:
        pts = [(sum(r["cost"] or 0 for r in rounds if rid(r) == k and m(r) == mo),
                statistics.mean(r["reward"] for r in rounds if rid(r) == k and m(r) == mo)) for k in F.BINARY]
        ax.scatter(*zip(*pts), s=60, color=COL[mo], edgecolor="white", lw=1.2, label=NAME[mo], zorder=3)
    ax.set_xlim(0, 4.2); ax.set_ylim(0.85, 1.0); ax.set_xticks([0, 1, 2, 3, 4], ["$0", "$1", "$2", "$3", "$4"])
    ax.set_xlabel("Cost of a 7-task run (USD)"); ax.set_ylabel("Mean reward"); ax.set_title("Cost vs reward (one dot per round)")
    F.ygrid(ax); F.xgrid(ax); ax.legend(loc="lower right")


TASKS = ["a1-a12-100ul", "split-200ul-two-wells", "ampure-bead-cleanup", "colony-pcr-screening",
         "golden-gate-assembly", "ecoli-heat-shock-transformation", "opentrons-rna-extraction"]
SHORT_T = ["A1–A12 100 µL", "Split 200 µL", "AMPure clean-up", "Colony PCR", "Golden Gate", "Heat-shock", "RNA extraction"]


def per_task(ax):
    h = 0.27
    for j, mo in enumerate(M):
        vals = [statistics.mean(r["reward"] for r in rounds if rid(r) in F.BINARY and m(r) == mo and F.task(r) == t) for t in TASKS]
        ys = [i + (j - 1) * h for i in range(len(TASKS))]
        ax.barh(ys, vals, height=h * 0.92, color=COL[mo], label=NAME[mo])
        for y, v in zip(ys, vals):
            if v < 0.995: ax.text(v + 0.015, y, f"{v:.2f}", va="center", fontsize=8)
    ax.set_yticks(range(len(TASKS)), SHORT_T); ax.invert_yaxis(); ax.set_xlim(0, 1.12)
    ax.set_xlabel("Mean reward, R3–R7"); ax.set_title("Reward per task"); F.xgrid(ax)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=3, fontsize=8)


def lost_stacked(ax):
    left = [0.0] * 3
    for t in F.ETYPES:
        vals = [F.lost[(mo, t)] for mo in M]
        ax.bar(range(3), vals, bottom=left, width=0.6, color=F.ECOL[t], edgecolor="white", lw=1.2, label=t)
        left = [a + b for a, b in zip(left, vals)]
    for i, v in enumerate(left): ax.text(i, v + 0.05, f"{v:.1f}", ha="center", fontsize=10)
    ax.set_xticks(range(3), [NAME[k] for k in M]); ax.set_ylim(0, 3.6); ax.set_ylabel("Reward points lost, R3–R7 (of 35)")
    ax.set_title("Points lost per model, by error type"); F.ygrid(ax)
    ax.legend(loc="upper left", fontsize=7.5, ncol=2)


def lost_pie(ax):
    tot = [sum(F.lost[(mo, t)] for mo in M) for t in F.ETYPES]
    s = sum(tot)
    w, _ = ax.pie(tot, colors=[F.ECOL[t] for t in F.ETYPES], startangle=90, counterclock=False,
                  wedgeprops={"width": 0.42, "edgecolor": "white", "linewidth": 2})
    ax.text(0, 0, f"{s:.1f}\npoints lost", ha="center", va="center", fontsize=11)
    ax.legend(w, [f"{t}  {v / s:.0%}" for t, v in zip(F.ETYPES, tot)], loc="upper center", bbox_to_anchor=(0.5, 0.02), ncol=2, fontsize=8, handlelength=1)
    ax.set_title("Share of lost points by error type"); ax.set_aspect("equal")


def outcomes(ax):
    perfect = [sum(1 for r in rounds if rid(r) == k and (r["reward"] or 0) >= 1) for k in F.ALL]
    judged = [sum(1 for r in rounds if rid(r) == k and (r["reward"] or 0) < 1) for k in F.ALL]
    ax.bar(F.ALL, perfect, color="#c3c2b7", width=0.62, label="Full marks")
    ax.bar(F.ALL, judged, bottom=perfect, color="#2a78d6", width=0.62, edgecolor="white", lw=1, label="Lost points to the judge")
    for i, (p, j) in enumerate(zip(perfect, judged)): ax.text(i, p + j / 2, str(j), ha="center", va="center", color="white", fontweight="bold")
    ax.set_ylim(0, 24); ax.set_yticks([0, 7, 14, 21]); ax.set_ylabel("Trials (21 per round)")
    ax.set_title("Outcome of every trial, by round"); F.ygrid(ax); ax.legend(loc="upper center", ncol=2, fontsize=8)


def layers_pie(ax):
    n = sum(1 for r in rounds if rid(r) in F.ALL)
    j = sum(1 for r in rounds if rid(r) in F.ALL and (r["reward"] or 0) < 1)
    w, _ = ax.pie([n - j, j], colors=["#c3c2b7", "#2a78d6"], startangle=90, counterclock=False,
                  wedgeprops={"width": 0.42, "edgecolor": "white", "linewidth": 2})
    ax.text(0, 0, f"{n}\ntrials", ha="center", va="center", fontsize=12)
    ax.legend(w, [f"Full marks ({n - j})", f"Lost points to the LLM judge ({j})"], loc="upper center", bbox_to_anchor=(0.5, 0.04), fontsize=8.5)
    ax.text(0, -1.62, "0 lost to traps, simulator, checks or critical cap", ha="center", fontsize=8.5, color=F.INK2)
    ax.set_title("Which verifier layer cost points"); ax.set_aspect("equal")


def by_round(ax):
    for mo in M:
        ys = [statistics.mean(r["reward"] for r in rounds if rid(r) == k and m(r) == mo) for k in F.ALL]
        ax.plot(F.ALL, ys, color=COL[mo], lw=2, marker="o", ms=6, mec="white", mew=1.2, label=NAME[mo])
    ax.set_ylim(0.86, 1.0); ax.set_ylabel("Mean reward"); ax.set_xlabel("Eval round (verifier revision)")
    ax.set_title("Reward as the verifier changed"); F.ygrid(ax); ax.legend(loc="lower right")


def years(ax):
    papers = {}
    for r in F.corpus: papers.setdefault(r["slug"], r["year"])
    yc = collections.Counter(y for y in papers.values() if y)
    ys = sorted(yc)
    ax.bar(ys, [yc[y] for y in ys], color="#2a78d6", width=0.62)
    for y in ys: ax.text(y, yc[y] + 0.12, str(yc[y]), ha="center")
    ax.set_ylabel("Papers"); ax.set_ylim(0, 8); ax.set_title(f"Source papers by year (n = {len(papers)})"); F.ygrid(ax)


def lh_pie(ax):
    lh = collections.Counter(r["liquid_handling"] for r in F.corpus)
    keys = ["mostly", "partly", "little"]
    w, _ = ax.pie([lh[k] for k in keys], colors=["#2a78d6", "#6da7ec", "#cde2fb"], startangle=90, counterclock=False,
                  wedgeprops={"width": 0.42, "edgecolor": "white", "linewidth": 2})
    ax.text(0, 0, f"{len(F.corpus)}\nexperiments", ha="center", va="center", fontsize=11)
    ax.legend(w, [f"{k} liquid handling ({lh[k]})" for k in keys], loc="upper center", bbox_to_anchor=(0.5, 0.04), fontsize=8.5)
    ax.set_title("Liquid handling per experiment"); ax.set_aspect("equal")


def p2p(ax):
    stages = [("not_identified", "Not split"), ("identified", "Identified"), ("rejected", "Rejected"), ("converted", "Converted")]
    sc = collections.Counter(r["pipeline_state"] for r in F.corpus)
    ax.bar([s[1] for s in stages], [sc[s[0]] for s in stages], color=["#c3c2b7", "#9ec5f4", "#eb6834", "#2a78d6"], width=0.6)
    for i, s in enumerate(stages): ax.text(i, sc[s[0]] + 0.8, str(sc[s[0]]), ha="center")
    ax.set_ylabel("Experiments"); ax.set_ylim(0, 58); ax.set_title("paper2protocol outcome per experiment"); F.ygrid(ax)


for name, fn in [("01_reward_per_model", reward), ("02_cost_per_trial", cost), ("03_cost_vs_reward", cost_vs_reward),
                 ("04_reward_per_task", per_task), ("05_points_lost_stacked", lost_stacked), ("06_points_lost_pie", lost_pie),
                 ("07_trial_outcomes_by_round", outcomes), ("08_verifier_layer_pie", layers_pie), ("09_reward_by_round", by_round),
                 ("10_papers_by_year", years), ("11_liquid_handling_pie", lh_pie), ("12_paper2protocol_outcome", p2p)]:
    square(name, fn)
print("wrote", len(list(OUT.glob("*.png"))), "square figures to", OUT)
