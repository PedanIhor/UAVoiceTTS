#!/bin/bash
# h3: everything via Chatterbox (no seed_f0 accent) + stress marks in 70% of anchors (so marks don't mean "slow, with pauses").
# Each step can be rerun — finished work isn't recomputed. Log: ~/omni_ft/h3.log.  Run: bash finetune/run_h3.sh
cd "$(dirname "$0")/.."
[[ -z $CAFFEINATED ]] && exec env CAFFEINATED=1 caffeinate -dimsu bash "$0" "$@"
LOG=~/omni_ft/h3.log; exec > >(tee -a $LOG) 2>&1
source ~/miniconda/etc/profile.d/conda.sh
export PYTHONUNBUFFERED=1 PYTORCH_ENABLE_MPS_FALLBACK=1 H2DIR=~/omni_ft/h3
step() { echo; echo "===== $(date '+%H:%M') $*"; }
fail() { echo "!!!!! $(date '+%H:%M') ERROR: $* — pipeline stopped"; exit 1; }
step "1/6 stress marks for anchors";   conda activate omnitrain; python finetune/anchors_stress.py || fail "stress"; conda deactivate
step "2/6 VC: Chatterbox for all voices"; conda activate vccb
python vc/h3_plan.py || fail "plan"; VC=~/omni_ft/vc3 python vc/vc_full.py chatterbox || fail "VC"; conda deactivate
conda activate mlxtts
step "3/6 quality check";  VCPLAN=~/omni_ft/vc3/plan.jsonl OLDQA=~/omni_ft/h2/qa.jsonl python finetune/qa_new.py || fail "QA"
step "4/6 build h3 dataset";   python finetune/h2_prep.py || fail "build"
step "5/6 train h3";        RUN=h3 python finetune/h2_train.py || fail "training"
step "6/6 voice test phrases"
for a in step500 step750 step1000; do python finetune/higgs_eval.py ~/omni_ft/higgs/exp/h3/$a.safetensors || echo "(eval $a failed)"; done
step "DONE. Listen: tts_local/out_ft/listen.html (columns higgs-h3_…)"
