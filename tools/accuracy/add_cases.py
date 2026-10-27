"""Add the reviewed accuracy sample to tools/grammar_cases.json: wrong
detections that are now fixed become "absent", correct ones "present".
Residual wrong ones (still detected) are left out.

    python -I -X utf8 tools/accuracy/add_cases.py
"""
import json, os, sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
exec(open(os.path.join(TOOLS, "gemini_grammar_review", "verdicts", "gem_head.py"), encoding="utf-8").read())
HERE = os.path.dirname(os.path.abspath(__file__))
sample = json.load(open(os.path.join(HERE, os.environ.get("SAMPLE", "sample") + ".json"), encoding="utf-8"))
v = json.load(open(os.path.join(HERE, ("verdicts" if os.environ.get("SAMPLE", "sample") == "sample" else os.environ["SAMPLE"] + "_verdicts") + ".json"), encoding="utf-8"))
cp = os.path.join(TOOLS, "grammar_cases.json")
d = json.load(open(cp, encoding="utf-8"))
by_text = {c["text"]: c for c in d["cases"]}
added = 0
for r in sample:
    ok = v[str(r["n"])]["ok"]
    found = r["gid"] in gd.sentence_ids(r["text"])
    if ok != found:
        continue                          # a residual (wrong but still found) or a regression
    c = by_text.get(r["text"])
    if c is None:
        c = {"text": r["text"], "absent": [], "present": []}
        d["cases"].append(c)
        by_text[r["text"]] = c
        added += 1
    key = "present" if ok else "absent"
    if r["gid"] not in c[key]:
        c[key] = sorted(c[key] + [r["gid"]])
json.dump(d, open(cp, "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=1)
open(cp, "a", encoding="utf-8").write("\n")
print("added", added, "sentences; total", len(d["cases"]))
