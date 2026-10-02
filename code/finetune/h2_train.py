"""h2: LoRA fine-tuning of Higgs Audio v3 (MLX) on a mix of:
 • VC — opentts phrases (correct stress, 70% with marks) in NPC voices after voice conversion;
 • anchors — what base Higgs itself said in NPC voices (no marks) — keep the "native" sound of the voices.
Voice sample — NPC refs_tight with text, exactly as at inference. Anchor share ANCHOR (0.5).
Variables: RUN (h2), STEPS, ACC, LR, RANK, ALPHA, SAVE, ANCHOR, CONCAT."""
import os, sys, json, time, random
import numpy as np
import mlx.core as mx, mlx.nn as nn, mlx.optimizers as optim
from mlx.utils import tree_flatten, tree_map
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from higgs_common import load_model, apply_lora, build_example, loss_fn, boc_eoc, FT

H2 = os.path.expanduser(os.environ.get("H2DIR", "~/omni_ft/h2")); HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUN = os.environ.get("RUN", "h2"); STEPS = int(os.environ.get("STEPS", 1000)); ACC = int(os.environ.get("ACC", 4))
LR = float(os.environ.get("LR", 1e-4)); RANK = int(os.environ.get("RANK", 16)); ALPHA = float(os.environ.get("ALPHA", 32))
SAVE = int(os.environ.get("SAVE", 250)); WARM = max(1, int(0.05 * STEPS)); MAXT = int(os.environ.get("MAXT", 600))
ANCHOR = float(os.environ.get("ANCHOR", 0.5)); ANCHOR_ACUTE = float(os.environ.get("ANCHOR_ACUTE", 0.7))   # share of anchors with stress marks
OUT = os.path.join(FT, "exp", RUN); os.makedirs(OUT, exist_ok=True)
random.seed(42); mx.random.seed(42)

def rows(part): return [json.loads(l) for l in open(os.path.join(H2, part + ".jsonl"), encoding="utf-8")]
train, dev = [r for r in rows("train") if r["T"] <= MAXT], rows("dev")
vc_rows = [r for r in train if r["kind"] == "vc"]; an_rows = [r for r in train if r["kind"] == "anchor"]
vc_by_voice = {}
for r in vc_rows: vc_by_voice.setdefault(r["voice"], []).append(r)
_ref = {}
def ref_of(voice):
    if voice not in _ref:
        _ref[voice] = (np.load(os.path.join(H2, "refcodes", voice + ".npy")),
                       open(os.path.join(HERE, "refs_tight", voice + ".txt"), encoding="utf-8").read().strip())
    return _ref[voice]
CONCAT = float(os.environ.get("CONCAT", 0.5)); MAXCAT = int(os.environ.get("MAXCAT", 600))
EDGEFR = 7; GAPMIN = int(os.environ.get("GAPMIN", 6)); GAPMAX = int(os.environ.get("GAPMAX", 12))   # 40 ms frames
def example(model, r, rng, concat=None):
    parts = [r]
    if r["kind"] == "vc" and rng.random() < (CONCAT if concat is None else concat):   # concatenate 2–3 VC phrases of the same voice
        want, T = rng.choice((2, 3)), r["T"]
        for _ in range(20):
            if len(parts) >= want: break
            c = rng.choice(vc_by_voice[r["voice"]])
            if c not in parts and T + c["T"] <= MAXCAT: parts.append(c); T += c["T"]
    cs = [np.load(p["codes"]) for p in parts]
    for i in range(len(cs) - 1):                       # pause between concatenated phrases 0.24–0.48 s
        gap = rng.randint(GAPMIN, GAPMAX); ta = max(0, EDGEFR - gap // 2); tb = max(0, EDGEFR - (gap - gap // 2))
        if ta: cs[i] = cs[i][:-ta]
        if tb: cs[i + 1] = cs[i + 1][tb:]
    rc, rt = ref_of(r["voice"])
    text = " ".join(p["text"] for p in parts)
    if r["kind"] == "anchor" and "text_acute" in r and rng.random() < ANCHOR_ACUTE: text = r["text_acute"]
    return build_example(model, rc, rt, text, np.concatenate(cs, axis=0))
_orders = {"vc": [], "anchor": []}
def next_row(rng):
    kind = "anchor" if rng.random() < ANCHOR else "vc"
    src = an_rows if kind == "anchor" else vc_rows
    if not _orders[kind]: _orders[kind] = src[:]; rng.shuffle(_orders[kind])
    return _orders[kind].pop()

model = load_model()
n = apply_lora(model, RANK, ALPHA)
boc, _ = boc_eoc(model)
ntr = sum(v.size for _, v in tree_flatten(model.trainable_parameters()))
print(f"[higgs] LoRA on {n} layers, trainable params {ntr/1e6:.1f} M; VC {len(vc_rows)} phrases ({len(vc_by_voice)} voices), "
      f"anchors {len(an_rows)} (with marks {sum('text_acute' in r for r in an_rows)}, used in {ANCHOR_ACUTE:.0%}), dev {len(dev)}; steps {STEPS} × {ACC}, lr {LR}, anchor share {ANCHOR:.0%}", flush=True)
json.dump({"r": RANK, "alpha": ALPHA, "lr": LR, "steps": STEPS, "acc": ACC, "model": os.environ.get("HIGGS_MODEL", "")},
          open(os.path.join(OUT, "lora_config.json"), "w"))

sched = optim.join_schedules([optim.linear_schedule(LR * 0.01, LR, WARM), optim.cosine_decay(LR, STEPS - WARM, LR * 0.1)], [WARM])
opt = optim.AdamW(learning_rate=sched, weight_decay=0.0)
lvg = nn.value_and_grad(model, loss_fn)

drng = random.Random(7); dev_set = [example(model, r, drng, concat=0) for r in [x for x in dev if x["kind"] == "vc"][:40] + [x for x in dev if x["kind"] == "anchor"]]
def dev_loss():
    ls = [loss_fn(model, x, P, t, boc) for x, P, t in dev_set]
    mx.eval(ls); return float(np.mean([float(l) for l in ls]))
print(f"[higgs] dev loss before training: {dev_loss():.4f}", flush=True)

rng = random.Random(42); order = []; skipped = 0; t0 = time.time(); run_loss = []
def save(tag):
    p = os.path.join(OUT, f"{tag}.safetensors")
    mx.save_safetensors(p, dict(tree_flatten(model.trainable_parameters())))
    print(f"[higgs] saved: {p}", flush=True)
for step in range(1, STEPS + 1):
    acc, k = None, 0
    for _ in range(ACC):
        x, P, t = example(model, next_row(rng), rng)
        loss, g = lvg(model, x, P, t, boc)
        mx.eval(loss, g)
        if not np.isfinite(float(loss)): skipped += 1; continue
        acc = g if acc is None else tree_map(lambda a, b: a + b, acc, g); k += 1; run_loss.append(float(loss))
    if not k: continue
    acc = tree_map(lambda a: a / k, acc)
    acc, gn = optim.clip_grad_norm(acc, 1.0)
    if not np.isfinite(float(gn)): skipped += 1; print(f"[higgs] step {step}: grad_norm not finite — skipped", flush=True); continue
    opt.update(model, acc); mx.eval(model.trainable_parameters(), opt.state)
    if step % 5 == 0:
        el = time.time() - t0
        print(f"[higgs] step {step}/{STEPS}  loss {np.mean(run_loss[-5*ACC:]):.4f}  grad {float(gn):.2f}  lr {float(sched(step)):.2e}  "
              f"{el/step:.1f} s/step  left ~{el/step*(STEPS-step)/60:.0f} min  memory {mx.get_peak_memory()/1e9:.1f} GB  skipped {skipped}", flush=True)
    if step == 50 or step % SAVE == 0 or step == STEPS:
        save(f"step{step}")
        if step % SAVE == 0 or step == STEPS: print(f"[higgs] dev loss: {dev_loss():.4f}", flush=True)
print(f"[higgs] done in {(time.time()-t0)/60:.0f} min, skipped {skipped}")
