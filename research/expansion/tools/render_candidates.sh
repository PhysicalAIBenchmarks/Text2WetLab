#!/bin/bash
# Render the passing third-party Opentrons protocols (logs from the t2w-sim container) as 3D replay videos.
S=/private/tmp/claude-501/-Users-nialloleary/36017c47-22e1-459a-91a2-0b4a5634f844/scratchpad/plr
B=~/Desktop/Text2WetLab_PLR_3D/candidates; L=$B/logs; V=$B/videos; mkdir -p $V $B/clips
CODE=~/.cache/text2wetlab-ingest/code/experimental
cd $S
python3 - "$L" > $B/render_plan.tsv <<'PY'
import json, os, sys
L = sys.argv[1]
for cand in sorted(os.listdir(L)):
    runs = []
    for f in os.listdir(os.path.join(L, cand)):
        p = os.path.join(L, cand, f)
        try:
            d = json.load(open(p))
        except Exception:
            continue
        if not d.get("ok"):
            continue
        n = sum(1 for e in d["events"] if e["kind"] in ("aspirate", "dispense"))
        if n >= 6:
            runs.append((n, f, p))
    for n, f, p in sorted(runs, reverse=True)[:3]:
        moves = sum(1 for e in json.load(open(p))["events"] if e["kind"] in ("pick", "drop", "aspirate", "dispense"))
        print(f"{cand}\t{f}\t{p}\t{min(0.35, max(0.004, 40.0 / max(moves, 1)))}")
PY
while IFS=$'\t' read -r cand f p per; do
  name="${f%.json}"; out="$V/${cand}__${name}.mp4"
  [ -s "$out" ] && continue
  venv/bin/python replay_candidate.py "$p" "$CODE/$cand" "$cand | ${name}" "$per" "$out" < /dev/null 2>&1 | grep -v "^viewer" | tail -1
done < $B/render_plan.tsv
# highlights: 15 s from the middle of each candidate's first video
ls $V/*.mp4 | awk -F'__' '!seen[$1]++' > $B/clips/list.txt
: > $B/clips/concat.txt
while read -r v; do
  d=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$v"); st=$(python3 -c "print(max(0, $d/2 - 7.5))")
  c="$B/clips/$(basename "$v")"; ffmpeg -nostdin -loglevel error -y -ss "$st" -t 15 -i "$v" -c:v libx264 -pix_fmt yuv420p -r 25 "$c" && echo "file '$c'" >> $B/clips/concat.txt
done < $B/clips/list.txt
ffmpeg -loglevel error -y -f concat -safe 0 -i $B/clips/concat.txt -c copy $B/HIGHLIGHTS_all_candidates.mp4 && echo "highlights $(ffprobe -v error -show_entries format=duration -of csv=p=0 $B/HIGHLIGHTS_all_candidates.mp4)s"
