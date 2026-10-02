"""Probe VC across all NPC voices (refs_all): 2 clean same-sex clips each via chatterbox and seed_f0.
python vc_probe.py chatterbox|seed_f0  → out_vc_probe/<model>/<voice>__<id>.wav"""
import os, sys, json, time, random
import numpy as np, soundfile as sf
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "finetune")); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from qa_filter import passed
OUT = os.path.join(HERE, "out_vc_probe"); REFS = os.path.join(HERE, "refs_all")
SEX = {"mykyta": "male", "oleksa": "male", "tetiana": "female", "lada": "female", "kateryna": "female"}
def voices():
    return sorted(f[:-4] for f in os.listdir(REFS) if f.endswith(".wav"))
def vsex(v): return "female" if "female" in v else "male"
def plan():
    rows = [json.loads(l) for l in open(os.path.expanduser("~/omni_ft/r3/data/train.jsonl"), encoding="utf-8")]
    ok = passed(); pool = {"male": [], "female": []}
    for r in rows:
        if r["id"] in ok and "́" in r["text"] and 3 <= sf.info(r["audio_path"]).duration <= 7:
            pool[SEX[r["id"].rsplit("_", 1)[0]]].append(r)
    jobs = []
    for v in voices():
        rng = random.Random(v)
        for r in rng.sample(pool[vsex(v)], 2): jobs.append((v, r))
    d = os.path.join(OUT, "src"); os.makedirs(d, exist_ok=True)
    for _, r in jobs:
        dst = os.path.join(d, r["id"] + ".wav")
        if not os.path.exists(dst):
            y, sr = sf.read(r["audio_path"]); sf.write(dst, y, sr)
            open(dst[:-4] + ".txt", "w", encoding="utf-8").write(r["text"])
    json.dump([(v, r["id"]) for v, r in jobs], open(os.path.join(OUT, "plan.json"), "w"))
    return jobs
if __name__ == "__main__":
    kind = sys.argv[1]; d = os.path.join(OUT, kind); os.makedirs(d, exist_ok=True)
    jobs = [(v, r) for v, r in plan() if not os.path.exists(os.path.join(d, f"{v}__{r['id']}.wav"))]
    print(f"[{kind}] voices {len(voices())}, to do {len(jobs)}", flush=True)
    if not jobs: sys.exit()
    from vc_common import make_converter
    conv = make_converter(kind); t0 = time.time()
    for i, (v, r) in enumerate(jobs):
        y = conv(os.path.join(OUT, "src", r["id"] + ".wav"), os.path.join(REFS, v + ".wav"))
        sf.write(os.path.join(d, f"{v}__{r['id']}.wav"), y, 24000)
        print(f"[{kind}] {i+1}/{len(jobs)} {v:28s} {r['id']:14s} ~{(time.time()-t0)/(i+1)*(len(jobs)-i-1)/60:.0f} min left", flush=True)
