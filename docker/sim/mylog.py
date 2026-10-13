"""eval/runlog.py, but keeping protocol comments as caption events."""
import json, sys
sys.path.insert(0, sys.argv[4])
import runlog
_parse = runlog.parse
def parse(text, payload):
    if text.startswith("COMMENT: "):
        return {"kind": "comment", "text": text[9:], "instrument": "", "channels": 1}
    return _parse(text, payload)
runlog.parse = parse
out = runlog.main(sys.argv[1], sys.argv[2])
open(sys.argv[3], "w").write(json.dumps(out))
print(sys.argv[1].split("results/")[-1], "ok" if out["ok"] else out["error"][:200], len(out.get("events", [])))
