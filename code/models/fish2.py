"""Fish S2 Pro — second chance, following the official fish-speech docs. What changes vs. previous tests:
 1) text starts with <|speaker:0|> — as in the official example; it binds the text to the reference voice
 2) official sampling params: temperature 1.0, top_p 0.9, top_k 30 (mlx-audio defaults are 0.7 / 0.7)
 3) longer reference: 15–25 s (docs: 10–30 s) — refs_long/
 4) no system "instruct" (it's not in the official code — hence the instruction being read aloud);
    style only via a square-bracket tag inside the text, as in the S2 docs
3 voices × 4 variants → out_models/fish2/<variant>/"""
import os, sys, time, zlib, html
import numpy as np, soundfile as sf, mlx.core as mx
sys.path.insert(0, os.path.dirname(__file__))
from common import HERE, text_for
from mlx_audio.tts import load
from mlx_audio.utils import load_audio
VOICES = [("humanmalestandardnpc", "human", "male"), ("dwarfmalestandardnpc", "dwarf", "male"), ("orcmalestandardnpc", "orc", "male")]
TAG = {"human": "[calm, clear voice]", "dwarf": "[loud, raspy, hearty voice]", "orc": "[deep, gravelly, guttural voice]"}
# variant: (reference folder or None, style tag in text)
VARIANTS = {"A_tight_official": ("refs_tight", False), "B_long_official": ("refs_long", False),
            "C_long_tag": ("refs_long", True), "D_noref_tag": (None, True),
            "E_long_uatag": ("refs_long", "ua"), "F_noref_uatag": (None, "ua")}
UA_TAG = "[speaking Ukrainian, native Ukrainian pronunciation]"
OUT = os.path.join(HERE, "out_models", "fish2")
jobs = [(v, *x) for v in VARIANTS for x in VOICES if not os.path.exists(os.path.join(OUT, v, x[0] + ".wav"))]
print("to do:", len(jobs))
if jobs:
    model = load("mlx-community/fish-audio-s2-pro"); sr = model.sample_rate
    for v, name, race, sex in jobs:
        refdir, use_tag = VARIANTS[v]
        tag = UA_TAG if use_tag == "ua" else TAG[race] if use_tag else ""
        text = "<|speaker:0|>" + (tag + " " if tag else "") + text_for(race, sex)["text"]
        kw = dict(temperature=1.0, top_p=0.9, top_k=30, max_tokens=2048)
        if refdir:
            ref = os.path.join(HERE, refdir, name + ".wav")
            kw.update(ref_audio=load_audio(ref, sample_rate=sr),
                      ref_text=open(ref[:-4] + ".txt", encoding="utf-8").read().strip())
        mx.random.seed(zlib.crc32(name.encode()))
        t0 = time.time()
        audio = np.concatenate([np.array(r.audio, dtype=np.float32).reshape(-1) for r in model.generate(text=text, **kw)])
        os.makedirs(os.path.join(OUT, v), exist_ok=True)
        sf.write(os.path.join(OUT, v, name + ".wav"), audio, sr)
        print(f"{v:18s} {name:24s} {time.time()-t0:5.1f} s")
rows = "".join(f"<tr><td><b>{r}</b></td><td><audio controls preload='none' src='../../refs_long/{n}.wav'></audio></td>"
               + "".join(f"<td><audio controls preload='none' src='{v}/{n}.wav'></audio></td>" for v in VARIANTS) + "</tr>" for n, r, _ in VOICES)
open(os.path.join(OUT, "listen.html"), "w", encoding="utf-8").write(
    "<meta charset='utf-8'><title>Fish: second chance</title><style>body{font:14px sans-serif;margin:20px}td{padding:4px 8px}audio{width:200px}</style>"
    "<h2>Fish S2 Pro per the official docs</h2><p>A — short reference; B — long reference (15–25 s); C — long reference + style tag in text; "
    "D — no reference, tag only; E/F — \"speaking Ukrainian\" tag with long reference / without reference. Everywhere: &lt;|speaker:0|&gt; and official sampling params.</p><table><tr><th></th><th>reference (long)</th>"
    + "".join(f"<th>{v}</th>" for v in VARIANTS) + "</tr>" + rows + "</table>")
print("Listen:out_models/fish2/listen.html")
