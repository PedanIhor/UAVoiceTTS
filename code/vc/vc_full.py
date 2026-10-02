"""Full conversion: clean opentts clips (qa_filter) → NPC voices. Same-sex voices are assigned round-robin
(evenly). Each voice uses the VC from vc_choice.json. Source loudness is normalized to RMS −23 dB.
python vc_full.py plan               — build the plan (~/omni_ft/vc/plan.jsonl), once
python vc_full.py chatterbox|seed_f0 — convert clips for this model's voices (can be interrupted and resumed)"""
import os, sys, json, time, random
import numpy as np, soundfile as sf
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "finetune")); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
VC = os.path.expanduser(os.environ.get("VC", "~/omni_ft/vc")); REFS = os.path.join(HERE, "refs_all")
SEX = {"mykyta": "male", "oleksa": "male", "tetiana": "female", "lada": "female", "kateryna": "female"}
CHOICE = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "vc_choice.json")))
PLAN = os.path.join(VC, "plan.jsonl")
def make_plan():
    from qa_filter import passed
    ok = passed(); rows = []
    for part in ("train", "dev"):
        for l in open(os.path.expanduser(f"~/omni_ft/r3/data/{part}.jsonl"), encoding="utf-8"):
            r = json.loads(l)
            if r["id"] in ok: rows.append(r | {"part": part})
    rng = random.Random(11); rng.shuffle(rows)
    vs = {s: sorted(v for v in CHOICE if ("female" in v) == (s == "female")) for s in ("male", "female")}
    cnt = {"male": 0, "female": 0}; os.makedirs(VC, exist_ok=True)
    with open(PLAN, "w", encoding="utf-8") as f:
        for r in rows:
            s = SEX[r["id"].rsplit("_", 1)[0]]; v = vs[s][cnt[s] % len(vs[s])]; cnt[s] += 1
            f.write(json.dumps({"id": r["id"], "part": r["part"], "voice": v, "model": CHOICE[v], "text": r["text"],
                                "src": r["audio_path"], "wav": os.path.join(VC, "wav", f"{r['id']}__{v}.wav")}, ensure_ascii=False) + "\n")
    print(f"plan: {len(rows)} clips → {PLAN}; male voices {len(vs['male'])} (~{cnt['male']//len(vs['male'])} clips per voice), "
          f"female {len(vs['female'])} (~{cnt['female']//len(vs['female'])} per voice)")
if __name__ == "__main__":
    if sys.argv[1] == "plan": make_plan(); sys.exit()
    kind = sys.argv[1]
    jobs = [j for j in map(json.loads, open(PLAN, encoding="utf-8")) if j["model"] == kind and not os.path.exists(j["wav"])]
    print(f"[{kind}] to do {len(jobs)}", flush=True)
    if not jobs: sys.exit()
    from vc_common import make_converter
    conv = make_converter(kind); os.makedirs(os.path.join(VC, "wav"), exist_ok=True); tmp = os.path.join(VC, f"tmp_{kind}.wav"); t0 = time.time()
    for i, j in enumerate(jobs):
        y, sr = sf.read(j["src"], dtype="float32")
        if y.ndim > 1: y = y.mean(1)
        y = y * (10 ** (-23 / 20) / (np.sqrt(np.mean(y ** 2)) + 1e-9)); y = np.clip(y, -0.99, 0.99)
        sf.write(tmp, y, sr)
        try:
            out = conv(tmp, os.path.join(REFS, j["voice"] + ".wav"))
            sf.write(j["wav"], out, 24000)
        except Exception as e:
            print(f"  error {j['id']} → {j['voice']}: {e}", flush=True)
        if (i + 1) % 25 == 0:
            el = time.time() - t0
            print(f"[{kind}] {i+1}/{len(jobs)}  {el/(i+1):.1f} s/clip  ~{el/(i+1)*(len(jobs)-i-1)/60:.0f} min left", flush=True)
