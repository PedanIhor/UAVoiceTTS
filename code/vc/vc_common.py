"""Shared VC code: load a converter (chatterbox | seed_f0 | seed) → conv(src_wav, ref_wav) -> (np.float32 24 kHz)."""
import os, sys
import numpy as np, librosa
def make_converter(kind):
    if kind.startswith("seed"):
        import torch
        _fn = torch.from_numpy                                   # MPS has no float64 (Seed-VC's F0 is float64)
        torch.from_numpy = lambda a: _fn(a.astype(np.float32) if getattr(a, "dtype", None) == np.float64 else a)
        cwd = os.getcwd(); os.chdir(os.path.expanduser("~/omni_ft/tools/seed-vc")); sys.path.insert(0, os.getcwd())
        from seed_vc_wrapper import SeedVCWrapper
        vc = SeedVCWrapper(); os.chdir(cwd); f0 = kind == "seed_f0"; root = os.path.expanduser("~/omni_ft/tools/seed-vc")
        def conv(src, ref):
            here = os.getcwd(); os.chdir(root)
            try:
                g = vc.convert_voice(src, ref, diffusion_steps=30, length_adjust=1.0, inference_cfg_rate=0.7,
                                     f0_condition=f0, auto_f0_adjust=True, pitch_shift=0, stream_output=False)
                out = None
                try:
                    while True:
                        x = next(g); out = x[1] if isinstance(x, tuple) else x
                except StopIteration as e:
                    if e.value is not None: out = e.value
            finally: os.chdir(here)
            y = np.asarray(out, dtype=np.float32).reshape(-1)
            return librosa.resample(y, orig_sr=44100 if f0 else 22050, target_sr=24000)
        return conv
    import torch
    from chatterbox.vc import ChatterboxVC
    vc = ChatterboxVC.from_pretrained("mps" if torch.backends.mps.is_available() else "cpu")
    vc.watermarker.apply_watermark = lambda wav, sample_rate: wav            # training data — no watermark
    def conv(src, ref):
        y = vc.generate(src, target_voice_path=ref).squeeze(0).numpy().astype(np.float32)
        return librosa.resample(y, orig_sr=vc.sr, target_sr=24000) if vc.sr != 24000 else y
    return conv
