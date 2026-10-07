"""Upload the public dataset to the HuggingFace Hub. Reads HF_TOKEN from the environment.

    python scripts/deploy_hf.py --dry-run      # stage, list what would be published and what would be deleted

The Hub copy mirrors the allowlist: files on the Hub that are no longer published (an old layout, a path the allowlist
dropped) are deleted in the same deploy. The dataset card is hf_dataset_card.md with its results table generated from
the latest results/runs/ folder, the same data as the leaderboard.

Publishing is an allowlist. Never published:
  - tasks/<task>/private/ and harbor/   hidden grader, oracle and sandbox files (contamination)
  - tasks/<task>/ publishes only task.toml and public/
  - sources/<slug>/code and pipeline   third-party scripts and paper full text (licences differ per paper)
  - data/, .git, caches                 generated or internal
"""
import argparse
import importlib.util
import os
import shutil
import tempfile
from pathlib import Path

REPO_ID = os.environ.get("HF_REPO_ID", "EvanOLeary/Text2WetLab")
ROOT = Path(__file__).resolve().parent.parent
INCLUDE = ["tasks", "eval", "manuscript", "assets", "docs", "sources", "PROVENANCE.csv", "LICENSE"]
HIDDEN = {"private", "harbor", "tests", "solution", "environment"}  # hidden inside tasks/<task>/
NOISE = {"__pycache__", ".DS_Store"}
NEVER_PUBLISHED_SUFFIXES = (".pdf",)  # papers are fetched by URL and checked by SHA-256; licences differ per paper
KEEP_ON_HUB = {".gitattributes"}       # created by the Hub; never ours to delete
RESULTS_MARKER = "<!-- RESULTS -->"


def _ignore(directory, names):
    rel = Path(directory).resolve().relative_to(ROOT).parts
    skip = {n for n in names if n in NOISE or n.endswith(".pyc") or n.endswith(NEVER_PUBLISHED_SUFFIXES)}
    if len(rel) == 2 and rel[0] == "tasks":
        skip |= HIDDEN & set(names)
    if len(rel) == 2 and rel[0] == "sources":
        skip |= {"code", "pipeline"} & set(names)
    return skip


def results_markdown() -> str:
    """The latest run's summary, from the same function that builds the leaderboard."""
    spec = importlib.util.spec_from_file_location("build_site", ROOT / "scripts/build_site.py")
    site = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(site)
    run = sorted((ROOT / "results/runs").iterdir())[-1]
    d = site.run_data(run)
    fmt = lambda v: "-" if v is None else f"{v:.3f}"
    lines = [f"Run `{d['run']}`: {len(d['tasks'])} tasks, one attempt each, the same Claude Code agent for every model, "
             "Claude Sonnet 5.5 as a three-vote judge. Full results: "
             "[leaderboard](https://physicalaibenchmarks.github.io/Text2WetLab/leaderboard.html), "
             f"[report](https://github.com/PhysicalAIBenchmarks/Text2WetLab/blob/main/results/runs/{d['run']}/REPORT.md).",
             "",
             f"| Model | Mean, refusals as 0 | Mean, tasks answered | Mean, {d['n_common']} tasks all answered | Easy | Hard | Refusals | Agent cost |",
             "|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|"]
    for r in sorted(d["rows"], key=lambda r: -(r["all"] or 0)):
        lines.append(f"| {r['name']} | {fmt(r['all'])} | {fmt(r['answered'])} ({r['n_answered']}) | {fmt(r['common'])} | "
                     f"{fmt(r['easy'])} | {fmt(r['hard'])} | {r['refusals']} | ${r['cost']:.2f} |")
    if d.get("n_provisional"):
        lines += ["", f"{d['n_provisional']} of these scores are provisional until a re-judge with the audited verifier "
                  f"(reasons in `results/runs/{d['run']}/PROVISIONAL.json`; marked † on the leaderboard)."]
    return "\n".join(lines)


def stale_files(on_hub: set[str], published: set[str]) -> list[str]:
    """Files on the Hub that this deploy does not publish: deleted so the Hub mirrors the allowlist."""
    return sorted(on_hub - published - KEEP_ON_HUB)


def stage(dest: Path) -> list[str]:
    """Copy the public files into dest; return their relative paths."""
    for name in INCLUDE:
        src = ROOT / name
        if src.is_dir():
            shutil.copytree(src, dest / name, ignore=_ignore)
        elif src.exists():
            shutil.copy(src, dest / name)
    card = (ROOT / "hf_dataset_card.md").read_text()
    (dest / "README.md").write_text(card.replace(RESULTS_MARKER, results_markdown()))
    return sorted(str(p.relative_to(dest)) for p in dest.rglob("*") if p.is_file())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        files = stage(Path(tmp))
        from huggingface_hub import CommitOperationDelete, HfApi

        api = HfApi(token=os.environ.get("HF_TOKEN"))
        try:
            on_hub = set(api.list_repo_files(REPO_ID, repo_type="dataset"))
        except Exception:  # first deploy, or no access in a dry run
            on_hub = set()
        stale = stale_files(on_hub, set(files))
        if args.dry_run:
            print("\n".join(files))
            print("\n".join(f"DELETE {f}" for f in stale))
            print(f"{len(files)} files would be published to {REPO_ID}, {len(stale)} deleted")
            return
        api.create_repo(REPO_ID, repo_type="dataset", exist_ok=True)
        api.upload_folder(folder_path=tmp, repo_id=REPO_ID, repo_type="dataset", commit_message="Deploy from GitHub")
        if stale:
            api.create_commit(REPO_ID, repo_type="dataset", operations=[CommitOperationDelete(path_in_repo=f) for f in stale],
                              commit_message=f"Remove {len(stale)} files no longer published")
    print(f"Deployed to https://huggingface.co/datasets/{REPO_ID}: {len(files)} files, {len(stale)} removed")


if __name__ == "__main__":
    main()
