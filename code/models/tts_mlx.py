"""Higgs TTS 3 via mlx-audio (Apple Silicon).
python tts_mlx.py higgs|higgsmlx [--all | words]
Anti-pause variants — VARIANT env var: tight (reference without pauses), sent (per sentence), tight_sent."""
import os, sys, time
import numpy as np, soundfile as sf
sys.path.insert(0, os.path.dirname(__file__))
from common import choose, text_for, ref_wav, ref_text, out_dir, SENT, split_sentences
from mlx_audio.tts import load
from mlx_audio.utils import load_audio

MODELS = {"higgs": "bosonai/higgs-audio-v3-tts-4b",                  # original, mlx-audio converts on load
          "higgsmlx": "nikolai-bratanov/mlx-bf16-higgs-tts-3-4b"}     # same weights, pre-converted to MLX bf16
key = sys.argv[1]; out = out_dir(key)
todo = [s for s in choose(sys.argv[2:]) if not os.path.exists(os.path.join(out, s[0] + ".wav"))]
print(f"[{key}] to do: {len(todo)} → {os.path.basename(out)}")
if not todo: sys.exit()
t_load = time.time()
model = load(MODELS[key])
print(f"[{key}] model loaded in {time.time()-t_load:.1f} s")
sr = model.sample_rate

def synth(text, name):
    gen = model.generate(text=text, ref_audio=ref_wav(name), ref_text=ref_text(name),
                             temperature=0.8, max_new_tokens=2048)
    return np.concatenate([np.array(r.audio, dtype=np.float32).reshape(-1) for r in gen])

for name, race, sex, kind in todo:
    full = text_for(race, sex)["text"]
    t0 = time.time()
    parts = split_sentences(full) if SENT else [full]
    chunks = []
    for i, text in enumerate(parts):
        chunks.append(synth(text, name))
        if SENT and i < len(parts) - 1:
            chunks.append(np.zeros(int(sr * 0.35), np.float32))
    audio = np.concatenate(chunks)
    sf.write(os.path.join(out, name + ".wav"), audio, sr)
    print(f"[{key}] {name:28s} {len(audio)/sr:5.1f} s of audio in {time.time()-t0:5.1f} s")
