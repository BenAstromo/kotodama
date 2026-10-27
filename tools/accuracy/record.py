"""Record accuracy verdicts: every item in a range is correct except the listed
wrong ones (with a note each). Results go to tools/accuracy/verdicts.json.

    python -I -X utf8 tools/accuracy/record.py <first> <last> '{"50": "note", ...}'
    python -I -X utf8 tools/accuracy/record.py --report
"""
import json, math, os, sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
NAME = os.environ.get("SAMPLE", "sample")
VP = os.path.join(HERE, ("verdicts" if NAME == "sample" else NAME + "_verdicts") + ".json")
sample = json.load(open(os.path.join(HERE, os.environ.get("SAMPLE", "sample") + ".json"), encoding="utf-8"))
v = json.load(open(VP, encoding="utf-8")) if os.path.exists(VP) else {}

if sys.argv[1] != "--report":
    first, last = int(sys.argv[2 - 1]), int(sys.argv[2])
    wrong = json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}
    for n in range(first, last + 1):
        v[str(n)] = {"ok": str(n) not in wrong, "note": wrong.get(str(n), "")}
    json.dump(v, open(VP, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def ci(k, n):
    """Wilson 95% interval for k of n."""
    if not n:
        return 0, 0, 0
    p, z = k / n, 1.96
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, c - h, c + h


groups = {}
for r in sample:
    if str(r["n"]) in v:
        key = "A (all, as used)" if r["set"] == "A" else f"B {r['level']}"
        g = groups.setdefault(key, [0, 0])
        g[1] += 1
        g[0] += v[str(r["n"])]["ok"]
print(f"reviewed {len(v)} of {len(sample)}")
for key in sorted(groups):
    k, n = groups[key]
    p, lo, hi = ci(k, n)
    print(f"  {key:18} {k}/{n} correct = {p:.0%}  (95%: {lo:.0%}–{hi:.0%})")
