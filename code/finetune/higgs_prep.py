"""Encodes r3 audio with the Higgs codec (on GPU) → ~/omni_ft/higgs/codes/<id>.npy, lists train/dev.jsonl."""
import os, sys, json, time
import numpy as np
import mlx.core as mx
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from higgs_common import load_model, FT, SRC
from mlx_audio.utils import load_audio
os.makedirs(os.path.join(FT, "codes"), exist_ok=True)
model = load_model(); codec = model._codec; sr = model.sample_rate
print(f"model: {type(model).__module__}, rate {sr} Hz, codebooks {model.config.audio_num_codebooks}")
for part in ("train", "dev"):
    rows = [json.loads(l) for l in open(os.path.join(SRC, "data", part + ".jsonl"), encoding="utf-8")]
    out, t0 = [], time.time()
    for i, r in enumerate(rows):
        dst = os.path.join(FT, "codes", r["id"] + ".npy")
        if not os.path.exists(dst):
            try:
                w = np.array(load_audio(r["audio_path"], sample_rate=sr), dtype=np.float32).reshape(-1)
                codes = codec.encode(mx.array(w).reshape(1, -1, 1))[0].astype(mx.int32)
                np.save(dst, np.array(codes))
            except Exception as e:
                print(f"  skip {r['id']}: {e}"); continue
        T = int(np.load(dst, mmap_mode="r").shape[0])
        out.append({"id": r["id"], "spk": r["id"].rsplit("_", 1)[0], "text": r["text"], "codes": dst, "T": T})
        if (i + 1) % 200 == 0:
            print(f"{part}: {i+1}/{len(rows)}  {(time.time()-t0)/(i+1):.2f} s/phrase", flush=True)
    with open(os.path.join(FT, part + ".jsonl"), "w", encoding="utf-8") as f:
        for x in out: f.write(json.dumps(x, ensure_ascii=False) + "\n")
    fr = [x["T"] for x in out]
    print(f"{part}: {len(out)} phrases, frames: min {min(fr)}, median {int(np.median(fr))}, max {max(fr)} "
          f"(≈{max(fr)/25:.1f} s at 25 frames/s)")
