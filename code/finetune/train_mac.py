"""Run OmniVoice training on Mac (MPS). Three workarounds:
1) data loader without worker processes (on macOS spawn can't pickle a lambda from OmniVoice code);
2) fixed batch shapes: number of phrases always MAX_B, length rounded up to a multiple of BUCKET —
   otherwise the Apple GPU compiles kernels for every new shape, the cache grows, memory runs out, steps slow down;
3) clearing the MPS cache after every optimizer step;
4) NaN guard: if NaN/inf appear in gradients, the step is skipped instead of corrupting weights.
PAD_BATCH=0 — don't pad the batch with empty rows up to MAX_B (to check whether they cause NaN)."""
import os, runpy, sys, json
import torch, torch.nn.functional as F
import torch.utils.data as tud

cfg = json.load(open(sys.argv[sys.argv.index("--train_config") + 1]))
MAX_B = int(cfg["max_batch_size"]); BUCKET = int(os.environ.get("BUCKET", 64))
PAD_BATCH = os.environ.get("PAD_BATCH", "1") != "0"

_orig_init = tud.DataLoader.__init__
def _init(self, *a, **k):
    k["num_workers"] = 0; k.pop("prefetch_factor", None); k["persistent_workers"] = False; k["pin_memory"] = False
    _orig_init(self, *a, **k)
tud.DataLoader.__init__ = _init

from omnivoice.data import collator as C
_orig_call = C.PaddingDataCollator.__call__
LAST = [None]
STATS = {'ok': [], 'bad': []}
def _call(self, samples):
    out = _orig_call(self, samples[:MAX_B])
    B, _, T = out["input_ids"].shape
    LAST[0] = (B, T, [x.get("id", x.get("label", "?")) if isinstance(x, dict) else "?" for x in samples[:MAX_B]])
    TB = -(-T // BUCKET) * BUCKET
    pad_id = self.processor.text_tokenizer.pad_token_id
    dt, db = TB - T, (MAX_B - B if PAD_BATCH else 0)
    NB = B + db
    valid = out["attention_mask"][:, 0, 0, :]                                  # [B, T] real positions
    valid = F.pad(valid, (0, dt), value=False)
    out["input_ids"] = F.pad(out["input_ids"], (0, dt, 0, 0, 0, db), value=pad_id)
    out["labels"] = F.pad(out["labels"], (0, dt, 0, 0, 0, db), value=-100)     # empty rows don't contribute to loss
    out["audio_mask"] = F.pad(out["audio_mask"], (0, dt, 0, db), value=False)
    out["position_ids"] = F.pad(out["position_ids"], (0, dt, 0, db), value=0)
    if db:
        extra = torch.zeros(db, TB, dtype=torch.bool); extra[:, 0] = True       # one "visible" position to avoid NaN
        valid = torch.cat([valid, extra], 0)
    out["attention_mask"] = valid[:, None, None, :].expand(NB, 1, TB, TB).contiguous()
    return out
C.PaddingDataCollator.__call__ = _call
MODEL = [None]
from omnivoice.models import omnivoice as _OVM
_orig_fwd = _OVM.OmniVoice.forward
def _fwd(self, input_ids, audio_mask, labels=None, attention_mask=None, *a, **k):
    out = _orig_fwd(self, input_ids, audio_mask, labels, attention_mask, *a, **k)
    if not _FWD_SEEN[0]:
        _FWD_SEEN[0] = True; print("[train_mac] logits check enabled", flush=True)
    lg = out.logits
    with torch.no_grad():
        badpos = (~torch.isfinite(lg)).any(-1).any(1)  # [B,S]
        if badpos.any():
            am = attention_mask[:, 0, 0, :] if attention_mask is not None and attention_mask.dim() == 4 else None
            lab = (labels != -100).any(1) if labels is not None else None
            n = int(badpos.sum()); rows = badpos.any(1).nonzero().flatten().tolist()
            msg = f"[train_mac]   FORWARD: non-finite logits at {n} positions, rows {rows}, S={lg.shape[2]}"
            if am is not None: msg += f" | of them in padding: {int((badpos & ~am).sum())}"
            if lab is not None: msg += f" | with labels: {int((badpos & lab).sum())}"
            msg += f" | loss={float(out.loss) if out.loss is not None else None}"
            print(msg, flush=True)
    if lg.requires_grad:
        def _h(g):
            if not torch.isfinite(g).all():
                print(f"[train_mac]   BACKWARD: NaN already in logits gradient ({int((~torch.isfinite(g)).sum())} el.)", flush=True)
        lg.register_hook(_h)
    return out
_OVM.OmniVoice.forward = _fwd
import accelerate as _acc
_orig_clip = _acc.Accelerator.clip_grad_norm_
def _clip(self, parameters, *a, **k):
    parameters = list(parameters)
    if MODEL[0] is not None:
        names = {id(p): n for n, p in MODEL[0].named_parameters()}
        bad = []
        for p in parameters:
            if p.grad is not None:
                nf = ~torch.isfinite(p.grad)
                if nf.any():
                    bad.append((names.get(id(p), "?").replace("base_model.model.", "").replace("llm.model.", ""), int(nf.sum()), "inf" if torch.isinf(p.grad).any() else "nan"))
        if bad:
            print(f"[train_mac]   BEFORE CLIP: non-finite gradients in {len(bad)} params: " + "; ".join(f"{n} ({c} el., {t})" for n, c, t in bad[:8]), flush=True)
        else:
            mx = max((float(p.grad.abs().max()) for p in parameters if p.grad is not None), default=0)
            if mx > 1e4: print(f"[train_mac]   BEFORE CLIP: all finite, but max |grad| = {mx:.3g}", flush=True)
    return _orig_clip(self, parameters, *a, **k)
_acc.Accelerator.clip_grad_norm_ = _clip
_FWD_SEEN = [False]
import peft as _peft
_orig_gpm = _peft.get_peft_model
def _gpm(*a, **k):
    m = _orig_gpm(*a, **k); MODEL[0] = m; return m
_peft.get_peft_model = _gpm
def _bad_names():
    if MODEL[0] is None: return "?"
    names = {id(p): n for n, p in MODEL[0].named_parameters()}
    bad = [names.get(id(p), "?") for g in _OPT[0].param_groups for p in g["params"] if p.grad is not None and not torch.isfinite(p.grad).all()]
    short = sorted({n.replace("base_model.model.", "").replace("llm.model.", "") for n in bad})
    return f"{len(bad)} params: " + ", ".join(short[:6]) + (" …" if len(short) > 6 else "")
_OPT = [None]

if torch.backends.mps.is_available():
    _orig_step = torch.optim.AdamW.step
    skipped = [0]
    def _step(self, *a, **k):
        bad = any(p.grad is not None and not torch.isfinite(p.grad).all() for g in self.param_groups for p in g["params"])
        if bad:
            _OPT[0] = self
            print(f"[train_mac]   NaN in: {_bad_names()}", flush=True)
            skipped[0] += 1
            B, T, ids = LAST[0] if LAST[0] else (0, 0, [])
            STATS['bad'].append(T)
            print(f"[train_mac] NaN/inf in gradients — step skipped (total skipped: {skipped[0]}) | batch B={B} length T={T} | ids={ids}", flush=True)
            for g in self.param_groups:
                for p in g["params"]: p.grad = None
            torch.mps.empty_cache(); return None
        if LAST[0]: STATS['ok'].append(LAST[0][1])
        n = len(STATS['ok']) + len(STATS['bad'])
        if n % 50 == 0:
            import statistics as st
            print(f"[train_mac] over {n} steps: ok T≈{st.mean(STATS['ok'] or [0]):.0f} (max {max(STATS['ok'] or [0])}), NaN T≈{st.mean(STATS['bad'] or [0]):.0f} (min {min(STATS['bad'] or [0])})", flush=True)
        r = _orig_step(self, *a, **k); torch.mps.empty_cache(); return r
    torch.optim.AdamW.step = _step

sys.argv = ["omnivoice.cli.train"] + sys.argv[1:]
runpy.run_module("omnivoice.cli.train", run_name="__main__")
