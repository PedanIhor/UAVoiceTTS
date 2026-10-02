"""VC plan for h3: all voices via Chatterbox (seed_f0 has an audible accent). Existing Chatterbox files from ~/omni_ft/vc
are reused, the rest will be regenerated in ~/omni_ft/vc3/wav. → ~/omni_ft/vc3/plan.jsonl"""
import os, json
OLD = os.path.expanduser("~/omni_ft/vc/plan.jsonl"); NEW = os.path.expanduser("~/omni_ft/vc3"); os.makedirs(os.path.join(NEW, "wav"), exist_ok=True)
n_re = n_new = 0
with open(os.path.join(NEW, "plan.jsonl"), "w", encoding="utf-8") as f:
    for j in map(json.loads, open(OLD, encoding="utf-8")):
        if j["model"] == "chatterbox" and os.path.exists(j["wav"]): n_re += 1
        else: j["model"] = "chatterbox"; j["wav"] = os.path.join(NEW, "wav", os.path.basename(j["wav"])); n_new += 1
        f.write(json.dumps(j, ensure_ascii=False) + "\n")
print(f"h3 plan: reusing {n_re} existing Chatterbox clips, {n_new} to regenerate")
