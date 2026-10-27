import os, sys
exec(open("qt_goal.py", encoding="utf-8").read().split("from jlpt_progress import goal, history")[0])
from jlpt_progress import progress_dialog as pd, theme
shots = []
for gold, t in ((False, None), (False, 0.18), (False, 0.35), (True, None)):
    w = QtWidgets.QWidget(); w.setStyleSheet("background: #1e1e1e;")
    row = QtWidgets.QHBoxLayout(w)
    left = pd.NeonTitle(pd.TITLE_LEFT_GOLD if gold else pd.TITLE_LEFT)
    right = pd.NeonTitle(pd.TITLE_RIGHT_GOLD if gold else pd.TITLE_RIGHT)
    sep = QtWidgets.QLabel("|"); sep.setStyleSheet("font-size: 18px; color: #555555;")
    row.addStretch(); row.addWidget(left); row.addWidget(sep); row.addWidget(right); row.addStretch()
    pd._INTRO["run"] = 7; pd._neon_at([left, right], None if t is None else t * 1.8)
    w.resize(560, 54); w.show(); app.processEvents()
    shots.append(w.grab())
pd._neon_at([], None)
img = QtGui.QPixmap(560, 54 * 4); img.fill(QtGui.QColor("#1e1e1e"))
p = QtGui.QPainter(img)
for i, s in enumerate(shots): p.drawPixmap(0, 54 * i, s)
p.end(); img.save(os.path.join(OUT, "neon_title.png")); print("saved")
