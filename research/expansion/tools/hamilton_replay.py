"""3D replay of a Hamilton STARlet run log (from the t2w-sim container) on PyLabRobot's STARlet model.

usage: hamilton_replay.py <log.json> <label> <seconds_per_event> <out.mp4>
Rebuilds the authors' APE deck on a simulated STARlet (with its meshes), moves the X-arm to each target,
updates tip and volume trackers, and moves the binding plate onto the magnet and back.
"""
import asyncio, json, sys

import replay_log
from pylabrobot.hamilton.star.device import STARlet
from pylabrobot.resources import Coordinate, Resource, set_tip_tracking, set_volume_tracking
from pylabrobot.resources.agenbio.plates import AGenBio_1_troughplate_100000uL_Fl
from pylabrobot.resources.alpaqua.magnetic_racks import Alpaqua_96_magnum_flx
from pylabrobot.resources.bioer.plates import BioER_96_wellplate_Vb_2200uL
from pylabrobot.resources.diy.grindbio.modules import Hamilton_MFX_plateholder_DWP_metal_tapped_10mm_3dprint
from pylabrobot.resources.hamilton.mfx_carriers import MFX_CAR_L5_base
from pylabrobot.resources.hamilton.mfx_modules import Hamilton_MFX_plateholder_DWP_metal_tapped
from pylabrobot.resources.hamilton.tip_carriers import TIP_CAR_480_A00
from pylabrobot.resources.hamilton.tip_racks import hamilton_96_tiprack_1000uL
from pylabrobot.visualizer3D.facility import Facility


class HamiltonReplay:
  def __init__(self, log, task):
    set_tip_tracking(True)
    set_volume_tracking(True)
    self.facility = Facility(name="facility", size_x=2000, size_y=1200, size_z=1000)
    self.star = STARlet(simulation=True)
    self.facility.assign_child_resource(self.star, location=Coordinate(0, 0, 0))
    deck = self.star.deck
    self.focus_name = deck.name
    tip_car = TIP_CAR_480_A00("tip_car")
    deck.assign_child_resource(tip_car, rails=25)
    for i in range(3):
      tip_car[i] = hamilton_96_tiprack_1000uL(f"tips_0{i}")
    m13 = {i: Hamilton_MFX_plateholder_DWP_metal_tapped_10mm_3dprint(n) for i, n in enumerate(
      ["rail13_mag_module", "rail13_waste_module", "rail13_elution_plate_module", "rail13_wash1_module", "rail13_wash2_module"])}
    deck.assign_child_resource(MFX_CAR_L5_base("car_13", modules=m13), rails=13)
    for i, r in enumerate([Alpaqua_96_magnum_flx("mag_plate"), AGenBio_1_troughplate_100000uL_Fl("waste_trough"),
                           BioER_96_wellplate_Vb_2200uL("elution_plate"), AGenBio_1_troughplate_100000uL_Fl("wash1_trough"),
                           AGenBio_1_troughplate_100000uL_Fl("wash2_trough")]):
      m13[i].assign_child_resource(r)
    m19 = {i: Hamilton_MFX_plateholder_DWP_metal_tapped(n) for i, n in enumerate(
      ["rail19_binding_module", "rail19_source_module", "rail19_flowthrough_module", "rail19_binding_trough_module", "rail19_elution_trough_module"])}
    deck.assign_child_resource(MFX_CAR_L5_base("car_19", modules=m19), rails=19)
    for i, r in enumerate([BioER_96_wellplate_Vb_2200uL("binding_plate"), BioER_96_wellplate_Vb_2200uL("source_plate"),
                           BioER_96_wellplate_Vb_2200uL("flowthrough_plate"), AGenBio_1_troughplate_100000uL_Fl("binding_trough"),
                           AGenBio_1_troughplate_100000uL_Fl("elution_trough")]):
      m19[i].assign_child_resource(r)
    for name in ("source_plate",):
      for w in deck.get_resource(name).get_all_items():
        w.tracker.set_volume(350)
    for name in ("binding_trough", "wash1_trough", "wash2_trough", "elution_trough"):
      for w in deck.get_resource(name).get_all_items():
        w.tracker.set_volume(w.max_volume * 0.9)
    self.head = Resource(name="channels", size_x=20, size_y=70, size_z=120, category="pipette")
    self.facility.assign_child_resource(self.head, location=Coordinate(800, 300, 450))
    self.events = log["events"]
    self.caption = lambda t: None
    self.delay = 0.05
    self.topped_up = 0

  def get(self, name):
    deck = self.star.deck
    return deck.get_resource(name) if deck.has_resource(name) else None

  async def move_to(self, res):
    loc = res.get_absolute_location() + Coordinate(res.get_size_x() / 2 - 10, -20, res.get_size_z() + 40)
    self.facility.unassign_child_resource(self.head)
    self.facility.assign_child_resource(self.head, location=loc)
    try:
      await self.star.x_arm.move_to_x_position(round(min(max(loc.x, 0), 1000), 1))
    except Exception:
      pass
    await asyncio.sleep(self.delay)

  async def run(self, label):
    try:
      await self.star.setup()
    except Exception:
      pass
    self.caption(f"{label}: start")
    await asyncio.sleep(1.5)
    last_move = None
    for ev in self.events:
      k = ev["kind"]
      if k == "comment":
        self.caption(f"{label} | {ev['text'][:110]}")
        await asyncio.sleep(0.15)
      elif k == "delay":
        await asyncio.sleep(0.1)
      elif k == "pick":
        spots = [self.get(n) for n in ev["spots"]]
        spots = [s for s in spots if s is not None]
        if spots:
          await self.move_to(spots[0])
          for s in spots:
            if s.tracker.has_tip:
              s.tracker.remove_tip()
      elif k == "drop":
        spots = [self.get(n) for n in ev["spots"]]
        spots = [s for s in spots if s is not None and hasattr(s, "tracker")]
        if spots:
          await self.move_to(spots[0])
          for s in spots:
            if not s.tracker.has_tip:
              s.tracker.add_tip(s.make_tip())
      elif k in ("aspirate", "dispense"):
        wells = [(self.get(n), v) for n, v in zip(ev["wells"], ev["vols"])]
        wells = [(w, v) for w, v in wells if w is not None and hasattr(w, "tracker")]
        if not wells:
          continue
        await self.move_to(wells[0][0])
        for w, v in wells:
          if k == "aspirate":
            if w.tracker.get_used_volume() < v:
              w.tracker.set_volume(min(w.max_volume, v))
              self.topped_up += 1
            w.tracker.remove_liquid(min(v, w.tracker.get_used_volume()))
          else:
            w.tracker.add_liquid(min(v, w.tracker.get_free_volume()))
      elif k == "move":
        key = (ev["plate"], ev["to"])
        if key == last_move:
          continue
        last_move = key
        plate, dest = self.get(ev["plate"]), self.get(ev["to"])
        if plate is None or dest is None:
          continue
        await self.move_to(plate)
        plate.parent.unassign_child_resource(plate)
        dest.assign_child_resource(plate)
        self.caption(f"{label} | CoRe gripper: {ev['plate']} -> {ev['to']}")
        await asyncio.sleep(0.8)
    self.caption(f"{label}: finished ({len(self.events)} robot events)")
    await asyncio.sleep(3.0)

  def final_state(self):
    return {}


async def main(log_path, label, per_event, out):
  replay_log.LogReplay = HamiltonReplay
  await replay_log.main(log_path, "hamilton", label, per_event, out, out + ".state.json")


if __name__ == "__main__":
  asyncio.run(main(*sys.argv[1:5]))
