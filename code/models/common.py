"""Shared across all models: voice list (refs_all/), selection of 18 voices, quest texts."""
import json, os, re
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # tts_local/
VARIANT = os.environ.get("VARIANT", "")            # "", "tight", "sent", "tight_sent"
REF_LANG = os.environ.get("REF_LANG", "ru")        # ru | en — language of the client's voiceover the reference was taken from
REFS = os.path.join(HERE, ("refs_long" if "long" in VARIANT else "refs_tight" if "tight" in VARIANT else "refs_all") + ("_en" if REF_LANG == "en" else ""))
SENT = "sent" in VARIANT
def split_sentences(t): return [x for x in re.split(r"(?<=[.!?…])\s+", t) if x.strip()]
RACES = ["nightelf", "human", "dwarf", "gnome", "goblin", "orc", "undead", "tauren", "troll", "skyborne"]

def parse(name):
    for r in RACES:
        m = re.match(rf"{r}(female|male)(.*?)npc\d*$", name)
        if m: return r, m.group(1), m.group(2) or "standard"

def all_sets():
    out = []
    for f in sorted(os.listdir(REFS)):
        if f.endswith(".wav") and parse(f[:-4]):
            out.append((f[:-4],) + parse(f[:-4]))
    return out

def choose(args):
    sets = all_sets()
    if "--all" in args: return sets
    words = [a for a in args if not a.startswith("--")]
    if words: return [s for s in sets if any(w in s[0] for w in words)]
    chosen, seen = [], set()   # one per race+sex: standard, otherwise first alphabetically
    for s in sorted(sets, key=lambda s: (s[1], s[2], s[3] != "standard", s[3])):
        if (s[1], s[2]) not in seen:
            seen.add((s[1], s[2])); chosen.append(s)
    return chosen

_tests = None
def text_for(race, sex):
    global _tests
    if _tests is None:
        _tests = {(t["race"], t["sex"]): t for t in json.load(open(os.path.join(HERE, "tests_all.json"), encoding="utf-8"))}
    other = "female" if sex == "male" else "male"
    return _tests.get((race, sex)) or _tests.get((race, other)) or _tests[("human", sex)]

def ref_wav(name): return os.path.join(REFS, name + ".wav")
def ref_text(name):
    p = os.path.join(REFS, name + ".txt")
    return open(p, encoding="utf-8").read().strip() if os.path.exists(p) else None
def out_dir(model):
    tags = [t for t in (VARIANT, "en" if REF_LANG == "en" else "") if t]
    d = os.path.join(HERE, "out_models", "_".join([model] + tags)); os.makedirs(d, exist_ok=True); return d
