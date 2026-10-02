#!/bin/bash
# Overnight h2 pipeline: VC → anchors → quality check → dataset build → training → voicing test phrases.
# Each step can be rerun: finished work isn't recomputed. Log: ~/omni_ft/overnight.log
# The Mac won't sleep while the script runs (caffeinate). Run:  bash finetune/run_overnight.sh
cd "$(dirname "$0")/.."
[[ -z $CAFFEINATED ]] && exec env CAFFEINATED=1 caffeinate -dimsu bash "$0" "$@"
LOG=~/omni_ft/overnight.log; mkdir -p ~/omni_ft
exec > >(tee -a $LOG) 2>&1
source ~/miniconda/etc/profile.d/conda.sh
export PYTHONUNBUFFERED=1 PYTORCH_ENABLE_MPS_FALLBACK=1
step() { echo; echo "===== $(date '+%H:%M') $*"; }
fail() { echo "!!!!! $(date '+%H:%M') ERROR: $* — pipeline stopped"; exit 1; }

step "1/6 VC: opentts → NPC voices";            bash vc/run_vc_full.sh || fail "VC"
conda activate mlxtts
step "2/6 anchors: base Higgs in NPC voices";    python finetune/anchors_gen.py 12 || fail "anchors"
step "3/6 quality check (Whisper)";          python finetune/qa_new.py || fail "QA"
step "4/6 build h2 dataset (Higgs codes)";        python finetune/h2_prep.py || fail "build"
step "5/6 train h2";                          RUN=h2 python finetune/h2_train.py || fail "training"
step "6/6 voice test phrases";
for a in step500 step1000; do python finetune/higgs_eval.py ~/omni_ft/higgs/exp/h2/$a.safetensors || echo "(eval $a failed)"; done
step "DONE. Listen: tts_local/out_ft/listen.html (columns higgs-h2_…)"
