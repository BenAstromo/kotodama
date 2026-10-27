"""Which grammar points are never (or almost never) detected (2026-10-17,
owner: "check for grammar points that are not being detected").

For every point: whether it is searched in sentences at all, how many of its
own OpenJLPT examples detect it, and how many Tatoeba sentences detect it.
Points with 0 Tatoeba hits are listed first: either the pattern is too rare
for Tatoeba, or the detector misses its real forms.

    python -I -X utf8 tools/accuracy/point_coverage.py <jpn_sentences.tsv> [out.tsv]
"""
import collections, json, os, sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
exec(open(os.path.join(TOOLS, "gemini_grammar_review", "verdicts", "gem_head.py"), encoding="utf-8").read())
HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
sp = __import__("jlpt_progress.sentence_parser", fromlist=["x"])

points = gd.data()
searched = {}
for line in open(os.path.join(HERE, "points.txt"), encoding="utf-8"):
    g, lvl, pat, how = line.rstrip("\n").split("\t")
    searched[g] = (lvl, pat, how)

ex = {p["id"]: p["ex"] for p in json.load(open(os.path.join(TOOLS, "grammar_examples.json"), encoding="utf-8"))["points"]}
ex_hit = {}
for g, sents in ex.items():
    ex_hit[g] = sum(1 for s in sents if g in gd.sentence_ids(s))

hits = collections.Counter()
example = {}
n = 0
with open(sys.argv[1], encoding="utf-8") as f:
    for line in f:
        parts = line.rstrip("\n").split("\t")
        if len(parts) < 3:
            continue
        t = sp.clean(parts[2])
        if not t:
            continue
        n += 1
        if n % 50000 == 0:
            print(f"  {n:,}", flush=True)
        for g in set(gd.sentence_ids(t)):
            hits[g] += 1
            example.setdefault(g, t)
        sp._TOK_CACHE.clear()

rows = []
for g, (lvl, pat, how) in searched.items():
    rows.append((hits[g], lvl, g, pat, how, ex_hit.get(g, 0), len(ex.get(g, ())), example.get(g, "")))
rows.sort(key=lambda r: (r[0], r[1]))
out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "point_coverage.tsv")
with open(out, "w", encoding="utf-8") as f:
    f.write("tatoeba_hits\tlevel\tid\tpattern\tsearched\texamples_detected\texamples\tfirst_tatoeba_hit\n")
    for r in rows:
        f.write("\t".join(str(x) for x in r) + "\n")
print(f"{n:,} sentences; points with 0 hits: {sum(1 for r in rows if r[0] == 0)}, "
      f"never searched: {sum(1 for r in rows if r[4] == 'NOT SEARCHED')}; wrote {out}")
