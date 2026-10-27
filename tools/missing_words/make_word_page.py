import sys, os, json, html
S = os.path.dirname(os.path.abspath(__file__))
sys.argv = [sys.argv[0], S]
exec(open(os.path.join(S, "stubs.py"), encoding="utf-8").read())
sys.path.insert(0, S)
import levels_3900 as L
mn = __import__(pkg + ".meanings", fromlist=["x"])
sug = L.suggestions()
rows = []
for x in json.load(open(os.path.join(S, "mc_keep.json"), encoding="utf-8")):
    if x["rank"] > 3900:
        continue
    hit = mn.lookup(x["d"], x["r"])
    senses = [g for _p, g in (hit[1][:3] if hit else [])]
    lvl = sug.get(x["d"], "N2")
    rows.append({"k": x["d"] + "\t" + x["r"], "d": x["d"], "r": x["r"], "rank": x["rank"],
                 "pos": x["pos"], "m": "; ".join(senses)[:160], "s": lvl, "def": x["d"] not in sug})
order = {"N5": 0, "N4": 1, "N3": 2, "N2": 3, "N1": 4, "skip": 5}
rows.sort(key=lambda r: (order[r["s"]], r["rank"]))
counts = {l: sum(1 for r in rows if r["s"] == l) for l in order}
print(counts, len(rows))

PAGE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Missing Words Review</title>
<style>
:root{--bg:#f6f5f2;--card:#fff;--ink:#1d1c1a;--muted:#6b6862;--line:#e3e0da;--accent:#2f5d8a;--chg:#fff4cc;
--n1:#9c27b0;--n2:#f44336;--n3:#ff9800;--n4:#8bc34a;--n5:#4caf50;--skip:#888}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#161514;--card:#201f1d;--ink:#ecebe8;--muted:#a29f98;--line:#34322e;--accent:#8ab4e0;--chg:#3b3214}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,"Segoe UI","Yu Gothic UI",Meiryo,sans-serif}
header{position:sticky;top:0;z-index:5;background:var(--bg);border-bottom:1px solid var(--line);padding:12px 16px}
h1{font-size:18px;margin:0 0 2px}header p{margin:0 0 8px;color:var(--muted);font-size:13px;max-width:900px}
.bar{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
button{font:inherit;font-size:13px;border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:6px;padding:4px 10px;cursor:pointer}
button.on,button.primary{background:var(--accent);color:#fff;border-color:var(--accent)}
main{max-width:1000px;margin:0 auto;padding:12px 16px}
table{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line);border-radius:8px;overflow:hidden}
td,th{padding:6px 10px;border-top:1px solid var(--line);text-align:left;vertical-align:top}
th{font-size:12px;color:var(--muted);font-weight:600}
td.w{font-size:18px;white-space:nowrap}td.r{color:var(--muted);white-space:nowrap}td.m{font-size:13px;color:var(--muted)}
td.k{font-size:12px;color:var(--muted);text-align:right;white-space:nowrap}
tr.chg{background:var(--chg)}
select{font:inherit;font-size:14px;padding:2px 4px;border-radius:5px;border:1px solid var(--line);background:var(--card);color:var(--ink)}
.dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:4px}
#count{font-size:13px;color:var(--muted)}
#out{width:100%;height:150px;margin-top:8px;display:none;font:12px/1.4 monospace;background:var(--card);color:var(--ink);border:1px solid var(--line);border-radius:6px;padding:8px}
@media (max-width:600px){td.m,th.m{display:none}}
</style></head><body>
<header><h1>Words on no JLPT list (top 3,900 by frequency)</h1>
<p>{{SUMMARY}} Each has my suggested level; change the dropdown where you disagree, or pick <b>skip</b> to leave the word off the lists. Changes are saved in this browser and highlighted. Tell Claude when you're done (or press <b>Copy result</b>).</p>
<div class="bar"><span id="tabs"></span><span id="count"></span><button class="primary" id="copy">Copy result</button></div>
<textarea id="out" readonly></textarea></header>
<main><table><thead><tr><th>Word</th><th>Reading</th><th class="m">Meaning</th><th>Rank</th><th>Level</th></tr></thead><tbody id="tb"></tbody></table></main>
<script>
const DATA = /*DATA*/null;
const KEY = "jlpt_missing_words_v1";
let ch = {}; try { ch = JSON.parse(localStorage.getItem(KEY) || "{}"); } catch (e) {}
const save = () => { try { localStorage.setItem(KEY, JSON.stringify(ch)); } catch (e) {} count(); };
const LV = ["N5","N4","N3","N2","N1","skip"];
let tab = "N5";
const esc = s => s.replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const cur = r => ch[r.k] || r.s;
function tabs() {
  const el = document.getElementById("tabs"); el.innerHTML = "";
  for (const l of [...LV, "All"]) {
    const n = DATA.filter(r => l === "All" || r.s === l).length;
    const b = document.createElement("button"); b.className = l === tab ? "on" : "";
    b.innerHTML = (l === "All" ? "" : `<span class="dot" style="background:var(--${l.toLowerCase()})"></span>`) + `${l === "skip" ? "Skip" : l} (${n})`;
    b.onclick = () => { tab = l; tabs(); render(); }; el.appendChild(b); el.append(" ");
  }
}
function render() {
  const tb = document.getElementById("tb"); tb.innerHTML = "";
  for (const r of DATA) {
    if (tab !== "All" && r.s !== tab) continue;
    const tr = document.createElement("tr"); if (ch[r.k]) tr.className = "chg";
    tr.innerHTML = `<td class="w">${esc(r.d)}</td><td class="r">${r.r !== r.d ? esc(r.r) : ""}</td><td class="m">${esc(r.m)}</td><td class="k">#${r.rank.toLocaleString()}</td>`;
    const td = document.createElement("td"); const sel = document.createElement("select");
    for (const l of LV) { const o = document.createElement("option"); o.value = l; o.textContent = l === r.s ? `${l} (suggested)` : l; sel.appendChild(o); }
    sel.value = cur(r);
    sel.onchange = () => { if (sel.value === r.s) delete ch[r.k]; else ch[r.k] = sel.value; tr.className = ch[r.k] ? "chg" : ""; save(); };
    td.appendChild(sel); tr.appendChild(td); tb.appendChild(tr);
  }
}
function result() {
  return DATA.map(r => `${r.d}\t${r.r}\t${cur(r)}${ch[r.k] ? "\t(changed from " + r.s + ")" : ""}`).join("\n");
}
function count() { const n = Object.keys(ch).length; document.getElementById("count").textContent = n ? `${n} changed` : ""; }
document.getElementById("copy").onclick = async () => { const o = document.getElementById("out"); o.value = result(); o.style.display = "block"; o.select(); try { await navigator.clipboard.writeText(o.value); } catch (e) {} };
window.reviewResult = () => JSON.stringify(ch);
tabs(); render(); count();
</script></body></html>"""
summary = (f"{len(rows)} words in the 3,900 most common (the add-on's N5–N3 frequency range) are on no JLPT list "
           f"(after leaving out other spellings of listed words and verb forms like 言える). Suggested: "
           + ", ".join(f"{l} {n}" for l, n in counts.items()) + ".")
out = PAGE.replace("/*DATA*/null", json.dumps(rows, ensure_ascii=False)).replace("{{SUMMARY}}", html.escape(summary))
open(os.path.join(ADDON, "tools", "missing_words_review.html"), "w", encoding="utf-8").write(out)
