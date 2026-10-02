"""Comparison page: row = voice, columns = models. Open out_models/listen.html"""
import os, sys, html
sys.path.insert(0, os.path.dirname(__file__))
from common import choose, text_for, HERE
base = os.path.join(HERE, "out_models"); os.makedirs(base, exist_ok=True)
NAMES = {"higgs": "Higgs TTS 3", "higgsmlx": "Higgs (MLX bf16)", "omni": "OmniVoice no reference", "fish": "Fish S2"}
cols = [("original (reference)", "../refs_all")]
cols += [("OmniVoice" + d[7:].replace("_", " "), "../" + d) for d in sorted(os.listdir(HERE)) if d.startswith("out_all") and os.path.isdir(os.path.join(HERE, d))]
for d in sorted(os.listdir(base)):
    if os.path.isdir(os.path.join(base, d)) and not d.startswith("_"):
        m, var = d.partition("_")[::2]; cols.append((NAMES.get(m, m) + (" " + var.replace("_", "+") if var else ""), d))
rows = []
for name, race, sex, kind in choose(sys.argv[1:]):
    t = text_for(race, sex)
    cells = []
    for _, d in cols:
        f = os.path.join(base, d, name + ".wav")
        cells.append(f"<td><audio controls preload='none' src='{d}/{name}.wav'></audio></td>" if os.path.exists(f) else "<td>—</td>")
    rows.append(f"<tr><td><b>{race}</b> {'fem.' if sex=='female' else 'male'}<br><small>{kind}</small></td>{''.join(cells)}"
                f"<td><small><b>{html.escape(t['title'])}</b><br>{html.escape(t['text'])}</small></td></tr>")
open(os.path.join(base, "listen.html"), "w", encoding="utf-8").write(
    "<meta charset='utf-8'><title>Model comparison</title><style>body{font:14px sans-serif;margin:20px}"
    "td{border-bottom:1px solid #ddd;padding:6px;vertical-align:top}audio{width:190px}small{color:#555}</style>"
    "<h2>Voiceover model comparison</h2>"
    "<table><tr><th>Voice</th>" + "".join(f"<th>{c}</th>" for c, _ in cols) + "<th>Text</th></tr>" + "".join(rows) + "</table>")
print("Listen:out_models/listen.html")
