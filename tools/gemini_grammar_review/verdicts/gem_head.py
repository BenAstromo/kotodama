"""Grammar detection test (2026-10-14). Run after any change to grammar_data /
sentence_parser:

    python -I -X utf8 tools/grammar_eval.py            # report + differences
    python -I -X utf8 tools/grammar_eval.py --update   # accept the current results

1. OpenJLPT's example sentences (tools/grammar_examples.json, 1,526): how many
   detect their own point, per level. A rough recall figure: these are clean
   textbook sentences, and real ones are missed more often.
2. Owner's rulings (tools/grammar_cases.json): sentences the owner flagged
   ("absent": must not be detected) and real uses kept ("present"). Any
   failure is printed; there should be none.
3. Every sentence's detected ids compared with tools/grammar_eval_baseline.json:
   each gained / lost id is listed, so a fix can't silently change other
   points. Read them, then --update.

Needs no Anki and no collection.
"""
import json, os, sys, types

sys.stdout.reconfigure(encoding="utf-8")
HERE = r"C:/Users/benne/AppData/Roaming/Anki2/addons21/jlpt_progress/tools"
ADDON = r"C:/Users/benne/AppData/Roaming/Anki2/addons21/jlpt_progress"


class _Any:
    def __init__(s, *a, **k): pass
    def __getattr__(s, n): return _Any()
    def __call__(s, *a, **k): return _Any()
    def __or__(s, o): return s


aqt = types.ModuleType("aqt")
aqt.mw = _Any()
aqt.gui_hooks = types.SimpleNamespace(deck_browser_will_render_content=[], webview_did_receive_js_message=[],
                                      profile_did_open=[], state_did_change=[], state_will_change=[], reviewer_will_answer_card=[],
                                      reviewer_did_answer_card=[], webview_will_set_content=[])
qt = types.ModuleType("aqt.qt")
for n in ["QAction", "QMenu", "QObject", "QDialog", "QWidget", "QGroupBox", "QColor", "pyqtSignal", "QFont", "QLabel"]:
    setattr(qt, n, _Any)
utils = types.ModuleType("aqt.utils"); utils.showWarning = print; utils.tooltip = print
anki = types.ModuleType("anki"); anki_utils = types.ModuleType("anki.utils")
anki_utils.ids2str = lambda ids: "(" + ",".join(str(i) for i in ids) + ")"
sys.modules.update({"aqt": aqt, "aqt.qt": qt, "aqt.utils": utils, "anki": anki, "anki.utils": anki_utils})
sys.path.insert(0, os.path.dirname(ADDON))
gd = __import__(os.path.basename(ADDON) + ".grammar_data", fromlist=["x"])
