"""Duplicate-card finder (2026-10-27): which notes count as one word.
Plain Python, no Anki or PyQt: the add-on's real analysis on a made-up
deck. Run from anywhere:
    python -X utf8 tools/dev/maint/t_dups.py
"""
import os, sys, types

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
from jlpt_progress import jlpt_data, card_state

fails = []


def check(name, ok, detail=""):
    print(("ok   " if ok else "FAIL ") + name + ("" if ok else f"  {detail}"))
    if not ok:
        fails.append(name)


lists = jlpt_data.build_lists({})
ur = jp._build_unique_readings(lists)
sentence = card_state.pseudo_nid(1_700_000_000_000, 0)
deck = {1: ("うるさい", "うるさい"), 2: ("煩い", "うるさい"), 3: ("聞く", "きく"),
        5: ("できる", "できる"), 6: ("出来る", "できる"), 7: ("ねこ", "ねこ"), 8: ("猫", "ねこ"),
        9: ("会う", "あう"), 10: ("遭う", "あう"), 11: ("汚れ", "よごれ"), 12: ("汚れ", "けがれ"),
        13: ("スマホ", ""), sentence: ("話す", "はなす"), 14: ("話す", "はなす"),
        15: ("いる", "いる"), 16: ("要る", "いる")}
di, ri, nd, nr = {}, {}, {}, {}
for nid, (d, r) in deck.items():
    di.setdefault(jp._norm(d), []).append(nid)
    for p in jp._reading_parts(jp._norm(r)):
        ri.setdefault(p, []).append(nid)
    nd[nid] = d
    if r:
        nr[nid] = r
# 4 is a second 聞く note (collect_words drops it from the index, keeps it here).
res = jp.analyse(di, ri, nd, nr, lists, ur, exact_duplicates={3: [3, 4]})
groups = [set(g) for g in res["duplicates"]]
print("groups:", [[deck.get(n, ("聞く",))[0] for n in g] for g in res["duplicates"]])

check("exact copies (聞く ×2)", {3, 4} in groups)
check("kana word + kanji card (うるさい / 煩い)", {1, 2} in groups)
check("できる / 出来る", {5, 6} in groups)
check("kana card ≠ kanji word (ねこ / 猫)", not any({7, 8} <= g for g in groups))
check("different kanji ≠ one word (会う / 遭う)", not any({9, 10} <= g for g in groups))
check("different reading ≠ one word (汚れ よごれ / けがれ)", not any({11, 12} <= g for g in groups))
check("a sentence card's word is no duplicate", not any(sentence in g for g in groups))
check("いる ≠ 要る (one kana entry lists both)", not any({15, 16} <= g for g in groups))
check("nothing else", len(groups) == 3, groups)

print("\nall passed" if not fails else f"\n{len(fails)} failed")
sys.exit(1 if fails else 0)
