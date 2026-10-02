"""OmniVoice without reference (voice design from a description) → out_models/omni_design/"""
import os, sys, time, zlib
import soundfile as sf, torch
sys.path.insert(0, os.path.dirname(__file__))
from common import choose, text_for, HERE
from noref_common import DESIGN
out = os.path.join(HERE, "out_models", "omni_design"); os.makedirs(out, exist_ok=True)
todo = [s for s in choose(sys.argv[1:]) if not os.path.exists(os.path.join(out, s[0] + ".wav"))]
print(f"[omni_design] to do: {len(todo)}")
if todo:
    from omnivoice import OmniVoice
    dev = "mps" if torch.backends.mps.is_available() else "cpu"
    model = OmniVoice.from_pretrained("k2-fsa/OmniVoice", device_map=dev, dtype=torch.float32)
    for name, race, sex, kind in todo:
        torch.manual_seed(zlib.crc32(name.encode()))       # same voice on re-run
        t0 = time.time()
        audio = model.generate(text=text_for(race, sex)["text"], language="uk", instruct=DESIGN[(race, sex)])[0]
        sf.write(os.path.join(out, name + ".wav"), audio, 24000)
        print(f"[omni_design] {name:28s} '{DESIGN[(race, sex)]}' {time.time()-t0:5.1f} s")
