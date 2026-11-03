#!/bin/bash
set -euo pipefail
mkdir -p /app
cp "$(dirname "$0")/protocol.py" /app/protocol.py
