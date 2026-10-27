"""Mini widget flicker waits while Anki is in the background (owner
2026-10-22: "not do the flicker animation and sound effects until you tab
in"). Offscreen PyQt6, a fake main window; writes neonweb/wait.html for a
browser check of the CSS pause. Prints FAILS: none when everything holds."""
import os, sys, types
ADDON = r"C:\Users\benne\AppData\Roaming\Anki2\addons21\jlpt_progress"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "neonweb", "wait.html")
os.environ["QT_QPA_PLATFORM"] = "offscreen"
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
mini = importlib.import_module("jlpt_progress.mini_widget")

fails = []
def check(name, got, want=True):
    ok = got == want
    print(("ok   " if ok else "FAIL ") + name, "" if ok else f"(got {got!r}, want {want!r})")
    if not ok:
        fails.append(name)


class FakeMain(QtWidgets.QWidget):
    """Anki's main window: active / minimised on demand, a deck list web view."""
    def __init__(self):
        super().__init__()
        self.active, self.mini_ = False, True
        self.js = []
        self.deckBrowser = types.SimpleNamespace(web=types.SimpleNamespace(eval=self.js.append))
    def isActiveWindow(self): return self.active
    def isMinimized(self): return self.mini_


win = FakeMain()
mini.mw = win
counts = {"N5": (569, 682), "N4": (485, 640), "N3": (1075, 1703), "N2": (737, 1827), "N1": (1231, 3212)}
res = {l: {"known_words": [0] * k, "missing_words": [0] * (n - k)} for l, (k, n) in counts.items()}

def pump(ms):
    t = QtCore.QElapsedTimer(); t.start()
    while t.elapsed() < ms:
        app.processEvents(); QtCore.QThread.msleep(5)

# Started minimised: the draw is paused, nothing woken yet
html = mini._widget_html(res, deck_name="Big", show_rank=True, show_art=False, neon=True)
check("minimised: animated elements carry the wait class", html.count(mini.NEON_WAIT_CLASS) > 5)
check("minimised: the pause rule is in the CSS", "animation-play-state: paused !important" in html)
check("minimised: wake pending", mini._WAKE["pending"])
QtWidgets.QApplication.sendEvent(win, QtCore.QEvent(QtCore.QEvent.Type.WindowStateChange)); pump(150)
check("still minimised (a state change, not restored): not woken", win.js, [])
# Tabbed in: activated and restored
win.active, win.mini_ = True, False
QtWidgets.QApplication.sendEvent(win, QtCore.QEvent(QtCore.QEvent.Type.WindowActivate)); pump(150)
check("activated: the page is woken once", len(win.js), 1)
check("activated: it removes the wait class", mini.NEON_WAIT_CLASS in (win.js or [""])[0] and "classList.remove" in win.js[0])
check("activated: nothing pending any more", mini._WAKE["pending"], False)
QtWidgets.QApplication.sendEvent(win, QtCore.QEvent(QtCore.QEvent.Type.WindowActivate)); pump(150)
check("activated again: no second wake", len(win.js), 1)
# In front already: no waiting at all
html2 = mini._widget_html(res, deck_name="Big", show_rank=True, show_art=False, neon=True)
check("in front: no wait class on the elements", f" {mini.NEON_WAIT_CLASS}\"" in html2, False)
check("in front: nothing pending", mini._WAKE["pending"], False)
# Behind another window (not minimised, not active): waits too
win.active = False
html3 = mini._widget_html(res, deck_name="Big", show_rank=True, show_art=False, neon=True)
check("behind another window: waits", mini._WAKE["pending"] and html3.count(mini.NEON_WAIT_CLASS) > 5)

# A page for the browser check: the CSS pause holds, removing the class runs it
os.makedirs(os.path.dirname(OUT), exist_ok=True)
page = ("<!doctype html><meta charset=utf-8><title>wait</title>"
        "<body style='background:#2c2c2c;color:#ddd;font-family:Segoe UI;margin:0;height:420px'>"
        "<script>window.__msgs=[];function pycmd(m){__msgs.push(m);}</script>" + html + "</body>")
open(OUT, "w", encoding="utf-8").write(page)
print("wrote", OUT)
print("FAILS:", fails or "none")
