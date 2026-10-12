"""replay_log.py plus fault annotation: red caption at the faulty event, red pins on affected wells.

usage: replay_fault.py <events.json> <faults.json> <task> <label> <seconds_per_event> <out.mp4>
"""
import asyncio, json, sys
import replay_log
from replay_log import LogReplay
from pylabrobot.resources import Coordinate, Resource


class FaultReplay(LogReplay):
  def __init__(self, log, task, faults):
    super().__init__(log, task)
    self.faults = faults
    self.at = {}
    for f in faults:
      if f["i"] is not None:
        self.at.setdefault(f["i"], []).append(f)
    self.pins = 0
    self.red = lambda on: None

  def pin(self, slot, well):
    lw = self.by_slot.get(slot)
    if lw is None:
      return
    v = self._vessel(lw, well)
    loc = v.get_absolute_location() + Coordinate(v.get_size_x() / 2 - 4, v.get_size_y() / 2 - 4, v.get_size_z() + 10)
    self.pins += 1
    self.facility.assign_child_resource(
      Resource(name=f"fault_{self.pins}", size_x=8, size_y=8, size_z=45, category="finger"), location=loc)

  async def run(self, label):
    self.fill()
    n = sum(1 for f in self.faults if f.get("severity") != "note")
    self.caption(f"{label}: start  ({n} fault{'s' if n != 1 else ''} vs oracle)")
    await asyncio.sleep(1.5)
    last = ""
    for i, ev in enumerate(self.events):
      k = ev["kind"]
      if k == "comment":
        last = ev["text"][:110]
        self.caption(f"{label} | {last}")
        await asyncio.sleep(0.6)
      elif k == "pick":
        await self.pick(ev)
      elif k == "drop":
        await self.drop_tip()
      elif k in ("aspirate", "dispense"):
        vessels, mult = self.targets(ev)
        await self.move_to(vessels[0], dz=5)
        for v in vessels:
          vol = ev["volume"] * mult
          if k == "aspirate":
            if v.tracker.get_used_volume() < vol:
              v.tracker.set_volume(min(v.max_volume, vol))
            v.tracker.remove_liquid(min(vol, v.tracker.get_used_volume()))
          else:
            v.tracker.add_liquid(min(vol, v.tracker.get_free_volume()))
      elif k == "delay":
        self.caption(f"{label} | {last}  [delay {ev['seconds']:.0f} s]")
        await asyncio.sleep(0.4)
      elif k in ("engage", "disengage", "temp"):
        self.caption(f"{label} | " + {"engage": "magnet ENGAGED", "disengage": "magnet disengaged"}.get(k, f"temp {ev.get('celsius')} C"))
        await asyncio.sleep(0.4)
      for f in self.at.get(i, []):
        for w in f["wells"]:
          self.pin(f["slot"], w)
        self.red(True)
        self.caption(f"FAULT ({f['kind']}): {f['msg']}")
        await asyncio.sleep(2.5)
        self.red(False)
        self.caption(f"{label} | {last}  [{self.pins} faulty well(s) pinned red]")
    faults = [f for f in self.faults if f.get("severity") != "note"]
    notes = [f for f in self.faults if f.get("severity") == "note"]
    if faults:
      self.red(True)
      self.caption(f"{label}: {len(faults)} fault(s): " + " | ".join(f["msg"][:70] for f in faults)[:230])
      await asyncio.sleep(4.0)
      self.red(False)
    if notes:
      self.caption(f"{label}: notes vs authors' script: " + " | ".join(f["msg"] for f in notes))
      await asyncio.sleep(3.0)
    if not faults:
      self.caption(f"{label}: matches the oracle, no faults")
      await asyncio.sleep(3.0)


async def main(events, faults_path, task, label, per_event, out_path):
  replay_log.LogReplay = lambda log, task: FaultReplay(log, task, json.load(open(faults_path)))
  orig_main = replay_log.main
  # reuse replay_log.main's recording, adding a red-caption toggle once the page exists
  import types
  src = open(replay_log.__file__).read()
  src = src.replace('rp.caption = lambda text:', 'rp.red = lambda on: loop.create_task(page.evaluate("o => { document.getElementById(\'cap\').style.background = o ? \'rgba(200,20,40,.92)\' : \'rgba(0,0,0,.75)\'; }", on))\n    rp.caption = lambda text:')
  ns = {}
  exec(compile(src.split('if __name__ == "__main__":')[0], replay_log.__file__, "exec"), ns)
  ns["LogReplay"] = lambda log, task: FaultReplay(log, task, json.load(open(faults_path)))
  await ns["main"](events, task, label, per_event, out_path, out_path + ".state.json")


if __name__ == "__main__":
  asyncio.run(main(*sys.argv[1:7]))
