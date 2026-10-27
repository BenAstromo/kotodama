import random
import stubenv as E
rd = E.load("rank_data"); cs = E.load("card_state")
T = rd.BELT_THRESHOLDS
E.check("belt thresholds strictly increasing, start at 0", T[0] == 0 and all(a < b for a, b in zip(T, T[1:])))
E.check("degree thresholds strictly increasing", all(a < b for a, b in zip(rd.DEGREE_THRESHOLDS, rd.DEGREE_THRESHOLDS[1:])))
prev, bad, keys = None, [], None
for c in range(0, 25001):
    i = rd.get_rank_info(c)
    keys = keys or set(i)
    k = (i["rank_index"], i["belt_index"], i["degree_index"] or 0)
    if prev is not None and k < prev: bad.append(("goes down", c, prev, k))
    if i["is_max_amaterasu"] != (c >= rd.MAX_CARDS): bad.append(("is_max_amaterasu", c))
    if set(i) != keys: bad.append(("keys differ", c))
    if not i["is_max"] and not (i.get("belt_end", c + 1) > c): bad.append(("belt_end not ahead", c, i.get("belt_end")))
    if not 0 <= i["rank_index"] < len(rd.MAIN_RANKS_EN): bad.append(("rank_index range", c))
    prev = k
E.check("rank/belt/degree never go down as the count rises (0–25,000)", not [b for b in bad if b[0] == "goes down"], bad[:3])
E.check("is_max_amaterasu exactly from 20,000", not [b for b in bad if b[0] == "is_max_amaterasu"], bad[:3])
E.check("same keys at every count; ranges ok; belt_end ahead", not [b for b in bad if b[0] in ("keys differ", "rank_index range", "belt_end not ahead")], bad[:3])
for t in T[1:]:
    a, b = rd.get_rank_info(t - 1), rd.get_rank_info(t)
    if (a["rank_index"], a["belt_index"], a["degree_index"]) == (b["rank_index"], b["belt_index"], b["degree_index"]) and not a["is_max"]:
        bad.append(("threshold doesn't change belt", t))
E.check("every threshold starts a new belt (20,000: the Tenth Degree)", not [b for b in bad if b[0] == "threshold doesn't change belt"], [b for b in bad if b[0].startswith("thr")][:3])
E.check("negative count handled", rd.get_rank_info(-5)["rank_index"] == 0)
# loanword schedule
rng = random.Random(7); errs = []
for trial in range(3000):
    loans = sorted(rng.sample(range(1, 20000), rng.randint(0, 300)))
    hand = rng.randint(0, 50); extra = {"hand": hand, "loans": loans}
    last = -1
    for cards in sorted(rng.sample(range(0, 22000), 40)):
        n = cs.loans_counted(cards, loans)
        if not 0 <= n <= len(loans): errs.append(("range", cards, n))
        if n < last: errs.append(("not monotone", cards))
        last = n
        total, n2, h = cs.rank_split(cards, extra)
        if total != cards + n + hand or n2 != n or h != hand: errs.append(("split sum", cards))
        c2, n3 = cs.cards_for_rank(total, extra)
        if (c2, n3) != (cards, n): errs.append(("round trip", cards, total, (c2, n3), (cards, n)))
        nyc = cs.loans_not_yet_counted(total, extra)
        if not 0 <= nyc <= len(loans): errs.append(("not-yet range", nyc))
E.check("loans_counted in range and never decreasing", not [e for e in errs if e[0] in ("range", "not monotone")], errs[:3])
E.check("rank = cards + loans counted + hand marks", not [e for e in errs if e[0] == "split sum"], errs[:3])
E.check("cards_for_rank undoes rank_split", not [e for e in errs if e[0] == "round trip"], [e for e in errs if e[0] == "round trip"][:3])
E.check("loans_not_yet_counted in range", not [e for e in errs if e[0] == "not-yet range"])
# with every loan counted, the last one joins at ~rank − index
L = sorted(range(100, 20000, 8)); n_all = cs.loans_counted(20000, L)
print(f"  {len(L)} loans: counted at 20,000 cards: {n_all}")
E.finish()
