"""
Ingest one paper: metadata, PDF, full text, codebase. Writes sources/<slug>/record.json.

    python scripts/ingest.py <slug> [--doi DOI ...] [--pdf-url URL ...] [--code-url URL ...] [--no-pdf] [--no-code]

`slug` is a key of sources/sources.json, or a new one if --doi/--title are given. The flags let a human or an
agent add what automatic discovery missed (a publisher PDF link, a repository named in the paper) and re-run.

PDFs and clones go to a cache OUTSIDE the repo ($INGEST_CACHE, default ~/.cache/text2wetlab-ingest) because
licences differ per paper and per repository. The record keeps the URL, size, SHA-256, page count and a
`redistributable` flag, so ingestion is reproducible and nothing third-party is committed by accident.

Never spends API credit: Europe PMC, bioRxiv, PLOS, Crossref, GitHub only.
"""
import argparse
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
from urllib.parse import urlparse

import httpx

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
CACHE = pathlib.Path(os.environ.get("INGEST_CACHE", pathlib.Path.home() / ".cache/text2wetlab-ingest"))
SOURCES = ROOT / "sources"


def record_path(slug):
    return SOURCES / slug / "record.json"
HEADERS = {"User-Agent": "Mozilla/5.0 (text2wetlab ingestion; research)"}
EPMC = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
MAX_REPO_KB = 300_000     # skip clones above ~300 MB
MIN_PDF_BYTES = 30_000


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def get(http, url, **kw):
    try:
        return http.get(url, **kw)
    except Exception:
        return None


# ---------------------------------------------------------------- metadata
def epmc_core(http, doi):
    r = get(http, EPMC, params={"query": f'DOI:"{doi}"', "format": "json", "resultType": "core", "pageSize": 1})
    if r is None or r.status_code != 200:
        return {}
    res = r.json().get("resultList", {}).get("result", [])
    return res[0] if res else {}


def redistributable(licence: str | None) -> str:
    l = (licence or "").lower().replace("-", " ").strip()
    if not l:
        return "unknown"
    if l.startswith(("cc by nc", "cc by nd")):
        return "no"      # NC / ND clauses: not for a benchmark dataset that others may use commercially
    if l.startswith(("cc by", "cc0", "pd", "public domain")):
        return "yes"
    return "unknown"


# ---------------------------------------------------------------- PDF
def pdf_candidates(http, doi, meta, extra):
    urls = list(extra)
    for e in (meta.get("fullTextUrlList", {}) or {}).get("fullTextUrl", []) or []:
        if e.get("documentStyle") == "pdf" and e.get("availabilityCode") in ("OA", "F"):
            urls.append(e["url"])
    pmcid = meta.get("pmcid")
    if pmcid:
        # NCBI's PMC Open Access service lists direct links to OA PDFs (the sanctioned bulk route)
        r = get(http, "https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi", params={"id": pmcid})
        if r is not None and r.status_code == 200:
            for href in re.findall(r'format="pdf"[^>]*href="([^"]+)"', r.text) + re.findall(r'href="([^"]+\.pdf)"', r.text):
                urls.append(href.replace("ftp://ftp.ncbi.nlm.nih.gov", "https://ftp.ncbi.nlm.nih.gov"))
        # NCBI's PMC Open Access dataset on S3: official open data, and it serves PDFs when the websites bot-block scripts
        urls += [f"https://pmc-oa-opendata.s3.amazonaws.com/{pmcid}.{v}/{pmcid}.{v}.pdf" for v in (1, 2, 3)]
        urls.append(f"https://europepmc.org/backend/ptpmcrender.fcgi?accid={pmcid}&blobtype=pdf")
    if doi.startswith("10.1101/") or doi.startswith("10.64898/"):
        r = get(http, f"https://api.biorxiv.org/details/biorxiv/{doi}")
        if r is not None and r.status_code == 200 and r.json().get("collection"):
            urls.append(f"https://www.biorxiv.org/content/{doi}v{r.json()['collection'][-1]['version']}.full.pdf")
    if doi.startswith("10.1371/journal."):
        j = {"pone": "plosone", "pcbi": "ploscompbiol", "pgen": "plosgenetics", "pbio": "plosbiology"}.get(doi.split(".")[1], "plosone")
        urls.append(f"https://journals.plos.org/{j}/article/file?id={doi}&type=printable")
    r = get(http, f"https://api.crossref.org/works/{doi}")
    if r is not None and r.status_code == 200:
        for l in r.json().get("message", {}).get("link", []) or []:
            if "pdf" in (l.get("content-type") or ""):
                urls.append(l["URL"])
    seen, out = set(), []
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def try_download_pdf(http, urls, dest):
    tried = []
    for u in urls:
        r = get(http, u, follow_redirects=True)
        ok = r is not None and r.status_code == 200 and r.content[:5] == b"%PDF-" and len(r.content) >= MIN_PDF_BYTES
        tried.append({"url": u, "ok": ok, "http": None if r is None else r.status_code})
        if ok:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(r.content)
            return u, r.content, tried
    return None, None, tried


def pdf_pages(path):
    try:
        from pypdf import PdfReader

        return len(PdfReader(str(path)).pages)
    except Exception:
        return None


# ---------------------------------------------------------------- full text
def fulltext_info(doi, slug):
    """Section/legend counts from the pipeline's own ingest (JATS XML). No LLM."""
    cached = ROOT / "sources" / slug / "pipeline/paper.json"
    try:
        if cached.exists():
            p = json.loads(cached.read_text())
            return {"source": p.get("source", "cached paper.json"), "sections": len(p["sections"]), "legends": len(p["legends"])}
        from paper2protocol.ingest import fetch_paper

        p = fetch_paper(doi)
        return {"source": p.source, "sections": len(p.sections), "legends": len(p.legends)}
    except Exception as e:
        return {"source": None, "error": f"{type(e).__name__}: {str(e)[:100]}"}


# ---------------------------------------------------------------- code
def gh_json(path):
    r = subprocess.run(["gh", "api", path], capture_output=True, text=True)
    try:
        return json.loads(r.stdout) if r.returncode == 0 else None
    except Exception:
        return None


def repo_of(url):
    u = urlparse(url.removesuffix(".git"))
    parts = [p for p in u.path.split("/") if p]
    return (u.netloc, parts[0], parts[1]) if len(parts) >= 2 else (u.netloc, None, None)


def analyse_clone(path):
    py = [p for p in path.rglob("*.py") if ".git" not in p.parts]
    ot, api, robots = [], set(), set()
    for p in py:
        t = p.read_text(errors="replace")
        if re.search(r"\bopentrons\b|\.load_labware\(|\.load_instrument\(|\bprotocol_api\b", t):  # protocols often never import the package
            ot.append(p)
            api.update(re.findall(r"apiLevel['\"]?\s*[:=]\s*['\"]?(\d+\.\d+)", t))
            if re.search(r"OT-2|OT2|ot2", t):
                robots.add("OT-2")
            if re.search(r"Flex|flex", t):
                robots.add("Flex")
    return {"py_files": len(py), "opentrons_py_files": len(ot), "api_levels": sorted(api), "robot_mentions": sorted(robots)}


PERMISSIVE = {"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC", "Unlicense", "CC0-1.0"}
SPARSE = ["*.py", "*.ipynb", "*.json", "*.yaml", "*.yml", "*.toml", "*.cfg", "*.md", "*.rst", "*.txt", "*.csv", "*.xdl", "*.xml",
          "LICENSE*", "LICENCE*", "COPYING*"]
ARCHIVE_EXT = (".zip", ".tar.gz", ".tgz", ".tar")


def licence_from_text(root):
    """SPDX-ish id from a LICENSE/COPYING file, for hosts that do not report one."""
    for f in sorted(root.rglob("*")):
        if f.is_file() and re.match(r"(licen[cs]e|copying)", f.name, re.I) and ".git" not in f.parts:
            t = f.read_text(errors="replace")[:4000]
            for pat, spdx in [(r"MIT License|Permission is hereby granted, free of charge", "MIT"), (r"Apache License,? Version 2", "Apache-2.0"),
                              (r"GNU AFFERO GENERAL PUBLIC LICENSE", "AGPL-3.0"), (r"GNU LESSER GENERAL PUBLIC", "LGPL-3.0"),
                              (r"GNU GENERAL PUBLIC LICENSE\s+Version 3", "GPL-3.0"), (r"GNU GENERAL PUBLIC LICENSE\s+Version 2", "GPL-2.0"),
                              (r"Redistribution and use in source and binary forms", "BSD-3-Clause"), (r"Creative Commons Attribution 4", "CC-BY-4.0"),
                              (r"CC0|Creative Commons Zero", "CC0-1.0"), (r"unlicense\.org", "Unlicense")]:
                if re.search(pat, t, re.I):
                    return spdx
            return "unclear"
    return "none"


def git_clone(remote, dest, partial):
    """Shallow clone; a partial clone (sparse checkout of code, configs and docs) for repositories over the size limit."""
    if dest.exists():
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not partial:
        r = subprocess.run(["git", "clone", "-q", "--depth", "1", remote, str(dest)], capture_output=True, text=True, timeout=900)
        return r.returncode == 0, r.stderr
    r = subprocess.run(["git", "clone", "-q", "--depth", "1", "--filter=blob:none", "--no-checkout", remote, str(dest)],
                       capture_output=True, text=True, timeout=900)
    if r.returncode:
        return False, r.stderr
    subprocess.run(["git", "-C", str(dest), "sparse-checkout", "set", "--no-cone", *SPARSE], capture_output=True, text=True)
    r = subprocess.run(["git", "-C", str(dest), "checkout", "-q"], capture_output=True, text=True, timeout=900)
    return r.returncode == 0, r.stderr


def download_files(files, dest):
    """files: [(name, url, size_bytes)]. Downloads up to MAX_REPO_KB in total and unpacks archives."""
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True, exist_ok=True)
    total, got, skipped = 0, [], []
    with httpx.Client(headers=HEADERS, timeout=600, follow_redirects=True) as http:
        for name, url, size in sorted(files, key=lambda f: (not f[0].lower().endswith(ARCHIVE_EXT + (".py",)), f[2] or 0)):
            if (size or 0) + total > MAX_REPO_KB * 1024:
                skipped.append(name)
                continue
            r = get(http, url)
            if r is None or r.status_code != 200:
                skipped.append(name)
                continue
            out = dest / pathlib.Path(name).name
            out.write_bytes(r.content)
            total += len(r.content)
            got.append(name)
            if out.name.lower().endswith(ARCHIVE_EXT):
                try:
                    shutil.unpack_archive(str(out), str(dest / (out.name + "_x")))
                except Exception:
                    pass
    return got, skipped, total


def zenodo_id(url):
    m = re.search(r"zenodo\.(\d+)|zenodo\.org/(?:record|records)/(\d+)", url)
    return (m.group(1) or m.group(2)) if m else None


def osf_id(url):
    m = re.search(r"osf\.io/([a-z0-9]{5})", url)
    return m.group(1) if m else None


def osf_files(node):
    """Walk an OSF node's osfstorage and list (path, download url, size)."""
    out, stack = [], [f"https://api.osf.io/v2/nodes/{node}/files/osfstorage/"]
    with httpx.Client(headers=HEADERS, timeout=60, follow_redirects=True) as http:
        while stack and len(out) < 2000:
            r = get(http, stack.pop())
            if r is None or r.status_code != 200:
                continue
            j = r.json()
            for d in j.get("data", []):
                a = d["attributes"]
                if a["kind"] == "folder":
                    stack.append(d["relationships"]["files"]["links"]["related"]["href"])
                else:
                    out.append((a["materialized_path"].lstrip("/"), d["links"]["download"], a.get("size") or 0))
            if j.get("links", {}).get("next"):
                stack.append(j["links"]["next"])
    return out


def finish(rec, dest):
    rec.update(analyse_clone(dest))
    rec["cache_path"] = str(dest).replace(str(pathlib.Path.home()), "~")
    if rec.get("licence") in (None, "", "none", "unclear"):
        rec["licence"] = licence_from_text(dest)
    rec["redistributable"] = "yes" if rec["licence"] in PERMISSIVE else "no"
    return rec


def ingest_code(url, slug):
    rec = {"url": url, "status": "manual"}
    if not re.match(r"https?://", url or ""):
        rec["status"] = "no public code"
        return rec
    host, owner, name = repo_of(url)
    rec["host"] = host
    if "zenodo" in url and zenodo_id(url):
        zid = zenodo_id(url)
        with httpx.Client(headers=HEADERS, timeout=60, follow_redirects=True) as http:
            r = get(http, f"https://zenodo.org/api/records/{zid}")
        if r is None or r.status_code != 200:
            rec["status"] = "zenodo record not found"
            return rec
        meta = r.json()
        files = [(f["key"], f["links"]["self"], f.get("size") or 0) for f in meta.get("files", [])]
        dest = CACHE / "code" / slug / f"zenodo-{zid}"
        got, skipped, total = download_files(files, dest)
        rec.update({"repo": f"zenodo:{zid}", "licence": ((meta.get("metadata") or {}).get("license") or {}).get("id") or "",
                    "files": len(files), "files_downloaded": len(got), "files_skipped_size": skipped, "size_kb": total // 1024})
        rec["status"] = "downloaded" if got else "zenodo: no files within the size limit"
        return finish(rec, dest) if got else rec
    if "osf.io" in host and osf_id(url):
        node = osf_id(url)
        files = osf_files(node)
        dest = CACHE / "code" / slug / f"osf-{node}"
        got, skipped, total = download_files(files, dest)
        rec.update({"repo": f"osf:{node}", "files": len(files), "files_downloaded": len(got), "files_skipped_size": skipped, "size_kb": total // 1024})
        rec["status"] = "downloaded" if got else "osf: no files downloaded"
        return finish(rec, dest) if got else rec
    if host in ("huggingface.co", "www.protocols.io", "protocols.io"):
        rec["status"] = "not code: " + ("dataset" if host == "huggingface.co" else "protocol text")
        return rec
    if host == "github.com" and owner and not name:
        rec["status"] = "organisation link: name the repository with --code-url"
        return rec
    if not owner:
        rec["status"] = "non-git link: needs manual download"
        return rec
    if host == "github.com":
        meta = gh_json(f"repos/{owner}/{name}")
        if meta is None:
            rec["status"] = "not found (404 or private)"
            return rec
        lic = (meta.get("license") or {}).get("spdx_id")
        rec.update({"repo": f"{owner}/{name}", "default_branch": meta["default_branch"], "size_kb": meta["size"], "archived": meta["archived"],
                    "licence": lic if lic and lic != "NOASSERTION" else ("unclear" if lic else "none")})
        partial = meta["size"] > MAX_REPO_KB
    else:  # GitLab and other git hosts: owner/group path may be nested, so clone the URL as given
        rec["repo"] = urlparse(url).path.strip("/").removesuffix(".git")
        partial = True
    dest = CACHE / "code" / slug / f"{owner}__{(name or 'repo')}"
    ok, err = git_clone(url.removesuffix("/") if host != "github.com" else f"https://github.com/{owner}/{name}", dest, partial)
    if not ok:
        rec["status"] = "clone failed: " + err.strip()[-100:]
        return rec
    rec["commit"] = subprocess.run(["git", "-C", str(dest), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    rec["status"] = "cloned (partial: code, configs and docs only)" if partial else "cloned"
    return finish(rec, dest)


# ---------------------------------------------------------------- merging with a previous record
def stricter(new, old):
    """A previous explicit "no" always wins; any other stored value ("unknown" just means nothing was known yet)
    does not block a better-informed new value. A re-run can never turn a deliberate "no" into a "yes"."""
    return "no" if old == "no" else new


def merge_prev(rec, prev):
    """Carry hand-curated information from the previous record into a freshly computed one."""
    if prev.get("experiments_hint"):
        rec["experiments_hint"] = prev["experiments_hint"]
    if prev.get("note") and not rec.get("note_set_by_flag"):
        rec["note"] = prev["note"]
    if prev.get("pdf") and rec.get("pdf") is not None:
        old, new = prev["pdf"], rec["pdf"]
        keep = stricter(new.get("redistributable"), old.get("redistributable"))
        if keep == "no" and new.get("redistributable") != "no" and old.get("licence"):
            new["licence"] = old["licence"]
        new["redistributable"] = keep
    old_code = {c.get("url"): c for c in prev.get("code", [])}
    merged = []
    for c in rec.get("code", []):
        o = old_code.get(c.get("url"))
        fetched = str(c.get("status", "")).startswith(("cloned", "downloaded"))
        if o and (o.get("status") == "downloaded" and not o.get("files_downloaded") or (o.get("host") != "github.com" and not fetched)):
            c = o                                   # hand-managed archive, or a non-GitHub link this run could not fetch: kept
        elif o:
            keep = stricter(c.get("redistributable"), o.get("redistributable"))
            if keep == "no" and c.get("redistributable") != "no" and o.get("licence"):
                c["licence"] = o["licence"]
            c["redistributable"] = keep
        merged.append(c)
    rec["code"] = merged
    return rec


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1].strip())
    ap.add_argument("slug")
    ap.add_argument("--doi", action="append", default=[])
    ap.add_argument("--title")
    ap.add_argument("--pdf-url", action="append", default=[])
    ap.add_argument("--code-url", action="append", default=[])
    ap.add_argument("--no-pdf", action="store_true")
    ap.add_argument("--no-code", action="store_true")
    ap.add_argument("--note")
    ap.add_argument("--reanalyse", action="store_true", help="no network: re-run the code analysis on cached clones and update the record")
    a = ap.parse_args()
    if a.reanalyse:
        path = record_path(a.slug)
        rec = json.loads(path.read_text())
        for c in rec.get("code", []):
            if c.get("cache_path"):
                clone = pathlib.Path(c["cache_path"].replace("~", str(pathlib.Path.home())))
                if clone.exists():
                    c.update(analyse_clone(clone))
        path.write_text(json.dumps(rec, indent=1, ensure_ascii=False, sort_keys=True) + "\n")
        print(f"{a.slug}: re-analysed", [(c.get("repo"), c.get("opentrons_py_files")) for c in rec.get("code", [])])
        return
    src = {s["slug"]: s for s in json.loads((ROOT / "sources/sources.json").read_text())}.get(a.slug, {"slug": a.slug, "dois": [], "origin": ["manual"], "known_code": [], "note": ""})
    path = record_path(a.slug)
    prev = json.loads(path.read_text()) if path.exists() else {}
    dois = list(dict.fromkeys(a.doi + src["dois"] + prev.get("dois", [])))
    codes = list(dict.fromkeys(a.code_url + src["known_code"] + [c["url"] for c in prev.get("code", [])]))
    pdf_extra = list(dict.fromkeys(a.pdf_url + [t["url"] for t in prev.get("pdf", {}).get("tried", []) if t.get("manual")]))
    rec = {"slug": a.slug, "dois": dois, "title": a.title or src.get("title") or prev.get("title", ""), "origin": src["origin"],
           "note": a.note or prev.get("note") or src.get("note", ""), "note_set_by_flag": bool(a.note)}
    with httpx.Client(headers=HEADERS, timeout=60, follow_redirects=True) as http:
        meta = {}
        for d in dois:
            meta = epmc_core(http, d)
            if meta:
                rec["doi_primary"] = d
                break
        rec["journal"] = meta.get("journalTitle") or meta.get("bookOrReportDetails", {}).get("publisher") or prev.get("journal", "")
        rec["year"] = meta.get("pubYear") or prev.get("year", "")
        rec["pmcid"] = meta.get("pmcid") or src.get("pmcid")
        rec["open_access"] = meta.get("isOpenAccess") == "Y"
        rec["paper_licence"] = meta.get("license") or ""
        rec["title"] = rec["title"] or meta.get("title", "")
        if dois:
            rec["fulltext"] = fulltext_info(rec.get("doi_primary", dois[0]), a.slug)
        if not a.no_pdf and dois:
            urls = pdf_candidates(http, rec.get("doi_primary", dois[0]), meta, pdf_extra)
            dest = CACHE / "pdf" / f"{a.slug}.pdf"
            url, content, tried = try_download_pdf(http, urls, dest)
            for t in tried:
                t["manual"] = t["url"] in a.pdf_url
            pl = rec["paper_licence"]
            rec["pdf"] = ({"status": "downloaded", "url": url, "sha256": sha256(content), "bytes": len(content), "pages": pdf_pages(dest),
                           "licence": pl, "redistributable": redistributable(pl), "tried": tried}
                          if url else {"status": "not_found" if rec["open_access"] else "paywalled_or_not_found", "tried": tried,
                                       "licence": pl, "redistributable": "unknown"})
        elif prev.get("pdf"):
            rec["pdf"] = prev["pdf"]
    if not a.no_code:
        rec["code"] = [ingest_code(u, a.slug) for u in codes]
    elif prev.get("code"):
        rec["code"] = prev["code"]
    rec = merge_prev(rec, prev)
    rec.pop("note_set_by_flag", None)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rec, indent=1, ensure_ascii=False, sort_keys=True) + "\n")
    pdf = rec.get("pdf", {})
    print(f"{a.slug}: pdf={pdf.get('status', 'skipped')} ({pdf.get('pages')} pages, redistributable={pdf.get('redistributable')}) "
          f"fulltext={rec.get('fulltext', {}).get('sections')} sections; code={[c['status'] for c in rec.get('code', [])]}")


if __name__ == "__main__":
    main()
