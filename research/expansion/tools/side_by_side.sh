#!/bin/bash
# Side-by-side PyLabRobot | MuJoCo for every task, both driven by the same oracle run log.
S=/private/tmp/claude-501/-Users-nialloleary/36017c47-22e1-459a-91a2-0b4a5634f844/scratchpad
L=$S/plr/logs; O=~/Desktop/Text2WetLab_SideBySide; mkdir -p $O $S/sbs
cd $S/plr
for t in colony-pcr-screening-hard ecoli-heat-shock-transformation-hard golden-gate-assembly-hard opentrons-rna-extraction-hard; do
  [ -s cmp/$t.oracle.mp4 ] && continue
  per=$(python3 -c "
import json; e=json.load(open('logs/$t.oracle.json'))['events']
n=sum(1 for x in e if x['kind'] in ('pick','drop','aspirate','dispense')); print(min(0.35, max(0.004, 55.0/max(n,1))))")
  venv/bin/python replay_log.py logs/$t.oracle.json $t "Oracle (reference)" $per cmp/$t.oracle.mp4 cmp/$t.oracle.state.json < /dev/null 2>&1 | grep -v "^viewer" | tail -1
done
for f in $L/*.oracle.json; do
  t=$(basename $f .oracle.json); p=$S/plr/cmp/$t.oracle.mp4
  [ -s "$p" ] || { echo "no PLR video for $t"; continue; }
  dur=$(ffprobe -v error -show_entries format=duration -of csv=p=0 $p)
  (cd $S/mj && venv/bin/python mj_render.py $f $S/sbs/$t.mj.mp4 $dur "MuJoCo" < /dev/null > /dev/null 2>&1)
  ffmpeg -nostdin -loglevel error -y -i $p -i $S/sbs/$t.mj.mp4 \
    -filter_complex "[0:v]scale=960:540,tpad=stop_mode=clone:stop_duration=600[a];[1:v]scale=960:540,tpad=stop_mode=clone:stop_duration=600[b];[a][b]hstack=inputs=2[v]" \
    -map "[v]" -t $dur -c:v libx264 -pix_fmt yuv420p -crf 23 $O/$t.mp4 && echo "side-by-side $t ($dur s)"
done
ls $O | wc -l
