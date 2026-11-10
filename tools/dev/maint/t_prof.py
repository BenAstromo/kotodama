"""Where the main thread's time goes (2026-11-10): cProfile of the deck-list
widget's redraw, the main window's build, the slow first tabs and Refresh,
on perfdeck's synthetic deck.

    %TEMP%\\qtv\\Scripts\\python.exe -X utf8 t_prof.py <out.txt> [what,…]

what: widget, open, tabs, refresh, grid (default: all). Writes the top
functions by cumulative and by own time for each. Delete env/ afterwards.
"""
import cProfile, io, os, pstats, sys, time
OUT = sys.argv[1]
WHAT = sys.argv[2].split(",") if len(sys.argv) > 2 else ["widget", "open", "tabs", "refresh", "grid"]
import stubenv as E
import perfdeck
from PyQt6 import QtCore

perfdeck.install(E)
pkg = E.load()
pd = E.load("progress_dialog")
mwid = E.load("mini_widget")
REP = io.StringIO()


def prof(name, fn, n=1):
    pr = cProfile.Profile()
    t = time.perf_counter()
    pr.enable()
    for _ in range(n):
        fn()
    pr.disable()
    dt = (time.perf_counter() - t) / n
    REP.write(f"\n\n######## {name}: {dt * 1000:.1f} ms each ({n}×)\n")
    for key in ("cumulative", "tottime"):
        s = io.StringIO()
        pstats.Stats(pr, stream=s).strip_dirs().sort_stats(key).print_stats(28)
        REP.write(f"--- by {key}\n" + "\n".join(s.getvalue().splitlines()[6:]) + "\n")


class Content:
    stats = ""


def widget():
    c = Content()
    mwid._on_deck_browser_will_render_content(None, c)
    return c.stats


t = time.perf_counter()
while time.perf_counter() - t < 120:
    E.pump(0.05)
    h = widget()
    if "%" in h:
        break
E.pump(0.5)
if "widget" in WHAT:
    prof("deck-list widget redraw", widget, 20)

dlg = None


def find_dlg():
    return next((w for w in E.app.topLevelWidgets() if isinstance(w, pd.ProgressDialog) and w.isVisible()), None)


def open_main():
    global dlg
    pkg._open_progress_dialog(dict(E.CFG))
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < 120:
        E.app.processEvents()
        dlg = find_dlg()
        if dlg:
            break
        time.sleep(0.001)
    dlg.grab()


if "open" in WHAT:
    prof("main window open (main thread; waits included)", open_main)
else:
    open_main()
E.pump(1.0)
if "tabs" in WHAT:
    for i in range(dlg._tabs.count()):
        name = dlg._tabs.tabText(i).split()[0]
        if name in ("Missing", "Marked", "Word"):
            prof(f"tab {name}: first show", lambda i=i: (dlg._tabs.setCurrentIndex(i),
                                                         E.app.processEvents(), dlg.grab()))
        else:
            dlg._tabs.setCurrentIndex(i)
            E.pump(0.3)
    dlg._tabs.setCurrentIndex(0)
    E.pump(0.3)


def refresh():
    dlg._do_full_refresh()
    t0 = time.perf_counter()
    while dlg._refreshing and time.perf_counter() - t0 < 120:
        E.app.processEvents()
        time.sleep(0.001)


if "refresh" in WHAT:
    prof("Refresh (main thread; the analysis runs in a thread)", refresh)
if "grid" in WHAT:
    def grid():
        dlg._open_grid_for_level("freq:20000")
        w = dlg._grid_windows["word:freq:20000"]
        E.app.processEvents(); w.grab()
        w.hide(); w.deleteLater(); dlg._grid_windows.pop("word:freq:20000")
    prof("grid freq:20000 open", grid)
with open(OUT, "w", encoding="utf-8") as f:
    f.write(REP.getvalue())
dlg.reject()
E.pump(0.3)
os._exit(0)
