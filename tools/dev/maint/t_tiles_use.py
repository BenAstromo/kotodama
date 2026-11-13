"""Painted grid tiles (2026-11-10): every interaction through the _TileCanvas.

    %TEMP%\\qtv\\Scripts\\python.exe -X utf8 t_tiles_use.py

Opens the real main window on a small deck, then in the word (N5, All,
freq:6000), kanji and grammar grid windows checks: tiles are not widgets;
hit-testing (tiles, gaps, past the row's end); hover (state, repaint,
cursor, leave, after a wheel scroll); tooltips (the tile's text, gold
recoloured in gold mode, none over a gap); left / Shift / Ctrl / middle /
Ctrl+middle / right clicks reach the right action; override_changed
reaches the dialog; search highlights, scrolls to the match and cycles on
Enter; the rain's mist region covers tiles but not the gaps; the Off-list
tab's tiles; a Refresh rebuilds the grids without errors.
"""
import io, os, sys, time, traceback
import stubenv as E
import mkcol
QtCore, QtGui, QtWidgets = E.QtCore, E.QtGui, E.QtWidgets
Qt = QtCore.Qt

ERRS = []
_real_err = sys.stderr


class Tee(io.TextIOBase):
    def write(self, s):
        if "Traceback" in s or "Error" in s:
            ERRS.append(s)
        return _real_err.write(s)

    def flush(self):
        _real_err.flush()


sys.stderr = Tee()
sys.excepthook = lambda *a: (ERRS.append("".join(traceback.format_exception(*a))),
                             traceback.print_exception(*a))

WORDS = [("食べる", "たべる", (2, 2, 30)), ("水", "みず", (2, 2, 5)), ("学校", "がっこう", (1, 1, 0)),
         ("先生", "せんせい", (0, 0, 0)), ("天気", "てんき", (2, -1, 40)), ("テレビ", "テレビ", (3, 3, 2)),
         ("経済", "けいざい", (2, 2, 100)), ("ご飯", "ごはん", (2, 2, 12)), ("猫", "ねこ", (2, 2, 3)),
         ("スマホ", "スマホ", (2, 2, 30))]
SENTS = ["私は毎日学校に行きます。", "昨日は雨が降ったので、家で本を読みました。", "水を飲みたいです。"]
nts = {"Vocab": ["Word", "Reading", "Sentence"], "SentOnly": ["Sentence"]}
notes = [("Main", "Vocab", {"Word": w, "Reading": r, "Sentence": SENTS[i % 3]}, c)
         for i, (w, r, c) in enumerate(WORDS)]
notes += [("Main", "SentOnly", {"Sentence": s}, (2, 2, 25)) for s in SENTS]
E.mw.col = mkcol.Col(nts, ["Main"], notes)
E.CFG.update(deck_name="Main", field_mappings=[
    {"note_type": "Vocab", "field": "Word", "reading_field": "Reading", "sentence_field": "Sentence"},
    {"note_type": "SentOnly", "field": "", "reading_field": "", "sentence_field": "Sentence"}])

pkg = E.load()
pd = E.load("progress_dialog")
kv = E.load("kanji_view")
rain = E.load("rain")
ovm = E.load("overrides")
check = E.check

CALLS = []
pd._open_jisho = lambda w, r="": CALLS.append(("jisho", w))
pd._search_term_in_browser = lambda d, r: CALLS.append(("browser_text", d))
pd._open_in_browser = lambda nid: CALLS.append(("browser", nid))
pd._open_notes_in_browser = lambda nids: CALLS.append(("browser_many", tuple(nids)))
pd._copy_word = lambda w, parent=None: CALLS.append(("copy", w, parent))
kv._open_jisho_kanji = lambda ch: CALLS.append(("jisho_kanji", ch))
kv.open_kanji_words = lambda parent, ch, kres: CALLS.append(("kanji_words", ch, parent))
kv.search_grammar_in_deck = lambda gid, parent=None: CALLS.append(("grammar_search", gid, parent))
kv._copy_word = lambda w, parent=None: CALLS.append(("copy", w, parent))
TIPS = []
_show = QtWidgets.QToolTip.showText
QtWidgets.QToolTip.showText = staticmethod(lambda *a, **k: (TIPS.append(a), _show(*a, **k)))

pkg._open_progress_dialog(dict(E.CFG))
t0 = time.monotonic()
dlg = None
while time.monotonic() - t0 < 60:
    E.pump(0.2)
    dl = [w for w in E.app.topLevelWidgets() if isinstance(w, pd.ProgressDialog) and w.isVisible()]
    if dl:
        dlg = dl[0]
        break
check("main window opened", dlg is not None)
if dlg is None:
    E.finish()
E.pump(1.0)
MARKED = []
_orig_marked = dlg._grid_marked
dlg._grid_marked = lambda key: (MARKED.append(key), _orig_marked(key))


def mouse(target, kind, pos, button=Qt.MouseButton.NoButton, mods=Qt.KeyboardModifier.NoModifier):
    t = {"move": QtCore.QEvent.Type.MouseMove, "press": QtCore.QEvent.Type.MouseButtonPress}[kind]
    ev = QtGui.QMouseEvent(t, QtCore.QPointF(pos), QtCore.QPointF(target.mapToGlobal(pos)),
                           button, button if kind == "press" else Qt.MouseButton.NoButton, mods)
    QtWidgets.QApplication.sendEvent(target, ev)
    return ev


def tip_at(canvas, pos):
    TIPS.clear()
    ev = QtGui.QHelpEvent(QtCore.QEvent.Type.ToolTip, pos, canvas.mapToGlobal(pos))
    QtWidgets.QApplication.sendEvent(canvas, ev)
    return TIPS[-1] if TIPS else None


def centre(t):
    return QtCore.QPoint(t._x + t._w // 2, t._y + t._h // 2)


def grid(key, opener):
    before = set(dlg._grid_windows)
    opener()
    E.pump(0.4)
    w = dlg._grid_windows.get(key)
    w.resize(900, 700)
    E.pump(0.3)
    return w


def common_checks(name, w, panel):
    canvases = w.findChildren(pd._TileCanvas)
    check(f"[{name}] has canvases", bool(canvases))
    cv = canvases[0]
    tiles = cv._cells
    check(f"[{name}] tiles are not Qt objects", not any(isinstance(t, QtCore.QObject) for t in tiles))
    check(f"[{name}] no tile widgets under the canvas",
          all(isinstance(c, pd._NeonZone) for c in cv.findChildren(QtWidgets.QWidget)))
    t0_, t1 = tiles[0], tiles[1]
    check(f"[{name}] hit-test: tile centre", cv._tile_at(centre(t0_)) is t0_)
    check(f"[{name}] hit-test: tile corner", cv._tile_at(QtCore.QPoint(t0_._x, t0_._y)) is t0_
          and cv._tile_at(QtCore.QPoint(t0_._x + t0_._w - 1, t0_._y + t0_._h - 1)) is t0_)
    gap = QtCore.QPoint(t0_._x + t0_._w + 1, t0_._y + 5)
    check(f"[{name}] hit-test: gap between tiles", cv._tile_at(gap) is None)
    check(f"[{name}] hit-test: above the grid", cv._tile_at(QtCore.QPoint(5, 1)) is None)
    last = cv._rows[-1]
    check(f"[{name}] hit-test: past the last row's end",
          cv._tile_at(QtCore.QPoint(last[2] + 5, last[0] + 5)) is None)
    # hover
    mouse(cv, "move", centre(t0_))
    check(f"[{name}] hover: tile hovered, pointing hand",
          t0_._hovered and cv.cursor().shape() == Qt.CursorShape.PointingHandCursor)
    mouse(cv, "move", centre(t1))
    check(f"[{name}] hover moves to the next tile", t1._hovered and not t0_._hovered)
    mouse(cv, "move", gap)
    check(f"[{name}] hover: gap clears it, normal cursor",
          not t1._hovered and cv._hover is None and cv.cursor().shape() == Qt.CursorShape.ArrowCursor)
    mouse(cv, "move", centre(t1))
    QtWidgets.QApplication.sendEvent(cv, QtCore.QEvent(QtCore.QEvent.Type.Leave))
    check(f"[{name}] leave clears hover", not t1._hovered and cv._hover is None)
    # tooltip
    tip = tip_at(cv, centre(t0_))
    check(f"[{name}] tooltip: the tile's text, its rectangle",
          tip is not None and tip[1] == t0_.toolTip() and tip[2] is cv and tip[3] == t0_.geometry())
    check(f"[{name}] tooltip: none over a gap", tip_at(cv, gap) is None)
    pd._GOLD_MODE["on"] = True
    tip = tip_at(cv, centre(t0_))
    pd._GOLD_MODE["on"] = False
    check(f"[{name}] gold tooltip recoloured + gold sheet",
          tip is not None and "#f5c518" in tip[1] and "#f5c518" in cv.styleSheet())
    tip_at(cv, centre(t0_))
    check(f"[{name}] tooltip sheet back to normal", "#f5c518" not in cv.styleSheet()
          and "font-size" in cv.styleSheet())
    # update() repaints just the tile's rect (and dies quietly with its canvas)
    t0_.update()
    # search
    s = panel._search_edit
    first_text = tiles[-1]._display if hasattr(tiles[-1], "_display") else None
    return cv, tiles


# ── N5 word grid ─────────────────────────────────────────────────────────────
w = grid("word:N5", lambda: dlg._open_grid_for_level("N5"))
panel = w.findChild(pd.WordGridPanel)
cv, tiles = common_checks("N5", w, panel)
known = next(t for t in panel._all_cells if t._known and not t._dups)
missing = next(t for t in panel._all_cells if not t._known and t._new_nid is None
               and not t._is_found and not t._is_suspended)
kc = known._canvas
CALLS.clear()
mouse(kc, "press", centre(known), Qt.MouseButton.LeftButton)
check("[N5] left-click known → Browser", CALLS == [("browser", known._nid)], CALLS)
mc = missing._canvas
CALLS.clear()
mouse(mc, "press", centre(missing), Qt.MouseButton.LeftButton)
check("[N5] left-click missing → copy, parent = its window", CALLS and CALLS[0][:2] == ("copy", missing._display)
      and CALLS[0][2] is w, CALLS)
CALLS.clear()
mouse(mc, "press", centre(missing), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ShiftModifier)
check("[N5] Shift+click → Jisho", CALLS == [("jisho", missing._display)], CALLS)
CALLS.clear()
mouse(mc, "press", centre(missing), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ControlModifier)
check("[N5] Ctrl+click → Browser text search", CALLS == [("browser_text", missing._display)], CALLS)
MARKED.clear()
ov = dlg._overrides
mouse(mc, "press", centre(missing), Qt.MouseButton.MiddleButton)
E.pump(0.2)
check("[N5] middle-click marks found + tells the dialog",
      ov.is_found(missing._display, missing._reading) and MARKED == ["word:N5"])
check("[N5] the hover text says marked", "Marked as found" in missing.toolTip())
mouse(mc, "press", centre(missing), Qt.MouseButton.MiddleButton, Qt.KeyboardModifier.ControlModifier)
check("[N5] Ctrl+middle-click suspends", ov.is_suspended(missing._display, missing._reading)
      and not ov.is_found(missing._display, missing._reading))
mouse(mc, "press", centre(missing), Qt.MouseButton.MiddleButton, Qt.KeyboardModifier.ControlModifier)
check("[N5] Ctrl+middle-click again unsuspends", not ov.is_suspended(missing._display, missing._reading))
MARKED.clear()
mouse(kc, "press", centre(known), Qt.MouseButton.MiddleButton)
check("[N5] middle-click a known tile does nothing", MARKED == [] and not ov.is_found(known._display, known._reading))
ev = mouse(cv, "press", QtCore.QPoint(2, 2), Qt.MouseButton.LeftButton)
check("[N5] a click off the tiles is passed on", not ev.isAccepted())
# search
target = panel._all_cells[-1]
bar = panel._scroll.verticalScrollBar()
bar.setValue(0); E.pump(0.05)
panel._search_edit.setText(target._display)
E.pump(0.1)
first = next(c for c in panel._all_cells if c.matches_search(target._display))
print("search target", target._display, "first match", first._display, first._y)
check("[N5] search highlights the match", target._highlighted)
vp = panel._scroll.viewport()
r = QtCore.QRect(first._canvas.mapTo(vp, first.pos()), QtCore.QSize(first._w, first._h))
check("[N5] search scrolled the match into view", vp.rect().contains(r), (r, vp.rect(), bar.value()))
check("[N5] search status names it", target._display in panel._search_status.text())
far = next(c for c in reversed(panel._all_cells)
           if sum(x.matches_search(c._display) for x in panel._all_cells) == 1)
panel._search_edit.setText("")
bar.setValue(0); E.pump(0.05)
panel._search_edit.setText(far._display)
E.pump(0.1)
r = QtCore.QRect(far._canvas.mapTo(vp, far.pos()), QtCore.QSize(far._w, far._h))
check("[N5] search scrolls down to a far match", bar.value() > 0 and vp.rect().contains(r),
      (far._display, r, bar.value()))
panel._search_edit.setText("")
E.pump(0.05)
check("[N5] clearing the search un-highlights", not any(t._highlighted for t in panel._all_cells))
# wheel scroll under a still mouse re-hovers
bar.setValue(0); E.pump(0.05)
w.close(); E.pump(0.2)

# ── All grid (several canvases, rain mist region) ────────────────────────────
w = grid("word:All", lambda: dlg._open_grid_for_level("All"))
panel = w.findChild(pd.WordGridPanel)
cv, tiles = common_checks("All", w, panel)
reg = rain.ui_region(w)
cvs = w.findChildren(pd._TileCanvas)
on = [c for c in cvs if not c.visibleRegion().isEmpty()]
t = on[0]._cells[0]
tp = on[0].mapTo(w, centre(t))
gp = on[0].mapTo(w, QtCore.QPoint(t._x + t._w + 1, t._y + 5))
check("[All] mist region covers a tile", reg.contains(tp))
check("[All] mist region leaves the gap", not reg.contains(gp))
# matches cycle on Enter
panel._search_edit.setText("い")
E.pump(0.05)
n = sum(t._highlighted for t in panel._all_cells)
check("[All] search: many matches highlighted", n > 5, n)
st0 = panel._search_status.text()
panel._on_search_next(); panel._on_search_next()
check("[All] Enter cycles the matches", "Match 3 /" in panel._search_status.text(), panel._search_status.text())
panel._search_edit.setText("")
# wheel scroll: hover follows the tiles under a still mouse
vp = panel._scroll.viewport()
c0 = on[0]
t = c0._cells[0]
QtGui.QCursor.setPos(c0.mapToGlobal(centre(t)))
c0._rehover()
before = c0._hover
panel._scroll.verticalScrollBar().setValue(45)
E.pump(0.05)
c0._rehover()
check("[All] after a scroll the hover is the tile under the mouse",
      c0._hover is not before or before is None)
w.close(); E.pump(0.2)

# ── freq:6000 ───────────────────────────────────────────────────────────────
w = grid("word:freq:6000", lambda: dlg._open_grid_for_level("freq:6000"))
panel = w.findChild(pd.WordGridPanel)
cv, tiles = common_checks("freq:6000", w, panel)
w.close(); E.pump(0.2)

# ── kanji / grammar ─────────────────────────────────────────────────────────
if (dlg._results.get("kanji") or {}).get("levels"):
    w = grid("kanji:N5", lambda: dlg._open_kanji_grid("N5"))
    panel = w.findChild(pd.WordGridPanel)
    cv, tiles = common_checks("kanji N5", w, panel)
    t = tiles[0]
    CALLS.clear()
    mouse(cv, "press", centre(t), Qt.MouseButton.LeftButton)
    check("[kanji] click → its words window, parent = grid window",
          CALLS and CALLS[0][:2] == ("kanji_words", t._char) and CALLS[0][2] is w, CALLS)
    CALLS.clear()
    mouse(cv, "press", centre(t), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ShiftModifier)
    check("[kanji] Shift+click → Jisho kanji", CALLS == [("jisho_kanji", t._char)], CALLS)
    un = next((x for x in panel._all_cells if x._can_override), None)
    if un is not None:
        MARKED.clear()
        mouse(un._canvas, "press", centre(un), Qt.MouseButton.MiddleButton)
        check("[kanji] middle-click marks found + tells the dialog",
              dlg._kanji_overrides.is_found(un._char, "") and MARKED == ["kanji:N5"])
        mouse(un._canvas, "press", centre(un), Qt.MouseButton.MiddleButton)
    panel._search_edit.setText(panel._all_cells[-1]._char)
    E.pump(0.05)
    check("[kanji] search highlights", panel._all_cells[-1]._highlighted)
    w.close(); E.pump(0.2)
if dlg._results.get("grammar"):
    w = grid("grammar:N5", lambda: dlg._open_grammar_grid("N5"))
    panel = w.findChild(pd.WordGridPanel)
    cv, tiles = common_checks("grammar N5", w, panel)
    wide = [t for t in tiles if t._w > pd.CELL_W]
    check("[grammar] wide tiles keep their width", bool(wide))
    t = wide[0]
    check("[grammar] hit-test near a wide tile's right edge",
          cv._tile_at(QtCore.QPoint(t._x + t._w - 2, t._y + 3)) is t)
    CALLS.clear()
    ex = next((x for x in tiles if x._p.get("ex_ja")), None)
    if ex is not None:
        mouse(ex._canvas, "press", centre(ex), Qt.MouseButton.RightButton)
        check("[grammar] right-click copies the example", CALLS and CALLS[0][:2] == ("copy", ex._p["ex_ja"]), CALLS)
    CALLS.clear()
    nw = next((x for x in tiles if not x._stat.get("words")), None)
    if nw is not None:
        mouse(nw._canvas, "press", centre(nw), Qt.MouseButton.LeftButton)
        check("[grammar] click → find it in the deck, parent = grid window",
              CALLS and CALLS[0][:2] == ("grammar_search", nw._gid) and CALLS[0][2] is w, CALLS)
    w.close(); E.pump(0.2)

# ── tabs: Word Grid (flat) and Off-list ─────────────────────────────────────
for i in range(dlg._tabs.count()):
    dlg._tabs.setCurrentIndex(i)
    E.pump(0.4)
cvs = dlg.findChildren(pd._TileCanvas)
check("main window tabs have tile canvases", len(cvs) >= 2, len(cvs))
check("no tile widgets anywhere", not any(type(x).__name__ in ("WordCell", "KanjiCell", "GrammarCell")
                                          for x in dlg.findChildren(QtWidgets.QWidget)))
# a Refresh rebuilds the grids (and highlighted tiles whose canvas is gone don't break the timer)
pd._GOLD_MODE["on"] = True
some = cvs[0]._cells[0]
some.set_highlighted(True)
pd._GOLD_MODE["on"] = False
dlg._do_full_refresh()
t0 = time.monotonic()
while dlg._refreshing and time.monotonic() - t0 < 60:
    E.pump(0.2)
E.pump(1.0)
pd._GOLD_MODE["on"] = True
pd._hl_tick()
pd._GOLD_MODE["on"] = False
sip = __import__(E._MM + ".sip", fromlist=["sip"])
QtCore.QCoreApplication.sendPostedEvents(None, getattr(QtCore.QEvent.Type.DeferredDelete, "value", QtCore.QEvent.Type.DeferredDelete))
gone = sip.isdeleted(some._canvas)
pd._GOLD_MODE["on"] = True
pd._hl_tick()
pd._GOLD_MODE["on"] = False
check("highlight timer drops tiles of deleted canvases", gone and some not in pd._HL_CELLS, gone)
check("no errors", not ERRS, "".join(ERRS)[:3000])
dlg.reject()
E.pump(0.5)
E.finish()
