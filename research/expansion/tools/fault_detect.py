"""Align a model's Opentrons run log against the oracle's and list faults, deterministically.

usage: fault_detect.py <logs_dir> <task> [--md]
Fault kinds (each tied to the model event index where it first shows, and the wells it touches):
  volume      same source -> destination well, total volume off by >5% from the oracle
  missing     a source -> destination flow the oracle has and the model never does
  extra       a source -> destination flow the model does and the oracle never does
  order       reagents reach a destination in a different first-addition order
  mix         pipette-mixing in a well the oracle never mixes
  timing      total protocol delays < 60% of the oracle's
  magnet      fewer magnet engage cycles than the oracle
"""
import collections, json, re, sys

ROWS = "ABCDEFGH"


def slot(key):
  return int(re.findall(r"on (\d+)$", key)[0])


def short(key):
  return re.sub(r" on .*$", "", key)


def parse(path):
  log = json.load(open(path))
  ev, loads = log["events"], {slot(k): v for k, v in log["labware"].items()}
  plate96 = lambda key: "96" in loads.get(slot(key), "") and "tiprack" not in loads.get(slot(key), "")
  transfers, mixes, delay, engages, sources = [], [], 0.0, 0, set()
  pending = None
  for i, e in enumerate(ev):
    k = e["kind"]
    if k == "delay":
      delay += e["seconds"]
    elif k == "engage":
      engages += 1
    elif k == "aspirate":
      pending = e
    elif k == "dispense" and pending is not None:
      a, ch = pending, e["channels"]
      cols = lambda w, key: [f"{r}{re.findall(r'\d+', w)[0]}" for r in ROWS] if ch == 8 and plate96(key) else [w]
      if slot(a["labware"]) == slot(e["labware"]) and a["well"] == e["well"]:
        mixes.append(dict(i=i, slot=slot(e["labware"]), wells=cols(e["well"], e["labware"]), name=short(e["labware"])))
      else:
        src = (slot(a["labware"]), "*" if plate96(a["labware"]) or "tuberack" in loads.get(slot(a["labware"]), "") else a["well"])
        sources.add((slot(a["labware"]), a["well"]))
        for w in cols(e["well"], e["labware"]):
          transfers.append(dict(i=i, src=src, src_name=short(a["labware"]), dst=slot(e["labware"]),
                                dst_well=w, dst_name=short(e["labware"]), vol=e["volume"]))
      pending = None
  return dict(n=len(ev), transfers=transfers, mixes=mixes, delay=delay, engages=engages, sources=sources)


def src_label(t):
  s, w = t["src"]
  return f"{t['src_name']}" + (f" {w}" if w != "*" else "") + f" (slot {s})"


def faults(oracle, model):
  out = []
  # total volume and well count per (source, destination slot): well layouts may legitimately differ
  def agg(run):
    tot, wells, first = collections.Counter(), collections.defaultdict(set), {}
    for t in run["transfers"]:
      k = (t["src"], t["dst"])
      tot[k] += t["vol"]; wells[k].add(t["dst_well"]); first.setdefault(k, t)
    return tot, wells, first
  vo, wo, fo = agg(oracle)
  vm, wm, first = agg(model)
  groups = {}
  for k in set(vo) | set(vm):
    a, b = vo.get(k, 0), vm.get(k, 0)
    if a and b and abs(a - b) > 0.05 * a:
      groups[k] = ("volume", a / len(wo[k]), b / len(wm[k]), sorted(wm[k]))
    elif a and not b:
      groups[k] = ("missing", a / len(wo[k]), 0, [])
    elif b and not a:
      groups[k] = ("extra", 0, b / len(wm[k]), sorted(wm[k]))
  o_src_names = {t["src"]: src_label(t) for t in oracle["transfers"]}
  for (src, dst), (kind, a, b, wells) in groups.items():
    t0 = first.get((src, dst)) or fo.get((src, dst))
    i = first[(src, dst)]["i"] if (src, dst) in first else None
    name, dname = src_label(t0), t0["dst_name"]
    if kind == "volume":
      tm, to = vm[(src, dst)], vo[(src, dst)]
      msg = (f"{b:g} uL {name} -> {dname} per well; oracle {a:g} uL" if len(wm[(src, dst)]) == len(wo[(src, dst)])
             else f"{tm:,.0f} uL total {name} -> {dname}; oracle {to:,.0f} uL ({(tm - to) / to:+.0%})")
    elif kind == "missing":
      msg = f"never moves {name} -> {dname} (oracle {a:g} uL into each of {len(wo[(src, dst)])} wells)"
    else:
      msg = f"extra transfer {name} -> {dname} ({b:g} uL x {len(wells)} wells; oracle none)"
    out.append(dict(kind=kind, i=i, slot=dst, wells=wells, msg=msg))
  # first-addition order into each destination slot
  def order(run):
    seen = collections.defaultdict(list)
    for t in run["transfers"]:
      if t["src"] not in [s for s, _ in seen[t["dst"]]]:
        seen[t["dst"]].append((t["src"], t))
    return seen
  oo, mo = order(oracle), order(model)
  for dst in mo:
    common = [s for s, _ in oo.get(dst, []) if s in [x for x, _ in mo[dst]]]
    mseq = [(s, t) for s, t in mo[dst] if s in common]
    for pos, (s, t) in enumerate(mseq):
      if s != common[pos]:
        expected = next(t2 for s2, t2 in oo[dst] if s2 == common[pos])
        out.append(dict(kind="order", i=t["i"], slot=dst, wells=[t["dst_well"]],
                        msg=f"adds {src_label(t)} to {t['dst_name']} before {src_label(expected)} (oracle order differs)"))
        break
  # mixing where the oracle never mixes
  omix = {(m["slot"], w) for m in oracle["mixes"] for w in m["wells"]}
  flagged = set()
  for m in model["mixes"]:
    new = [w for w in m["wells"] if (m["slot"], w) not in omix and (m["slot"], w) not in flagged
           and (m["slot"], w) not in model["sources"]]
    if new:
      flagged |= {(m["slot"], w) for w in new}
      out.append(dict(kind="mix", i=m["i"], slot=m["slot"], wells=new,
                      msg=f"pipette-mixes {m['name']} {','.join(new[:4])} (oracle never mixes here)"))
  if oracle["delay"] and model["delay"] < 0.6 * oracle["delay"]:
    out.append(dict(kind="timing", i=None, slot=None, wells=[],
                    msg=f"total waits {model['delay']/60:.0f} min vs oracle {oracle['delay']/60:.0f} min", severity="note"))
  if model["engages"] < oracle["engages"]:
    out.append(dict(kind="magnet", i=None, slot=None, wells=[],
                    msg=f"magnet engaged {model['engages']}x vs oracle {oracle['engages']}x", severity="note"))
  # collapse repeated per-well mix faults into one entry per slot
  return sorted(out, key=lambda f: (f["i"] is None, f["i"] or 0))


MODELS = {"claude-opus-5-5": "Opus 5.5", "claude-sonnet-5-5": "Sonnet 5.5", "claude-fable-5-1": "Fable 5.1"}

if __name__ == "__main__":
  logs, task = sys.argv[1], sys.argv[2]
  o = parse(f"{logs}/{task}.oracle.json")
  result = {}
  for m, name in MODELS.items():
    fs = faults(o, parse(f"{logs}/{task}.{m}.json"))
    result[m] = fs
    json.dump(fs, open(f"{logs}/{task}.{m}.faults.json", "w"), indent=1)
    if "--md" in sys.argv:
      print(f"- **{name}**: " + ("no faults vs oracle" if not fs else ""))
      for f in fs:
        print(f"  - {'note' if f.get('severity') == 'note' else 'FAULT'} `{f['kind']}` {f['msg']}")
