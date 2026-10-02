"""Shared for the stress test: variants (markup × temperature), 3 voices, output folders out_stress2/<model>/<variant>/."""
import os, re
from common import HERE, text_for
VOICES = [("humanmalestandardnpc", "human", "male"), ("dwarfmalestandardnpc", "dwarf", "male"), ("orcmalestandardnpc", "orc", "male")]
# variant: (markup, temperature)
VARIANTS = {"0_plain_t0.8": ("plain", 0.8), "1_acute_t0.8": ("acute", 0.8), "2_upper_t0.8": ("upper", 0.8),
            "3_plain_t0.4": ("plain", 0.4), "4_acute_t0.4": ("acute", 0.4), "5_plain_t0.55": ("plain", 0.55),
            "6_acute_t0.55": ("acute", 0.55), "7_upper_t0.55": ("upper", 0.55)}
MODELS = {"omni": "OmniVoice", "higgs": "Higgs", "higgsmlx": "Higgs MLX bf16"}
REFS = os.path.join(HERE, "refs_tight")
OUT = os.path.join(HERE, "out_stress2")
A, VOW = "́", "аеєиіїоуюяАЕЄИІЇОУЮЯ"
_st = None
def stressify(t):
    global _st
    if _st is None:
        from ukrainian_word_stress import Stressifier, StressSymbol
        try:
            _st = Stressifier(stress_symbol=StressSymbol.CombiningAcuteAccent); _st("тест")
        except Exception as e:
            from ukrainian_word_stress import Disambiguation
            print("stanza unavailable, dictionary-based stress:", str(e).splitlines()[0])
            _st = Stressifier(stress_symbol=StressSymbol.CombiningAcuteAccent, disambiguation=Disambiguation.Dictionary)
    return _st(t)
def mark(text, kind):
    if kind == "plain": return text
    s = stressify(text)
    return s if kind == "acute" else re.sub(f"([{VOW}]){A}", lambda m: m.group(1).upper(), s)
def todo(model):
    return [(v, *x) for v in VARIANTS for x in VOICES if not os.path.exists(os.path.join(OUT, model, v, x[0] + ".wav"))]
def save(model, v, name, audio, sr, text):
    import soundfile as sf
    d = os.path.join(OUT, model, v); os.makedirs(d, exist_ok=True)
    sf.write(os.path.join(d, name + ".wav"), audio, sr)
    open(os.path.join(d, name + ".txt"), "w", encoding="utf-8").write(text)
def ref_text(name): return open(os.path.join(REFS, name + ".txt"), encoding="utf-8").read().strip()
