"""Replay an Opentrons run log (from eval/runlog.py + comments) in PyLabRobot's 3D viewer.

usage: replay_log.py <events.json> <task> <label> <seconds_per_event> <out.mp4> <final_state.json>
The deck is rebuilt from the labware the protocol itself loaded; starting contents come from the
task's fixed deck (by slot). Every aspirate/dispense/tip event is applied to the trackers in order.
"""
import asyncio, json, os, re, shutil, sys

from replay3d import LABWARE, Replay, RNA_DECK, rna_ir, expand, Facility, Viewer3D
from pylabrobot.resources import set_volume_tracking, set_tip_tracking, Coordinate, Resource
from pylabrobot.resources.opentrons import OTDeck

TASKS = os.path.expanduser("~/Desktop/Text2WetLab-harbor-results/tasks")
ROWS = "ABCDEFGH"


def slot_of(key):
  return int(re.findall(r"on (\d+)$", key)[0])


def initial_fill(task):
  """[(slot, [wells] or None, volume or None)] from the task's fixed deck."""
  if task.startswith("opentrons-rna-extraction"):
    ir = rna_ir()
    slot_by_label = {s["label"]: int(n) for n, s in RNA_DECK["slots"].items()}
    return [(slot_by_label[c["container"]], c["wells"], c["volume_ul"]) for c in ir["initial_contents"]]
  deck = json.load(open(f"{TASKS}/{task}/tests/deck.json"))
  ir = json.load(open(f"{TASKS}/{task}/tests/ir.json"))
  out = []
  for c in ir["initial_contents"]:
    cont = deck["containers"].get(c["container"], {"slot": None})
    slot = cont["slot"]
    if not isinstance(slot, int):
      slot = int(re.findall(r"(\d+)$", str(slot))[0])
    wells = expand(c["wells"]) if c["wells"] else [cont.get("well") or "A1"]
    out.append((slot, wells, c["volume_ul"]))
  return out


class LogReplay(Replay):
  def __init__(self, log, task):
    set_volume_tracking(True)
    set_tip_tracking(True)
    self.facility = Facility(name="lab", size_x=800, size_y=700, size_z=400)
    self.deck = OTDeck(with_trash=True)
    self.facility.assign_child_resource(self.deck, location=Coordinate(0, 0, 0))
    self.by_slot, self.key_to_slot = {}, {}
    for key, load in log["labware"].items():
      slot = slot_of(key)
      self.key_to_slot[key] = slot
      if slot in self.by_slot:
        continue
      lw = LABWARE[load](name=f"slot{slot}_{load[:20]}")
      self.deck.assign_child_at_slot(lw, slot)
      self.by_slot[slot] = lw
    self.head = Resource(name="pipette", size_x=14, size_y=14, size_z=90, category="pipette")
    self.facility.assign_child_resource(self.head, location=Coordinate(300, 300, 160))
    self.events, self.task = log["events"], task
    self.caption = lambda t: None
    self.delay = 0.02
    self.topped_up = 0
    self.held = {}  # instrument -> volume in tip (for display only)

  def resolve(self, labware_key):
    key = labware_key
    if key not in self.key_to_slot:  # run-log text vs str(labware) mismatch: match on slot
      return self.by_slot[slot_of(key)]
    return self.by_slot[self.key_to_slot[key]]

  def targets(self, ev):
    lw = self.resolve(ev["labware"])
    if ev["channels"] == 8 and len(lw.get_all_items()) >= 96:
      col = re.findall(r"\d+", ev["well"])[0]
      return [self._vessel(lw, f"{r}{col}") for r in ROWS], 1
    return [self._vessel(lw, ev["well"])], ev["channels"]

  def racks_for(self, instrument):
    size = re.findall(r"P(\d+)", instrument)
    size = int(size[0]) if size else 300
    want = {20: ("20ul",), 300: ("300ul", "200ul"), 1000: ("1000ul",)}.get(size, ("300ul",))
    return [lw for lw in self.by_slot.values() if "tiprack" in lw.name and any(w in lw.name for w in want)]

  async def pick(self, ev):
    n = ev["channels"]
    for rack in self.racks_for(ev["instrument"]):
      for c in range(1, 13):
        spots = [rack.get_item(f"{r}{c}") for r in ROWS]
        free = [s for s in spots if s.tracker.has_tip]
        if (n == 8 and len(free) == 8) or (n == 1 and free):
          await self.move_to(free[0])
          for s in (free if n == 8 else free[:1]):
            s.tracker.remove_tip()
          return
    racks = self.racks_for(ev["instrument"])  # out of tips: the operator refills
    for rack in racks:
      for s in rack.get_all_items():
        if not s.tracker.has_tip:
          s.tracker.add_tip(s.make_tip())

  def fill(self):
    for slot, wells, vol in initial_fill(self.task):
      lw = self.by_slot.get(slot)
      if lw is None:
        continue
      for w in wells:
        v = self._vessel(lw, w)
        v.tracker.set_volume(min(v.max_volume, vol if vol is not None else v.max_volume * 0.8))

  def final_state(self):
    out = {}
    for slot, lw in self.by_slot.items():
      if "tiprack" in lw.name:
        continue
      for v in lw.get_all_children():
        if hasattr(v, "tracker") and hasattr(v.tracker, "get_used_volume"):
          vol = round(v.tracker.get_used_volume(), 2)
          if vol:
            out[f"{slot}:{v.name.split('_')[-1] if 'tube' not in v.name else v.name.split('_')[-2]}"] = vol
    return out

  async def run(self, label):
    self.fill()
    self.caption(f"{label}: start")
    await asyncio.sleep(1.5)
    last_comment = ""
    for i, ev in enumerate(self.events):
      k = ev["kind"]
      if k == "comment":
        last_comment = ev["text"][:110]
        self.caption(f"{label} | {last_comment}")
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
            have = v.tracker.get_used_volume()
            if have < vol:
              self.topped_up += 1
              v.tracker.set_volume(min(v.max_volume, vol))
            v.tracker.remove_liquid(min(vol, v.tracker.get_used_volume()))
          else:
            v.tracker.add_liquid(min(vol, v.tracker.get_free_volume()))
      elif k == "delay":
        self.caption(f"{label} | {last_comment}  [delay {ev['seconds']:.0f} s]")
        await asyncio.sleep(0.4)
      elif k in ("engage", "disengage", "temp"):
        what = {"engage": "magnet ENGAGED", "disengage": "magnet disengaged"}.get(k, f"temp {ev.get('celsius')} C")
        self.caption(f"{label} | {what}")
        await asyncio.sleep(0.4)
    self.caption(f"{label}: finished ({len(self.events)} robot events)")
    await asyncio.sleep(3.0)


async def main(events_path, task, label, per_event, out_path, state_path):
  log = json.load(open(events_path))
  rp = LogReplay(log, task)
  rp.delay = float(per_event)
  viewer = Viewer3D(rp.facility, open_browser=False, name=label)
  await viewer.start()
  from playwright.async_api import async_playwright
  tmp = out_path + ".rec"
  shutil.rmtree(tmp, ignore_errors=True)
  async with async_playwright() as p:
    browser = await p.chromium.launch(headless=True, args=["--use-angle=metal", "--enable-gpu", "--ignore-gpu-blocklist"])
    ctx = await browser.new_context(viewport={"width": 1280, "height": 720}, record_video_dir=tmp,
                                    record_video_size={"width": 1280, "height": 720})
    page = await ctx.new_page()
    await page.goto(viewer.url.replace("/#", "/?view=iso#"))
    await viewer.wait_for_browser(timeout=60)
    for _ in range(120):
      if await page.evaluate("() => (window.plrViewer?.resources() || []).length > 0"):
        break
      await asyncio.sleep(0.25)
    for btn in ("#toolbar-right-toggle", "#toolbar-left-toggle"):
      try:
        await page.click(btn, timeout=2000)
      except Exception:
        pass
    await page.add_style_tag(content="#stats-panel,#scale-bar,#zoom-controls,#home-button,#navbar-device-tools{display:none!important}")
    await asyncio.sleep(1.0)
    await page.evaluate("() => plrViewer.focus('ot2_deck', 'iso')")
    await asyncio.sleep(0.5)
    await page.keyboard.press("Escape")
    await page.evaluate("""() => { const d = document.createElement('div'); d.id = 'cap';
      d.style.cssText = 'position:fixed;left:12px;right:12px;bottom:12px;padding:10px 14px;' +
        'background:rgba(0,0,0,.75);color:#fff;font:600 22px system-ui;border-radius:8px;z-index:99999';
      document.body.appendChild(d); }""")
    loop = asyncio.get_running_loop()
    rp.caption = lambda text: loop.create_task(
      page.evaluate("t => { document.getElementById('cap').textContent = t; }", text))
    await asyncio.sleep(0.5)
    await rp.run(label)
    video = page.video
    await ctx.close()
    await browser.close()
    src = await video.path()
  os.system(f'ffmpeg -loglevel error -y -i "{src}" -c:v libx264 -pix_fmt yuv420p -crf 23 "{out_path}"')
  shutil.rmtree(tmp, ignore_errors=True)
  await viewer.stop()
  json.dump({"final": rp.final_state(), "topped_up": rp.topped_up}, open(state_path, "w"))
  print("wrote", out_path, "topped_up", rp.topped_up)


if __name__ == "__main__":
  asyncio.run(main(*sys.argv[1:7]))
