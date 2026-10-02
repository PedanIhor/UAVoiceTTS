"""Ukrainian StyleTTS2 with its OWN voices (speakers from the author's demo), no NPC reference.
Stress from a dictionary, pronunciation via IPA. All male voices read the same male text, female voices the same female text,
so voices can be compared with each other. + the single-speaker model (Filatov's voice) as a narrator candidate.
Output: out_models/styletts2_builtin/ and the listen.html page there."""
import os, re, sys, time, glob, html
from unicodedata import normalize
import numpy as np, soundfile as sf, torch
sys.path.insert(0, os.path.dirname(__file__))
from common import HERE, text_for
from huggingface_hub import snapshot_download
from styletts2_inference.models import StyleTTS2
from ukrainian_word_stress import Stressifier
from ipa_uk import ipa

OUT = os.path.join(HERE, "out_models", "styletts2_builtin"); os.makedirs(OUT, exist_ok=True)
MALE = {"Артем Окороков", "Вʼячеслав Дудко", "Денис Денисенко", "Кирило Татарченко", "Матвій Ніколаєв", "Михайло Тишин",
        "Олександр Ролдугін", "Павло Буковський", "Петро Філяк", "Роман Куліш", "Тарас Василюк", "Юрій Вихованець", "Юрій Кудрявець"}
TEXT = {"male": text_for("dwarf", "male")["text"], "female": text_for("human", "female")["text"]}

space = snapshot_download("patriotyk/styletts2-ukrainian", repo_type="space", allow_patterns=["voices/*", "filatov.pt"])
voices = sorted(glob.glob(os.path.join(space, "voices", "*.pt")))
try:
    stressify = Stressifier(); stressify("тест")
except Exception as e:
    from ukrainian_word_stress import Disambiguation
    print("stanza unavailable, dictionary-based stress:", str(e).splitlines()[0])
    stressify = Stressifier(disambiguation=Disambiguation.Dictionary)

def parts(text):
    ps, cur = [], ""
    for i, ch in enumerate(text):
        cur += ch
        if ch in ".?!:" and (i == len(text) - 1 or text[i + 1] == " "):
            ps.append(cur.strip()); cur = ""
    if cur.strip(): ps.append(cur.strip())
    return ps

def synth(model, style, text):
    wavs, shown = [], []
    for t in parts(text):
        t = normalize("NFKC", t.replace('"', "")); t = re.sub(r"[᠆‐‑‒–—―⁻₋−⸺⸻]", "-", t)
        if t[-1] not in ".?!:-": t += "."
        t = stressify(re.sub(r" - ", ": ", t)); shown.append(t)
        wavs.append(model(model.tokenizer.encode(ipa(t)), speed=1.0, s_prev=style).cpu().numpy())
    return np.concatenate(wavs), " ".join(shown)

rows = []
multi = StyleTTS2(hf_path="patriotyk/styletts2_ukrainian_multispeaker", device="cpu")
for p in voices:
    name = os.path.basename(p)[:-3]; sex = "male" if name in MALE else "female"
    dst = os.path.join(OUT, name + ".wav")
    if not os.path.exists(dst):
        t0 = time.time(); audio, shown = synth(multi, torch.load(p), TEXT[sex])
        sf.write(dst, audio, 24000); open(dst[:-4] + ".txt", "w", encoding="utf-8").write(shown)
        print(f"{name:28s} {len(audio)/24000:5.1f} s of audio in {time.time()-t0:5.1f} s")
    rows.append((sex, name))
single_dst = os.path.join(OUT, "_narrator (Filatov).wav")
if not os.path.exists(single_dst):
    single = StyleTTS2(hf_path="patriotyk/styletts2_ukrainian_single", device="cpu")
    audio, shown = synth(single, torch.load(os.path.join(space, "filatov.pt")), TEXT["male"])
    sf.write(single_dst, audio, 24000); print("narrator (Filatov) ready")
rows.append(("male", "_narrator (Filatov)"))

def tr(sex, n):
    return f"<tr><td>{html.escape(n)}</td><td><audio controls preload='none' src='{html.escape(n)}.wav'></audio></td></tr>"
page = ("<meta charset='utf-8'><title>StyleTTS2: built-in voices</title><style>body{font:14px sans-serif;margin:20px}td{padding:4px 8px}</style>"
        "<h2>StyleTTS2 uk — built-in speaker voices</h2>"
        f"<h3>Male (text: {html.escape(TEXT['male'])})</h3><table>" + "".join(tr(s, n) for s, n in rows if s == "male") + "</table>"
        f"<h3>Female (text:{html.escape(TEXT['female'])})</h3><table>" + "".join(tr(s, n) for s, n in rows if s == "female") + "</table>")
open(os.path.join(OUT, "listen.html"), "w", encoding="utf-8").write(page)
print("Listen:out_models/styletts2_builtin/listen.html")
