import sys, os, json
S = os.path.dirname(os.path.abspath(__file__))
sys.argv = [sys.argv[0], S]
exec(open(os.path.join(S, "stubs.py"), encoding="utf-8").read())
sp = sentence_parser
rows = json.load(open(os.path.join(S, "missing_common.json"), encoding="utf-8"))
keep = []
for x in rows:
    if x["rank"] > 6000 or x["shared"]:
        continue
    d = x["d"]
    if x["compound"] and d[-2:] in ("える", "ける", "せる", "てる", "める", "れる", "げる", "べる", "ねる"):
        continue
    keep.append(x)
print(len(keep), "after filters (<= 6000)", sum(1 for x in keep if x["rank"] <= 3900), "<= 3900")
for x in keep:
    if x["rank"] <= 3900:
        print(f'{x["rank"]}\t{x["d"]}\t{x["r"]}\t{x["gloss"][:28]}')
json.dump(keep, open(os.path.join(S, "mc_keep.json"), "w", encoding="utf-8"), ensure_ascii=False)
