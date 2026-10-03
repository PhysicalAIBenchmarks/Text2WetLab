"""Deterministic volume bookkeeping over a Protocol. No LLM, no deck/tip simulation."""

import re

from .models import CAPACITY_UL, CheckIssue, Protocol

ROWS = "ABCDEFGH"
EPS = 1e-6


def expand_wells(wells: list[str], kind: str) -> list[str]:
    """['A1:A3', 'B1'] -> ['A1','A2','A3','B1']. Tubes (empty list) -> ['']."""
    if not wells:
        return [""]
    out = []
    for w in wells:
        w = w.strip().upper().replace("-", ":").replace("–", ":")
        if ":" in w:
            a, b = w.split(":", 1)
            ra, ca = _rc(a)
            rb, cb = _rc(b)
            for r in range(min(ra, rb), max(ra, rb) + 1):
                for c in range(min(ca, cb), max(ca, cb) + 1):
                    out.append(f"{ROWS[r]}{c}")
        else:
            if kind.startswith("plate_96"):
                _rc(w)  # validate
            out.append(w)
    return out


def _rc(w: str) -> tuple[int, int]:
    m = re.fullmatch(r"([A-H])(\d{1,2})", w)
    if not m or not 1 <= int(m.group(2)) <= 12:
        raise ValueError(f"bad 96-well position {w!r}")
    return ROWS.index(m.group(1)), int(m.group(2))


def _loc(container: str, well: str) -> str:
    return f"{container} {well}" if well else container


def check(p: Protocol) -> list[CheckIssue]:
    issues: list[CheckIssue] = []
    kinds = {c.name: c.kind for c in p.containers}
    # volume per (container, well); None = stock with ample volume; missing = never filled
    vol: dict[tuple[str, str], float | None] = {}

    def err(step, msg, sev="error"):
        issues.append(CheckIssue(step=step, severity=sev, message=msg))

    def wells_of(step, container, wells):
        try:
            return expand_wells(wells, kinds.get(container, ""))
        except ValueError as e:
            err(step, str(e))
            return []

    for c in p.initial_contents:
        if c.container not in kinds:
            err(0, f"initial contents reference unknown container {c.container!r}")
            continue
        for w in wells_of(0, c.container, c.wells):
            prev = vol.get((c.container, w), 0.0)
            vol[(c.container, w)] = None if c.volume_ul is None or prev is None else prev + c.volume_ul

    for i, s in enumerate(p.steps, 1):
        if s.kind == "manual":
            if not s.action.strip():
                err(i, "manual step has no action text", "warning")
            continue

        if s.dest not in kinds:
            err(i, f"unknown destination container {s.dest!r}")
            continue
        if s.volume_ul is None or s.volume_ul <= 0:
            err(i, f"{s.kind} step has no positive volume")
            continue
        dests = wells_of(i, s.dest, s.dest_wells)

        if s.kind == "mix":
            for d in dests:
                cur = vol.get((s.dest, d))
                if cur is not None and s.volume_ul > cur + EPS:
                    err(i, f"mix volume {s.volume_ul:g} µL exceeds contents of {_loc(s.dest, d)} ({cur:g} µL)", "warning")
                    break
            continue

        # transfer
        if s.source not in kinds:
            err(i, f"unknown source container {s.source!r}")
            continue
        srcs = wells_of(i, s.source, s.source_wells)
        if not srcs or not dests:
            continue
        if len(srcs) == 1:
            pairs = [(srcs[0], d) for d in dests]
        elif len(srcs) == len(dests):
            pairs = list(zip(srcs, dests))
        elif len(dests) == 1:
            pairs = [(sw, dests[0]) for sw in srcs]  # pooling
        else:
            err(i, f"{len(srcs)} source wells cannot pair with {len(dests)} destination wells")
            continue

        reported = set()
        for sw, dw in pairs:
            skey, dkey = (s.source, sw), (s.dest, dw)
            if skey not in vol:
                if "unfilled" not in reported:
                    err(i, f"draws from {_loc(s.source, sw)} before anything was put there")
                    reported.add("unfilled")
                vol[skey] = None  # don't cascade
            elif vol[skey] is not None:
                vol[skey] -= s.volume_ul
                if vol[skey] < -EPS and "over" not in reported:
                    err(i, f"withdraws more than {_loc(s.source, sw)} holds (short by {-vol[skey]:g} µL)")
                    reported.add("over")
            if kinds[s.dest] == "waste":
                continue
            cur = vol.get(dkey, 0.0)
            vol[dkey] = None if cur is None else cur + s.volume_ul
            cap = CAPACITY_UL.get(kinds[s.dest])
            if cap is not None and vol[dkey] is not None and vol[dkey] > cap + EPS and "cap" not in reported:
                err(i, f"{_loc(s.dest, dw)} reaches {vol[dkey]:g} µL, above {kinds[s.dest]} capacity {cap:g} µL")
                reported.add("cap")
    return issues
