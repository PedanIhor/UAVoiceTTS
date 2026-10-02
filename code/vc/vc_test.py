"""Voice conversion test: opentts clips (with correct stress) → NPC voices.
python vc_test.py seed|seed_f0|chatterbox   → out_vc/<model>/<voice>__<id>.wav"""
import os, sys, json, time, random
import numpy as np, soundfile as sf, librosa
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))          # tts_local
OUT = os.path.join(HERE, "out_vc"); REFS = os.path.join(HERE, "refs_all")
SRC = os.path.expanduser("~/omni_ft/r3/data/train.jsonl")
VOICES = {"male": ["humanmalestandardnpc", "undeadmaledarknpc", "goblinmalezanynpc"],
          "female": ["taurenfemalestandardnpc", "nightelffemalepriestessnpc", "undeadfemalestandardnpc"]}
SEX = {"mykyta": "male", "oleksa": "male", "tetiana": "female", "lada": "female", "kateryna": "female"}
PER = {"mykyta": 3, "oleksa": 3, "tetiana": 2, "lada": 2, "kateryna": 2}

def sources():
    """12 clips with stress marks, 3–8 s, fixed selection; source copies go to out_vc/src."""
    rows = [json.loads(l) for l in open(SRC, encoding="utf-8")]
    rng = random.Random(3); rng.shuffle(rows); got = []
    for spk, n in PER.items():
        c = [r for r in rows if r["id"].startswith(spk + "_") and "́" in r["text"]
             and 3 <= sf.info(r["audio_path"]).duration <= 8][:n]
        got += c
    d = os.path.join(OUT, "src"); os.makedirs(d, exist_ok=True)
    for r in got:
        dst = os.path.join(d, r["id"] + ".wav")
        if not os.path.exists(dst):
            y, sr = sf.read(r["audio_path"]); sf.write(dst, y, sr)
            open(dst[:-4] + ".txt", "w", encoding="utf-8").write(r["text"])
    return got

if __name__ == "__main__":
    kind = sys.argv[1]; d = os.path.join(OUT, kind); os.makedirs(d, exist_ok=True)
    jobs = [(r, v) for r in sources() for v in VOICES[SEX[r["id"].rsplit("_", 1)[0]]]
            if not os.path.exists(os.path.join(d, f"{v}__{r['id']}.wav"))]
    print(f"[{kind}] to do: {len(jobs)}")
    if not jobs: sys.exit()
    if kind.startswith("seed"):
        os.chdir(os.path.expanduser("~/omni_ft/tools/seed-vc")); sys.path.insert(0, os.getcwd())
        import torch
        _from_numpy = torch.from_numpy               # MPS has no float64, but Seed-VC returns F0 as float64 — cast to float32
        torch.from_numpy = lambda a: _from_numpy(a.astype(np.float32) if getattr(a, "dtype", None) == np.float64 else a)
        from seed_vc_wrapper import SeedVCWrapper
        vc = SeedVCWrapper(); f0 = kind == "seed_f0"
        def conv(src, ref):
            g = vc.convert_voice(src, ref, diffusion_steps=30, length_adjust=1.0, inference_cfg_rate=0.7,
                                 f0_condition=f0, auto_f0_adjust=True, pitch_shift=0, stream_output=False)
            out = None
            try:
                while True:
                    x = next(g); out = x[1] if isinstance(x, tuple) else x
            except StopIteration as e:
                if e.value is not None: out = e.value
            return np.asarray(out, dtype=np.float32).reshape(-1), (44100 if f0 else 22050)
    else:
        import torch
        from chatterbox.vc import ChatterboxVC
        vc = ChatterboxVC.from_pretrained("mps" if torch.backends.mps.is_available() else "cpu")
        vc.watermarker.apply_watermark = lambda wav, sample_rate: wav        # no watermark: this is training data
        def conv(src, ref):
            return vc.generate(src, target_voice_path=ref).squeeze(0).numpy(), vc.sr
    for r, v in jobs:
        t0 = time.time()
        y, sr = conv(os.path.join(OUT, "src", r["id"] + ".wav"), os.path.join(REFS, v + ".wav"))
        if sr != 24000: y = librosa.resample(y, orig_sr=sr, target_sr=24000)
        sf.write(os.path.join(d, f"{v}__{r['id']}.wav"), y, 24000)
        print(f"[{kind}] {v:28s} {r['id']:14s} {len(y)/24000:4.1f} s in {time.time()-t0:4.1f} s", flush=True)
