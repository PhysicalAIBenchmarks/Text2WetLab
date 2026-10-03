"""Upload the dataset to the HuggingFace Hub. Reads HF_TOKEN from the environment."""
import os
import shutil
import tempfile
from pathlib import Path

from huggingface_hub import HfApi

REPO_ID = os.environ.get("HF_REPO_ID", "EvanOLeary/Text2WetLab")
ROOT = Path(__file__).resolve().parent.parent
INCLUDE = ["tasks", "ref", "eval", "paper", "assets", "docs", "LICENSE"]

api = HfApi(token=os.environ["HF_TOKEN"])
api.create_repo(REPO_ID, repo_type="dataset", exist_ok=True)

with tempfile.TemporaryDirectory() as tmp:
    stage = Path(tmp)
    for name in INCLUDE:
        src = ROOT / name
        if src.is_dir():
            shutil.copytree(src, stage / name, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        elif src.exists():
            shutil.copy(src, stage / name)
    shutil.copy(ROOT / "hf_dataset_card.md", stage / "README.md")
    api.upload_folder(folder_path=str(stage), repo_id=REPO_ID, repo_type="dataset",
                      commit_message="Deploy from GitHub")
print(f"Deployed to https://huggingface.co/datasets/{REPO_ID}")
