"""Sample Tatoeba hits for given grammar points (2026-10-17), to read a new
rule's precision: count + up to N random hits per point, trigger in 【】.

    python -I -X utf8 tools/accuracy/point_samples.py <jpn_sentences.tsv> <N> id1 id2 ...
"""
import os, random, sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
exec(open(os.path.join(TOOLS, "gemini_grammar_review", "verdicts", "gem_head.py"), encoding="utf-8").read())
sp = __import__("jlpt_progress.sentence_parser", fromlist=["x"])
N = int(sys.argv[2])
want = set(sys.argv[3:])
rng = random.Random(20261017)
count = {g: 0 for g in want}
keep = {g: [] for g in want}
with open(sys.argv[1], encoding="utf-8") as f:
    for line in f:
        parts = line.rstrip("\n").split("\t")
        if len(parts) < 3:
            continue
        t = sp.clean(parts[2])
        if not t or len(t) > 70:
            continue
        spans = {}
        ids = set(gd.token_ids(t, spans)) & want
        for g in ids:
            count[g] += 1
            a, b = spans.get(g, [(0, 0)])[0]
            ex = t[:a] + "【" + t[a:b] + "】" + t[b:]
            if len(keep[g]) < N:
                keep[g].append(ex)
            elif rng.random() < N / count[g]:
                keep[g][rng.randrange(N)] = ex
        sp._TOK_CACHE.clear()
for g in sorted(want, key=lambda g: count[g]):
    print(f"== {g}: {count[g]} hits")
    for ex in keep[g]:
        print("   ", ex)
