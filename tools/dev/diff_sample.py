"""Gained / lost detections between two dumps; per point counts and up to N random examples."""
import json, random, sys, collections
sys.stdout.reconfigure(encoding="utf-8")
old = json.load(open(sys.argv[1], encoding="utf-8")); new = json.load(open(sys.argv[2], encoding="utf-8"))
N = int(sys.argv[3]); rng = random.Random(20261052)
gain, lost = collections.defaultdict(list), collections.defaultdict(list)
for sid, (t, ids) in new.items():
    o = old.get(sid, [t, {}])[1]
    for g in ids:
        if g not in o: gain[g].append((t, ids[g]))
    for g in o:
        if g not in ids: lost[g].append((t, o[g]))
def mark(t, spans):
    out, pos = "", 0
    for x, y in sorted(set(map(tuple, spans))):
        if x >= pos:
            out += t[pos:x] + "【" + t[x:y] + "】"; pos = y
    return out + t[pos:]
for name, d in (("GAINED", gain), ("LOST", lost)):
    print(f"===== {name}: {sum(len(v) for v in d.values())} over {len(d)} points")
    for g, v in sorted(d.items(), key=lambda x: -len(x[1])):
        print(f"--- {g}: {len(v)}")
        for t, s in rng.sample(v, min(N, len(v))):
            if len(t) <= 90: print("   ", mark(t, s))
