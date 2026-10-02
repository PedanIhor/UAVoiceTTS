"""Page out_allv/listen.html: all voices by race; NPC sample | base Higgs | h3 (with marks) | text + pauses/tempo."""
import os, re, json, html, numpy as np, soundfile as sf
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); OUT = os.path.join(HERE, "out_allv")
TX = json.load(open(os.path.join(OUT, "texts.json"), encoding="utf-8"))
RACES = ["human", "dwarf", "gnome", "nightelf", "orc", "troll", "tauren", "undead", "goblin", "skyborne"]
def stats(p, text):
    if not os.path.exists(p): return ""
    y, sr = sf.read(p); y = y.mean(1) if y.ndim > 1 else y; fr = int(0.02 * sr); n = len(y) // fr
    e = 20 * np.log10(np.sqrt((y[:n*fr].reshape(n, fr) ** 2).mean(1)) + 1e-9); loud = np.nonzero(e > e.max() - 40)[0]
    gaps = [(b - a - 1) * 0.02 for a, b in zip(loud[:-1], loud[1:]) if (b - a - 1) * 0.02 >= 0.35]
    cps = len(text) / (len(y) / sr); warn = " ⚠" if gaps and max(gaps) > 0.6 or cps < 10 else ""
    return f"<div class='sc'>{len(y)/sr:.1f} s · {cps:.0f} chars/s · pauses ≥0.35 s: {len(gaps)}{(' (max ' + format(max(gaps), '.1f') + ' s)') if gaps else ''}{warn}</div>"
au = lambda p: f"<audio controls preload='none' src='{os.path.relpath(p, OUT)}'></audio>" if os.path.exists(p) else "—"
def show(t): return re.sub("(.)́", r"<b class='st'>\1&#769;</b>", html.escape(t))
rows = []
for race in RACES:
    vs = sorted(v for v in TX if v.startswith(race) and not (race == "human" and False))
    if not vs: continue
    rows.append(f"<tr class='r'><td colspan='4'>{race}</td></tr>")
    for v in vs:
        b, h = os.path.join(OUT, "base", v + ".wav"), os.path.join(OUT, "h3", v + ".wav")
        rows.append(f"<tr><td><b>{v.replace('npc','').replace(race,'')}</b><br>{au(os.path.join(HERE,'refs_tight',v+'.wav'))}</td>"
                    f"<td>{au(b)}{stats(b, TX[v]['plain'])}</td><td>{au(h)}{stats(h, TX[v]['plain'])}</td><td class='t'>{show(TX[v]['acute'])}</td></tr>")
open(os.path.join(OUT, "listen.html"), "w", encoding="utf-8").write(f"""<!doctype html><meta charset='utf-8'><title>All voices h3</title><style>
body{{font:14px system-ui;margin:16px;background:#fff;color:#222}} table{{border-collapse:collapse}} td,th{{border:1px solid #ddd;padding:6px;vertical-align:top}}
tr.r td{{background:#eef1f6;font-weight:600;text-transform:capitalize}} .t{{max-width:520px}} b.st{{color:#c0392b}} .sc{{font-size:12px;color:#666}} audio{{width:220px}}
@media (prefers-color-scheme:dark){{body{{background:#1c1c1e;color:#eee}} td,th{{border-color:#444}} tr.r td{{background:#2a2d33}} .sc{{color:#aaa}}}}</style>
<h2>All NPC voices: base Higgs and h3 (step1000)</h2><p>Base voices text without stress marks, h3 — with marks (highlighted on the right). ⚠ — long pause (&gt;0.6 s) or slow tempo.</p>
<table><tr><th>voice (sample)</th><th>base Higgs</th><th>h3 step1000</th><th>text</th></tr>{''.join(rows)}</table>""")
print("Listen: out_allv/listen.html")
