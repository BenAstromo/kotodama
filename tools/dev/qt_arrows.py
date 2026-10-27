import os, sys, types, importlib.util
os.environ["QT_QPA_PLATFORM"] = "offscreen"
from PyQt6 import QtCore, QtGui, QtWidgets
qt = types.ModuleType("aqt.qt")
for m in (QtCore, QtGui, QtWidgets):
    for k in dir(m):
        if not k.startswith("_"): setattr(qt, k, getattr(m, k))
aqt = types.ModuleType("aqt"); aqt.qt = qt
sys.modules.update({"aqt": aqt, "aqt.qt": qt})
spec = importlib.util.spec_from_file_location("theme", r"C:\Users\benne\AppData\Roaming\Anki2\addons21\jlpt_progress\theme.py")
theme = importlib.util.module_from_spec(spec); spec.loader.exec_module(theme)
app = QtWidgets.QApplication([])
app.setFont(QtGui.QFont("Segoe UI", 9))
out = []
for gold in (False, True):
    d = QtWidgets.QDialog(); d.resize(420, 140)
    lay = QtWidgets.QVBoxLayout(d)
    tabs = QtWidgets.QTabWidget()
    for name in ("語彙", "漢字 & 文法", "テキストチェック", "履歴", "仲間", "見つけた単語"):
        tabs.addTab(QtWidgets.QWidget(), name)
    lay.addWidget(tabs)
    row = QtWidgets.QHBoxLayout(); row.addStretch()
    share = QtWidgets.QPushButton("画像で共有…"); row.addWidget(share)
    q = QtWidgets.QPushButton("?"); q.setObjectName("kicon"); q.setStyleSheet("font-weight: bold;"); row.addWidget(q)
    lay.addLayout(row)
    theme.apply(d, gold=gold)
    if os.environ.get("NOHOVER"): d.setStyleSheet(chr(10).join(l for l in d.styleSheet().splitlines() if ":hover::" not in l))
    if os.environ.get("NOCOLOR"): d.setStyleSheet(d.styleSheet() + "QDialog#kotodama QTabBar QToolButton { color: transparent; }")
    d.show(); app.processEvents()
    btns = [b for b in tabs.tabBar().findChildren(QtWidgets.QToolButton)]
    print("gold" if gold else "normal", [(b.text(), b.arrowType().name, b.isVisible()) for b in btns])
    out.append(d.grab())
img = QtGui.QPixmap(420, 290); img.fill(QtGui.QColor("black"))
p = QtGui.QPainter(img); p.drawPixmap(0, 0, out[0]); p.drawPixmap(0, 150, out[1]); p.end()
img.save(os.path.join(os.path.dirname(os.path.abspath(__file__)), "arrows.png"))
crop = img.copy(360, 150, 60, 40).scaled(360, 240, QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.FastTransformation)
crop.save(os.path.join(os.path.dirname(os.path.abspath(__file__)), "arrows_zoom.png"))
for b in btns: print(b.geometry())
