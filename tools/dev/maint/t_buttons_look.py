"""Button-column look regression (2026-11-10, _ButtonColumn): renders the
tables with a button per row (Marked & Suspended: found / suspended
Revert; kanji / grammar Missing ★ Found and Marked Revert), normal and gold,
so the widget buttons and the painted ones can be compared pixel by pixel
with t_tiles_look.py compare. Also checks the painted buttons' clicks.

    %TEMP%\\qtv\\Scripts\\python.exe -X utf8 t_buttons_look.py <dir>

Run once with KT_SRC=<old copy> and once on the add-on, then compare.
"""
import os, sys, time
OUT = os.path.abspath(sys.argv[1])
os.makedirs(OUT, exist_ok=True)
os.environ["KT_ENV"] = os.path.join(OUT, "_env", "addons21")
os.environ["QT_QPA_FONTDIR"] = r"C:\Windows\Fonts"
import stubenv as E
import mkcol
from PyQt6 import QtCore, QtGui, QtWidgets
Qt = QtCore.Qt

WORDS = [("食べる", "たべる", (2, 2, 30)), ("水", "みず", (2, 2, 5)), ("学校", "がっこう", (1, 1, 0)),
         ("先生", "せんせい", (0, 0, 0)), ("天気", "てんき", (2, -1, 40)), ("テレビ", "テレビ", (3, 3, 2))]
SENTS = ["私は毎日学校に行きます。", "昨日は雨が降ったので、家で本を読みました。"]
nts = {"Vocab": ["Word", "Reading", "Sentence"], "SentOnly": ["Sentence"]}
notes = [("Main", "Vocab", {"Word": w, "Reading": r, "Sentence": SENTS[i % 2]}, c)
         for i, (w, r, c) in enumerate(WORDS)]
notes += [("Main", "SentOnly", {"Sentence": s}, (2, 2, 25)) for s in SENTS]
E.mw.col = mkcol.Col(nts, ["Main"], notes)
E.CFG.update(deck_name="Main", field_mappings=[
    {"note_type": "Vocab", "field": "Word", "reading_field": "Reading", "sentence_field": "Sentence"},
    {"note_type": "SentOnly", "field": "", "reading_field": "", "sentence_field": "Sentence"}])
pkg = E.load()
pd = E.load("progress_dialog")
kv = E.load("kanji_view")
jd = E.load("jlpt_data")

pkg._open_progress_dialog(dict(E.CFG))
dlg = None
t0 = time.monotonic()
while time.monotonic() - t0 < 60 and dlg is None:
    E.pump(0.2)
    dlg = next((w for w in E.app.topLevelWidgets() if isinstance(w, pd.ProgressDialog) and w.isVisible()), None)
E.pump(1.0)
dlg.resize(1100, 800)
# marks: some words found, some suspended; kanji / grammar marks too
words = [l.split("\t")[:2] for l in open(os.path.join(E.ADDON, "jlpt_n4.txt"), encoding="utf-8")
         if not l.startswith("#") and l.strip()][:40]
ov = dlg._overrides
ov.add_found_many([(w, r) for w, r in words[:30]])
for w, r in words[30:36]:
    ov.toggle_suspended(w, r)
for ch in "雨雪風空":
    dlg._kanji_overrides.toggle_found(ch, "")
dlg._kanji_overrides.toggle_suspended("海", "")
gids = list(E.load("grammar_data").data())[:6]
for g in gids[:3]:
    dlg._grammar_overrides.toggle_found(g, "")
dlg._grammar_overrides.toggle_suspended(gids[4], "")
dlg._on_override_changed()

names = [dlg._tabs.tabText(i).split()[0] for i in range(dlg._tabs.count())]


def show_tab(name):
    dlg._tabs.setCurrentIndex(names.index(name))
    E.pump(0.4)
    page = dlg._tabs.currentWidget()
    sw = page.findChild(kv.KindSwitcher) if not isinstance(page, kv.KindSwitcher) else page
    return sw


def grab_tables(tag):
    for tab in ("Missing", "Marked"):
        sw = show_tab(tab)
        for k in range(sw.combo.count()):
            sw.combo.setCurrentIndex(k)
            E.pump(0.3)
            page = sw.stack.currentWidget()
            if hasattr(page, "refresh") and not os.environ.get("KT_NO_REFRESH"):
                page.refresh()
                E.pump(0.2)
            for j, t in enumerate(t for t in page.findChildren(QtWidgets.QTableWidget) if t.isVisible()):
                t.scrollToTop()
                E.pump(0.4)                   # a refill's buttons settle (old: widgets)
                t.viewport().repaint()
                t.viewport().grab().toImage().save(
                    os.path.join(OUT, f"{tag}_{tab}_{sw.combo.itemText(k)}_{j}.png"))
        sw.combo.setCurrentIndex(0)


grab_tables("normal")
dlg._gold = True
pd._GOLD_MODE["on"] = True
dlg._apply_gold_now()
E.pump(0.3)
grab_tables("gold")
pd._GOLD_MODE["on"] = False
dlg._gold = False
dlg._apply_gold_now()
E.pump(0.3)

# clicks on the painted buttons (new code only)
CHECKS = []
d = None
sw = show_tab("Marked")
sw.combo.setCurrentIndex(0); E.pump(0.2)
panel = sw.stack.currentWidget()
tables = [t for t in panel.findChildren(QtWidgets.QTableWidget) if t.isVisible()]
t = tables[0]
d = t.itemDelegateForColumn(t.columnCount() - 1)
if isinstance(d, getattr(pd, "_ButtonColumn", ())):
    n0 = len(ov.found)
    t.viewport().grab()
    r = d._rects[0]
    vp = t.viewport()

    def click(pos, button=Qt.MouseButton.LeftButton):
        for typ in (QtCore.QEvent.Type.MouseButtonPress, QtCore.QEvent.Type.MouseButtonRelease):
            ev = QtGui.QMouseEvent(typ, QtCore.QPointF(pos), QtCore.QPointF(vp.mapToGlobal(pos)),
                                   button, button if typ == QtCore.QEvent.Type.MouseButtonPress
                                   else Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier)
            QtWidgets.QApplication.sendEvent(vp, ev)
        E.pump(0.3)

    click(r.center(), Qt.MouseButton.RightButton)
    E.check("right-click on a Revert does nothing", len(ov.found) == n0)
    click(r.center())
    E.check("painted Revert reverts the first marked word", len(ov.found) == n0 - 1, (n0, len(ov.found)))
    ks = show_tab("Missing")
    ks.combo.setCurrentIndex(1); E.pump(0.3)
    kp = ks.stack.currentWidget()
    kt = [x for x in kp.findChildren(QtWidgets.QTableWidget) if x.isVisible()][0]
    hh = kt.horizontalHeader()
    right = hh.sectionViewportPosition(kt.columnCount() - 1) + hh.sectionSize(kt.columnCount() - 1)
    E.check("kanji Missing: ★ Found inside the table (On / Kun capped)",
            right <= kt.viewport().width() and hh.sectionSize(4) <= kp.CAPPED_PX,
            ([hh.sectionSize(c) for c in range(kt.columnCount())], kt.viewport().width()))
    kt.horizontalScrollBar().setValue(kt.horizontalScrollBar().maximum())
    E.pump(0.05)
    kt.viewport().grab()                  # the painted buttons know their places once drawn
    kd = kt.itemDelegateForColumn(kt.columnCount() - 1)
    first = kp._shown[0][1]
    kvp = kt.viewport()
    rr = kd._rects[0]
    ev = QtGui.QHelpEvent(QtCore.QEvent.Type.ToolTip, rr.center(), kvp.mapToGlobal(rr.center()))
    shown = []
    _st = QtWidgets.QToolTip.showText
    QtWidgets.QToolTip.showText = staticmethod(lambda *a, **k: shown.append(a[1]))
    QtWidgets.QApplication.sendEvent(kvp, ev)
    QtWidgets.QToolTip.showText = _st
    E.check("★ Found button tooltip", shown == ["Mark as found (counts as known)"], shown)
    vp = kvp
    t = kt
    press = QtCore.QPoint(rr.center())
    ev = QtGui.QMouseEvent(QtCore.QEvent.Type.MouseButtonPress, QtCore.QPointF(press),
                           QtCore.QPointF(kvp.mapToGlobal(press)), Qt.MouseButton.LeftButton,
                           Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    QtWidgets.QApplication.sendEvent(kvp, ev)
    away = QtCore.QPoint(5, rr.bottom() + 40)
    ev = QtGui.QMouseEvent(QtCore.QEvent.Type.MouseButtonRelease, QtCore.QPointF(away),
                           QtCore.QPointF(kvp.mapToGlobal(away)), Qt.MouseButton.LeftButton,
                           Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier)
    QtWidgets.QApplication.sendEvent(kvp, ev)
    E.pump(0.2)
    E.check("released off the button: nothing happens", not dlg._kanji_overrides.is_found(first, ""))
    click(rr.center())
    E.check("★ Found marks the kanji found", dlg._kanji_overrides.is_found(first, ""))
    E.check("the table dropped it", all(k != first for _, k in kp._shown))
    E.check("no button widgets in any table", not any(
        isinstance(w, QtWidgets.QPushButton) and w.isVisible()
        for tb in dlg.findChildren(QtWidgets.QTableWidget) for w in tb.viewport().findChildren(QtWidgets.QWidget)))
print("rendered", len([n for n in os.listdir(OUT) if n.endswith(".png")]), "images")
dlg.reject()
E.pump(0.3)
import shutil
shutil.rmtree(os.path.join(OUT, "_env"), ignore_errors=True)
E.finish()
