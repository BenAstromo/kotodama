import os, sys
exec(open("qt_goal.py", encoding="utf-8").read().split("from jlpt_progress import goal, history")[0])
from jlpt_progress import progress_dialog as pd, theme
dlg = QtWidgets.QDialog(); dlg.setObjectName("kotodama")
v = QtWidgets.QVBoxLayout(dlg); tabs = QtWidgets.QTabWidget(); v.addWidget(tabs)
for n in ("Vocabulary", "Word Grid", "History"): tabs.addTab(QtWidgets.QWidget(), n)
theme.apply(dlg, gold=False)
dlg.resize(420, 120); dlg.show(); app.processEvents()
bar = tabs.tabBar()
shots = [("before (stylesheet line)", bar.grab())]
bar.setStyleSheet("QTabBar::tab:selected { border-bottom-color: transparent; }")
u = pd._TabUnderline(bar)
pd._INTRO["run"] = 3
for t in (0.0, 0.3, 0.45, 0.6, 1.0):
    pd._neon_at([u], t * 1.8); app.processEvents()
    shots.append((f"intro t={t}", bar.grab()))
pd._neon_at([u], None); u.deleteLater(); bar.setStyleSheet(""); app.processEvents()
shots.append(("after (restored)", bar.grab()))
H = 34
img = QtGui.QPixmap(560, H * len(shots)); img.fill(QtGui.QColor("#1b1b1b"))
p = QtGui.QPainter(img); p.setPen(QtGui.QColor("#cccccc"))
for i, (label, pm) in enumerate(shots):
    p.drawPixmap(0, i * H, pm); p.drawText(380, i * H + 22, label)
p.end(); img.save(os.path.join(OUT, "tabline.png")); print("saved")
# after the underline is deleted, switching tabs must not touch it (owner's log 2026-10-21)
u2 = pd._TabUnderline(bar)
u2.deleteLater(); app.processEvents(); QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete.value); app.processEvents()
errs = []
sys.excepthook = lambda *a: errs.append(a[1])
for i in (1, 2, 0):
    tabs.setCurrentIndex(i); app.processEvents()
print("tab switches after delete, errors:", errs or "none")
