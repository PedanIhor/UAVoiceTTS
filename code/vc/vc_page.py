"""Scoring and listening page for the VC test: python vc_page.py [--score]
--score (in the vcseed env, needs resemblyzer): voice similarity (0–1) of the output to the NPC sample → out_vc/scores.json.
Page out_vc/listen.html: for each clip — the source with its text (stress marks highlighted), below it NPC voices × models."""
import os, sys, re, json, html, glob
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "out_vc"); REFS = os.path.join(HERE, "refs_all")
MODELS = [m for m in ("seed", "seed_f0", "chatterbox") if os.path.isdir(os.path.join(OUT, m))]
SC = os.path.join(OUT, "scores.json")

def score():
    from resemblyzer import VoiceEncoder, preprocess_wav
    import numpy as np
    enc = VoiceEncoder("cpu"); cache = {}
    def emb(p):
        if p not in cache: cache[p] = enc.embed_utterance(preprocess_wav(p))
        return cache[p]
    s = {}
    for m in MODELS + ["src"]:
        for f in glob.glob(os.path.join(OUT, m, "*__*.wav")) if m != "src" else []:
            v, sid = os.path.basename(f)[:-4].split("__")
            ref = os.path.join(REFS, v + ".wav"); src = os.path.join(OUT, "src", sid + ".wav")
            s[f"{m}/{v}/{sid}"] = {"ref": float(np.dot(emb(f), emb(ref))), "src": float(np.dot(emb(f), emb(src)))}
            s.setdefault(f"orig/{v}/{sid}", {"ref": float(np.dot(emb(src), emb(ref))), "src": 1.0})
    json.dump(s, open(SC, "w"), indent=1)
    import statistics as st
    for m in MODELS:
        vals = [x for k, x in s.items() if k.startswith(m + "/")]
        if not vals: print(f"{m:11s} — no finished files"); continue
        print(f"{m:11s} similarity to NPC {st.mean(x['ref'] for x in vals):.3f} | to speaker {st.mean(x['src'] for x in vals):.3f}")
    vals = [x for k, x in s.items() if k.startswith("orig/")]
    print(f"{'source':11s} similarity to NPC {st.mean(x['ref'] for x in vals):.3f}  (baseline: no conversion)")

def show(t): return re.sub("(.)́", r"<b class='st'>\1&#769;</b>", html.escape(t))
def au(p): return f"<audio controls preload='none' src='{os.path.relpath(p, OUT)}'></audio>" if os.path.exists(p) else "—"

def page():
    s = json.load(open(SC)) if os.path.exists(SC) else {}
    rows = []
    for src in sorted(glob.glob(os.path.join(OUT, "src", "*.wav"))):
        sid = os.path.basename(src)[:-4]; text = open(src[:-4] + ".txt", encoding="utf-8").read()
        rows.append(f"<tr class='src'><td colspan='{len(MODELS)+2}'><b>{sid}</b> {au(src)}<div class='t'>{show(text)}</div></td></tr>")
        voices = sorted({os.path.basename(f).split("__")[0] for m in MODELS for f in glob.glob(os.path.join(OUT, m, f"*__{sid}.wav"))})
        for v in voices:
            cells = [f"<td>{v.replace('npc','')}<br>{au(os.path.join(REFS, v + '.wav'))}</td>"]
            for m in MODELS:
                k = s.get(f"{m}/{v}/{sid}"); sc = f"<div class='sc'>NPC {k['ref']:.2f} · speaker {k['src']:.2f}</div>" if k else ""
                cells.append(f"<td>{au(os.path.join(OUT, m, f'{v}__{sid}.wav'))}{sc}</td>")
            rows.append("<tr>" + "".join(cells) + "</tr>")
    head = "<tr><th>NPC voice (sample)</th>" + "".join(f"<th>{m}</th>" for m in MODELS) + "</tr>"
    doc = f"""<!doctype html><meta charset='utf-8'><title>VC Test</title><style>
body{{font:14px system-ui;margin:16px;background:#fff;color:#222}} table{{border-collapse:collapse}} td,th{{border:1px solid #ddd;padding:6px;vertical-align:top}}
tr.src td{{background:#f4f6fa}} .t{{margin-top:4px;max-width:900px}} b.st{{color:#c0392b}} .sc{{font-size:12px;color:#666}} audio{{width:230px}}
@media (prefers-color-scheme:dark){{body{{background:#1c1c1e;color:#eee}} tr.src td{{background:#2a2d33}} td,th{{border-color:#444}} .sc{{color:#aaa}}}}
</style><h2>Voice conversion: opentts → NPC</h2>
<p>Similarity: "NPC" — how close it is to the NPC sample (higher is better), "speaker" — how much of the original speaker remains (lower is better).</p>
<table>{head}{''.join(rows)}</table>"""
    open(os.path.join(OUT, "listen.html"), "w", encoding="utf-8").write(doc); print("Listen: out_vc/listen.html")

if __name__ == "__main__":
    if "--score" in sys.argv: score()
    page()
