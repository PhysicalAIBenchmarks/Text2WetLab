"""
Dry-run plan for re-running the paper2protocol pipeline: what would run, how many tokens, roughly what it costs.

    python scripts/rerun_plan.py [--count] [--env FILE]

SPENDS NOTHING. It never calls a generation endpoint. With --count it calls `messages.count_tokens`, which is free,
on the real `identify` prompts. Everything for the later stages is an ENVELOPE built from the sizes of the pipeline
outputs already in sources/*/pipeline, and is labelled as such. Run the real thing afterwards with the command it prints.

Stages (paper2protocol/llm.py STAGES, all claude-sonnet-5-5):
  identify  paper -> experiments                     1 call per paper, no tools
  resolve   is there enough detail? web research     web_search + web_fetch server tools, effort high
  extract   experiment -> Protocol (the IR)          effort high
  critic    review the IR against the paper          effort high
"""
import argparse
import csv
import json
import pathlib
import statistics
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
RUNS = ROOT / "sources"
# $ per million tokens, from the claude-api reference cached 2026-09-25. Batch is half price. Cache reads are 0.1x input.
PRICE = {"claude-sonnet-5-5": {"in": 2.00, "out": 10.00, "cache_read": 0.20}}
MODEL = "claude-sonnet-5-5"
CHARS_PER_TOKEN = 4.0   # rough; only used where nothing was counted


def usd(tokens_in, tokens_out, p=PRICE[MODEL]):
    return tokens_in / 1e6 * p["in"] + tokens_out / 1e6 * p["out"]


def papers_needing_identify():
    rows = list(csv.DictReader(open(ROOT / "sources/master.csv")))
    by = {}
    for r in rows:
        by.setdefault(r["slug"], []).append(r)
    need = {s: rs for s, rs in by.items() if all(r["experiment_source"] != "paper2protocol identify" for r in rs) and rs[0]["doi"]}
    return rows, by, need


def measured_envelopes():
    """Per-experiment sizes (tokens) observed in the committed pipeline outputs."""
    from paper2protocol.ingest import experiment_section_ids, paper_text
    from paper2protocol.models import Experiment, Paper

    inp, proto, suff, crit = [], [], [], []
    for d in sorted(RUNS.glob("*/pipeline/exp*/protocol.json")):
        exps = json.loads((d.parent.parent / "experiments.json").read_text())
        exps = exps if isinstance(exps, list) else exps["experiments"]
        n = int(d.parent.name[3:])
        if not (d.parent.parent / "paper.json").exists():   # not committed for papers whose text we may not redistribute
            continue
        paper = Paper.model_validate_json((d.parent.parent / "paper.json").read_text())
        exp = Experiment.model_validate(exps[n - 1])
        inp.append(len(paper_text(paper, section_ids=experiment_section_ids(paper, exp), legends=True)) / CHARS_PER_TOKEN)
        proto.append(d.stat().st_size / CHARS_PER_TOKEN)
        suff.append((d.parent / "sufficiency.json").stat().st_size / CHARS_PER_TOKEN if (d.parent / "sufficiency.json").exists() else 0)
        crit.append((d.parent / "critic.json").stat().st_size / CHARS_PER_TOKEN if (d.parent / "critic.json").exists() else 0)
    q = lambda xs: (statistics.median(xs), max(xs))
    return {"n": len(inp), "section_text_in": q(inp), "protocol_out": q(proto), "sufficiency_out": q(suff), "critic_out": q(crit)}


def count_identify(need, env_file):
    import anthropic
    from dotenv import dotenv_values

    from paper2protocol import llm
    from paper2protocol.identify import TASK
    from paper2protocol.ingest import fetch_paper

    v = dotenv_values(env_file)
    kw = {"api_key": v["ANTHROPIC_API_KEY"]}
    if v.get("ANTHROPIC_WORKSPACE_ID"):
        kw["default_headers"] = {"anthropic-workspace-id": v["ANTHROPIC_WORKSPACE_ID"]}
    client = anthropic.Anthropic(**kw)
    from paper2protocol.ingest import paper_text

    out = {}
    for slug, rows in need.items():
        doi = rows[0]["doi"]
        try:
            paper = fetch_paper(doi)
            ctx = paper_text(paper)
            r = client.messages.count_tokens(model=MODEL, system=llm.SYSTEM, messages=[{"role": "user", "content": [
                {"type": "text", "text": ctx}, {"type": "text", "text": TASK}]}])
            out[slug] = {"tokens": r.input_tokens, "how": "counted"}
        except Exception as e:
            out[slug] = {"tokens": None, "how": f"{type(e).__name__}: {str(e)[:60]}"}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", action="store_true", help="count real identify tokens via the free count_tokens endpoint")
    ap.add_argument("--env", default=str(ROOT / ".env"))
    a = ap.parse_args()
    rows, by, need = papers_needing_identify()
    env = measured_envelopes()
    print(f"Pipeline outputs measured for envelopes: {env['n']} converted experiments (median, max tokens)")
    for k in ("section_text_in", "protocol_out", "sufficiency_out", "critic_out"):
        print(f"   {k:16} median {env[k][0]:7.0f}   max {env[k][1]:7.0f}")

    print(f"\n== identify: {len(need)} papers have no pipeline split yet (need a DOI and full text)")
    counted = count_identify(need, a.env) if a.count else {}
    id_in = []
    for slug in need:
        c = counted.get(slug, {})
        t = c.get("tokens")
        if t is None:  # no count available: fall back to the paper's section count as a crude proxy
            secs = need[slug][0]["fulltext_sections"] or 20
            t = int(secs) * 1800
        id_in.append(t)
        print(f"   {slug:40} {t:8,d} input tokens  ({c.get('how', 'ESTIMATED from section count')})")
    id_out = 3000
    c_id = usd(sum(id_in), id_out * len(need))

    # experiments that would be converted: liquid handling mostly/partly and not yet converted/rejected
    todo = [r for r in rows if r["liquid_handling"] in ("mostly", "partly", "most", "part") and r["pipeline_state"] in ("identified", "not_identified", "assessed")]
    n = len(todo)
    sec, proto, suff, crit = (env[k] for k in ("section_text_in", "protocol_out", "sufficiency_out", "critic_out"))
    print(f"\n== resolve + extract + critic: {n} experiments (liquid handling mostly/partly, not yet converted)")
    lo = dict(res_in=sec[0] * 3, res_out=suff[0] * 2, ext_in=sec[0] * 1.3, ext_out=proto[0] * 1.5, cr_in=sec[0] + proto[0], cr_out=crit[0] * 1.5)
    hi = dict(res_in=sec[1] * 8, res_out=suff[1] * 3, ext_in=sec[1] * 1.5, ext_out=proto[1] * 2.5, cr_in=sec[1] + proto[1], cr_out=crit[1] * 2.5)
    def per(e): return usd(e["res_in"] + e["ext_in"] + e["cr_in"], e["res_out"] + e["ext_out"] + e["cr_out"])
    print(f"   per experiment: ${per(lo):.2f} (typical) to ${per(hi):.2f} (largest paper)  [ASSUMED multipliers: resolve reads ~3-8x the section text through web tools]")
    c_lo, c_hi = c_id + n * per(lo), c_id + n * per(hi)
    print(f"\n== TOTAL (token cost only, {MODEL}, standard rates)")
    print(f"   identify  {len(need):3d} papers          ${c_id:7.2f}")
    print(f"   convert   {n:3d} experiments     ${n * per(lo):7.2f} to ${n * per(hi):7.2f}")
    print(f"   TOTAL                              ${c_lo:7.2f} to ${c_hi:7.2f}   (batch would be about half; cache hits cost 0.1x on re-runs)")
    print("\nNOT included (unverified, not in the pricing reference): per-use fees for the web_search and web_fetch server tools;")
    print("resolve allows up to 8 searches and 10 fetches per experiment (llm.WEB_TOOLS), so a per-search fee would scale with the experiment count.")
    print("\nTo run for real (this spends money; P2P_CACHE_MODE=use makes repeated calls free):")
    print("   uv run paper2protocol list <doi>                 # identify, writes sources/<slug>/pipeline/experiments.json")
    print("   uv run paper2protocol convert <doi> -e <n>       # resolve + extract + critic + check")
    print("   export P2P_WEB_SEARCH_MAX=8 P2P_WEB_FETCH_MAX=10  # per-call tool caps, lower them to cap spend")


if __name__ == "__main__":
    main()
