#!/bin/bash
# Blind A/B of NPC references: Russian (refs_tight) vs Ukrainian from VC clips (refs_uk). ~30–40 min. Result: prod/out_ab2/listen.html
cd "$(dirname "$0")"
[[ -z $CAFFEINATED ]] && exec env CAFFEINATED=1 caffeinate -dimsu bash "$0" "$@"
source ~/miniconda/etc/profile.d/conda.sh; export PYTHONUNBUFFERED=1
conda activate mlxtts
python ref_ab.py && open out_ab2/listen.html
