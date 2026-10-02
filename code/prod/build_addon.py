"""Build the addon: out/meta.jsonl + out/sounds → code/addon/UAVoiceTTS (Index.lua + Sounds/), the release zip, and copy it into the game's AddOns folder.
Rows from out/base.jsonl (previous release, see make_base.py) stay unless the quest part was re-voiced in out/meta.jsonl.
python build_addon.py   (any environment)"""
import os, json, shutil, zipfile
HERE = os.path.dirname(os.path.abspath(__file__)); ADD = os.environ.get("ADDON_DIR") or os.path.join(os.path.dirname(HERE), "addon", "UAVoiceTTS")
ZIP = os.environ.get("ZIP_OUT") or os.path.join(os.path.dirname(os.path.dirname(HERE)), "UAVoiceTTS.zip")
GAME = os.environ.get("ADDONS", "/Applications/World of Warcraft/_classic_beta_/Interface/AddOns")
def read_jsonl(path):
    rows = []
    for l in open(path, encoding="utf-8"):
        try: rows.append(json.loads(l))
        except ValueError: pass                      # half-written last line while synth.py is running
    return rows
meta = read_jsonl(os.path.join(HERE, "out", "meta.jsonl"))
BASE = os.path.join(HERE, "out", "base.jsonl")
base = read_jsonl(BASE) if os.path.exists(BASE) else []
fresh = {(m["quest"], m["part"], m["sex"]) for m in meta}
scheme = lambda sex: "x" if sex == "x" else "mf"                      # single version or by player sex
fresh_scheme = {(m["quest"], m["part"]): scheme(m["sex"]) for m in meta}
old = [b for b in base if (b["quest"], b["part"], b["sex"]) not in fresh                       # not re-voiced yet (a missing m/f twin keeps its old file)
       and fresh_scheme.get((b["quest"], b["part"]), scheme(b["sex"])) == scheme(b["sex"])     # and the variant scheme did not change
       and os.path.exists(os.path.join(ADD, "Sounds", b["file"]))]
print(f"re-voiced: {len(meta)} files; kept from previous build: {len(old)} files")
titles = {b["quest"]: b["title"] for b in base if b.get("title")}
titles.update({j["quest"]: j["title"] for j in map(json.loads, open(os.path.join(HERE, "jobs.jsonl"), encoding="utf-8")) if j.get("title")})
os.makedirs(os.path.join(ADD, "Sounds"), exist_ok=True)
idx = {}
for m in meta:
    shutil.copy2(os.path.join(HERE, "out", "sounds", m["file"]), os.path.join(ADD, "Sounds", m["file"]))
for m in meta + old:
    idx.setdefault(m["quest"], {}).setdefault("a" if m["part"] == "accept" else "c", {})[m["sex"]] = m
def lua(s): return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'
lines = ["-- Auto-generated: code/prod/build_addon.py. [questID] = { a = accept, c = turn-in; x — single version, m/f — by player sex }", "UAVoiceTTS_Index = {"]
for q in sorted(idx):
    parts = []
    for p, vs in sorted(idx[q].items()):
        vv = ", ".join(f"{s} = {{ f = {lua(m['file'])}, d = {m['dur']}, c = {{ " + ", ".join(f"{{ {t}, {lua(x)} }}" for t, x in m["cues"]) + " } }"
                       for s, m in sorted(vs.items()))
        parts.append(f"{p} = {{ {vv} }}")
    if q in titles: parts.insert(0, f"t = {lua(titles[q])}")
    lines.append(f"    [{q}] = {{ {', '.join(parts)} }},")
lines.append("}")
open(os.path.join(ADD, "Index.lua"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
allrows = meta + old
print(f"quests {len(idx)}, files {len(allrows)}, sound size {sum(os.path.getsize(os.path.join(ADD,'Sounds',m['file'])) for m in allrows)/1e6:.0f} MB")
with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as z:      # only files that Index.lua references
    for f in ("UAVoiceTTS.toc", "UAVoiceTTS.lua", "Index.lua"): z.write(os.path.join(ADD, f), "UAVoiceTTS/" + f)
    for m in allrows: z.write(os.path.join(ADD, "Sounds", m["file"]), "UAVoiceTTS/Sounds/" + m["file"], compress_type=zipfile.ZIP_STORED)
print("zip:", ZIP, f"{os.path.getsize(ZIP)/1e6:.0f} MB")
if os.path.isdir(GAME):
    dst = os.path.join(GAME, "UAVoiceTTS")
    shutil.copytree(ADD, dst, dirs_exist_ok=True); print("installed into the game:", dst)
