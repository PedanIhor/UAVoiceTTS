"""Similarity scoring (resemblyzer) and per-voice VC selection page: out_vc_probe/listen.html.
Voices where chatterbox loses most to seed_f0 are at the top. Tick the voices where seed_f0 is better;
a line to copy appears at the bottom of the page."""
import os, sys, json, html, statistics as st
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "out_vc_probe"); REFS = os.path.join(HERE, "refs_all"); M = ("chatterbox", "seed_f0")
plan = json.load(open(os.path.join(OUT, "plan.json")))
from resemblyzer import VoiceEncoder, preprocess_wav
import numpy as np
enc = VoiceEncoder("cpu"); cache = {}
def emb(p):
    if p not in cache: cache[p] = enc.embed_utterance(preprocess_wav(p))
    return cache[p]
by = {}
for v, sid in plan:
    for m in M:
        p = os.path.join(OUT, m, f"{v}__{sid}.wav")
        if os.path.exists(p): by.setdefault(v, {}).setdefault(m, []).append((sid, p, float(np.dot(emb(p), emb(os.path.join(REFS, v + ".wav"))))))
def mean(v, m): return st.mean(x[2] for x in by[v].get(m, [])) if by[v].get(m) else float("nan")
order = sorted(by, key=lambda v: -(mean(v, "seed_f0") - mean(v, "chatterbox")))
au = lambda p: f"<audio controls preload='none' src='{os.path.relpath(p, OUT)}'></audio>"
rows = []
for v in order:
    dlt = mean(v, "seed_f0") - mean(v, "chatterbox")
    cells = [f"<td><label><input type='checkbox' value='{v}' {'checked' if dlt > 0.03 else ''}> <b>{v.replace('npc','')}</b></label><br>{au(os.path.join(REFS, v + '.wav'))}"
             f"<div class='sc'>seed_f0 − chatterbox: {dlt:+.3f}</div></td>"]
    for m in M:
        c = "".join(f"<div>{au(p)}<span class='sc'> {s:.2f}</span></div>" for _, p, s in by[v].get(m, []))
        cells.append(f"<td>{c}<div class='sc'>mean {mean(v, m):.3f}</div></td>")
    srcs = "".join(f"<div>{au(os.path.join(OUT,'src',sid+'.wav'))}</div>" for sid, _, _ in by[v].get("chatterbox", []))
    cells.append(f"<td>{srcs}</td>")
    rows.append("<tr>" + "".join(cells) + "</tr>")
tot = {m: st.mean(mean(v, m) for v in by) for m in M}
doc = f"""<!doctype html><meta charset='utf-8'><title>Per-Voice VC Choice</title><style>
body{{font:14px system-ui;margin:16px;background:#fff;color:#222}} table{{border-collapse:collapse}} td,th{{border:1px solid #ddd;padding:6px;vertical-align:top}}
.sc{{font-size:12px;color:#666}} audio{{width:210px}} textarea{{width:100%;height:60px}}
@media (prefers-color-scheme:dark){{body{{background:#1c1c1e;color:#eee}} td,th{{border-color:#444}} .sc{{color:#aaa}}}}</style>
<h2>Which VC for which voice</h2>
<p>Mean similarity to NPC: chatterbox {tot['chatterbox']:.3f}, seed_f0 {tot['seed_f0']:.3f}. Top rows are where chatterbox loses most.
Checked = use <b>seed_f0</b> for this voice (pre-checked where seed_f0 is 0.03+ higher). Copy the line at the bottom into the chat.</p>
<table><tr><th>voice (sample)</th><th>chatterbox</th><th>seed_f0</th><th>source</th></tr>{''.join(rows)}</table>
<p><b>To copy:</b></p><textarea id='o' readonly></textarea>
<script>function u(){{document.getElementById('o').value='seed_f0: '+[...document.querySelectorAll('input:checked')].map(e=>e.value).join(', ')}}
document.querySelectorAll('input').forEach(e=>e.onchange=u);u();</script>"""
open(os.path.join(OUT, "listen.html"), "w", encoding="utf-8").write(doc)
print(f"voices {len(by)} | mean similarity: chatterbox {tot['chatterbox']:.3f}, seed_f0 {tot['seed_f0']:.3f}\nListen: out_vc_probe/listen.html")
