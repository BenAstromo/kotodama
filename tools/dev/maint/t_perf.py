"""Performance measurement (2026-11-10, the grid canvas rewrite): times and
memory of the add-on's heavy paths on a mid-size synthetic deck, offscreen.

    %TEMP%\\qtv\\Scripts\\python.exe -X utf8 t_perf.py <out.json> [rounds]

Measures: import (startup), the deck-list widget's first count, opening the
main window, every tab, Refresh; for each big grid window (All, freq:6000,
freq:20000, kanji All, grammar All; normal and gold): build + first paint,
private memory while open, scrolling (ms per viewport step, repainted
synchronously), search (typing one kana that matches many tiles), hover
(moving the mouse over 50 tiles). Each grid is opened `rounds` times
(default 3) and the median kept. Writes a JSON report, prints a table.
Delete env/ afterwards.
"""
import ctypes, gc, json, os, random, statistics, sys, time
OUT = sys.argv[1] if len(sys.argv) > 1 else "perf.json"
ROUNDS = int(sys.argv[2]) if len(sys.argv) > 2 else 3
ONLY = sys.argv[3].split(",") if len(sys.argv) > 3 else None

T0 = time.perf_counter()
import stubenv as E
import mkcol
from PyQt6 import QtCore, QtGui, QtWidgets

REPORT = {}


def private_mb():
    from ctypes import wintypes

    class PMC(ctypes.Structure):
        _fields_ = [("cb", ctypes.c_ulong), ("PageFaultCount", ctypes.c_ulong),
                    ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                    ("a", ctypes.c_size_t), ("b", ctypes.c_size_t), ("c", ctypes.c_size_t),
                    ("d", ctypes.c_size_t), ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t), ("PrivateUsage", ctypes.c_size_t)]
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.GetCurrentProcess.restype = wintypes.HANDLE
    k32.K32GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD]
    c = PMC(); c.cb = ctypes.sizeof(c)
    k32.K32GetProcessMemoryInfo(k32.GetCurrentProcess(), ctypes.byref(c), c.cb)
    return c.PrivateUsage / 2**20


def settle(sec=0.3):
    for _ in range(3):
        E.pump(sec / 3)
        QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete.value)
        E.app.processEvents()
    gc.collect()


import perfdeck
REPORT["deck_notes"] = perfdeck.install(E)

t = time.perf_counter()
pkg = E.load()
pd = E.load("progress_dialog")
mwid = E.load("mini_widget")
REPORT["import_s"] = round(time.perf_counter() - t, 3)


class Content:
    stats = ""


t = time.perf_counter()
c = Content(); mwid._on_deck_browser_will_render_content(None, c)
while time.perf_counter() - t < 120:
    E.pump(0.05)
    c = Content(); mwid._on_deck_browser_will_render_content(None, c)
    if "jlpt" in c.stats.lower() and "%" in c.stats:
        break
REPORT["widget_first_count_s"] = round(time.perf_counter() - t, 3)
t = time.perf_counter()
for _ in range(20):
    c = Content(); mwid._on_deck_browser_will_render_content(None, c)
REPORT["widget_redraw_ms"] = round((time.perf_counter() - t) / 20 * 1000, 2)

settle()
mb0 = private_mb()
t = time.perf_counter()
pkg._open_progress_dialog(dict(E.CFG))
dlg = None
while time.perf_counter() - t < 120:
    E.app.processEvents()
    dl = [w for w in E.app.topLevelWidgets() if isinstance(w, pd.ProgressDialog) and w.isVisible()]
    if dl:
        dlg = dl[0]
        break
    time.sleep(0.002)
dlg.grab()
REPORT["main_open_s"] = round(time.perf_counter() - t, 3)
settle(1.0)
REPORT["main_window_open_mb"] = round(private_mb() - mb0, 1)
tabs = {}
for i in range(dlg._tabs.count()):
    t = time.perf_counter()
    dlg._tabs.setCurrentIndex(i)
    E.app.processEvents()
    dlg.grab()
    tabs[dlg._tabs.tabText(i)] = round(time.perf_counter() - t, 3)
    settle(0.6)
REPORT["tab_first_show_s"] = tabs
REPORT["main_window_mb"] = round(private_mb() - mb0, 1)
dlg._tabs.setCurrentIndex(0)
settle()

t = time.perf_counter()
dlg._do_full_refresh()
while dlg._refreshing and time.perf_counter() - t < 120:
    E.app.processEvents()
    time.sleep(0.002)
REPORT["refresh_s"] = round(time.perf_counter() - t, 3)
settle(1.0)


def grid_window(key):
    w = dlg._grid_windows.get(key)
    return w


def open_grid(kind, level):
    if kind == "word":
        dlg._open_grid_for_level(level)
    elif kind == "kanji":
        dlg._open_kanji_grid(level)
    else:
        dlg._open_grammar_grid(level)


def measure_grid(kind, level, gold=False):
    key = f"{kind}:{level}"
    rows = []
    for r in range(ROUNDS):
        pd._GOLD_MODE["on"] = gold
        settle(0.5)
        mb = private_mb()
        t = time.perf_counter()
        open_grid(kind, level)
        w = grid_window(key)
        E.app.processEvents()
        w.grab()
        t_open = time.perf_counter() - t
        settle(0.5)
        mb_open = private_mb() - mb
        panel = w.findChild(pd.WordGridPanel)
        sa = panel._scroll
        bar = sa.verticalScrollBar()
        vp = sa.viewport()
        steps = 0
        t = time.perf_counter()
        v = 0
        t_paint = 0.0
        while v < bar.maximum() and steps < 40:
            v = min(bar.maximum(), v + vp.height())
            bar.setValue(v)
            E.app.processEvents()
            tp = time.perf_counter()
            vp.repaint()
            t_paint += time.perf_counter() - tp
            steps += 1
        t_scroll = (time.perf_counter() - t) / max(1, steps) * 1000
        t_paint = t_paint / max(1, steps) * 1000
        bar.setValue(0); E.app.processEvents()
        # search: one common kana (many matches), then clear
        t = time.perf_counter()
        panel._search_edit.setText("か" if kind != "grammar" else "te")
        E.app.processEvents(); vp.repaint()
        t_search = time.perf_counter() - t
        t = time.perf_counter()
        panel._search_edit.setText("")
        E.app.processEvents(); vp.repaint()
        t_clear = time.perf_counter() - t
        # hover: move over 50 points across the top of the viewport
        bar.setValue(0); E.app.processEvents()
        t = time.perf_counter()
        for i in range(50):
            pos = QtCore.QPointF(20 + (i * 37) % max(40, vp.width() - 40), 120 + (i % 5) * 40)
            target = vp.childAt(pos.toPoint()) or vp
            lp = target.mapFrom(vp, pos.toPoint())
            ev = QtGui.QMouseEvent(QtCore.QEvent.Type.MouseMove, QtCore.QPointF(lp),
                                   vp.mapToGlobal(pos), QtCore.Qt.MouseButton.NoButton,
                                   QtCore.Qt.MouseButton.NoButton, QtCore.Qt.KeyboardModifier.NoModifier)
            QtWidgets.QApplication.sendEvent(target, ev)
            E.app.processEvents()
        t_hover = (time.perf_counter() - t) / 50 * 1000
        n_obj = len(w.findChildren(QtCore.QObject))
        w.hide(); w.deleteLater()
        dlg._grid_windows.pop(key, None)
        settle(0.8)
        mb_after = private_mb() - mb
        rows.append(dict(open_s=t_open, mb_open=mb_open, mb_after=mb_after, scroll_ms=t_scroll,
                         paint_ms=t_paint,
                         search_s=t_search, clear_s=t_clear, hover_ms=t_hover, qobjects=n_obj,
                         scroll_steps=steps))
    pd._GOLD_MODE["on"] = False
    med = {k: round(statistics.median(r[k] for r in rows), 3) for k in rows[0]}
    med["mb_first"] = round(rows[0]["mb_open"], 1)      # fresh heap: the real cost
    med["open_first_s"] = round(rows[0]["open_s"], 3)
    med["mb_marginal"] = marginal_mb(kind, level, gold)
    return med


def build_copy(kind, level):
    kv = E.load("kanji_view")
    if kind == "word":
        return dlg._build_grid_window(level, "perf-copy")
    if kind == "kanji":
        return kv.open_kanji_grid(dlg, dlg._results["kanji"], level, dlg._kanji_overrides,
                                  dlg._deck_name, lambda: None)
    return kv.open_grammar_grid(dlg, dlg._results["grammar"], level, dlg._grammar_overrides,
                                dlg._deck_name, lambda: None)


def marginal_mb(kind, level, gold):
    """Memory one more open copy of the grid costs: three copies open at
    once, (third - first) / 2 — the first soaks up the heap's free space."""
    pd._GOLD_MODE["on"] = gold
    wins, mem = [], []
    for k in range(3):
        w = build_copy(kind, level)
        E.app.processEvents(); w.grab()
        wins.append(w)
        settle(0.4)
        mem.append(private_mb())
    for w in wins:
        w.hide(); w.deleteLater()
    settle(0.8)
    pd._GOLD_MODE["on"] = False
    return round((mem[2] - mem[0]) / 2, 1)


GRIDS = [("word", "All", False), ("word", "freq:6000", False), ("word", "freq:20000", False),
         ("kanji", "All", False), ("grammar", "All", False), ("word", "All", True),
         ("word", "N5", False)]
REPORT["grids"] = {}
for kind, level, gold in GRIDS:
    name = f"{kind}:{level}" + (" gold" if gold else "")
    if ONLY is not None and name not in ONLY:
        continue
    try:
        REPORT["grids"][name] = measure_grid(kind, level, gold)
    except Exception as e:
        import traceback; traceback.print_exc()
        REPORT["grids"][name] = {"error": repr(e)}
    print(name, REPORT["grids"][name], flush=True)

# the Word Grid tab (flat, every JLPT word) lives in the main window
REPORT["total_s"] = round(time.perf_counter() - T0, 1)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(REPORT, f, ensure_ascii=False, indent=1)
print(json.dumps({k: v for k, v in REPORT.items() if k != "grids"}, ensure_ascii=False))
dlg.reject()
E.pump(0.5)
os._exit(0)
