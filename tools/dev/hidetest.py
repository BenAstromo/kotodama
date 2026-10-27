exec(open("loans.py", encoding="utf-8").read().split("lists = ")[0])
cards = [("有る", "ある"), ("見る", "みる"), ("私", "わたし"), ("月", "つき"), ("聞く", "きく")]
cov = freq_data.coverage({i + 1: c[0] for i, c in enumerate(cards)}, {i + 1: c[1] for i, c in enumerate(cards)}, None)
for key in ("missing", "missing_lean"):
    ws = {m[1] + m[2] for m in cov[key]}
    print(key, len(cov[key]), {w: (w in ws) for w in ("在るある", "診るみる", "聴くきく", "私わたくし", "月がつ", "するする")})
