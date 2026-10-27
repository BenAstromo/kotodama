import os, sys
os.environ["QT_QPA_PLATFORM"] = "offscreen"
from PyQt6.QtGui import QImage, QPainter, QColor, QFont
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QRect, Qt
app = QApplication([])
S = os.path.dirname(os.path.abspath(__file__))
crops = [("vocab", QRect(10, 110, 1200, 230)), ("kanji", QRect(10, 110, 1200, 380)),
         ("marked", QRect(10, 110, 1200, 340)), ("history", QRect(10, 110, 1200, 300)),
         ("nakama", QRect(10, 110, 1200, 300))]
W = 2 * 1200 + 30; H = sum(r.height() + 40 for _, r in crops) + 40
out = QImage(W, H, QImage.Format.Format_RGB32); out.fill(QColor("#0b0b0b"))
p = QPainter(out); p.setPen(QColor("#d4a017")); f = QFont("Segoe UI"); f.setPixelSize(20); f.setBold(True); p.setFont(f)
p.drawText(10, 28, "BEFORE"); p.drawText(1200 + 30, 28, "AFTER")
y = 40
for name, r in crops:
    for i, pre in enumerate(("ty_o_", "ty_n_")):
        img = QImage(os.path.join(S, pre + name + ".png"))
        p.drawImage(i * (1200 + 30), y, img.copy(r))
    y += r.height() + 40
p.end(); out.save(sys.argv[1]); print(out.width(), out.height())
