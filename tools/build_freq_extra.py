"""Build freq_extra.txt: frequency ranks for words that freq_bccwj.txt (the
top 20,000 short-unit words) doesn't rank.

Two kinds of entry:
  x  exact      short-unit (SUW) words ranked beyond 20,000, with their real
                SUW rank (same filtering/mapping as build_freq.py).
  e  estimated  long-unit (LUW) words — compounds and set phrases the SUW list
                splits apart (日本語 = 日本 + 語, 可能性 = 可能 + 性, お願い =
                お + 願い). Their rank is where their frequency would fall in
                the SUW ranking (same per-million scale, laws register
                excluded). Nothing is inserted into the SUW ranking, so the
                top-20,000 list, its tiers and coverage stay unchanged.

The add-on only uses these for display and sorting ("≈#2,340"), never for
the Frequency Check bars.

Usage (from the folder containing data/jmdict.pkl):
    python tools/build_freq_extra.py <addon_dir> <suw.tsv> <luw.zip or .tsv>
"""
import bisect, csv, collections, io, pickle, re, sys, zipfile

csv.field_size_limit(10**9)
A, SUW_PATH, LUW_PATH = sys.argv[1:4]
CAP = 40_000          # don't list words rarer than this rank (keeps the file ~2 MB)
J = pickle.load(open("data/jmdict.pkl", "rb"))
byk = collections.defaultdict(list); byr = collections.defaultdict(list)
for s, e in J.items():
    for k in e["keb"]: byk[k].append(s)
    for r in e["reb"]: byr[r].append(s)
k2h = lambda s: "".join(chr(ord(c) - 0x60) if "ァ" <= c <= "ヶ" else c for c in s)
# Same content parts of speech and register exclusion as build_freq.py.
KEEP = ("名詞-普通名詞", "動詞", "形容詞", "形状詞-一般", "形状詞-タリ", "副詞", "連体詞",
        "接続詞", "感動詞-一般", "代名詞")
EXCLUDED_REGISTERS = ("OL",)
JP = re.compile(r"[぀-ヿ一-鿿㐀-䶿々〆]+")
KANJI = re.compile(r"[一-鿿㐀-䶿々〆]")
UK = "word usually written using kana alone"


def read_tsv(path):
    if path.endswith(".zip"):
        z = zipfile.ZipFile(path)
        name = next(n for n in z.namelist() if n.endswith(".tsv"))
        return io.TextIOWrapper(z.open(name), encoding="utf-8")
    return open(path, encoding="utf-8")


def aggregate(path):
    """{(lemma, reading): frequency} for content words, and the corpus total."""
    agg = collections.OrderedDict(); total = 0
    with read_tsv(path) as f:
        for row in csv.DictReader(f, delimiter="\t"):
            freq = int(row["frequency"]) - sum(int(row[r + "_frequency"] or 0) for r in EXCLUDED_REGISTERS)
            total += freq
            if not row["pos"].startswith(KEEP):
                continue
            lemma = row["lemma"]; rd = k2h(row["lForm"])
            if not lemma or not rd or not JP.fullmatch(lemma):
                continue
            agg[(lemma, rd)] = agg.get((lemma, rd), 0) + freq
    return agg, total


def map_entry(lemma, rd):
    """(display, reading, forms, seq) via JMdict, as in build_freq.py; None if
    the word has no dictionary entry."""
    cands = [s for s in set(byk.get(lemma, []) + byr.get(lemma, []))
             if rd in [k2h(r) for r in J[s]["reb"]]]
    if not cands:
        return None
    def _rpos(s):
        rs = [k2h(r) for r in J[s]["reb"]]
        return rs.index(rd) if rd in rs else 99
    cands.sort(key=lambda s: (0 if lemma in J[s]["keb"] else 1, _rpos(s), s))
    e = J[cands[0]]
    is_kana = not KANJI.search(lemma)
    uk = bool(e["misc"]) and UK in (e["misc"][0] or [])
    display = (lemma if is_kana else rd) if (is_kana or uk or not e["keb"]) else e["keb"][0]
    forms = [lemma]
    for x in e["keb"] + e["reb"]:
        if x not in forms:
            forms.append(x)
    if display not in forms:
        forms.insert(0, display)
    return display, (lemma if is_kana else rd), forms, cands[0]


# ── SUW: the full ranking (the first 20,000 are freq_bccwj.txt) ─────────────
suw, total = aggregate(SUW_PATH)
suw_mapped = []
for (lemma, rd), fr in sorted(suw.items(), key=lambda kv: -kv[1]):
    m = map_entry(lemma, rd)
    if m:
        suw_mapped.append((m, fr / total * 1e6))
print("SUW mapped words:", len(suw_mapped), file=sys.stderr)

# Sanity check: the first 20,000 must be exactly the bundled list.
bundled = [l.split("\t")[0] for l in open(A + "/freq_bccwj.txt", encoding="utf-8")
           if l.strip() and not l.startswith("#")]
same = sum(1 for (m, _), d in zip(suw_mapped, bundled) if m[0] == d)
print(f"top-20,000 agreement with freq_bccwj.txt: {same:,} / {len(bundled):,}", file=sys.stderr)

covered = {m[3] for m, _ in suw_mapped}              # JMdict entries the SUW list ranks
neg_pmws = [-p for _, p in suw_mapped]                # ascending, for bisect
out = []
for rank, (m, pmw) in enumerate(suw_mapped[20_000:CAP], start=20_001):
    out.append((m[0], m[1], rank, "x", m[2]))

# ── LUW: compounds and phrases the SUW list never ranks ─────────────────────
luw, _ = aggregate(LUW_PATH)
by_seq = {}
for (lemma, rd), fr in luw.items():
    m = map_entry(lemma, rd)
    if not m or m[3] in covered:
        continue
    pmw = fr / total * 1e6                            # same scale as the SUW list
    if m[3] not in by_seq or by_seq[m[3]][1] < pmw:
        by_seq[m[3]] = (m, pmw)
n_est = 0
for m, pmw in sorted(by_seq.values(), key=lambda v: -v[1]):
    est = bisect.bisect_left(neg_pmws, -pmw) + 1     # SUW words more frequent, + 1
    if est > CAP:
        break
    out.append((m[0], m[1], est, "e", m[2])); n_est += 1
print("estimated (LUW) entries:", n_est, file=sys.stderr)

with open(A + "/freq_extra.txt", "w", encoding="utf-8", newline="\n") as f:
    f.write("# Frequency ranks for words outside freq_bccwj.txt's top 20,000 (display and sorting only).\n")
    f.write("# Source: NINJAL BCCWJ short-unit (x = exact rank beyond 20,000) and long-unit\n")
    f.write("#   (e = estimated: where a compound's frequency falls in the short-unit ranking)\n")
    f.write("#   frequency lists v1.0 (CC BY-NC-ND 3.0); laws register excluded; spellings via JMdict.\n")
    f.write("# Format: display<TAB>reading<TAB>rank<TAB>x|e<TAB>other spellings (|-separated)\n\n")
    for d, r, rank, kind, forms in sorted(out, key=lambda t: t[2]):
        # The display and reading are always matched; list only the others.
        extra = [x for x in forms if x not in (d, r)]
        f.write(f"{d}\t{r}\t{rank}\t{kind}\t{'|'.join(extra)}\n")
print(len(out), "entries written")
