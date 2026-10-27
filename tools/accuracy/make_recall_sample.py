"""Recall sample (2026-10-14): 100 random Tatoeba sentences nobody has
reviewed (not in grammar_cases.json, the precision sample or OpenJLPT's
examples), at most 40 characters so each can be annotated in full. For each
one the reviewer lists every JLPT point actually used; comparing with the
detections gives recall (how much real grammar the parser finds).

    python -I -X utf8 tools/accuracy/make_recall_sample.py <jpn_sentences.tsv>

Writes tools/accuracy/recall_sample.json and points.txt (id, level, pattern,
and whether the point is searched in sentences at all).
"""
import json, os, random, sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
exec(open(os.path.join(TOOLS, "gemini_grammar_review", "verdicts", "gem_head.py"), encoding="utf-8").read())
HERE = os.path.dirname(os.path.abspath(__file__))
sp = __import__("jlpt_progress.sentence_parser", fromlist=["x"])
SEED = int(sys.argv[2]) if len(sys.argv) > 2 else 20261015
OUT = sys.argv[3] if len(sys.argv) > 3 else "recall_sample"

seen = {c["text"] for c in json.load(open(os.path.join(TOOLS, "grammar_cases.json"), encoding="utf-8"))["cases"]}
for p in json.load(open(os.path.join(TOOLS, "grammar_examples.json"), encoding="utf-8"))["points"]:
    seen.update(p["ex"])
for f in os.listdir(HERE):
    if f.endswith(".json") and "sample" in f:
        data = json.load(open(os.path.join(HERE, f), encoding="utf-8"))
        if isinstance(data, list):
            seen.update(r["text"] for r in data)
texts = []
with open(sys.argv[1], encoding="utf-8") as f:
    for line in f:
        parts = line.rstrip("\n").split("\t")
        if len(parts) >= 3:
            t = sp.clean(parts[2])
            if t and len(t) <= 40 and t not in seen:
                texts.append(t)
rng = random.Random(SEED)
picked = rng.sample(sorted(set(texts)), 100)
points = gd.data()
out = []
for n, t in enumerate(picked, 1):
    ids = [g for g in gd.sentence_ids(t) if g in points]
    out.append({"n": n, "text": t, "detected": ids})
json.dump(out, open(os.path.join(HERE, OUT + ".json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

searched = {g for g, *_ in gd.detectors()}
token_ids = set()
import re as _re
src = open(os.path.join(os.path.dirname(TOOLS), "grammar_data.py"), encoding="utf-8").read()
token_ids = set(_re.findall(r'hit(?:_rx)?\("([a-z0-9-]+)"', src))
lines = []
for g, p in points.items():
    how = "searched" if g in searched or g in token_ids else "NOT SEARCHED"
    lines.append(f"{g}\t{p['level']}\t{p['pattern']}\t{how}")
open(os.path.join(HERE, "points.txt"), "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
print(len(out), "sentences;", sum(1 for l in lines if l.endswith("NOT SEARCHED")), "points not searched")
