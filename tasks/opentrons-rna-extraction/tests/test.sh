#!/bin/bash
set -uo pipefail
ls -A /logs/verifier > /tmp/t2wl_preexisting 2>/dev/null || true
rm -f /logs/verifier/reward.json /logs/verifier/reward.txt
python /tests/grade.py
exit_code=$?
test -f /logs/verifier/reward.json || printf '0\n' > /logs/verifier/reward.txt
exit "$exit_code"
