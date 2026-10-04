#!/usr/bin/env python3
"""Simulate an OT-2 protocol and print its robot actions as JSON events."""
import json
import re
import sys
import traceback

from opentrons import protocol_api, simulate

WELL = r"([A-P]\d{1,2}) (?:of|in) (.+?)(?: at [\d.]+ uL/sec)?$"
PATTERNS = [
    ("aspirate", re.compile(r"^Aspirating ([\d.]+) uL from " + WELL)),
    ("dispense", re.compile(r"^Dispensing ([\d.]+) uL into " + WELL)),
    ("pick", re.compile(r"^Picking up tip")),
    ("drop", re.compile(r"^(?:Dropping|Returning) tip")),
    ("delay", re.compile(r"^Delaying for (\d+) minutes and ([\d.]+) seconds")),
    ("engage", re.compile(r"^Engaging Magnetic Module")),
    ("disengage", re.compile(r"^Disengaging Magnetic Module")),
    ("temp", re.compile(r"^Setting Temperature Module temperature to ([\d.]+)")),
]
INSTRUMENT_KINDS = {"aspirate", "dispense", "pick", "drop"}

_comment = protocol_api.ProtocolContext.comment


def tagged_comment(self, msg):
    return _comment(self, f"COMMENT: {msg}")


def parse(text: str, payload: dict) -> dict | None:
    if text.startswith("COMMENT: "):
        return None
    for kind, pattern in PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        instrument = str(payload.get("instrument", ""))
        if kind in INSTRUMENT_KINDS and not instrument:
            return None
        event = {"kind": kind, "instrument": instrument}
        event["channels"] = 8 if "8-Channel" in instrument else 1
        if kind in {"aspirate", "dispense"}:
            event.update(volume=float(match[1]), well=match[2], labware=match[3])
        elif kind == "delay":
            event["seconds"] = int(match[1]) * 60 + float(match[2])
        elif kind == "temp":
            event["celsius"] = float(match[1])
        return event
    return None


def main(protocol: str, labware_dir: str) -> dict:
    protocol_api.ProtocolContext.comment = tagged_comment
    try:
        with open(protocol) as handle:
            runlog, _ = simulate.simulate(
                handle, protocol, custom_labware_paths=[labware_dir]
            )
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"[-3000:],
                "traceback": traceback.format_exc()[-3000:]}
    events: list[dict] = []
    pending_air = False

    def walk(entries):
        nonlocal pending_air
        for entry in entries:
            payload = entry.get("payload", {})
            text = str(payload.get("text", ""))
            if text.startswith("Air gap"):
                pending_air = True
            event = parse(text, payload)
            if event:
                if pending_air and event["kind"] == "aspirate":
                    event["kind"] = "air"
                    pending_air = False
                events.append(event)
            walk(entry.get("subcommands", []))

    walk(runlog)
    return {"ok": True, "events": events, "n_commands": len(runlog)}


if __name__ == "__main__":
    print(json.dumps(main(sys.argv[1], sys.argv[2])))
