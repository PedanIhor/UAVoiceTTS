"""Prepare text for voiceover (omnitrain env): numbers → words, stress marks (ukrainian_word_stress),
split into sentence chunks (≤ MAXC characters) — the model was trained on lines up to ~24 s. → jobs_tts.jsonl"""
import os, re, sys, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(os.path.dirname(HERE), "models"))
sys.path.insert(0, HERE)
from stress_fix import mark
import hashlib
_dp = os.path.join(HERE, "stress_dict.txt")
MODE = os.environ.get("STRESS", "dict") + ":" + (hashlib.md5(open(_dp, "rb").read()).hexdigest()[:8] if os.path.exists(_dp) else "")  # dictionary changed — re-mark   # dict — marks only for words from stress_dict.txt (Ihor's decision 02.10)
MAXC = int(os.environ.get("MAXC", 260))
try:
    from num2words import num2words
    def nums(t): return re.sub(r"\d+", lambda m: num2words(int(m.group()), lang="uk"), t)
except ImportError:
    print("! num2words missing (pip install num2words) — numbers will stay as digits"); nums = lambda t: t
def chunks(t):
    sents = [s for s in re.split(r"(?<=[.!?…])\s+", t) if s.strip()]; out, cur = [], ""
    for s in sents:
        if cur and len(cur) + 1 + len(s) > MAXC: out.append(cur); cur = s
        else: cur = (cur + " " + s).strip()
    if cur: out.append(cur)
    return out
src = os.path.join(HERE, "jobs.jsonl"); dst = os.path.join(HERE, "jobs_tts.jsonl")
done = {json.loads(l)["id"]: json.loads(l) for l in open(dst, encoding="utf-8")} if os.path.exists(dst) else {}
jobs = [json.loads(l) for l in open(src, encoding="utf-8")]
with open(dst, "w", encoding="utf-8") as f:
    for i, j in enumerate(jobs):
        if j["id"] in done and done[j["id"]]["text"] == j["text"] and done[j["id"]].get("stress") == MODE and not os.environ.get("RESTRESS"): j = done[j["id"]]
        else:
            parts = chunks(j["text"]); j["chunks"] = [{"show": p, "tts": mark(nums(p), MODE.split(":")[0])} for p in parts]; j["stress"] = MODE
        f.write(json.dumps(j, ensure_ascii=False) + "\n")
        if (i + 1) % 50 == 0: print(f"{i+1}/{len(jobs)}", flush=True)
print(f"done: {len(jobs)} jobs, chunks {sum(len(json.loads(l)['chunks']) for l in open(dst, encoding='utf-8'))}")
