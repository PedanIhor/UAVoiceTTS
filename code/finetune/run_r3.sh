#!/bin/bash
# Third OmniVoice fine-tuning round: against pauses.
#  - recordings cleaned: edge silence trimmed (35 dB threshold, 0.3 s of silence kept on each edge), pauses inside phrases NOT compressed
#  - full-length phrases (up to ~9 s), not just short ones: on short ones the model learned to "chop" long text into 2–3 word chunks
#  - real LoRA (OmniVoice from GitHub; the pip version doesn't support LoRA and trained the whole model)
# Steps: STEP=setup|data|tokens|train|eval. Everything goes to ~/omni_ft/r3 (pilot untouched).
cd "$(dirname "$0")"
set -eo pipefail
source ~/miniconda/etc/profile.d/conda.sh
conda activate omnitrain
export PYTHONUNBUFFERED=1 PYTORCH_ENABLE_MPS_FALLBACK=1 TOKENIZERS_PARALLELISM=false
export FT=~/omni_ft/r3 CLEAN=1 MAXGAP=${MAXGAP:-0} TOP_DB=${TOP_DB:-35} EDGE=${EDGE:-0.3} HOURS=${HOURS:-5} STRESSED_RATIO=${STRESSED_RATIO:-0.7}
mkdir -p $FT; LOG=$FT/log.txt
S=${STEP:-all}
if [[ $S == all || $S == setup ]]; then
  echo "=== 0/4 OmniVoice from GitHub (with LoRA)" | tee -a $LOG
  pip uninstall -y omnivoice 2>&1 | tail -1 | tee -a $LOG
  pip install --no-cache-dir --force-reinstall --no-deps "git+https://github.com/k2-fsa/OmniVoice" 2>&1 | tail -3 | tee -a $LOG
  python -c "import omnivoice, os; print(\"omnivoice from:\", os.path.dirname(omnivoice.__file__))" | tee -a $LOG
  pip install -q peft 2>&1 | tail -1
  python -c "import omnivoice.utils.lora; print('LoRA module in place')" | tee -a $LOG; fi
if [[ $S == all || $S == data ]]; then
  echo "=== 1/4 data (with pause cleanup)" | tee -a $LOG; python prep_data.py 2>&1 | tee -a $LOG; fi
if [[ $S == all || $S == tokens ]]; then
  echo "=== 2/4 audio tokens (on CPU, slow)" | tee -a $LOG
  for part in train dev; do
    python -m omnivoice.scripts.extract_audio_tokens --input_jsonl $FT/data/$part.jsonl \
      --tar_output_pattern $FT/tokens/$part/audios/shard-%06d.tar --jsonl_output_pattern $FT/tokens/$part/txts/shard-%06d.jsonl \
      --tokenizer_path eustlb/higgs-audio-v2-tokenizer --nj_per_gpu 4 --skip_errors 2>&1 | tee -a $LOG
  done; fi
if [[ $S == all || $S == train ]]; then
  echo "=== 3/4 training (LoRA, 1000 steps, checkpoint every 250)" | tee -a $LOG
  printf '{"train":[{"manifest_path":["%s"]}],"dev":[{"manifest_path":["%s"]}]}\n' $FT/tokens/train/data.lst $FT/tokens/dev/data.lst > $FT/data_config.json
  python train_mac.py --train_config train_config_r3.json --data_config $FT/data_config.json --output_dir $FT/exp/r3 2>&1 | tee -a $LOG; fi
if [[ $S == all || $S == eval ]]; then
  echo "=== 4/4 evaluation" | tee -a $LOG
  for c in $(ls -d $FT/exp/r3/checkpoint* 2>/dev/null | sort -V | tail -2); do python eval_ft.py $c 2>&1 | tee -a $LOG; done
  open ../out_ft/listen.html; fi
