import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "eval"))
from trace_replay import parse_log, replay

FX = pathlib.Path(__file__).parent / "fixtures"
L1 = pathlib.Path(__file__).parent.parent / "tasks/L1/serial-dilution-200ul"


def log(path):
    return (FX / path).read_text()


def test_parse_counts_atomic_commands():
    assert len(parse_log((L1 / "run_log.txt").read_text())) == 5


def test_l1_reference_passes_all_criteria():
    r = replay((L1 / "run_log.txt").read_text())
    assert all(r["criteria"].values()) and not r["errors"] and not r["tip_attached"]


def test_missing_tip_pickup_is_flagged():
    text = "\n".join(l for l in (L1 / "run_log.txt").read_text().splitlines() if not l.startswith("Picking"))
    r = replay(text)
    assert any(e == "NoTipError" for _, e in r["errors"])


def test_a1_a12_good_reaspirates_and_ends_clean():
    r = replay(log("L1_a1_a12/good_run_log.txt"))
    assert not r["errors"] and not r["tip_attached"]
    assert r["plate_ul"].sum() == 1200


def test_a1_a12_bad_overdispense_is_caught():
    """Opentrons simulate accepts this protocol silently; the replayer flags it."""
    r = replay(log("L1_a1_a12/bad_run_log.txt"))
    assert any(e == "overdispense" for _, e in r["errors"])
