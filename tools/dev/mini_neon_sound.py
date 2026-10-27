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
html = mw_._widget_html(res, deck_name="Big", show_rank=True, show_art=False, neon=True)
again = mw_._widget_html(res, deck_name="Big", show_rank=True, show_art=False, neon=False)
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
        "<body style='background:#2c2c2c;color:#ddd;font-family:Segoe UI;margin:0;height:420px;position:relative'>"
        "<script>window.__msgs=[];var __t0=performance.now();function pycmd(m){__msgs.push([m,Math.round(performance.now()-__t0)]);}</script>"
        "<button onclick='location.reload()' style='position:absolute;left:20px;top:20px'>replay</button>"
        + html + "</body>")
open(OUT, "w", encoding="utf-8").write(page); print("wrote", OUT)

import time, glob
from jlpt_progress import neon_sound
t0 = time.time()
while neon_sound._mini["worker"] and neon_sound._mini["worker"].is_alive() and time.time() - t0 < 5:
    time.sleep(0.01)
print("rendered in", round(time.time() - t0, 2), "s; runs done:", list(neon_sound._mini["done"]))
import re
print("script runs:", re.findall(r"jlpt_neon_sound:(\d+)", html))

# ── handler test ──
played = []
neon_sound.play_file = lambda path, volume=neon_sound._VOLUME: played.append((os.path.basename(path or ""), volume))
run = int(re.findall(r"jlpt_neon_sound:(\d+)", html)[0])
fails = []
def check(name, got, want):
    ok = got == want; print(("ok  " if ok else "FAIL"), name, got, "" if ok else f"(want {want})")
    if not ok: fails.append(name)
h = mw_._on_webview_did_receive_js_message
check("our message handled", h(False, f"jlpt_neon_sound:{run}", None), (True, None))
check("played once, quiet", played, [(f"neon_flicker_{os.getpid()}_{run}.wav", neon_sound.MINI_VOLUME)])
check("again: nothing (used up)", (h(False, f"jlpt_neon_sound:{run}", None), len(played)), ((True, None), 1))
check("other messages untouched", h(False, "someone_else", None), False)
# a draw whose sound is still rendering: plays when ready (within MINI_LATE)
html2 = mw_._widget_html(res, deck_name="Big", show_rank=True, show_art=False, neon=True)
run2 = int(re.findall(r"jlpt_neon_sound:(\d+)", html2)[0])
h(False, f"jlpt_neon_sound:{run2}", None)
t0 = time.time()
while time.time() - t0 < 1.0:
    app.processEvents(); time.sleep(0.005)
print("late one:", played[1:], "rendered:", run2 not in neon_sound._mini["done"])
held2 = mw_._widget_html(res, deck_name="Big", neon=True, neon_hold=True)
check("held draw: no sound script", "jlpt_neon_sound" in held2, False)
print("FAILS:", fails or "none")
