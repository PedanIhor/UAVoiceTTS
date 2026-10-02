"""Shared reject filter based on qa_data.py results. Used by VC and Higgs data prep.
passed(ids) → set of ids that passed the filter. Standalone: python qa_filter.py — summary."""
import os, json
SRC = os.path.expanduser(os.environ.get("SRC", "~/omni_ft/r3"))
MAXCER = float(os.environ.get("QA_MAXCER", 0.15)); MAXCER_KAT = float(os.environ.get("QA_MAXCER_KAT", 0.05))
def ok(x):
    lim = MAXCER_KAT if x["id"].startswith("kateryna_") else MAXCER      # kateryna has 13% rejects — be stricter with her remaining phrases
    return x["cer"] <= lim and 7 <= x["cps"] <= 20 and x["rms_db"] > -45
def load():
    return {x["id"]: x for x in (json.loads(l) for l in open(os.path.join(SRC, "qa.jsonl"), encoding="utf-8"))}
def passed():
    return {k for k, x in load().items() if ok(x)}
if __name__ == "__main__":
    q = load(); p = passed()
    for spk in ("mykyta", "oleksa", "tetiana", "lada", "kateryna"):
        s = [k for k in q if k.startswith(spk + "_")]
        print(f"{spk:9s} kept {sum(k in p for k in s):4d} of {len(s)}")
    print(f"total kept {len(p)} of {len(q)}")
