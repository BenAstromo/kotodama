"""Word Addition Project: frequency words (top N) that no JLPT entry covers.
Same rules as tools/missing_words/missing_common.py + mc2.py, without a
collection copy. Writes wa_candidates.json next to this script."""
import json, os, sys, types
sys.stdout.reconfigure(encoding="utf-8")
ADDON = r"C:\Users\benne\AppData\Roaming\Anki2\addons21\jlpt_progress"
HERE = os.path.dirname(os.path.abspath(__file__))
LIMIT = int(sys.argv[1]) if len(sys.argv) > 1 else 6000


class _Any:
    def __init__(s, *a, **k): pass
    def __getattr__(s, n): return _Any()
    def __call__(s, *a, **k): return _Any()
    def __or__(s, o): return s
    def __iter__(s): return iter(())


aqt = types.ModuleType("aqt"); aqt.mw = _Any(); aqt.gui_hooks = _Any()
qt = types.ModuleType("aqt.qt")
qt.__getattr__ = lambda n: _Any
utils = types.ModuleType("aqt.utils"); utils.showWarning = print; utils.tooltip = print
anki = types.ModuleType("anki"); au = types.ModuleType("anki.utils"); au.ids2str = str
sys.modules.update({"aqt": aqt, "aqt.qt": qt, "aqt.utils": utils, "anki": anki, "anki.utils": au})
pkg = types.ModuleType("jlpt_progress"); pkg.__path__ = [ADDON]; sys.modules["jlpt_progress"] = pkg
import importlib
fd = importlib.import_module("jlpt_progress.freq_data")
jd = importlib.import_module("jlpt_progress.jlpt_data")
mn = importlib.import_module("jlpt_progress.meanings")

entries = fd.load()
lists = jd.build_lists({})
kata = lambda x: "".join(chr(ord(c) - 0x60) if "ァ" <= c <= "ヶ" else c for c in x)
covered, spell_read = set(), set()
for lvl in jd.LEVELS:
    for d, r in lists.get(lvl, []):
        rk = fd.word_rank(d, r, jd.alt_forms(d, r))
        if rk:
            covered.add(rk)
        for f in [d] + jd.alt_forms(d, r):
            for rr in [r] + jd.alt_readings(d, r):
                spell_read.add((f, kata(rr)))
rows = []
for i, (d, r, pmw, forms) in enumerate(entries, 1):
    if i > LIMIT:
        break
    if i in covered or (d, kata(r)) in spell_read:
        continue
    if (d, r) in fd.SHARED_WITH:
        continue
    if (d, r) in fd.COMPOUNDS and d[-2:] in ("える", "ける", "せる", "てる", "める", "れる", "げる", "べる", "ねる"):
        continue
    hit = mn.lookup(d, r)
    senses = [g for _p, g in (hit[1][:3] if hit and hit[1] else [])]
    pos = hit[1][0][0] if hit and hit[1] else ""
    rows.append({"rank": i, "d": d, "r": r, "pmw": round(pmw, 1), "pos": pos,
                 "m": "; ".join(senses)[:160], "compound": (d, r) in fd.COMPOUNDS,
                 "flag": fd.FLAGS.get((d, r), "") if hasattr(fd, "FLAGS") else ""})
json.dump(rows, open(os.path.join(HERE, "wa_candidates.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=0)
print(len(rows), "candidates in the top", LIMIT, "|", sum(1 for x in rows if x["rank"] <= 3900), "in the top 3,900")
