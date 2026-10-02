"""Higgs without reference: random voice with a fixed seed + pitch token → out_models/higgs_noref/"""
import os, sys, time, zlib
import numpy as np, soundfile as sf, mlx.core as mx
sys.path.insert(0, os.path.dirname(__file__))
from common import choose, text_for, HERE
from noref_common import higgs_prefix
from mlx_audio.tts import load
out = os.path.join(HERE, "out_models", "higgs_noref"); os.makedirs(out, exist_ok=True)
todo = [s for s in choose(sys.argv[1:]) if not os.path.exists(os.path.join(out, s[0] + ".wav"))]
print(f"[higgs_noref] to do: {len(todo)}")
if todo:
    model = load("nikolai-bratanov/mlx-bf16-higgs-tts-3-4b"); sr = model.sample_rate
    for name, race, sex, kind in todo:
        mx.random.seed(zlib.crc32(name.encode()))
        t0 = time.time()
        gen = model.generate(text=higgs_prefix(race, sex) + text_for(race, sex)["text"], temperature=0.8, max_new_tokens=2048)
        audio = np.concatenate([np.array(r.audio, dtype=np.float32).reshape(-1) for r in gen])
        sf.write(os.path.join(out, name + ".wav"), audio, sr)
        print(f"[higgs_noref] {name:28s} {time.time()-t0:5.1f} s")
