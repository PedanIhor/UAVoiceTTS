"""Summary of prepared data: python data_stats.py [~/omni_ft/r2]"""
import sys, os, json, collections, statistics as st
import numpy as np, soundfile as sf
FT = os.path.expanduser(sys.argv[1] if len(sys.argv) > 1 else "~/omni_ft/r2")
def edge_sil(y, sr, thr_db=-40):
    fr = int(0.01 * sr); n = len(y) // fr
    if not n: return 0, 0
    e = 20 * np.log10(np.sqrt((y[:n*fr].reshape(n, fr) ** 2).mean(1)) + 1e-9)
    loud = np.nonzero(e > e.max() + thr_db)[0]
    return (loud[0] * 0.01, (n - 1 - loud[-1]) * 0.01) if len(loud) else (0, 0)
for part in ("train", "dev"):
    rows = [json.loads(l) for l in open(f"{FT}/data/{part}.jsonl", encoding="utf-8")]
    by = collections.defaultdict(list); lead, tail, stressed = [], [], 0
    for r in rows:
        y, sr = sf.read(r["audio_path"], dtype="float32")
        if y.ndim > 1: y = y.mean(1)
        by[r["id"].rsplit("_", 1)[0]].append(len(y) / sr)
        a, b = edge_sil(y, sr); lead.append(a); tail.append(b)
        stressed += "́" in r["text"]
    alld = [d for v in by.values() for d in v]
    print(f"\n== {part}: {len(rows)} phrases, {sum(alld)/3600:.2f} h, with stress marks {stressed} ({100*stressed/len(rows):.0f}%)")
    print(f"   phrase length: min {min(alld):.1f} s, median {st.median(alld):.1f} s, max {max(alld):.1f} s")
    for v, d in sorted(by.items()):
        print(f"   {v:9s} {len(d):5d} phrases  {sum(d)/3600:.2f} h  median {st.median(d):.1f} s")
    print(f"   leading silence: median {st.median(lead):.2f} s, max {max(lead):.2f} s")
    print(f"   trailing silence: median {st.median(tail):.2f} s, max {max(tail):.2f} s")
    print(f"   phrases with edge > 0.8 s: at start {sum(x > 0.8 for x in lead)}, at end {sum(x > 0.8 for x in tail)}")
