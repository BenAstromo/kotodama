"""Fresh accuracy sample for grammar detection (2026-10-14).

Runs the current detection over Tatoeba and draws detections nobody has
reviewed, to measure precision honestly (the review sample, the test cases
in grammar_cases.json and OpenJLPT's examples are all left out):

  A  400 detections drawn uniformly from all hits, so each point appears as
     often as it fires in real text (overall precision)
  B  50 each from N3, N2 and N1 points (precision where the review found most
     errors)

    python -I -X utf8 tools/accuracy/make_sample.py <jpn_sentences.tsv> [seed] [out name] [size of A]

Writes tools/accuracy/sample.json (+ sample.txt to read). Fixed seed, so the
same code gives the same sample.
"""
import hashlib, json, os, random, re, sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
exec(open(os.path.join(TOOLS, "gemini_grammar_review", "verdicts", "gem_head.py"), encoding="utf-8").read())
sp = __import__("jlpt_progress.sentence_parser", fromlist=["x"])
HERE = os.path.dirname(os.path.abspath(__file__))   # gem_head.py sets its own HERE

SKIP_FIRST = 16      # the review showed the first 8 hits per point (md5 order); skip 16 to be safe
SEED = int(sys.argv[2]) if len(sys.argv) > 2 else 20261014
OUT = sys.argv[3] if len(sys.argv) > 3 else "sample"
SIZE_A = int(sys.argv[4]) if len(sys.argv) > 4 else 400

texts = {}
with open(sys.argv[1], encoding="utf-8") as f:
    for line in f:
        parts = line.rstrip("\n").split("\t")
        if len(parts) >= 3 and parts[2].strip():
            texts[int(parts[0])] = sp.clean(parts[2])
seen = {c["text"] for c in json.load(open(os.path.join(TOOLS, "grammar_cases.json"), encoding="utf-8"))["cases"]}
for p in json.load(open(os.path.join(TOOLS, "grammar_examples.json"), encoding="utf-8"))["points"]:
    seen.update(p["ex"])
for f in os.listdir(os.path.join(TOOLS, "accuracy")):   # every earlier sample
    if f.endswith(".json") and "sample" in f:
        data = json.load(open(os.path.join(TOOLS, "accuracy", f), encoding="utf-8"))
        if isinstance(data, list):
            seen.update(r["text"] for r in data)

points = gd.data()
per_gid = {}
hits = []            # (sid, gid, spans)
order = sorted(texts, key=lambda n: hashlib.md5(str(n).encode()).hexdigest())
for i, sid in enumerate(order):
    if i % 25000 == 0:
        print(f"  {i:,} / {len(order):,}", flush=True)
    t = texts[sid]
    spans = {}
    gd.sentence_ids(t, spans)
    for gid, s in spans.items():
        if gid not in points:
            continue
        k = per_gid.get(gid, 0)
        per_gid[gid] = k + 1
        if k < SKIP_FIRST or t in seen:
            continue
        hits.append((sid, gid, sorted(set(map(tuple, s)))))
print(f"{len(hits):,} eligible detections over {len(per_gid)} points")

rng = random.Random(SEED)
a = rng.sample(hits, SIZE_A)
taken = {(h[0], h[1]) for h in a}
b = []
for lvl in ("N3", "N2", "N1"):      # 50 per level: N3 points fire far more often than N2 / N1
    pool = [h for h in hits if points[h[1]]["level"] == lvl and (h[0], h[1]) not in taken]
    b += rng.sample(pool, min(50, len(pool)))

out, lines = [], []
for set_name, rows in (("A", a), ("B", b)):
    for sid, gid, s in rows:
        t = texts[sid]
        p = points[gid]
        marked, pos = "", 0
        for x, y in s:
            if x >= pos:
                marked += t[pos:x] + "【" + t[x:y] + "】"
                pos = y
        marked += t[pos:]
        split = " ".join(tok[0] for tok in sp.tokens(t) if tok[1] != "punct" or tok[0].strip())
        n = len(out) + 1
        out.append({"n": n, "set": set_name, "sid": sid, "gid": gid, "level": p["level"],
                    "pattern": p["pattern"], "meaning": p.get("meaning", ""), "text": t,
                    "spans": s, "marked": marked, "split": split})
        lines.append(f"{n}. [{set_name}] [{p['level']}] {gid} — {p['pattern']} — {p.get('meaning', '')}\n"
                     f"   {marked}\n   split: {split}")
json.dump(out, open(os.path.join(HERE, OUT + ".json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
open(os.path.join(HERE, OUT + ".txt"), "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
lv = {}
for r in out:
    lv.setdefault((r["set"], r["level"]), 0)
    lv[(r["set"], r["level"])] += 1
print("sample:", len(out), sorted(lv.items()))
