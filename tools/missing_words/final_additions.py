"""Word Addition Project: the final word list for tools/build_jlpt.py.

    py -I tools/missing_words/final_additions.py <round2.json> [<round3.json>]

<round2.json> / <round3.json>: the owner's saved page choices (Artifact db docs
review/round2 and review/round3, saved with ArtifactData), {"choices":
{"r<rank>": level | "skip"}}. Order of decisions, later wins:
  top 3,900:     confidence_rules.final() → review/round2 → fit_check.SUGGEST
                 (owner accepted all 67, db doc fit/choices empty)
  #3,901–6,000:  round3.judgements() → review/round3
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


def saved(path):
    return json.load(open(path, encoding="utf-8"))["choices"] if path else {}


r2 = saved(sys.argv[1])
r3 = saved(sys.argv[2] if len(sys.argv) > 2 else None)
cands = json.load(open(os.path.join(HERE, "wa_candidates.json"), encoding="utf-8"))
own = json.load(open(os.path.join(HERE, R.OWNER_FILE), encoding="utf-8"))["choices"]
top = [x for x in cands if x["rank"] <= 3900]
res2 = R.final(top, C.judgements(), own)
j3 = R3.judgements()
seqs = json.load(open(os.path.join(ADDON, "meanings.json"), encoding="utf-8"))["k"]

out, skipped, no_id = [], 0, []
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
    seq = seqs.get(x["d"] + "\t" + x["r"])
    if seq is None:
        no_id.append(x["d"])
    out.append({"level": v[1], "word": x["d"], "reading": x["r"], "jmdict_id": seq, "rank": x["rank"]})

out.sort(key=lambda e: (e["level"], e["rank"]))
json.dump(out, open(os.path.join(HERE, "word_additions.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=0)
print(len(out), "words, skipped", skipped, dict(collections.Counter("N" + e["level"] for e in out)))
print("no JMdict id:", no_id)
