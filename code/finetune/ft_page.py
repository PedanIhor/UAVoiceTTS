"""Page out_ft/listen.html: rows — voice × (plain/acute), columns — model versions,
on the right — the text fed to the model; stressed vowels highlighted. Can be run standalone: python ft_page.py"""
import os, re, sys, html
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "models"))
from stress_common import VOICES
OUT = os.path.join(HERE, "out_ft")

def show(text):
    """Escapes text and highlights the stressed vowel (vowel + U+0301)."""
    t = html.escape(text)
    return re.sub("(.)́", r"<b class='st'>\1&#769;</b>", t)

def _order(t):
    """base → higgs-base → runs by name (h1, h2, h3…), within each — by step."""
    if t == "base": return (0, "", 0)
    if t == "higgs-base": return (1, "", 0)
    m = re.match(r"(.*?)[_-](?:step|checkpoint-)(\d+)(.*)$", t)
    return (2, m.group(1) + m.group(3), int(m.group(2))) if m else (3, t, 0)

def build():
    tags = sorted((t for t in os.listdir(OUT) if os.path.isdir(os.path.join(OUT, t))),
                  key=_order)
    rows = []
    for n, r, _ in VOICES:
        for k in ("plain", "acute"):
            txt = next((open(os.path.join(OUT, t, f"{n}_{k}.txt"), encoding="utf-8").read()
                        for t in tags if os.path.exists(os.path.join(OUT, t, f"{n}_{k}.txt"))), "")
            cells = "".join(f"<td><audio controls preload='none' src='{t}/{n}_{k}.wav'></audio></td>"
                            if os.path.exists(os.path.join(OUT, t, f"{n}_{k}.wav")) else "<td>—</td>" for t in tags)
            rows.append(f"<tr class='{k}'><td><b>{r}</b><br><small>{k}</small></td>{cells}<td class='tx'>{show(txt)}</td></tr>")
    open(os.path.join(OUT, "listen.html"), "w", encoding="utf-8").write(
        "<meta charset='utf-8'><title>OmniVoice: fine-tuning</title><style>"
        "body{font:14px sans-serif;margin:20px}td{padding:6px 8px;vertical-align:top;border-bottom:1px solid #ddd}"
        "audio{width:190px}.tx{max-width:520px;line-height:1.6}.st{color:#c0392b;background:#fdecea;border-radius:3px;padding:0 1px}"
        "tr.acute td{background:#fafafa}small{color:#666}</style>"
        "<h2>OmniVoice: base vs fine-tuned versions</h2>"
        "<p>plain — text as is; acute — with stress marks (stressed vowels highlighted in red). On the right — exactly the text fed to the model.</p>"
        "<table><tr><th></th>" + "".join(f"<th>{t}</th>" for t in tags) + "<th>Input text</th></tr>" + "".join(rows) + "</table>")
    print("Listen: out_ft/listen.html")

if __name__ == "__main__":
    build()
