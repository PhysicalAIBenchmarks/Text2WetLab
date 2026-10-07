"""Where a paper's outputs go: <root>/<slug>/pipeline/ (root defaults to sources/).

The slug is the paper's key in <root>/sources.json (looked up by DOI), else a name the caller chose
(a local file's stem, or --slug), else the DOI made filesystem-safe.
"""

import json
import re
from pathlib import Path

ROOT_DEFAULT = "sources"


def safe(s: str) -> str:
    return re.sub(r"[^\w.-]+", "_", s)


def slug_for_doi(root: str | Path, doi: str) -> str:
    f = Path(root) / "sources.json"
    if f.exists():
        want = safe(doi).lower()
        for s in json.loads(f.read_text()):
            if want in {safe(d).lower() for d in s.get("dois", [])}:
                return s["slug"]
    return safe(doi)


def pipeline_dir(root: str | Path, slug: str) -> Path:
    d = Path(root) / slug / "pipeline"
    d.mkdir(parents=True, exist_ok=True)
    return d
