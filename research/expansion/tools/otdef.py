"""Build a PyLabRobot resource from any Opentrons labware definition (official library or a repo's custom JSON)."""
import glob, json, os
from pylabrobot.resources import Coordinate, Plate, Well
from pylabrobot.resources.opentrons import load_ot_tip_rack

OT_DEFS = os.path.join(os.path.dirname(__file__), "otvenv/lib/python3.10/site-packages/opentrons_shared_data/data/labware/definitions/2")
_custom = {}


def register_custom(root):
  """Index custom labware JSON files under a repo (loadName -> definition)."""
  for f in glob.glob(os.path.join(root, "**", "*.json"), recursive=True):
    try:
      d = json.load(open(f, errors="replace"))
    except Exception:
      continue
    if isinstance(d, dict) and "wells" in d and "parameters" in d:
      _custom[d["parameters"].get("loadName")] = d


def definition(load_name):
  if load_name in _custom:
    return _custom[load_name]
  versions = sorted(glob.glob(os.path.join(OT_DEFS, load_name, "*.json")))
  return json.load(open(versions[-1])) if versions else None


def from_definition(d, name):
  dims = d["dimensions"]
  items = {}
  for well_name, w in d["wells"].items():
    if w.get("shape") == "circular":
      sx = sy = w["diameter"]
    else:
      sx, sy = w.get("xDimension", 8), w.get("yDimension", 8)
    well = Well(name=f"{name}_{well_name}", size_x=sx, size_y=sy, size_z=w["depth"],
                max_volume=w.get("totalLiquidVolume") or 1000.0,
                cross_section_type="circle" if w.get("shape") == "circular" else "rectangle")
    well.location = Coordinate(w["x"] - sx / 2, w["y"] - sy / 2, w["z"])
    items[well_name] = well
  return Plate(name=name, size_x=dims["xDimension"], size_y=dims["yDimension"], size_z=dims["zDimension"],
               ordered_items=items, model=d["parameters"].get("loadName"))


def load(load_name, name):
  """A PLR resource for an Opentrons load name: tip racks via PLR's loader, everything else as a plate of wells."""
  d = definition(load_name)
  if d and d["parameters"].get("isTiprack"):
    try:
      return load_ot_tip_rack(load_name, name)
    except Exception:
      pass
  if d is None:
    return None
  return from_definition(d, name)
