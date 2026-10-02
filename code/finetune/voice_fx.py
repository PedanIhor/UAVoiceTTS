"""Voice post-processing for production. Undead: variant B "crypt" (chosen by Ihor 01.10.2026).
apply(voice, y, sr) -> y (mono float32). Other voices — unchanged."""
import numpy as np
_UNDEAD = None
def apply(voice, y, sr):
    global _UNDEAD
    if not voice.startswith("undead"): return y
    if _UNDEAD is None:
        from pedalboard import Pedalboard, Reverb
        _UNDEAD = Pedalboard([Reverb(room_size=0.55, damping=0.35, wet_level=0.28, dry_level=0.85, width=0.8)])
    z = _UNDEAD(np.asarray(y, dtype=np.float32)[None, :], sr)[0]
    return z / (np.abs(z).max() + 1e-9) * 0.9
