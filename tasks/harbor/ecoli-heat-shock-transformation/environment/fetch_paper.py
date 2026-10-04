#!/usr/bin/env python3
"""Fetch a bioRxiv paper's full text (JATS XML) and write it as plain text, unless the file is already there.

Used for papers whose licence does not let us ship them in the repo (e.g. APEX, bioRxiv "all rights reserved"):
their paper.txt is gitignored, and the Dockerfile next to this script runs it at build time when the file is missing.
Standard library only, so it runs in the task image's plain python:3.10.

    python fetch_paper.py --doi 10.1101/2024.08.13.607171 --version 1 --out data/paper.txt

The bioRxiv version is pinned so the text, and its sha256 in tests/data_hashes.json, stays the same between builds.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

BIORXIV_API = "https://api.biorxiv.org/details/biorxiv/{doi}"
HEADERS = {"User-Agent": "Mozilla/5.0 (text2wetlab fetch_paper)"}


def _get(url: str, attempts: int = 8) -> bytes:
    for i in range(attempts):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=120) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 502, 503, 504) or i == attempts - 1:
                raise
            wait = int(e.headers.get("Retry-After") or 0) or min(5 * 2 ** i, 120)
        except urllib.error.URLError:
            if i == attempts - 1:
                raise
            wait = min(5 * 2 ** i, 120)
        print(f"fetch {url} failed, retrying in {wait}s", file=sys.stderr)
        time.sleep(wait)
    raise RuntimeError("unreachable")


def _strip_ns(root: ET.Element) -> ET.Element:
    for el in root.iter():
        if isinstance(el.tag, str) and "}" in el.tag:
            el.tag = el.tag.split("}", 1)[1]
    return root


def _text(el: ET.Element | None) -> str:
    return re.sub(r"\s+", " ", "".join(el.itertext())).strip() if el is not None else ""


def _table(tw: ET.Element) -> str:
    rows = [t for t in (_text(tw.find("label")), _text(tw.find("caption"))) if t]
    for tr in tw.iter("tr"):
        rows.append(" | ".join(_text(c) for c in tr if c.tag in ("td", "th")))
    return "\n".join(rows)


def _sections(parent: ET.Element, path: list[str], out: list[str]) -> None:
    for sec in parent.findall("sec"):
        heading = path + [_text(sec.find("title")) or "(untitled)"]
        parts = [_table(el) if el.tag == "table-wrap" else _text(el)
                 for el in sec if el.tag not in ("title", "sec", "fig")]
        body = "\n".join(p for p in parts if p)
        out.append(" > ".join(heading) + ("\n" + body if body else ""))
        _sections(sec, heading, out)


def jats_to_text(xml: bytes, doi: str, licence: str) -> str:
    root = _strip_ns(ET.fromstring(xml))
    legends = [f"{_text(f.find('label'))} {_text(f.find('caption'))}".strip() for f in root.iter("fig")]
    out = [_text(root.find(".//article-meta//article-title")), f"DOI: {doi}", f"Licence: {licence}", "",
           "Abstract", _text(root.find(".//article-meta/abstract")), ""]
    sections: list[str] = []
    for part in ("body", "back"):
        if (el := root.find(part)) is not None:
            _sections(el, [], sections)
    out += [s + "\n" for s in sections]
    if legends:
        out += ["Figure legends"] + legends
    return "\n".join(out).rstrip() + "\n"


def fetch(doi: str, version: str) -> tuple[bytes, str]:
    coll = json.loads(_get(BIORXIV_API.format(doi=doi))).get("collection") or []
    match = [c for c in coll if str(c.get("version")) == str(version)]
    if not match or not match[0].get("jatsxml"):
        raise RuntimeError(f"bioRxiv has no JATS XML for {doi} v{version}")
    return _get(match[0]["jatsxml"]), match[0].get("license", "unknown")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--doi", required=True)
    ap.add_argument("--version", required=True, help="bioRxiv version to pin, e.g. 1")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--force", action="store_true", help="re-fetch even if --out exists")
    args = ap.parse_args()
    if args.out.exists() and not args.force:
        print(f"{args.out} already present; not fetching")
        return 0
    xml, licence = fetch(args.doi, args.version)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(jats_to_text(xml, args.doi, f"bioRxiv {licence} (fetched at build time, not redistributed)"))
    print(f"wrote {args.out} from bioRxiv {args.doi} v{args.version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
