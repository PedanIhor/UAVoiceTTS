"""Stress check for a single word: several spelling variants × temperature × voices, 3 attempts each.
python word_probe.py  (mlxtts env) → out_probe/listen.html"""
import os, sys, html
import numpy as np, soundfile as sf
HERE = os.path.dirname(os.path.abspath(__file__)); TL = os.path.dirname(HERE); sys.path.insert(0, os.path.join(TL, "finetune"))
from higgs_common import load_model, load_adapter
OUT = os.path.join(HERE, "out_probe"); os.makedirs(OUT, exist_ok=True); REFS = os.path.join(TL, "refs_tight")
# WORD — word with the stressed vowel in uppercase (впОралася); PHRASES — phrases with {w} (or {W} — capitalized), separated by «;;»
WORD = os.environ.get("WORD", "герОю")
PHRASES = os.environ.get("PHRASES", "Дякую тобі за допомогу, {w}. Ти добре впоралась.;;{W}, я з задоволенням спостерігав за твоїми успіхами.").split(";;")
_i = [k for k, ch in enumerate(WORD) if ch.isupper() and k > 0][0]
_acute = WORD[:_i] + WORD[_i].lower() + "\u0301" + WORD[_i + 1:]
VARIANTS = {f"acute ({_acute})": _acute, f"uppercase ({WORD})": WORD, f"acute+uppercase ({WORD[:_i+1]}\u0301{WORD[_i+1:]})": WORD[:_i + 1] + "\u0301" + WORD[_i + 1:],
            f"unmarked ({WORD.lower()})": WORD.lower()}
OUT = os.path.join(HERE, "out_probe", WORD.lower()); os.makedirs(OUT, exist_ok=True)
VOICES = os.environ.get("VOICES", "taurenmaleeldernpc,orcmalestandardnpc").split(","); TEMPS = [0.7, 0.5]
model = load_model(); load_adapter(model, os.path.expanduser("~/omni_ft/higgs/exp/h3/step1000.safetensors")); rows = []
for pi, PHRASE in enumerate(PHRASES):
  for vn, w in VARIANTS.items():
    text = PHRASE.format(w=w, W=w[:1].upper() + w[1:])
    for v in VOICES:
        for t in TEMPS:
            cells = []
            for k in range(3):
                p = os.path.join(OUT, f"p{pi}_{list(VARIANTS).index(vn)}_{v[:6]}_{t}_{k}.wav")
                if not os.path.exists(p):
                    gen = model.generate(text=text, ref_audio=os.path.join(REFS, v + ".wav"),
                                         ref_text=open(os.path.join(REFS, v + ".txt"), encoding="utf-8").read().strip(), temperature=t, max_new_tokens=600, seed=50 + k)
                    sf.write(p, np.concatenate([np.array(r.audio, dtype=np.float32).reshape(-1) for r in gen]), model.sample_rate)
                cells.append(f"<audio controls preload='none' src='{os.path.basename(p)}'></audio>")
            rows.append(f"<tr><td>{html.escape(text)}</td><td>{v.replace('npc','')}</td><td>{t}</td><td>{''.join(cells)}</td></tr>"); print(vn, v, t, flush=True)
open(os.path.join(OUT, "listen.html"), "w", encoding="utf-8").write("<!doctype html><meta charset='utf-8'><style>body{font:14px system-ui;margin:16px}td{border:1px solid #ccc;padding:5px}audio{width:200px}</style>"
    f"<h3>Stress in the word «{html.escape(_acute)}»</h3><table><tr><th>input text</th><th>voice</th><th>temp.</th><th>3 attempts</th></tr>{''.join(rows)}</table>")
print(f"Listen: prod/out_probe/{WORD.lower()}/listen.html")
