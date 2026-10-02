"""Texts for checking all voices: new ClassicUA quest chunks (not test and not from anchors), 100–200 chars,
one per voice; with stress marks (ukrainian_word_stress). Env omnitrain → out_allv/texts.json"""
import os, sys, json
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(HERE, "models"))
from anchors_gen import texts
from stress_common import stressify
pool = [t for t in texts()[1000:] if 100 <= len(t) <= 200]                 # first 636 went into anchors
voices = sorted(f[:-4] for f in os.listdir(os.path.join(HERE, "refs_tight")) if f.endswith(".wav"))
out = os.path.join(HERE, "out_allv"); os.makedirs(out, exist_ok=True)
res = {v: {"plain": pool[i], "acute": stressify(pool[i])} for i, v in enumerate(voices)}
json.dump(res, open(os.path.join(out, "texts.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"{len(res)} voices; example: {res[voices[0]]['acute']}")
