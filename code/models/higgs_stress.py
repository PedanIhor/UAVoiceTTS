"""Higgs: checks whether the model follows stress marks (no official support) and whether
a lower temperature makes stresses consistent. 3 voices × 6 variants → out_stress_higgs/"""
import os, re, sys, time, json, html
import numpy as np, soundfile as sf
sys.path.insert(0, os.path.dirname(__file__))
from common import HERE, text_for
from mlx_audio.tts import load
from ukrainian_word_stress import Stressifier, StressSymbol
try:
    st = Stressifier(stress_symbol=StressSymbol.CombiningAcuteAccent); st("тест")
except Exception as e:
    from ukrainian_word_stress import Disambiguation
    print("stanza unavailable, dictionary-based stress:", str(e).splitlines()[0])
    st = Stressifier(stress_symbol=StressSymbol.CombiningAcuteAccent, disambiguation=Disambiguation.Dictionary)
A, VOW = "́", "аеєиіїоуюяАЕЄИІЇОУЮЯ"
plain = lambda t: t
acute = lambda t: st(t)
upper = lambda t: re.sub(f"([{VOW}]){A}", lambda m: m.group(1).upper(), st(t))
VARIANTS = {"0_plain_t0.8": (plain, 0.8), "1_acute_t0.8": (acute, 0.8), "2_upper_t0.8": (upper, 0.8),
            "3_plain_t0.4": (plain, 0.4), "4_acute_t0.4": (acute, 0.4), "5_plain_t0.2": (plain, 0.2)}
REFS = os.path.join(HERE, "refs_tight"); OUT = os.path.join(HERE, "out_stress_higgs")
VOICES = [("humanmalestandardnpc", "human", "male"), ("dwarfmalestandardnpc", "dwarf", "male"), ("orcmalestandardnpc", "orc", "male")]
todo = [(v, *x) for v in VARIANTS for x in VOICES if not os.path.exists(os.path.join(OUT, v, x[0] + ".wav"))]
print("to do:", len(todo))
if todo:
    model = load("bosonai/higgs-audio-v3-tts-4b"); sr = model.sample_rate
    for v, name, race, sex in todo:
        fn, temp = VARIANTS[v]; text = fn(text_for(race, sex)["text"])
        ref_txt = open(os.path.join(REFS, name + ".txt"), encoding="utf-8").read().strip()
        t0 = time.time()
        gen = model.generate(text=text, ref_audio=os.path.join(REFS, name + ".wav"), ref_text=ref_txt,
                             temperature=temp, max_new_tokens=2048)
        audio = np.concatenate([np.array(r.audio, dtype=np.float32).reshape(-1) for r in gen])
        os.makedirs(os.path.join(OUT, v), exist_ok=True)
        sf.write(os.path.join(OUT, v, name + ".wav"), audio, sr)
        open(os.path.join(OUT, v, name + ".txt"), "w", encoding="utf-8").write(text)
        print(f"{v:14s} {name:24s} {time.time()-t0:5.1f} s")
rows = "".join(f"<tr><td><b>{r}</b></td>" + "".join(f"<td><audio controls preload='none' src='{v}/{n}.wav'></audio></td>" for v in VARIANTS) + "</tr>" for n, r, _ in VOICES)
texts = "".join(f"<p><b>{v}</b>: {html.escape(open(os.path.join(OUT, v, 'humanmalestandardnpc.txt'), encoding='utf-8').read())}</p>"
                for v in VARIANTS if os.path.exists(os.path.join(OUT, v, "humanmalestandardnpc.txt")))
open(os.path.join(OUT, "listen.html"), "w", encoding="utf-8").write(
    "<meta charset='utf-8'><title>Higgs: stress</title><style>body{font:14px sans-serif;margin:20px}td{padding:6px}audio{width:190px}</style>"
    "<h2>Higgs: stress marks and temperature</h2><p>t = temperature (default 0.8; lower = less randomness).</p><table><tr><th></th>"
    + "".join(f"<th>{v}</th>" for v in VARIANTS) + "</tr>" + rows + "</table><h3>Input (human)</h3>" + texts)
print("Listen:out_stress_higgs/listen.html")
