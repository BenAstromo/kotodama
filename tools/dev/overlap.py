"""How the JLPT lists (Waller-based) and the frequency tiers (modern
estimates) overlap, cumulative per level."""
import os, sys, types
ADDON = r"C:\Users\benne\AppData\Roaming\Anki2\addons21\jlpt_progress"
class _Any:
    def __init__(s, *a, **k): pass
    def __getattr__(s, n): return _Any()
    def __call__(s, *a, **k): return _Any()
    def __bool__(s): return False
    def __iter__(s): return iter(())
aqt = types.ModuleType("aqt"); aqt.mw = _Any(); aqt.gui_hooks = _Any()
qt = types.ModuleType("aqt.qt")
sys.modules.update({"aqt": aqt, "aqt.qt": qt})
pkg = types.ModuleType("jlpt_progress"); pkg.__path__ = [ADDON]; sys.modules["jlpt_progress"] = pkg
from jlpt_progress import jlpt_data, freq_data
lists = jlpt_data.build_lists({})
LV = jlpt_data.LEVELS
TIERS = dict(zip(LV, [800, 1500, 3900, 6000, 13400]))
rows = freq_data.load()
print("freq rows:", len(rows))
rank_of = {}
cum = []
for i, lvl in enumerate(LV):
    cum += lists[lvl]
    ranks = []
    for d, r in lists[lvl]:
        rk = freq_data.word_rank(d, r, jlpt_data.alt_forms(d, r))
        rank_of[(d, r)] = rk
    n = TIERS[lvl]
    cr = [rank_of[w] for w in cum]
    in_top = {rk for rk in cr if rk and rk <= n}
    outside = sum(1 for rk in cr if not rk or rk > n)
    norank = sum(1 for rk in cr if not rk)
    print(f"up to {lvl}: list {len(cum):,} | top {n:,} | list words inside top-N {len(in_top):,} "
          f"| list words outside top-N {outside:,} (no rank {norank:,}) | top-N rows on no list up to {lvl} {n - len(in_top):,} "
          f"| union {len(cum) - 0 + (n - len(in_top)) - (len(cum) - outside - len(in_top)) if False else outside + n:,}")
# per-level: median rank of each level's own words
import statistics
for lvl in LV:
    rk = sorted(rank_of[w] for w in lists[lvl] if rank_of[w])
    print(lvl, "own words:", len(lists[lvl]), "ranked", len(rk), "median rank", statistics.median(rk),
          "p75", rk[int(len(rk) * .75)], "p90", rk[int(len(rk) * .9)])
import random
random.seed(7)
n5 = [(w, rank_of[w]) for w in lists["N5"] if rank_of[w] and rank_of[w] > 2000]
print("N5 list words ranked past 2,000:", len(n5), random.sample(n5, 12))
listed = {rank_of[w] for lvl in LV for w in lists[lvl] if rank_of[w]}
top = [(i + 1, r) for i, r in enumerate(rows[:800]) if i + 1 not in listed]
print("top-800 rows on no list at all:", len(top), [ (rk, r[0] if isinstance(r,(list,tuple)) else r) for rk, r in random.sample(top, 15)])
n4up = {rank_of[w] for lvl in LV[2:] for w in lists[lvl] if rank_of[w]}
t = [(rk) for rk in range(1, 801) if rk in n4up and rk not in {rank_of[w] for lvl in LV[:2] for w in lists[lvl] if rank_of[w]}]
print("top-800 rows whose word is listed only at N3-N1:", len(t))
print("sample row:", rows[0])
