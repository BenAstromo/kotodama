"""Dev probe: print the parser's tokens and the detected grammar ids for
sentences (one per argument, or one per line of a file given as @path).

    python -I -X utf8 tools/accuracy/probe.py 彼はＤＪです。 頂きます。
"""
import os, sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
exec(open(os.path.join(TOOLS, "gemini_grammar_review", "verdicts", "gem_head.py"), encoding="utf-8").read())
sp = __import__("jlpt_progress.sentence_parser", fromlist=["x"])
args = []
for a in sys.argv[1:]:
    if a.startswith("@"):
        args += [l.strip() for l in open(a[1:], encoding="utf-8") if l.strip()]
    else:
        args.append(a)
points = gd.data()
for t in args:
    toks = sp.tokens(t)
    print(t)
    print("   ", " | ".join(f"{x[0]}:{x[1]}" + (f"[{x[2]}]" if x[2] and x[2] != x[0] else "")
                          + (f"<{x[5]}>" if len(x) > 5 and x[5] else "") for x in toks))
    print("   →", " ".join(g for g in gd.sentence_ids(t) if g in points))
