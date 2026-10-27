"""Real PyQt6 (offscreen): the whole add-on (__init__ included) over a
synthetic 8k-note collection; the analysis must run off the main thread
(QueryOp), the window / Refresh / snapshot / mini widget must still work.
Writes only to the scratch dir (history, caches, found count redirected)."""
import os, random, sys, threading, time, types
import faulthandler; faulthandler.enable(file=open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "fh.txt"), "w"), all_threads=True)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["KOTODAMA_NAKAMA_URL"] = "http://127.0.0.1:8799"
sys.stdout.reconfigure(encoding="utf-8")
ADDON = os.environ.get("TY_ADDON") or "C:/Users/benne/AppData/Roaming/Anki2/addons21/jlpt_progress"
SCR = os.path.dirname(os.path.abspath(__file__))
CORPUS = r"C:\Users\benne\AppData\Local\Temp\data\tatoeba\jpn_sentences.tsv"
DB = os.path.join(SCR, "qtdb")
os.makedirs(DB, exist_ok=True)

# synthetic collection from the speed test (its stub's Col over sqlite)
PFX = sys.argv[1] if len(sys.argv) > 1 else "ty_"
sys.argv = ["x", DB, CORPUS]
sys.path.insert(0, os.path.join(ADDON, "tools"))
import speed_test as st
st.ADDON = ADDON
import sqlite3
st.build(os.path.join(DB, "qt_8000.anki2"), 8000, random.Random(3)).close()
sdb = sqlite3.connect(os.path.join(DB, "qt_8000.anki2"), check_same_thread=False)   # Anki's backend is thread-safe
sdb.execute("create table revlog (id integer primary key, cid integer, type integer, ivl integer)")
sdb.executemany("insert into revlog values (?,?,?,?)",
                [(nid + 5_000_000, nid, 0, 1) for (nid,) in
                 sdb.execute("select id from cards where type != 0").fetchall()[::7]])
sdb.commit()
col = st.stub_anki(sdb).col
for m in [m for m in sys.modules if m.startswith("aqt") or m.startswith("anki")]:
    del sys.modules[m]

from PyQt6 import QtCore, QtGui, QtWidgets
qt = types.ModuleType("aqt.qt")
for m in (QtCore, QtGui, QtWidgets):
    for k in dir(m):
        if not k.startswith("_"):
            setattr(qt, k, getattr(m, k))
qt.pyqtSignal = QtCore.pyqtSignal; qt.pyqtSlot = QtCore.pyqtSlot
qt.__all__ = [k for k in dir(qt) if not k.startswith("_")]
app = QtWidgets.QApplication([])
for _f in ("YuGothB.ttc", "YuGothM.ttc", "segoeui.ttf", "segoeuib.ttf"): QtGui.QFontDatabase.addApplicationFont("C:/Windows/Fonts/" + _f)
_f = QtGui.QFont("Segoe UI"); _f.setPointSize(9); app.setFont(_f)   # Anki on Windows

MAIN = threading.main_thread()
log = {"op_threads": [], "success_threads": [], "labels": [], "tooltips": [], "refreshes": 0}


class _Poster(QtCore.QObject):
    sig = QtCore.pyqtSignal(object)
poster = _Poster()
poster.sig.connect(lambda fn: fn(), QtCore.Qt.ConnectionType.QueuedConnection)


class QueryOp:
    """Like aqt.operations.QueryOp: op(col) in a worker thread, success /
    failure back on the main thread."""
    def __init__(self, *, parent, op, success):
        self._op, self._success, self._failure, self._label = op, success, None, None

    def failure(self, fn):
        self._failure = fn; return self

    def with_progress(self, label=None):
        self._label = label; return self

    def run_in_background(self):
        log["labels"].append(self._label)

        def run():
            log["op_threads"].append(threading.current_thread() is not MAIN)
            try:
                r = self._op(col)
            except BaseException as e:
                import traceback
                with open(os.path.join(SCR, "op_err.txt"), "a", encoding="utf-8") as f:
                    traceback.print_exc(file=f)
                poster.sig.emit(lambda e=e: (self._failure or (lambda e: print("FAIL in op", repr(e))))(e))
                return
            poster.sig.emit(lambda: (log["success_threads"].append(threading.current_thread() is MAIN),
                                     self._success(r)))
        threading.Thread(target=run, daemon=True).start()


class Hooks:
    def __getattr__(self, n):
        v = []; setattr(self, n, v); return v


cfg = {"deck_name": st.DECK, "ignore_suspended_cards": True, "lists": {}, "mini_widget_enabled": True,
       "field_mappings": [{"note_type": "Vocab", "field": "Word", "reading_field": "Reading", "sentence_field": "Sentence"},
                          {"note_type": "Sentence", "field": "", "reading_field": "", "sentence_field": "Sentence"}],
       "kanji_source": {"mode": "vocab", "deck": "", "mappings": []},
       "grammar_source": {"mode": "sentence", "deck": "", "mappings": []}}


class MW(QtWidgets.QMainWindow):
    pass
mw = MW()
mw.col = col
mw.state = "deckBrowser"
mw.addonManager = types.SimpleNamespace(getConfig=lambda *a: cfg, writeConfig=lambda *a: None,
                                        setWebExports=lambda *a: None)
mw.form = types.SimpleNamespace(menubar=QtWidgets.QMenuBar(mw), menuHelp=QtWidgets.QMenu("Help", mw))
mw.form.menubar.addMenu(mw.form.menuHelp)
mw.deckBrowser = types.SimpleNamespace(refresh=lambda: log.__setitem__("refreshes", log["refreshes"] + 1))
mw.col.sched = types.SimpleNamespace(day_cutoff=int(time.time()) + 3600)
aqt = types.ModuleType("aqt"); aqt.qt = qt; aqt.mw = mw; aqt.gui_hooks = Hooks()
ops = types.ModuleType("aqt.operations"); ops.QueryOp = QueryOp
utils = types.ModuleType("aqt.utils"); utils.showWarning = print; utils.showInfo = print
utils.tooltip = lambda *a, **k: log["tooltips"].append(a[0])
for n in ("openLink", "askUser", "getText", "qconnect", "tr"):
    setattr(utils, n, lambda *a, **k: None)
anki = types.ModuleType("anki"); au = types.ModuleType("anki.utils")
au.ids2str = lambda ids: "(" + ",".join(str(i) for i in ids) + ")"
sys.modules.update({"aqt": aqt, "aqt.qt": qt, "aqt.utils": utils, "aqt.operations": ops,
                    "anki": anki, "anki.utils": au})

# the real package, its user_files writes redirected before anything runs
sys.path.insert(0, os.path.dirname(ADDON))
import importlib
cs = importlib.import_module("jlpt_progress.card_state")
cs._FOUND_PATH = os.path.join(DB, "found.json")
nk = importlib.import_module("jlpt_progress.nakama")
nk._PATH = os.path.join(DB, "nakama.json")
if os.path.exists(nk._PATH): os.remove(nk._PATH)
real_nakama = os.path.join(ADDON, "user_files", "nakama.json")
real_nakama_existed = os.path.exists(real_nakama)
hist = importlib.import_module("jlpt_progress.history")
hist._PATH = os.path.join(DB, "history.json")
if os.path.exists(hist._PATH):
    os.remove(hist._PATH)
gd = importlib.import_module("jlpt_progress.grammar_data")
gd._PCACHE_PATH = os.path.join(DB, "pc.json")
sp = importlib.import_module("jlpt_progress.sentence_parser")
sp._words_cache_path = lambda: os.path.join(DB, "wc.json")
for p in (gd._PCACHE_PATH, os.path.join(DB, "wc.json")):
    if os.path.exists(p):
        os.remove(p)
history_calls = []
_rec, _bs = hist.record, hist.build_series
hist.record = lambda *a, **k: (history_calls.append("record"), _rec(*a, **k))[1]
hist.build_series = lambda *a, **k: (history_calls.append("series"), _bs(*a, **k))[1]
real_history_path = os.path.join(ADDON, "user_files", "history.json")
real_mtime = os.path.getmtime(real_history_path) if os.path.exists(real_history_path) else None
jp = importlib.import_module("jlpt_progress")
pd = importlib.import_module("jlpt_progress.progress_dialog")
mwid = importlib.import_module("jlpt_progress.mini_widget")
_ar = pd.ProgressDialog._apply_refresh
def _timed_apply(self, *a):
    t = time.perf_counter(); _ar(self, *a); print(f"     (_apply_refresh on the main thread: {(time.perf_counter()-t)*1000:.0f} ms)")
pd.ProgressDialog._apply_refresh = _timed_apply
_init = pd.ProgressDialog.__init__
def _timed_init(self, *a, **k):
    t = time.perf_counter(); _init(self, *a, **k); print(f"     (ProgressDialog built on the main thread: {(time.perf_counter()-t)*1000:.0f} ms)")
pd.ProgressDialog.__init__ = _timed_init

ok = True
def check(name, cond):
    global ok
    print(("PASS " if cond else "FAIL ") + name); ok &= bool(cond)


def pump_until(cond, timeout=180):
    """Run the event loop until cond(); returns the longest gap (s)
    between main-thread timer ticks meanwhile (UI responsiveness)."""
    last = [time.perf_counter()]; gap = [0.0]
    def tick():
        now = time.perf_counter(); gap[0] = max(gap[0], now - last[0]); last[0] = now
    t = QtCore.QTimer(); t.setInterval(20); t.timeout.connect(tick); t.start()
    end = time.time() + timeout
    while not cond() and time.time() < end:
        app.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 20)
    t.stop()
    return gap[0]


def dialogs():
    return [w for w in app.topLevelWidgets() if isinstance(w, pd.ProgressDialog) and w.isVisible()]




class _Scr:
    def availableGeometry(self): return QtCore.QRect(0, 0, 1920, 1040)
pd.ProgressDialog.screen = lambda self: _Scr()
jp.open_progress_dialog_direct()
pump_until(lambda: dialogs())
dlg = dialogs()[0]
dlg.resize(1225, 950)
for _ in range(3): app.processEvents()
check("neon director on with the window", pd._NEON["on"])
# 2e: a 1 s main-thread stall mid-flicker must pause the animation, not finish it
def _busy():
    return bool(pd._NEON["batches"]) or any(isinstance(getattr(r(), "_neon_state", None), tuple)
                                            for r in pd._NEON["items"] if r() is not None)
seen = []
t0 = time.time()
while (not pd._NEON["seq"] or _busy()) and time.time() - t0 < 6:
    app.processEvents(); seen.append(pd._NEON["clock"]); time.sleep(0.01)
    if len(seen) == 25: time.sleep(1.0)
steps = [b - a for a, b in zip(seen, seen[1:])]
print("flicker samples", len(seen), "max clock step", round(max(steps), 3) if steps else None)
check("first look finished", pd._NEON["seq"] >= 1 and not _busy())
check("no jump bigger than ~2 frames", max(steps) <= 0.034 + 1e-9)
ks = (dlg._results.get("kanji") or {}).get("stats")
if ks:
    items = [s for s in ks.values() if s.get("score") is not None]
    a = sum(s["card_mean"] for s in items) / len(items); b = sum(s["score"] for s in items) / len(items)
    print(f"kanji mean before {a:.3f} after {b:.3f}")
    for n in (1, 2, 3, 5, 10, 20):
        xs = [(s["card_mean"], s["score"]) for s in items if s["cards"] == n]
        if xs: print(f"  n={n}: {len(xs)} kanji, mean {sum(x for x,_ in xs)/len(xs):.3f} -> {sum(y for _,y in xs)/len(xs):.3f}")
names = [dlg._tabs.tabText(i) for i in range(dlg._tabs.count())]
print(names)
check("first tab is Vocabulary", names[0] == "Vocabulary")
def shot(name, idx, settle=4):
    name = PFX + name.replace("ui2_", "")
    dlg._tabs.setCurrentIndex(idx)
    for _ in range(settle): app.processEvents()
    dlg.grab().save(os.path.join(SCR, name))
shot("ui2_vocab.png", 0)
ix = lambda pre: [i for i, t in enumerate(names) if t.startswith(pre)][0]
shot("ui2_kanji.png", ix("Kanji"))
shot("ui2_marked.png", ix("Marked"))
shot("ui2_textcheck.png", ix("Text Check"))
shot("ui2_history.png", ix("History"))
nk.state().update(id="TEST2345", key="k" * 64, name="Ben")
dlg._nakama_tab._build(); shot("ui2_nakama.png", ix("Nakama"))
# a level grid with pinned headers
g = pd.WordGridPanel(dlg._results, "All", dlg._overrides)
g.resize(1000, 700); g.show()
for _ in range(3): app.processEvents()
sb = g._scroll.verticalScrollBar(); sb.setValue(sb.maximum() // 2)
for _ in range(3): app.processEvents()
check("pinned header shows while scrolled", g._pin.isVisible() and "N" in g._pin.text())
g.grab().save(os.path.join(SCR, PFX + "grid.png"))
sb.setValue(0); app.processEvents()
check("pinned header hidden at the top", not g._pin.isVisible())
print("ALL PASS" if ok else "SOME FAILED"); sys.stdout.flush(); os._exit(0)
