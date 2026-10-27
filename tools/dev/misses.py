import json, os, sys
sys.stdout.reconfigure(encoding="utf-8")
TOOLS = sys.argv[1]
exec(open(os.path.join(TOOLS, "gemini_grammar_review", "verdicts", "gem_head.py"), encoding="utf-8").read())
pts = gd.data()
ex = json.load(open(os.path.join(TOOLS, "grammar_examples.json"), encoding="utf-8"))["points"]
order = {"N5": 0, "N4": 1, "N3": 2, "N2": 3, "N1": 4}
rows = []
for p in ex:
    g = p["id"]
    if g not in pts: continue
    for t in p["ex"]:
        ids = gd.sentence_ids(t)
        if g not in ids:
            rows.append((order[pts[g]["level"]], pts[g]["level"], g, pts[g]["pattern"], t, " ".join(sorted(i for i in ids if i in pts))))
rows.sort()
for r in rows: print("\t".join(r[1:]))
print(len(rows), file=sys.stderr)
