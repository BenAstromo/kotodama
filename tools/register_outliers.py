"""For each BCCWJ register: its share of the corpus, and how many top-ranked
words owe most of their count to that register alone (outlier influence)."""
import csv, collections, re
csv.field_size_limit(10**9)
k2h = lambda s: "".join(chr(ord(c) - 0x60) if "\u30A1" <= c <= "\u30F6" else c for c in s)
KEEP = ("名詞-普通名詞", "動詞", "形容詞", "形状詞-一般", "形状詞-タリ", "副詞", "連体詞", "接続詞", "感動詞-一般", "代名詞")
JP = re.compile(r"[\u3040-\u30FF\u4E00-\u9FFF\u3400-\u4DBF\u3005\u3006]+")
REG = {"PB": "books", "PM": "magazines", "PN": "newspapers", "LB": "library books",
       "OW": "white papers", "OT": "textbooks", "OP": "PR newsletters", "OB": "bestsellers",
       "OC": "Q&A sites (Chiebukuro)", "OY": "blogs", "OV": "verse/poetry", "OL": "laws", "OM": "Diet minutes"}

tot = collections.Counter()
per = collections.defaultdict(collections.Counter)
corpus = collections.Counter()
with open(r"C:/Users/benne/AppData/Local/Temp/data/BCCWJ_frequencylist_suw_ver1_0.tsv", encoding="utf-8") as f:
    for row in csv.DictReader(f, delimiter="\t"):
        for r in REG:
            corpus[r] += int(row[r + "_frequency"] or 0)
        if not row["pos"].startswith(KEEP) or not JP.fullmatch(row["lemma"] or ""):
            continue
        key = (row["lemma"], k2h(row["lForm"]))
        tot[key] += int(row["frequency"])
        for r in REG:
            per[key][r] += int(row[r + "_frequency"] or 0)

all_tokens = sum(corpus.values())
ranked = [k for k, _ in tot.most_common(13402)]
print(f"{'register':26} {'corpus share':>12} {'top-13,402 words >50% from it':>30}   examples (rank)")
for r, name in sorted(REG.items(), key=lambda kv: -corpus[kv[0]]):
    dom = [(i + 1, k[0]) for i, k in enumerate(ranked) if per[k][r] > 0.5 * tot[k]]
    share = corpus[r] / all_tokens * 100
    ex = " ".join(f"{w}({i})" for i, w in dom[:14])
    print(f"{name:26} {share:11.1f}% {len(dom):30}   {ex}")
