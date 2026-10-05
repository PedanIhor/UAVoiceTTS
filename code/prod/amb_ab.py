"""Accent at the start of lines: one line per frequent shared-spelling starter word («Коли», «Герою», «Не», «Принеси»…),
voiced with the Russian (refs_tight) and the approved Ukrainian references (refs_uk; undead also UK+fx). Same seed.
Input: out_probe/ambiguous_starts.json → prod/out_ab3/listen.html
bash amb_ab.sh   (mlxtts env; WORDS=14)"""
import os, sys, re, json, html, collections
import numpy as np, soundfile as sf
HERE = os.path.dirname(os.path.abspath(__file__)); TL = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(TL, "finetune"))
from higgs_common import load_model, load_adapter
from voice_fx import apply as fx
AD = os.path.expanduser(os.environ.get("ADAPTER", "~/omni_ft/higgs/exp/h3/step1000.safetensors"))
OLD, NEW = os.path.join(TL, "refs_tight"), os.path.join(TL, "refs_uk")
OUT = os.path.join(HERE, "out_ab3"); os.makedirs(OUT, exist_ok=True); TEMP, SR = 0.7, 24000
VOICES = [f[:-4] for f in sorted(os.listdir(NEW)) if f.endswith(".wav") and "__" not in f]      # voices with an approved UK reference
rows = json.load(open(os.path.join(HERE, "out_probe", "ambiguous_starts.json"), encoding="utf-8"))
first = lambda r: r["prefix"].split()[0].lower().replace("́", "")
order = [w for w, _ in collections.Counter(map(first, rows)).most_common()]
picked, used = [], collections.Counter()
for w in order:
    cand = [r for r in rows if first(r) == w and r["voice"] in VOICES and 40 <= len(r["text"]) <= 200]
    if not cand: continue
    cand.sort(key=lambda r: used[r["voice"]])                   # spread lines over voices
    picked.append(cand[0]); used[cand[0]["voice"]] += 1
    if len(picked) >= int(os.environ.get("WORDS", 14)): break

# extra lines heard by ear (id[:voice override] — voices without a UK reference are swapped for a same-sex one)
EXTRA = os.environ.get("EXTRA", "107_accept,107_complete:orcmalestandardnpc,114_accept:taurenmaleeldernpc,354_accept")
jobs = {j["id"]: j for j in map(json.loads, open(os.path.join(HERE, "jobs_tts.jsonl"), encoding="utf-8"))}
for e in filter(None, EXTRA.split(",")):
    jid, _, vo = e.partition(":"); j = jobs[jid]; txt = j["chunks"][0]["tts"]
    picked.append({"id": jid, "chunk": 0, "voice": vo or j["voice"], "prefix": " ".join(txt.split()[:2]), "text": txt})

def norm(t): return re.sub(r"[^\w' ]+", " ", t.replace("́", "").lower().replace("’", "'").replace("ʼ", "'")).split()
def cer(a, b):
    a, b = " ".join(a), " ".join(b)
    if not a: return 1.0
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i] + [0] * len(b)
        for j, cb in enumerate(b, 1): cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb))
        prev = cur
    return prev[-1] / len(a)
from mlx_audio.stt import load as load_stt
asr = load_stt("mlx-community/whisper-large-v3-turbo-asr-fp16")
model = load_model(); load_adapter(model, AD)
tr = []
for i, r in enumerate(picked):
    v = r["voice"]
    variants = [("RU", OLD, v), ("UK", NEW, v)] + ([("UK+fx", NEW, v + "__fx")] if os.path.exists(os.path.join(NEW, v + "__fx.wav")) else [])
    cells = []
    for tag, d, n in variants:
        p = os.path.join(OUT, f"{i:02d}_{v[:10]}_{tag.lower().replace('+', '_')}.wav")
        if not os.path.exists(p):
            gen = model.generate(text=r["text"], ref_audio=os.path.join(d, n + ".wav"),
                                 ref_text=open(os.path.join(d, n + ".txt"), encoding="utf-8").read().strip(),
                                 temperature=TEMP, max_new_tokens=int(len(r["text"]) * 3.5) + 200, seed=1000)
            sf.write(p, fx(v, np.concatenate([np.array(x.audio, dtype=np.float32).reshape(-1) for x in gen]), SR), SR)
        e = cer(norm(r["text"]), norm(asr.generate(p, language="uk").text))
        cells.append(f"<td>{tag} <small>CER {e:.2f}</small><br><audio controls preload=none src='{os.path.basename(p)}'></audio></td>")
    tr.append(f"<tr><td>{v.replace('npc', '')}</td><td><b>{html.escape(r['prefix'])}</b>{html.escape(r['text'][len(r['prefix']):])}</td>{''.join(cells)}</tr>")
    print(i, v, r["prefix"], flush=True)
open(os.path.join(OUT, "listen.html"), "w", encoding="utf-8").write(
    "<!doctype html><meta charset='utf-8'><style>body{font:14px system-ui;margin:16px;max-width:1400px}td{border:1px solid #ccc;padding:6px;vertical-align:top}audio{width:220px}</style>"
    "<h3>Accent at the start of lines: Russian vs Ukrainian references</h3><p>Bold = shared-spelling start. Listen to the first second.</p>"
    f"<table>{''.join(tr)}</table>")
print("Listen: code/prod/out_ab3/listen.html")
