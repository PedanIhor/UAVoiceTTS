#!/bin/bash
# VC test: STEP=setup|run|score  (run = all three variants in turn; or ONLY=seed|seed_f0|chatterbox)
cd "$(dirname "$0")"; set -eo pipefail
source ~/miniconda/etc/profile.d/conda.sh
export PYTHONUNBUFFERED=1 PYTORCH_ENABLE_MPS_FALLBACK=1
case ${STEP:-run} in
  setup) bash setup_vc.sh ;;
  run)   for m in ${ONLY:-seed seed_f0 chatterbox}; do
           if [[ $m == chatterbox ]]; then conda activate vccb; else conda activate vcseed; fi
           python vc_test.py $m || echo "!!! $m failed — continuing with the rest"
           conda deactivate
         done
         conda activate vcseed; python vc_page.py --score; open ../out_vc/listen.html ;;
  score) conda activate vcseed; python vc_page.py --score; open ../out_vc/listen.html ;;
esac
