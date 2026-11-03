"""Where the local tools find the SDK: the liquid-handling SDK checkout (with its .venv) and the unitelabs-sdk and
unitelabs-labware checkouts that venv installs editable, all next to the Text2WetLab checkout. `UL_PYTHON` overrides
the interpreter.

Used by the local runners (validate_ref.py, adversarial.py, session_run.py, run_loop.py); the graders inside a task use
/opt/ul and never import this.
"""
import os
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent   # backends/unitelabs
CHECKOUTS = ROOT.parents[2]                             # the directory the Text2WetLab checkout sits in
LHSDK = CHECKOUTS / "python-lib"          # unitelabs-liquid-handling
ULSDK = CHECKOUTS / "python-sdk"          # unitelabs-sdk (Audit, lineage contract)
DOCS = CHECKOUTS / "docs"
UL_PYTHON = os.environ.get("UL_PYTHON", str(LHSDK / ".venv/bin/python"))
LHSDK_SRC = LHSDK / "src/unitelabs"              # the liquid handling package
ULSDK_SRC = ULSDK / "src/unitelabs"              # the sdk package
LABWARE = CHECKOUTS / "labware"           # unitelabs-labware (the model notifications lineage seeds come from)
# The labware package: its checkout, which the liquid-handling SDK venv installs editable while the lineage work is unreleased, else
# the copy in that venv.
LABWARE_SRC = LABWARE / "src/unitelabs" if (LABWARE / "src/unitelabs/labware").is_dir() else \
    next(LHSDK.glob(".venv/lib/python3.*/site-packages/unitelabs"), LHSDK / ".venv/lib/site-packages/unitelabs")
