"""Dump grammar ids for every Tatoeba sentence with the add-on at argv[1]."""
import json, os, sys, types
sys.stdout.reconfigure(encoding="utf-8")
ADDON, CORPUS, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
class _Any:
    def __init__(s, *a, **k): pass
    def __getattr__(s, n): return _Any()
    def __call__(s, *a, **k): return _Any()
    def __or__(s, o): return s
aqt = types.ModuleType("aqt"); aqt.mw = _Any()
aqt.gui_hooks = types.SimpleNamespace(deck_browser_will_render_content=[], webview_did_receive_js_message=[],
    profile_did_open=[], state_did_change=[], state_will_change=[], reviewer_will_answer_card=[], reviewer_did_answer_card=[], webview_will_set_content=[])
qt = types.ModuleType("aqt.qt")
for n in ["QAction", "QMenu", "QObject", "QDialog", "QWidget", "QGroupBox", "QColor", "pyqtSignal", "QFont", "QStyledItemDelegate", "QLabel"]:
    setattr(qt, n, _Any)
utils = types.ModuleType("aqt.utils"); utils.showWarning = print; utils.tooltip = print
anki = types.ModuleType("anki"); au = types.ModuleType("anki.utils"); au.ids2str = lambda ids: ""
sys.modules.update({"aqt": aqt, "aqt.qt": qt, "aqt.utils": utils, "anki": anki, "anki.utils": au})
sys.path.insert(0, os.path.dirname(ADDON))
gd = __import__(os.path.basename(ADDON) + ".grammar_data", fromlist=["x"])
sp = __import__(os.path.basename(ADDON) + ".sentence_parser", fromlist=["x"])
print(gd.__file__)
pts = gd.data()
out = {}
with open(CORPUS, encoding="utf-8") as f:
    for k, line in enumerate(f):
        parts = line.rstrip("\n").split("\t")
        if len(parts) >= 3 and parts[2].strip():
            t = sp.clean(parts[2])
            spans = {}
            ids = gd.sentence_ids(t, spans)
            out[parts[0]] = [t, {g: spans.get(g, []) for g in ids if g in pts}]
        if k % 50000 == 0:
            print(k, flush=True)
json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
