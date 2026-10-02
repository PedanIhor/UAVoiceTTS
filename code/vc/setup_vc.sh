#!/bin/bash
# Two separate clean envs (Seed-VC and Chatterbox need incompatible transformers versions).
# Base packages from conda-forge (torch, scipy, librosa, ffmpeg): pip builds of scipy crash on recent macOS.
# RESET=1 — remove old envs and rebuild from scratch.
set -eo pipefail
source ~/miniconda/etc/profile.d/conda.sh
TOOLS=~/omni_ft/tools; mkdir -p $TOOLS
BASE='python=3.11 pytorch torchaudio numpy<2 scipy librosa pysoundfile ffmpeg setuptools<81 pip'
if [[ ${RESET:-1} == 1 ]]; then conda env remove -y -n vcseed 2>/dev/null || true; conda env remove -y -n vccb 2>/dev/null || true; fi

echo "=== vcseed (Seed-VC + resemblyzer for voice similarity scoring)"
conda env list | grep -q '^vcseed ' || conda create -y -n vcseed -c conda-forge --override-channels $BASE
conda activate vcseed
[[ -d $TOOLS/seed-vc ]] || git clone --depth 1 https://github.com/Plachtaa/seed-vc $TOOLS/seed-vc
pip install -q munch einops descript-audio-codec pydub resemblyzer hydra-core omegaconf "transformers==4.46.3" accelerate "huggingface-hub<1"
python -c "import torch, resemblyzer, munch, dac, transformers; print('vcseed ready: torch', torch.__version__, '| mps', torch.backends.mps.is_available(), '| transformers', transformers.__version__)"
conda deactivate

echo "=== vccb (Chatterbox VC)"
conda env list | grep -q '^vccb ' || conda create -y -n vccb -c conda-forge --override-channels $BASE
conda activate vccb
pip install -q --no-deps chatterbox-tts
pip install -q s3tokenizer "transformers==5.2.0" "diffusers==0.29.0" "conformer==0.3.2" omegaconf pyloudnorm safetensors \
  spacy-pkuseg pykakasi "resemble-perth @ git+https://github.com/resemble-ai/Perth.git@master"
python -c "import torch; from chatterbox.vc import ChatterboxVC; print('vccb ready: torch', torch.__version__, '| mps', torch.backends.mps.is_available())"
