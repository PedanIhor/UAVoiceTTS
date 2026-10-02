"""Transcribe references (Whisper, Russian) -> refs_all/<voice>.txt. Higgs and Fish clone more accurately with the reference text."""
import os, re, sys
# On short lines Whisper "hallucinates" YouTube subtitle tails — strip them
BAD = re.compile(r"\s*(Продолжение следует\.*|Субтитры[^.!?]*|[^.!?]*DimaTorzok[^.!?]*|Редактор субтитров[^.!?]*|Спасибо за просмотр[^.!?]*)[.!?…]*", re.I)
sys.path.insert(0, os.path.dirname(__file__))
from common import all_sets, REFS, REF_LANG
from mlx_audio.stt import load
todo = [s for s in all_sets() if not os.path.exists(os.path.join(REFS, s[0] + ".txt"))]
if not todo: print("Transcripts already exist."); sys.exit()
m = load("mlx-community/whisper-large-v3-turbo-asr-fp16")
for name, *_ in todo:
    t = m.generate(os.path.join(REFS, name + ".wav"), language=REF_LANG).text.strip()
    t = BAD.sub("", t).strip()
    open(os.path.join(REFS, name + ".txt"), "w", encoding="utf-8").write(t)
    print(f"{name:28s} {t}")
