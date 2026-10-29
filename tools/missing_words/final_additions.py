"""Word Addition Project: the final word list for tools/build_jlpt.py.

    py -I tools/missing_words/final_additions.py <round2.json> [<round3.json>]
        [--speech=<speech.json> --jitendex=<jitendex-yomitan.zip>]

<round2.json> / <round3.json> / <speech.json>: the owner's saved page choices
(Artifact db docs review/round2, review/round3, review/speech, saved with
ArtifactData), {"choices": {"r<rank>": level | "skip" | "other"}}. Order of
decisions, later wins:
  top 3,900:     confidence_rules.final() → review/round2 → fit_check.SUGGEST
                 (owner accepted all 67, db doc fit/choices empty)
  #3,901–6,000:  round3.judgements() → review/round3
  speech:        speech_round.judgements() → frequency rule → review/speech
                 ("other" = owner's note, decided in speech_round.RESOLVED)
Frequency rule (owner 2026-10-29): every addition must sit inside its level's
bar size (speech_round.LEVEL_CAP); a word too rare moves up a level at a time
until it fits. Rank = the better of written and speech rank. A written-round
word with no speech rank keeps its level: the speech list counts short units,
so it splits 日本語 / お願い / 右側 apart and has no rank for them.
Writes word_additions.json next to this script: [{"level", "word", "reading",
"jmdict_id", "rank"}], read by build_jlpt.py as OUR_ADDITIONS (flag "ours").
"""
import collections, json, os, sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
ADDON = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import confidence_3900 as C
import confidence_rules as R
import fit_check as F
import round3 as R3
import speech_round as S


def saved(path):
    return json.load(open(path, encoding="utf-8"))["choices"] if path else {}


def hira(s):
    return "".join(chr(ord(c) - 96) if "ァ" <= c <= "ヶ" else c for c in s)


args = [a for a in sys.argv[1:] if not a.startswith("--")]
opt = lambda name: next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith(f"--{name}=")), None)
speech_arg, jitendex_arg = opt("speech"), opt("jitendex")
r2 = saved(args[0])
r3 = saved(args[1] if len(args) > 1 else None)
rs = saved(speech_arg)
cands = json.load(open(os.path.join(HERE, "wa_candidates.json"), encoding="utf-8"))
own = json.load(open(os.path.join(HERE, R.OWNER_FILE), encoding="utf-8"))["choices"]
top = [x for x in cands if x["rank"] <= 3900]
res2 = R.final(top, C.judgements(), own)
j3 = R3.judgements()
seqs = json.load(open(os.path.join(ADDON, "meanings.json"), encoding="utf-8"))["k"]

# Speech rank of every spelling (freq_cejc.txt: display, reading, per million, alt spellings).
srank = {}
with open(os.path.join(ADDON, "freq_cejc.txt"), encoding="utf-8") as f:
    i = 0
    for line in f:
        if not line.strip() or line.startswith("#"):
            continue
        i += 1
        cols = line.rstrip("\n").split("\t")
        r = hira(cols[1] or cols[0])
        for d in [cols[0]] + [a for a in (cols[3].split("|") if len(cols) > 3 else []) if a]:
            srank.setdefault((d, r), i)

_jm = None


def jmdict_id(d, r):
    # meanings.json first (same ids as before); for speech words it doesn't have
    # yet, Jitendex's best entry the way build_meanings.py picks it (a plain
    # JMdict search would give かえる "frog" the id of 帰る). --jitendex=<zip>.
    global _jm
    seq = seqs.get(d + "\t" + r)
    if seq is not None or not jitendex_arg:
        return seq
    if _jm is None:
        sys.path.insert(0, os.path.join(ADDON, "tools"))
        import build_meanings as BM
        _, index, gl = BM.load_jitendex(jitendex_arg)
        def _jm(key):
            hits = index.get(key)
            if not hits and key[0] == key[1]:     # kana spelling of a kanji headword (どかす → 退かす)
                hits = [h for k, v in index.items() if k[1] == key[1] for h in v]
            return BM.pick(hits, index, gl) if hits else None
    return _jm((d, hira(r)))


out, skipped, no_id, moved = [], 0, [], collections.Counter()
for x in cands:
    if x["rank"] > 6000:
        continue
    key = "r%d" % x["rank"]
    if x["rank"] <= 3900:
        v = r2.get(key, res2[x["rank"]][0])
        if x["d"] in F.SUGGEST:
            v = F.SUGGEST[x["d"]][1]
    else:
        v = r3.get(key, j3[x["d"]][0])
    if v == "skip":
        skipped += 1
        continue
    sp = srank.get((x["d"], hira(x["r"])))
    if sp is not None:
        fv, _ = S.fit_level(v, min(x["rank"], sp))
        if fv != v:
            moved[v + ">" + fv] += 1
            v = fv
    seq = jmdict_id(x["d"], x["r"])
    if seq is None:
        no_id.append(x["d"])
    out.append({"level": v[1], "word": x["d"], "reading": x["r"], "jmdict_id": seq, "rank": x["rank"]})
print("written rounds moved by the frequency rule:", dict(moved))

if speech_arg:
    js, have, s_moved = S.judgements(), {(e["word"], hira(e["reading"])) for e in out}, collections.Counter()
    seen, n_sp = set(), 0
    for x in json.load(open(os.path.join(HERE, "speech_candidates.json"), encoding="utf-8")):
        if x["earlier"] or x["d"] in seen:
            continue                      # the same word under two readings: one row (as on the page)
        seen.add(x["d"])
        rank = min(x["srank"], x["wrank"] or x["srank"])
        v, note = S.fit_level(js[x["d"]][0], rank)
        if note:
            s_moved[js[x["d"]][0] + ">" + v] += 1
        c = rs.get("r%d" % x["srank"])
        if c == "other":
            c = S.RESOLVED[x["srank"]]
        if c:
            v = S.fit_level(c, rank)[0]
        if v == "skip" or (x["d"], hira(x["r"])) in have:
            continue
        seq = jmdict_id(x["d"], x["r"])
        if seq is None:
            no_id.append(x["d"])
        out.append({"level": v[1], "word": x["d"], "reading": x["r"], "jmdict_id": seq, "rank": x["wrank"]})
        n_sp += 1
    print("speech round:", n_sp, "words; moved by the frequency rule:", dict(s_moved))

# Direction sets share one level (owner 2026-10-29): 東西南北 + 口 / 部 / 側 are
# learned together, so all four go to N2 (the level their common members fit)
# and a rarer member (東口 ≈#11,000, 東側 / 南側 / 北側 ≈#7,000) joins as an
# exception to the frequency rule. Missing members are added.
SETS = {"口": "ぐち", "部": "ぶ", "側": "がわ"}
DIRS = {"東": "ひがし", "西": "にし", "南": "みなみ", "北": "きた"}
SET_LEVEL = "2"
for tail, tr in SETS.items():
    for head, hr in DIRS.items():
        d = head + tail
        r = ("とう" if head == "東" else {"西": "せい", "南": "なん", "北": "ほく"}[head]) + "ぶ" if tail == "部" else hr + tr
        e = next((e for e in out if e["word"] == d), None)
        if e:
            e["level"] = SET_LEVEL
        else:
            out.append({"level": SET_LEVEL, "word": d, "reading": r, "jmdict_id": jmdict_id(d, r),
                        "rank": next((x["rank"] for x in cands if x["d"] == d), None)})
            if out[-1]["jmdict_id"] is None:
                no_id.append(d)

out.sort(key=lambda e: (e["level"], e["rank"] or 99999))
json.dump(out, open(os.path.join(HERE, "word_additions.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=0)
print(len(out), "words, skipped", skipped, dict(collections.Counter("N" + e["level"] for e in out)))
print("no JMdict id:", no_id)
