#!/bin/bash
# Fine-tune Higgs Audio v3 (MLX, LoRA) on r3 data. Steps: STEP=check|prep|train|eval
#   check — verify mlx-audio;  prep — encode audio with the Higgs codec;  train — training (RUN, STEPS, LR, RANK…);
#   eval  — voice test phrases: base + last two saves of run RUN (or ADAPTER=path).
cd "$(dirname "$0")"
set -eo pipefail
source ~/miniconda/etc/profile.d/conda.sh
conda activate mlxtts
export PYTHONUNBUFFERED=1 HFT=~/omni_ft/higgs SRC=~/omni_ft/r3 RUN=${RUN:-h1}
mkdir -p $HFT; LOG=$HFT/log.txt
case ${STEP:-check} in
  check) python -c "
import mlx.core as mx, mlx_audio, importlib.metadata as m
from mlx_audio.tts.models.higgs_audio_v3 import model as M
from mlx_audio.tts.models.higgs_audio_v3.prompt import ReferenceCodes
assert all(hasattr(M.Model, a) for a in ('_build_prompt_embeddings','_embed_audio_codes','_audio_logits')), 'old mlx-audio version'
print('mlx', mx.__version__, '| mlx-audio', m.version('mlx-audio'), '| Higgs v3: everything needed is in place')" ;;
  prep)  python higgs_prep.py 2>&1 | tee -a $LOG ;;
  train) python higgs_train.py 2>&1 | tee -a $LOG ;;
  eval)  if [[ -n $ADAPTER ]]; then python higgs_eval.py $ADAPTER 2>&1 | tee -a $LOG
         else
           python higgs_eval.py 2>&1 | tee -a $LOG
           for a in $(ls $HFT/exp/$RUN/step*.safetensors 2>/dev/null | sort -V | tail -2); do python higgs_eval.py $a 2>&1 | tee -a $LOG; done
         fi
         open ../out_ft/listen.html ;;
esac
