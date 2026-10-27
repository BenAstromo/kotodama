import os, sys, types
ADDON = r"C:\Users\benne\AppData\Roaming\Anki2\addons21\jlpt_progress"
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
import importlib, time
from unittest import mock
sys.stdout.reconfigure(encoding="utf-8")
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")
app = QtWidgets.QApplication([])
CFG = {}
pkg._cfg = lambda: CFG
aqt.mw = mock.MagicMock()
fails = []
def check(name, got, want):
    ok = got == want; print(("ok  " if ok else "FAIL"), name, got, "" if ok else f"(want {want})")
    if not ok: fails.append(name)
# Settings → Animations: neon flicker / rain (owner 2026-10-22)
effects = importlib.import_module("jlpt_progress.effects")
check("both on by default", (effects.animations_on(), effects.rain_on()), (True, True))
CFG.update(neon_flicker=False, rain=False); effects._FLAGS.clear()
check("both off from settings", (effects.animations_on(), effects.rain_on()), (False, False))
CFG.update(neon_flicker=True); check("cached for a second", effects.animations_on(), False)
effects._FLAGS.clear(); check("re-read after", effects.animations_on(), True)
CFG.update(neon_flicker=False); effects._FLAGS.clear()
cd = importlib.import_module("jlpt_progress.config_dialog")
cd.mw = aqt.mw
dlg = cd.ConfigDialog(None, dict(CFG))
check("checkboxes from settings", (dlg.flicker_chk.isChecked(), dlg.rain_chk.isChecked()), (False, False))
dlg.flicker_chk.setChecked(True); dlg.rain_chk.setChecked(True)
out = dlg.get_config()
check("saved", (out["neon_flicker"], out["rain"]), (True, True))
dlg2 = cd.ConfigDialog(None, {})
check("default dialog: both checked", (dlg2.flicker_chk.isChecked(), dlg2.rain_chk.isChecked()), (True, True))
dlg.resize(900, 900); dlg.show(); app.processEvents()
dlg.grab().save(os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings_anim.png"))
mw_ = importlib.import_module("jlpt_progress.mini_widget")
CFG.update(neon_flicker=False); effects._FLAGS.clear()
check("mini widget: no flicker when off", mw_._flicker_on(), False)
print("FAILS:", fails or "none")
