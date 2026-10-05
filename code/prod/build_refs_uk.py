"""Ukrainian NPC voice references, styled like the Russian ones: 4–6 short crisp phrases (1.2–3.5 s), 7–10 s total,
tight pauses, ONE source speaker per reference. Source: our VC clips (~/omni_ft/vc/wav, plan.jsonl).
Builds one candidate per source speaker → code/refs_uk/cand/<voice>__<speaker>.wav/.txt and refs_uk/cand/listen.html.
No quest lines are generated. After approval:  python build_refs_uk.py pick <voice>=<speaker> ...
python build_refs_uk.py            (mlxtts env; VOICES=a,b,c)
More candidates per speaker: VARIANTS=clear,lively,clear2 MAX_CLIP=4.5 PAGE=other.html"""
import os, sys, re, json, html, shutil
import numpy as np, soundfile as sf
HERE = os.path.dirname(os.path.abspath(__file__)); TL = os.path.dirname(HERE)
VC = os.path.expanduser(os.environ.get("VC", "~/omni_ft/vc"))
VOICES = os.environ.get("VOICES", "orcmalestandardnpc,humanfemalestandardnpc,undeadmalestandardnpc,taurenmaleeldernpc").split(",")
OLD, NEW = os.path.join(TL, "refs_tight"), os.path.join(TL, "refs_uk"); CAND = os.path.join(NEW, "cand"); os.makedirs(CAND, exist_ok=True)
SR, GAP, MIN_T, MAX_T = 24000, 0.35, 7.0, 10.5

if sys.argv[1:2] == ["fx"]:                        # undead: candidates with the crypt effect (the Russian undead refs already have Blizzard's effect)
    sys.path.insert(0, os.path.join(TL, "finetune")); from voice_fx import apply as fx
    page = os.path.join(CAND, os.environ.get("PAGE", "listen.html")); h = open(page, encoding="utf-8").read()
    for f in sorted(os.listdir(CAND)):
        if not f.endswith(".wav") or f.endswith("__fx.wav") or not f.startswith("undead"): continue
        y, sr = sf.read(os.path.join(CAND, f), dtype="float32"); fxn = f[:-4] + "__fx.wav"
        sf.write(os.path.join(CAND, fxn), fx(f, y, sr), sr)
        shutil.copyfile(os.path.join(CAND, f[:-4] + ".txt"), os.path.join(CAND, fxn[:-4] + ".txt"))   # can be picked as a reference too
        tag = f"src='{f}'></audio>"
        if tag in h and fxn not in h: h = h.replace(tag, tag + f"<br>with effect ({fxn[len(f[:-4]) + 2:-4]}):<br><audio controls preload=none src='{fxn}'></audio>")
        print("preview:", fxn)
    open(page, "w", encoding="utf-8").write(h); sys.exit()

if sys.argv[1:2] == ["todo"]:                      # voices used by the jobs (starting zones + up to level 30) without a Ukrainian reference
    vs = set()
    for f in (os.path.join(HERE, "jobs_tts.jsonl"), os.path.join(TL, "..", "_archive", "tmp", "jobs_tts_all.jsonl")):
        if os.path.exists(f): vs |= {json.loads(l)["voice"] for l in open(f, encoding="utf-8")}
    print(",".join(sorted(v for v in vs if not os.path.exists(os.path.join(NEW, v + ".wav"))))); sys.exit()

if sys.argv[1:2] == ["summary"]:                   # final references of all voices vs the Russian ones
    vs = sorted(f[:-4] for f in os.listdir(NEW) if f.endswith(".wav"))
    tr = "".join(f"<tr><td>{v.replace('npc', '')}</td><td>"
                 + (f"<audio controls preload=none src='../refs_tight/{v}.wav'></audio>" if os.path.exists(os.path.join(OLD, v + ".wav")) else "")
                 + f"</td><td><audio controls preload=none src='{v}.wav'></audio></td><td>{html.escape(open(os.path.join(NEW, v + '.txt'), encoding='utf-8').read())}</td></tr>" for v in vs)
    open(os.path.join(NEW, "summary.html"), "w", encoding="utf-8").write(
        "<!doctype html><meta charset='utf-8'><style>body{font:14px system-ui;margin:16px;max-width:1200px}td{border:1px solid #ccc;padding:6px}audio{width:220px}</style>"
        f"<h3>Ukrainian NPC references in use ({len(vs)})</h3><p>Change one: python build_refs_uk.py pick &lt;voice&gt;=&lt;candidate&gt; (candidates: cand/all.html)</p>"
        f"<table><tr><th>voice</th><th>RU (old)</th><th>UK (now)</th><th>text</th></tr>{tr}</table>")
    print("Summary: code/refs_uk/summary.html"); sys.exit()

if sys.argv[1:2] == ["auto"]:                      # voices without an approved reference: take the cleanest candidate
    STATS = json.load(open(os.path.join(CAND, "stats.json"), encoding="utf-8"))
    for v in VOICES:
        if os.path.exists(os.path.join(NEW, v + ".wav")): continue
        c = [k for k in STATS if k.startswith(v + "__")]
        if not c: print("no candidates:", v); continue
        best = min(c, key=lambda k: (not k.endswith("_lively"), round(STATS[k]["cer"], 3), STATS[k]["cps"]))   # «lively» won for humanfemale
        for ext in (".wav", ".txt"):
            shutil.copyfile(os.path.join(CAND, best + ext), os.path.join(NEW, v + ext))
            if v.startswith("undead") and os.path.exists(os.path.join(CAND, best + "__fx" + ext)):
                shutil.copyfile(os.path.join(CAND, best + "__fx" + ext), os.path.join(NEW, v + "__fx" + ext))
        print(f"auto: {v} ← {best[len(v) + 2:]}")
    sys.exit()

if sys.argv[1:2] == ["pick"]:                      # approved: voice=speaker → refs_uk/<voice>.wav/.txt
    for a in sys.argv[2:]:
        v, s = a.split("=")
        for ext in (".wav", ".txt"):
            shutil.copyfile(os.path.join(CAND, f"{v}__{s}{ext}"), os.path.join(NEW, v + ext))
            if os.path.exists(os.path.join(CAND, f"{v}__{s}__fx{ext}")): shutil.copyfile(os.path.join(CAND, f"{v}__{s}__fx{ext}"), os.path.join(NEW, v + "__fx" + ext))
        print("reference:", v, "←", s)
    sys.exit()

def clean(t): return re.sub(r"\s+", " ", t.replace("́", "").replace("—", " ").strip(" -–—")).strip()
NARR = re.compile(r"\b(сказа|озва|говори|каже|відпові|відказ|одвіт|спита|вигукну|згукну|гукну|крикну|шепну|мовив|мовила|промови|пробурм)", re.I)
FEM = re.compile(r"\w+(лася|лась)\b", re.I)
def score(t, male=False):
    """Prefer short spoken lines: questions/exclamations, no narration («— сказав він»), few proper names;
    no feminine verb forms («помстилася») in male voices."""
    s = 0.0
    if male and FEM.search(t): s -= 3
    if t.rstrip().endswith(("?", "!")): s += 1.0
    if NARR.search(t): s -= 1.5
    s -= 0.4 * len(re.findall(r"(?<=\s)[А-ЯІЇЄҐ]\w+", t))          # capitalized words mid-sentence ≈ names
    return s
def trim(y):
    fr = int(0.02 * SR); n = len(y) // fr
    e = 20 * np.log10(np.sqrt((y[:n * fr].reshape(n, fr) ** 2).mean(1)) + 1e-9); loud = np.nonzero(e > e.max() - 38)[0]
    return y[max(0, loud[0] * fr - int(0.03 * SR)):(loud[-1] + 1) * fr + int(0.06 * SR)]

def norm(t): return re.sub(r"[^\w' ]+", " ", t.lower().replace("’", "'").replace("ʼ", "'")).split()
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

plan = [json.loads(l) for l in open(os.path.join(VC, "plan.jsonl"), encoding="utf-8")]
VARIANTS = os.environ.get("VARIANTS", "")          # e.g. "clear,lively,clear2" — several candidates per speaker
MAX_CLIP = float(os.environ.get("MAX_CLIP", 3.5))
PAGE = os.environ.get("PAGE", "listen.html")
CACHE = os.path.join(CAND, "asr_cache.json"); cache = json.load(open(CACHE, encoding="utf-8")) if os.path.exists(CACHE) else {}
def load_clip(r, p):
    """trimmed 24 kHz audio + Whisper check (cached): cer, cps (letters per second)"""
    y, sr = sf.read(p, dtype="float32")
    if y.ndim > 1: y = y.mean(1)
    if sr != SR: y = np.interp(np.arange(int(len(y) * SR / sr)) * sr / SR, np.arange(len(y)), y).astype(np.float32)
    t = clean(r["text"]); y = trim(y)
    if p not in cache: cache[p] = asr.generate(p, language="uk").text
    e = cer(norm(t), norm(cache[p])); cps = len(re.sub(r"\W", "", t)) / (len(y) / SR)
    return y, t, e, cps
def assemble(clips):
    global ASSEMBLED; ASSEMBLED = []
    parts, texts, total = [], [], 0.0
    for y, t, e, cps in clips:
        d = len(y) / SR
        if total + d > MAX_T: continue
        parts += [y / (np.sqrt(np.mean(y ** 2)) + 1e-9) * 10 ** (-20 / 20), np.zeros(int(GAP * SR), np.float32)]
        texts.append(t); total += d + GAP; ASSEMBLED.append((e, cps))
        if total >= MIN_T and len(texts) >= 4: break
    return parts, texts, total
SP = os.path.join(CAND, "stats.json"); STATS = json.load(open(SP, encoding="utf-8")) if os.path.exists(SP) else {}
rows = []
for v in VOICES:
    by_spk = {}
    for r in plan:
        if r["voice"] != v: continue
        p = os.path.join(VC, "wav", os.path.basename(r["wav"]))
        if os.path.exists(p) and 1.2 <= sf.info(p).duration <= MAX_CLIP: by_spk.setdefault(r["id"].rsplit("_", 1)[0], []).append((r, p))
    old_t = open(os.path.join(OLD, v + ".txt"), encoding="utf-8").read().strip()
    rows.append(f"<tr class=v><td><b>{v.replace('npc', '')}</b></td><td>RU now<br><audio controls preload=none src='../../refs_tight/{v}.wav'></audio></td>"
                f"<td>{html.escape(old_t)}</td></tr>")
    male = "female" not in v
    for spk, items in sorted(by_spk.items()):
        clips = [c for c in (load_clip(r, p) for r, p in items) if not NARR.search(c[1])]   # no «— сказав він» in a reference
        clean_ok = [c for c in clips if c[2] <= 0.06]                                   # VC did not smear the speech
        sets = {}
        if not VARIANTS:
            sets[""] = sorted(clean_ok, key=lambda c: -score(c[1], male))
        for tag in filter(None, VARIANTS.split(",")):
            if tag == "clear":                          # flawless recognition, slowest (most articulated) speech first
                sets["_clear"] = sorted([c for c in clips if c[2] == 0], key=lambda c: (c[3], -score(c[1], male)))
            elif tag == "clear2":                       # same, but without the phrases of "clear"
                used = set(assemble(sets.get("_clear", []))[1])
                sets["_clear2"] = sorted([c for c in clips if c[2] == 0 and c[1] not in used], key=lambda c: (c[3], -score(c[1], male)))
            elif tag == "lively":                       # questions/exclamations, but not fast
                sets["_lively"] = sorted([c for c in clean_ok if c[3] <= 14], key=lambda c: (-score(c[1], male), c[3]))
        for tag, ordered in sets.items():
            parts, texts, total = assemble(ordered)
            if len(texts) < 3: print(f"{v} / {spk}{tag}: too few clean short phrases ({len(texts)}) — skipped"); continue
            name = f"{v}__{spk}{tag}"
            sf.write(os.path.join(CAND, name + ".wav"), np.clip(np.concatenate(parts[:-1]), -0.97, 0.97), SR)
            open(os.path.join(CAND, name + ".txt"), "w", encoding="utf-8").write(" ".join(texts) + "\n")
            rows.append(f"<tr><td>{spk}{tag}</td><td>{total - GAP:.1f} s<br><audio controls preload=none src='{name}.wav'></audio></td><td>{html.escape(' '.join(texts))}</td></tr>")
            STATS[name] = {"cer": float(np.mean([a for a, _ in ASSEMBLED])), "cps": float(np.mean([b for _, b in ASSEMBLED])), "n": len(texts)}
            print(f"{name}: {total - GAP:.1f} s, {len(texts)} phrases", flush=True)
json.dump(cache, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False)
json.dump(STATS, open(SP, "w", encoding="utf-8"), indent=1)
open(os.path.join(CAND, PAGE), "w", encoding="utf-8").write(
    "<!doctype html><meta charset='utf-8'><style>body{font:14px system-ui;margin:16px;max-width:1100px}td{border:1px solid #ccc;padding:6px;vertical-align:top}"
    "audio{width:240px}tr.v td{background:#eef}</style><h3>Ukrainian NPC references — candidates (one source speaker each)</h3>"
    "<p>Compare with the current Russian reference: timbre should match, speech should be clean. Pick one speaker per voice.</p>"
    f"<table>{''.join(rows)}</table>")
import subprocess; subprocess.run([sys.executable, os.path.abspath(__file__), "fx"])
print(f"Listen: code/refs_uk/cand/{PAGE}")
