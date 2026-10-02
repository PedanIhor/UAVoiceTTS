#!/bin/bash
# Batch: all quests in zones up to level 30 for both factions + cities (quests ≤30) + dungeons ≤30 (list — zones.json, rebuild with zones_make.py) → h3 voiceover → UAVoiceTTS addon in the game's AddOns folder.
# Can be interrupted and restarted — finished work is not recomputed. Log: prod/trial.log. ~1 min per line (3635 lines ≈ 2 days).
cd "$(dirname "$0")"
[[ -z $CAFFEINATED ]] && exec env CAFFEINATED=1 caffeinate -dimsu bash "$0" "$@"
exec > >(tee -a trial.log) 2>&1
source ~/miniconda/etc/profile.d/conda.sh; export PYTHONUNBUFFERED=1
step() { echo; echo "===== $(date '+%H:%M') $*"; }
fail() { echo "!!!!! $(date '+%H:%M') ERROR: $* — stopped"; exit 1; }
conda activate mlxtts                 # everything in one env (omnitrain is only needed for STRESS=all — automatic stress marking)
[[ ${STRESS:-dict} == all* ]] && conda activate omnitrain
step "0/5 in-game and Discord reports → stress dictionary and re-voicing queue"; python reports.py --apply || fail "reports"
step "1/5 jobs (ClassicUA + NPC voices)"; python build_jobs.py ${RACES:-zone:all} || fail "jobs"
step "2/5 numbers and stress dictionary";  python -c "import num2words" 2>/dev/null || pip install -q num2words; python stress_jobs.py || fail "stress"
conda activate mlxtts
step "3/5 voiceover";           python synth.py || fail "voiceover"
step "4/5 build addon";     python build_addon.py || fail "addon"
step "5/5 package";            (cd ../addon && rm -f ../../UAVoiceTTS.zip && zip -qr -X ../../UAVoiceTTS.zip UAVoiceTTS -x "*.DS_Store") || fail "zip"
step "DONE: UkrAddon/UAVoiceTTS.zip is ready (restart the game fully to hear new sounds). Publish: gh release upload <tag> UAVoiceTTS.zip --clobber"
