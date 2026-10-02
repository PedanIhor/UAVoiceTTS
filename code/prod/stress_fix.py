"""Fixes for automatic stress marking (ukrainian_word_stress):
 1) a word with several marks (the dictionary is unsure: захи́снико́м) — strip the marks and let the model decide;
 2) a capitalized word (sentence start) is marked the same as its lowercase form: «Ге́рою» → «Геро́ю»;
 3) the manual dictionary prod/stress_dict.txt (one per line: word with a mark, e.g. впо́рався) — highest priority.
STRESS mode: all — mark everything (with the fixes above); dict — only dictionary words, the rest unmarked."""
import os, re
from stress_common import stressify
A = "́"; HERE = os.path.dirname(os.path.abspath(__file__))
WORD = re.compile(r"[А-Яа-яІіЇїЄєҐґ'’́]+")
VOW = "аеєиіїоуюяАЕЄИІЇОУЮЯ"
def caps_to_acute(w):
    """впОрався → впо́рався: a single uppercase vowel (not the first letter) = stress. Easier for writing the dictionary by hand."""
    if A in w: return w
    caps = [i for i, ch in enumerate(w) if ch in VOW and ch.isupper() and i > 0]
    if len(caps) != 1: return w
    i = caps[0]; return w[:i] + w[i].lower() + A + w[i + 1:]
def load_dict():
    p = os.path.join(HERE, "stress_dict.txt"); d = {}
    if os.path.exists(p):
        for l in open(p, encoding="utf-8"):
            w = caps_to_acute(l.split("#")[0].strip())
            if w and A in w: d[w.replace(A, "").lower()] = w.lower()
    return d
DICT = load_dict(); _low = {}
def _lower_stress(w):
    if w not in _low: _low[w] = stressify(w.lower())
    return _low[w]
def keep_case(src, stressed):
    out, i = [], 0
    for ch in stressed:
        if ch == A: out.append(ch); continue
        out.append(src[i] if i < len(src) else ch); i += 1
    return "".join(out)
def fix_word(w, mode):
    plain = w.replace(A, ""); low = plain.lower()
    if low in DICT: return keep_case(plain, DICT[low])
    if mode == "dict": return plain
    if plain[:1].isupper() and plain[1:].islower() and A in w:
        w = keep_case(plain, _lower_stress(low))
    if w.count(A) > 1: return plain
    return w
def mark(text, mode="all"):
    s = stressify(text) if mode == "all" else text
    return WORD.sub(lambda m: fix_word(m.group(0), mode), s)
