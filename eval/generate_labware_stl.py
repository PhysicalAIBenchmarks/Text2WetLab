"""
Generate approximate STL/OBJ meshes from Opentrons shared-data labware JSON definitions.

Usage:
  python eval/generate_labware_stl.py assets/labware_defs/corning_96_wellplate_360ul_flat/1.json
  python eval/generate_labware_stl.py assets/labware_defs/  # all labware in directory

Output: assets/stl/<labware_name>.obj

Requires: trimesh (pip install trimesh)
"""

import json
import sys
import pathlib
import trimesh
import numpy as np


def box_mesh(x, y, z, w, d, h):
    """Axis-aligned box with corner at (x,y,z), dimensions w×d×h."""
    m = trimesh.creation.box(extents=[w, d, h])
    m.apply_translation([x + w/2, y + d/2, z + h/2])
    return m


def cylinder_mesh(cx, cy, z_bottom, diameter, depth, segments=16):
    """Downward-pointing cylinder (well bore) centred at (cx, cy)."""
    r = diameter / 2
    m = trimesh.creation.cylinder(radius=r, height=depth, sections=segments)
    m.apply_translation([cx, cy, z_bottom + depth/2])
    return m


def labware_from_def(def_path: str) -> trimesh.Trimesh:
    with open(def_path) as f:
        defn = json.load(f)

    dims = defn["dimensions"]
    W = dims["xDimension"]
    D = dims["yDimension"]
    H = dims["zDimension"]

    # Outer body
    body = box_mesh(0, 0, 0, W, D, H)

    # Subtract well bores
    wells = defn.get("wells", {})
    bore_meshes = []
    for well_id, well in wells.items():
        shape = well.get("shape", "circular")
        depth = well.get("depth", 5.0)
        z_top = well.get("z", H)
        z_bottom = z_top - depth
        cx = well.get("x", W/2)
        cy = well.get("y", D/2)

        if shape == "circular":
            diameter = well.get("diameter", 6.0)
            bore = cylinder_mesh(cx, cy, z_bottom, diameter, depth)
        else:
            # rectangular well — use box
            xdim = well.get("xDimension", 8.0)
            ydim = well.get("yDimension", 8.0)
            bore = box_mesh(cx - xdim/2, cy - ydim/2, z_bottom, xdim, ydim, depth)

        bore_meshes.append(bore)

    if bore_meshes:
        bores = trimesh.util.concatenate(bore_meshes)
        result = body.difference(bores, engine="blender") if trimesh.boolean.exists() else body
    else:
        result = body

    return result


def main():
    if len(sys.argv) < 2:
        print("Usage: generate_labware_stl.py <def.json|defs_dir/>")
        sys.exit(1)

    target = pathlib.Path(sys.argv[1])
    out_dir = pathlib.Path("assets/stl")
    out_dir.mkdir(parents=True, exist_ok=True)

    paths = list(target.rglob("*.json")) if target.is_dir() else [target]

    for p in paths:
        try:
            with open(p) as f:
                defn = json.load(f)
            name = defn.get("parameters", {}).get("loadName", p.stem)
            print(f"  {name} ...", end=" ", flush=True)

            mesh = labware_from_def(p)
            out = out_dir / f"{name}.obj"
            mesh.export(str(out))
            print(f"→ {out}")
        except Exception as e:
            print(f"SKIP ({e})")


if __name__ == "__main__":
    main()
