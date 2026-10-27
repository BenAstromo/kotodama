"""Frequency-list words no JLPT entry maps to, by tier."""
import sys, os, json, collections, pickle
S = os.path.dirname(os.path.abspath(__file__))
sys.argv = [sys.argv[0], S]
exec(open(os.path.join(S, "stubs.py"), encoding="utf-8").read())
fd = __import__(pkg + ".freq_data", fromlist=["x"])
jd = __import__(pkg + ".jlpt_data", fromlist=["x"])
mn = __import__(pkg + ".meanings", fromlist=["x"])
entries = fd.load()
lists = jd.build_lists({})
covered = {}
spell_read = set()
kata = lambda x: ''.join(chr(ord(c) - 0x60) if 'ァ' <= c <= 'ヶ' else c for c in x)
for lvl in jd.LEVELS:
    for d, r in lists.get(lvl, []):
        rk = fd.word_rank(d, r, jd.alt_forms(d, r))
        if rk:
            covered.setdefault(rk, lvl)
        for f in [d] + jd.alt_forms(d, r):
            for rr in [r] + jd.alt_readings(d, r):
                spell_read.add((f, kata(rr)))
tiers = [(800, "N5"), (1500, "N4"), (3900, "N3"), (6000, "N2"), (13400, "N1")]
def tier(rank):
    for lim, lvl in tiers:
        if rank <= lim:
            return lvl
    return "past N1"
cnt = collections.Counter(); tot = collections.Counter()
rows = []
for i, (d, r, pmw, forms) in enumerate(entries, 1):
    t = tier(i)
    tot[t] += 1
    if i not in covered and (d, kata(r)) not in spell_read:
        cnt[t] += 1
        hit = mn.lookup(d, r)
        pos = hit[1][0][0] if hit and hit[1] else ""
        gloss = hit[1][0][1] if hit and hit[1] else ""
        rows.append({"rank": i, "d": d, "r": r, "tier": t, "pos": pos, "gloss": gloss,
                     "flag": fd.FLAGS.get((d, r), ""), "shared": (d, r) in fd.SHARED_WITH,
                     "compound": (d, r) in fd.COMPOUNDS})
for lim, lvl in tiers:
    print(f"{lvl} range (≤{lim:,}): {cnt[lvl]:,} of {tot[lvl]:,} frequency words are on no JLPT list")
print("past N1:", cnt["past N1"])
json.dump(rows, open(os.path.join(S, "missing_common.json"), "w", encoding="utf-8"), ensure_ascii=False)
for x in rows[:120]:
    print(x["rank"], x["d"], x["r"], x["pos"][:25], "|", x["gloss"][:40], x["flag"], "S" if x["shared"] else "", "C" if x["compound"] else "")
