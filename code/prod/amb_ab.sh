#!/bin/bash
# Accent at line starts: Russian vs Ukrainian references. ~15 min. Result: prod/out_ab3/listen.html
cd "$(dirname "$0")"
[[ -z $CAFFEINATED ]] && exec env CAFFEINATED=1 caffeinate -dimsu bash "$0" "$@"
source ~/miniconda/etc/profile.d/conda.sh; export PYTHONUNBUFFERED=1
conda activate mlxtts
python amb_ab.py && open out_ab3/listen.html
