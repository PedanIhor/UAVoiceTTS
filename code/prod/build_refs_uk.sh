#!/bin/bash
# Ukrainian NPC reference candidates (no quest lines generated). Result: code/refs_uk/cand/listen.html
cd "$(dirname "$0")"
source ~/miniconda/etc/profile.d/conda.sh; export PYTHONUNBUFFERED=1
conda activate mlxtts
python build_refs_uk.py "$@" && [[ $1 != pick && $1 != fx ]] && open ../refs_uk/cand/${PAGE:-listen.html}
