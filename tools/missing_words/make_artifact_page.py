"""Word Addition Project: build the phone review page (claude.ai Artifact).

    py -I tools/missing_words/make_artifact_page.py [out.html]

Reads wa_candidates.json (from wa_candidates.py), confidence_3900.py (tiers),
confidence_rules.py + owner_choices_2026-10-20.json (round 2) and fills
artifact_template.html. Default output: word_additions.html in this folder
(not shipped; tools/ is outside the package). Publish it with the Artifact
tool to the existing URL https://claude.ai/artifact/NHt9rMw2icW5aSLuNxSLuq
(capabilities {"db": {}} are already stored there). The page saves choices
to the db doc review/round2 = {choices: {"r<rank>": level|"skip"}, updated},
only where they differ from the page's value. Bump the db doc name in the
template (docRef = db.doc("review/round2")) when starting a new round.
"""
import json, os, sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import confidence_3900 as C
import confidence_rules as R

cands = [x for x in json.load(open(os.path.join(HERE, "wa_candidates.json"), encoding="utf-8"))
         if x["rank"] <= 3900]
judge = C.judgements()
own = json.load(open(os.path.join(HERE, R.OWNER_FILE), encoding="utf-8"))["choices"]
res = R.final(cands, judge, own)
rows = []
for x in cands:
    v, why, seen = res[x["rank"]]
    rows.append({"rank": x["rank"], "d": x["d"], "r": "" if x["r"] == x["d"] else x["r"], "m": x["m"],
                 "t": judge[x["d"]][0], "s": v, "was": seen, "why": why})
lv = {"N5": 0, "N4": 1, "N3": 2, "N2": 3, "N1": 4, "skip": 5}
rows.sort(key=lambda r: (lv[r["s"]], r["rank"]))
tpl = open(os.path.join(HERE, "artifact_template.html"), encoding="utf-8").read()
out = tpl.replace("__ROWS__", json.dumps(rows, ensure_ascii=False).replace("</", "<\\/"))
path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "word_additions.html")
open(path, "w", encoding="utf-8").write(out)
print(len(rows), "rows,", sum(1 for r in rows if r["was"] != r["s"]), "changed →", path)
