"""Voice the jobs (mlxtts env): Higgs + LoRA h3, chunk by chunk; each chunk gets up to TRIES attempts with auto-check
(pace, long pauses, Whisper CER); the first passing one is taken, otherwise the best. Undead get the "crypt" effect.
Voices are cloned from Ukrainian references (code/refs_uk); a changed reference re-voices its lines.
Loudness is normalized, output is OGG (Vorbis). → out/sounds/<id>.ogg, out/meta.jsonl (duration, subtitles, checks).
Can be interrupted and resumed."""
import os, re, sys, json, time, subprocess, shutil
import numpy as np, soundfile as sf
HERE = os.path.dirname(os.path.abspath(__file__)); TL = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(TL, "finetune"))
from higgs_common import load_model, load_adapter
from voice_fx import apply as fx
JOBS = os.path.join(HERE, os.environ.get("JOBS", "jobs_tts.jsonl"))   # OUT_DIR / JOBS — for side experiments (compare_voices.py)
AD = os.path.expanduser(os.environ.get("ADAPTER", "~/omni_ft/higgs/exp/h3/step1000.safetensors"))
TRIES = int(os.environ.get("TRIES", 4)); TEMP = float(os.environ.get("TEMP", 0.7)); GAP = 0.3
OUT = os.path.join(HERE, os.environ.get("OUT_DIR", "out")); SND = os.path.join(OUT, "sounds"); os.makedirs(SND, exist_ok=True); META = os.path.join(OUT, "meta.jsonl")
# Ukrainian NPC references (build_refs_uk.py) — Russian ones (refs_tight) gave a Russian accent, esp. at line starts.
# Undead: reference with the crypt effect baked in (like Blizzard's Russian undead clips); UNDEAD_REF=dry to switch off.
REFS = os.path.join(TL, os.environ.get("REFS_DIR", "refs_uk")); UNDEAD_REF = os.environ.get("UNDEAD_REF", "fx")
import hashlib
def ref_name(voice):
    n = voice + "__fx" if voice.startswith("undead") and UNDEAD_REF == "fx" and os.path.exists(os.path.join(REFS, voice + "__fx.wav")) else voice
    if not os.path.exists(os.path.join(REFS, n + ".wav")): sys.exit(f"no reference {REFS}/{n}.wav — run refs_all.sh")
    return n
def ref_id(voice):
    """identity of the reference used for a voice: changing a reference re-voices its lines automatically"""
    n = ref_name(voice); h = hashlib.md5()
    for ext in (".wav", ".txt"): h.update(open(os.path.join(REFS, n + ext), "rb").read())
    return f"{os.path.basename(REFS)}/{n}:{h.hexdigest()[:8]}"
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
def trim(y, sr):
    fr = int(0.02 * sr); n = len(y) // fr
    e = 20 * np.log10(np.sqrt((y[:n * fr].reshape(n, fr) ** 2).mean(1)) + 1e-9); loud = np.nonzero(e > e.max() - 40)[0]
    if not len(loud): return y, 0.0
    gaps = [(b - a - 1) * 0.02 for a, b in zip(loud[:-1], loud[1:])]
    return y[max(0, loud[0] * fr - int(0.05 * sr)):(loud[-1] + 1) * fr + int(0.1 * sr)], max(gaps, default=0.0)
model = load_model(); print("LoRA:", load_adapter(model, AD), flush=True); SR = model.sample_rate
from mlx_audio.stt import load as load_stt
asr = load_stt("mlx-community/whisper-large-v3-turbo-asr-fp16")
FFMPEG = shutil.which("ffmpeg")
def save_ogg(y, path):
    try:
        sf.write(path, y, SR, format="OGG", subtype="VORBIS"); return path
    except Exception:
        if FFMPEG:
            tmp = path[:-4] + ".wav"; sf.write(tmp, y, SR)
            subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", tmp, "-c:a", "libvorbis", "-q:a", "3", "-ac", "1", path], check=True); os.remove(tmp); return path
        p = path[:-4] + ".wav"; sf.write(p, y, SR); return p
def one_chunk(c, voice, tmp):
    best = None; show = c["show"]
    for k in range(TRIES):
        gen = model.generate(text=c["tts"], ref_audio=os.path.join(REFS, ref_name(voice) + ".wav"),
                             ref_text=open(os.path.join(REFS, ref_name(voice) + ".txt"), encoding="utf-8").read().strip(),
                             temperature=TEMP, max_new_tokens=int(len(show) * 3.5) + 200, seed=1000 + k)
        y = np.concatenate([np.array(r.audio, dtype=np.float32).reshape(-1) for r in gen]); y, maxgap = trim(y, SR)
        dur = len(y) / SR; cps = len(show) / max(dur, 0.3)
        sf.write(tmp, y, SR); e = cer(norm(c["tts"]), norm(asr.generate(tmp, language="uk").text))   # numbers as words, no stress marks
        score = e + max(0, maxgap - 0.6) + max(0, 9 - cps) * 0.1 + max(0, cps - 22) * 0.1
        q = {"try": k + 1, "dur": round(dur, 2), "cps": round(cps, 1), "maxgap": round(maxgap, 2), "cer": round(e, 3)}
        if best is None or score < best[0]: best = (score, y, q)
        if e <= 0.12 and maxgap <= 0.6 and 9 <= cps <= 22: break
    return best[1], best[2]
# done = present in meta and voiced from the same text (marking/dictionary changed — re-voice automatically)
TTS = {j["id"]: " | ".join(c["tts"] for c in j["chunks"]) for j in map(json.loads, open(JOBS, encoding="utf-8"))}
REF = {j["id"]: ref_id(j["voice"]) for j in map(json.loads, open(JOBS, encoding="utf-8"))}
if os.path.exists(META):
    rows = [json.loads(l) for l in open(META, encoding="utf-8")]
    stale = {r["id"] for r in rows if r.get("tts") != TTS.get(r["id"]) or r.get("ref") != REF.get(r["id"])}   # text or reference changed
    gone = {r["id"] for r in rows if not os.path.exists(os.path.join(SND, r["file"]))}   # file deleted by hand — re-voice
    if gone: print(f"files missing (deleted) — re-voicing {len(gone)}: {', '.join(sorted(gone))}", flush=True)
    stale |= gone
    if stale:
        open(META, "w", encoding="utf-8").writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in rows if r["id"] not in stale)
        print(f"total to re-voice: {len(stale)}", flush=True)
done = {json.loads(l)["id"] for l in open(META, encoding="utf-8")} if os.path.exists(META) else set()
QUEUE = os.path.join(HERE, "redo_queue.txt" if OUT == os.path.join(HERE, "out") else "_no_queue_for_experiments")                         # queue from reports.py (reports without a new word)
REDO = [x for x in os.environ.get("REDO", "").split(",") if x] + (open(QUEUE, encoding="utf-8").read().split() if os.path.exists(QUEUE) else [])       # REDO=id1,id2 | word:геро́ю | all — re-voice
if REDO:
    allj = list(map(json.loads, open(JOBS, encoding="utf-8")))
    redo = {j["id"] for j in allj if "all" in REDO or j["id"] in REDO or any(r.startswith("word:") and r[5:] in "".join(c["tts"] for c in j["chunks"]) for r in REDO)}
    keep = [l for l in open(META, encoding="utf-8") if json.loads(l)["id"] not in redo] if os.path.exists(META) else []
    open(META, "w", encoding="utf-8").writelines(keep); done -= redo; print(f"to re-voice: {len(redo)}", flush=True)
    if os.path.exists(QUEUE): os.replace(QUEUE, QUEUE + ".prev")   # already removed from meta — will be voiced even if interrupted
jobs = [j for j in map(json.loads, open(JOBS, encoding="utf-8")) if j["id"] not in done]
print(f"to voice: {len(jobs)}", flush=True); t0 = time.time(); tmp = os.path.join(OUT, "_tmp.wav")
with open(META, "a", encoding="utf-8") as mf:
    for i, j in enumerate(jobs):
        parts, cues, qs, pos = [], [], [], 0.0
        for c in j["chunks"]:
            y, q = one_chunk(c, j["voice"], tmp)
            cues.append([round(pos, 2), c["show"]]); qs.append(q); parts.append(y); pos += len(y) / SR + GAP
            parts.append(np.zeros(int(GAP * SR), np.float32))
        y = fx(j["voice"], np.concatenate(parts[:-1]), SR)
        y = y * (10 ** (-18 / 20) / (np.sqrt(np.mean(y ** 2)) + 1e-9)); y = np.clip(y, -0.97, 0.97).astype(np.float32)
        path = save_ogg(y, os.path.join(SND, j["id"] + ".ogg"))
        bad = any(q["cer"] > 0.2 or q["maxgap"] > 0.8 for q in qs)
        mf.write(json.dumps({"id": j["id"], "quest": j["quest"], "part": j["part"], "sex": j["sex"], "voice": j["voice"], "file": os.path.basename(path),
                             "dur": round(len(y) / SR, 2), "cues": cues, "qa": qs, "flag": bad, "tts": TTS[j["id"]], "ref": REF[j["id"]]}, ensure_ascii=False) + "\n"); mf.flush()
        el = time.time() - t0
        print(f"{i+1}/{len(jobs)} {j['id']:18s} {len(y)/SR:5.1f} s  attempts {sum(q['try'] for q in qs)}{'  ⚠' if bad else ''}  ~{el/(i+1)*(len(jobs)-i-1)/60:.0f} min", flush=True)
