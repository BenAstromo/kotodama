"""Real PyQt6 (offscreen): the whole add-on (__init__ included) over a
synthetic 8k-note collection; the analysis must run off the main thread
(QueryOp), the window / Refresh / snapshot / mini widget must still work.
Writes only to the scratch dir (history, caches, found count redirected)."""
import os, random, sys, threading, time, types
import faulthandler; faulthandler.enable(file=open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "fh.txt"), "w"), all_threads=True)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["KOTODAMA_NAKAMA_URL"] = "http://127.0.0.1:8799"
sys.stdout.reconfigure(encoding="utf-8")
ADDON = r"C:\Users\benne\AppData\Roaming\Anki2\addons21\jlpt_progress"
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
app.setFont(QtGui.QFont("Yu Gothic UI"))

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
# ── neon: each element flickers on when it's first actually on screen ──
st = lambda w: getattr(w, "_neon_state", "lit")
def pump(sec):
    end = time.time() + sec
    while time.time() < end:
        app.processEvents(); time.sleep(0.004)
def settled():                     # nothing holding or mid-flicker
    return not pd._NEON["batches"] and not any(isinstance(st(r()), tuple) for r in pd._NEON["items"] if r())
def items():
    return [r() for r in pd._NEON["items"] if r() is not None]
check("director on with the window", pd._NEON["on"])
shots, t0 = [], time.time()
while time.time() - t0 < 6:
    app.processEvents(); time.sleep(0.003)
    c = pd._NEON["clock"]
    if len(shots) < 8 and c >= len(shots) * 0.11 and any(isinstance(st(w), tuple) and st(w)[0] is not None for w in items()):
        dlg.grab().copy(QtCore.QRect(10, 110, 1200, 520)).save(os.path.join(SCR, f"neon_{len(shots)}.png")); shots.append(round(c, 2))
    if settled() and pd._NEON["seq"]:
        break
print("frames at clock =", shots)
check("first look lit and finished", settled() and pd._NEON["seq"] >= 1)
check("nothing still dark that's on screen", all(not pd._on_screen(w) for w in items() if st(w) == "pending"))
ov = dlg._overview
scroll = ov._rank_bar.parentWidget()
while not isinstance(scroll, QtWidgets.QScrollArea):
    scroll = scroll.parentWidget()
print("rank bar on screen at open:", pd._on_screen(ov._rank_bar), " state:", st(ov._rank_bar))
if st(ov._rank_bar) == "pending":
    check("rank below the fold waits", not pd._on_screen(ov._rank_bar) and st(ov._rank_badge) == "pending")
    scroll.ensureWidgetVisible(ov._rank_bar, 0, 60)
    pump(0.12)
    check("rank lights once scrolled to", st(ov._rank_bar) != "pending")
else:
    print("     (window tall enough to show the rank at open)")
seq = pd._NEON["seq"]
pump(0.05)
# mid-flicker look at the rank badge
for k in range(4):
    pump(0.18); dlg.grab().save(os.path.join(SCR, f"neon_rank_{k}.png"))
pump(2.0)
# a taller window shows more: whatever is pending and becomes visible lights
pend = [w for w in items() if st(w) == "pending" and w.window() is dlg and pd._neon_page(w) is pd._neon_page(ov._all_bar)]
print("overview elements still unseen:", len(pend))
if pend:
    dlg.resize(1225, 3000); pump(0.15)
    shown = [w for w in pend if pd._on_screen(w)]
    check("taller window: newly visible elements light", shown and all(st(w) != "pending" for w in shown))
    dlg.resize(1225, 950); pump(0.1)
pump(2.0)
lit = [w for cls in (pd.LevelBar, pd.RankBar, pd.BeltBar, pd.RankBadge, pd.NeonTitle, pd._NeonZone)
       for w in dlg.findChildren(cls) if getattr(w, "_neon_pat", None)]
check("each element its own pattern", len(lit) > 3 and
      len({tuple(round(e, 3) for e, _ in w._neon_pat) for w in lit}) == len(lit))
# the Word Grid tab: canvases wait until the tab shows, then the visible ones light
gi = [i for i in range(dlg._tabs.count()) if dlg._tabs.tabText(i) == "Word Grid"][0]
# (built the first time its tab shows: _LazyTab, 2026-10-24)
check("grid tab unseen: not built yet", dlg._grid_flat is None)
dlg._tabs.setCurrentIndex(gi)
check("grid builds after the switch, under a note", dlg._grid_flat is None)
end = time.time() + 30
while dlg._grid_flat is None and time.time() < end:
    pump(0.02)
pump(0.06)
canv = [c for c in dlg._grid_flat.findChildren(pd._TileCanvas)]
zones = [z for c in canv for z in c._zones]
print("Word Grid zones:", len(zones), " colours:", sorted({z.color for z in zones}))
check("Word Grid glows per section (several colours)", len({z.color for z in zones}) >= 3)
gshots = []
for k in range(5):
    pump(0.15); img = dlg.grab(); img.save(os.path.join(SCR, f"neon_grid_{k}.png")); gshots.append(k)
zl = lambda: [z for c in dlg._grid_flat.findChildren(pd._TileCanvas) for z in c._zones]
check("grid lights when its tab is shown", any(st(z) != "pending" for z in zl()))
check("rows further down still wait", st(zl()[-1]) == "pending")
pump(2.0)
check("grid veil gone once lit", all(not z.isVisible() for z in zl() if st(z) == "lit"))
dlg.grab().save(os.path.join(SCR, "neon_grid_lit.png"))
# scroll half way: the rows that come into view light, the ones below still wait
gsb = dlg._grid_flat._scroll.verticalScrollBar(); gsb.setValue(gsb.maximum() // 2); pump(0.12)
vis = [z for z in zl() if pd._on_screen(z)]
check("scrolled: the zones now in view light", vis and all(st(z) != "pending" for z in vis))
check("scrolled: the last rows still wait", st(zl()[-1]) == "pending")
for k in range(3):
    pump(0.12); dlg.grab().save(os.path.join(SCR, f"neon_grid_mid_{k}.png"))
pump(2.0); dlg.grab().save(os.path.join(SCR, "neon_grid_mid_lit.png"))
gsb.setValue(0); pump(0.1)
# a refresh's rebuild of a page already seen: lit at once, no second flicker
dlg._tabs.setCurrentIndex(0); pump(0.1)
with pd._neon_quiet():
    ov.update_results(dlg._results)
pump(0.15)
check("rebuilt overview lit at once", st(dlg._overview._all_bar) == "lit")
# a bar's grid window (All levels, one section per level): the top section
# lights on opening, the lower ones only once scrolled to
before = set(app.topLevelWidgets())
dlg._open_grid_for_level("All"); pump(0.1)
gw = [w for w in app.topLevelWidgets() if w not in before and w.isVisible() and isinstance(w, QtWidgets.QDialog)][0]
gw.resize(1000, 600); pump(0.1)
gc = gw.findChildren(pd._TileCanvas)
print("grid window sections:", len(gc))
check("grid window: top section lights", st(gc[0]._zones[0]) != "pending")
check("grid window: lower sections wait", len(gc) > 1 and all(st(z) == "pending" for z in gc[-1]._zones))
gs = gw.findChildren(QtWidgets.QScrollArea)[0]
check("grid window: tiles fit its width (not cut off)",
      max(c.geometry().right() for c in gc) <= gs.viewport().width()
      and gs.widget().width() <= gs.viewport().width())
gs.verticalScrollBar().setValue(gs.verticalScrollBar().maximum()); pump(0.12)
check("grid window: last section lights once scrolled to", any(st(z) != "pending" for z in gc[-1]._zones))
pump(2.0); gw.close()
# a single level's grid window (the one in the owner's screenshot) at 900 × 620
before = set(app.topLevelWidgets())
dlg._open_grid_for_level("N5"); pump(0.2)
gw = [w for w in app.topLevelWidgets() if w not in before and w.isVisible() and isinstance(w, QtWidgets.QDialog)][0]
gs = gw.findChildren(QtWidgets.QScrollArea)[0]
gc = gw.findChildren(pd._TileCanvas)
right = max(t.geometry().right() for c in gc for t in c._cells)
check(f"N5 grid window: tiles inside the view (right edge {right} <= {gs.viewport().width()})",
      right <= gs.viewport().width() and gs.widget().width() <= gs.viewport().width())
pump(2.0); gw.grab().save(os.path.join(SCR, "neon_n5_window.png")); gw.close()
# Top 6,000 grid: every tile the count treats as marked found draws as found
# (owner 2026-10-22: がん / おお / いや drawn as missing among the found tiles)
before = set(app.topLevelWidgets())
dlg._open_grid_for_level("freq:6000"); pump(0.3)
fw = [w for w in app.topLevelWidgets() if w not in before and w.isVisible() and isinstance(w, QtWidgets.QDialog)][0]
fr = (dlg._results.get("frequency") or {}).get("found_ranks", set())
cells = [c for cv in fw.findChildren(pd._TileCanvas) for c in cv._cells]
odd = [c._display for c in cells if c._nid is None and c._rank is not None and (c._rank - 1) in fr and not c._is_found]
via_row = [c._display for c in cells if c._found_row and not dlg._overrides.is_found(c._display, c._reading)]
print("found rows:", len(fr), " found through another form:", len(via_row), via_row[:8])
check("Top 6,000: no counted-found tile drawn as missing", odd == [])
fw.close()
import glob
wavs = glob.glob(os.path.join(ADDON, "user_files", "neon_flicker_*.wav"))
print("neon wavs:", len(wavs), " batches so far:", pd._NEON["seq"])
check("neon sound prepared", len(wavs) >= 1)
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
# ── rain on the glass, level signs, sparks, the rare stutter ──
dlg._tabs.setCurrentIndex(0); pump(0.2)
rain = getattr(dlg, "_rain", None)
check("rain attached to the main window", rain is not None)
dlg.activateWindow(); dlg.raise_(); pump(1.3)
print("window active:", dlg.isActiveWindow(), " rain running:", rain._timer.isActive())
if not dlg.isActiveWindow():                     # offscreen may not activate: pretend
    dlg.isActiveWindow = lambda: True
    rain._resume(); pump(0.1)
check("rain runs while the window is in front", rain._timer.isActive())
def grab_rain(name):
    """The window with its glass (its own window now) laid over it."""
    img = dlg.grab()
    qp = QtGui.QPainter(img); qp.drawPixmap(0, 0, rain.grab()); qp.end()
    img.save(os.path.join(SCR, name))
check("the glass is its own click-through window over the dialog",
      rain.isWindow() and rain.geometry().size() == dlg.size()
      and bool(rain.windowFlags() & QtCore.Qt.WindowType.WindowTransparentForInput))
signs = [w for w in dlg._overview.findChildren(pd.LevelSign) if w.isVisible()]
check("five level signs on the Vocabulary tab", len(signs) == 5)
lights = pd.neon_lights(dlg)
kinds = {type(w).__name__ for _r, _c, _k, w in lights}
print("lights on screen:", len(lights), sorted(kinds))
check("lights include the bars and the signs", {"LevelBar", "LevelSign"} <= kinds)
pump(1.0)
print("drops:", len(rain._drops), " streaks:", len(rain._streaks), " sliders:", len(rain._sliders))
check("drops on the glass", len(rain._drops) >= 20)
lit_drops = [d for d in rain._drops if (rain._light_at(d.x, d.y)[1] > 0.3)]
check("some drops catch a tube's light", len(lit_drops) > 0)
# a spark: from a tube, in that tube's colour
rain._next["spark"] = 0; pump(0.05)
sp = rain._sparks[-1] if rain._sparks else None
from jlpt_progress.rain import _is_tube
cols = {c.rgb() for _r, c, _k, w in rain._lights if _is_tube(w)}
check("spark fired", sp is not None)
check("spark in its tube's colour", sp is not None and sp["color"].rgb() in cols)
pump(0.06); grab_rain("rain_spark.png")
# the spark's sound (owner: "can't hear the sparks"), and its doubled size
from jlpt_progress import neon_sound as _ns2
check("spark sounds rendered", len(_ns2._SPARKS) == 3 and all(os.path.getsize(f) > 10000 for f in _ns2._SPARKS))
_pf0, heard = _ns2.play_file, []
_ns2.play_file = lambda path, volume=_ns2._VOLUME, level=None, window=False: heard.append((os.path.basename(path), volume))
rain._next["spark"] = 0; pump(0.05)
_ns2.play_file = _pf0
check("a spark plays its crackle", heard and heard[-1][0].startswith("neon_spark_") and heard[-1][1] == _ns2.SPARK_VOLUME)
check("a spark has 18-32 pieces", rain._sparks and 18 <= len(rain._sparks[-1]["parts"]) <= 32)
pump(0.1); grab_rain("rain_spark2.png")
# the rare stutter: one lit tube flickers again, with a quiet sound
played = []
from jlpt_progress import neon_sound
_pf = neon_sound.play_file
neon_sound.play_file = lambda path, volume=neon_sound._VOLUME, level=None, window=False: played.append(volume)
def _st_safe(w):
    try:
        return getattr(w, "_neon_state", None)
    except RuntimeError:
        return None
# the rain's own trigger calls _neon_stutter on a random tube; here a known
# steady one, so the check doesn't depend on that tube's state
from jlpt_progress.rain import _is_tube as _it2
steady = [w for _r, _c, _k, w in pd.neon_lights(dlg) if _it2(w) and _st_safe(w) == "lit"]
check("a steady tube to stutter", len(steady) > 0)
dlg.activateWindow(); pump(0.2)
rain._stutter_fn(steady[0]); pump(0.05)
stut = [w for w in steady if isinstance(_st_safe(w), tuple)]
check("a tube stutters", len(stut) == 1)
pump(1.2)
check("its sound is very quiet", played and abs(played[-1] - pd.RARE_FLICKER_VOLUME) < 1e-9)
check("it's steady again", all(_st_safe(w) == "lit" for w in stut))
neon_sound.play_file = _pf
check("no glare smears (removed 2026-10-26)", not hasattr(rain, "_glares"))
# CPU: the rain running vs stopped, 4 s each, main window in front
import time as _t
def cpu(sec):
    c0, w0 = _t.process_time(), _t.time()
    pump(sec)
    return (_t.process_time() - c0) / (_t.time() - w0)
on = cpu(4.0)
rain._pause(); real_running = rain._running; rain._running = lambda: False
off = cpu(4.0)
rain._running = real_running; rain._resume()
print(f"CPU with rain {on * 100:.1f} %  without {off * 100:.1f} %  (one core; offscreen raster)")
# same on the Word Grid tab (thousands of tiles under the glass)
dlg._tabs.setCurrentIndex([i for i in range(dlg._tabs.count()) if dlg._tabs.tabText(i) == "Word Grid"][0])
pump(2.5)
on_g = cpu(4.0)
rain._pause(); rain._running = lambda: False
off_g = cpu(4.0)
rain._running = real_running; rain._resume()
print(f"Word Grid: CPU with rain {on_g * 100:.1f} %  without {off_g * 100:.1f} %")
grab_rain("rain_grid.png")
dlg._tabs.setCurrentIndex(0); pump(1.0)
grab_rain("rain_overview.png")
# no focus mute (owner 2026-11-03: removed; it kept silencing the window's
# sounds as it opened): a spark plays with no active window too
from jlpt_progress import neon_sound as _ns3
heard2 = []
_pf1 = _ns3.play_file
_ns3.play_file = lambda path, volume=_ns3._VOLUME, level=None: heard2.append(volume)
_real_aw = QtWidgets.QApplication.activeWindow
QtWidgets.QApplication.activeWindow = staticmethod(lambda: None)
rain._spark_fn(); pump(0.05)
check("no active window: a spark is still heard", heard2 == [_ns3.SPARK_VOLUME])
QtWidgets.QApplication.activeWindow = _real_aw
_ns3.play_file = _pf1
# a bar that has just flickered on sparks half the time (owner 2026-10-22)
import random as _rnd
bar = next(w for _r, _c, _k, w in pd.neon_lights(dlg) if isinstance(w, pd.LevelBar))
sign = next(w for _r, _c, _k, w in pd.neon_lights(dlg) if isinstance(w, pd.LevelSign))
_rr = _rnd.random
n0 = len(rain._sparks)
_rnd.random = lambda: 0.2; pd._first_light_spark(bar)
check("first light: a bar sparks (roll < 0.5)", len(rain._sparks) == n0 + 1)
_rnd.random = lambda: 0.7; pd._first_light_spark(bar)
check("first light: no spark on the other half", len(rain._sparks) == n0 + 1)
_rnd.random = lambda: 0.2; pd._first_light_spark(sign)
check("first light: signs don't spark", len(rain._sparks) == n0 + 1)
_rnd.random = _rr
hits = 0
_orig_fls = pd._first_light_spark
pd._first_light_spark = lambda w: globals().__setitem__("hits", hits + 1)
pd._neon_stutter(bar); pump(1.0)
check("a stutter ending is no first light", hits == 0)
import weakref as _wr
bar._neon_state = "pending"; pd._NEON["items"].append(_wr.ref(bar)); pd._neon_wake(); pump(4.0)
check("a bar's flicker ending asks for a first-light spark", hits >= 1)
pd._first_light_spark = _orig_fls
# Settings → Animations (owner 2026-10-22): flicker off → lit at once, no stutter; rain off → no glass
pd._NEON["instant"] = True
bar._neon_state = "pending"; pd._NEON["items"].append(_wr.ref(bar)); pd._neon_wake(); pump(0.15)
check("flicker off: a newly seen bar is lit at once", bar._neon_state == "lit" and pd._intro_light(bar) == 1.0)
pd._neon_stutter(bar)
check("flicker off: no stutter", bar._neon_state == "lit")
pd._NEON["instant"] = False
from jlpt_progress import effects as _fx
_ron = _fx.rain_on
_aw = dlg.isActiveWindow
dlg.isActiveWindow = lambda: True                # offscreen may not activate: pretend
rain._resume(); pump(0.1)
# (2026-10-25: the glass also carries Night look's lens effects, so the
# rain off alone leaves it up without drops; off with them too, it goes)
_rfn, _ffn = rain._rain_fn, rain._fx_fn
rain._rain_fn = lambda: False; pump(0.3)
check("rain off, lens effects on: no drops, slow frames",
      rain.isVisible() and not rain._drops and rain._timer.interval() == 100)
rain._fx_fn = lambda key: False; pump(1.3)
check("rain and lens effects off: the glass is hidden and stopped",
      not rain.isVisible() and not rain._timer.isActive())
rain._rain_fn, rain._fx_fn = _rfn, _ffn; pump(3.0)
check("rain back on: it resumes", rain.isVisible() and rain._timer.isActive())
dlg.isActiveWindow = _aw
pd._NEON["instant"] = False
# inactive: stops
rain._pause(); dlg.isActiveWindow = lambda: False
QtWidgets.QApplication.sendEvent(dlg, QtCore.QEvent(QtCore.QEvent.Type.WindowActivate)); pump(0.2)
check("rain stays stopped while the window is in the background", not rain._timer.isActive())
print("ALL PASS" if ok else "SOME FAILED"); sys.stdout.flush(); os._exit(0)
