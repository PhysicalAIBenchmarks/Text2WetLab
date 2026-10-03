"""Full-text sources: DOI → JATS XML.

Each Source says which DOIs it can handle and how to fetch JATS for them. fetch_jats()
tries matching sources in order. To support a new publisher, write a fetch function that
returns JATS bytes and add a Source to SOURCES.
"""

import re
from collections.abc import Callable
from dataclasses import dataclass

import httpx

HEADERS = {"User-Agent": "Mozilla/5.0 (text2wetlab paper2protocol)"}
EPMC_SEARCH = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
EPMC_FULLTEXT = "https://www.ebi.ac.uk/europepmc/webservices/rest/{id}/fullTextXML"
BIORXIV_API = "https://api.biorxiv.org/details/biorxiv/{doi}"
PLOS_XML = "https://journals.plos.org/{journal}/article/file?id={doi}&type=manuscript"

# DOI infix → journals.plos.org path segment
PLOS_JOURNALS = {
    "pone": "plosone", "pbio": "plosbiology", "pcbi": "ploscompbiol", "pgen": "plosgenetics",
    "ppat": "plospathogens", "pntd": "plosntds", "pmed": "plosmedicine", "pdig": "plosdigitalhealth",
    "pgph": "globalpublichealth", "pclm": "climate", "pwat": "water", "pstr": "sustainabilitytransformation",
}


@dataclass
class Source:
    name: str
    handles: Callable[[str], bool]
    fetch: Callable[[httpx.Client, str], tuple[bytes, str]]  # → (jats_xml, source label)


def _xml_or_raise(r: httpx.Response) -> bytes:
    r.raise_for_status()
    if not r.content.lstrip().startswith(b"<"):
        raise RuntimeError(f"non-XML response ({r.content[:60]!r})")
    return r.content


def _europepmc(http: httpx.Client, doi: str) -> tuple[bytes, str]:
    """Europe PMC: open-access journal articles (via PMC) and many preprints."""
    r = http.get(EPMC_SEARCH, params={"query": f'DOI:"{doi}"', "format": "json", "resultType": "lite"})
    r.raise_for_status()
    hits = [h for h in r.json()["resultList"]["result"] if h.get("inEPMC") == "Y"]
    if not hits:
        raise RuntimeError("no Europe PMC full text for this DOI")
    pid = hits[0].get("pmcid") or hits[0]["id"]  # journal articles use PMCID, preprints PPR id
    return _xml_or_raise(http.get(EPMC_FULLTEXT.format(id=pid))), f"europepmc:{pid}"


def _plos(http: httpx.Client, doi: str) -> tuple[bytes, str]:
    m = re.match(r"10\.1371/journal\.(\w+)\.", doi)
    journal = PLOS_JOURNALS.get(m.group(1)) if m else None
    if not journal:
        raise RuntimeError(f"unknown PLOS journal for {doi}")
    return _xml_or_raise(http.get(PLOS_XML.format(journal=journal, doi=doi))), f"plos:{journal}"


def _biorxiv(http: httpx.Client, doi: str) -> tuple[bytes, str]:
    r = http.get(BIORXIV_API.format(doi=doi))
    r.raise_for_status()
    coll = r.json().get("collection") or []
    if not coll:
        raise RuntimeError("DOI not found in bioRxiv API")
    url = coll[-1].get("jatsxml")  # last entry = latest version
    if not url:
        raise RuntimeError("no JATS XML listed")
    return _xml_or_raise(http.get(url)), "biorxiv"


# Order matters: Europe PMC first (tables as text, no rate limiting), then publishers.
SOURCES = [
    Source("europepmc", lambda doi: True, _europepmc),
    Source("plos", lambda doi: doi.startswith("10.1371/journal."), _plos),
    Source("biorxiv", lambda doi: doi.startswith(("10.1101/", "10.64898/")), _biorxiv),
]


def fetch_jats(doi: str, only: str | None = None) -> tuple[bytes, str]:
    """Try each matching source (or just `only`); return (xml, label) from the first that works."""
    errors = []
    candidates = [s for s in SOURCES if (s.name == only if only else s.handles(doi))]
    if not candidates:
        raise RuntimeError(f"no source named {only!r}; have {[s.name for s in SOURCES]}")
    with httpx.Client(headers=HEADERS, timeout=60, follow_redirects=True) as http:
        for s in candidates:
            try:
                return s.fetch(http, doi)
            except Exception as e:  # noqa: BLE001 — try the next source
                errors.append(f"{s.name}: {e}")
    raise RuntimeError(
        f"Could not get full text for {doi}:\n  " + "\n  ".join(errors)
        + "\nDownload the JATS XML in a browser and pass it with --xml."
    )


# Publisher article ids in URLs, e.g. .../synbio/article/5/1/ysaa010/5869449 → "ysaa010"
ARTICLE_ID = re.compile(r"/([a-z]{2,8}\d{3,7})(?=[/?#]|$)", re.I)


def lookup_doi(ref: str) -> tuple[str, str]:
    """Resolve a non-DOI reference (publisher URL without a DOI, article id, or title) to a
    DOI via Europe PMC. Returns (doi, matched title) for the best hit."""
    m = ARTICLE_ID.search(ref)
    query = m.group(1) if m else ref.strip()
    hits = [h for h in search(query, limit=5) if h["doi"]]
    if not hits:
        raise RuntimeError(f"Could not find a DOI for {ref!r} (searched Europe PMC for {query!r})")
    return hits[0]["doi"], hits[0]["title"]


def search(query: str, limit: int = 10, preprints_only: bool = False) -> list[dict]:
    """Title/keyword search via Europe PMC (journals + preprints)."""
    q = f"({query})" + (' AND SRC:PPR AND PUBLISHER:"bioRxiv"' if preprints_only else "")
    r = httpx.get(EPMC_SEARCH, params={"query": q, "format": "json", "resultType": "lite", "pageSize": limit},
                  headers=HEADERS, timeout=60)
    r.raise_for_status()
    return [
        {"doi": h.get("doi", ""), "title": h.get("title", ""), "date": h.get("firstPublicationDate", ""),
         "venue": h.get("journalTitle") or h.get("bookOrReportDetails", {}).get("publisher", "") or h.get("source", ""),
         "full_text_in_epmc": h.get("inEPMC") == "Y"}
        for h in r.json()["resultList"]["result"]
    ]
