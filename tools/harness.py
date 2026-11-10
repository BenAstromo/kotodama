"""Run the add-on's real analysis against a read-only copy of the collection."""
import sys, types, sqlite3, json, time
S = sys.argv[1]
db = sqlite3.connect(S + "/col_copy.anki2")
ntypes = {i: n for i, n in db.execute("select id,name from notetypes")}
fields = {}
for ntid, ord_, name in db.execute("select ntid,ord,name from fields order by ntid,ord"):
    fields.setdefault(ntid, []).append(name)

class Note(dict):
    def __init__(self, mid, flds):
        super().__init__(zip(fields[mid], flds.split("\x1f")))
        self._nt = {"name": ntypes[mid]}
    def note_type(self): return self._nt

class Col:
    # Understands the searches the add-on builds (card_state.deck_search):
    # '"deck:NAME"', optionally followed by ' -is:suspended' and ' is:review'.
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
        def all(self, sql, *a): return db.execute(sql, a).fetchall()
        def first(self, sql, *a): return db.execute(sql, a).fetchone()
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
                                      profile_did_open=[], state_did_change=[], state_will_change=[],
                                      reviewer_will_answer_card=[], reviewer_did_answer_card=[],
                                      webview_will_set_content=[])
qt = types.ModuleType("aqt.qt")
names = ["QAction","QMenu","QObject","QDialog","QWidget","QGroupBox","QColor","pyqtSignal","QFont","QStyledItemDelegate","QLabel"]
for n in names: setattr(qt, n, _Any)
qt.__all__ = names
utils = types.ModuleType("aqt.utils"); utils.showWarning = print; utils.tooltip = print
anki = types.ModuleType("anki"); anki_utils = types.ModuleType("anki.utils")
anki_utils.ids2str = lambda ids: "(" + ",".join(str(i) for i in ids) + ")"
sys.modules.update({"aqt": aqt, "aqt.qt": qt, "aqt.utils": utils, "anki": anki, "anki.utils": anki_utils})
sys.path.insert(0, r"C:/Users/benne/AppData/Roaming/Anki2/addons21")
import jlpt_progress as jp
from jlpt_progress import jlpt_data, freq_data
from jlpt_progress.overrides import Overrides

cfg = json.load(open(r"C:/Users/benne/AppData/Roaming/Anki2/addons21/jlpt_progress/meta.json", encoding="utf-8"))["config"]
t = time.time()
lists = jlpt_data.build_lists(cfg["lists"])
ur = jp._build_unique_readings(lists)
IGNORE_SUSP = "--ignore-suspended" in sys.argv
di, ri, nd, nr = jp.collect_words(cfg["deck_name"], cfg["field_mappings"], IGNORE_SUSP)
res = jp.analyse(di, ri, nd, nr, lists, ur, overrides=Overrides())
print(f"analysis took {time.time()-t:.2f}s; notes scanned {len(nd)}; deck notes {len(Col().find_notes(chr(34)+'deck:'+cfg['deck_name']+chr(34)))}")
for l in jlpt_data.LEVELS:
    k = len(res[l]["known_words"]); m = len(res[l]["missing_words"])
    print(f"{l}: {k}/{k+m}")
print("unlisted:", len(res["unlisted"]["known_words"]))
f = res["frequency"]
print("freq tiers:", f["tiers"]); print("notes_in_top:", f["notes_in_top"]); print("text coverage: %.1f%%" % (f["text_coverage"]*100))
print("top missing:", f["missing"][:25])
alt_hits = [(d, r) for l in jlpt_data.LEVELS for d, r, nid in res[l]["known_words"] if nid and jlpt_data.alt_forms(d, r) and jp._norm(d) not in di]
print("matched via alt spelling e.g.:", alt_hits[:15], len(alt_hits))
loans = [(d, r) for l in jlpt_data.LEVELS for d, r in res[l]["missing_words"] if jlpt_data.is_english_loanword(d, r)]
print("missing loanwords:", len(loans))

from jlpt_progress import card_state, rank_data
mat = card_state.note_maturity(cfg["deck_name"], IGNORE_SUSP)
from collections import Counter
print("ignore suspended:", IGNORE_SUSP)
print("note maturity:", {card_state.STATE_NAMES[k]: v for k, v in sorted(Counter(mat.values()).items())})
rc = card_state.rank_count(cfg["deck_name"], IGNORE_SUSP)
ri_ = rank_data.get_rank_info(rc)
print(f"rank count (studied notes + found): {rc:,} -> {ri_['rank_name']} / {ri_['belt_display_name']} Belt")
