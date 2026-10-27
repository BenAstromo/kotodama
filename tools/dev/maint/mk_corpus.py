import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
texts = set()
for k, v in d.items():
    if isinstance(v, dict):
        texts.update(t for t in v if isinstance(t, str))
with open(sys.argv[2], "w", encoding="utf-8") as f:
    for i, t in enumerate(sorted(texts)):
        t = t.replace("\t", " ").replace("\n", " ")
        f.write(f"{i}\tjpn\t{t}\n")
print(len(texts), list(d))
