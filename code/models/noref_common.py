"""No audio reference: the voice is defined by a description. Per race/sex descriptions are my rough guess at each race's character."""
# OmniVoice voice design: gender / age / pitch (trained on Chinese and English — may be unstable for Ukrainian)
DESIGN = {
    ("human", "male"): "male, middle-aged, moderate pitch",   ("human", "female"): "female, young adult, moderate pitch",
    ("dwarf", "male"): "male, elderly, low pitch",            ("dwarf", "female"): "female, middle-aged, low pitch",
    ("gnome", "male"): "male, young adult, high pitch",       ("gnome", "female"): "female, young adult, very high pitch",
    ("nightelf", "male"): "male, middle-aged, low pitch",     ("nightelf", "female"): "female, young adult, moderate pitch",
    ("orc", "male"): "male, middle-aged, very low pitch",     ("orc", "female"): "female, middle-aged, low pitch",
    ("undead", "male"): "male, elderly, low pitch",           ("undead", "female"): "female, middle-aged, low pitch",
    ("tauren", "male"): "male, elderly, very low pitch",      ("tauren", "female"): "female, middle-aged, low pitch",
    ("troll", "male"): "male, young adult, low pitch",        ("troll", "female"): "female, young adult, moderate pitch",
    ("goblin", "male"): "male, middle-aged, high pitch",      ("goblin", "female"): "female, young adult, high pitch",
}
# Higgs: without a reference the voice is random; we only set pitch via a prosody token and fix the seed so the voice is reproducible
def higgs_prefix(race, sex):
    d = DESIGN[(race, sex)]
    if "very low" in d or "low pitch" in d: return "<|prosody:pitch_low|>"
    if "high pitch" in d: return "<|prosody:pitch_high|>"
    return ""
