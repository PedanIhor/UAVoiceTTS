"""One-off: turn an existing addon Index.lua into out/base.jsonl (baseline rows for build_addon.py).
python make_base.py [path/to/Index.lua]   Rows that are not re-voiced stay in the addon as they are."""
import os, re, sys, json
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(HERE), "addon", "UAVoiceTTS", "Index.lua")
TOK = re.compile(r'\s*(?:(?P<s>"(?:[^"\\]|\\.)*")|(?P<n>-?\d+(?:\.\d+)?)|(?P<i>[A-Za-z_]\w*)|(?P<p>[{}\[\]=,]))')
def tokens(src):
    pos = 0
    while pos < len(src):
        m = TOK.match(src, pos)
        if not m: break
        pos = m.end()
        for k in "snip":
            if m.group(k) is not None: yield k, m.group(k); break
def parse(toks):
    k, v = next(toks)
    if k == "s": return re.sub(r'\\(.)', r'\1', v[1:-1])
    if k == "n": return float(v) if "." in v else int(v)
    assert v == "{", v
    arr, d = [], {}
    while True:
        k, v = next(toks)
        if v == "}": return arr if not d else {**d, **({"_arr": arr} if arr else {})}
        if v == ",": continue
        if v == "[":
            _, key = next(toks); next(toks); next(toks); d[int(key)] = parse(toks)      # [N] =
        elif k == "i":
            nk, nv = next(toks)
            if nv == "=": d[v] = parse(toks)
            else: raise SystemExit("bare identifier in table: " + v)
        else:
            toks = _push(toks, (k, v)); arr.append(parse(toks))
def _push(toks, t):
    import itertools; return itertools.chain([t], toks)
src = open(SRC, encoding="utf-8").read()
body = src[src.index("UAVoiceTTS_Index = ") + len("UAVoiceTTS_Index = "):]
idx = parse(tokens(body)); rows = []
for q, e in sorted(idx.items()):
    for p, part in (("a", "accept"), ("c", "complete")):
        for sex, m in (e.get(p) or {}).items():
            rid = f"{q}_{part}" + ("" if sex == "x" else "_" + sex)
            rows.append({"id": rid, "quest": q, "part": part, "sex": sex, "file": m["f"], "dur": m["d"],
                         "cues": [list(c) if isinstance(c, list) else [c[1], c[2]] for c in m["c"]] if isinstance(m["c"], list) else m["c"],
                         "title": e.get("t")})
os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
with open(os.path.join(HERE, "out", "base.jsonl"), "w", encoding="utf-8") as f:
    for r in rows: f.write(json.dumps(r, ensure_ascii=False) + "\n")
print(f"quests {len(idx)}, rows {len(rows)}")
