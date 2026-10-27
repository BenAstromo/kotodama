"""Word-split test for the Text Check (2026-10-17). Run after any change to
sentence_parser / text_check:

    python -I -X utf8 tools/vocab_eval.py            # report + failures + differences
    python -I -X utf8 tools/vocab_eval.py --update   # accept the current output as baseline

tools/vocab_cases.json: [sentence, gold] pairs, hand-checked (first 150:
Tatoeba, seed 20261030, 18–60 characters, drawn by
tools/accuracy/make_vocab_sample.py). It measures exactly what the Text
Check counts (text_check.piece_items): the words, and the runs no list word
covers.

Gold items, space-separated:
    word        a word that must be counted. Matches the parser's word when
                it is its display, one of its spellings, or (kana) its
                reading; "word:reading" also needs that reading.
    ~word       optional: fine either way (auxiliaries after て, light する,
                particle-like verbs in について, いる, ない …)
    a|b         either is right; "a+b" inside means both words
    ?text       a run that should be unrecognised (a word our lists lack)
    ~?text      unrecognised or absent, both fine (names)
Runs of katakana only are never scored (names, loanwords off the lists).

Scores: word recall (required words found), word precision (counted words
that are right), unexpected unrecognised runs (each lowers coverage by
mistake), sentences fully right.
"""
import json, os, sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(HERE, "gemini_grammar_review", "verdicts", "gem_head.py"), encoding="utf-8").read())
HERE = os.path.dirname(os.path.abspath(__file__))
sp = __import__("jlpt_progress.sentence_parser", fromlist=["x"])
tc = __import__("jlpt_progress.text_check", fromlist=["x"])
jd = __import__("jlpt_progress.jlpt_data", fromlist=["x"])

CASES = os.path.join(HERE, "vocab_cases.json")
BASE = os.path.join(HERE, "vocab_eval_baseline.json")
if "--cases" in sys.argv:          # score another gold file (a fresh sample), no baseline
    CASES = sys.argv[sys.argv.index("--cases") + 1]
    BASE = os.devnull + ".none"


def hira(s):
    return sp._hira(s)


_SPELL = {}


def spellings(d, r):
    k = (d, r)
    if k not in _SPELL:
        s = {d}
        try:
            s.update(jd.same_kanji_forms(d, r))
            s.update(jd.alt_forms(d, r))
        except Exception:
            pass
        s.update(sp._other_spellings(d, r))
        _SPELL[k] = s
    return _SPELL[k]


def word_match(g, item):
    if item[0] != "word":
        return False
    w, _, rd = g.partition(":")
    d, r = item[1], item[2]
    if rd and hira(rd) != hira(r):
        return False
    if w == d or w in spellings(d, r):
        return True
    return not sp._has_kanji(w) and hira(w) == hira(r) and not sp._has_kanji(w)


def is_kata(s):
    return all(0x30A0 <= ord(c) <= 0x30FF for c in s)


def parse_gold(gold):
    """[(optional, [option, …])], option = [atom, …], atom = word or ?text."""
    out = []
    for item in gold.split():
        opt = item.startswith("~")
        alts = [a.lstrip("~") for a in item.split("|")]
        out.append((opt, [a.split("+") for a in alts]))
    return out


def atom_match(a, item):
    if a.startswith("?"):
        return item[0] == "unrec" and item[1] == a[1:]
    return word_match(a, item)


def score(text, gold):
    """(required n, required found, counted n, counted right, unexpected
    unrec list, missed list, wrong list)."""
    items = [it for it in tc.piece_items(sp.tokens(text))]
    items = [it for it in items if not (it[0] == "unrec" and is_kata(it[1]))]
    left = list(items)
    req = found = 0
    missed = []
    entries = parse_gold(gold)
    # required items first, then optional ones
    for pass_opt in (False, True):
        for opt, options in entries:
            if opt != pass_opt:
                continue
            words_only = all(not a.startswith("?") for o in options for a in o)
            if not opt and words_only:
                req += 1
            hit = None
            for o in options:
                idx = []
                pool = list(range(len(left)))
                for a in o:
                    j = next((j for j in pool if atom_match(a, left[j]) and j not in idx), None)
                    if j is None:
                        idx = None
                        break
                    idx.append(j)
                if idx is not None:
                    hit = idx
                    break
            if hit is not None:
                if not opt and words_only:
                    found += 1
                for j in sorted(hit, reverse=True):
                    left.pop(j)
            elif not opt:
                missed.append("|".join("+".join(o) for o in options))
    counted = sum(1 for it in items if it[0] == "word")
    wrong = [f"{it[1]}:{it[2]}" for it in left if it[0] == "word"]
    unexpected = [it[1] for it in left if it[0] == "unrec"]
    return req, found, counted, counted - len(wrong), unexpected, missed, wrong


def wilson(k, n, z=1.96):
    if not n:
        return (0, 0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    m = z * ((p * (1 - p) + z * z / (4 * n)) / n) ** 0.5
    return ((c - m) / d, (c + m) / d)


def main():
    cases = json.load(open(CASES, encoding="utf-8"))
    tot = [0, 0, 0, 0, 0]
    perfect = 0
    fails = []
    current = {}
    for text, gold in cases:
        req, found, counted, right, unexp, missed, wrong = score(text, gold)
        tot[0] += req; tot[1] += found; tot[2] += counted; tot[3] += right; tot[4] += len(unexp)
        ok = not (unexp or missed or wrong)
        perfect += ok
        if not ok:
            fails.append((text, missed, wrong, unexp))
        current[text] = [f"{it[1]}:{it[2]}" if it[0] == "word" else "?" + it[1]
                         for it in tc.piece_items(sp.tokens(text))]
    print(f"Sentences: {len(cases)}, fully right {perfect} ({perfect / len(cases):.0%})")
    lo, hi = wilson(tot[1], tot[0])
    print(f"Word recall    {tot[1]}/{tot[0]} = {tot[1] / tot[0]:.1%} (95% CI {lo:.0%}–{hi:.0%})")
    lo, hi = wilson(tot[3], tot[2])
    print(f"Word precision {tot[3]}/{tot[2]} = {tot[3] / tot[2]:.1%} (95% CI {lo:.0%}–{hi:.0%})")
    print(f"Unexpected unrecognised runs: {tot[4]} ({tot[4] / max(tot[2], 1) * 100:.1f} per 100 counted words)")
    if "-q" not in sys.argv:
        print("\nFailures (missed / wrong word / unexpected unrecognised):")
        for text, missed, wrong, unexp in fails:
            print(" ", text)
            if missed:
                print("     missed:", " ".join(missed))
            if wrong:
                print("     wrong: ", " ".join(wrong))
            if unexp:
                print("     unrec: ", " ".join(unexp))
    if os.path.exists(BASE):
        base = json.load(open(BASE, encoding="utf-8"))
        diffs = [(t, base.get(t), v) for t, v in current.items() if base.get(t) != v]
        print(f"\nDifferences from the baseline: {len(diffs)}")
        for t, old, new in diffs:
            print(" ", t)
            print("     was:", " ".join(old or []))
            print("     now:", " ".join(new))
    if "--update" in sys.argv:
        json.dump(current, open(BASE, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
        print("baseline updated")


main()
