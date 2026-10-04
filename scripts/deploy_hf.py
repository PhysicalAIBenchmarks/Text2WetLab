"""Upload the public dataset to the HuggingFace Hub. Reads HF_TOKEN from the environment.

    python scripts/deploy_hf.py --dry-run      # stage and list what would be published

Publishing is an allowlist. Never published:
  - tasks/<level>/<task>/tests/ and solution/   hidden grader and oracle files (contamination)
  - ref/                                        third-party scripts, several without a licence
  - out/, .git, caches                          generated or internal
"""
import argparse
import os
import shutil
import tempfile
from pathlib import Path

REPO_ID = os.environ.get("HF_REPO_ID", "EvanOLeary/Text2WetLab")
ROOT = Path(__file__).resolve().parent.parent
INCLUDE = ["tasks", "eval", "manuscript", "assets", "docs", "PROVENANCE.csv", "LICENSE"]
HIDDEN = {"tests", "solution"}  # directories directly inside tasks/<level>/<task>/
NOISE = {"__pycache__", ".DS_Store"}


def _ignore(directory, names):
    rel = Path(directory).resolve().relative_to(ROOT).parts
    skip = {n for n in names if n in NOISE or n.endswith(".pyc")}
    if len(rel) == 3 and rel[0] == "tasks":
        skip |= HIDDEN & set(names)
    return skip


def stage(dest: Path) -> list[str]:
    """Copy the public files into dest; return their relative paths."""
    for name in INCLUDE:
        src = ROOT / name
        if src.is_dir():
            shutil.copytree(src, dest / name, ignore=_ignore)
        elif src.exists():
            shutil.copy(src, dest / name)
    shutil.copy(ROOT / "hf_dataset_card.md", dest / "README.md")
    return sorted(str(p.relative_to(dest)) for p in dest.rglob("*") if p.is_file())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        files = stage(Path(tmp))
        if args.dry_run:
            print("\n".join(files))
            print(f"{len(files)} files would be published to {REPO_ID}")
            return
        from huggingface_hub import HfApi

        api = HfApi(token=os.environ["HF_TOKEN"])
        api.create_repo(REPO_ID, repo_type="dataset", exist_ok=True)
        api.upload_folder(folder_path=tmp, repo_id=REPO_ID, repo_type="dataset", commit_message="Deploy from GitHub")
    print(f"Deployed to https://huggingface.co/datasets/{REPO_ID}")


if __name__ == "__main__":
    main()
