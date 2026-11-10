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

Open the page in the Browser pane with a file:/// URL (pages outside the
project folder render as static snapshots). Delete it once reviewed.
"""
import html, json, os, sqlite3, sys, types

sys.stdout.reconfigure(encoding="utf-8")
S = sys.argv[1]
ADDON = r"C:/Users/benne/AppData/Roaming/Anki2/addons21/jlpt_progress"
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
    db = _DB()

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

