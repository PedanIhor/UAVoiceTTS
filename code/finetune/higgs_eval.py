"""Evaluate Higgs: python higgs_eval.py [path to stepN.safetensors]  → out_ft/higgs-<run>_<step>/ and page out_ft/listen.html.
Texts are taken from out_ft/base/*.txt — same as for OmniVoice (no markup and with stress marks). TEMP — temperature (0.7)."""
import os, sys, time
import numpy as np, soundfile as sf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from higgs_common import load_model, load_adapter
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "models"))
from stress_common import VOICES
ad = sys.argv[1] if len(sys.argv) > 1 else None
TEMP = float(os.environ.get("TEMP", 0.7)); SEED = int(os.environ.get("SEED", 1)); LSCALE = float(os.environ.get("LORA_SCALE", 1))
tag = "higgs-" + (os.path.basename(os.path.dirname(ad)) + "_" + os.path.basename(ad).split(".")[0] if ad else "base") + (f"_seed{SEED}" if SEED != 1 else "") + (f"_x{LSCALE:g}" if ad and LSCALE != 1 else "")
OUT = os.path.join(HERE, "out_ft"); d = os.path.join(OUT, tag); os.makedirs(d, exist_ok=True)
model = load_model()
if ad:
    print("LoRA:", load_adapter(model, ad))
    if LSCALE != 1:                       # weaken LoRA: blend of base and fine-tuned model (0 = base, 1 = as trained)
        from higgs_common import LoRALinear
        for _, m in model.named_modules():
            if isinstance(m, LoRALinear): m.scale *= LSCALE
        print(f"LoRA scaled down to ×{LSCALE:g}")
REFS = os.path.join(HERE, "refs_tight")
for name, race, sex in VOICES:
    for kind in ("plain", "acute"):
        dst = os.path.join(d, f"{name}_{kind}.wav")
        if os.path.exists(dst): continue
        text = open(os.path.join(OUT, "base", f"{name}_{kind}.txt"), encoding="utf-8").read()
        t0 = time.time()
        gen = model.generate(text=text, ref_audio=os.path.join(REFS, name + ".wav"),
                             ref_text=open(os.path.join(REFS, name + ".txt"), encoding="utf-8").read().strip(),
                             temperature=TEMP, max_new_tokens=2048, seed=SEED)
        audio = np.concatenate([np.array(r.audio, dtype=np.float32).reshape(-1) for r in gen])
        sf.write(dst, audio, model.sample_rate); open(dst[:-4] + ".txt", "w", encoding="utf-8").write(text)
        print(f"{tag} {name} {kind}: {len(audio)/model.sample_rate:.1f} s of audio in {time.time()-t0:.0f} s", flush=True)
from ft_page import build
build()
