import json, os, re, sys, unicodedata
from collections import Counter, defaultdict
sys.stdout.reconfigure(encoding="utf-8")
A = sys.argv[1]
def rows(fn):
    raw = open(os.path.join(A, fn), "rb").read()
    probs = []
    if raw.startswith(b"\xef\xbb\xbf"): probs.append("UTF-8 BOM")
    if b"\r\n" in raw: probs.append("CRLF line endings")
    txt = raw.decode("utf-8")
    if "\ufffd" in txt: probs.append("replacement char U+FFFD")
    out = []
    for i, line in enumerate(txt.split("\n"), 1):
        if not line.strip() or line.startswith("#"):
            continue
        out.append((i, line.rstrip("\r").split("\t")))
    return txt, out, probs
def odd(s):
    return [c for c in s if unicodedata.category(c) in ("Cc", "Cf", "Zs") and c != " " or c in "\u3000"] 
report = []
# JLPT lists
level_of = defaultdict(list)
for lvl in ("n5", "n4", "n3", "n2", "n1"):
    fn = f"jlpt_{lvl}.txt"; txt, rs, probs = rows(fn)
    m = re.search(r"— ([\d,]+) words", txt)
    head_n = int(m.group(1).replace(",", "")) if m else None
    keys = Counter((r[0], r[1]) for _, r in rs)
    dups = [k for k, n in keys.items() if n > 1]
    bad = [(i, r) for i, r in rs if len(r) < 2 or not r[0].strip() or not r[1].strip() or len(r) > 5]
    ws = [(i, r) for i, r in rs if any(c != c.strip() for c in r[:2]) or any(odd(c) for c in r)]
    nfkc = [(i, r[0]) for i, r in rs if unicodedata.normalize("NFKC", r[0]) != r[0]]
    for _, r in rs: level_of[(r[0], r[1])].append(lvl.upper())
    report.append(f"{fn}: {len(rs)} rows (header says {head_n}); dups {len(dups)} {dups[:5]}; malformed {len(bad)} {bad[:3]}; "
                  f"stray whitespace/control {len(ws)} {ws[:3]}; non-NFKC display {len(nfkc)} {nfkc[:5]}; {probs or 'encoding ok'}")
multi = {k: v for k, v in level_of.items() if len(v) > 1}
report.append(f"JLPT word+reading on several levels: {len(multi)} {list(multi.items())[:8]}")
# kanji
txt, rs, probs = rows("kanji_jlpt.txt")
ch = Counter(r[0] for _, r in rs)
bad = [(i, r[:3]) for i, r in rs if len(r[0]) != 1 or r[1] not in ("N5","N4","N3","N2","N1") or len(r) < 7]
report.append(f"kanji_jlpt.txt: {len(rs)} rows; dup chars {[k for k,n in ch.items() if n>1][:10]}; malformed {len(bad)} {bad[:5]}; {probs or 'encoding ok'}")
# freq
txt, rs, probs = rows("freq_bccwj.txt")
keys = Counter((r[0], r[1]) for _, r in rs)
bad = [(i, r) for i, r in rs if len(r) < 4 or not re.fullmatch(r"[\d.]+", r[2] or "")]
nonmono = [(rs[j][0], rs[j][1][2], rs[j+1][1][2]) for j in range(len(rs)-1)
           if len(rs[j][1]) > 2 and len(rs[j+1][1]) > 2 and re.fullmatch(r"[\d.]+", rs[j][1][2]) and re.fullmatch(r"[\d.]+", rs[j+1][1][2])
           and float(rs[j+1][1][2]) > float(rs[j][1][2])]
report.append(f"freq_bccwj.txt: {len(rs)} rows; dups {[k for k,n in keys.items() if n>1][:8]}; malformed {len(bad)} {bad[:3]}; "
              f"frequency not descending at {len(nonmono)} places {nonmono[:5]}; {probs or 'encoding ok'}")
txt, rs2, probs = rows("freq_extra.txt")
keys2 = Counter((r[0], r[1]) for _, r in rs2)
bad = [(i, r) for i, r in rs2 if len(r) < 4 or r[3] not in ("e", "x") or not r[2].isdigit()]
overlap = set(keys) & set(keys2)
report.append(f"freq_extra.txt: {len(rs2)} rows; dups {sum(1 for n in keys2.values() if n>1)} {[k for k,n in keys2.items() if n>1][:6]}; malformed {len(bad)} {bad[:3]}; "
              f"also in top 20,000: {len(overlap)} {list(overlap)[:6]}; {probs or 'encoding ok'}")
for fn, cols in (("kana_ok.txt", 2), ("kana_usual.txt", 3), ("kinds_fix.txt", 4)):
    txt, rs, probs = rows(fn)
    k = Counter(tuple(r[:2]) for _, r in rs)
    bad = [(i, r) for i, r in rs if len(r) < cols]
    report.append(f"{fn}: {len(rs)} rows; dups {[x for x,n in k.items() if n>1]}; malformed {bad[:5]}; {probs or 'encoding ok'}")
# grammar json
g = json.load(open(os.path.join(A, "grammar_jlpt.json"), encoding="utf-8"))
pts = g["points"]; ids = Counter(p["id"] for p in pts)
lv = Counter(p["level"] for p in pts)
missing = [p.get("id") for p in pts if not all(p.get(k) for k in ("id", "level", "pattern", "meaning"))]
report.append(f"grammar_jlpt.json: {len(pts)} points {dict(lv)}; dup ids {[k for k,n in ids.items() if n>1]}; missing fields {missing[:8]}")
m = json.load(open(os.path.join(A, "meanings.json"), encoding="utf-8"))
dangling = [k for k, s in m["k"].items() if str(s) not in m["m"]]
emptym = [s for s, v in m["m"].items() if not v or not v[1]]
report.append(f"meanings.json: {len(m['k'])} keys, {len(m['m'])} entries; keys pointing nowhere {len(dangling)} {dangling[:5]}; empty entries {len(emptym)} {emptym[:5]}")
print("\n".join(report))
