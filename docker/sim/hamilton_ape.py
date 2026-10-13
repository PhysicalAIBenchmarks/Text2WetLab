"""Run the har1eyk STARlet "Automated Protein Extraction" protocol on PyLabRobot's simulated backend and log it.

usage (in the container): python /t2w/hamilton_ape.py <protocol_dir> <out.json>
The deck is rebuilt from the authors' APE_96w notebook (rails 25 tips, 13 and 19 MFX carriers). Every
liquid-handler call is recorded with resource names so the host can replay it on a 3D STARlet; waits,
manual pauses and prints become comment events instead of real delays.
"""
import asyncio, builtins, json, sys, time

from pylabrobot.liquid_handling import LiquidHandler
from pylabrobot.liquid_handling.backends import LiquidHandlerChatterboxBackend
from pylabrobot.resources.hamilton import STARLetDeck, MFX_CAR_L5_base, TIP_CAR_480_A00
from pylabrobot.resources.hamilton.mfx_modules import Hamilton_MFX_plateholder_DWP_metal_tapped
from pylabrobot.resources.diy.grindbio.modules import Hamilton_MFX_plateholder_DWP_metal_tapped_10mm_3dprint
from pylabrobot.resources.alpaqua import Alpaqua_96_magnum_flx
from pylabrobot.resources.bioer.plates import BioER_96_wellplate_Vb_2200uL
from pylabrobot.resources.agenbio.plates import AGenBio_1_troughplate_100000uL_Fl
from pylabrobot.resources import hamilton_96_tiprack_1000uL, set_tip_tracking, set_volume_tracking

EVENTS = []


class SimulatedSTAR(LiquidHandlerChatterboxBackend):
  """The generic simulated backend, answering any STAR-only firmware command (CoRe gripper tools, sensors) as a no-op."""

  def __getattr__(self, name):
    if name.startswith("_"):
      raise AttributeError(name)

    async def no_op(*a, **k):
      return True
    return no_op


def names(xs):
  return [getattr(x, "name", str(x)) for x in xs]


def build(lh):
  tip_car = TIP_CAR_480_A00("tip_car")
  lh.deck.assign_child_resource(tip_car, rails=25)
  racks = [hamilton_96_tiprack_1000uL(f"tips_0{i}") for i in range(3)]
  for i, r in enumerate(racks):
    tip_car[i] = r
  m13 = {i: Hamilton_MFX_plateholder_DWP_metal_tapped_10mm_3dprint(n) for i, n in enumerate(
    ["rail13_mag_module", "rail13_waste_module", "rail13_elution_plate_module", "rail13_wash1_module", "rail13_wash2_module"])}
  lh.deck.assign_child_resource(MFX_CAR_L5_base("car_13", modules=m13), rails=13)
  r13 = [Alpaqua_96_magnum_flx("mag_plate"), AGenBio_1_troughplate_100000uL_Fl("waste_trough"),
         BioER_96_wellplate_Vb_2200uL("elution_plate"), AGenBio_1_troughplate_100000uL_Fl("wash1_trough"),
         AGenBio_1_troughplate_100000uL_Fl("wash2_trough")]
  for i, r in enumerate(r13):
    m13[i].assign_child_resource(r)
  m19 = {i: Hamilton_MFX_plateholder_DWP_metal_tapped(n) for i, n in enumerate(
    ["rail19_binding_module", "rail19_source_module", "rail19_flowthrough_module", "rail19_binding_trough_module", "rail19_elution_trough_module"])}
  lh.deck.assign_child_resource(MFX_CAR_L5_base("car_19", modules=m19), rails=19)
  r19 = [BioER_96_wellplate_Vb_2200uL("binding_plate"), BioER_96_wellplate_Vb_2200uL("source_plate"),
         BioER_96_wellplate_Vb_2200uL("flowthrough_plate"), AGenBio_1_troughplate_100000uL_Fl("binding_trough"),
         AGenBio_1_troughplate_100000uL_Fl("elution_trough")]
  for i, r in enumerate(r19):
    m19[i].assign_child_resource(r)
  res = {r.name: r for r in r13 + r19}
  return res, racks


def record(lh):
  def wrap(method, kind, fn):
    orig = getattr(lh, method)

    async def inner(*a, **k):
      EVENTS.append(fn(*a, **k) | {"kind": kind})
      try:
        return await orig(*a, **k)
      except ValueError as e:  # PLR 0.2.2 cannot spread 8 channels in one trough; newer PLR can. Logged, not simulated.
        if "space channels" not in str(e):
          raise
    setattr(lh, method, inner)

  arg = lambda a, k, i, *keys: a[i] if len(a) > i else next((k[x] for x in keys if x in k), None)
  wrap("pick_up_tips", "pick", lambda *a, **k: {"spots": names(arg(a, k, 0, "tip_spots") or [])})
  wrap("drop_tips", "drop", lambda *a, **k: {"spots": names(arg(a, k, 0, "tip_spots") or [])})
  wrap("return_tips", "drop", lambda *a, **k: {"spots": []})
  wrap("aspirate", "aspirate", lambda *a, **k: {"wells": names(arg(a, k, 0, "resources") or []), "vols": list(arg(a, k, 1, "vols") or [])})
  wrap("dispense", "dispense", lambda *a, **k: {"wells": names(arg(a, k, 0, "resources") or []), "vols": list(arg(a, k, 1, "vols") or [])})
  wrap("move_plate", "move", lambda *a, **k: {"plate": getattr(arg(a, k, 0, "plate"), "name", "?"), "to": getattr(arg(a, k, 1, "to"), "name", "?")})
  wrap("move_resource", "move", lambda *a, **k: {"plate": getattr(arg(a, k, 0, "resource"), "name", "?"), "to": getattr(arg(a, k, 1, "to"), "name", "?")})


async def main(proto_dir, out):
  sys.path.insert(0, proto_dir)
  set_tip_tracking(False)
  set_volume_tracking(False)
  _print = builtins.print
  builtins.input = lambda *a, **k: EVENTS.append({"kind": "comment", "text": "Operator pause: " + " ".join(map(str, a))[:140]}) or ""
  _sleep = asyncio.sleep

  async def no_wait(s, *a, **k):
    if s >= 1:
      EVENTS.append({"kind": "delay", "seconds": float(s)})
    await _sleep(0)
  asyncio.sleep = no_wait
  time.sleep = lambda s: EVENTS.append({"kind": "delay", "seconds": float(s)})

  backend = SimulatedSTAR(num_channels=8)
  lh = LiquidHandler(backend=backend, deck=STARLetDeck(core_grippers="1000uL-at-waste"))
  await lh.setup()
  res, racks = build(lh)
  record(lh)
  import ape_96w_protocol as ape
  ape.print = lambda *a, **k: EVENTS.append({"kind": "comment", "text": " ".join(map(str, a))[:160]})  # protocol's own messages only
  ok, err = True, None
  try:
    await ape.run_ape_96w(lh, binding_plate=res["binding_plate"], source_plate=res["source_plate"],
      flowthrough_plate=res["flowthrough_plate"], elution_plate=res["elution_plate"], mag_plate=res["mag_plate"],
      binding_trough=res["binding_trough"], wash1_trough=res["wash1_trough"], wash2_trough=res["wash2_trough"],
      waste_trough=res["waste_trough"], elution_trough=res["elution_trough"], tip_racks=racks,
      lysate_volume=300, binding_buffer_volume=1500, bead_volume_note=50, wash_volume=900, elution_volume=120,
      binding_mix_rounds=6, binding_incubation_seconds=30, wash_mix_rounds=1, wash1_cycles=1, magnet_settle_seconds=20,
      wash_incubation_seconds=2, elution_incubation_seconds=120)
  except Exception as e:
    ok, err = False, f"{type(e).__name__}: {e}"[:400]
  json.dump({"ok": ok, "error": err, "events": EVENTS}, open(out, "w"))
  print("ok" if ok else "FAIL " + err, len(EVENTS), "events")


if __name__ == "__main__":
  asyncio.run(main(sys.argv[1], sys.argv[2]))
