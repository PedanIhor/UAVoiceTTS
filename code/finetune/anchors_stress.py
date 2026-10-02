"""Stress marking of anchor texts (ukrainian_word_stress) → ~/omni_ft/anchors/anchors_acute.json {id: text with marks}.
Needed so stress marks also appear with the base model's "clean" speech, not only with VC phrases. Env omnitrain."""
import os, sys, json
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(HERE, "models"))
from stress_common import stressify
A = os.path.expanduser("~/omni_ft/anchors"); out = os.path.join(A, "anchors_acute.json")
res = json.load(open(out, encoding="utf-8")) if os.path.exists(out) else {}
rows = [json.loads(l) for l in open(os.path.join(A, "anchors.jsonl"), encoding="utf-8")]
for i, r in enumerate(rows):
    if r["id"] not in res: res[r["id"]] = stressify(r["text"])
    if (i + 1) % 100 == 0: json.dump(res, open(out, "w", encoding="utf-8"), ensure_ascii=False); print(i + 1, "/", len(rows), flush=True)
json.dump(res, open(out, "w", encoding="utf-8"), ensure_ascii=False)
print("example:", res[rows[0]["id"]])
