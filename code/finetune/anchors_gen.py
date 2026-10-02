"""Anchor examples: base Higgs (not fine-tuned) voices ClassicUA quest texts with each NPC's voice (refs_tight),
without stress marks. They keep the fine-tuned model close to the "native" sound of NPC voices.
python anchors_gen.py [N per voice, default 12]  (env mlxtts) → ~/omni_ft/anchors/wav/<voice>__<k>.wav, anchors.jsonl
Test quests (tests_all.json) are excluded. Can be interrupted and resumed."""
import os, re, sys, json, random, time
import numpy as np, soundfile as sf
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CUA = os.environ.get("CUA", "/Applications/World of Warcraft/_classic_beta_/Interface/AddOns/ClassicUA")
OUT = os.path.expanduser("~/omni_ft/anchors"); os.makedirs(os.path.join(OUT, "wav"), exist_ok=True)
REFS = os.path.join(HERE, "refs_tight"); N = int(sys.argv[1]) if len(sys.argv) > 1 else 12
TEMP = float(os.environ.get("TEMP", 0.7))
def texts():
    skip = {t["quest"] for t in json.load(open(os.path.join(HERE, "tests_all.json"), encoding="utf-8"))}
    BAD = re.compile(r"[{}<>$|\[\]]|\d")
    chunks = []
    for f in ("quest_both.lua", "quest_alliance.lua", "quest_horde.lua"):
        s = open(os.path.join(CUA, "entries", "classic", f), encoding="utf-8").read()
        for m in re.finditer(r'\n\[(\d+)\] = \{ en="[^"]*",\s*\[===\[(.*?)\]===\],\s*\[===\[(.*?)\]===\]', s, re.S):
            if int(m.group(1)) in skip: continue
            t = re.sub(r"\{стать:([^:}]*):([^}]*)\}", r"\1", m.group(3))
            t = re.sub(r"\s*\n+\s*", " ", t).strip()
            sents = [x for x in re.split(r"(?<=[.!?…])\s+", t) if x.strip()]
            cur = ""
            for x in sents:                                     # chunks of 1–3 sentences, 60–220 chars
                if len(cur) + len(x) + 1 <= 220: cur = (cur + " " + x).strip()
                else:
                    if 60 <= len(cur): chunks.append(cur)
                    cur = x if len(x) <= 220 else ""
            if 60 <= len(cur) <= 220: chunks.append(cur)
    chunks = sorted({c for c in chunks if not BAD.search(c)})
    random.Random(5).shuffle(chunks); return chunks
if __name__ == "__main__":
    pool = texts(); voices = sorted(f[:-4] for f in os.listdir(REFS) if f.endswith(".wav"))
    print(f"text chunks {len(pool)}, voices {len(voices)}, {N} per voice", flush=True)
    jobs = [(v, k, pool[(vi * N + k) % len(pool)]) for vi, v in enumerate(voices) for k in range(N)]
    man = os.path.join(OUT, "anchors.jsonl")
    with open(man, "w", encoding="utf-8") as f:
        for v, k, t in jobs: f.write(json.dumps({"id": f"{v}__{k}", "voice": v, "text": t, "wav": os.path.join(OUT, "wav", f"{v}__{k}.wav")}, ensure_ascii=False) + "\n")
    todo = [(v, k, t) for v, k, t in jobs if not os.path.exists(os.path.join(OUT, "wav", f"{v}__{k}.wav"))]
    print(f"to do {len(todo)}", flush=True)
    if not todo: sys.exit()
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from higgs_common import load_model
    model = load_model(); t0 = time.time()
    for i, (v, k, t) in enumerate(todo):
        gen = model.generate(text=t, ref_audio=os.path.join(REFS, v + ".wav"),
                             ref_text=open(os.path.join(REFS, v + ".txt"), encoding="utf-8").read().strip(),
                             temperature=TEMP, max_new_tokens=1200, seed=100 + k)
        y = np.concatenate([np.array(r.audio, dtype=np.float32).reshape(-1) for r in gen])
        sf.write(os.path.join(OUT, "wav", f"{v}__{k}.wav"), y, model.sample_rate)
        el = time.time() - t0
        print(f"{i+1}/{len(todo)} {v:28s} {len(y)/model.sample_rate:4.1f} s  ~{el/(i+1)*(len(todo)-i-1)/60:.0f} min left", flush=True)
