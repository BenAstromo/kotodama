exec(open("loans.py", encoding="utf-8").read().split("lists = ")[0])
lists = jlpt_data.build_lists({})
LV = jlpt_data.LEVELS
lvl_of = {}
for lvl in LV:
    for d, r in lists[lvl]:
        rk = freq_data.word_rank(d, r, jlpt_data.alt_forms(d, r))
        if rk and rk not in lvl_of:
            lvl_of[rk] = lvl
rows = freq_data.load()
import random; random.seed(3)
for top, upto in ((3900, "N3"),):
    below = LV[:LV.index(upto) + 1]
    fill = [(i + 1, rows[i][0], lvl_of.get(i + 1, "none")) for i in range(top) if lvl_of.get(i + 1) not in below]
    from collections import Counter
    c = Counter(l for _, _, l in fill)
    print(f"top {top} after the lists up to {upto}: {len(fill)} words to fill; by JLPT level: {dict(c)}")
    for l in ("N3", "N2", "N1", "none"):
        xs = [w for _, w, ll in fill if ll == l]
        print("  ", l, random.sample(xs, min(14, len(xs))))
