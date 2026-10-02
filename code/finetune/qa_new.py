"""QA of new material for h2 (env mlxtts): VC phrases (~/omni_ft/vc) and anchors (~/omni_ft/anchors).
Whisper (uk) → CER vs text, speech rate. → ~/omni_ft/h2/qa.jsonl. Can be interrupted and resumed."""
import os, re, json, time
import soundfile as sf
H2 = os.path.expanduser(os.environ.get("H2DIR", "~/omni_ft/h2")); os.makedirs(H2, exist_ok=True); OUT = os.path.join(H2, "qa.jsonl")
VCPLAN = os.path.expanduser(os.environ.get("VCPLAN", "~/omni_ft/vc/plan.jsonl")); OLDQA = os.environ.get("OLDQA")
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
items = []
for j in map(json.loads, open(VCPLAN, encoding="utf-8")):
    items.append({"key": "vc:" + j["id"], "kind": "vc", "part": j["part"], "voice": j["voice"], "text": j["text"], "wav": j["wav"]})
for j in map(json.loads, open(os.path.expanduser("~/omni_ft/anchors/anchors.jsonl"), encoding="utf-8")):
    items.append({"key": "an:" + j["id"], "kind": "anchor", "part": "train", "voice": j["voice"], "text": j["text"], "wav": j["wav"]})
if OLDQA and not os.path.exists(OUT):                     # carry over checks for the same files from the previous run
    old = {json.loads(l)["wav"]: json.loads(l) for l in open(os.path.expanduser(OLDQA), encoding="utf-8")}
    with open(OUT, "w", encoding="utf-8") as f:
        for x in items:
            if x["wav"] in old: f.write(json.dumps(old[x["wav"]] | {"key": x["key"], "part": x["part"]}, ensure_ascii=False) + "\n")
done = {json.loads(l)["key"] for l in open(OUT, encoding="utf-8")} if os.path.exists(OUT) else set()
todo = [x for x in items if x["key"] not in done and os.path.exists(x["wav"])]
print(f"total {len(items)}, files present {sum(os.path.exists(x['wav']) for x in items)}, to check {len(todo)}", flush=True)
from mlx_audio.stt import load
m = load("mlx-community/whisper-large-v3-turbo-asr-fp16"); t0 = time.time()
with open(OUT, "a", encoding="utf-8") as f:
    for i, x in enumerate(todo):
        try:
            dur = sf.info(x["wav"]).duration; hyp = m.generate(x["wav"], language="uk").text.strip()
        except Exception as e:
            print("  error", x["key"], e); continue
        t = x["text"].replace("́", "")
        f.write(json.dumps(x | {"dur": round(dur, 2), "cps": round(len(t) / max(dur - 0.6, 0.3), 1),
                                "cer": round(cer(norm(t), norm(hyp)), 3), "asr": hyp}, ensure_ascii=False) + "\n"); f.flush()
        if (i + 1) % 200 == 0: print(f"{i+1}/{len(todo)}  {(time.time()-t0)/(i+1):.2f} s/phrase", flush=True)
rows = [json.loads(l) for l in open(OUT, encoding="utf-8")]
for k in ("vc", "anchor"):
    r = [x for x in rows if x["kind"] == k]; ok = [x for x in r if x["cer"] <= 0.2 and 7 <= x["cps"] <= 22]
    print(f"{k}: checked {len(r)}, passing (CER ≤ 0.2, 7–22 chars/s) {len(ok)}")
