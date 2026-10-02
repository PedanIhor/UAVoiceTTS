"""Page out_stress2/listen.html: rows = voice × variant, columns = models."""
import os, sys, html
sys.path.insert(0, os.path.dirname(__file__))
from stress_common import VARIANTS, VOICES, MODELS, OUT
rows = []
for name, race, _ in VOICES:
    for v in VARIANTS:
        cells = "".join(f"<td><audio controls preload='none' src='{m}/{v}/{name}.wav'></audio></td>"
                        if os.path.exists(os.path.join(OUT, m, v, name + ".wav")) else "<td>—</td>" for m in MODELS)
        rows.append(f"<tr><td><b>{race}</b></td><td>{v}</td>{cells}</tr>")
    rows.append("<tr><td colspan='5'>&nbsp;</td></tr>")
txt = {}
for v in VARIANTS:
    for m in MODELS:
        p = os.path.join(OUT, m, v, "humanmalestandardnpc.txt")
        if os.path.exists(p) and v not in txt: txt[v] = open(p, encoding="utf-8").read()
os.makedirs(OUT, exist_ok=True)
open(os.path.join(OUT, "listen.html"), "w", encoding="utf-8").write(
    "<meta charset='utf-8'><title>Stress: comparison</title><style>body{font:14px sans-serif;margin:20px}td{padding:4px 8px}audio{width:210px}</style>"
    "<h2>Stress: markup × temperature × model</h2><p>acute — stress mark (мо́ва), upper — stressed vowel capitalized (мОва), t — temperature. "
    "For OmniVoice t is mapped to position_temperature (0.8 = default).</p><table><tr><th>Voice</th><th>Variant</th>"
    + "".join(f"<th>{n}</th>" for n in MODELS.values()) + "</tr>" + "".join(rows) + "</table><h3>Input (human)</h3>"
    + "".join(f"<p><b>{v}</b>: {html.escape(t)}</p>" for v, t in txt.items()))
print("Listen:out_stress2/listen.html")
