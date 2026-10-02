"""In-game reports: reads the UAVoiceTTS addon's SavedVariables and shows them.
python reports.py            — list reports
python reports.py --apply    — add stressed words (впОрався) to stress_dict.txt and show the re-voicing command
Other players' reports from Discord: copy the channel messages into prod/reports_in.txt (or a channel export into prod/discord/)."""
import os, re, sys, glob
HERE = os.path.dirname(os.path.abspath(__file__))
WTF = os.environ.get("WTF", "/Applications/World of Warcraft/_classic_beta_/WTF")
os.makedirs(os.path.join(HERE, "discord"), exist_ok=True)
VOW = "аеєиіїоуюяАЕЄИІЇОУЮЯ"
def from_saved():
    out = []
    for f in glob.glob(os.path.join(WTF, "Account", "*", "SavedVariables", "UAVoiceTTS.lua")):
        s = open(f, encoding="utf-8").read()
        for b in re.findall(r"\{([^{}]*\[\"reason\"\][^{}]*)\}", s):
            r = dict(re.findall(r'\["(\w+)"\]\s*=\s*"?((?:[^"\\]|\\.)*?)"?\s*,', b + ","))
            out.append(r)
    return out
def from_lines():
    """Reports from Discord: any text (copied from the channel or a DiscordChatExporter export) in prod/reports_in.txt
    or in files prod/discord/*.txt|*.json|*.csv. Looks for lines «UAV#1;quest;part;sex;file;reason;word;comment;sentence»."""
    files = [os.path.join(HERE, "reports_in.txt")] + glob.glob(os.path.join(HERE, "discord", "*"))
    out, seen = [], set()
    for p in files:
        if not os.path.isfile(p): continue
        for m in re.finditer(r"UAV#1;([^\n\r\"]*)", open(p, encoding="utf-8", errors="ignore").read()):
            f = (m.group(1).split(";") + [""] * 8)[:8]
            key = tuple(f[:7])
            if key in seen: continue                      # the same report may have been pasted several times
            seen.add(key)
            out.append({"q": f[0], "p": f[1], "sex": f[2], "s": f[3], "reason": f[4], "word": f[5], "note": f[6], "line": f[7], "src": "discord"})
        # old format UAV|…
        for l in open(p, encoding="utf-8", errors="ignore"):
            parts = l.strip().split("|")
            if len(parts) >= 7 and parts[0] == "UAV":
                out.append({"q": parts[1], "p": parts[2], "s": parts[3], "reason": parts[4], "word": parts[5], "note": parts[6], "src": "discord"})
    return out
def stressed(word):
    """впОрався → впо́рався (a single uppercase vowel mid-word = stress)"""
    w = word.strip()
    caps = [i for i, ch in enumerate(w) if ch in VOW and ch.isupper() and i > 0]
    if len(caps) != 1: return None
    i = caps[0]; return (w[:i] + w[i].lower() + "́" + w[i + 1:]).lower()
reps = from_saved() + from_lines()
if not reps: print("no reports (SavedVariables is written on game exit or /reload)"); sys.exit()
add, redo = [], set()
for r in reps:
    print(f"quest {r.get('q')} {'accept' if r.get('p') == 'a' else 'turn-in'} [{r.get('s')}] — {r.get('reason')}: {r.get('word') or ''} {('· ' + r['note']) if r.get('note') else ''}"
          + (f"\n    «{r['line']}»" if r.get("line") else ""))
    redo.add((r.get("s") or "").replace(".ogg", ""))
    if r.get("reason") == "наголос" and r.get("word") and stressed(r["word"]): add.append(stressed(r["word"]))
if "--apply" in sys.argv:
    p = os.path.join(HERE, "stress_dict.txt"); have = set(l.split("#")[0].strip() for l in open(p, encoding="utf-8"))
    new = [w for w in dict.fromkeys(add) if w not in have]
    if new:
        cur = open(p, encoding="utf-8").read()
        open(p, "a", encoding="utf-8").write(("" if cur.endswith("\n") else "\n") + "\n".join(new) + "\n")
    print(f"\nadded to dictionary: {', '.join(new) or 'nothing new'}")
    # new (not yet processed) reports → re-voicing queue redo_queue.txt; synth.py will pick it up and clear it
    dp, qp = os.path.join(HERE, "reports_done.txt"), os.path.join(HERE, "redo_queue.txt")
    done = set(open(dp, encoding="utf-8").read().splitlines()) if os.path.exists(dp) else set()
    fresh = {}
    for x in reps:
        k = "|".join(str(x.get(f, "")) for f in ("q", "p", "s", "reason", "word", "note", "time"))
        if k not in done and x.get("s"): fresh[k] = x["s"].replace(".ogg", "")
    if fresh:
        q = set(open(qp, encoding="utf-8").read().split()) if os.path.exists(qp) else set()
        open(qp, "w", encoding="utf-8").write("\n".join(sorted(q | set(fresh.values()))) + "\n")
        open(dp, "a", encoding="utf-8").write("\n".join(fresh) + "\n")
    print(f"new reports: {len(fresh)} → queued for re-voicing: {', '.join(sorted(set(fresh.values()))) or '—'}")
