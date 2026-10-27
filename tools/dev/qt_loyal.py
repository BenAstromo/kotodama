import os, sys, types
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["QT_QPA_FONTDIR"] = r"C:\Windows\Fonts"
ADDON = r"C:\Users\benne\AppData\Roaming\Anki2\addons21\jlpt_progress"
OUT = os.path.dirname(os.path.abspath(__file__))
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
aqt = types.ModuleType("aqt"); aqt.qt = qt; aqt.mw = _Any()
aqt.gui_hooks = _Any()
utils = types.ModuleType("aqt.utils"); utils.showWarning = print; utils.tooltip = print; utils.askUser = lambda *a, **k: False
anki = types.ModuleType("anki"); au = types.ModuleType("anki.utils"); au.ids2str = lambda ids: ""
sys.modules.update({"aqt": aqt, "aqt.qt": qt, "aqt.utils": utils, "anki": anki, "anki.utils": au})
pkg = types.ModuleType("jlpt_progress"); pkg.__path__ = [ADDON]; sys.modules["jlpt_progress"] = pkg
app = QtWidgets.QApplication([])
app.setFont(QtGui.QFont("Segoe UI", 9))
from jlpt_progress import loyalty, share_card, rank_data, history
history.today = lambda: __import__("datetime").date(2026, 10, 20)
print("real months from your history:", loyalty.months_with_kotodama())
for m in (0, 1, 5, 6, 11, 12, 18, 30, 59, 60, 61):
    print(m, "|", loyalty.line(m) or "-", "|", loyalty.line(m, True) or "-", "|", loyalty.next_step(m))
# ladder strip
strip = QtGui.QImage(12 * 76, 90, QtGui.QImage.Format.Format_ARGB32_Premultiplied); strip.fill(QtGui.QColor("#1a1a1a"))
p = QtGui.QPainter(strip)
for i in range(12):
    loyalty.paint_gem(p, QtCore.QRectF(i * 76 + 16, 6, 44, 44), i, dim=False)
    p.setPen(QtGui.QColor("#dddddd")); p.setFont(QtGui.QFont("Segoe UI", 8))
    p.drawText(QtCore.QRectF(i * 76, 54, 76, 30), QtCore.Qt.AlignmentFlag.AlignCenter, loyalty.TIERS[i][1] + "\n" + loyalty.duration(loyalty.TIERS[i][0]))
p.end(); strip.save(os.path.join(OUT, "loyal_strip.png"))
# share image + Nakama card at Jade (6) and Diamond (60); gold (Amaterasu) share at 18
import datetime
def data(count, months):
    info = rank_data.get_rank_info(count)
    return {"levels": [("N5", 600, 900), ("N4", 500, 900), ("N3", 700, 1500), ("N2", 400, 1800), ("N1", 300, 3000)],
            "freq": (5000, 20000), "info": info, "date": datetime.date(2026, 10, 20), "loyal": months}
share_card.render(data(5000, 6), "Ben").save(os.path.join(OUT, "loyal_share.png"))
share_card.render(data(20000, 18), "Ben", "がんばろう").save(os.path.join(OUT, "loyal_share_gold.png"))
prof = {"name": "Friend", "data": {"rank": 5000, "loyal": 60, "jlpt": {"N5": [600, 900]}, "freq": [5000, 20000],
                                    "week": 40, "month": 120, "found": 12, "found_loan": 300}}
share_card.render_profile(prof, {"rank": 4000, "jlpt": {"N5": [500, 900]}, "freq": [4000, 20000]}, "synced 2 h ago").save(os.path.join(OUT, "loyal_card.png"))
from jlpt_progress import divine_text, progress_dialog as pd
for t in ("Jade · 6 months with Kotodama", "Ruby · 4.5 years with Kotodama", "Bronze · 1 month with Kotodama"):
    print(t, "→", divine_text.translate(t))
shots = []
for gold, months, sun in ((False, 61, False), (True, 61, True)):
    pd._GOLD_MODE["on"] = gold
    loyalty.PREVIEW["months"] = months; loyalty.PREVIEW["sun"] = sun
    d = QtWidgets.QDialog(); d.setStyleSheet("QDialog { background: #1a1a1a; } QLabel { color: #e0e0e0; }")
    v = QtWidgets.QVBoxLayout(d); v.setContentsMargins(32, 16, 32, 16)
    pd._add_loyalty_section(v)
    d.resize(800, 470); d.show(); app.processEvents()
    shots.append(d.grab())
img = QtGui.QPixmap(800, 950); img.fill(QtGui.QColor("black"))
p = QtGui.QPainter(img); p.drawPixmap(0, 0, shots[0]); p.drawPixmap(0, 480, shots[1]); p.end()
img.save(os.path.join(OUT, "loyal_dialog.png"))
d2 = data(20000, 60); d2["sun"] = True
share_card.render(d2, "Ben").save(os.path.join(OUT, "loyal_share_sun.png"))
for m, s in ((60, False), (60, True), (59, True)):
    print("tier", m, s, loyalty.line(m, sun=s), "|", loyalty.line(m, True, s), "|", loyalty.next_step(m, sun=s), "|", divine_text.translate(loyalty.line(m, sun=s)))
loyalty.PREVIEW.update(months=None, sun=False)
seq = []
for _ in range(14):
    loyalty.cycle_preview(); seq.append((loyalty.PREVIEW["months"], loyalty.PREVIEW["sun"]))
print("cycle:", seq)
