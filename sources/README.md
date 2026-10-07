# sources/: what we collected

Every paper the project has looked at, with its PDF and its code, and one master CSV row per **experiment**
(a paper that splits into several liquid-handling workflows gets several rows).

| File | What |
|---|---|
| `sources.json` | the papers to ingest: slug, DOIs, how it was found, code links already known |
| `candidates.json`, `CANDIDATES.md` | the 24-paper Amass BiomedCore search (2026-10-03), as found |
| `<slug>/record.json` | one record per paper: metadata, PDF, full text, code, experiments |
| `<slug>/pipeline/` | `paper2protocol` output for that paper: `paper.json`, `experiments.json`, `exp<N>/` (NL + IR). Not published: it holds paper full text |
| `<slug>/code/` | author scripts we vendored for comparison, each with upstream commit and licence (see `CODE.md`). Never published, never a pipeline input |
| `master.csv` | one row per (paper, experiment). Built by `scripts/build_master_csv.py`. Published to HuggingFace |

PDFs and clones live in a cache **outside** the repo (`$INGEST_CACHE`, default `~/.cache/text2wetlab-ingest/{pdf,code}`):
licences differ per paper and per repository. The record keeps URL, size, SHA-256, pages and a `redistributable` flag.

```bash
python scripts/ingest.py <slug> [--doi DOI] [--pdf-url URL] [--code-url URL] [--note TEXT]   # re-runnable
python scripts/build_master_csv.py
```

## Record schema (`<slug>/record.json`)

```
slug, dois[], doi_primary, title, journal, year, pmcid, open_access, paper_licence, origin[], note
fulltext  { source, sections, legends }                 JATS full text from Europe PMC / PLOS / bioRxiv (no LLM)
pdf       { status: downloaded | not_found | paywalled_or_not_found, url, sha256, bytes, pages,
            licence, redistributable: yes | no | unknown, tried[] }
code[]    { url, host, status, repo, commit, licence, redistributable, size_kb, py_files, opentrons_py_files,
            api_levels[], robot_mentions[], cache_path }
experiments_hint[]  { id, title, liquid_handling: mostly | partly | little, evidence }   hand-read split, see below
```

`redistributable` is `yes` only for CC-BY / CC0 papers and for repositories under MIT, Apache-2.0, BSD, ISC,
Unlicense or CC0. Anything unlicensed is `no`: it is ingested for comparison and never published.

`experiments_hint` is the paper's split into workflows that involve liquid handling, read from the full text, with
the section or figure each came from. It is a free preliminary split. The pipeline's own `identify` stage
(`sources/<slug>/pipeline/experiments.json`) is authoritative where it has run, and the master CSV prefers it.
