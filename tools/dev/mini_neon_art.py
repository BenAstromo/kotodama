import os, sys, types
ADDON = r"C:\Users\benne\AppData\Roaming\Anki2\addons21\jlpt_progress"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "neonweb", "index.html")
from PyQt6 import QtCore, QtGui, QtWidgets
qt = types.ModuleType("aqt.qt")
for m in (QtCore, QtGui, QtWidgets):
    for k in dir(m):
        if not k.startswith("_"): setattr(qt, k, getattr(m, k))
qt.pyqtSignal = QtCore.pyqtSignal
class Hooks:
    def __getattr__(self, n): v = []; setattr(self, n, v); return v
aqt = types.ModuleType("aqt"); aqt.qt = qt; aqt.mw = None; aqt.gui_hooks = Hooks()
utils = types.ModuleType("aqt.utils"); utils.showWarning = print; utils.tooltip = print
for n in ("openLink", "askUser", "getText", "qconnect", "tr", "showInfo"): setattr(utils, n, lambda *a, **k: None)
sys.modules.update({"aqt": aqt, "aqt.qt": qt, "aqt.utils": utils})
pkg = types.ModuleType("jlpt_progress"); pkg.__path__ = [ADDON]; sys.modules["jlpt_progress"] = pkg
pkg._cfg = lambda: {}
sys.stdout.reconfigure(encoding="utf-8")
app = QtWidgets.QApplication([])
import importlib
cs = importlib.import_module("jlpt_progress.card_state")
cs.rank_count = lambda *a, **k: 8144
mw_ = importlib.import_module("jlpt_progress.mini_widget")
counts = {"N5": (569, 682), "N4": (485, 640), "N3": (1075, 1703), "N2": (737, 1827), "N1": (1231, 3212)}
res = {l: {"known_words": [0] * k, "missing_words": [0] * (n - k)} for l, (k, n) in counts.items()}
html = mw_._widget_html(res, deck_name="Big", show_rank=True, show_art=True, neon=True)
again = mw_._widget_html(res, deck_name="Big", show_rank=True, show_art=True, neon=False)
assert "jlpt-neon" not in again
held = mw_._widget_html(res, deck_name="Big", neon=True, neon_hold=True)
assert "step-end 4.00s" in held and "step-end 0.30s" in html and "<script>var" not in html, "delays"
print("hold variant OK")
import random
from jlpt_progress.theme import flicker_pattern
names = ["N5", "N4", "N3", "N2", "N1", "rank", "belt"]
for visit in range(6):
    run = random.randrange(1 << 30)
    ends = {n: flicker_pattern(run + i + 1)[-1][0] for i, n in enumerate(names)}
    print("visit", visit + 1, "lit in order:", " ".join(sorted(names, key=ends.get)),
          "| longest", round(max(ends.values()), 2), "s")
print("neon classes:", html.count("jlpt-neon-f"), "fills,", html.count("jlpt-neon-t"), "texts")
page = ("<!doctype html><meta charset=utf-8><title>neon</title>"
        "<body style='background:#2c2c2c;color:#ddd;font-family:Segoe UI;margin:0;height:640px;position:relative'>"
        "<script>function pycmd(){}</script>"
        "<button onclick='location.reload()' style='position:absolute;left:20px;top:20px'>replay</button>"
        + html + "</body>")
open(OUT, "w", encoding="utf-8").write(page); print("wrote", OUT)
