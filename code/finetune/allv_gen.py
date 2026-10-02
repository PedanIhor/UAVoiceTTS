"""Voice all NPC voices: first base Higgs (text without marks — how the voice sounds "as is"),
then h3 (text with stress marks). Env mlxtts. ADAPTER — path to LoRA (default h3 step1000)."""
import os, sys, json, time
import numpy as np, soundfile as sf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from higgs_common import load_model, load_adapter
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); OUT = os.path.join(HERE, "out_allv"); REFS = os.path.join(HERE, "refs_tight")
AD = os.path.expanduser(os.environ.get("ADAPTER", "~/omni_ft/higgs/exp/h3/step1000.safetensors"))
TX = json.load(open(os.path.join(OUT, "texts.json"), encoding="utf-8")); TEMP = float(os.environ.get("TEMP", 0.7))
model = load_model()
def run(tag, kind):
    d = os.path.join(OUT, tag); os.makedirs(d, exist_ok=True); t0 = time.time(); todo = [v for v in TX if not os.path.exists(os.path.join(d, v + ".wav"))]
    for i, v in enumerate(todo):
        gen = model.generate(text=TX[v][kind], ref_audio=os.path.join(REFS, v + ".wav"),
                             ref_text=open(os.path.join(REFS, v + ".txt"), encoding="utf-8").read().strip(), temperature=TEMP, max_new_tokens=1500, seed=1)
        y = np.concatenate([np.array(r.audio, dtype=np.float32).reshape(-1) for r in gen])
        sf.write(os.path.join(d, v + ".wav"), y, model.sample_rate)
        print(f"[{tag}] {i+1}/{len(todo)} {v:28s} {len(y)/model.sample_rate:4.1f} s  ~{(time.time()-t0)/(i+1)*(len(todo)-i-1)/60:.0f} min", flush=True)
run("base", "plain")
print("LoRA:", load_adapter(model, AD))
run("h3", "acute")
