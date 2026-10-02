"""Compares checkpoint weights with base OmniVoice: did the fine-tuning actually get saved.
python check_ckpt.py ~/omni_ft/exp/pilot/checkpoint-200"""
import sys, os, glob
from safetensors import safe_open
from huggingface_hub import snapshot_download
ck = os.path.join(os.path.expanduser(sys.argv[1]), "model.safetensors")
base_dir = snapshot_download("k2-fsa/OmniVoice", allow_patterns=["*.safetensors", "*.json"])
base_files = [f for f in glob.glob(os.path.join(base_dir, "*.safetensors"))]
bk = {}
for bf in base_files:
    with safe_open(bf, "pt") as f:
        for k in f.keys(): bk[k] = bf
changed, same, absent = 0, 0, 0
examples = []
with safe_open(ck, "pt") as f:
    for k in f.keys():
        if k not in bk: absent += 1; continue
        with safe_open(bk[k], "pt") as g:
            a, b = f.get_tensor(k).float(), g.get_tensor(k).float()
        if a.shape != b.shape or (a - b).abs().max().item() > 1e-6:
            changed += 1
            if len(examples) < 5: examples.append(k)
        else: same += 1
print(f"changed: {changed}, same as base: {same}, not in base: {absent}")
print("changed examples:", examples)
print("VERDICT:", "fine-tuning saved (weights merged into model)" if changed > 2 else "looks like fine-tuning did NOT make it into the save")
