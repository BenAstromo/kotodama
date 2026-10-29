"""Word Addition Project, spoken round (owner 2026-10-28): words in the top
6,000 of everyday conversation (freq_cejc.txt, CEJC) that no JLPT list entry
covers. Written frequency underrates basic spoken words (animals, household
things, body parts), so this finds gaps the BCCWJ rounds missed.

    py -I tools/missing_words/speech_candidates.py

Covered = the row's display or any of its spellings is a list word or
alternate spelling with a matching reading (katakana folded to hiragana).
Each candidate gets its written (BCCWJ) rank and, when an earlier round
already judged it, that decision. Writes speech_candidates.json here.
"""
import json, os, sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
ADDON = os.path.dirname(os.path.dirname(HERE))
LIMIT = 6000
hira = lambda s: "".join(chr(ord(c) - 0x60) if "ァ" <= c <= "ヶ" else c for c in s)


def rows(name):
    for line in open(os.path.join(ADDON, name), encoding="utf-8"):
        if line.startswith("#") or not line.strip():
            continue
        p = line.rstrip("\n").split("\t")
        yield p[0], p[1], [s for s in p[3].split("|") if s] if len(p) > 3 else []


listed = set()   # (spelling, reading in hiragana)
for l in "54321":
    for line in open(os.path.join(ADDON, f"jlpt_n{l}.txt"), encoding="utf-8"):
        if line.startswith("#") or not line.strip():
            continue
        p = line.rstrip("\n").split("\t")
        reads = [p[1]] + [r for r in (p[4].split("|") if len(p) > 4 else []) if r]
        for f in [p[0]] + [a for a in (p[2].split("|") if len(p) > 2 else []) if a]:
            for r in reads:
                listed.add((f, hira(r)))

written = {}
for i, (d, r, fs) in enumerate(rows("freq_bccwj.txt"), 1):
    written.setdefault((d, hira(r)), i)

judged = {}
for x in json.load(open(os.path.join(HERE, "wa_candidates.json"), encoding="utf-8")):
    judged[(x["d"], hira(x["r"]))] = x["rank"]
adds = {(e["word"], hira(e["reading"])) for e in json.load(open(os.path.join(HERE, "word_additions.json"), encoding="utf-8"))}

sys.path.insert(0, HERE)
exec(open(os.path.join(HERE, "wa_candidates.py"), encoding="utf-8").read().split("import importlib")[0])
import importlib
mn = importlib.import_module("jlpt_progress.meanings")

out = []
for i, (d, r, fs) in enumerate(rows("freq_cejc.txt"), 1):
    if i > LIMIT:
        break
    rh = hira(r)
    if any((f, rh) in listed for f in [d] + fs):
        continue
    hit = mn.lookup(d, r)
    out.append({"srank": i, "d": d, "r": r, "wrank": written.get((d, rh)),
                "earlier": ("added" if (d, rh) in adds else "skipped") if (d, rh) in judged else "",
                "pos": hit[1][0][0] if hit and hit[1] else "", "m": "; ".join(s[1] for s in hit[1])[:110] if hit and hit[1] else ""})
json.dump(out, open(os.path.join(HERE, "speech_candidates.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
new = [x for x in out if not x["earlier"]]
print(len(out), "not on the lists;", len(out) - len(new), "already judged in rounds 2–3;", len(new), "new")
