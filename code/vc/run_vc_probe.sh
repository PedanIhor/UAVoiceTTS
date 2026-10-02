#!/bin/bash
# Probe VC across all voices: chatterbox and seed_f0, then scoring and the selection page.
cd "$(dirname "$0")"; set -eo pipefail
source ~/miniconda/etc/profile.d/conda.sh
export PYTHONUNBUFFERED=1 PYTORCH_ENABLE_MPS_FALLBACK=1
conda activate vccb;   python vc_probe.py chatterbox || echo "!!! chatterbox failed"; conda deactivate
conda activate vcseed; python vc_probe.py seed_f0    || echo "!!! seed_f0 failed"
python vc_probe_page.py; open ../out_vc_probe/listen.html
