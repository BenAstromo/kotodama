"""Tile look regression (2026-11-10, grid canvas rewrite): renders every tile
state of the word / kanji / grammar grids offscreen, normal and gold, on a
real _TileCanvas (glow included), and compares two renders pixel by pixel.

    %TEMP%\\qtv\\Scripts\\python.exe -X utf8 t_tiles_look.py render <dir>
    %TEMP%\\qtv\\Scripts\\python.exe -X utf8 t_tiles_look.py compare <dirA> <dirB> [diffdir]

Works on both the widget tiles and the painted ones: it only builds cells
with their constructors, sets `_hovered` / `set_highlighted`, and grabs the
canvas. Uses its own env (KT_ENV) next to the output, deleted after.
"""
import os, sys, shutil, time

MODE = sys.argv[1]
if MODE == "compare":
    from PyQt6 import QtGui
    a, b = sys.argv[2], sys.argv[3]
    diffdir = sys.argv[4] if len(sys.argv) > 4 else None
    bad = 0
    for name in sorted(os.listdir(a)):
        if not name.endswith(".png"):
            continue
        ia, ib = QtGui.QImage(os.path.join(a, name)), QtGui.QImage(os.path.join(b, name))
        if ib.isNull():
            print("MISSING", name); bad += 1; continue
        if ia.size() != ib.size():
            print("SIZE", name, ia.size(), ib.size()); bad += 1; continue
        ia = ia.convertToFormat(QtGui.QImage.Format.Format_ARGB32)
        ib = ib.convertToFormat(QtGui.QImage.Format.Format_ARGB32)
        n, worst = 0, 0
        diff = QtGui.QImage(ia.size(), QtGui.QImage.Format.Format_ARGB32) if diffdir else None
        if diff is not None:
            diff.fill(0xff000000)
        for y in range(ia.height()):
            for x in range(ia.width()):
                pa, pb = ia.pixel(x, y), ib.pixel(x, y)
                if pa != pb:
                    d = max(abs(((pa >> s) & 255) - ((pb >> s) & 255)) for s in (0, 8, 16, 24))
                    worst = max(worst, d)
                    n += 1
                    if diff is not None:
                        diff.setPixel(x, y, 0xffff0000)
        print(("SAME " if n == 0 else "DIFF ") + f"{name}: {n} px differ, worst channel Δ {worst}")
        if n:
            bad += 1
            if diffdir:
                os.makedirs(diffdir, exist_ok=True)
                diff.save(os.path.join(diffdir, name))
    print("ALL SAME" if not bad else f"{bad} differ")
    sys.exit(0)

OUT = os.path.abspath(sys.argv[2])
os.makedirs(OUT, exist_ok=True)
os.environ["KT_ENV"] = os.path.join(OUT, "_env", "addons21")
os.environ["QT_QPA_FONTDIR"] = r"C:\Windows\Fonts"     # offscreen: real Japanese glyphs
import stubenv as E
from PyQt6 import QtCore, QtGui, QtWidgets

pkg = E.load()
pd = E.load("progress_dialog")
kv = E.load("kanji_view")
cs = E.load("card_state")
ov_mod = E.load("overrides")
theme = E.load("theme")
_real_mono = time.monotonic


class _FrozenClock:
    """While painting: the gold search ring pulses with the clock."""
    def __enter__(self):
        time.monotonic = lambda: 1234.5

    def __exit__(self, *a):
        time.monotonic = _real_mono

uf = os.path.join(E.ADDON, "user_files")
ov = ov_mod.Overrides(os.path.join(uf, "t_overrides.json"))
kov = ov_mod.Overrides(os.path.join(uf, "t_kov.json"))
gov = ov_mod.Overrides(os.path.join(uf, "t_gov.json"))

# Words: (display, reading) pairs, each used for one state.
W = [("食べる", "たべる"), ("水", "みず"), ("学校", "がっこう"), ("先生", "せんせい"), ("天気", "てんき"),
     ("テレビ", "テレビ"), ("経済", "けいざい"), ("ご飯", "ごはん"), ("猫", "ねこ"), ("大人", "おとな"),
     ("大学", "だいがく"), ("コーヒー", "コーヒー"), ("パソコン", "パソコン"), ("明日", "あした"),
     ("勉強", "べんきょう"), ("電車", "でんしゃ"), ("友達", "ともだち"), ("時間", "じかん")]
pd._DUP_OF.clear()
pd._DUP_OF[9003] = [9003, 9004]


def word_cells(level, gold):
    """Every state of a word tile at one level ("N5".."N1", "freq", "unlisted")."""
    over = level != "unlisted"
    cells = []
    i = iter(range(1000))

    def mk(nid=None, maturity=None, **k):
        d, r = W[next(i) % len(W)]
        d = d + ("" if not k.pop("salt", 0) else "")
        c = pd.WordCell(d, r, nid, level, ov, overridable=over,
                        rank=k.pop("rank", 120 if level == "freq" else None),
                        maturity=maturity, **k)
        cells.append(c)
        return c

    for m in (cs.NEW, cs.LEARNING, cs.YOUNG, cs.MATURE, None):
        mk(9000 + (m or 0), m)
    mk(9003, cs.MATURE)                                  # ⧉ duplicate
    h = mk(9001, cs.YOUNG); h._hovered = True            # hovered known
    s = mk(9002, cs.MATURE); s.set_highlighted(True)     # search match, known
    if over:
        f = mk(); ov.found.add(ov_mod.key(f._display, f._reading))          # found
        wt = mk(waiting=True); ov.found.add(ov_mod.key(wt._display, wt._reading))
        sp = mk(); ov.suspended.add(ov_mod.key(sp._display, sp._reading))   # suspended
        fh = mk(); ov.found.add(ov_mod.key(fh._display, fh._reading)); fh._hovered = True
        mk(found_row=True) if level == "freq" else None
    mk(new_nid=777)                                      # New (dashed)
    nh = mk(new_nid=778); nh._hovered = True
    mk()                                                 # missing
    mh = mk(); mh._hovered = True
    ms = mk(); ms.set_highlighted(True)                  # search match, missing
    for c in cells:
        c._refresh_tooltip()
    return cells


def kanji_cells():
    chars = "日本人大学生先水火木金土月年時間食飲見聞読書"
    stats, out = {}, []
    for k, ch in enumerate(chars[:8]):
        stats[ch] = {"score": k / 7, "cards": 1 + k, "best": cs.MATURE, "words": [("日本", 3, 1)]}
    stats[chars[8]] = {"pending": True, "words": [("水曜", 0, 2)]}
    kres = {"stats": stats, "deck": "Main", "learn": {}}
    for ch in chars[:9]:
        out.append(kv.KanjiCell(ch, "N5", kres, kov))
    f = kv.KanjiCell(chars[9], "N4", kres, kov); kov.found.add(ov_mod.key(chars[9], "")); out.append(f)
    s = kv.KanjiCell(chars[10], "N3", kres, kov); kov.suspended.add(ov_mod.key(chars[10], "")); out.append(s)
    for ch in chars[11:14]:
        out.append(kv.KanjiCell(ch, "N2", kres, kov))
    out.append(kv.KanjiCell(chars[14], "offlist", kres, kov))
    out[2]._hovered = True
    out[12]._hovered = True
    out[3].set_highlighted(True)
    out[13].set_highlighted(True)
    for c in out:
        c._refresh_tooltip()
    return out


def grammar_cells():
    gd = E.load("grammar_data")
    ids = list(gd.data())[:14]
    stats = {}
    for k, g in enumerate(ids[:6]):
        stats[g] = {"score": k / 5, "cards": 2, "best": cs.YOUNG, "words": [("文", 2, 5)]}
    stats[ids[6]] = {"words": [("文", 0, 6)]}
    gres = {"stats": stats, "deck": "Main"}
    out = [kv.GrammarCell(g, gres, gov) for g in ids]
    gov.found.add(ov_mod.key(ids[7], ""))
    gov.suspended.add(ov_mod.key(ids[8], ""))
    out[1]._hovered = True
    out[10]._hovered = True
    out[2].set_highlighted(True)
    out[11].set_highlighted(True)
    for c in out:
        c._refresh_tooltip()
    return out


def render(name, cells, glow, gold, width=560):
    pd._GOLD_MODE["on"] = gold
    host = QtWidgets.QDialog()
    theme.apply(host, gold=gold)
    host.setStyleSheet(host.styleSheet() + " QDialog#kotodama { background: #121212; }")
    lay = QtWidgets.QVBoxLayout(host)
    lay.setContentsMargins(0, 0, 0, 0)
    canvas = pd._TileCanvas(cells, glow=glow)
    lay.addWidget(canvas)
    host.resize(width, 400)
    host.show()
    E.pump(0.05)
    host.resize(width, canvas.minimumHeight())
    E.pump(0.05)
    with _FrozenClock():
        img = host.grab(canvas.geometry()).toImage()
    img.save(os.path.join(OUT, name + ".png"))
    host.hide()
    host.deleteLater()
    E.pump(0.02)


for gold in (False, True):
    sfx = "_gold" if gold else ""
    for lvl in ("N5", "N4", "N3", "N2", "N1", "freq", "unlisted"):
        glow = pd.UNLISTED_FG if lvl == "unlisted" else True
        render(f"word_{lvl}{sfx}", word_cells(lvl, gold), glow, gold)
    render(f"kanji{sfx}", kanji_cells(), "blend", gold)
    render(f"grammar{sfx}", grammar_cells(), "blend", gold, width=700)
print("rendered", len([n for n in os.listdir(OUT) if n.endswith(".png")]), "images to", OUT)
shutil.rmtree(os.path.join(OUT, "_env"), ignore_errors=True)
os._exit(0)
