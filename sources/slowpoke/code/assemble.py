"""
Build the two Slowpoke OT-2 protocols the way the authors' generators do, without their tkinter GUI.

    python references/slowpoke/assemble.py OUTDIR      # writes colony_pcr.py and cloning.py

Each upstream "workflow" script is a template that uses two global variables it never defines. The authors'
generators (generator_*_protocol.py) ask for CSV files in pop-up windows, parse them with plain functions,
then write `<name> = <json>` for each variable above the template. This script runs those same parsing
functions (extracted with ast, because importing the generators would open dialogs) on the CSVs the repo
ships, and writes the same file. Nothing here is authored by us except this wrapper.
"""
import ast
import csv
import json
import os
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
JOBS = {
    "colony_pcr.py": ("Colony_PCR", "generator_for_colony_PCR_protocol.py", "colony_PCR_workflow_OT2.py",
                      [("pcr_deck_colony_template_maps_dict", "pcr_deck_colony_template_maps", ["pcr_deck_map.csv", "colony_template_map.csv"]),
                       ("pcr_recipe_to_make", "generate_pcr_recipe", ["pcr_recipe_to_make.csv"])]),
    "cloning.py": ("Cloning", "generator_OT2_for_cloning_protocol.py", "cloning_workflow_OT2.py",
                   [("dna_plate_map_dict", "generate_plate_maps", ["fixed_toolkit_map.csv", "custom_parts_map.csv"]),
                    ("combinations_to_make", "generate_combinations", ["combination-to-make.csv"])]),
}


def parsers(path, names):
    text = path.read_text(encoding="utf-8", errors="replace")
    src = "\n".join(ast.get_source_segment(text, n) for n in ast.parse(text).body
                    if isinstance(n, ast.FunctionDef) and n.name in names)
    ns = {"csv": csv, "json": json, "os": os}
    exec(src.replace("\t", "    "), ns)
    return ns


def build(name):
    sub, generator, template, variables = JOBS[name]
    d = HERE / sub
    ns = parsers(d / generator, {fn for _, fn, _ in variables})
    head = "".join(f"{var} = {json.dumps(ns[fn](*[str(d / a) for a in args]))}\n\n" for var, fn, args in variables)
    return head + (d / template).read_text(encoding="utf-8", errors="replace")


def main(outdir):
    out = pathlib.Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    for name in JOBS:
        (out / name).write_text(build(name))
        print("wrote", out / name)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "assembled")
