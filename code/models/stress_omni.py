"""Stress test for OmniVoice. OmniVoice has no Higgs-style "temperature": it picks tokens deterministically,
randomness is in the unmasking order (position_temperature, default 5.0). We scale it: t0.8 → 5.0 (default),
t0.55 → 3.4, t0.4 → 2.5."""
import os, sys, time
import soundfile as sf, torch
sys.path.insert(0, os.path.dirname(__file__))
from stress_common import VARIANTS, REFS, todo, mark, save, text_for
jobs = todo("omni")
print(f"[omni] to do: {len(jobs)}")
if jobs:
    from omnivoice import OmniVoice
    dev = "mps" if torch.backends.mps.is_available() else "cpu"
    model = OmniVoice.from_pretrained("k2-fsa/OmniVoice", device_map=dev, dtype=torch.float32, load_asr=True)
    for v, name, race, sex in jobs:
        kind, temp = VARIANTS[v]; text = mark(text_for(race, sex)["text"], kind)
        w, sr = sf.read(os.path.join(REFS, name + ".wav"), dtype="float32")
        t0 = time.time()
        audio = model.generate(text=text, language="uk", ref_audio=(torch.from_numpy(w).unsqueeze(0), sr),
                               position_temperature=5.0 * temp / 0.8)[0]
        save("omni", v, name, audio, 24000, text)
        print(f"[omni] {v:14s} {name:24s} {time.time()-t0:5.1f} s")
