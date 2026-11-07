"""Open → every tab → grids → close, N times. Anything that grows with
each round is a leak: top-level widgets, live QObjects, QTimers, hook
registrations, the shared neon lists, process memory."""
import ctypes, gc, os, sys, time
N = int(sys.argv[1]) if len(sys.argv) > 1 else 20
import stubenv as E
import mkcol
from PyQt6 import QtCore, QtWidgets

WORDS = [("食べる", "たべる", (2, 2, 30)), ("水", "みず", (2, 2, 5)), ("学校", "がっこう", (1, 1, 0)),
         ("先生", "せんせい", (0, 0, 0)), ("天気", "てんき", (2, -1, 40)), ("テレビ", "テレビ", (3, 3, 2)),
         ("経済", "けいざい", (2, 2, 100)), ("ご飯", "ごはん", (2, 2, 12)), ("猫", "ねこ", (2, 2, 3))]
col = mkcol.Col({"Vocab": ["Word", "Reading", "Sentence"]}, ["Main"],
                [("Main", "Vocab", {"Word": w, "Reading": r, "Sentence": "私は毎日学校に行きます。"}, c)
                 for w, r, c in WORDS])
E.mw.col = col
E.CFG.update(deck_name="Main", field_mappings=[{"note_type": "Vocab", "field": "Word",
             "reading_field": "Reading", "sentence_field": "Sentence"}])
pkg = E.load()
pd = E.load("progress_dialog")


class PMC(ctypes.Structure):
    _fields_ = [("cb", ctypes.c_ulong), ("PageFaultCount", ctypes.c_ulong),
                ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t),
                ("PrivateUsage", ctypes.c_size_t)]


def private_mb(peak=False):
    from ctypes import wintypes
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.GetCurrentProcess.restype = wintypes.HANDLE
    k32.K32GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD]
    c = PMC(); c.cb = ctypes.sizeof(c)
    k32.K32GetProcessMemoryInfo(k32.GetCurrentProcess(), ctypes.byref(c), c.cb)
    return (c.PeakPagefileUsage if peak else c.PrivateUsage) / 2**20


def settle():
    for _ in range(5):
        E.pump(0.15)
        QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete.value)
        E.app.processEvents()
    gc.collect()


def all_qobjects():
    seen, stack = set(), list(E.app.topLevelWidgets()) + [E.app, E.mw]
    while stack:
        o = stack.pop()
        try:
            if id(o) in seen:
                continue
            seen.add(id(o))
            stack.extend(o.children())
        except RuntimeError:
            pass
    return len(seen)


def snapshot():
    hooks = {k: len(v) for k, v in vars(E.aqt.gui_hooks).items() if isinstance(v, list)}
    timers = [o for o in gc.get_objects() if isinstance(o, QtCore.QTimer)]
    live_t = 0
    for t in timers:
        try:
            live_t += t.isActive()
        except RuntimeError:
            pass
    return {"toplevel": len(E.app.topLevelWidgets()), "qobjects": all_qobjects(),
            "py_qtimers": len(timers), "active_timers": live_t,
            "dialogs": sum(isinstance(w, pd.ProgressDialog) for w in E.app.topLevelWidgets()),
            "neon_items": len(pd._NEON["items"]), "neon_lights": len(pd._NEON["lights"]),
            "hl_cells": len(pd._HL_CELLS), "hooks": sum(hooks.values()),
            "focus_receivers": E.app.receivers(E.app.focusWindowChanged) if hasattr(E.app, "receivers") else -1,
            "gc_objects": len(gc.get_objects()), "mb": round(private_mb(), 1),
            "peak_mb": round(private_mb(peak=True), 1)}


def one_round(i):
    pkg._open_progress_dialog(dict(E.CFG))
    t0 = time.monotonic()
    dlg = None
    while time.monotonic() - t0 < 60 and dlg is None:
        E.pump(0.1)
        dl = [w for w in E.app.topLevelWidgets() if isinstance(w, pd.ProgressDialog) and w.isVisible()]
        dlg = dl[0] if dl else None
    assert dlg is not None, "window didn't open"
    for k in range(dlg._tabs.count()):
        dlg._tabs.setCurrentIndex(k)
        E.pump(0.15)
    for lvl in ("N5", "All", "freq:6000"):
        dlg._open_grid_for_level(lvl)
        E.pump(0.1)
    if dlg._kanji_tab is not None and (dlg._results.get("kanji") or {}).get("levels"):
        dlg._open_kanji_grid("N5")
    dlg._grid_windows.get("word:N5") and dlg._grid_windows["word:N5"].reject()
    dlg._open_grid_for_level("N5")                 # reuse a kept grid
    dlg._tabs.setCurrentIndex(0)
    E.pump(0.3)
    dlg.reject()
    settle()


one_round(0)                                       # warm-up: caches, first imports
one_round(1)
base = snapshot()
print("after 2 rounds:", base, flush=True)
mid = None
for i in range(2, N):
    one_round(i)
    if i == N // 2:
        mid = snapshot()
        print(f"after {i + 1} rounds:", mid, flush=True)
end = snapshot()
print(f"after {N} rounds:", end, flush=True)
rounds = N - 2
for k in ("toplevel", "dialogs", "qobjects", "py_qtimers", "active_timers", "neon_items",
          "neon_lights", "hl_cells", "hooks", "focus_receivers"):
    grow = end[k] - base[k]
    E.check(f"{k}: {base[k]} → {end[k]} over {rounds} rounds", grow <= 1)
gc_grow = (end["gc_objects"] - base["gc_objects"]) / rounds
mb_grow = (end["mb"] - base["mb"]) / rounds
# from halfway: the first rounds still fill Qt's and the heap's caches
peak_grow = (end["peak_mb"] - mid["peak_mb"]) / (N - 1 - N // 2)
print(f"python objects +{gc_grow:.0f} / round, memory now +{mb_grow:.2f} MB / round, "
      f"peak +{peak_grow:.2f} MB / round")
E.check("python objects don't grow per round (< 300)", gc_grow < 300)
# The peak, not the level after closing (2026-11-07): Windows keeps freed
# memory for reuse some rounds and returns it in others, so the level after
# a round swings by 200 MB (the All grid's ~7,850 tile widgets) with no
# leak; the peak stays flat unless something really is kept. A kept grid
# window would add 100+ MB a round.
E.check("peak memory doesn't grow per round (< 3 MB)", peak_grow < 3)
E.finish()
