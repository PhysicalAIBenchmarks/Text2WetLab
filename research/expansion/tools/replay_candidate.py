"""3D replay of a third-party Opentrons protocol's run log (from the t2w-sim container).

usage: replay_candidate.py <events.json> <repo_dir> <label> <seconds_per_event> <out.mp4>
The deck comes from the labware the protocol loaded (benchmark map, then the Opentrons library, then
custom labware JSON in the repo). No starting volumes are known, so a source is filled the first time
it is drawn from (counted as `topped_up`).
"""
import asyncio, re, sys

import otdef
import replay_log
from replay3d import LABWARE, Facility
from replay_log import LogReplay, slot_of
from pylabrobot.resources import set_volume_tracking, set_tip_tracking, Coordinate, Resource
from pylabrobot.resources.opentrons import OTDeck


class CandidateReplay(LogReplay):
  def __init__(self, log, task):
    set_volume_tracking(True)
    set_tip_tracking(True)
    self.facility = Facility(name="lab", size_x=800, size_y=700, size_z=400)
    self.deck = OTDeck(with_trash=True)
    self.facility.assign_child_resource(self.deck, location=Coordinate(0, 0, 0))
    self.by_slot, self.key_to_slot, self.missing = {}, {}, []
    for key, load in log["labware"].items():
      try:
        slot = slot_of(key)
      except IndexError:
        continue
      self.key_to_slot[key] = slot
      if slot in self.by_slot or not 1 <= slot <= 11:
        continue
      name = f"s{slot}_{load}"
      lw = LABWARE[load](name=name) if load in LABWARE else otdef.load(load, name)
      if lw is None:
        self.missing.append(load)
        continue
      try:
        self.deck.assign_child_at_slot(lw, slot)
        self.by_slot[slot] = lw
      except Exception:
        self.missing.append(load)
    self.head = Resource(name="pipette", size_x=14, size_y=14, size_z=90, category="pipette")
    self.facility.assign_child_resource(self.head, location=Coordinate(300, 300, 160))
    self.events, self.task = log["events"], task
    self.caption = lambda t: None
    self.delay = 0.02
    self.topped_up = 0

  def fill(self):
    pass  # no starting volumes are known for third-party protocols

  def racks_for(self, instrument):
    racks = [lw for lw in self.by_slot.values() if "tiprack" in lw.name]
    size = re.findall(r"P(\d+)", instrument)
    want = {"20": ("20ul", "10ul"), "300": ("300ul", "200ul"), "50": ("50ul",), "1000": ("1000ul",)}.get(size[0] if size else "", ())
    sized = [lw for lw in racks if any(w in lw.name for w in want)]
    return sized or racks

  def targets(self, ev):
    if slot_of(ev["labware"]) not in self.by_slot:
      return [], 1
    return super().targets(ev)

  async def run(self, label):
    usable = [e for e in self.events if e["kind"] not in ("aspirate", "dispense") or slot_of(e["labware"]) in self.by_slot]
    self.events = usable
    await super().run(label)


def resolve(self, labware_key):
  return self.by_slot[slot_of(labware_key)]


CandidateReplay.resolve = resolve


async def main(events, repo, label, per_event, out):
  otdef.register_custom(repo)
  replay_log.LogReplay = CandidateReplay
  replay_log.initial_fill = lambda task: []
  await replay_log.main(events, "candidate", label, per_event, out, out + ".state.json")


if __name__ == "__main__":
  asyncio.run(main(*sys.argv[1:6]))
