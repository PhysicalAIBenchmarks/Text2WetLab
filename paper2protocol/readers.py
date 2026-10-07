"""Any input → Paper. The pipeline downstream of this file only ever sees a `Paper`.

    DOI / doi.org link / publisher URL / title   fetched as JATS XML (sources.py)       ingest.fetch_paper
    *.xml                                        a JATS file you already have          ingest.parse_jats
    *.pdf                                        text layer, split on headings         pdf_text + text_to_paper
    *.md, *.txt                                  Markdown or plain text, split on headings  text_to_paper

PDF and text inputs have no structure to read, so sections come from heading heuristics: Markdown `#` lines,
numbered headings ("2.1 Library prep") and the usual article headings (Methods, Results, ...). Figure
legends are lines that start with "Fig. N" / "Figure N". These are coarse; check `paper.json` before trusting
an experiment split built on them. Scanned PDFs with no text layer are rejected, not OCR'd.
To add an input kind, write a function returning a Paper and register its suffix in READERS.
"""

import hashlib
import re
from pathlib import Path

from .ingest import parse_jats
from .models import Legend, Paper, Section

KNOWN = r"abstract|introduction|background|methods?|materials and methods|experimental(?: procedures| section)?|results(?: and discussion)?|discussion|conclusions?|references|acknowledge?ments|supplementary(?: information| materials?)?"
HEADING = re.compile(rf"^(?:#{{1,6}}\s+(?P<md>.+)|(?P<num>(?-i:\d{{1,2}}(?:\.\d{{1,2}}){{0,3}}\.?\s+[A-Z][^\n.;]{{2,70}}))|(?P<known>(?:{KNOWN}))\s*:?)$", re.I)
LEGEND = re.compile(r"^(?P<label>(?:Supplementary\s+)?Fig(?:ure|\.)?\s*S?\d+[A-Za-z]?)[.:|]?\s*(?P<rest>.*)$", re.I)
METHODS = re.compile(r"method|procedure|experimental|protocol|assay|preparation|library", re.I)


def pdf_text(path: Path) -> str:
    from pypdf import PdfReader

    text = "\n".join((p.extract_text() or "") for p in PdfReader(str(path)).pages)
    if len(text.strip()) < 500:
        raise ValueError(f"{path.name}: no usable text layer (scanned PDF?). OCR is not supported")
    return text


def text_to_paper(text: str, *, doi: str, source: str, title: str = "") -> Paper:
    lines = [ln.strip() for ln in text.replace("\r\n", "\n").split("\n")]
    banner = re.compile(r"(research|original|review|short)?\s*(article|paper|report)s?|open access|\W*", re.I)
    title = title or next((ln.lstrip("# ").strip() for ln in lines if len(ln) >= 15 and not banner.fullmatch(ln)), "")
    sections, legends, buf, heading, in_refs, in_methods = [], [], [], "Front matter", False, False

    def flush():
        body = " ".join(buf).strip()
        if body and not in_refs:
            sections.append(Section(id=f"s{len(sections) + 1}", heading=heading, kind="methods" if in_methods else "", text=body))
        buf.clear()

    def top_level(name: str, m) -> bool:       # "2 Methods", "Methods", "# Title" end the previous part; "2.1 Plate setup" does not
        return bool(m.group("known")) or (m.group("num") is not None and not re.match(r"\d+\.\d", name)) or bool(re.fullmatch(KNOWN, name, re.I))

    for ln in lines:
        m = HEADING.match(ln) if ln else None
        if m and len(ln) < 100:
            flush()
            name = (m.group("md") or m.group("num") or m.group("known")).strip()
            in_refs = bool(re.fullmatch(r"references", name, re.I))
            if top_level(name, m):
                in_methods = bool(METHODS.search(name))
            heading = name
        elif ln and (lg := LEGEND.match(ln)):
            legends.append(Legend(id=f"fig{len(legends) + 1}", label=re.sub(r"\s+", " ", lg["label"]).replace("Fig.", "Figure").replace("Fig ", "Figure "), title="", text=lg["rest"]))
        elif ln:
            buf.append(ln)
    flush()
    abstract = next((s.text for s in sections if re.fullmatch(r"abstract", s.heading, re.I)), "")
    sections = [s for s in sections if not re.fullmatch(r"abstract", s.heading, re.I)]
    for i, s in enumerate(sections, 1):
        s.id = f"s{i}"
    return Paper(doi=doi, title=title, abstract=abstract, source=source, sections=sections, legends=legends)


def read_file(path: str | Path, *, doi: str = "") -> Paper:
    p = Path(path)
    kind = p.suffix.lower()
    if kind not in (".xml", ".pdf", ".md", ".txt"):
        raise ValueError(f"unsupported input {p.name!r}; expected a DOI/URL or a .xml, .pdf, .md or .txt file")
    label = f"file:{p.name} sha256:{hashlib.sha256(p.read_bytes()).hexdigest()[:12]}"
    if kind == ".xml":
        return parse_jats(p.read_bytes(), doi, source=label)
    if kind == ".pdf":
        return text_to_paper(pdf_text(p), doi=doi, source=label)
    return text_to_paper(p.read_text(), doi=doi, source=label)
