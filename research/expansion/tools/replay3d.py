"""Replay a Text2WetLab task in PyLabRobot's 3D viewer and record it to a video.

usage: replay3d.py <task_dir> <out_dir> [--live]
Builds the task's OT-2 deck from tests/deck.json, fills it from tests/ir.json, then walks the IR
steps: a pipette marker moves tip rack -> source -> destination while the volume and tip trackers
update, which the viewer draws. Manual (non-pipetting) steps are shown as captions.
"""
import asyncio, json, os, re, sys, string, shutil

from pylabrobot.resources import set_volume_tracking, set_tip_tracking, Coordinate, Resource, Tube
from pylabrobot.resources.opentrons import (
  OTDeck, opentrons_96_tiprack_20ul, opentrons_96_tiprack_300ul, opentrons_96_filtertiprack_200ul,
  opentrons_96_filtertiprack_1000ul)
from pylabrobot.resources.opentrons.tube_racks import (
  opentrons_24_tuberack_eppendorf_1_5ml_safelock_snapcap,
  opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap, opentrons_6_tuberack_falcon_50ml_conical,
  opentrons_15_tuberack_falcon_15ml_conical)
from pylabrobot.resources.corning import cor_96_wellplate_360uL_Fb
from pylabrobot.resources.biorad import biorad_96_wellplate_200uL_Vb
from pylabrobot.resources.nest import (
  nest_1_troughplate_195000uL_Vb, nest_12_troughplate_15000uL_Vb, NEST_96_wellplate_2200uL_Ub)
from pylabrobot.visualizer3D.server import Viewer3D
from pylabrobot.visualizer3D.facility import Facility

LABWARE = {
  "corning_96_wellplate_360ul_flat": cor_96_wellplate_360uL_Fb,
  "biorad_96_wellplate_200ul_pcr": biorad_96_wellplate_200uL_Vb,
  "nest_1_reservoir_195ml": nest_1_troughplate_195000uL_Vb,
  "nest_12_reservoir_15ml": nest_12_troughplate_15000uL_Vb,
  "opentrons_96_tiprack_20ul": opentrons_96_tiprack_20ul,
  "opentrons_96_tiprack_300ul": opentrons_96_tiprack_300ul,
  "opentrons_96_filtertiprack_200ul": opentrons_96_filtertiprack_200ul,
  "opentrons_96_filtertiprack_1000ul": opentrons_96_filtertiprack_1000ul,
  "opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap": opentrons_24_tuberack_eppendorf_1_5ml_safelock_snapcap,
  "opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap": opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap,
  "opentrons_6_tuberack_falcon_50ml_conical": opentrons_6_tuberack_falcon_50ml_conical,
  "opentrons_15_tuberack_falcon_15ml_conical": opentrons_15_tuberack_falcon_15ml_conical,
  # stand-ins (no exact PyLabRobot definition)
  "usascientific_96_wellplate_2.4ml_deep": NEST_96_wellplate_2200uL_Ub,
  "thermo_96_wellplate_200ul": biorad_96_wellplate_200uL_Vb,
}

ROWS = string.ascii_uppercase


def expand(spec):
  """['A1:H12'] -> column-major well names; plain names pass through."""
  out = []
  for s in spec:
    m = re.fullmatch(r"([A-P])(\d+):([A-P])(\d+)", s)
    if not m:
      out.append(s)
      continue
    r0, c0, r1, c1 = ROWS.index(m[1]), int(m[2]), ROWS.index(m[3]), int(m[4])
    for c in range(c0, c1 + 1):
      for r in range(r0, r1 + 1):
        out.append(f"{ROWS[r]}{c}")
  return out


class Replay:
  def __init__(self, deck_spec, ir):
    set_volume_tracking(True)
    set_tip_tracking(True)
    self.ir = ir
    self.facility = Facility(name="lab", size_x=800, size_y=700, size_z=400)
    self.deck = OTDeck(with_trash=True)
    self.facility.assign_child_resource(self.deck, location=Coordinate(0, 0, 0))
    self.labware, self.containers, self.tipracks = {}, {}, {}
    for slot, s in sorted(deck_spec["slots"].items(), key=lambda kv: int(kv[0])):
      lw = LABWARE[s["load_name"]](name=s["label"])
      self.deck.assign_child_at_slot(lw, int(slot))
      self.labware[s["label"]] = lw
    for key, t in deck_spec["tips"].items():
      rack = LABWARE[t["load_name"]](name=f"tips_{key}ul")
      self.deck.assign_child_at_slot(rack, int(t["slot"]))
      self.tipracks[key] = rack
    for name, c in deck_spec.get("containers", {}).items():
      self.containers[name] = (c["label"], c.get("well"))
    self.head = Resource(name="pipette", size_x=14, size_y=14, size_z=90, category="pipette")
    self.facility.assign_child_resource(self.head, location=Coordinate(300, 300, 160))
    self.caption = lambda text: None
    self.delay = 0.1

  def wells(self, container, spec):
    label, default_well = self.containers.get(container, (container, None))
    lw = self.labware[label]
    names = expand(spec) if spec else [default_well or "A1"]
    return [self._vessel(lw, n) for n in names]

  @staticmethod
  def _vessel(lw, well):
    item = lw.get_item(well)
    if hasattr(item, "tracker"):
      return item
    if item.children:  # a tube already sits in this rack position
      return item.children[0]
    cap = 50000 if "50ml" in lw.name or "50" in str(lw.model) else (
      15000 if "15ml" in str(lw.model) else 2000 if "2ml" in str(lw.model) else 1500)
    tube = Tube(name=f"{lw.name}_{well}_tube", size_x=item.get_size_x() * 0.8,
                size_y=item.get_size_y() * 0.8, size_z=max(20.0, lw.get_size_z() * 0.9), max_volume=cap)
    item.assign_child_resource(tube)
    return tube

  def fill(self):
    for c in self.ir["initial_contents"]:
      for w in self.wells(c["container"], c["wells"]):
        cap = w.max_volume
        vol = c["volume_ul"] if c["volume_ul"] is not None else cap * 0.8
        w.tracker.set_volume(min(vol, cap))

  async def move_to(self, resource, dz=30.0):
    loc = resource.get_absolute_location() + Coordinate(
      resource.get_size_x() / 2 - 7, resource.get_size_y() / 2 - 7, resource.get_size_z() + dz)
    self.facility.unassign_child_resource(self.head)
    self.facility.assign_child_resource(self.head, location=loc)
    await asyncio.sleep(self.delay)

  def rack_for(self, vol):
    keys = sorted(self.tipracks, key=float)
    for k in keys:
      if vol <= float(k):
        return self.tipracks[k]
    return self.tipracks[keys[-1]]

  async def pick_tip(self, vol):
    rack = self.rack_for(vol)
    spots = [s for s in rack.get_all_items() if s.tracker.has_tip]
    if not spots:  # reset_tipracks(): the operator refills the rack
      for s in rack.get_all_items():
        s.tracker.add_tip(s.make_tip())
      spots = rack.get_all_items()
    await self.move_to(spots[0])
    spots[0].tracker.remove_tip()

  async def drop_tip(self):
    trash = self.deck.get_trash_area() if hasattr(self.deck, "get_trash_area") else None
    if trash is not None:
      await self.move_to(trash)

  @staticmethod
  def move_liquid(src, dst, vol):
    have = src.tracker.get_used_volume()
    if have < vol:  # "plenty" sources: top up rather than fail
      src.tracker.set_volume(min(src.max_volume, have + vol))
    src.tracker.remove_liquid(vol)
    room = dst.tracker.get_free_volume()
    dst.tracker.add_liquid(min(vol, room))

  def count_ops(self):
    n = 0
    for s in self.ir["steps"]:
      if s["kind"] == "transfer":
        n += max(len(expand(s["source_wells"]) or [1]), len(expand(s["dest_wells"]) or [1]))
      elif s["kind"] == "mix":
        n += len(expand(s["dest_wells"]) or [1])
    return n

  async def run(self, seconds=50.0):
    ops = max(1, self.count_ops())
    self.delay = min(0.5, max(0.025, seconds / ops / 3))
    self.fill()
    self.caption(self.ir.get("title", ""))
    await asyncio.sleep(2.0)
    for i, s in enumerate(self.ir["steps"], 1):
      if s["kind"] == "manual":
        self.caption(f"Step {i} (manual, not pipetted): {s['action']}")
        await asyncio.sleep(1.8)
        continue
      if s["kind"] == "mix":
        self.caption(f"Step {i}: mix {s['dest']} {', '.join(s['dest_wells']) or ''} x{s['mix_cycles']}")
        await self.pick_tip(s["volume_ul"] or 20)
        for w in self.wells(s["dest"], s["dest_wells"]):
          await self.move_to(w, dz=5)
          await self.move_to(w, dz=25)
        await self.drop_tip()
        continue
      vol = float(s["volume_ul"])
      src = self.wells(s["source"], s["source_wells"])
      dst = self.wells(s["dest"], s["dest_wells"])
      mix = f", mix x{s['mix_cycles']}" if s.get("mix_cycles") else ""
      self.caption(f"Step {i}: {vol:g} uL {s.get('reagent') or ''} {s['source']} -> {s['dest']} "
                   f"({max(len(src), len(dst))} wells{mix})")
      if len(src) == 1:
        pairs = [(src[0], d) for d in dst]
      elif len(dst) == 1:
        pairs = [(sw, dst[0]) for sw in src]
      else:
        pairs = list(zip(src, dst))
      one_tip = len(src) == 1  # shared reagent: one tip for the step
      if one_tip:
        await self.pick_tip(vol)
      for sw, dw in pairs:
        if not one_tip:
          await self.pick_tip(vol)
        await self.move_to(sw, dz=5)
        await self.move_to(dw, dz=5)
        self.move_liquid(sw, dw, vol)
        if not one_tip:
          await self.drop_tip()
      if one_tip:
        await self.drop_tip()
    self.caption("Done: final volumes shown on the deck")
    await asyncio.sleep(3.0)


RNA_DECK = {
  "slots": {
    "1": {"load_name": "usascientific_96_wellplate_2.4ml_deep", "label": "waste_plate"},
    "4": {"load_name": "usascientific_96_wellplate_2.4ml_deep", "label": "mag_plate"},
    "5": {"load_name": "nest_12_reservoir_15ml", "label": "reservoir"},
    "6": {"load_name": "thermo_96_wellplate_200ul", "label": "elution_plate"},
    "10": {"load_name": "opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap", "label": "samples_1_24"},
    "7": {"load_name": "opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap", "label": "samples_25_48"},
  },
  "tips": {"200": {"load_name": "opentrons_96_filtertiprack_200ul", "slot": 2},
           "1000": {"load_name": "opentrons_96_filtertiprack_1000ul", "slot": 11}},
  "containers": {},
}
ODD = [f"{r}{c}" for c in (1, 3, 5, 7, 9, 11) for r in "ABCDEFGH"]
TUBES = [f"{r}{c}" for c in range(1, 7) for r in "ABCD"]


def rna_ir():
  t = lambda src, sw, dst, dw, v, reagent, mix=None: {
    "kind": "transfer", "source": src, "source_wells": sw, "dest": dst, "dest_wells": dw,
    "volume_ul": v, "reagent": reagent, "mix_cycles": mix}
  m = lambda a: {"kind": "manual", "action": a}
  return {
    "title": "Magnetic-bead SARS-CoV-2 RNA extraction, 48 samples (PLOS ONE 2021)",
    "initial_contents": [
      {"container": "reservoir", "wells": ["A2", "A4", "A6", "A7", "A9", "A10", "A11", "A12"],
       "volume_ul": None},
      {"container": "samples_1_24", "wells": TUBES, "volume_ul": 300},
      {"container": "samples_25_48", "wells": TUBES, "volume_ul": 300},
    ],
    "steps": [
      m("Magnet disengaged; temperature module to 4 C"),
      t("reservoir", ["A2"], "mag_plate", ODD, 40, "magnetic beads"),
      t("reservoir", ["A6"], "mag_plate", ODD[:24], 250, "isopropanol"),
      t("reservoir", ["A7"], "mag_plate", ODD[24:], 250, "isopropanol"),
      t("samples_1_24", TUBES, "mag_plate", ODD[:24], 250, "sample", 5),
      t("samples_25_48", TUBES, "mag_plate", ODD[24:], 250, "sample", 5),
      m("Incubate 5 min at room temperature"),
      m("Engage magnet, wait 4 min"),
      t("mag_plate", ODD, "waste_plate", ODD, 540, "supernatant"),
      t("reservoir", ["A9"], "mag_plate", ODD[:24], 500, "70% ethanol"),
      t("reservoir", ["A10"], "mag_plate", ODD[24:], 500, "70% ethanol"),
      t("mag_plate", ODD, "waste_plate", ODD, 500, "ethanol wash 1"),
      t("reservoir", ["A11"], "mag_plate", ODD[:24], 500, "70% ethanol"),
      t("reservoir", ["A12"], "mag_plate", ODD[24:], 500, "70% ethanol"),
      t("mag_plate", ODD, "waste_plate", ODD, 500, "ethanol wash 2"),
      m("Air-dry beads 4 min, magnet engaged"),
      m("Disengage magnet"),
      t("reservoir", ["A4"], "mag_plate", ODD, 100, "elution buffer", 5),
      m("Wait 30 s, engage magnet 90 s"),
      t("mag_plate", ODD, "elution_plate", ODD, 80, "eluate (RNA)"),
      m("Disengage magnet; eluate held at 4 C"),
    ],
  }


async def main(task_dir, out_dir, live):
  name = os.path.basename(task_dir.rstrip("/"))
  if name.startswith("opentrons-rna-extraction"):
    deck_spec, ir = RNA_DECK, rna_ir()
  else:
    deck_spec = json.load(open(os.path.join(task_dir, "tests", "deck.json")))
    ir = json.load(open(os.path.join(task_dir, "tests", "ir.json")))
  rp = Replay(deck_spec, ir)
  viewer = Viewer3D(rp.facility, open_browser=live, name=name)
  await viewer.start()
  if live:
    await viewer.wait_for_browser()
    await rp.run()
    await viewer.stop()
    return

  from playwright.async_api import async_playwright
  tmp = os.path.join(out_dir, f".rec_{name}")
  shutil.rmtree(tmp, ignore_errors=True)
  async with async_playwright() as p:
    browser = await p.chromium.launch(headless=True, args=["--use-angle=metal", "--enable-gpu", "--ignore-gpu-blocklist"])
    ctx = await browser.new_context(viewport={"width": 1280, "height": 720},
                                    record_video_dir=tmp, record_video_size={"width": 1280, "height": 720})
    page = await ctx.new_page()
    page.on("console", lambda msg: msg.type == "error" and print("  console:", msg.text[:200]))
    url = viewer.url.replace("/#", "/?view=iso#")
    await page.goto(url)
    await viewer.wait_for_browser(timeout=60)
    for _ in range(120):  # until the scene has actually arrived and been drawn
      if await page.evaluate("() => (window.plrViewer?.resources() || []).length > 0"):
        break
      await asyncio.sleep(0.25)
    for btn in ("#toolbar-right-toggle", "#toolbar-left-toggle"):
      try:
        await page.click(btn, timeout=2000)
      except Exception:
        pass
    await page.add_style_tag(content="#stats-panel,#scale-bar,#zoom-controls,#home-button{display:none!important}")
    await asyncio.sleep(1.0)
    await page.evaluate("() => plrViewer.focus('ot2_deck', 'iso')")
    await asyncio.sleep(0.5)
    await page.keyboard.press("Escape")  # close the inspector the focus opened
    await asyncio.sleep(1.0)
    await page.evaluate("""() => { const d = document.createElement('div'); d.id = 'cap';
      d.style.cssText = 'position:fixed;left:16px;right:16px;bottom:16px;padding:10px 14px;' +
        'background:rgba(0,0,0,.7);color:#fff;font:600 18px system-ui;border-radius:8px;z-index:99999';
      document.body.appendChild(d); }""")
    loop = asyncio.get_running_loop()
    rp.caption = lambda text: loop.create_task(
      page.evaluate("t => { document.getElementById('cap').textContent = t; }", text))
    await rp.run()
    video = page.video
    await ctx.close()
    await browser.close()
    src = await video.path()
  os.makedirs(out_dir, exist_ok=True)
  dst = os.path.join(out_dir, f"{name}.mp4")
  os.system(f'ffmpeg -loglevel error -y -i "{src}" -c:v libx264 -pix_fmt yuv420p -crf 23 "{dst}"')
  shutil.rmtree(tmp, ignore_errors=True)
  await viewer.stop()
  print("wrote", dst)


if __name__ == "__main__":
  asyncio.run(main(sys.argv[1], sys.argv[2], "--live" in sys.argv))
