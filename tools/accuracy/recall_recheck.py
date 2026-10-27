"""Re-detect an annotated recall sample with the current code (2026-10-14):
recall and wrong detections now vs. when it was annotated. The sample has
been looked at while fixing, so this is NOT a fresh measurement; use a new
seed for that. --add-cases writes the results into tools/grammar_cases.json
(gold points now found → "present", wrong ones now gone → "absent").

    SAMPLE=recall_sample3 python -I -X utf8 tools/accuracy/recall_recheck.py [--add-cases]
"""
import json, os, sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
exec(open(os.path.join(TOOLS, "gemini_grammar_review", "verdicts", "gem_head.py"), encoding="utf-8").read())
HERE = os.path.dirname(os.path.abspath(__file__))
NAME = os.environ.get("SAMPLE", "recall_sample")
sample = {str(r["n"]): r for r in json.load(open(os.path.join(HERE, NAME + ".json"), encoding="utf-8"))}
v = json.load(open(os.path.join(HERE, NAME.replace("sample", "verdicts") + ".json"), encoding="utf-8"))
points = gd.data()
tp0 = tp1 = n = fp0 = fp1 = 0
missed = {}
cases = []
for k, a in v.items():
    t = sample[k]["text"]
    before = set(sample[k]["detected"])
    now = {g for g in gd.sentence_ids(t) if g in points}
    gold, fp = set(a["gold"]), set(a.get("fp", []))
    n += len(gold)
    tp0 += len(gold & before)
    tp1 += len(gold & now)
    fp0 += len(fp & before)
    fp1 += len(fp & now)
    for g in gold - now:
        missed[g] = missed.get(g, 0) + 1
    for g in now - gold - fp:
        print(f"  new, not annotated: {k} {g} | {t}")
    cases.append((t, sorted(gold & now), sorted(fp - now)))
print(f"recall then {tp0}/{n} = {tp0 / n:.0%}, now {tp1}/{n} = {tp1 / n:.0%}")
print(f"annotated wrong detections then {fp0}, now {fp1}")
print("still missed:", ", ".join(f"{g} {c}" for g, c in sorted(missed.items(), key=lambda x: -x[1])[:20]))
if "--add-cases" in sys.argv:
    cp = os.path.join(TOOLS, "grammar_cases.json")
    d = json.load(open(cp, encoding="utf-8"))
    by_text = {c["text"]: c for c in d["cases"]}
    added = 0
    for t, present, absent in cases:
        if not present and not absent:
            continue
        c = by_text.get(t)
        if c is None:
            c = {"text": t, "absent": [], "present": []}
            d["cases"].append(c)
            by_text[t] = c
            added += 1
        for g in present:
            if g not in c["present"]:
                c["present"].append(g)
        for g in absent:
            if g not in c["absent"]:
                c["absent"].append(g)
    json.dump(d, open(cp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(added, "cases added;", len(d["cases"]), "total")
