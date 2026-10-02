"""Where exactly the pauses are: Whisper with word timestamps for each file, pauses ≥ 0.3 s between words.
An "unjustified" pause = no punctuation mark before it. Report: out_models/pauses_report.txt
python analyze_pauses.py [folders relative to tts_local, default: all out_all*/ and out_models/*/]"""
import os, sys, glob, re
sys.path.insert(0, os.path.dirname(__file__))
from common import HERE, choose
from mlx_audio.stt import load
dirs = sys.argv[1:] or sorted(d for d in glob.glob(os.path.join(HERE, "out_all*")) + glob.glob(os.path.join(HERE, "out_models", "*"))
                               if os.path.isdir(d) and "_old" not in d)
dirs = [d if os.path.isabs(d) else os.path.join(HERE, d) for d in dirs]
voices = [s[0] for s in choose([])]
m = load("mlx-community/whisper-large-v3-turbo-asr-fp16")
lines, summary = [], []
for d in dirs:
    tot_bad = tot_all = n = 0
    for v in voices:
        p = os.path.join(d, v + ".wav")
        if not os.path.exists(p): continue
        r = m.generate(p, language="uk", word_timestamps=True)
        words = [w for s in r.segments for w in s.get("words", [])]
        marked, bad, allp = [], 0, 0
        for i, w in enumerate(words):
            marked.append(w["word"].strip())
            if i + 1 < len(words):
                gap = words[i + 1]["start"] - w["end"]
                if gap >= 0.3:
                    allp += 1
                    ok = re.search(r"[.,!?;:…—–-]$", w["word"].strip())
                    if not ok: bad += 1
                    marked.append(f"⟦{gap:.1f}{'' if ok else ' !!'}⟧")
        n += 1; tot_bad += bad; tot_all += allp
        lines.append(f"[{os.path.relpath(d, HERE)}] {v}: pauses {allp}, unjustified {bad}\n   " + " ".join(marked))
    if n: summary.append(f"{os.path.relpath(d, HERE):32s} files {n:2d}  pauses {tot_all:3d}  unjustified {tot_bad:3d}  (avg {tot_bad/n:.1f} per file)")
rep = "TOTAL (!! = pause where there is no punctuation mark)\n" + "\n".join(summary) + "\n\n" + "\n".join(lines)
open(os.path.join(HERE, "out_models", "pauses_report.txt"), "w", encoding="utf-8").write(rep)
print("\n".join(summary)); print("Details: out_models/pauses_report.txt")
