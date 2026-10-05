#!/bin/bash
# Old vs new voice on the same quest line for all voices (~30–40 min). Result: prod/out_cmp/listen.html
cd "$(dirname "$0")"
[[ -z $CAFFEINATED ]] && exec env CAFFEINATED=1 caffeinate -dimsu bash "$0" "$@"
source ~/miniconda/etc/profile.d/conda.sh; export PYTHONUNBUFFERED=1
conda activate mlxtts
python compare_voices.py prepare || exit 1
JOBS=out_cmp/jobs.jsonl OUT_DIR=out_cmp/new python synth.py || exit 1                       # new: refs_uk (undead: fx reference)
JOBS=out_cmp/jobs.jsonl OUT_DIR=out_cmp/old REFS_DIR=refs_tight python synth.py || exit 1   # old: only lines not voiced before
python compare_voices.py && open out_cmp/listen.html
