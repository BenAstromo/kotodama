"""Offscreen test environment for the maintenance pass.

Copies the add-on (code + data, NOT user_files / media / meta.json) into
<scratch>/env/addons21/jlpt_progress, so every write a test causes lands in
the copy. Stubs aqt / anki around real PyQt6. Import this first:

    import stubenv as E
    pd = E.load("progress_dialog")
"""
import os, shutil, sys, types, threading, importlib, json

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["KOTODAMA_NAKAMA_URL"] = "http://127.0.0.1:9"     # nothing listens: never the real Worker
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

REAL = r"C:\Users\benne\AppData\Roaming\Anki2\addons21\jlpt_progress"
HERE = os.path.dirname(os.path.abspath(__file__))
ENV = os.environ.get("KT_ENV") or os.path.join(HERE, "env", "addons21")
ADDON = os.path.join(ENV, "jlpt_progress")


def fresh_copy(with_user_files=False):
    if os.path.exists(ADDON):
        shutil.rmtree(ADDON)
    def ignore(d, names):
        skip = {"__pycache__", "tools", "server", ".claude", "meta.json"}
        if os.path.normpath(d) == os.path.normpath(REAL):
            skip |= {"media"} if os.environ.get("KT_NO_MEDIA") else set()
            if not with_user_files:
                skip.add("user_files")
        return [n for n in names if n in skip]
    shutil.copytree(REAL, ADDON, ignore=ignore)
    os.makedirs(os.path.join(ADDON, "user_files"), exist_ok=True)


if not os.environ.get("KT_KEEP"):
    fresh_copy(bool(os.environ.get("KT_USER_FILES")))

if os.environ.get("KT_QT") == "5":            # Anki's Qt5 builds (2.1.50-2.1.66)
    from PyQt5 import QtCore, QtGui, QtWidgets
    _MM = "PyQt5"
else:
    from PyQt6 import QtCore, QtGui, QtWidgets
    _MM = "PyQt6"
qt = types.ModuleType("aqt.qt")
for m in (QtCore, QtGui, QtWidgets):
    for k in dir(m):
        if not k.startswith("_"):
            setattr(qt, k, getattr(m, k))
try:
    import importlib as _il
    QtMultimedia = _il.import_module(_MM + ".QtMultimedia"); QtMultimediaWidgets = _il.import_module(_MM + ".QtMultimediaWidgets")
    for m in (QtMultimedia, QtMultimediaWidgets):
        for k in dir(m):
            if not k.startswith("_"):
                setattr(qt, k, getattr(m, k))
except Exception:
    pass
qt.pyqtSignal = QtCore.pyqtSignal; qt.pyqtSlot = QtCore.pyqtSlot
qt.__all__ = [k for k in dir(qt) if not k.startswith("_")]
app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

LOG = {"tooltips": [], "warnings": [], "refreshes": 0}
CFG = json.load(open(os.path.join(REAL, "config.json"), encoding="utf-8"))


class Hooks:
    def __getattr__(self, n):
        v = []
        setattr(self, n, v)
        return v


class _Poster(QtCore.QObject):
    sig = QtCore.pyqtSignal(object)
poster = _Poster()
poster.sig.connect(lambda fn: fn(), QtCore.Qt.ConnectionType.QueuedConnection)


class QueryOp:
    def __init__(self, *, parent, op, success):
        self._op, self._success, self._failure = op, success, None
    def failure(self, fn):
        self._failure = fn; return self
    def with_progress(self, label=None):
        return self
    def run_in_background(self):
        def run():
            try:
                r = self._op(mw.col)
            except BaseException as e:
                poster.sig.emit(lambda e=e: (self._failure or (lambda e: LOG["warnings"].append(repr(e))))(e))
                return
            poster.sig.emit(lambda: self._success(r))
        threading.Thread(target=run, daemon=True).start()


class MW(QtWidgets.QMainWindow):
    pass
mw = MW()
mw.col = None
mw.state = "deckBrowser"
mw.pm = types.SimpleNamespace(name="Test", profileFolder=lambda: ENV)
mw.addonManager = types.SimpleNamespace(
    getConfig=lambda *a: CFG, writeConfig=lambda name, c: CFG.update(c),
    setWebExports=lambda *a: None, addonFromModule=lambda m: "jlpt_progress",
    addonsFolder=lambda *a: ENV, toggleEnabled=lambda *a, **k: None,
    isEnabled=lambda *a: True)
mw.form = types.SimpleNamespace(menubar=QtWidgets.QMenuBar(mw), menuHelp=QtWidgets.QMenu("Help", mw),
                                menuTools=QtWidgets.QMenu("Tools", mw))
mw.deckBrowser = types.SimpleNamespace(refresh=lambda: LOG.__setitem__("refreshes", LOG["refreshes"] + 1))
mw.taskman = types.SimpleNamespace(run_in_background=lambda fn, on_done=None, **k: threading.Thread(
    target=lambda: _done(fn, on_done), daemon=True).start(), run_on_main=lambda fn: poster.sig.emit(fn))


def _done(fn, on_done):
    import concurrent.futures as cf
    fut = cf.Future()
    try:
        fut.set_result(fn())
    except BaseException as e:
        fut.set_exception(e)
    if on_done:
        poster.sig.emit(lambda: on_done(fut))


aqt = types.ModuleType("aqt"); aqt.qt = qt; aqt.mw = mw; aqt.gui_hooks = Hooks()
aqt.dialogs = types.SimpleNamespace(open=lambda *a, **k: None)
ops = types.ModuleType("aqt.operations"); ops.QueryOp = QueryOp
utils = types.ModuleType("aqt.utils")
utils.showWarning = lambda *a, **k: LOG["warnings"].append(a[0] if a else "")
utils.showInfo = utils.showWarning
utils.tooltip = lambda *a, **k: LOG["tooltips"].append(a[0] if a else "")
for n in ("openLink", "askUser", "getText", "qconnect", "tr", "showText", "getFile", "getSaveFile"):
    setattr(utils, n, lambda *a, **k: None)
sound = types.ModuleType("aqt.sound"); sound.av_player = types.SimpleNamespace(play_file=lambda *a: None)
anki = types.ModuleType("anki"); au = types.ModuleType("anki.utils")
au.ids2str = lambda ids: "(" + ",".join(str(i) for i in ids) + ")"
au.strip_html = lambda s: s
anki.utils = au
sys.modules.update({"aqt": aqt, "aqt.qt": qt, "aqt.utils": utils, "aqt.operations": ops,
                    "aqt.sound": sound, "anki": anki, "anki.utils": au})
sys.path.insert(0, ENV)


def load(name=None):
    pkg = importlib.import_module("jlpt_progress")
    return importlib.import_module("jlpt_progress." + name) if name else pkg


def pump(sec=0.2):
    import time
    end = time.monotonic() + sec
    while time.monotonic() < end:
        app.processEvents()
        time.sleep(0.005)


RESULTS = []


def check(name, cond, detail=None):
    RESULTS.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond or detail is None else f"   {detail}"), flush=True)


def finish():
    bad = [n for n, ok in RESULTS if not ok]
    print("ALL PASS" if not bad else f"{len(bad)} FAILED: {bad}", flush=True)
    os._exit(0 if not bad else 1)
