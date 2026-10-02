"""Fish S2 Pro without reference: voice from a free-form description (instruct), seed fixed per voice → out_models/fish_noref/"""
import os, sys, time, zlib
import numpy as np, soundfile as sf, mlx.core as mx
sys.path.insert(0, os.path.dirname(__file__))
from common import choose, text_for, HERE
from mlx_audio.tts import load
UA = " Speaks Ukrainian as a native speaker, with standard Ukrainian pronunciation and correct word stress."
DESC = {
    ("human", "male"): "Clear, noble middle-aged male voice with confident, measured delivery.",
    ("human", "female"): "Warm, clear young female voice, friendly and articulate.",
    ("dwarf", "male"): "Loud, raspy, hearty bass voice of an old male, energetic and boisterous.",
    ("dwarf", "female"): "Hearty, slightly raspy middle-aged female voice, energetic and warm.",
    ("gnome", "male"): "High-pitched, quick, cheerful young male voice, nerdy and excitable.",
    ("gnome", "female"): "Very high-pitched, bright, bubbly young female voice, quick delivery.",
    ("nightelf", "male"): "Deep, calm, slow male voice, serene and wise.",
    ("nightelf", "female"): "Proud, graceful, firm female voice, poetic and composed.",
    ("orc", "male"): "Deep, gravelly, guttural low-pitched male voice, stern and proud.",
    ("orc", "female"): "Low, husky, strong female voice, stern and confident.",
    ("undead", "male"): "Raspy, dry, sinister old male voice, cold and hoarse.",
    ("undead", "female"): "Cold, hollow, raspy female voice, sinister and weary.",
    ("tauren", "male"): "Very deep, slow, rumbling bass male voice, calm and wise.",
    ("tauren", "female"): "Low, calm, gentle female voice, slow and wise.",
    ("troll", "male"): "Relaxed, husky, sing-song male voice with a laid-back rhythm.",
    ("troll", "female"): "Relaxed, husky, melodic female voice, laid-back.",
    ("goblin", "male"): "High, fast, shrill scheming male voice, greedy and excited.",
    ("goblin", "female"): "High, fast, sharp female voice, sly and excited.",
}
out = os.path.join(HERE, "out_models", "fish_noref"); os.makedirs(out, exist_ok=True)
todo = [s for s in choose(sys.argv[1:]) if not os.path.exists(os.path.join(out, s[0] + ".wav"))]
print(f"[fish_noref] to do: {len(todo)}")
if todo:
    model = load("mlx-community/fish-audio-s2-pro"); sr = model.sample_rate
    for name, race, sex, kind in todo:
        mx.random.seed(zlib.crc32(name.encode()))
        t0 = time.time()
        gen = model.generate(text=text_for(race, sex)["text"], instruct=DESC[(race, sex)] + UA, max_tokens=2048)
        audio = np.concatenate([np.array(r.audio, dtype=np.float32).reshape(-1) for r in gen])
        sf.write(os.path.join(out, name + ".wav"), audio, sr)
        print(f"[fish_noref] {name:28s} {time.time()-t0:5.1f} s")
