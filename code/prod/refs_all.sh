#!/bin/bash
# Ukrainian references for every voice that has none yet: candidates (lively + clear per source speaker) → auto-pick
# the cleanest «lively» → code/refs_uk/summary.html. Override any voice: python build_refs_uk.py pick <voice>=<candidate>
cd "$(dirname "$0")"
source ~/miniconda/etc/profile.d/conda.sh; export PYTHONUNBUFFERED=1
conda activate mlxtts
TODO=$(python build_refs_uk.py todo)
echo "voices without a Ukrainian reference: $TODO"
[[ -n $TODO ]] && VOICES=$TODO VARIANTS=lively,clear MAX_CLIP=4.5 PAGE=all.html python build_refs_uk.py && VOICES=$TODO PAGE=all.html python build_refs_uk.py fx && VOICES=$TODO python build_refs_uk.py auto
python build_refs_uk.py summary && open ../refs_uk/summary.html
