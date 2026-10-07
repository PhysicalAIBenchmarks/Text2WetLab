"""Track every remote URL of the project: the hosted pages, and every link in the repo that points at them.

    python scripts/check_urls.py                 # check all; exit 1 if any is not HTTP 200
    python scripts/check_urls.py --write         # also regenerate docs/urls.md (the hosted-URL list)

"Ours" means the GitHub Pages site, this GitHub organisation and the Hugging Face dataset. Links are found in every
tracked text file; a URL ends at whitespace, a quote, a bracket or a comma (PROVENANCE.csv has URLs in CSV columns).
Run by .github/workflows/links.yml after each Pages deploy, weekly, and on demand.
"""
import argparse
import concurrent.futures
import pathlib
import re
import subprocess
import sys
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = "https://physicalaibenchmarks.github.io/Text2WetLab"
REPO = "https://github.com/PhysicalAIBenchmarks/Text2WetLab"
HF = "https://huggingface.co/datasets/EvanOLeary/Text2WetLab"
HOSTED = [  # (what, url): the addresses people are given
    ("Site: visualisation gallery", f"{SITE}/"),
    ("Site: leaderboard (generated from results/runs/)", f"{SITE}/leaderboard.html"),
    ("Site: preprint (built from manuscript/)", f"{SITE}/docs/preprint/preprint.html"),
    ("Site: PLR machine coverage", f"{SITE}/plr_coverage_table.html"),
    ("Site: PLR paper-code pairs", f"{SITE}/plr_embodiment_pairs.html"),
    ("Site: demo", f"{SITE}/docs/demo.html"),
    ("Site: old leaderboard address (redirects)", f"{SITE}/docs/leaderboard.html"),
    ("Repository", REPO),
    ("Latest results report", f"{REPO}/blob/main/results/runs/2026-10-07-openrouter/REPORT.md"),
    ("Hugging Face dataset", HF),
]
OURS = re.compile(r"https?://(?:physicalaibenchmarks\.github\.io|github\.com/PhysicalAIBenchmarks|huggingface\.co/datasets/EvanOLeary)"
                  r"[^\s\"'<>()\[\]{}`,|]*")
TEXT = {".md", ".html", ".py", ".toml", ".yml", ".yaml", ".csv", ".json", ".txt", ".bib", ".sh", ".cff"}


def repo_links() -> set[str]:
    files = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.split()
    found = set()
    for name in files:
        path = ROOT / name
        if path.suffix in TEXT and path.is_file() and path.stat().st_size < 5_000_000:
            for url in OURS.findall(path.read_text(errors="ignore")):
                url = url.rstrip(".;:!?*_")
                if "{" not in url and not url.endswith(".git"):
                    found.add(url)
    return found


def status(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "Text2WetLab link check"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return str(response.status)
    except urllib.error.HTTPError as e:
        return str(e.code)
    except Exception as e:  # DNS, timeout, TLS
        return type(e).__name__


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="regenerate docs/urls.md")
    a = ap.parse_args()
    hosted = [u for _, u in HOSTED]
    urls = sorted(set(hosted) | repo_links())
    with concurrent.futures.ThreadPoolExecutor(10) as pool:
        codes = dict(zip(urls, pool.map(status, urls)))
    bad = {u: c for u, c in codes.items() if c != "200"}
    print(f"{len(urls)} URLs checked ({len(hosted)} hosted, {len(urls) - len(hosted)} more linked from the repo): "
          f"{len(urls) - len(bad)} OK, {len(bad)} failing")
    for url, code in sorted(bad.items()):
        print(f"  {code}  {url}")
    if a.write:
        rows = "\n".join(f"| {what} | <{url}> |" for what, url in HOSTED)
        (ROOT / "docs/urls.md").write_text(f"""# Remote URLs

Every public address of the project. `scripts/check_urls.py` checks these and every other link in the repo that
points at them ({len(urls)} URLs at the last regeneration); `.github/workflows/links.yml` runs it after each Pages
deploy, every Monday, and on demand, and fails if any URL stops returning 200.

| What | URL |
|---|---|
{rows}

The site is built by `scripts/build_site.py` and deployed by `.github/workflows/pages.yml` on every change to `main`
that touches a page, `docs/`, `assets/`, `results/runs/` or `manuscript/`. The dataset is uploaded by the `deploy-hf`
job in `.github/workflows/ci.yml`.
""")
        print("wrote docs/urls.md")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
