"""Blind A/B test on quest lines: current Russian NPC references (refs_tight) vs approved Ukrainian ones
(refs_uk/<voice>.wav, built by build_refs_uk.py and picked). If refs_uk/<voice>__fx.wav exists (undead with the
crypt effect baked into the reference), it is tested as a third variant. Same seed for all → prod/out_ab2/listen.html
bash ref_ab.sh   (mlxtts env; VOICES=a,b,c  LINES=5)"""
import os, sys, re, json, html, random
import numpy as np, soundfile as sf
HERE = os.path.dirname(os.path.abspath(__file__)); TL = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(TL, "finetune"))
from higgs_common import load_model, load_adapter
from voice_fx import apply as fx
AD = os.path.expanduser(os.environ.get("ADAPTER", "~/omni_ft/higgs/exp/h3/step1000.safetensors"))
VOICES = os.environ.get("VOICES", "orcmalestandardnpc,humanfemalestandardnpc,undeadmalestandardnpc,taurenmaleeldernpc").split(",")
LINES = int(os.environ.get("LINES", 5)); TEMP = 0.7; SR = 24000
OLD, NEW = os.path.join(TL, "refs_tight"), os.path.join(TL, "refs_uk")
OUT = os.path.join(HERE, "out_ab2"); os.makedirs(OUT, exist_ok=True)
for v in VOICES:
    if not os.path.exists(os.path.join(NEW, v + ".wav")): sys.exit(f"no approved Ukrainian reference for {v}: python build_refs_uk.py pick {v}=<speaker>")

def norm(t):
    t = t.replace("́", "").lower().replace("’", "'").replace("ʼ", "'")
    return re.sub(r"[^\w' ]+", " ", re.sub(r"\s+", " ", t)).split()
def cer(ref, hyp):
    a, b = " ".join(ref), " ".join(hyp)
    if not a: return 1.0
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i] + [0] * len(b)
        for j, cb in enumerate(b, 1): cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb))
        prev = cur
    return prev[-1] / len(a)

from mlx_audio.stt import load as load_stt
asr = load_stt("mlx-community/whisper-large-v3-turbo-asr-fp16")
def asr_cer(path, text): return cer(norm(text), norm(asr.generate(path, language="uk").text))

# the same quest lines with every reference variant
model = load_model(); load_adapter(model, AD)
jobs = [json.loads(l) for l in open(os.path.join(HERE, "jobs_tts.jsonl"), encoding="utf-8")]
rows, rng = [], random.Random(3)
for v in VOICES:
    pool = [c for j in jobs if j["voice"] == v for c in j["chunks"][:1] if 60 <= len(c["show"]) <= 220]
    rng.shuffle(pool)
    variants = [("RU", OLD, v), ("UK", NEW, v)] + ([("UK+fx", NEW, v + "__fx")] if os.path.exists(os.path.join(NEW, v + "__fx.wav")) else [])
    refs = " ".join(f"{tag} <audio controls preload=none src='../../{os.path.basename(d)}/{n}.wav'></audio>" for tag, d, n in variants)
    rows.append(f"<tr class=v><td colspan={len(variants) + 2}><b>{v.replace('npc', '')}</b> — references: {refs}</td></tr>")
    for i, c in enumerate(pool[:LINES]):
        cells = {}
        for tag, d, n in variants:
            p = os.path.join(OUT, f"{v[:12]}_{i}_{tag.lower().replace('+', '_')}.wav")
            if not os.path.exists(p):
                gen = model.generate(text=c["tts"], ref_audio=os.path.join(d, n + ".wav"),
                                     ref_text=open(os.path.join(d, n + ".txt"), encoding="utf-8").read().strip(),
                                     temperature=TEMP, max_new_tokens=int(len(c["show"]) * 3.5) + 200, seed=1000)
                y = np.concatenate([np.array(r.audio, dtype=np.float32).reshape(-1) for r in gen])
                sf.write(p, fx(v, y, SR), SR)
            cells[tag] = (os.path.basename(p), asr_cer(p, c["tts"]))
        order = list(cells); rng.shuffle(order); L = "ABC"
        rows.append(f"<tr><td>{html.escape(c['show'])}</td>"
                    + "".join(f"<td>{L[k]} <audio controls preload=none src='{cells[t][0]}'></audio></td>" for k, t in enumerate(order))
                    + "<td><details><summary>answer</summary>" + ", ".join(f"{L[k]}={t} ({cells[t][1]:.2f})" for k, t in enumerate(order)) + "</details></td></tr>")
        print(v, i, " · ".join(f"{t} CER {cells[t][1]:.2f}" for t in cells), flush=True)
open(os.path.join(OUT, "listen.html"), "w", encoding="utf-8").write(
    "<!doctype html><meta charset='utf-8'><style>body{font:14px system-ui;margin:16px;max-width:1300px}td{border:1px solid #ccc;padding:6px;vertical-align:top}"
    "audio{width:220px}tr.v td{background:#eef}</style><h3>Blind test: Russian vs Ukrainian NPC references</h3>"
    "<p>For each line pick the best one (accent, timbre, cleanliness), then open «answer». CER = Whisper error (lower is better).</p>"
    f"<table>{''.join(rows)}</table>")
print("Listen: code/prod/out_ab2/listen.html")
