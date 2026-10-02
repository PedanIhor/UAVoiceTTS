"""Stress test for Higgs: python stress_higgs.py higgs|higgsmlx"""
import os, sys, time
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from stress_common import VARIANTS, REFS, todo, mark, save, ref_text, text_for
from mlx_audio.tts import load
IDS = {"higgs": "bosonai/higgs-audio-v3-tts-4b", "higgsmlx": "nikolai-bratanov/mlx-bf16-higgs-tts-3-4b"}
key = sys.argv[1]; jobs = todo(key)
print(f"[{key}] to do: {len(jobs)}")
if jobs:
    model = load(IDS[key]); sr = model.sample_rate
    for v, name, race, sex in jobs:
        kind, temp = VARIANTS[v]; text = mark(text_for(race, sex)["text"], kind)
        t0 = time.time()
        gen = model.generate(text=text, ref_audio=os.path.join(REFS, name + ".wav"), ref_text=ref_text(name),
                             temperature=temp, max_new_tokens=2048)
        audio = np.concatenate([np.array(r.audio, dtype=np.float32).reshape(-1) for r in gen])
        save(key, v, name, audio, sr, text)
        print(f"[{key}] {v:14s} {name:24s} {time.time()-t0:5.1f} s")
