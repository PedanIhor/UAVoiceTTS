#!/bin/bash
# One-time environment setup for OmniVoice fine-tuning on Mac (MPS).
# torch/scipy from conda-forge — single OpenMP (otherwise segfault on CPU, as happened with StyleTTS2).
set -e
source ~/miniconda/etc/profile.d/conda.sh
conda env list | grep -q '^omnitrain ' || conda create -y -n omnitrain python=3.11
conda install -y -n omnitrain -c conda-forge pytorch torchaudio scipy librosa pysoundfile   # in conda-forge soundfile is called pysoundfile
conda activate omnitrain
pip install "omnivoice[lora]" datasets tensorboard ukrainian-word-stress stanza
python -c "import torch, scipy.optimize; print('torch', torch.__version__, '| MPS:', torch.backends.mps.is_available())"
echo "Done. Next: bash finetune/run_pilot.sh"
