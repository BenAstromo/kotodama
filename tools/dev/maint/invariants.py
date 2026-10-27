"""Counting invariants on the owner's real deck (collection copy)."""
import sys, os, io, contextlib
S = sys.argv[1]
sys.argv = [sys.argv[0], S, "--ignore-suspended"]
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    exec(open(os.path.join(S, "harness.py"), encoding="utf-8").read())
sys.stdout.reconfigure(encoding="utf-8")
R = []
def check(n, c, extra=""):
    R.append(c); print(("PASS " if c else "FAIL ") + n + (f"  {extra}" if extra and not c else ""))
L = jlpt_data.LEVELS
ov = Overrides()
# 1. a note counts at most once across levels + Off-list
seen, dup = {}, []
for l in L:
    for d, r, nid in res[l]["known_words"]:
        if nid is not None:
            if nid in seen: dup.append((nid, seen[nid], l, d))
            seen[nid] = l
for d, r, nid in res["unlisted"]["known_words"]:
    if nid in seen: dup.append((nid, seen[nid], "unlisted", d))
    seen[nid] = "unlisted"
check("each note counted at most once (levels + Off-list)", not dup, dup[:5])
# 2. every scanned note is somewhere
lost = [n for n in nd if n not in seen]
check("every scanned note is counted somewhere", not lost, [(n, nd[n]) for n in lost[:8]])
# 3. per level: known and missing don't overlap, no word twice
for l in L:
    k = [(d, r) for d, r, _ in res[l]["known_words"]]; m = [tuple(x) for x in res[l]["missing_words"]]
    check(f"{l}: known ∩ missing empty, no duplicates", not (set(k) & set(m)) and len(set(k)) == len(k) and len(set(m)) == len(m),
          (set(k) & set(m), len(k) - len(set(k)), len(m) - len(set(m))))
# 4. every list word is known, missing or suspended (nothing silently dropped)
for l in L:
    shown = {(d, r) for d, r, _ in res[l]["known_words"]} | {tuple(x) for x in res[l]["missing_words"]}
    gone = [(d, r) for d, r in lists[l] if (d, r) not in shown and not ov.is_suspended(d, r)]
    other = [(d, r) for d, r in gone if not any((d, r) in {(a, b) for a, b, _ in res[x]["known_words"]} | {tuple(y) for y in res[x]["missing_words"]} for x in L)]
    check(f"{l}: every list word shown somewhere (or suspended)", not other, (len(other), other[:6]))
# 5. suspended words aren't counted anywhere
susp_shown = [(l, d, r) for l in L for d, r, _ in res[l]["known_words"] if ov.is_suspended(d, r)] + \
             [(l, *x) for l in L for x in res[l]["missing_words"] if ov.is_suspended(*x)]
check("suspended words are in no count", not susp_shown, susp_shown[:6])
# 6. found marks: known with no note only if marked found
nonote = [(l, d, r) for l in L for d, r, nid in res[l]["known_words"] if nid is None and not ov.is_found(d, r)]
check("known without a note ⇒ marked found (or via a merged form)", len(nonote) == 0, (len(nonote), nonote[:6]))
# 7. frequency tiers
f = res["frequency"]
tiers = f["tiers"]; tot = f.get("tier_totals") or {}
check("tier counts never shrink with a bigger tier", all(a[1] <= b[1] for a, b in zip(tiers, tiers[1:])), tiers)
check("tier counts ≤ tier size", all(k <= n for n, k in tiers), tiers)
nit = f["notes_in_top"]; ks = sorted(nit)
check("notes_in_top never shrinks", all(nit[a] <= nit[b] for a, b in zip(ks, ks[1:])), nit)
check("text coverage within 0–100 %", 0 <= f["text_coverage"] <= 1)
ent = f["entries"]
check("frequency entries ranked 1..N without gaps", [e[0] for e in ent] == list(range(1, len(ent) + 1)))
known_ranks = sum(1 for e in ent[:20000] if e[3] is not None) + len([1 for r in f.get("found_ranks", set()) if r < 20000])
print("  (top-20,000 known by note + found:", known_ranks, " tier says:", dict(tiers).get(20000), ")")
print("ALL PASS" if all(R) else f"{R.count(False)} FAILED")
