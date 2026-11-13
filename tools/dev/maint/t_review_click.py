"""Progress Review clicks (guide item 11): a click on a clickable label
reaches its _rv_click on PyQt6 and on Anki's Qt5 builds (KT_QT=5; Qt5's
QMouseEvent has no position()). Any traceback = FAIL."""
import sys, traceback
import stubenv as E
import mkcol
QtTest = __import__(E._MM + ".QtTest", fromlist=["QtTest"])
E.mw.col = mkcol.Col({"V": ["Word"]}, ["Main"], [])
rv = E.load("review_view")
ERRS = []
sys.excepthook = lambda *a: ERRS.append("".join(traceback.format_exception(*a)))
hits = []
lbl = rv._label("Words · 12")
lbl._rv_click = lambda: hits.append(1)
f = rv._Hover(lbl)
lbl.installEventFilter(f)
lbl.resize(120, 30)
lbl.show()
E.pump(0.2)
QtTest.QTest.mouseClick(lbl, E.QtCore.Qt.MouseButton.LeftButton, pos=E.QtCore.QPoint(10, 10))
E.pump(0.2)
E.check(f"[{E._MM}] a click reaches the label's action", hits == [1])
E.check(f"[{E._MM}] no errors", not ERRS)
if ERRS:
    print("".join(ERRS)[:3000])
E.finish()
