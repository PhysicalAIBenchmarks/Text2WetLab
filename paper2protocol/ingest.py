"""DOI → Paper: fetch JATS full text (see sources.py) and parse it into sections/legends/refs."""

import re
import sys
from pathlib import Path

from lxml import etree

from .models import Legend, Paper, Reference, Section
from .sources import fetch_jats, lookup_doi, search  # noqa: F401  (re-exported for cli)



def normalize_doi(s: str, allow_lookup: bool = False) -> str:
    """Accept bare DOIs, doi.org URLs and publisher URLs (e.g. PLOS ?id=..., bioRxiv content
    URLs). With allow_lookup, a URL/id/title with no DOI in it is resolved via Europe PMC."""
    s = s.strip()
    m = re.search(r"(10\.\d{4,9}/[^\s?#&]+)", s)
    if not m:
        if allow_lookup:
            doi, title = lookup_doi(s)
            print(f"Resolved to {doi} — {title}", file=sys.stderr)
            return doi
        raise ValueError(f"Not a DOI: {s!r}")
    doi = m.group(1)
    doi = re.sub(r"(\.full|\.full-text|\.abstract|\.pdf|\.source\.xml)$", "", doi)
    if doi.startswith(("10.1101/", "10.64898/")):  # bioRxiv version suffix
        doi = re.sub(r"v\d+$", "", doi)
    return doi.rstrip("/")


def fetch_paper(doi: str, xml_path: str | None = None, source: str | None = None) -> Paper:
    if xml_path:
        return parse_jats(Path(xml_path).read_bytes(), doi, source=f"file:{xml_path}")
    xml, label = fetch_jats(doi, only=source)
    return parse_jats(xml, doi, source=label)


# ---------------------------------------------------------------- JATS parsing

def _text(el) -> str:
    return re.sub(r"\s+", " ", el.xpath("string()")).strip() if el is not None else ""


def _join_text(el) -> str:
    """Like _text, but separates child elements (JATS citations have no inner whitespace)."""
    return re.sub(r"\s+", " ", " ".join(t.strip() for t in el.itertext() if t.strip()))


def _strip_ns(root):
    for el in root.iter():
        if isinstance(el.tag, str) and "}" in el.tag:
            el.tag = el.tag.split("}", 1)[1]
    return root


def parse_jats(xml: bytes, doi: str, source: str) -> Paper:
    root = _strip_ns(etree.fromstring(xml, etree.XMLParser(recover=True, huge_tree=True)))
    title = _text(root.find(".//article-meta//article-title"))
    abstract = _text(root.find(".//article-meta/abstract"))

    legends = []
    for i, fig in enumerate(root.iter("fig"), 1):
        cap = fig.find("caption")
        legends.append(Legend(
            id=fig.get("id") or f"fig{i}",
            label=_text(fig.find("label")) or f"Figure {i}",
            title=_text(cap.find("title")) if cap is not None else "",
            text=_text(cap) if cap is not None else "",
        ))
    # Drop figures from the body so their captions don't pollute section text.
    for fig in list(root.iter("fig")):
        fig.getparent().remove(fig)

    sections: list[Section] = []
    body = root.find("body")
    if body is not None:
        _walk(body, "s", [], sections)
    back = root.find("back")
    if back is not None:  # some preprints put methods/supplementary under <back>
        _walk(back, "b", [], sections)
    references = []
    for i, ref in enumerate(root.iter("ref"), 1):
        cit = next((c for c in ref if c.tag in ("element-citation", "mixed-citation", "citation")), None)
        doi_el = ref.find(".//pub-id[@pub-id-type='doi']")
        references.append(Reference(id=ref.get("id") or f"ref{i}", label=_text(ref.find("label")),
                                    citation=_join_text(cit if cit is not None else ref),
                                    doi=_text(doi_el)))
    return Paper(doi=doi, title=title, abstract=abstract, source=source, sections=sections,
                 legends=legends, references=references)


def _walk(parent, prefix: str, path: list[str], out: list[Section], kind: str = ""):
    """Flatten nested <sec>s. Top-level ids are '<prefix><n>' (s1, b1); nested add '.<n>'."""
    n = 0
    for child in parent:
        if child.tag != "sec":
            continue
        if child.get("sec-type") == "ref-list":  # references are parsed separately
            continue
        n += 1
        sid = f"{prefix}.{n}" if path else f"{prefix}{n}"
        heading = _text(child.find("title")) or "(untitled)"
        hpath = path + [heading]
        # Own text = everything except the title and nested sections.
        parts = []
        for el in child:
            if el.tag in ("title", "sec"):
                continue
            t = _table_text(el) if el.tag == "table-wrap" else _text(el)
            if t:
                parts.append(t)
        sec_kind = child.get("sec-type", "") or kind
        out.append(Section(id=sid, heading=" > ".join(hpath), kind=sec_kind, text="\n".join(parts)))
        _walk(child, sid, hpath, out, sec_kind)


def _table_text(tw) -> str:
    rows = []
    cap = _text(tw.find("caption")) or _text(tw.find("label"))
    if cap:
        rows.append(cap)
    trs = list(tw.iter("tr"))
    for tr in trs:
        rows.append(" | ".join(_text(c) for c in tr if c.tag in ("td", "th")))
    if not trs and tw.find(".//graphic") is not None:
        rows.append("[table provided only as an image in this source; contents unavailable]")
    return "\n".join(rows)


def is_methods(s: Section) -> bool:
    top = s.heading.split(" > ")[0]
    return "method" in s.kind.lower() or bool(re.search(r"method|material|experimental procedure|protocol", top, re.I))


def experiment_section_ids(paper: Paper, exp) -> list[str]:
    """Sections an experiment's prompts should see: its own refs plus every Methods section
    (reagent tables and shared recipes are often not listed in shared_refs)."""
    ids = set(exp.section_refs) | set(exp.shared_refs)
    ids |= {s.id for s in paper.sections if is_methods(s)}
    return [s.id for s in paper.sections if s.id in ids]


def paper_text(paper: Paper, section_ids: list[str] | None = None, legends: bool = True,
               references: bool = False) -> str:
    """Render the paper (or a subset of sections) as tagged plain text for prompts."""
    out = [f"TITLE: {paper.title}", f"DOI: {paper.doi}", "", f"ABSTRACT: {paper.abstract}", ""]
    for s in paper.sections:
        if section_ids is None or s.id in section_ids:
            out.append(f"[{s.id}] {s.heading}\n{s.text}\n")
    if legends:
        out.append("FIGURE LEGENDS")
        for lg in paper.legends:
            out.append(f"[{lg.label}] {lg.text}\n")
    if references and paper.references:
        out.append("REFERENCES")
        for r in paper.references:
            link = f" https://doi.org/{r.doi}" if r.doi else ""
            out.append(f"[{r.label or r.id}] {r.citation}{link}")
    return "\n".join(out)
