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
HERE = os.path.dirname(os.path.abspath(__file__))
ADDON = os.path.dirname(HERE)


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
for n in ["QAction", "QMenu", "QObject", "QDialog", "QWidget", "QGroupBox", "QColor", "pyqtSignal", "QFont", "QStyledItemDelegate", "QLabel"]:
    setattr(qt, n, _Any)
utils = types.ModuleType("aqt.utils"); utils.showWarning = print; utils.tooltip = print
anki = types.ModuleType("anki"); anki_utils = types.ModuleType("anki.utils")
anki_utils.ids2str = lambda ids: "(" + ",".join(str(i) for i in ids) + ")"
sys.modules.update({"aqt": aqt, "aqt.qt": qt, "aqt.utils": utils, "anki": anki, "anki.utils": anki_utils})
sys.path.insert(0, os.path.dirname(ADDON))
gd = __import__(os.path.basename(ADDON) + ".grammar_data", fromlist=["x"])

pts = gd.data()
examples = json.load(open(os.path.join(HERE, "grammar_examples.json"), encoding="utf-8"))["points"]
cases = json.load(open(os.path.join(HERE, "grammar_cases.json"), encoding="utf-8"))["cases"]
BASE = os.path.join(HERE, "grammar_eval_baseline.json")

results = {}
def ids(text):
    if text not in results:
        results[text] = sorted(gd.sentence_ids(text))
    return results[text]

# 1. recall on OpenJLPT's examples
print("level  points  detect-any-own-example  own examples detected")
by_lvl = {}
for p in examples:
    g = p["id"]
    if g not in pts:
        continue
    row = by_lvl.setdefault(pts[g]["level"], [0, 0, 0, 0])
    hits = [g in ids(s) for s in p["ex"]]
    row[0] += 1
    row[1] += any(hits)
    row[2] += len(hits)
    row[3] += sum(hits)
for lvl in ("N5", "N4", "N3", "N2", "N1"):
    a, b, c, d = by_lvl.get(lvl, [0, 0, 0, 0])
    print(f"{lvl}     {a:4}    {b:4} ({b / max(a, 1):4.0%})              {d:4}/{c:<4} ({d / max(c, 1):.0%})")

# 2. owner's rulings
fails = []
for c in cases:
    got = set(ids(c["text"]))
    fails += [f"  should NOT detect {g}: {c['text']}" for g in c["absent"] if g in got]
    fails += [f"  should detect {g}: {c['text']}" for g in c["present"] if g not in got]
print(f"\nowner's rulings: {len(cases)} sentences, {len(fails)} failure(s)")
print("\n".join(fails))

# 3. differences from the baseline
try:
    base = json.load(open(BASE, encoding="utf-8"))
except OSError:
    base = None
if "--update" in sys.argv or base is None:
    json.dump(results, open(BASE, "w", encoding="utf-8"), ensure_ascii=False, indent=0, sort_keys=True)
    print("\nbaseline", "updated" if base is not None else "created", f"({len(results)} sentences)")
else:
    changed = 0
    for t, now in sorted(results.items()):
        old = base.get(t)
        if old is not None and old != now:
            changed += 1
            print(f"  {t}  | lost {sorted(set(old) - set(now))} | gained {sorted(set(now) - set(old))}")
    print(f"\n{changed} sentence(s) differ from the baseline" + (" (check them, then --update)" if changed else ""))
sys.exit(1 if fails else 0)
