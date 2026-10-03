from paper2protocol.guard import WebEvent, audit, web_events
from paper2protocol.ingest import normalize_doi
from paper2protocol.models import Paper

PAPER = Paper(doi="10.1371/journal.pone.0246302", title="", abstract="", source="", sections=[], legends=[])


def test_audit_flags_code_and_own_supplementary():
    events = [
        WebEvent(kind="fetch", value="https://www.promega.com/-/media/files/tb281.pdf"),
        WebEvent(kind="fetch", value="https://journals.plos.org/plosone/article/file?type=supplementary&id=10.1371/journal.pone.0246302.s001"),
        WebEvent(kind="result", value="https://github.com/someone/ot2-rna/blob/main/protocol.py"),
        WebEvent(kind="search", value="pone.0246302 opentrons protocol .py"),
    ]
    flags = audit(events, PAPER)
    assert [f.severity for f in flags] == ["accessed", "seen", "seen"]
    assert "supplementary" in flags[0].reason


def test_web_events_parses_server_tool_blocks():
    resp = {"content": [
        {"type": "server_tool_use", "name": "web_search", "input": {"query": "INTERFERin manual"}},
        {"type": "web_search_tool_result", "content": [{"url": "https://a.example/x"}]},
        {"type": "server_tool_use", "name": "web_fetch", "input": {"url": "https://a.example/x"}},
        {"type": "text", "text": "{}"},
    ]}
    assert [(e.kind, e.value) for e in web_events(resp)] == [
        ("search", "INTERFERin manual"), ("result", "https://a.example/x"), ("fetch", "https://a.example/x")]


def test_normalize_doi_from_publisher_urls():
    assert normalize_doi("https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0246302") == "10.1371/journal.pone.0246302"
    assert normalize_doi("https://www.biorxiv.org/content/10.1101/2024.09.14.613006v2.full") == "10.1101/2024.09.14.613006"
