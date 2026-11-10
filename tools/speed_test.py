"""Large-deck speed test (2026-10-17): times the add-on's real analysis on a
synthetic collection of N notes, to see how a stranger's 30k+ card deck
would feel. Report only: nothing in the add-on is changed.

    python -I -X utf8 tools/speed_test.py <scratch dir> <jpn_sentences.tsv> [notes ...]

Default sizes: 30000 60000. For each size it builds <scratch>/big_<N>.anki2
(an sqlite file with just the tables the add-on's queries touch: notetypes,
fields, decks, notes, cards) and times every stage the main window runs,
twice: session 1 = a fresh Anki session with no caches on disk, session 2 =
the next Anki session (fresh import, the parse / words caches from disk).
Never touches the owner's collection or the add-on's user_files/ (the parse
cache, words cache and found count are pointed at the scratch dir).

Since the speed fixes (2026-10-17) the window's and the mini widget's
analysis run off Anki's main thread, so these seconds are a wait with Anki
responsive, not a freeze; the "change check" is what the deck list still
runs on the main thread on every redraw.

Deck shape: 2/3 "Vocab" notes (Word / Reading / Sentence: a JLPT or frequency
word + a random Tatoeba sentence), 1/3 "Sentence" notes (only a Sentence
field: a sentence card, parsed for vocab too). Cards: 15% new, 5% learning,
40% young, 40% mature; 3% suspended.

Caveat: the real Anki answers find_notes / get_note from its Rust backend;
here they are sqlite queries, which are about as fast per note. The times
are for this PC (single thread, Python 3.14 here vs Anki's 3.13).
"""
import ctypes, json, os, random, sqlite3, sys, time, types

sys.stdout.reconfigure(encoding="utf-8")
ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRATCH, CORPUS = sys.argv[1], sys.argv[2]
SIZES = [int(a) for a in sys.argv[3:]] or [30000, 60000]
if os.path.abspath(SCRATCH).startswith(os.path.abspath(ADDON)):
    sys.exit("scratch dir must be outside the add-on folder")
os.makedirs(SCRATCH, exist_ok=True)
DECK = "Big"


def peak_mb() -> float:
    """Peak working set of this process (Windows), in MB; 0 elsewhere."""
    if os.name != "nt":
        return 0.0
    from ctypes import wintypes

    class PMC(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                    ("a", ctypes.c_size_t), ("b", ctypes.c_size_t), ("c", ctypes.c_size_t),
                    ("d", ctypes.c_size_t), ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]
    pmc = PMC(); pmc.cb = ctypes.sizeof(PMC)
    k32, psapi = ctypes.windll.kernel32, ctypes.windll.psapi
    k32.GetCurrentProcess.restype = wintypes.HANDLE      # 64-bit handle, or the call reads nothing
    psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(PMC), wintypes.DWORD]
    psapi.GetProcessMemoryInfo(k32.GetCurrentProcess(), ctypes.byref(pmc), pmc.cb)
    return pmc.PeakWorkingSetSize / 1e6


def words():
    out = []
    for name in ("jlpt_n5.txt", "jlpt_n4.txt", "jlpt_n3.txt", "jlpt_n2.txt", "jlpt_n1.txt", "freq_bccwj.txt"):
        for line in open(os.path.join(ADDON, name), encoding="utf-8"):
            if line.strip() and not line.startswith("#"):
                p = line.rstrip("\n").split("\t")
                out.append((p[0], p[1] if len(p) > 1 else ""))
    return out


def build(path, n, rng):
    if os.path.exists(path):
        os.remove(path)
    db = sqlite3.connect(path)
    db.executescript("""
        create table notetypes (id integer primary key, name text);
        create table fields (ntid integer, ord integer, name text);
        create table decks (id integer primary key, name text);
        create table notes (id integer primary key, mid integer, mod integer, flds text);
        create table cards (id integer primary key, nid integer, did integer, odid integer,
                            mod integer, type integer, queue integer, ivl integer, factor integer,
                            lapses integer, data text);""")
    db.executemany("insert into notetypes values (?,?)", [(1, "Vocab"), (2, "Sentence")])
    db.executemany("insert into fields values (?,?,?)",
                   [(1, 0, "Word"), (1, 1, "Reading"), (1, 2, "Sentence"), (2, 0, "Sentence")])
    db.execute("insert into decks values (1, ?)", (DECK,))
    ws = words()
    rng.shuffle(ws)
    sents = []
    with open(CORPUS, encoding="utf-8") as f:
        for line in f:
            p = line.rstrip("\n").split("\t")
            if len(p) >= 3 and 6 <= len(p[2]) <= 60:
                sents.append(p[2])
    rng.shuffle(sents)
    notes, cards = [], []
    for i in range(n):
        nid = 1_600_000_000_000 + i
        if i % 3 == 2:
            notes.append((nid, 2, nid // 1000, sents[i % len(sents)]))
        else:
            w, r = ws[i % len(ws)]
            notes.append((nid, 1, nid // 1000, "\x1f".join((w, r, sents[i % len(sents)]))))
        x = rng.random()
        ctype, ivl = (0, 0) if x < .15 else (1, 0) if x < .20 else (2, rng.randint(1, 20)) if x < .60 else (2, rng.randint(21, 900))
        queue = -1 if rng.random() < .03 else ctype
        cards.append((nid, nid, 1, 0, nid // 1000, ctype, queue, ivl, 2500, 0, ""))
    db.executemany("insert into notes values (?,?,?,?)", notes)
    db.executemany("insert into cards values (?,?,?,?,?,?,?,?,?,?,?)", cards)
    db.commit()
    return db


def stub_anki(db):
    """The harness's fake mw.col over the synthetic sqlite file."""
    ntypes = {i: n for i, n in db.execute("select id,name from notetypes")}
    fields = {}
    for ntid, _o, name in db.execute("select ntid,ord,name from fields order by ntid,ord"):
        fields.setdefault(ntid, []).append(name)

    class Note(dict):
        def __init__(self, mid, flds):
            super().__init__(zip(fields[mid], flds.split("\x1f")))
            self._nt = {"name": ntypes[mid]}

        def note_type(self):
            return self._nt

    class Col:
        def _where(self, q):
            name = q.split('"deck:', 1)[1].split('"', 1)[0].replace("::", "\x1f")
            dids = [i for i, nm in db.execute("select id,name from decks") if nm == name or nm.startswith(name + "\x1f")]
            qs = ",".join(map(str, dids))
            w = f"(did in ({qs}) or odid in ({qs}))"
            if "-is:new" in q:
                w += " and type != 0"
            if "-is:suspended" in q:
                w += " and queue != -1"
            if " is:review" in q:
                w += " and type in (2,3)"
            return w

        def find_notes(self, q):
            return [r[0] for r in db.execute(f"select distinct nid from cards where {self._where(q)}")]

        def find_cards(self, q):
            return [r[0] for r in db.execute(f"select id from cards where {self._where(q)}")]

        class _DB:
            def all(self, sql, *a):
                return db.execute(sql, a).fetchall()

            def first(self, sql, *a):
                return db.execute(sql, a).fetchone()

            def scalar(self, sql, *a):
                r = db.execute(sql, a).fetchone()
                return r[0] if r else None
        db = _DB()

        class _Models:
            def get(self, mid):
                return {"name": ntypes[mid],
                        "flds": [{"name": n, "ord": i} for i, n in enumerate(fields[mid])]}
        models = _Models()

        def get_note(self, nid):
            mid, flds = db.execute("select mid,flds from notes where id=?", (nid,)).fetchone()
            return Note(mid, flds)

    class _Any:
        def __init__(s, *a, **k): pass
        def __getattr__(s, n): return _Any()
        def __call__(s, *a, **k): return _Any()
        def __or__(s, o): return s

    aqt = types.ModuleType("aqt")
    aqt.mw = types.SimpleNamespace(col=Col(), form=_Any(), state="deckBrowser")
    aqt.gui_hooks = types.SimpleNamespace(**{h: [] for h in (
        "deck_browser_will_render_content", "webview_did_receive_js_message", "profile_did_open",
        "state_did_change", "state_will_change", "reviewer_will_answer_card", "reviewer_did_answer_card", "webview_will_set_content")})
    qt = types.ModuleType("aqt.qt")
    names = ["QAction", "QMenu", "QObject", "QDialog", "QWidget", "QGroupBox", "QColor", "pyqtSignal", "QFont", "QStyledItemDelegate", "QTimer", "QLabel"]
    for nm in names:
        setattr(qt, nm, _Any)
    qt.__all__ = names
    utils = types.ModuleType("aqt.utils"); utils.showWarning = print; utils.tooltip = print
    anki = types.ModuleType("anki"); au = types.ModuleType("anki.utils")
    au.ids2str = lambda ids: "(" + ",".join(str(i) for i in ids) + ")"
    sys.modules.update({"aqt": aqt, "aqt.qt": qt, "aqt.utils": utils, "anki": anki, "anki.utils": au})
    return aqt.mw


def session(n, label, cfg, times):
    """One Anki session: a fresh import of the add-on (cold in-memory
    caches), with the caches on disk as the previous session left them."""
    for m in [m for m in sys.modules if m == "jlpt_progress" or m.startswith("jlpt_progress.")]:
        del sys.modules[m]
    import jlpt_progress as jp
    from jlpt_progress import jlpt_data, card_state, grammar_data, kanji_data, mini_widget, sentence_parser
    from jlpt_progress.overrides import Overrides
    grammar_data._PCACHE_PATH = os.path.join(SCRATCH, f"parse_cache_{n}.json")
    words_path = os.path.join(SCRATCH, f"words_cache_{n}.json")
    sentence_parser._words_cache_path = lambda: words_path
    card_state._FOUND_PATH = os.path.join(SCRATCH, "found_count.json")
    card_state._found_cache = None
    from jlpt_progress import history
    history.record_auto = lambda *a, **k: None     # never write the owner's history.json
    history.record = lambda *a, **k: None
    jp._cfg = lambda: cfg
    print(f"  -- {label}")
    tag = label.split(" (")[0]

    def stage(name, fn):
        t0 = time.perf_counter()
        r = fn()
        times[f"{tag}: {name}"] = time.perf_counter() - t0
        print(f"    {name:52} {times[f'{tag}: {name}']:7.2f}s")
        return r

    t_open = time.perf_counter()
    lists = stage("load JLPT lists", lambda: jlpt_data.build_lists({}))
    ur = jp._build_unique_readings(lists)
    di, ri, nd, nr = stage("collect_words (notes + sentence cards parsed)",
                           lambda: jp.collect_words(DECK, cfg["field_mappings"], True))
    res = stage("analyse (JLPT match + frequency)", lambda: jp.analyse(di, ri, nd, nr, lists, ur, overrides=Overrides()))
    stage("note_maturity", lambda: card_state.note_maturity(DECK, True))
    stage("kanji analyse", lambda: kanji_data.analyse(cfg, DECK, nd))
    stage("grammar analyse", lambda: grammar_data.analyse(cfg))
    name = "= window open (sum of the above)"
    times[f"{tag}: {name}"] = time.perf_counter() - t_open
    print(f"    {name:52} {times[f'{tag}: {name}']:7.2f}s")
    stage("Refresh (same session: scans + analyses again)", lambda: (
        jp.analyse(*jp.collect_words(DECK, cfg["field_mappings"], True), lists, ur, overrides=Overrides()),
        kanji_data.analyse(cfg, DECK, nd), grammar_data.analyse(cfg)))
    stage("rank_count (runs after each new/learning answer)", lambda: card_state.rank_count(DECK, True))
    mini_widget.invalidate_cache()
    stage("mini widget recount (after a change)", lambda: mini_widget._compute_results(force=True))
    stage("mini widget change check (every deck-list redraw)", lambda: mini_widget.cached_results())
    return res, nd


def main():
    rng = random.Random(20261017)
    sys.path.insert(0, os.path.dirname(ADDON))
    results_all = []
    for n in SIZES:
        path = os.path.join(SCRATCH, f"big_{n}.anki2")
        t = time.perf_counter()
        db = build(path, n, rng)
        print(f"\n=== {n:,} notes (built in {time.perf_counter() - t:.1f}s: {path})")
        stub_anki(db)
        for f in (f"parse_cache_{n}.json", f"words_cache_{n}.json"):
            if os.path.exists(os.path.join(SCRATCH, f)):
                os.remove(os.path.join(SCRATCH, f))
        cfg = {"deck_name": DECK, "ignore_suspended_cards": True, "lists": {},
               "field_mappings": [{"note_type": "Vocab", "field": "Word", "reading_field": "Reading", "sentence_field": "Sentence"},
                                  {"note_type": "Sentence", "field": "", "reading_field": "", "sentence_field": "Sentence"}],
               "kanji_source": {"mode": "vocab", "deck": "", "mappings": []},
               "grammar_source": {"mode": "sentence", "deck": "", "mappings": []}}
        times = {}
        session(n, "session 1 (first ever: no caches on disk)", cfg, times)
        res, nd = session(n, "session 2 (next Anki session: caches from disk)", cfg, times)
        peak = peak_mb()
        print(f"  peak process memory so far {peak:,.0f} MB; notes scanned {len(nd):,}; "
              f"N5 known {len(res['N5']['known_words'])}, N1 known {len(res['N1']['known_words'])}")
        db.close()
        results_all.append((n, times, peak))
    print("\nsummary (seconds)")
    keys = list(results_all[0][1])
    print("  " + "stage".ljust(66) + "".join(f"{n:>10,}" for n, _t, _p in results_all))
    for k in keys:
        print("  " + k[:66].ljust(66) + "".join(f"{t[k]:10.2f}" for _n, t, _p in results_all))


if __name__ == "__main__":
    main()
