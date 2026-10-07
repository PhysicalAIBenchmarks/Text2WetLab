#!/bin/bash
# Create .venv-ot: the Opentrons 7.5 simulator the graders and tests run protocols in (same pins as the task images).
#     scripts/setup_ot_venv.sh [python3.10]        # or set OT_VENV to use an existing venv instead
set -euo pipefail
cd "$(dirname "$0")/.."
PY="${1:-python3.10}"
"$PY" -m venv .venv-ot
.venv-ot/bin/pip install --quiet opentrons==7.5.0 opentrons-shared-data==7.5.0 "pydantic<2"
echo "ready: $(.venv-ot/bin/python -c 'import opentrons; print("opentrons", opentrons.__version__)')"
