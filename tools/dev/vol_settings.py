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
app = QtWidgets.QApplication([])
CFG = {"effects_volume": 40}
pkg._cfg = lambda: CFG
aqt.mw = mock.MagicMock()
fails = []
def check(name, got, want):
    ok = got == want; print(("ok  " if ok else "FAIL"), name, got, "" if ok else f"(want {want})")
    if not ok: fails.append(name)
effects = importlib.import_module("jlpt_progress.effects")
ns = importlib.import_module("jlpt_progress.neon_sound")
check("volume from settings", effects.volume(), 0.4)
CFG["effects_volume"] = "junk"; check("bad value → default 50%", effects.volume(), 0.5)
CFG["effects_volume"] = 0; check("0 → muted", effects.muted(), True)
# players: record the QSoundEffect volume they set
from PyQt6 import QtMultimedia
vols = []
class FX:
    def __init__(self): pass
    def setSource(self, u): pass
    def setVolume(self, v): vols.append(round(v, 3))
    def play(self): pass
QtMultimedia.QSoundEffect = FX
import winsound; ws = []; winsound.PlaySound = lambda *a: ws.append(a)
CFG["effects_volume"] = 40
ns.play_file(__file__); ns.play_file(__file__, ns.MINI_VOLUME)
check("neon main / mini at 40%", [round(v, 3) for v in vols], [round(ns._VOLUME * 0.4, 3), round(ns.MINI_VOLUME * 0.4, 3)])
CFG["effects_volume"] = 0; vols.clear(); ns.play_file(__file__); ns.queue([[(0.1, 0.0)]], 5)
check("neon at 0%: nothing, nothing queued", (vols, ns._mini["latest"], ws), ([], None, []))
chime = importlib.import_module("jlpt_progress.chime")
chime._PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chime_test.wav")
CFG["effects_volume"] = 40; chime.play(); check("chime at 40%", vols, [0.2])
CFG["effects_volume"] = 0; vols.clear(); chime.play(); check("chime at 0%", (vols, ws), ([], []))
amb = importlib.import_module("jlpt_progress.ambience")
check("star sound off at 0%", amb.enabled(), False)
CFG["effects_volume"] = 40; check("star sound on at 40%", amb.enabled(), True)
class Out:
    def __init__(self): self.v = None
    def setVolume(self, v): self.v = v
    def volume(self): return self.v
class Pl:
    def stop(self): pass
    def setPosition(self, p): pass
    def play(self): pass
a = amb._Ambience(); o = Out(); a._player = lambda n, loop: (Pl(), o); a._play("sun", True)
check("star sound at 40%", o.v, 0.2)
# the Settings dialog
cd = importlib.import_module("jlpt_progress.config_dialog")
cd.mw = aqt.mw
CFG["effects_volume"] = 70
dlg = cd.ConfigDialog(None, dict(CFG))
sl = dlg.effects_slider
check("slider from settings", sl.value(), 70)
heard = []
ns.preview = lambda level: heard.append(level)
sl.setValue(25)
t0 = time.time()
while time.time() - t0 < 0.6: app.processEvents(); time.sleep(0.01)
check("sample after the slider settles", heard, [0.25])
lbl = [w.text() for w in dlg.findChildren(QtWidgets.QLabel) if w.text().endswith("%") or w.text() == "Off"]
check("value label", lbl, ["25%"])
sl.setValue(0); app.processEvents()
check("0 shows Off", [w.text() for w in dlg.findChildren(QtWidgets.QLabel) if w.text() in ("Off", "0%")], ["Off"])
sl.setValue(55)
check("saved", dlg.get_config()["effects_volume"], 55)
dlg.resize(900, 760); dlg.show(); app.processEvents()
grp = [g for g in dlg.findChildren(QtWidgets.QGroupBox) if g.title() == "Sound effects"][0]
dlg.grab().save(os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings_sound.png"))
print("FAILS:", fails or "none")
