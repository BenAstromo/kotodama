"""Re-run the detector on the accuracy sample: lists correct detections that
are now lost (regressions) and wrong ones that are still there.

    python -I -X utf8 tools/accuracy/recheck.py
"""
import json, os, sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
exec(open(os.path.join(TOOLS, "gemini_grammar_review", "verdicts", "gem_head.py"), encoding="utf-8").read())
HERE = os.path.dirname(os.path.abspath(__file__))
sample = json.load(open(os.path.join(HERE, os.environ.get("SAMPLE", "sample") + ".json"), encoding="utf-8"))
v = json.load(open(os.path.join(HERE, ("verdicts" if os.environ.get("SAMPLE", "sample") == "sample" else os.environ["SAMPLE"] + "_verdicts") + ".json"), encoding="utf-8"))
lost, still = [], []
for r in sample:
    ok = v[str(r["n"])]["ok"]
    found = r["gid"] in gd.sentence_ids(r["text"])
    if ok and not found:
        lost.append(r)
    elif not ok and found:
        still.append(r)
wrong = sum(1 for x in v.values() if not x["ok"])
print(f"correct detections lost: {len(lost)}")
for r in lost:
    print(f"  LOST {r['n']} {r['gid']} | {r['text']}")
print(f"wrong detections still there: {len(still)} of {wrong}")
for r in still:
    print(f"  STILL {r['n']} {r['gid']} | {r['text']}")
