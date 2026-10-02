#!/bin/bash
# Full conversion opentts → NPC voices. Can be interrupted (Ctrl+C) and rerun — it resumes.
cd "$(dirname "$0")"; set -eo pipefail
source ~/miniconda/etc/profile.d/conda.sh
export PYTHONUNBUFFERED=1 PYTORCH_ENABLE_MPS_FALLBACK=1
conda activate vccb
[[ -f ~/omni_ft/vc/plan.jsonl ]] || python vc_full.py plan
python vc_full.py chatterbox; conda deactivate
conda activate vcseed; python vc_full.py seed_f0
echo "=== conversion finished"
