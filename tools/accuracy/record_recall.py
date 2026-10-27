"""Record recall annotations: for each sentence, every JLPT point really used
("gold") and detections that are wrong ("fp"). Others detected = neutral.

    python -I -X utf8 tools/accuracy/record_recall.py '{"1": {"gold": [...], "fp": [...]}, ...}'
    python -I -X utf8 tools/accuracy/record_recall.py --report
"""
import json, math, os, sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
NAME = os.environ.get("SAMPLE", "recall_sample")
VP = os.path.join(HERE, NAME.replace("sample", "verdicts") + ".json")
sample = {str(r["n"]): r for r in json.load(open(os.path.join(HERE, NAME + ".json"), encoding="utf-8"))}
v = json.load(open(VP, encoding="utf-8")) if os.path.exists(VP) else {}
if sys.argv[1] != "--report":
    v.update(json.loads(sys.argv[1]))
    json.dump(v, open(VP, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

ns = set()
for line in open(os.path.join(HERE, "points.txt"), encoding="utf-8"):
    g, lvl, pat, how = line.rstrip("\n").split("\t")
    if how == "NOT SEARCHED":
        ns.add(g)


def ci(k, n):
    if not n:
        return 0, 0, 0
    p, z = k / n, 1.96
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, c - h, c + h


tp = fn = fn_ns = fp = det = 0
missed = {}
for n, a in v.items():
    detected = set(sample[n]["detected"])
    gold = set(a["gold"])
    tp += len(gold & detected)
    for g in gold - detected:
        fn += 1
        fn_ns += g in ns
        missed[g] = missed.get(g, 0) + 1
    fp += len(a.get("fp", []))
    det += len(detected)
p, lo, hi = ci(tp, tp + fn)
print(f"sentences annotated: {len(v)}")
print(f"grammar uses: {tp + fn}; found {tp} = recall {p:.0%} (95%: {lo:.0%}–{hi:.0%})")
p2, lo2, hi2 = ci(tp, tp + fn - fn_ns)
print(f"  of points the parser searches for: {tp}/{tp + fn - fn_ns} = {p2:.0%} ({lo2:.0%}–{hi2:.0%})")
print(f"  misses on never-searched points: {fn_ns}")
print(f"wrong detections in these sentences: {fp} of {det}")
print("most missed:", ", ".join(f"{g} {c}" for g, c in sorted(missed.items(), key=lambda x: -x[1])[:15]))
