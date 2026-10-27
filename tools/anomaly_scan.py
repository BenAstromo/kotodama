"""Scan the user's deck + lists for word-detection anomalies."""
import io, contextlib, sys, os, re, collections
S = sys.argv[1]
with contextlib.redirect_stdout(io.StringIO()):
    exec(open(os.path.join(S, "harness.py"), encoding="utf-8").read())

N = jp._norm; H = jp._kata_to_hira
KANA = re.compile(r"^[぀-ヿー・]+$")
def sec(t): print(f"\n=== {t} ===")

# ── 1. Notes in the deck that were never scanned ──────────────────────────
all_nids = Col().find_notes(f'"deck:{cfg["deck_name"]}"')
skipped = [n for n in all_nids if n not in nd]
sec(f"1. Deck notes not scanned: {len(skipped)} of {len(all_nids)}")
db2 = sqlite3.connect(S + "/col_copy.anki2") if False else None
import sqlite3
dbc = sqlite3.connect(S + "/col_copy.anki2")
mapped = {m["note_type"]: m for m in cfg["field_mappings"]}
why = collections.Counter(); ex = collections.defaultdict(list)
for n in skipped:
    mid, flds = dbc.execute("select mid,flds from notes where id=?", (n,)).fetchone()
    nt = ntypes[mid]; vals = dict(zip(fields[mid], flds.split("\x1f")))
    if nt not in mapped:
        reason = f"note type not mapped: {nt}"
    else:
        f = mapped[nt]["field"]
        reason = "mapped field empty" if not jp._extract_words(vals.get(f, "")) else "duplicate word+reading of another note"
        if reason.startswith("dup"):
            ex[reason].append(jp._extract_words(vals.get(f, ""))[0])
    why[reason] += 1
for r, c in why.most_common(): print(f"  {c:4}  {r}  {ex.get(r, [])[:12]}")

# ── 2. Odd characters in scanned displays/readings ────────────────────────
sec("2. Cards with odd characters in word/reading")
odd = [(n, d, nr.get(n, "")) for n, d in nd.items()
       if re.search(r"[A-Za-z0-9&;<>\[\]()（）{}\s~～]", d + nr.get(n, ""))]
print(f"  {len(odd)}:", [(d, r) for _, d, r in odd[:30]])
noread = [d for n, d in nd.items() if not nr.get(n) and not KANA.match(d)]
print(f"  kanji cards with no reading: {len(noread)}", noread[:20])

# ── 3. JLPT matches that look suspicious ──────────────────────────────────
sec("3. JLPT matches where card spelling AND reading differ from the list entry")
sus = []
for l in jlpt_data.LEVELS:
    for d, r, n in res[l]["known_words"]:
        if not n: continue
        cd, cr = N(nd[n]), nr.get(n, "")
        parts = {H(p) for p in jp._reading_parts(cr)}
        if cd != N(d) and H(N(r)) not in parts:
            sus.append((l, d, r, nd[n], cr))
print(f"  {len(sus)}:"); [print("   ", s) for s in sus[:40]]

# ── 4. A note claimed by several JLPT entries ─────────────────────────────
sec("4. Notes counted for more than one JLPT entry")
cnt = collections.defaultdict(list)
for l in jlpt_data.LEVELS:
    for d, r, n in res[l]["known_words"]:
        if n: cnt[n].append((l, d, r))
multi = {n: v for n, v in cnt.items() if len(v) > 1}
print(f"  {len(multi)}:")
for n, v in list(multi.items())[:40]: print(f"    card {nd[n]}[{nr.get(n,'')}] -> {v}")

# ── 5. Near misses: Non-JLPT cards whose spelling is on a JLPT list ───────
sec("5. Non-JLPT cards whose spelling appears on a JLPT list (reading mismatch?)")
spell = collections.defaultdict(list)
for l in jlpt_data.LEVELS:
    for d, r in lists[l]:
        for f in [d] + jlpt_data.alt_forms(d, r):
            spell[N(f)].append((l, d, r))
near = [(d, nr.get(n, ""), spell[N(d)]) for d, _, n in res["unlisted"]["known_words"] if N(d) in spell]
print(f"  {len(near)}:"); [print("   ", x) for x in near[:60]]

# ── 6. Missing JLPT words that a deck card spells identically ─────────────
sec("6. Missing JLPT words with an identically-spelled card (already used elsewhere)")
missing_hits = []
for l in jlpt_data.LEVELS:
    for d, r in res[l]["missing_words"]:
        for f in [d] + jlpt_data.alt_forms(d, r):
            for n in di.get(N(f), []):
                missing_hits.append((l, d, r, nd[n], nr.get(n, "")))
print(f"  {len(missing_hits)}:"); [print("   ", x) for x in missing_hits[:50]]

# ── 7. Frequency: kana cards matched to many frequency words ──────────────
sec("7. Kana-only cards counted as several frequency words (homophones)")
fe = freq_data.load()
by = collections.defaultdict(list)
for rank, d, r, n in res["frequency"]["entries"]:
    if n: by[n].append((rank, d, r))
kana_multi = [(nd[n], v) for n, v in by.items() if KANA.match(N(nd[n])) and len(v) > 1]
print(f"  {len(kana_multi)}:"); [print("   ", x) for x in kana_multi[:30]]

# ── 8. Frequency entries with odd displays ────────────────────────────────
sec("8. Frequency entries with digits/full-width/odd display")
oddf = [(i + 1, d, r) for i, (d, r, p, f) in enumerate(fe) if re.search(r"[0-9０-９A-Za-zＡ-Ｚ]", d)]
print(f"  {len(oddf)}:", oddf[:30])
