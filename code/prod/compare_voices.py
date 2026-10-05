"""Old vs new voice on the same quest line, for every voice that has a Ukrainian reference.
Old = the line already voiced in the game build (out/, Russian references); voices with no such line are voiced with
refs_tight here. New = the same line through synth.py with refs_uk (production settings: QA retries, undead fx).
python compare_voices.py prepare → out_cmp/jobs.jsonl (+ copies of old sounds);  bash compare_voices.sh → out_cmp/listen.html"""
import os, sys, json, html, shutil, random
HERE = os.path.dirname(os.path.abspath(__file__)); TL = os.path.dirname(HERE)
OUT = os.path.join(HERE, "out_cmp"); os.makedirs(os.path.join(OUT, "old", "sounds"), exist_ok=True)
NEW = os.path.join(TL, "refs_uk")
VOICES = sorted(f[:-4] for f in os.listdir(NEW) if f.endswith(".wav") and "__" not in f)
ALL = os.path.join(TL, "..", "_archive", "tmp", "jobs_tts_all.jsonl")
def ref_id_old(v):                                  # same identity format as synth.ref_id, for refs_tight
    import hashlib; h = hashlib.md5(); d = os.path.join(TL, "refs_tight")
    for ext in (".wav", ".txt"): h.update(open(os.path.join(d, v + ext), "rb").read())
    return f"refs_tight/{v}:{h.hexdigest()[:8]}"
START = ["durotar", "mulgore", "tirisfal", "elwynn", "dunmorogh", "teldrassil"]
if sys.argv[1:2] == ["prepare"]:
    zq = json.load(open(os.path.join(HERE, "zones.json"))); start = {q for z in START for q in zq[z]}
    jobs = {j["id"]: j for f in (ALL, os.path.join(HERE, "jobs_tts.jsonl")) if os.path.exists(f)
            for j in map(json.loads, open(f, encoding="utf-8")) if j["quest"] in start}            # starting zones only
    meta = [json.loads(l) for l in open(os.path.join(HERE, "out", "meta.jsonl"), encoding="utf-8")]
    rng = random.Random(5); pick, old_meta = [], []
    for v in VOICES:
        done = [m for m in meta if m["voice"] == v and m["id"] in jobs]
        if done:                                   # a random line already in the game build, ~15 s preferred
            rng.shuffle(done); done.sort(key=lambda m: abs(m["dur"] - 15) > 10); m = done[0]
            shutil.copyfile(os.path.join(HERE, "out", "sounds", m["file"]), os.path.join(OUT, "old", "sounds", m["file"]))
            j = jobs[m["id"]]                       # keep the old sound: mark it as made from this text with refs_tight
            m = m | {"tts": " | ".join(c["tts"] for c in j["chunks"]), "ref": ref_id_old(v)}
            old_meta.append(m); pick.append(j)
        else:                                      # in starting zones but not voiced yet (e.g. class quests): voice old too
            cand = [j for j in jobs.values() if j["voice"] == v]
            if not cand: print("not in starting zones:", v); continue
            rng.shuffle(cand); pick.append(cand[0])
    with open(os.path.join(OUT, "jobs.jsonl"), "w", encoding="utf-8") as f:
        for j in pick: f.write(json.dumps(j, ensure_ascii=False) + "\n")
    with open(os.path.join(OUT, "old", "meta.jsonl"), "w", encoding="utf-8") as f:
        for m in old_meta: f.write(json.dumps(m, ensure_ascii=False) + "\n")
    print(f"lines: {len(pick)} (old already voiced: {len(old_meta)}, old to voice: {len(pick) - len(old_meta)})"); sys.exit()
# page
jobs = [json.loads(l) for l in open(os.path.join(OUT, "jobs.jsonl"), encoding="utf-8")]
def meta(d): return {m["id"]: m for m in map(json.loads, open(os.path.join(OUT, d, "meta.jsonl"), encoding="utf-8"))} if os.path.exists(os.path.join(OUT, d, "meta.jsonl")) else {}
old, new = meta("old"), meta("new"); tr = []
for j in jobs:
    o, n = old.get(j["id"]), new.get(j["id"])
    cell = lambda m, d: f"<audio controls preload=none src='{d}/sounds/{m['file']}'></audio><br><small>{m['dur']} s · CER {max(q['cer'] for q in m['qa']):.2f}</small>" if m else "—"
    tr.append(f"<tr><td>{j['voice'].replace('npc', '')}</td><td>{html.escape(' '.join(c['show'] for c in j['chunks']))[:400]}</td>"
              f"<td>{cell(o, 'old')}</td><td>{cell(n, 'new')}</td></tr>")
open(os.path.join(OUT, "listen.html"), "w", encoding="utf-8").write(
    "<!doctype html><meta charset='utf-8'><style>body{font:14px system-ui;margin:16px;max-width:1300px}td{border:1px solid #ccc;padding:6px;vertical-align:top}audio{width:230px}</style>"
    "<h3>Old (Russian references) vs new (Ukrainian references) — same line, production settings</h3>"
    f"<table><tr><th>voice</th><th>line</th><th>OLD</th><th>NEW</th></tr>{''.join(tr)}</table>")
print("Listen: code/prod/out_cmp/listen.html")
