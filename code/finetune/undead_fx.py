"""Echo for undead voices: in-game their lines are processed (reverb/"hollowness"), while the model outputs a dry voice.
Try several processing variants on h3 voiceovers → out_allv/undead_fx/<variant>/<voice>.wav + page undead.html.
Requires pedalboard (pip install pedalboard)."""
import os, glob, html
import numpy as np, soundfile as sf
from pedalboard import Pedalboard, Reverb, Delay, Chorus, HighpassFilter, Gain
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); A = os.path.join(HERE, "out_allv"); O = os.path.join(A, "undead_fx")
PRESETS = {
    "A_room":           Pedalboard([Reverb(room_size=0.25, damping=0.5, wet_level=0.18, dry_level=0.9, width=0.6)]),
    "B_crypt":          Pedalboard([Reverb(room_size=0.55, damping=0.35, wet_level=0.28, dry_level=0.85, width=0.8)]),
    "C_echo+crypt":     Pedalboard([Delay(delay_seconds=0.045, feedback=0.25, mix=0.22), Reverb(room_size=0.45, damping=0.4, wet_level=0.22, dry_level=0.85)]),
    "D_ghostly":        Pedalboard([Chorus(rate_hz=0.6, depth=0.15, mix=0.25), Delay(delay_seconds=0.03, feedback=0.2, mix=0.2),
                                    Reverb(room_size=0.4, damping=0.4, wet_level=0.22, dry_level=0.85), HighpassFilter(90)]),
}
voices = sorted(os.path.basename(f)[:-4] for f in glob.glob(os.path.join(A, "h3", "undead*.wav")))
for name, pb in PRESETS.items():
    os.makedirs(os.path.join(O, name), exist_ok=True)
    for v in voices:
        y, sr = sf.read(os.path.join(A, "h3", v + ".wav"), dtype="float32")
        z = pb(y[None, :] if y.ndim == 1 else y.T, sr)[0]
        z = z / (np.abs(z).max() + 1e-9) * 0.9
        sf.write(os.path.join(O, name, v + ".wav"), z, sr)
au = lambda p: f"<audio controls preload='none' src='{os.path.relpath(p, A)}'></audio>"
rows = "".join("<tr><td><b>" + v.replace("npc", "") + "</b><br>sample: " + au(os.path.join(HERE, "refs_tight", v + ".wav")) + "</td><td>" + au(os.path.join(A, "h3", v + ".wav")) + "</td>"
               + "".join("<td>" + au(os.path.join(O, n, v + ".wav")) + "</td>" for n in PRESETS) + "</tr>" for v in voices)
open(os.path.join(A, "undead.html"), "w", encoding="utf-8").write(f"""<!doctype html><meta charset='utf-8'><title>Undead echo</title><style>
body{{font:14px system-ui;margin:16px;background:#fff;color:#222}} td,th{{border:1px solid #ddd;padding:6px;vertical-align:top}} table{{border-collapse:collapse}} audio{{width:190px}}
@media (prefers-color-scheme:dark){{body{{background:#1c1c1e;color:#eee}} td,th{{border-color:#444}}}}</style>
<h2>Undead: processing variants</h2><table><tr><th>voice</th><th>h3 (dry)</th>{''.join('<th>'+html.escape(n)+'</th>' for n in PRESETS)}</tr>{rows}</table>""")
print("Listen: out_allv/undead.html")
