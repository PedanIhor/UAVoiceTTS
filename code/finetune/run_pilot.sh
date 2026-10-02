#!/bin/bash
# OmniVoice fine-tuning pilot: data → tokens → training → evaluation.
# Steps can be run separately: STEP=data|tokens|train|eval bash finetune/run_pilot.sh
# Pilot size: HOURS=5 (hours of speech), STRESSED_RATIO=0.7 (share of phrases with stress marks)
cd "$(dirname "$0")"
set -eo pipefail
source ~/miniconda/etc/profile.d/conda.sh
conda activate omnitrain
export PYTHONUNBUFFERED=1 PYTORCH_ENABLE_MPS_FALLBACK=1 TOKENIZERS_PARALLELISM=false
FT=~/omni_ft; mkdir -p $FT; LOG=$FT/pilot_log.txt
S=${STEP:-all}
if [[ $S == all || $S == data ]]; then
  echo "=== 1/4 data" | tee -a $LOG; python prep_data.py 2>&1 | tee -a $LOG; fi
if [[ $S == all || $S == tokens ]]; then
  echo "=== 2/4 audio tokens (on CPU, this is slow)" | tee -a $LOG
  for part in train dev; do
    python -m omnivoice.scripts.extract_audio_tokens --input_jsonl $FT/data/$part.jsonl \
      --tar_output_pattern $FT/tokens/$part/audios/shard-%06d.tar --jsonl_output_pattern $FT/tokens/$part/txts/shard-%06d.jsonl \
      --tokenizer_path eustlb/higgs-audio-v2-tokenizer --nj_per_gpu 4 --skip_errors 2>&1 | tee -a $LOG
  done; fi
if [[ $S == all || $S == train ]]; then
  echo "=== 3/4 training (LoRA, 800 steps, checkpoint every 200)" | tee -a $LOG
  printf '{"train":[{"manifest_path":["%s"]}],"dev":[{"manifest_path":["%s"]}]}\n' $FT/tokens/train/data.lst $FT/tokens/dev/data.lst > $FT/data_config.json
  python train_mac.py --train_config train_config_mac.json --data_config $FT/data_config.json --output_dir $FT/exp/pilot 2>&1 | tee -a $LOG; fi
if [[ $S == all || $S == eval ]]; then
  echo "=== 4/4 evaluation" | tee -a $LOG
  python eval_ft.py 2>&1 | tee -a $LOG                                       # base for comparison
  for c in $(ls -d $FT/exp/pilot/checkpoint* 2>/dev/null | sort -V | tail -3); do python eval_ft.py $c 2>&1 | tee -a $LOG; done
  open ../out_ft/listen.html; fi
