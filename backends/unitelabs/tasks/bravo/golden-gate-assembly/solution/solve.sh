#!/bin/bash
set -euo pipefail
mkdir -p /app
cp "$(dirname "$0")/INFEASIBLE.md" /app/INFEASIBLE.md
