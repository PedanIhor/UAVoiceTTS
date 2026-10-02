"""Prepares a pilot set from Yehor/opentts-uk (5 speakers = 5 dataset configs): HOURS hours split equally,
20 phrases from each — for dev. Text: with probability STRESSED_RATIO — with stress marks (text_stressed), otherwise plain.
The dataset has metadata (voices/<speaker>) separately, audio — in archives data/<speaker>.zip: download and unpack into ~/omni_ft/raw/.
Everything goes into ~/omni_ft/"""
import os, json, random, zipfile
from datasets import load_dataset, Audio
from huggingface_hub import hf_hub_download
HOURS = float(os.environ.get("HOURS", 5)); STRESSED_RATIO = float(os.environ.get("STRESSED_RATIO", 0.7))
VOICES = ["mykyta", "tetiana", "lada", "kateryna", "oleksa"]
FT = os.path.expanduser(os.environ.get("FT", "~/omni_ft"))
ROOT = os.path.join(FT, "data"); os.makedirs(ROOT, exist_ok=True)
RAW = os.path.expanduser("~/omni_ft/raw")                 # raw archives shared by all runs
# CLEAN=1: trim edge silence (threshold TOP_DB dB below peak). MAXGAP>0 — also compress pauses inside the phrase to MAXGAP s;
# MAXGAP<=0 (default) — leave pauses inside the phrase alone. EDGE — how much silence to keep on each edge, s.
CLEAN = os.environ.get("CLEAN", "0") == "1"; MAXGAP = float(os.environ.get("MAXGAP", 0))
TOP_DB = float(os.environ.get("TOP_DB", 35)); EDGE = float(os.environ.get("EDGE", 0.3))
MAXEDGE = float(os.environ.get("MAXEDGE", 0.8))   # drop phrases that after cleanup have > MAXEDGE s of near-silence (below -40 dB) at an edge
CLEAN_DIR = os.path.join(FT, f"clean_db{TOP_DB:g}_gap{MAXGAP:g}_edge{EDGE:g}"); os.makedirs(CLEAN_DIR, exist_ok=True)

def clean(path, dst):
    import numpy as np, soundfile as sf, librosa
    if os.path.exists(dst): return True
    try:
        y, sr = sf.read(path, dtype="float32", always_2d=True); y = y.mean(axis=1)
    except Exception:                        # libsndfile can't read some .ogg (like OmniVoice, use librosa/ffmpeg)
        try:
            y, sr = librosa.load(path, sr=None, mono=True)
        except Exception as e:
            print(f"  skip {os.path.basename(path)}: {e}"); return False
    iv = librosa.effects.split(y, top_db=TOP_DB, frame_length=1024, hop_length=256)
    if not len(iv): return False
    if MAXGAP > 0:                           # compress inner pauses
        gap = int(MAXGAP * sr); parts = []
        for j, (a, b) in enumerate(iv):
            if j: parts.append(np.zeros(min(a - iv[j - 1][1], gap), np.float32))
            parts.append(y[a:b])
    else:                                    # edges only: from start of first speech chunk to end of last
        parts = [y[iv[0][0]:iv[-1][1]]]
    pad = np.zeros(int(EDGE * sr), np.float32)
    sf.write(dst, np.concatenate([pad] + parts + [pad]), sr); return True

def edge_sil(path, thr_db=-40):
    import numpy as np, soundfile as sf
    y, sr = sf.read(path, dtype="float32")
    if y.ndim > 1: y = y.mean(1)
    fr = int(0.01 * sr); n = len(y) // fr
    if not n: return 0, 0
    e = 20 * np.log10(np.sqrt((y[:n*fr].reshape(n, fr) ** 2).mean(1)) + 1e-9)
    loud = np.nonzero(e > e.max() + thr_db)[0]
    return (loud[0] * 0.01, (n - 1 - loud[-1]) * 0.01) if len(loud) else (0, 0)
dropped_edge = 0

def audio_index(v):
    """Download and unpack the speaker archive; return {file name: full path}."""
    d = os.path.join(RAW, v)
    if not os.path.isdir(d):
        z = hf_hub_download("Yehor/opentts-uk", f"data/{v}.zip", repo_type="dataset")
        print(f"{v}: unpacking {os.path.getsize(z)/1e6:.0f} MB…"); zipfile.ZipFile(z).extractall(d)
    idx = {}
    for root, _, files in os.walk(d):
        for f in files:
            if f.lower().endswith((".ogg", ".wav", ".flac", ".mp3")): idx[f] = os.path.join(root, f)
    return idx
budget = HOURS * 3600 / len(VOICES)
random.seed(42)
train, dev, stats = [], [], {}
for v in VOICES:
    ds = load_dataset("Yehor/opentts-uk", v)
    split = "train" if "train" in ds else list(ds.keys())[0]
    ds = ds[split]
    if isinstance(ds.features.get("audio"), Audio):      # don't decode audio via datasets (requires torchcodec)
        ds = ds.cast_column("audio", Audio(decode=False))
    files = audio_index(v)
    if v == VOICES[0]: print("columns:", ds.column_names)
    idx = list(range(len(ds))); random.shuffle(idx)
    got, ndev = 0.0, 0
    for i in idx:
        r = ds[i]
        a = r["audio"]
        fname = os.path.basename(a["path"] if isinstance(a, dict) else str(a))
        path = files.get(fname)
        if not path: continue
        dur = float(r.get("duration") or 5.0)
        to_dev = ndev < 20
        if not to_dev and got >= budget: break
        if CLEAN:
            dst = os.path.join(CLEAN_DIR, f"{v}_{i}.wav")
            if not clean(path, dst): continue
            if MAXEDGE > 0 and max(edge_sil(dst)) > MAXEDGE:
                dropped_edge += 1; continue
            path = dst
        stressed = r.get("text_stressed")
        text = stressed if stressed and random.random() < STRESSED_RATIO else r["text"]
        row = {"id": f"{v}_{i}", "audio_path": path, "text": text.strip(), "language_id": "uk"}
        if to_dev: dev.append(row); ndev += 1
        else: train.append(row); got += dur
    stats[v] = round(got / 3600, 2)
    if not got: print(f"  ! files not matched: example audio={ds[0]['audio']!r}, archive has {len(files)} files, e.g. {next(iter(files), None)}")
    print(f"{v}: {stats[v]} h in train, {ndev} in dev")
random.shuffle(train)
for n, rows in (("train", train), ("dev", dev)):
    with open(os.path.join(ROOT, n + ".jsonl"), "w", encoding="utf-8") as f:
        for x in rows: f.write(json.dumps(x, ensure_ascii=False) + "\n")
print(f"cleanup: {CLEAN}, threshold {TOP_DB:g} dB, inner pauses: {'up to %g s' % MAXGAP if MAXGAP > 0 else 'untouched'}, edges {EDGE:g} s")
print(f"dropped due to long silence/noise at edges (> {MAXEDGE:g} s): {dropped_edge}")
print(f"total train: {len(train)} phrases, ~{sum(stats.values()):.1f} h; dev: {len(dev)}")
print("example:", next((x["text"] for x in train if "\u0301" in x["text"]), "—"))
