"""Quest voiceover jobs: ClassicUA texts + quest giver/turn-in NPC voices (race-sex).
python build_jobs.py [race ... | zone:zone ...]  (no args — all quests; e.g.: tauren zone:durotar) → prod/jobs.jsonl
Zones come from the Questie database (QuestieDB, zoneOrSort with subzones), list in prod/zones.json.
Parts: accept (description on accept), complete (text on turn-in). If the text contains the player's sex/name/class/race —
two versions (m/f), otherwise one (x). Player name → «герой/героїня», class and race → «мандрівник/мандрівниця» in the proper case."""
import os, re, sys, json
HERE = os.path.dirname(os.path.abspath(__file__)); TL = os.path.dirname(HERE)
CUA = os.environ.get("CUA", "/Applications/World of Warcraft/_classic_beta_/Interface/AddOns/ClassicUA")
NPC = os.environ.get("NPC_VOICES", os.path.join(TL, "data", "npc_voices.json"))   # quest ID -> race/sex of the giver (accept) and turn-in (complete) NPC
# default voice per race-sex (some have no «standard»)
VOICE = {("human", "male"): "humanmalestandardnpc", ("human", "female"): "humanfemalestandardnpc",
         ("dwarf", "male"): "dwarfmalestandardnpc", ("dwarf", "female"): "dwarffemalematernalnpc",
         ("gnome", "male"): "gnomemalestandardnpc", ("gnome", "female"): "gnomefemalestandardnpc",
         ("nightelf", "male"): "nightelfmalestandardnpc", ("nightelf", "female"): "nightelffemalestandardnpc",
         ("orc", "male"): "orcmalestandardnpc", ("orc", "female"): "orcfemalestandardnpc",
         ("troll", "male"): "trollmalestandardnpc", ("troll", "female"): "trollfemalestandardnpc",
         ("tauren", "male"): "taurenmaleeldernpc", ("tauren", "female"): "taurenfemalestandardnpc",
         ("scourge", "male"): "undeadmalestandardnpc", ("scourge", "female"): "undeadfemalestandardnpc",
         ("goblin", "male"): "goblinmalegruffnpc", ("goblin", "female"): "goblinfemalezanynpc",
         ("skyborne", "male"): "skybornemalestandardnpc", ("skyborne", "female"): "nightelffemalestandardnpc",
         ("bloodelf", "male"): "nightelfmalestandardnpc", ("bloodelf", "female"): "nightelffemalestandardnpc"}
CASES = "нрдзомк"
HERO = {"m": dict(zip(CASES, ["герой", "героя", "героєві", "героя", "героєм", "героєві", "герою"])),
        "f": dict(zip(CASES, ["героїня", "героїні", "героїні", "героїню", "героїнею", "героїні", "героїне"]))}
TRAV = {"m": dict(zip(CASES, ["мандрівник", "мандрівника", "мандрівникові", "мандрівника", "мандрівником", "мандрівникові", "мандрівнику"])),
        "f": dict(zip(CASES, ["мандрівниця", "мандрівниці", "мандрівниці", "мандрівницю", "мандрівницею", "мандрівниці", "мандрівнице"]))}
CODE = re.compile(r"\{([^{}:]+)(?::([^{}]*))?\}")
def expand(text, sex):
    def rep(m):
        key, arg = m.group(1), m.group(2)
        if key.lower() == "ім'я" and not arg:            # {ім'я} without a case — almost always direct address («Дякую, {ім'я}.») → vocative
            before, after = text[:m.start()].rstrip()[-1:], text[m.end():m.end() + 1]
            if before in ",.!?—-" or after in ",.!?" or before == "": arg = "к"
        k = key.lower()
        if k == "стать":
            a, _, b = (arg or "").partition(":"); return a if sex == "m" else b
        if k in ("ім'я", "клас", "раса"):
            w = (HERO if k == "ім'я" else TRAV)[sex].get((arg or "н")[:1], (HERO if k == "ім'я" else TRAV)[sex]["н"])
            return w.upper() if key.isupper() else (w[:1].upper() + w[1:] if key[:1].isupper() else w)
        return m.group(0)
    out = CODE.sub(rep, text)
    return re.sub(r"(^|[.!?…]\s+|\n\s*)([a-zа-яіїєґ])", lambda m: m.group(1) + m.group(2).upper(), out)   # capitalize sentence starts
def personal(text): return bool(re.search(r"\{(стать|ім'я|клас|раса)", text, re.I))
def tts_clean(t):
    t = re.sub(r"\s*\n+\s*", " ", t).strip()
    t = t.replace("…", "...").replace("«", "\"").replace("»", "\"")
    return re.sub(r"\s{2,}", " ", t)
def load_ua():
    ua = {}
    for f in ("quest_both.lua", "quest_alliance.lua", "quest_horde.lua"):
        s = open(os.path.join(CUA, "entries", "classic", f), encoding="utf-8").read()
        for m in re.finditer(r'\n\[(\d+)\] = \{ en="((?:[^"\\]|\\.)*)",(.*?)\n\},', s, re.S):
            items = re.findall(r"\[===\[(.*?)\]===\]|(?<![\w])nil(?![\w])", m.group(3), re.S)
            vals = [x if x else None for x in re.findall(r"\[===\[(.*?)\]===\]|\bnil\b", m.group(3), re.S)]
            toks = re.findall(r"(\[===\[.*?\]===\]|\bnil\b)", m.group(3), re.S)
            vals = [None if t == "nil" else t[5:-5] for t in toks]
            ua[int(m.group(1))] = {"en": m.group(2), "title": vals[0] if vals else None, "desc": vals[1] if len(vals) > 1 else None,
                                   "progress": vals[3] if len(vals) > 3 else None, "complete": vals[4] if len(vals) > 4 else None}
    return ua
def load_npc():
    q = json.load(open(NPC, encoding="utf-8"))["quests"]
    return {int(k): {part: tuple(v[part]) for part in ("accept", "complete")} for k, v in q.items()}
if __name__ == "__main__":
    args = sys.argv[1:]; races = {a for a in args if not a.startswith("zone:")}
    ZONES = json.load(open(os.path.join(HERE, "zones.json"))) if any(a.startswith("zone:") for a in args) else {}
    zq = {q for a in args if a.startswith("zone:") for z, qs in ZONES.items() if a[5:] in (z, "all") for q in qs}   # zone:all — all zones from zones.json
    ua, cq = load_ua(), load_npc(); jobs = []; miss = 0
    for q, g in sorted(cq.items()):
        if args and not (g["accept"][0] in races or q in zq): continue
        if q not in ua: miss += 1; continue
        for part, field in (("accept", "desc"), ("complete", "complete")):
            raw = ua[q][field]
            if not raw: continue
            voice = VOICE.get(g[part])
            if not voice: continue
            for sex in (("m", "f") if personal(raw) else ("x",)):
                jobs.append({"id": f"{q}_{part}" + ("" if sex == "x" else "_" + sex), "quest": q, "part": part, "sex": sex,
                             "voice": voice, "title": ua[q]["title"], "text": tts_clean(expand(raw, "m" if sex == "x" else sex))})
    with open(os.path.join(HERE, "jobs.jsonl"), "w", encoding="utf-8") as f:
        for j in jobs: f.write(json.dumps(j, ensure_ascii=False) + "\n")
    from collections import Counter
    print(f"jobs {len(jobs)} (quests skipped without ClassicUA text: {miss}); total characters {sum(len(j['text']) for j in jobs)}")
    print("voices:", Counter(j["voice"] for j in jobs).most_common())
    print("example:", jobs[0]["id"], jobs[0]["voice"], "|", jobs[0]["text"][:200])
