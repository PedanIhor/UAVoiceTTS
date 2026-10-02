"""QA of r3 training phrases: loudness, speech rate, audio-text match (Whisper, Ukrainian).
python qa_data.py  (env mlxtts)  → ~/omni_ft/r3/qa.jsonl + summary + worst examples.
Then the filter reads qa.jsonl and drops rejects (see PASS below)."""
import os, re, sys, json, time
import numpy as np, soundfile as sf
SRC = os.path.expanduser(os.environ.get("SRC", "~/omni_ft/r3"))
OUT = os.path.join(SRC, "qa.jsonl")
done = {}
if os.path.exists(OUT):
    for l in open(OUT, encoding="utf-8"): x = json.loads(l); done[x["id"]] = x
def norm(t):
    t = t.replace("́", "").lower().replace("’", "'").replace("ʼ", "'")
    return re.sub(r"[^\w' ]+", " ", re.sub(r"\s+", " ", t)).split()
def cer(ref, hyp):
    a, b = " ".join(ref), " ".join(hyp)
    if not a: return 1.0
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i] + [0] * len(b)
        for j, cb in enumerate(b, 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb))
        prev = cur
    return prev[-1] / len(a)
from mlx_audio.stt import load
m = load("mlx-community/whisper-large-v3-turbo-asr-fp16")
rows = [json.loads(l) | {"part": p} for p in ("train", "dev") for l in open(os.path.join(SRC, "data", p + ".jsonl"), encoding="utf-8")]
t0 = time.time()
with open(OUT, "a", encoding="utf-8") as f:
    for i, r in enumerate(rows):
        if r["id"] in done: continue
        y, sr = sf.read(r["audio_path"], dtype="float32")
        if y.ndim > 1: y = y.mean(1)
        dur = len(y) / sr; peak = float(np.abs(y).max())
        rms = 20 * np.log10(np.sqrt(np.mean(y ** 2)) + 1e-9)
        text = r["text"].replace("́", "")
        hyp = m.generate(r["audio_path"], language="uk").text.strip()
        x = {"id": r["id"], "part": r["part"], "dur": round(dur, 2), "peak": round(peak, 3), "rms_db": round(float(rms), 1),
             "cps": round(len(text) / max(dur - 0.6, 0.3), 1), "cer": round(cer(norm(text), norm(hyp)), 3), "text": text, "asr": hyp}
        f.write(json.dumps(x, ensure_ascii=False) + "\n"); f.flush(); done[x["id"]] = x
        if (i + 1) % 100 == 0: print(f"{i+1}/{len(rows)}  {(time.time()-t0)/(len(done) or 1):.2f} s/phrase", flush=True)
xs = list(done.values())
def pct(k, q): return np.percentile([x[k] for x in xs], q)
print(f"\ntotal {len(xs)} | CER median {pct('cer',50):.3f}, 95% {pct('cer',95):.3f} | chars/s 5–95%: {pct('cps',5):.1f}–{pct('cps',95):.1f} "
      f"| peak 5–95%: {pct('peak',5):.2f}–{pct('peak',95):.2f} | RMS dB 5–95%: {pct('rms_db',5):.0f}…{pct('rms_db',95):.0f}")
PASS = lambda x: x["cer"] <= 0.15 and 7 <= x["cps"] <= 20 and x["rms_db"] > -45
bad = [x for x in xs if not PASS(x)]
print(f"fail the filter (CER ≤ 0.15, 7–20 chars/s, RMS > −45 dB): {len(bad)} of {len(xs)}")
for spk in ("mykyta", "oleksa", "tetiana", "lada", "kateryna"):
    s = [x for x in xs if x["id"].startswith(spk + "_")]; b = [x for x in s if not PASS(x)]
    print(f"  {spk:9s} rejects {len(b):4d}/{len(s)}  loudness: RMS median {np.median([x['rms_db'] for x in s]):.0f} dB")
print("\nworst by CER:")
for x in sorted(xs, key=lambda x: -x["cer"])[:12]:
    print(f"  {x['id']:14s} CER {x['cer']:.2f} {x['cps']:4.1f} c/s  TEXT: {x['text'][:70]}\n{'':17s}ASR:   {x['asr'][:70]}")
