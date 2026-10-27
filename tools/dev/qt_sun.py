import os, sys
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "qt_loyal.py"), encoding="utf-8").read().split("print(\"real months")[0])
from jlpt_progress import loyalty
# side by side as in the Vocabulary tab: 28x28 icon slot + label, Diamond vs Sun Diamond
w = QtWidgets.QWidget(); w.setStyleSheet("background: #1e1e1e;")
v = QtWidgets.QVBoxLayout(w)
for idx, months, sun in ((loyalty.SUN - 1, 60, False), (loyalty.SUN, 60, True)):
    row = QtWidgets.QHBoxLayout()
    ic = QtWidgets.QLabel(); ic.setFixedSize(28, 28); ic.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
    ic.setPixmap(loyalty.gem_pixmap(20, idx)); row.addWidget(ic)
    lb = QtWidgets.QLabel(loyalty.line(months, sun=sun)); lb.setStyleSheet("color: #b0b0b0; font-size: 12px; font-weight: 600;")
    row.addWidget(lb); row.addStretch(); v.addLayout(row)
w.resize(320, 80); w.show(); app.processEvents()
w.grab().scaled(960, 240).save(os.path.join(OUT, "sun_size.png"))
