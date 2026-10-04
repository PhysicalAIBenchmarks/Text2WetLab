#!/bin/bash
set -uo pipefail
rm -f /logs/verifier/reward.json /logs/verifier/reward.txt
/opt/grader/bin/python /tests/grade.py
exit_code=$?
test -f /logs/verifier/reward.json || printf '0\n' > /logs/verifier/reward.txt
exit "$exit_code"
