"""New-user / other-PC robustness: one scenario per run (argv[1]).
Drives the real add-on (copy in the scratch env): the deck-list widget, the
main window (every tab, grids), Refresh, close. Any traceback = FAIL."""
import io, os, sys, time, traceback
SC = sys.argv[1]
QT_MSGS = []
if SC == "unicode":
    # guide item 15: a non-ASCII path must not break the style sheet
    _QC = __import__(("PyQt5" if os.environ.get("KT_QT") == "5" else "PyQt6") + ".QtCore", fromlist=["QtCore"])
    _QC.qInstallMessageHandler(lambda _t, _c, m: QT_MSGS.append(m))
    os.environ["KT_ENV"] = os.path.join(os.path.dirname(os.path.abspath(__file__)), "環境 ü ベン", "addons21")
import stubenv as E
import mkcol

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
         ("経済", "けいざい", (2, 2, 100)), ("ご飯", "ごはん", (2, 2, 12))]
SENTS = ["私は毎日学校に行きます。", "昨日は雨が降ったので、家で本を読みました。", "水を飲みたいです。"]

deck = "Main"
nts = {"Vocab": ["Word", "Reading", "Sentence"], "SentOnly": ["Sentence"]}
notes = [(deck, "Vocab", {"Word": w, "Reading": r, "Sentence": SENTS[i % 3]}, c)
         for i, (w, r, c) in enumerate(WORDS)]
notes += [(deck, "SentOnly", {"Sentence": s}, (2, 2, 25)) for s in SENTS]
maps = [{"note_type": "Vocab", "field": "Word", "reading_field": "Reading", "sentence_field": "Sentence"},
        {"note_type": "SentOnly", "field": "", "reading_field": "", "sentence_field": "Sentence"}]

if SC == "fresh":
    col = mkcol.Col(nts, [deck], notes)
    maps = []
    deck = ""
elif SC == "empty":
    col = mkcol.Col(nts, [deck], [])
elif SC == "nofield":
    col = mkcol.Col({"Lapis": ["Expression", "ExpressionReading"]}, [deck],
                    [(deck, "Lapis", {"Expression": w, "ExpressionReading": r}, c) for w, r, c in WORDS])
    maps = [{"note_type": "Lapis", "field": "Word", "reading_field": "Reading", "sentence_field": "Sentence"},
            {"note_type": "Gone", "field": "Word", "reading_field": "", "sentence_field": ""}]
elif SC == "baddeck":
    deck = 'Core_2k "best"*'
    col = mkcol.Col(nts, [deck, "Core 2k \"best\"x"], [(deck, *n[1:]) for n in notes]
                    + [("Core 2k \"best\"x", "Vocab", {"Word": "猫", "Reading": "ねこ"}, (2, 2, 30))])
elif SC == "tworows":
    # guide item 8: two "(all note types)" rows, different field names
    col = mkcol.Col({"A": ["Word", "Sentence"], "B": ["Expression", "SentenceJP"]}, [deck],
                    [(deck, "A", {"Word": "学校", "Sentence": SENTS[0]}, (2, 2, 30)),
                     (deck, "B", {"Expression": "水", "SentenceJP": SENTS[2]}, (2, 2, 30))])
    maps = [{"note_type": "", "field": "Word", "reading_field": "", "sentence_field": "Sentence"},
            {"note_type": "", "field": "Expression", "reading_field": "", "sentence_field": "SentenceJP"}]
elif SC == "nodeck":
    col = mkcol.Col(nts, ["Other"], [])
    deck = "Deleted deck"
else:                       # normal, corrupt, unicode, oldcfg, fail
    col = mkcol.Col(nts, [deck], notes)

E.mw.col = col
E.CFG.update(deck_name=deck, field_mappings=maps)
if SC == "oldcfg":
    # an old / partial config: most keys missing (an early version's meta.json)
    for k in list(E.CFG):
        if k not in ("deck_name", "field_mappings"):
            del E.CFG[k]
    E.CFG["lists"] = {"N5": {"mode": "bundled"}}         # partial lists block

uf = os.path.join(E.ADDON, "user_files")
if SC == "corrupt":
    for name in ("overrides.json", "kanji_overrides.json", "grammar_overrides.json", "history.json",
                 "parse_cache.json", "nakama.json", "goal_days.json", "found_count.json"):
        with open(os.path.join(uf, name), "w", encoding="utf-8") as f:
            f.write('{"broken": [1, 2')
    with open(os.path.join(uf, "words_cache.json"), "wb") as f:
        f.write(b"\xff\xfe\x00garbage")

pkg = E.load()
pd = E.load("progress_dialog")
mwid = E.load("mini_widget")


class Content:
    stats = ""


def widget():
    c = Content()
    mwid._on_deck_browser_will_render_content(None, c)
    return c.stats


widget()
E.pump(3.0)
html = widget()
E.check(f"[{SC}] deck-list widget drew without errors", not ERRS)
if SC not in ("fresh",):
    E.check(f"[{SC}] widget has content", bool(html) or SC in ("nodeck",))

if SC == "fresh":
    E.check("[fresh] Add-ons → Config opens Settings", bool(E.LOG.get("config_action")))
    E.check("[fresh] deck list shows the set-up card",
            "Click to set up" in html and "jlpt_open_progress" in html)
    pkg._open_progress_dialog(dict(E.CFG))
    E.check("[fresh] asks for a deck", any("deck" in str(w).lower() for w in E.LOG["warnings"]))
    E.finish()

if SC == "normal":
    # guide item 3: no precount once the user has gone to review
    E.mw.state = "review"
    pkg._prep["key"] = pkg._prep["out"] = None
    pkg.prepare_dialog()
    E.check("[normal] prepare_dialog starts nothing while reviewing", pkg._prep["running"] is None)
    E.mw.state = "deckBrowser"

if SC == "fail":
    # guide item 16: a failing count shows a warning with the traceback
    def boom(*a, **k):
        raise IndexError("list index out of range")
    pkg._dialog_work = boom
    E.LOG["warnings"].clear()
    pkg._prep["key"] = pkg._prep["out"] = None
    pkg._open_progress_dialog(dict(E.CFG))
    E.pump(2.0)
    E.check("[fail] warning names the report address and holds the traceback",
            any("Traceback" in str(w) and "issues" in str(w) for w in E.LOG["warnings"]))
    E.check("[fail] a second click can open again", not pkg._opening["busy"])
    E.finish()

if SC == "tworows":
    sp = E.load("sentence_parser")
    texts = sp.sentence_texts(deck, maps)
    E.check("[tworows] both rows' sentences are read", sorted(texts.values()) == sorted([SENTS[0], SENTS[2]]))

if SC == "nodeck":
    # guide item 7: no zero snapshot recorded, a warning instead of a window
    E.check("[nodeck] widget shows nothing", not html)
    hp = os.path.join(uf, "history.json")
    snap = False
    if os.path.exists(hp):
        import json
        try:
            snap = deck in json.dumps(json.load(open(hp, encoding="utf-8")), ensure_ascii=False)
        except Exception:
            snap = False
    E.check("[nodeck] no snapshot written for the missing deck", not snap)
    ok = pkg._open_progress_dialog(dict(E.CFG))
    E.check("[nodeck] window refused", ok is False)
    E.check("[nodeck] warns that the deck can't be found",
            any("can't find the deck" in str(w) for w in E.LOG["warnings"]))
    E.check("[nodeck] no errors", not ERRS)
    E.finish()

ok = pkg._open_progress_dialog(dict(E.CFG))
t0 = time.monotonic()
dlg = None
while time.monotonic() - t0 < 60:
    E.pump(0.2)
    dl = [w for w in E.app.topLevelWidgets() if isinstance(w, pd.ProgressDialog) and w.isVisible()]
    if dl:
        dlg = dl[0]
        break
E.check(f"[{SC}] main window opened", dlg is not None)
if dlg is None:
    print("warnings:", E.LOG["warnings"])
    E.finish()
E.pump(1.0)
_texts = [w.text() for w in dlg.findChildren(E.QtWidgets.QLabel)]
_read_none = any("read no words from your" in t for t in _texts)
_no_study = any("No studied cards in this deck yet" in t for t in _texts)
if SC == "nofield":
    E.check("[nofield] says no words were read and points to Settings", _read_none)
elif SC == "empty":
    E.check("[empty] says nothing has been studied yet", _no_study)
else:
    E.check(f"[{SC}] no empty-deck hint", not _read_none and not _no_study)
for i in range(dlg._tabs.count()):
    dlg._tabs.setCurrentIndex(i)
    E.pump(0.6)
E.check(f"[{SC}] every tab built without errors", not ERRS)
for lvl in ("N5", "All", "freq:6000"):
    dlg._open_grid_for_level(lvl)
    E.pump(0.4)
if dlg._kanji_tab is not None and (dlg._results.get("kanji") or {}).get("levels"):
    dlg._open_kanji_grid("N5"); E.pump(0.3)
if dlg._kanji_tab is not None and dlg._results.get("grammar"):
    dlg._open_grammar_grid("N5"); E.pump(0.3)
E.check(f"[{SC}] grids opened without errors", not ERRS)
dlg._do_full_refresh()
t0 = time.monotonic()
while dlg._refreshing and time.monotonic() - t0 < 60:
    E.pump(0.2)
E.pump(1.0)
E.check(f"[{SC}] Refresh finished without errors", not dlg._refreshing and not ERRS)
dlg.reject()
E.pump(1.0)
widget(); E.pump(2.0); widget()
E.check(f"[{SC}] closed, widget redrawn, no errors", not ERRS)
if SC == "unicode":
    bad = [m for m in QT_MSGS if "Could not parse stylesheet" in m]
    E.check("[unicode] every style sheet parsed", not bad)
if SC == "corrupt":
    for name in ("overrides.json", "history.json"):
        p = os.path.join(uf, name)
        try:
            import json
            json.load(open(p, encoding="utf-8"))
            good = True
        except Exception:
            good = False
        print(f"  {name}: {'valid JSON now' if good else 'still broken'}; files: "
              + ", ".join(sorted(n for n in os.listdir(uf) if name.split('.')[0] in n)))
if ERRS:
    print("---- errors ----")
    print("".join(ERRS)[:6000])
E.finish()
