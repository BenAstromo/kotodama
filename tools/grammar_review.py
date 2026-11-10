"""Grammar detection review page (owner request 2026-10-09).

Runs the real sentence grammar detection (grammar_data.sentence_ids) over a
read-only copy of the collection and writes tools/grammar_review.html: every
detected point (N1 first) with the deck sentences that triggered it, the
triggering text highlighted, and a checkbox per sentence to flag a wrong
detection. Flags are kept in the page (localStorage) and copied out with
"Copy flagged"; they become _CONTEXT / _NOT_AFTER fixes in grammar_data.

    python -I -X utf8 tools/grammar_review.py <dir with col_copy.anki2> [--check old_parse_cache.json]

--check: also compare each sentence's ids with an earlier parse_cache.json
(the cache stores text → ids) and print the differences.

Corpus mode (2026-10-14), for points the owner's deck never triggers:

    python -I -X utf8 tools/grammar_review.py --corpus <jpn_sentences.tsv> [--per-point 8]

reads Tatoeba's Japanese export (id<TAB>jpn<TAB>sentence; CC BY 2.0 FR,
https://tatoeba.org/downloads) and shows up to N detections per point
(a fixed sample, so the page is the same on every run) in
tools/grammar_review_corpus.html, with its own saved ticks.

The Browser pane refuses file:/// for generated pages: serve tools/ with the
.claude/launch.json "grammar-review" server (port 47391). Delete the pages
once reviewed.
"""
import hashlib, html, json, os, sqlite3, sys, types

sys.stdout.reconfigure(encoding="utf-8")
CORPUS = sys.argv[sys.argv.index("--corpus") + 1] if "--corpus" in sys.argv else None
PER_POINT = int(sys.argv[sys.argv.index("--per-point") + 1]) if "--per-point" in sys.argv else 8
S = None if CORPUS else sys.argv[1]
ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if CORPUS:
    db = sqlite3.connect(":memory:")
    db.execute("create table notetypes (id, name)")
    db.execute("create table fields (ntid, ord, name)")
else:
    db = sqlite3.connect(os.path.join(S, "col_copy.anki2"))
ntypes = {i: n for i, n in db.execute("select id,name from notetypes")}
fields = {}
for ntid, ord_, name in db.execute("select ntid,ord,name from fields order by ntid,ord"):
    fields.setdefault(ntid, []).append(name)


class Note(dict):
    def __init__(self, mid, flds):
        super().__init__(zip(fields[mid], flds.split("\x1f")))
        self._nt = {"name": ntypes[mid]}

    def note_type(self):
        return self._nt


class Col:   # the searches card_state.deck_search builds (see tools/harness.py)
    def _where(self, q):
        name = q.split('"deck:', 1)[1].split('"', 1)[0].replace("::", "\x1f")
        dids = [i for i, n in db.execute("select id,name from decks") if n == name or n.startswith(name + "\x1f")]
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
    db = _DB()

    class _Models:   # card_state.deck_notes reads the notes table in bulk (2026-10-17)
        def get(self, mid):
            return {"name": ntypes[mid], "flds": [{"name": n, "ord": i} for i, n in enumerate(fields[mid])]}
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
aqt.mw = types.SimpleNamespace(col=Col(), form=types.SimpleNamespace(menuTools=types.SimpleNamespace(addAction=lambda a: None), menubar=types.SimpleNamespace(insertMenu=lambda *a: None), menuHelp=types.SimpleNamespace(menuAction=lambda: None)))
aqt.gui_hooks = types.SimpleNamespace(deck_browser_will_render_content=[], webview_did_receive_js_message=[],
                                      profile_did_open=[], state_did_change=[], state_will_change=[], reviewer_will_answer_card=[],
                                      reviewer_did_answer_card=[], webview_will_set_content=[])
qt = types.ModuleType("aqt.qt")
for n in ["QAction", "QMenu", "QObject", "QDialog", "QWidget", "QGroupBox", "QColor", "pyqtSignal", "QFont", "QStyledItemDelegate", "QLabel"]:
    setattr(qt, n, _Any)
utils = types.ModuleType("aqt.utils"); utils.showWarning = print; utils.tooltip = print
anki = types.ModuleType("anki"); anki_utils = types.ModuleType("anki.utils")
anki_utils.ids2str = lambda ids: "(" + ",".join(str(i) for i in ids) + ")"
sys.modules.update({"aqt": aqt, "aqt.qt": qt, "aqt.utils": utils, "anki": anki, "anki.utils": anki_utils})
sys.path.insert(0, os.path.dirname(ADDON))
pkg = os.path.basename(ADDON)
grammar_data = __import__(pkg + ".grammar_data", fromlist=["x"])
sentence_parser = __import__(pkg + ".sentence_parser", fromlist=["x"])
card_state = __import__(pkg + ".card_state", fromlist=["x"])

if CORPUS:
    texts = {}
    with open(CORPUS, encoding="utf-8") as f:
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) >= 3 and parts[2].strip():
                texts[int(parts[0])] = sentence_parser.clean(parts[2])
    maturity = {}
else:
    cfg = json.load(open(os.path.join(ADDON, "meta.json"), encoding="utf-8"))["config"]
    deck = cfg["deck_name"]
    texts = sentence_parser.sentence_texts(deck, cfg["field_mappings"])
    maturity = card_state.note_maturity(deck, cfg.get("ignore_suspended_cards", False))

if "--check" in sys.argv:
    old = json.load(open(sys.argv[sys.argv.index("--check") + 1], encoding="utf-8"))["ids"]
    diffs = 0
    for text in sorted(set(texts.values())):
        if text in old:
            new = grammar_data.sentence_ids(text)
            if sorted(new) != sorted(old[text]):
                diffs += 1
                print("DIFF", text, "| lost", sorted(set(old[text]) - set(new)),
                      "| gained", sorted(set(new) - set(old[text])))
    print(f"--check: {diffs} sentences differ")

points = grammar_data.data()
by_point: dict[str, list] = {}
hits: dict[str, int] = {}
# Corpus mode: a fixed pseudo-random order (by id hash), keeping the first
# PER_POINT hits of each point.
order_ids = sorted(texts, key=lambda n: hashlib.md5(str(n).encode()).hexdigest()) if CORPUS else list(texts)
for i, nid in enumerate(order_ids):
    if CORPUS and i % 20000 == 0:
        print(f"  {i:,} / {len(order_ids):,}", flush=True)
    text = texts[nid]
    spans: dict = {}
    grammar_data.sentence_ids(text, spans)
    split = None
    state = None if CORPUS else maturity.get(nid, card_state.NEW)
    for gid, sp in spans.items():
        if gid not in points:
            continue
        hits[gid] = hits.get(gid, 0) + 1
        if CORPUS and len(by_point.get(gid, ())) >= PER_POINT:
            continue
        if split is None:
            split = " ".join(t[0] for t in sentence_parser.tokens(text) if t[1] != "punct" or t[0].strip())
        by_point.setdefault(gid, []).append({
            "nid": nid, "t": text, "s": sorted(set(map(tuple, sp))), "st": state, "sp": split})

order = {lvl: i for i, lvl in enumerate(["N1", "N2", "N3", "N4", "N5"])}
rows = []
for gid in sorted(by_point, key=lambda g: (order.get(points[g]["level"], 9), list(points).index(g))):
    p = points[gid]
    sents = sorted(by_point[gid], key=lambda x: (-(x["st"] or 0), len(x["t"])))
    rows.append({"id": gid, "lvl": p["level"], "pat": p["pattern"], "mean": p.get("meaning", ""),
                 "form": p.get("formation", ""), "hits": hits.get(gid, 0),
                 "learned": sum(1 for x in sents if (x["st"] or 0) >= card_state.YOUNG),
                 "sents": sents})

if CORPUS:
    summary = (f"Tatoeba: {len(texts):,} sentences · {len(rows)} points detected · "
               f"up to {PER_POINT} sentences shown per point")
else:
    learned_pts = sum(1 for r in rows if r["learned"])
    summary = (f"{len(texts):,} sentences · {len(rows)} points detected "
               f"({learned_pts} in a learned card, which is what counts)")
print(summary)

if "--text" in sys.argv:
    # Plain-text version for an outside review (owner 2026-10-14: "so Gemini
    # can analyse them"): every detected point with its sentences, the text
    # that triggered it in 【】, and the parser's word split.
    tpath = sys.argv[sys.argv.index("--text") + 1]
    lines = [
        "JLPT GRAMMAR DETECTION REVIEW",
        "",
        "An Anki add-on detects JLPT grammar points in Japanese sentences with a rule-based",
        "parser (no MeCab). Below is every grammar point it detected in "
        + ("a sample of Tatoeba sentences" if CORPUS else "the owner's sentence cards")
        + ", with up to " + str(PER_POINT) + " sentences each.",
        "For each sentence, 【】 marks the text that triggered the detection, and 'split:' shows",
        "how the parser divided the sentence into words.",
        "",
        "TASK: for every sentence, judge whether the grammar point is REALLY used there with the",
        "listed meaning (a false positive is e.g. the same kana inside another word, a different",
        "grammar point with the same form, or a lexical compound). Then, per point, describe the",
        "pattern behind the wrong hits as a concrete rule the parser could check (what comes",
        "before/after, which words to exclude), and flag points that are wrong so often they",
        "should not be auto-detected at all. Also note obvious parser split errors.",
        "Answer per point as: ID, sentence numbers that are wrong, and the rule.",
        "",
        summary,
        "",
    ]
    for r in rows:
        lines.append("=" * 78)
        lines.append(f"[{r['lvl']}] {r['id']}  —  {r['pat']}")
        if r["mean"]:
            lines.append(f"Meaning: {r['mean']}")
        if r["form"]:
            lines.append(f"Formation: {r['form']}")
        lines.append(f"Hits in {'Tatoeba' if CORPUS else 'deck'}: {r['hits']:,}"
                     + ("" if CORPUS else f" · in a learned card: {r['learned']}"))
        for i, s in enumerate(r["sents"], 1):
            t = s["t"]
            marked = ""
            pos = 0
            for a, b in s["s"]:
                if a < pos:
                    continue
                marked += t[pos:a] + "【" + t[a:b] + "】"
                pos = b
            marked += t[pos:]
            lines.append(f"  {i}. {marked}")
            lines.append(f"     split: {s['sp']}")
        lines.append("")
    open(tpath, "w", encoding="utf-8", newline="\n").write("\n".join(lines))
    print("wrote", tpath)

page = open(os.path.join(ADDON, "tools", "grammar_review_template.html"), encoding="utf-8").read()
page = (page.replace("/*DATA*/null", json.dumps(rows, ensure_ascii=False)).replace("{{SUMMARY}}", html.escape(summary))
        .replace("{{KEY}}", "jlpt_grammar_review_corpus_v1" if CORPUS else "jlpt_grammar_review_v1")
        .replace("/*CORPUS*/false", "true" if CORPUS else "false"))
out = os.path.join(ADDON, "tools", "grammar_review_corpus.html" if CORPUS else "grammar_review.html")
open(out, "w", encoding="utf-8").write(page)
print("wrote", out)
