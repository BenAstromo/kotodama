"""Marks reach only their own word, and marked loanwords join gradually
everywhere (2026-10-27 bug round). Plain Python, no Anki or PyQt: the
add-on's real analysis on an empty deck with the loanword button's marks in
a temporary overrides file. Run from anywhere:
    python -X utf8 tools/dev/maint/t_marks.py
"""
import os, sys, tempfile, time, types

ADDONS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))


class _Any:
    def __init__(s, *a, **k): pass
    def __getattr__(s, n): return _Any()
    def __call__(s, *a, **k): return _Any()
    def __or__(s, o): return s


aqt = types.ModuleType("aqt"); aqt.mw = _Any(); aqt.gui_hooks = _Any()
qt = types.ModuleType("aqt.qt")
for n in ["QAction", "QMenu", "QObject", "QDialog", "QWidget", "QGroupBox", "QColor", "pyqtSignal", "QFont", "QStyledItemDelegate", "QLabel"]:
    setattr(qt, n, _Any)
qt.__all__ = [n for n in dir(qt) if n[0] == "Q" or n == "pyqtSignal"]
utils = types.ModuleType("aqt.utils"); utils.showWarning = print; utils.tooltip = print
anki = types.ModuleType("anki"); anki_utils = types.ModuleType("anki.utils")
anki_utils.ids2str = lambda ids: "(" + ",".join(str(i) for i in ids) + ")"
sys.modules.update({"aqt": aqt, "aqt.qt": qt, "aqt.utils": utils, "anki": anki, "anki.utils": anki_utils})
sys.path.insert(0, ADDONS)
import jlpt_progress as jp
from jlpt_progress import jlpt_data, freq_data, card_state, history
from jlpt_progress.overrides import Overrides

fails = []


def check(name, ok, detail=""):
    print(("ok   " if ok else "FAIL ") + name + ("" if ok else f"  {detail}"))
    if not ok:
        fails.append(name)


lists = jlpt_data.build_lists({})
ur = jp._build_unique_readings(lists)
ents = freq_data.load()

# The loanword button's marks (empty deck: every list word it would mark).
pairs, seen = [], set()
for lvl in jlpt_data.LEVELS:
    for d, r in lists.get(lvl, []):
        if (d, r) not in seen and jlpt_data.is_english_loanword(d, r):
            seen.add((d, r)); pairs.append((d, r))
seen2 = {(d, freq_data._kata_to_hira(r)) for d, r in pairs}
for d, r, _p, _f in ents:
    key = (d, freq_data._kata_to_hira(r))
    if key not in seen2 and freq_data.is_english_loanword(d, r):
        seen2.add(key); pairs.append((d, r))
ov = Overrides(os.path.join(tempfile.mkdtemp(), "overrides.json"))
ov.add_found_many(pairs)


def analysis():
    return jp.analyse({}, {}, {}, {}, lists, ur, overrides=ov)


# 1. Only the button pressed: every marked word is a loanword ("6 words
#    marked found" came from ガン reaching がん, タイ reaching 鯛 …).
keys = card_state._found_keys(analysis())
hand = [k for k, v in keys.items() if not v[0]]
check("button marks are all loanwords", not hand, [ents[k[1]][:2] for k in hand if k[0] == "row"][:10])

# 2. A katakana mark never reaches a row that isn't katakana.
leaks = [(p, ents[rk][:2]) for p in pairs for rk in freq_data.mark_ranks([p])
         if not freq_data._is_katakana(ents[rk][0])]
check("katakana marks stay on katakana rows", not leaks, leaks[:10])

# 3. Kana words find their own row, not a homophone or a side form.
for (d, r), want in [(("ほうき", "ほうき"), "ほうき"), (("やかん", "やかん"), "やかん"),
                     (("はし", "はし"), "箸"), (("街", "まち"), "街"), (("捕える", "とらえる"), "捕らえる"),
                     (("せっけん", "せっけん"), "石鹸"), (("リポート", "リポート"), "レポート")]:
    rk = freq_data.word_rank(d, r, jlpt_data.alt_forms(d, r))
    check(f"{d} → {want}", rk is not None and ents[rk - 1][0] == want, rk and ents[rk - 1][:2])
for d, r in [("じゃ", "じゃ"), ("だけ", "だけ"), ("と", "と"), ("なんか", "なんか"), ("すり", "すり")]:
    rk = freq_data.word_rank(d, r, jlpt_data.alt_forms(d, r))
    check(f"{d} has no unrelated row", rk is None, rk and ents[rk - 1][:2])

# 3b. A kana-only card reaches only a tile spelled that way, or a kanji tile
#     of a word usually written in kana (owner 2026-10-27: と was 都, ねこ 猫).
kana_cards = ["と", "ねこ", "かぎ", "もの", "いう", "きょう", "そう"]
cov = freq_data.coverage({i: w for i, w in enumerate(kana_cards, 1)}, {})
landed = {}
for rank, disp, rd, nid in cov["entries"]:
    if nid:
        landed.setdefault(kana_cards[nid - 1], disp)
for w, want in [("と", None), ("ねこ", None), ("かぎ", None), ("もの", "物"), ("いう", "言う"),
                ("きょう", "今日"), ("そう", "そう")]:
    check(f"kana card {w} → {want}", landed.get(w) == want, landed.get(w))

# 4. Gradual loanwords: 332 studied cards → only the counted ones on the rank
# and frequency bars; the JLPT bars keep every marked one (2026-11-09).
card_state.mw.col = types.SimpleNamespace(find_notes=lambda q: list(range(332)))
res = analysis()
jl_all = sum(len(res[l]["known_words"]) for l in jlpt_data.LEVELS)
card_state.hold_back_loans(res, "deck", False, lists)
card_state.hold_back_loans(res, "deck", False, lists)          # must change nothing
parts = card_state.found_parts(res)
n = card_state.loans_counted(332, parts["loans"])
jl = sum(len(res[l]["known_words"]) for l in jlpt_data.LEVELS)
check("full marked list kept after holding back", len(parts["loans"]) == len(keys) - len(hand))
check("JLPT bars keep every marked loanword", jl == jl_all and jl > n, (jl, jl_all, n))
check("no JLPT words held back", not res["loans_waiting"]["pairs"])
check("frequency bar counts at most the counted loanwords", dict(res["frequency"]["tiers"])[20000] <= n)

# 5. History: on the JLPT line every marked loanword counts from day one.
DAYS, PER = 30, 12
now = time.time()
card_nid, revlog, cid = {}, [], 1
for d in range(DAYS):
    ts = now - (DAYS - 1 - d) * 86400
    for k in range(PER):
        card_nid[cid] = int((ts - 1000) * 1000) + k
        revlog.append((cid, int(ts * 1000) + k, 0, 1))
        cid += 1


class DB:
    def all(self, sql, *a):
        if sql.startswith("select id, nid from cards"):
            return list(card_nid.items())
        if sql.startswith("select cid, id, type, ivl from revlog"):
            return revlog
        return []


col = types.SimpleNamespace(find_cards=lambda q: list(card_nid),
                            find_notes=lambda q: list(set(card_nid.values())), db=DB())
card_state.mw.col = history.mw.col = col
history._rollover_hour = lambda: 4
res = analysis()
card_state.hold_back_loans(res, "deck", False, lists)
v = history.rebuild(res, "deck", False)["values"]
today_jl = sum(len(res[l]["known_words"]) for l in jlpt_data.LEVELS)
check("history ends at today's JLPT count", v["jlpt"][-1] == today_jl, (v["jlpt"][-1], today_jl))
check("history ends at today's top-20k count",
      v["f20000"][-1] == dict(res["frequency"]["tiers"])[20000])
check("JLPT loanwords count from day one", v["jlpt"][0] >= card_state.jlpt_loans(res) > 0,
      (v["jlpt"][0], card_state.jlpt_loans(res)))
check("history never drops without resets", all(a <= b for a, b in zip(v["jlpt"], v["jlpt"][1:])))

print("\nall passed" if not fails else f"\n{len(fails)} failed")
sys.exit(1 if fails else 0)
