"""Shared code for Higgs Audio v3 (MLX) fine-tuning: model loading, LoRA, training example assembly.
Prompt format as in mlx-audio: <|tts|> <|ref_text|>sample text <|ref_audio|>[sample codes] <|text|>text <|audio|> → code rows."""
import os, math, json
import numpy as np
import mlx.core as mx
import mlx.nn as nn

MODEL_ID = os.environ.get("HIGGS_MODEL", "bosonai/higgs-audio-v3-tts-4b")
FT = os.path.expanduser(os.environ.get("HFT", "~/omni_ft/higgs"))      # everything for Higgs
SRC = os.path.expanduser(os.environ.get("SRC", "~/omni_ft/r3"))       # r3 data (35 dB cleanup, 0.3 s edges, pauses untouched)
TARGETS = ("q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj")
ACUTE = "́"

def load_model():
    from mlx_audio.tts import load
    return load(MODEL_ID)

class LoRALinear(nn.Module):
    def __init__(self, base: nn.Linear, r: int, alpha: float):
        super().__init__()
        self.base = base
        out_d, in_d = base.weight.shape
        self.scale = alpha / r
        s = 1 / math.sqrt(in_d)
        self.lora_a = mx.random.uniform(-s, s, (in_d, r)).astype(mx.float32)
        self.lora_b = mx.zeros((r, out_d), dtype=mx.float32)
    def __call__(self, x):
        z = (x.astype(mx.float32) @ self.lora_a) @ self.lora_b
        return self.base(x) + (self.scale * z).astype(x.dtype)

def apply_lora(model, r=16, alpha=32):
    """Freezes the model and attaches LoRA to attention and MLP projections of all Qwen3 layers."""
    model.freeze()
    n = 0
    for layer in model.backbone.layers:
        for part in (getattr(layer, "self_attn", None), getattr(layer, "mlp", None)):
            if part is None: continue
            for name in TARGETS:
                m = getattr(part, name, None)
                if isinstance(m, nn.Linear) and not isinstance(m, LoRALinear):
                    setattr(part, name, LoRALinear(m, r, alpha)); n += 1
    assert n > 0, "no layers found for LoRA — different mlx-audio version?"
    return n

def load_adapter(model, path):
    cfg = json.load(open(os.path.join(os.path.dirname(path), "lora_config.json")))
    apply_lora(model, cfg["r"], cfg["alpha"])
    model.load_weights(path, strict=False)
    return cfg

def boc_eoc(model):
    return int(model.config.audio_boc_token_id), int(model.config.audio_eoc_token_id)

def delay(codes, boc, eoc):
    """[T, N] → [T+N-1, N], like apply_delay_pattern in mlx-audio."""
    t, n = codes.shape
    out = np.full((t + n - 1, n), eoc, dtype=np.int32)
    for c in range(n):
        out[:c, c] = boc
        out[c:c + t, c] = codes[:, c]
    return out

def build_example(model, ref_codes, ref_text, text, tgt_codes):
    """Input (prompt embeddings + target rows except the last), prompt length P and targets [L, N]."""
    from mlx_audio.tts.models.higgs_audio_v3.prompt import ReferenceCodes
    boc, eoc = boc_eoc(model)
    refs = [ReferenceCodes(codes=mx.array(delay(ref_codes, boc, eoc)), text=ref_text)] if ref_codes is not None else []
    prompt, _ = model._build_prompt_embeddings(text, refs)                 # [1, P, H]
    tgt = delay(tgt_codes, boc, eoc)                                        # [L, N]
    tin = model._embed_audio_codes(mx.array(tgt[:-1]))[None].astype(prompt.dtype)
    return mx.concatenate([prompt, tin], axis=1), prompt.shape[1], mx.array(tgt)

def loss_fn(model, x, P, tgt, boc):
    h = model.backbone(mx.zeros((1, x.shape[1]), dtype=mx.int32), input_embeddings=x)
    h = h[:, P - 1:, :]                                                     # the <|audio|> position predicts the first row
    logits = model._audio_logits(h)[0].astype(mx.float32)                  # [L, N, V]
    ce = nn.losses.cross_entropy(logits, tgt, reduction="none")            # [L, N]
    m = (tgt != boc).astype(mx.float32)                                     # don't train on "codebook not started yet" positions (the sampler sets them)
    return (ce * m).sum() / m.sum()
