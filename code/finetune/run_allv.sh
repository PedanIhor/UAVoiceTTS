#!/bin/bash
# Check all NPC voices on h3 step1000 (new texts). ~40–60 min.
cd "$(dirname "$0")/.."; set -eo pipefail
[[ -z $CAFFEINATED ]] && exec env CAFFEINATED=1 caffeinate -dimsu bash "$0" "$@"
source ~/miniconda/etc/profile.d/conda.sh; export PYTHONUNBUFFERED=1
[[ -f out_allv/texts.json ]] || { conda activate omnitrain; python finetune/allv_texts.py; conda deactivate; }
conda activate mlxtts; python finetune/allv_gen.py; python finetune/allv_page.py; open out_allv/listen.html
