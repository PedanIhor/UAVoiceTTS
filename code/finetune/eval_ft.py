"""Evaluate the fine-tuned model: 3 of our voices (tight NPC references) × {no markup, with stress marks}.
python eval_ft.py <LoRA checkpoint dir>  → tts_local/out_ft/<checkpoint name>/, page out_ft/listen.html"""
import os, sys, glob, time, html, json
import soundfile as sf, torch
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "models"))
from stress_common import mark, VOICES
from common import text_for
from omnivoice import OmniVoice
try:                                   # the pip version of omnivoice lacks this module (only the git version has it)
    from omnivoice.utils.lora import load_lora_adapter
except ImportError:
    load_lora_adapter = None
ckpt = sys.argv[1] if len(sys.argv) > 1 else None
tag = (os.path.basename(os.path.dirname(ckpt.rstrip("/"))) + "-" + os.path.basename(ckpt.rstrip("/"))) if ckpt else "base"
OUT = os.path.join(HERE, "out_ft"); d = os.path.join(OUT, tag); os.makedirs(d, exist_ok=True)
dev = "mps" if torch.backends.mps.is_available() else "cpu"
def load_model(ckpt):
    """Base, a separate LoRA adapter (adapter_config.json) or a full model from the checkpoint (config.json + model.safetensors).
    If model.safetensors contains LoRA layers (keys with "lora_"), wrap the base with the same LoRA and merge."""
    base = OmniVoice.from_pretrained("k2-fsa/OmniVoice", device_map=dev, dtype=torch.float32, load_asr=True)
    if not ckpt: return base
    if os.path.exists(os.path.join(ckpt, "adapter_config.json")):
        from peft import PeftModel
        return PeftModel.from_pretrained(base, ckpt).merge_and_unload()
    from safetensors.torch import load_file
    sd = load_file(os.path.join(ckpt, "model.safetensors"))
    if any("lora_" in k for k in sd):
        from peft import LoraConfig, get_peft_model
        c = json.load(open(os.path.join(ckpt, "train_config.json")))
        peft = get_peft_model(base, LoraConfig(r=c["lora_r"], lora_alpha=c["lora_alpha"], lora_dropout=0.0,
                              bias=c["lora_bias"], target_modules=c["lora_target_modules"], modules_to_save=c["lora_modules_to_save"]))
        missing, unexpected = peft.load_state_dict(sd, strict=False)
        if len(unexpected) > len(sd) // 2:                           # keys saved without the peft prefix — try with it
            missing, unexpected = peft.load_state_dict({"base_model.model." + k: v for k, v in sd.items()}, strict=False)
        print(f"[eval] LoRA from model.safetensors: unexpected keys {len(unexpected)}, missing {len(missing)}")
        return peft.merge_and_unload()
    m = OmniVoice.from_pretrained(ckpt, device_map=dev, dtype=torch.float32, load_asr=True)   # full merged model
    return m

model = load_model(ckpt)
for name, race, sex in VOICES:
    w, sr = sf.read(os.path.join(HERE, "refs_tight", name + ".wav"), dtype="float32")
    for kind in ("plain", "acute"):
        dst = os.path.join(d, f"{name}_{kind}.wav")
        if os.path.exists(dst): continue
        text = mark(text_for(race, sex)["text"], kind)
        audio = model.generate(text=text, language="uk", ref_audio=(torch.from_numpy(w).unsqueeze(0), sr))[0]
        sf.write(dst, audio, 24000); open(dst[:-4] + ".txt", "w", encoding="utf-8").write(text)
        print(tag, name, kind)
from ft_page import build
build()
