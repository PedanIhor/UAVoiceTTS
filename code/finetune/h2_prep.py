"""Build the h2 dataset (env mlxtts): QA-passed VC phrases and anchors → Higgs codec codes.
Silence edges normalized as in r3 (35 dB threshold, 0.3 s each). NPC voice samples (refs_tight) → refcodes.
→ ~/omni_ft/h2/{train,dev}.jsonl: {id, kind: vc|anchor, voice, text, codes, T}"""
import os, sys, json, time
import numpy as np
from mlx_audio.utils import load_audio      # no librosa in mlxtts env — read and resample with mlx-audio
import mlx.core as mx
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from higgs_common import load_model
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); REFS = os.path.join(HERE, "refs_tight")
H2 = os.path.expanduser(os.environ.get("H2DIR", "~/omni_ft/h2")); os.makedirs(os.path.join(H2, "codes"), exist_ok=True); os.makedirs(os.path.join(H2, "refcodes"), exist_ok=True)
MAXCER = float(os.environ.get("H2_MAXCER", 0.2))
model = load_model(); codec = model._codec; SR = model.sample_rate
def enc(y): return np.array(codec.encode(mx.array(y.astype(np.float32)).reshape(1, -1, 1))[0].astype(mx.int32))
def load(p): return np.array(load_audio(p, sample_rate=SR), dtype=np.float32).reshape(-1)
def edges(y):
    """Trim edge silence (20 ms frames 35 dB below peak), keep 0.3 s on each side."""
    fr = int(0.02 * SR); n = len(y) // fr
    if not n: return None
    e = 20 * np.log10(np.sqrt((y[:n * fr].reshape(n, fr) ** 2).mean(1)) + 1e-9)
    loud = np.nonzero(e > e.max() - 35)[0]
    if not len(loud): return None
    pad = np.zeros(int(0.3 * SR), np.float32); y = y[loud[0] * fr:(loud[-1] + 1) * fr]
    y = y / (np.abs(y).max() + 1e-9) * 0.9
    return np.concatenate([pad, y, pad])
for f in sorted(os.listdir(REFS)):                                            # voice samples
    if f.endswith(".wav"):
        p = os.path.join(H2, "refcodes", f[:-4] + ".npy")
        if not os.path.exists(p): np.save(p, enc(load(os.path.join(REFS, f))))
rows = [json.loads(l) for l in open(os.path.join(H2, "qa.jsonl"), encoding="utf-8")]
ok = [x for x in rows if x["cer"] <= MAXCER and 7 <= x["cps"] <= 22]
print(f"passing QA: VC {sum(x['kind']=='vc' for x in ok)}, anchors {sum(x['kind']=='anchor' for x in ok)} (of {len(rows)})", flush=True)
out = {"train": [], "dev": []}; t0 = time.time(); devvoices = set()
AC = os.path.expanduser("~/omni_ft/anchors/anchors_acute.json"); acute = json.load(open(AC, encoding="utf-8")) if os.path.exists(AC) else {}
for i, x in enumerate(ok):
    cid = x["key"].replace(":", "_"); p = os.path.join(H2, "codes", cid + ".npy")
    if not os.path.exists(p):
        y = edges(load(x["wav"]))
        if y is None: continue
        np.save(p, enc(y))
    T = int(np.load(p, mmap_mode="r").shape[0])
    part = x["part"]
    if x["kind"] == "anchor" and x["voice"] not in devvoices and len(devvoices) < 25:   # one anchor from each of 25 voices — into dev
        devvoices.add(x["voice"]); part = "dev"
    row = {"id": cid, "kind": x["kind"], "voice": x["voice"], "text": x["text"], "codes": p, "T": T}
    if x["kind"] == "anchor" and x["key"][3:] in acute: row["text_acute"] = acute[x["key"][3:]]
    out[part].append(row)
    if (i + 1) % 500 == 0: print(f"{i+1}/{len(ok)}  {(time.time()-t0)/(i+1):.2f} s/phrase", flush=True)
for part, r in out.items():
    with open(os.path.join(H2, part + ".jsonl"), "w", encoding="utf-8") as f:
        for x in r: f.write(json.dumps(x, ensure_ascii=False) + "\n")
    print(f"{part}: VC {sum(x['kind']=='vc' for x in r)}, anchors {sum(x['kind']=='anchor' for x in r)} (with stress marks {sum('text_acute' in x for x in r)}), voices {len({x['voice'] for x in r})}")
