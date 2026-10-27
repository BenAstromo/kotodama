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
- `parse39.py` / `compat39.py <addon dir>` (plain Python): Python 3.9 syntax and runtime hazards.
- `data_check.py <addon dir>`: bundled data file integrity.
- `invariants.py` / `hist_check.py <harness dir>`: counting and history invariants on a collection copy; put them next to tools/harness.py's copy and `col_copy.anki2` (see APP_VISION §9).
- `mk_corpus.py <parse_cache.json> <out.tsv>`: a stand-in Tatoeba-format corpus from your deck's sentences (qt_neon.py / speed_test.py need one).
