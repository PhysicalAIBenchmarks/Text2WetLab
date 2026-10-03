"""paper2protocol CLI: search / list / convert."""

import argparse
import json
import re
import sys
from pathlib import Path

from . import guard, llm
from .check import check
from .critic import critique
from .extract import extract
from .identify import identify, verify_figure_refs
from .ingest import fetch_paper, normalize_doi, search
from .models import Experiment, Paper
from .render import render
from .sources import SOURCES
from .resolve import details_block, resolve


def _out_dir(base: str, doi: str) -> Path:
    d = Path(base) / re.sub(r"[^\w.-]+", "_", doi)
    d.mkdir(parents=True, exist_ok=True)
    return d


def _dump(path: Path, obj) -> None:
    data = obj.model_dump() if hasattr(obj, "model_dump") else [o.model_dump() for o in obj]
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def load_paper(args) -> tuple[Paper, Path]:
    doi = normalize_doi(args.doi, allow_lookup=True)
    out = _out_dir(args.out, doi)
    pj = out / "paper.json"
    if pj.exists() and not args.xml and not args.refetch:
        paper = Paper.model_validate_json(pj.read_text())
    else:
        print(f"Fetching {doi} ...", file=sys.stderr)
        paper = fetch_paper(doi, args.xml, args.source)
        _dump(pj, paper)
    print(f"{paper.title}\n  ({paper.source}, {len(paper.sections)} sections, {len(paper.legends)} figures)\n",
          file=sys.stderr)
    # TODO: restricted-research screen. Gate here, before experiments are identified;
    # anything other than "allow" should stop the pipeline (see design spec).
    return paper, out


def get_experiments(paper: Paper, out: Path) -> list[Experiment]:
    exps = identify(paper)  # cached by llm.py, so repeat calls are free
    _dump(out / "experiments.json", exps)
    return exps


def cmd_search(args):
    for i, h in enumerate(search(args.query, args.limit, preprints_only=args.biorxiv), 1):
        ft = "" if h["full_text_in_epmc"] else "  (no Europe PMC full text)"
        print(f"{i:2}. {h['title']}\n    {h['doi']}  {h['venue']}  {h['date']}{ft}")


def cmd_list(args):
    paper, out = load_paper(args)
    exps = get_experiments(paper, out)
    for i, e in enumerate(exps, 1):
        figs = ", ".join(r if ok else f"{r}?" for r, ok in verify_figure_refs(paper, e)) or "no figure"
        heads = [paper.section(r).heading.split(" > ")[-1] if paper.section(r) else r for r in e.section_refs]
        print(f"{i}. {e.title}   [{figs}]   liquid handling: {e.liquid_handling}")
        print(f"   {e.goal}")
        print(f"   sections: {' → '.join(heads)}")
        if e.unresolved_refs:
            print(f"   deferred elsewhere: {'; '.join(e.unresolved_refs)}")
    print(f"\n(? = figure ref not found among the paper's figure labels)\nSaved to {out}/", file=sys.stderr)


def _pick(args) -> tuple[Paper, Experiment, Path]:
    paper, out = load_paper(args)
    exps = get_experiments(paper, out)
    if not 1 <= args.experiment <= len(exps):
        sys.exit(f"--experiment must be 1..{len(exps)}; run `list` to see them")
    exp = exps[args.experiment - 1]
    print(f"Experiment {args.experiment}: {exp.title}", file=sys.stderr)
    ed = out / f"exp{args.experiment}"
    ed.mkdir(exist_ok=True)
    return paper, exp, ed


def _assess(args, paper, exp, ed):
    llm.WEB_EVENTS.clear()
    suff = resolve(paper, exp, web=not args.no_web)
    _dump(ed / "sufficiency.json", suff)
    flags = guard.audit(llm.WEB_EVENTS, paper)
    (ed / "web_access.json").write_text(json.dumps({
        "flags": [f.model_dump() for f in flags],
        "events": [e.model_dump() for e in llm.WEB_EVENTS]}, indent=2, ensure_ascii=False))
    fetched = sum(e.kind == "fetch" for e in llm.WEB_EVENTS)
    print(f"Web research: {sum(e.kind == 'search' for e in llm.WEB_EVENTS)} searches, {fetched} pages fetched "
          f"(log: {ed / 'web_access.json'})")
    for f in flags:
        print(f"  !! LEAK FLAG [{f.severity}] {f.value} — {f.reason}")
    print(f"Detail check: {suff.verdict} — {suff.summary}")
    for g in suff.gaps:
        print(f"  [{g.status}] {g.detail}")
        if g.resolution:
            print(f"      → {g.resolution}" + (f"  ({g.source})" if g.source else ""))
    print()
    return suff, flags


def cmd_assess(args):
    _assess(args, *_pick(args))


def cmd_convert(args):
    paper, exp, ed = _pick(args)
    details, flags, banner = "", [], ""
    if not args.skip_assess:
        suff, flags = _assess(args, paper, exp, ed)
        if suff.verdict == "reject":
            if not args.force:
                sys.exit("Rejected: not enough detail to run this experiment (see gaps above). "
                         "Use --force to convert anyway.")
            missing = [g for g in suff.gaps if g.status == "missing"]
            banner = ("WARNING: the detail check REJECTED this experiment; --force was used. "
                      "Details the paper never gives, invented below:\n"
                      + "".join(f"  - {g.detail}\n" for g in missing)
                      + f"Assessment: {suff.summary}\n\n")
        details = details_block(suff)

    protocol = extract(paper, exp, details)
    _dump(ed / "protocol.json", protocol)
    text = banner + render(protocol)
    accessed = [f for f in flags if f.severity == "accessed"]
    if accessed:
        text = ("WARNING: during research the pipeline opened possible author code/supplementary files:\n"
                + "".join(f"  {f.value} ({f.reason})\n" for f in accessed)
                + "This protocol may not be an independent reconstruction from the paper text.\n\n" + text)
    (ed / "protocol.txt").write_text(text)

    issues = check(protocol)
    _dump(ed / "check.json", issues)

    report = None
    if not args.no_critic:
        report = critique(paper, exp, text, issues, details)
        _dump(ed / "critic.json", report)

    print(text)
    if issues:
        print("Automated checks:")
        for i in issues:
            print(f"  step {i.step}: [{i.severity}] {i.message}")
    if report:
        print(f"\nCritic: {report.verdict} — {report.summary}")
        for c in report.issues:
            print(f"  step {c.step}: [{c.severity}] {c.issue}\n      → {c.suggestion}")
    if flags:
        print(f"\n!! {len(flags)} leak flag(s) from web research — see {ed / 'web_access.json'}")
    print(f"\nSaved to {ed}/", file=sys.stderr)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="paper2protocol", description=__doc__)
    ap.add_argument("--cache", choices=["use", "refresh", "off", "only"], default=llm.CACHE_MODE,
                    help="LLM response cache mode (default: use)")
    ap.add_argument("--out", default="out", help="output directory (default: out/)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("search", help="find papers by title/keywords (Europe PMC)")
    s.add_argument("query")
    s.add_argument("--biorxiv", action="store_true", help="only bioRxiv preprints")
    s.add_argument("--limit", type=int, default=10)
    s.set_defaults(func=cmd_search)

    for name, fn, hlp in [("list", cmd_list, "list experiments in a paper"),
                          ("assess", cmd_assess, "check whether an experiment has enough detail to run"),
                          ("convert", cmd_convert, "assess, then convert one experiment to instructions")]:
        p = sub.add_parser(name, help=hlp)
        p.add_argument("doi", help="DOI, doi.org link, publisher article URL, or article id/title")
        p.add_argument("--source", choices=[src.name for src in SOURCES],
                       help="fetch full text only from this source (default: try all that apply)")
        p.add_argument("--xml", help="use a local JATS XML file instead of downloading")
        p.add_argument("--refetch", action="store_true", help="ignore saved paper.json")
        if name in ("assess", "convert"):
            p.add_argument("--experiment", "-e", type=int, required=True, help="number from `list`")
            p.add_argument("--no-web", action="store_true", help="assess without web research")
        if name == "convert":
            p.add_argument("--no-critic", action="store_true")
            p.add_argument("--skip-assess", action="store_true", help="skip the detail/sufficiency check")
            p.add_argument("--force", action="store_true", help="convert even if the assessment rejects")
        p.set_defaults(func=fn)

    args = ap.parse_args(argv)
    llm.CACHE_MODE = args.cache
    try:
        args.func(args)
    except llm.LLMRefusal as e:
        sys.exit(f"Stopped: {e}")


if __name__ == "__main__":
    main()
