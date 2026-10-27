"""Check verdicts against the detector; optionally append them to grammar_cases.json.

    python check_batches.py <verdicts module> <batch files, comma-separated> [--add-cases]
"""
import importlib.util, json, os, re, sys, types

sys.stdout.reconfigure(encoding="utf-8")
ADDON = r"C:/Users/benne/AppData/Roaming/Anki2/addons21/jlpt_progress"


exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "gem_head.py"), encoding="utf-8").read())

spec = importlib.util.spec_from_file_location("v", sys.argv[1])
vm = importlib.util.module_from_spec(spec); spec.loader.exec_module(vm)
src = "".join(open(f, encoding="utf-8").read() for f in sys.argv[2].split(","))
sents = {}
for blk in src.split("=" * 78 + "\n")[1:]:
    m = re.match(r"\[N\d\] (\S+)", blk)
    if m:
        sents[m.group(1)] = [re.sub(r"[【】]", "", l.split(". ", 1)[1])
                             for l in blk.splitlines() if re.match(r"  \d+\. ", l)]
bad = 0
cases = []
for gid, (wrong, moved) in vm.V.items():
    ss = sents.get(gid)
    if not ss:
        print("no sentences for", gid); bad += 1; continue
    wrong = set(range(1, len(ss) + 1)) if wrong is None else set(wrong)
    for n, t in enumerate(ss, 1):
        ids = gd.sentence_ids(t)
        want_absent = n in wrong
        ok = (gid not in ids) if want_absent else (gid in ids)
        if n in moved:
            ok = ok and moved[n] in ids
        if not ok:
            bad += 1
            print(f"MISMATCH {gid} #{n} want {'absent' if want_absent else 'present'}"
                  f"{' + ' + moved[n] if n in moved else ''}: {t}\n    got {ids}")
        if want_absent or n in moved:
            cases.append({"text": t, "absent": [gid] if want_absent else [],
                          "present": [moved[n]] if n in moved else []})
print(f"{bad} mismatch(es); {len(cases)} wrong-hit cases")
if "--add-cases" in sys.argv and not bad:
    p = os.path.join(ADDON, "tools", "grammar_cases.json")
    d = json.load(open(p, encoding="utf-8"))
    have = {c["text"] for c in d["cases"]}
    added = 0
    for c in cases:
        if c["text"] in have:
            for c2 in d["cases"]:
                if c2["text"] == c["text"]:
                    c2["absent"] = sorted(set(c2["absent"]) | set(c["absent"]))
                    c2["present"] = sorted(set(c2["present"]) | set(c["present"]))
        else:
            d["cases"].append(c); have.add(c["text"]); added += 1
    open(p, "w", encoding="utf-8", newline="\n").write(json.dumps(d, ensure_ascii=False, indent=1) + "\n")
    print("added", added, "cases; total", len(d["cases"]))
