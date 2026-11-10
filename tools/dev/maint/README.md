# Maintenance tests (2026-10-26 pass)

Run with the PyQt6 venv: `%TEMP%\qtv\Scripts\python.exe -X utf8 <test>.py` from this folder. For Anki's Qt5 builds: set `KT_QT=5` and use the PyQt5 venv `%TEMP%\qt5v` (`py -m venv qt5v` + `pip install PyQt5`); tools/dev/qt_neon.py runs on Qt5 with `PyQt6` replaced by `PyQt5`.
`stubenv.py` copies the add-on (not user_files / meta.json) into `env/` here and stubs Anki
around real PyQt6, so tests never touch your real files. `mkcol.py` = a small fake collection.
Delete `env/` afterwards (it holds a 27 MB copy).

- `t_scenarios.py <fresh|empty|nofield|baddeck|nodeck|corrupt|unicode|oldcfg|normal>`: widget, window, every tab, grids, Refresh, close.
- `t_leaks.py [rounds]`: open/close the window N times, counts windows / Qt objects / timers / hooks / memory.
- `t_nakama_offline.py <refused|timeout>`: Nakama with no server (never the real Worker).
- `t_userfile_safety.py`, `t_override_race.py`, `t_deck_query.py`, `t_decode.py`, `t_rank_math.py`, `t_sun_debug.py`: the regressions for the fixes in maintenance_log.md.
- `t_migrate.py` (plain Python): migrate.py in temp folders.
- `t_marks.py` (plain Python, any folder): marks reach only their own word (the loanword button's marks are all loanwords, katakana marks stay on katakana rows, kana words find their own row), marked loanwords join the rank and frequency bars gradually, and the JLPT bars and history lines count them at once (2026-11-09). Python: `%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe` (the `python` on PATH is a Store stub).
- `parse39.py` / `compat39.py <addon dir>` (plain Python): Python 3.9 syntax and runtime hazards.
- `data_check.py <addon dir>`: bundled data file integrity.
- `invariants.py` / `hist_check.py <harness dir>`: counting and history invariants on a collection copy; put them next to tools/harness.py's copy and `col_copy.anki2` (see APP_VISION §9).
- `mk_corpus.py <parse_cache.json> <out.tsv>`: a stand-in Tatoeba-format corpus from your deck's sentences (qt_neon.py / speed_test.py need one).

Grid canvas and performance (2026-11-10). `KT_SRC=<folder>` makes stubenv copy that folder instead of the add-on (an old version: `git archive <rev> | tar -x -C <folder>` + config.json), `KT_ENV` puts the copy elsewhere, so old and new can run side by side.
- `t_tiles_look.py render <dir>` / `compare <dirA> <dirB> [diffdir]`: every word / kanji / grammar tile state (each level, maturity, found, waiting ★, counted, suspended, New dashed, ⧉, hover, search match), normal and gold, on a real `_TileCanvas` with its glow; compare is pixel by pixel. Render the old version and the new, then compare: must print ALL SAME.
- `t_buttons_look.py <dir>`: the tables with a button per row (Marked & Suspended Revert, kanji / grammar Missing ★ Found and Marked Revert), normal and gold, for the same compare (`KT_NO_REFRESH=1` grabs them as first built), plus the painted buttons' clicks and tooltip.
- `t_tiles_use.py`: every interaction through the canvas (hit-testing, hover, cursor, tooltips normal / gold, every click and modifier, search + scroll-to-match + Enter, the rain mist region, a Refresh).
- `t_perf.py <out.json> [rounds] [grid,…|base]` (deck: `perfdeck.py`) and `t_perf_all.ps1 <out.json> [rounds]` (one fresh process per grid, merged): startup, deck-list widget, main window, tabs, Refresh; per grid window open, scroll, search, hover, and `mb_marginal` (memory one more open copy costs: the only memory number that isn't skewed by Windows reusing freed heap).
- `t_prof.py <out.txt> [widget,open,tabs,refresh,grid]`: cProfile of those. `t_mem.py <out.txt>`: Python heap (tracemalloc) per step; its private-memory totals include tracemalloc's own overhead.
