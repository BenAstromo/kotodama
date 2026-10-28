"""Offscreen check of the clickable gains: gained_nids windows, the link
HTML's gold translation, and a QLabel click → Browser search."""
import os, sys, types, datetime
os.environ["QT_QPA_PLATFORM"] = "offscreen"
ADDON = r"C:\Users\benne\AppData\Roaming\Anki2\addons21\jlpt_progress"
from PyQt6 import QtCore, QtGui, QtWidgets
qt = types.ModuleType("aqt.qt")
for m in (QtCore, QtGui, QtWidgets):
    for k in dir(m):
        if not k.startswith("_"): setattr(qt, k, getattr(m, k))
qt.pyqtSignal = QtCore.pyqtSignal
class _Any:
    def __init__(s, *a, **k): pass
    def __getattr__(s, n): return _Any()
    def __call__(s, *a, **k): return _Any()
    def __bool__(s): return False
    def __iter__(s): return iter(())
SEARCHES = []
class _Browser:
    def search_for(self, q): SEARCHES.append(q)
dialogs = types.SimpleNamespace(open=lambda name, mw: _Browser())
aqt = types.ModuleType("aqt"); aqt.qt = qt; aqt.mw = _Any(); aqt.gui_hooks = _Any(); aqt.dialogs = dialogs
TIPS = []
utils = types.ModuleType("aqt.utils"); utils.showWarning = print; utils.tooltip = lambda t, **k: TIPS.append(t); utils.askUser = lambda *a, **k: False
anki = types.ModuleType("anki"); au = types.ModuleType("anki.utils"); au.ids2str = lambda ids: ""
sys.modules.update({"aqt": aqt, "aqt.qt": qt, "aqt.utils": utils, "anki": anki, "anki.utils": au})
pkg = types.ModuleType("jlpt_progress"); pkg.__path__ = [ADDON]; sys.modules["jlpt_progress"] = pkg
pkg._cfg = lambda: {}
app = QtWidgets.QApplication([])
from jlpt_progress import history, history_view, divine_text, card_state

fails = []
def check(name, got, want):
    ok = got == want
    print(("ok  " if ok else "FAIL"), name, got, "" if ok else f"(want {want})")
    if not ok: fails.append(name)

d0 = datetime.date(2026, 9, 1)
days = [d0 + datetime.timedelta(days=i) for i in range(51)]      # last = index 50
pseudo = card_state.PSEUDO_BASE + 7
series = {"days": days,
          "gains": {"rank": list(range(51))},
          "gained": {"rank": [(50, 1, None), (49, 2, None), (44, 3, None), (43, 4, None),
                              (21, 5, None), (20, 6, None), (50, None, None)],
                     "kanji": [(50, 10, "日"), (50, 11, "鬱")],
                     "N5": [(50, pseudo, None), (50, pseudo + 1, None)]}}
check("today", history.gained_nids(series, "rank", 0), [1])
check("week = last 7 days (44..50)", history.gained_nids(series, "rank", 7), [1, 2, 3])
check("delta(7) agrees", history.delta(series, "rank", 7), 7)
check("month (21..50)", history.gained_nids(series, "rank", 30), [1, 2, 3, 4, 5])
check("keep filter", history.gained_nids(series, "kanji", 0, lambda x: x == "日"), [10])
check("sentence words → one note", history.gained_nids(series, "N5", 0), [pseudo // 1000])
check("missing key", history.gained_nids(series, "grammar", 7), [])

html = history_view.delta_html(series, "rank", "#ff5c8a")
print(html)
divine_text_ja = divine_text.translate(html) if hasattr(divine_text, "translate") else None
print("gold:", divine_text_ja)
check("gold has 今週/今月", bool(divine_text_ja) and "今週" in divine_text_ja and "今月" in divine_text_ja
      and "this" not in divine_text_ja, True)
today = "Today: " + " · ".join(history_view.gain_link(f"today:{k}", f"<b>{n}</b> / {p} {u}", "#ffffff")
                               for k, n, p, u in (("vocab", 3, 12, "words"), ("kanji", 0, 1, "kanji"),
                                                  ("grammar", 0, 1, "grammar point")))
ja = divine_text.translate(today)
print("gold today:", ja)
import re
visible = re.sub(r"<[^>]+>", "", ja)
check("gold today translated", "今日" in visible and "words" not in visible and "grammar" not in visible, True)

lbl = history_view.delta_label(series, "rank", "#ff5c8a", "x")
lbl.linkActivated.emit("gain:rank:30")
check("click month → Browser", SEARCHES[-1], "nid:1,2,3,4,5")
lbl.linkActivated.emit("gain:kanji:30")
check("click empty-ish", SEARCHES[-1], "nid:10,11")
history_view.open_gained(series, [("grammar", None)], 7)
check("nothing → tooltip", bool(TIPS), True)
history_view.open_gained(series, [("rank", None), ("kanji", None)], 0)
check("parts merged", SEARCHES[-1], "nid:1,10,11")

lbl.resize(400, 30)
img = lbl.grab().toImage()
blue = sum(1 for x in range(img.width()) for y in range(img.height())
           if (lambda c: c.blue() > 150 and c.red() < 90 and c.green() < 140)(img.pixelColor(x, y)))
check("no default blue link colour", blue, 0)
# every +N hover: what it's made of (owner 2026-10-28: "+35 today", 30 cards)
ls = {"days": days[:3], "gains": {"rank": [0, 5, 40]},
      "gained": {"rank": [(2, n, None) for n in range(30)] + [(1, 99, None)] * 5}}
check("parts: 30 cards + 5 loanwords today", history.gain_parts(ls, "rank", 1), (35, 30, 5))
tip = history_view.gain_tip(history.gain_parts(ls, "rank", 1), 1)
check("tip names both", tip.splitlines()[0],
      "+35 today: 30 learned from cards, 5 marked English loanwords joined.")
check("tip, cards only", history_view.gain_tip((3, 3, 0), 7).splitlines()[0], "+3 this week: 3 learned from cards.")
check("tip, a reset card", history_view.gain_tip((2, 3, 0), 30).splitlines()[0],
      "+2 this month: 3 learned from cards, 1 lost (cards reset to new).")
lbl2 = history_view.delta_label(ls, "rank", "#ff5c8a", "x")
lbl2.linkHovered.emit("gain:rank:1")
check("hover sets it", lbl2.toolTip().splitlines()[0], "+35 today: 30 learned from cards, 5 marked English loanwords joined.")
lbl2.linkHovered.emit("")
check("off the number: the label's own tip", lbl2.toolTip().startswith("Change in x"), True)
print("FAILS:", fails or "none")
