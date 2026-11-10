"""Where the main window's memory goes (2026-11-10): Python allocations
(tracemalloc, by file:line) vs the process's private memory, at each step:
the widget's count, the window open, every tab, a grid window.

    %TEMP%\\qtv\\Scripts\\python.exe -X utf8 t_mem.py <out.txt>
"""
import ctypes, gc, io, os, sys, time, tracemalloc
OUT = sys.argv[1]
tracemalloc.start(1)
import stubenv as E
import perfdeck
from PyQt6 import QtCore

perfdeck.install(E)
REP = io.StringIO()


def private_mb():
    from ctypes import wintypes

    class PMC(ctypes.Structure):
        _fields_ = [("cb", ctypes.c_ulong), ("PageFaultCount", ctypes.c_ulong),
                    ("a1", ctypes.c_size_t), ("a2", ctypes.c_size_t), ("a", ctypes.c_size_t),
                    ("b", ctypes.c_size_t), ("c", ctypes.c_size_t), ("d", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t),
                    ("PrivateUsage", ctypes.c_size_t)]
    k32 = ctypes.WinDLL("kernel32")
    k32.GetCurrentProcess.restype = wintypes.HANDLE
    k32.K32GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD]
    c = PMC(); c.cb = ctypes.sizeof(c)
    k32.K32GetProcessMemoryInfo(k32.GetCurrentProcess(), ctypes.byref(c), c.cb)
    return c.PrivateUsage / 2**20


last = {"snap": tracemalloc.take_snapshot(), "mb": private_mb()}


def step(name, top=18):
    for _ in range(3):
        E.pump(0.2)
        QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete.value)
    gc.collect()
    snap = tracemalloc.take_snapshot()
    mb = private_mb()
    py_now = sum(s.size for s in snap.statistics("filename")) / 2**20
    diff = snap.compare_to(last["snap"], "lineno")
    py_delta = sum(d.size_diff for d in diff) / 2**20
    REP.write(f"\n##### {name}: private {mb:.0f} MB ({mb - last['mb']:+.0f}); "
              f"Python heap {py_now:.0f} MB ({py_delta:+.0f})\n")
    for d in diff[:top]:
        if abs(d.size_diff) < 512 * 1024:
            break
        fr = d.traceback[0]
        REP.write(f"  {d.size_diff / 2**20:+7.1f} MB  {os.path.basename(fr.filename)}:{fr.lineno}\n")
    last["snap"], last["mb"] = snap, mb


step("stub + deck")
pkg = E.load()
pd = E.load("progress_dialog")
mwid = E.load("mini_widget")
step("import")


class Content:
    stats = ""


t = time.perf_counter()
while time.perf_counter() - t < 900:
    E.pump(0.05)
    c = Content(); mwid._on_deck_browser_will_render_content(None, c)
    if "%" in c.stats:
        break
step("deck-list widget counted")
pkg._open_progress_dialog(dict(E.CFG))
dlg = None
t = time.perf_counter()
while dlg is None and time.perf_counter() - t < 900:
    E.pump(0.05)
    dlg = next((w for w in E.app.topLevelWidgets() if isinstance(w, pd.ProgressDialog) and w.isVisible()), None)
step("main window open")
for i in range(dlg._tabs.count()):
    dlg._tabs.setCurrentIndex(i)
    E.pump(0.4)
    step("tab " + dlg._tabs.tabText(i).split()[0], top=8)
dlg._open_grid_for_level("All")
step("All grid window", top=8)
dlg._open_grammar_grid("All")
step("grammar grid window", top=8)
with open(OUT, "w", encoding="utf-8") as f:
    f.write(REP.getvalue())
dlg.reject()
E.pump(0.3)
os._exit(0)
