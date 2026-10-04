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


def test_long_protocols_are_replayed_in_full():
    """The env's 20-step cap must not truncate a valid protocol (this once left 3 of 12 wells unfilled)."""
    tip = "Picking up tip from A1 of Opentrons OT-2 96 Tip Rack 300 µL on slot 1"
    asp = "Aspirating 10.0 uL from A1 of Agilent 1 Well Reservoir 290 mL on slot 3 at 92.86 uL/sec"
    disp = "Dispensing 10.0 uL into {w} of Corning 96 Well Plate 360 µL Flat on slot 2 at 92.86 uL/sec"
    lines = [tip]
    for c in range(1, 13):
        lines += [asp, disp.format(w=f"A{c}")]
    lines.append("Dropping tip into Trash Bin on slot 12")
    r = replay("\n".join(lines))                      # 26 actions
    assert r["steps"] == 26 and not r["errors"]
    assert float(r["plate_ul"][0].sum()) == 120 and not r["tip_attached"]


def test_faults_after_all_criteria_pass_are_still_seen():
    *head, drop = (L1 / "run_log.txt").read_text().strip().splitlines()
    extra = "Dispensing 100.0 uL into C3 of Corning 96 Well Plate 360 µL Flat on slot 2 at 274.7 uL/sec"
    r = replay("\n".join(head + [extra, drop]))       # T1-T6 all pass before this; a 3rd dispense empties nothing
    assert any(e == "overdispense" for _, e in r["errors"])
