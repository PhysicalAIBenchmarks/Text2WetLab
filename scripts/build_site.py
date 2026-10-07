"""Assemble the GitHub Pages site in _site/: the pages, only the assets they reference, and a leaderboard generated
from the latest committed run, so the site can never show numbers the repo does not have.

    python scripts/build_site.py [--run results/runs/2026-10-07-openrouter] [--out _site]

Pages: index.html (visualisation gallery), leaderboard.html (generated), docs/preprint/preprint.html (built by
manuscript/build.sh), the PLR tables and docs/demo.html. docs/leaderboard.html, the old address, redirects.
"""
import argparse
import html
import json
import pathlib
import re
import shutil

ROOT = pathlib.Path(__file__).resolve().parent.parent
REPO = "https://github.com/PhysicalAIBenchmarks/Text2WetLab"
PAGES = ["index.html", "plr_coverage_table.html", "plr_embodiment_pairs.html", "docs/demo.html", "docs/preprint/preprint.html"]
ORDER = ["claude-sonnet-5.5", "claude-opus-5.5", "claude-fable-5.1", "gpt-6.1-sol"]
NAME = {"claude-sonnet-5.5": "Claude Sonnet 5.5", "claude-opus-5.5": "Claude Opus 5.5", "claude-fable-5.1": "Claude Fable 5.1",
        "gpt-6.1-sol": "GPT-6.1 Sol"}
LOCAL_REF = re.compile(r'(?:src|href|poster|data-src)=["\']([^"\'#?]+)')


def local_refs(page: pathlib.Path) -> set[pathlib.Path]:
    refs = set()
    for ref in LOCAL_REF.findall(page.read_text(errors="ignore")):
        if ref.startswith(("http:", "https:", "mailto:", "data:", "javascript:", "$")):
            continue
        target = (page.parent / ref).resolve()
        if target.is_file() and ROOT in target.parents:
            refs.add(target)
    return refs


def run_data(run: pathlib.Path) -> dict:
    trials = {}
    for f in sorted(run.glob("*/*/trial.json")):
        t = json.loads(f.read_text())
        grader = json.loads((f.parent / "grader.json").read_text()) if (f.parent / "grader.json").exists() else {}
        checks = grader.get("checks") or []
        if isinstance(checks, dict):
            checks = checks.get("checks", [])
        votes = (grader.get("judge") or {}).get("votes")
        trials[(f.parent.parent.name, f.parent.name)] = {
            "reward": (t.get("rewards") or {}).get("reward"), "refused": t.get("exception") == "AgentSafetyRefusalError",
            "error": t.get("exception"), "cost": t.get("cost_usd") or 0.0, "votes": votes,
            "failed": [c["name"] for c in checks if not c["pass"]]}
    models = [m for m in ORDER if any(k[0] == m for k in trials)] + sorted({m for m, _ in trials} - set(ORDER))
    tasks = sorted({k for _, k in trials}, key=lambda k: (k.endswith("-hard"), k))
    answered = {m: [k for k in tasks if (m, k) in trials and not trials[(m, k)]["refused"]] for m in models}
    common = [k for k in tasks if all(k in answered[m] for m in models)]
    mean = lambda xs: round(sum(xs) / len(xs), 3) if xs else None
    rows = []
    for m in models:
        r = lambda k: trials[(m, k)]["reward"] or 0.0
        rows.append({
            "id": m, "name": NAME.get(m, m),
            "all": mean([0.0 if trials[(m, k)]["refused"] else r(k) for k in tasks]),
            "answered": mean([r(k) for k in answered[m]]), "n_answered": len(answered[m]),
            "common": mean([r(k) for k in common]),
            "easy": mean([r(k) for k in answered[m] if not k.endswith("-hard")]),
            "hard": mean([r(k) for k in answered[m] if k.endswith("-hard")]),
            "refusals": sum(trials[(m, k)]["refused"] for k in tasks),
            "cost": round(sum(trials[(m, k)]["cost"] for k in tasks), 2)})
    provisional = json.loads((run / "PROVISIONAL.json").read_text()) if (run / "PROVISIONAL.json").exists() else {}
    for key, why in provisional.items():
        m, _, k = key.partition("/")
        if (m, k) in trials:
            trials[(m, k)]["provisional"] = why
    grid = {k: {m: trials.get((m, k)) for m in models} for k in tasks}
    return {"run": run.name, "models": models, "tasks": tasks, "rows": rows, "grid": grid, "n_common": len(common),
            "n_provisional": sum(1 for t in trials.values() if t.get("provisional"))}


def cell(t: dict | None) -> str:
    if t is None:
        return '<td class="na">–</td>'
    if t["refused"]:
        return '<td class="refused" title="AgentSafetyRefusalError: the model declined the task">refused</td>'
    if t["reward"] is None:
        return f'<td class="na" title="{html.escape(t["error"] or "")}">error</td>'
    r = t["reward"]
    tier = "full" if r >= 0.999 else "high" if r >= 0.7 else "mid" if r >= 0.45 else "low"
    note = f'judge votes: {t["votes"]}' + (f'; failed checks: {", ".join(t["failed"])}' if t["failed"] else "")
    if t.get("provisional"):
        return f'<td class="{tier} prov" title="{html.escape("Provisional: " + t["provisional"])}">{r:.2f}<sup>†</sup></td>'
    return f'<td class="{tier}" title="{html.escape(note)}">{r:.2f}</td>'


def leaderboard(d: dict) -> str:
    rows_json = json.dumps(d["rows"])
    head = "".join(f'<th scope="col">{html.escape(NAME.get(m, m))}</th>' for m in d["models"])
    body = []
    for i, k in enumerate(d["tasks"]):
        if i == 0 or k.endswith("-hard") != d["tasks"][i - 1].endswith("-hard"):
            label = "Paper-only (hard) · goal and paper" if k.endswith("-hard") else "Easy · steps given"
            body.append(f'<tr class="group"><th colspan="{len(d["models"]) + 1}">{label}</th></tr>')
        body.append(f'<tr><th scope="row"><code>{html.escape(k)}</code></th>' + "".join(cell(d["grid"][k][m]) for m in d["models"]) + "</tr>")
    report = f'{REPO}/blob/main/results/runs/{d["run"]}/REPORT.md'
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"/>
<title>Text2WetLab Leaderboard</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap"/>
<style>
:root {{ --bg:#07090f; --surface:#0e1220; --card:#12182a; --border:#1e2a42; --accent:#00d4ff; --accent2:#7c3aed;
        --green:#00e676; --amber:#ffb300; --red:#ff5c5c; --text:#e2e8f0; --muted:#7c8aa3; --chip:#1a2540; color-scheme:dark; }}
*,*::before,*::after {{ box-sizing:border-box; margin:0; padding:0; }}
body {{ font-family:'Inter',system-ui,sans-serif; background:var(--bg); color:var(--text); padding:0 16px 64px; line-height:1.55; }}
.wrap {{ max-width:1100px; margin:0 auto; }}
header {{ padding:44px 0 28px; border-bottom:1px solid var(--border); }}
nav {{ display:flex; flex-wrap:wrap; gap:10px; margin-bottom:22px; }}
nav a {{ font:12px 'JetBrains Mono',monospace; color:var(--accent); text-decoration:none; background:var(--chip);
        border:1px solid var(--border); border-radius:20px; padding:4px 12px; }}
nav a:hover {{ border-color:var(--accent); }}
h1 {{ font-size:clamp(28px,5vw,42px); letter-spacing:-.02em; line-height:1.15; text-wrap:balance; }}
h1 span {{ color:var(--accent); }}
.lede {{ color:var(--muted); max-width:66ch; margin-top:12px; }}
h2 {{ font-size:18px; margin:40px 0 6px; }}
.sub {{ color:var(--muted); font-size:14px; max-width:70ch; margin-bottom:16px; }}
.modes {{ display:flex; flex-wrap:wrap; gap:8px; margin:18px 0 14px; }}
.modes button {{ font:500 13px 'Inter',sans-serif; color:var(--text); background:var(--card); border:1px solid var(--border);
                border-radius:8px; padding:7px 12px; cursor:pointer; }}
.modes button[aria-pressed="true"] {{ border-color:var(--accent); color:var(--accent); }}
.rank {{ display:grid; gap:10px; }}
.row {{ display:grid; grid-template-columns:2.2rem minmax(0,1.4fr) minmax(0,2fr) repeat(3,minmax(4.5rem,auto)); gap:14px;
        align-items:center; background:var(--card); border:1px solid var(--border); border-radius:12px; padding:14px 16px; }}
.pos {{ font:700 20px 'JetBrains Mono',monospace; color:var(--muted); }}
.row:first-child .pos {{ color:var(--amber); }}
.model {{ font-weight:600; min-width:0; }}
.bar {{ height:10px; background:var(--surface); border-radius:6px; overflow:hidden; }}
.bar i {{ display:block; height:100%; background:linear-gradient(90deg,var(--accent2),var(--accent)); border-radius:6px; }}
.num {{ font:500 15px 'JetBrains Mono',monospace; font-variant-numeric:tabular-nums; text-align:right; }}
.num small {{ display:block; font:11px 'Inter',sans-serif; color:var(--muted); letter-spacing:.04em; text-transform:uppercase; }}
.scroll {{ overflow-x:auto; border:1px solid var(--border); border-radius:12px; }}
table {{ border-collapse:collapse; width:100%; font-size:14px; font-variant-numeric:tabular-nums; }}
th, td {{ padding:9px 12px; border-bottom:1px solid var(--border); text-align:center; white-space:nowrap; }}
thead th {{ font-size:12px; color:var(--muted); text-transform:uppercase; letter-spacing:.05em; background:var(--surface); }}
tbody th {{ text-align:left; font-weight:500; }}
tr.group th {{ text-align:left; font-size:12px; color:var(--accent); text-transform:uppercase; letter-spacing:.06em; background:var(--surface); }}
td {{ font-family:'JetBrains Mono',monospace; }}
td.full {{ color:var(--green); }} td.high {{ color:#9be7ff; }} td.mid {{ color:var(--amber); }} td.low {{ color:var(--red); }}
td.refused {{ color:var(--muted); font-style:italic; font-family:'Inter',sans-serif;
             background:repeating-linear-gradient(135deg,transparent 0 6px,#ffffff08 6px 12px); }}
td.na {{ color:var(--muted); }}
td.prov {{ outline:1px dashed var(--amber); outline-offset:-4px; }} sup {{ color:var(--amber); }}
code {{ font-family:'JetBrains Mono',monospace; font-size:.92em; }}
.notes {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(16rem,1fr)); gap:12px; }}
.note {{ background:var(--card); border:1px solid var(--border); border-radius:12px; padding:14px 16px; font-size:14px; color:var(--muted); min-width:0; }}
.note b {{ color:var(--text); display:block; margin-bottom:4px; }}
.note a, .sub a {{ color:var(--accent); }}
@media (max-width:640px) {{ .row {{ grid-template-columns:2rem minmax(0,1fr) auto; }} .bar, .row .num.extra {{ display:none; }} }}
</style>
</head>
<body>
<div class="wrap">
<header>
  <nav>
    <a href="{REPO}">GitHub</a><a href="index.html">Visualisation gallery</a>
    <a href="docs/preprint/preprint.html">Preprint</a><a href="{report}">Full report</a>
  </nav>
  <h1>Text2WetLab <span>Leaderboard</span></h1>
  <p class="lede">Agents write Opentrons OT-2 protocols for 11 wet-lab tasks: 7 easy tasks that give the steps, 4 hard tasks that
  give only a goal and the source paper (paper-only). Each protocol is simulated, checked against a ground truth, and scored by a
  three-vote rubric judge. One attempt per task, same Claude Code agent for every model. Run <code>{html.escape(d["run"])}</code>.</p>
</header>

<h2>Overall</h2>
<p class="sub">Refused tasks are not scored: a refusal is the provider's safety policy, not a protocol. Models are ranked on the
{d["n_common"]} tasks every model answered; refusals are listed beside the score.</p>
<div class="modes" role="group" aria-label="Which tasks to average">
  <button type="button" data-key="common" aria-pressed="true">The {d["n_common"]} tasks all models answered</button>
  <button type="button" data-key="answered" aria-pressed="false">All tasks each model answered</button>
</div>
<div class="rank" id="rank"></div>

<h2>Per task</h2>
<p class="sub">Hover a score for the judge votes and any failed check; † marks a provisional score. Every failure
with its evidence is in the <a href="{report}">full report</a>.</p>
<div class="scroll"><table>
  <thead><tr><th scope="col">Task</th>{head}</tr></thead>
  <tbody>{''.join(body)}</tbody>
</table></div>

<h2>How to read it</h2>
<div class="notes">
  <div class="note"><b>Reward</b>Rubric score: three core items at 25% each (robot practice, tips and contamination, fidelity to the task or paper) and task items sharing 25%. A failed critical check caps it at 0.30.</div>
  <div class="note"><b>Verifier</b>Lint gate, 10 reward-hacking traps, the Opentrons 7.5 simulator and deterministic checks against the ground truth come first. All 11 reference solutions pass; 152 broken or cheating protocols all fail.</div>
  <div class="note"><b>Provisional (†)</b>{d["n_provisional"]} scores were judged before the paper-only audit removed two requirements the papers do not support, or with fewer than three judge votes. Hover a † for the reason; they are re-judged in the next run.</div>
</div>
</div>
<script>
const ROWS = {rows_json};
const NCOMMON = {d["n_common"]};
const rank = document.getElementById('rank');
function fmt(v) {{ return v === null ? '–' : v.toFixed(3); }}
function draw(key) {{
  const rows = [...ROWS].sort((a, b) => (b[key] ?? -1) - (a[key] ?? -1));
  rank.innerHTML = rows.map((r, i) => `
    <div class="row">
      <div class="pos">${{i + 1}}</div>
      <div class="model">${{r.name}}</div>
      <div class="bar" aria-hidden="true"><i style="width:${{(r[key] ?? 0) * 100}}%"></i></div>
      <div class="num">${{fmt(r[key])}}<small>${{key === 'answered' ? r.n_answered + ' tasks' : NCOMMON + ' tasks'}}</small></div>
      <div class="num extra">${{r.refusals}}<small>refused, not scored</small></div>
      <div class="num extra">$${{r.cost.toFixed(2)}}<small>agent cost</small></div>
    </div>`).join('');
}}
document.querySelectorAll('.modes button').forEach(b => b.addEventListener('click', () => {{
  document.querySelectorAll('.modes button').forEach(x => x.setAttribute('aria-pressed', String(x === b)));
  draw(b.dataset.key);
}}));
draw('common');
</script>
</body>
</html>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", type=pathlib.Path, default=None, help="results/runs/<run>; default: the latest")
    ap.add_argument("--out", type=pathlib.Path, default=ROOT / "_site")
    a = ap.parse_args()
    run = a.run or sorted((ROOT / "results/runs").iterdir())[-1]
    out = a.out
    if out.exists():
        shutil.rmtree(out)
    files = set()
    for page in PAGES:
        p = ROOT / page
        if p.exists():
            files.add(p.resolve())
            files |= local_refs(p)
    for f in sorted(files):
        dest = out / f.relative_to(ROOT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, dest)
    (out / "leaderboard.html").write_text(leaderboard(run_data(run)))
    (out / "docs").mkdir(exist_ok=True)
    (out / "docs/leaderboard.html").write_text(
        '<!doctype html><meta charset="utf-8"><title>Text2WetLab Leaderboard</title>'
        '<meta http-equiv="refresh" content="0; url=../leaderboard.html"><a href="../leaderboard.html">Leaderboard</a>\n')
    (out / ".nojekyll").write_text("")
    size = sum(f.stat().st_size for f in out.rglob("*") if f.is_file())
    print(f"wrote {out} ({sum(1 for f in out.rglob('*') if f.is_file())} files, {size / 1e6:.1f} MB) from {run.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
