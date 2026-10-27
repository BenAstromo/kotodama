"""Word Addition Project review page, split by confidence (owner 2026-10-19).

    py -I tools/missing_words/make_confidence_page.py <wa_candidates.json>

<wa_candidates.json>: the candidate list (frequency rank, word, reading,
meanings) from the scratch script wa_candidates.py. Writes
tools/missing_words_confidence.html: Sure / Likely pre-set to "add" at the
suggested level, No pre-set to skip, Unsure left for the owner. Choices are
saved in localStorage (jlpt_word_confidence_v1); read them with
window.reviewResult() → {word\treading: level | "skip" | "?"}.
"""
import html, json, os, sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import confidence_3900 as C

cands = [x for x in json.load(open(sys.argv[1], encoding="utf-8")) if x["rank"] <= 3900]
judge = C.judgements()
rows = []
for x in cands:
    tier, lvl = judge[x["d"]]
    rows.append({"k": x["d"] + "\t" + x["r"], "d": x["d"], "r": x["r"] if x["r"] != x["d"] else "",
                 "rank": x["rank"], "m": x["m"], "t": tier, "s": lvl or "skip"})
order = {"sure": 0, "likely": 1, "unsure": 2, "no": 3}
lv = {"N5": 0, "N4": 1, "N3": 2, "N2": 3, "N1": 4, "skip": 5}
rows.sort(key=lambda r: (order[r["t"]], lv[r["s"]], r["rank"]))
counts = {t: sum(1 for r in rows if r["t"] == t) for t in order}
print(counts, len(rows))

PAGE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Word Additions Review</title>
<style>
:root{--bg:#f6f5f2;--card:#fff;--ink:#1d1c1a;--muted:#6b6862;--line:#e3e0da;--accent:#a8780a;--chg:#fff4cc;
--n1:#9c27b0;--n2:#e53935;--n3:#f57c00;--n4:#7cb342;--n5:#43a047;--skip:#8a8a8a;
--sure:#2e7d32;--likely:#558b2f;--unsure:#b26a00;--no:#757575}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#121212;--card:#1c1c1c;--ink:#ebeae6;
--muted:#9d9a93;--line:#2e2d2a;--accent:#d4a017;--chg:#3a3112;--sure:#66bb6a;--likely:#9ccc65;--unsure:#ffb74d;--no:#9e9e9e}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,"Segoe UI","Yu Gothic UI",Meiryo,sans-serif}
header{position:sticky;top:0;z-index:5;background:var(--bg);border-bottom:1px solid var(--line);padding:12px 16px}
h1{font-size:18px;margin:0 0 4px}
header p{margin:0 0 8px;color:var(--muted);font-size:13px;max-width:920px}
.tally{display:flex;flex-wrap:wrap;gap:14px;font-size:13px;align-items:center}
.tally b{font-variant-numeric:tabular-nums}
button{font:inherit;font-size:13px;border:1px solid var(--line);background:var(--card);color:var(--ink);
border-radius:6px;padding:4px 10px;cursor:pointer}
button:hover{border-color:var(--accent)}
button.primary{background:var(--accent);color:#111;border-color:var(--accent)}
main{max-width:1000px;margin:0 auto;padding:12px 16px 80px}
details{background:var(--card);border:1px solid var(--line);border-radius:10px;margin:14px 0;overflow:hidden}
summary{cursor:pointer;padding:12px 14px;display:flex;gap:10px;align-items:baseline;flex-wrap:wrap;list-style:none}
summary::-webkit-details-marker{display:none}
summary h2{font-size:16px;margin:0}
summary .why{color:var(--muted);font-size:13px;flex:1;min-width:220px}
summary .n{font-size:13px;color:var(--muted)}
.dot{width:10px;height:10px;border-radius:50%;display:inline-block;align-self:center}
.bulk{display:flex;gap:8px;flex-wrap:wrap;padding:0 14px 10px}
table{width:100%;border-collapse:collapse}
td,th{padding:6px 10px;border-top:1px solid var(--line);text-align:left;vertical-align:top}
th{font-size:12px;color:var(--muted);font-weight:600}
td.w{font-size:18px;white-space:nowrap}
td.w small{display:block;font-size:12px;color:var(--muted)}
td.m{font-size:13px;color:var(--muted)}
td.k{font-size:12px;color:var(--muted);text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}
td.c{white-space:nowrap}
select{font:inherit;font-size:13px;padding:3px 6px;border-radius:6px;border:1px solid var(--line);background:var(--card);color:var(--ink)}
tr.changed td{background:var(--chg)}
.lvl-N5{color:var(--n5)}.lvl-N4{color:var(--n4)}.lvl-N3{color:var(--n3)}.lvl-N2{color:var(--n2)}.lvl-N1{color:var(--n1)}
.lvl-skip{color:var(--skip)}.lvl-q{color:var(--unsure);font-weight:600}
.sug{font-size:12px;color:var(--muted)}
#copied{color:var(--sure);font-size:13px}
@media (max-width:640px){td.m{display:none}th.m{display:none}}
</style></head><body>
<header>
<h1>Word additions — words on no JLPT list, split by confidence</h1>
<p>Frequency words in the top 3,900 that no JLPT list covers. The question for each: is it so common in modern Japanese that it wouldn't be surprising on the test?
<b>Sure</b> and <b>Likely</b> are set to be added at the level shown, <b>No</b> is set to skip: just skim those.
<b>Unsure</b> needs your call: pick a level to add it, or Skip. Changes save automatically in this page.</p>
<div class="tally"><span>Add: <b id="t-add"></b></span><span>Skip: <b id="t-skip"></b></span>
<span>Undecided: <b id="t-q"></b></span><span id="t-lv"></span>
<button class="primary" id="copy">Copy result</button><span id="copied"></span></div>
</header><main id="main"></main>
<script>
const ROWS = __ROWS__;
const TIERS = [
 ["sure", "Sure", "Everyday or modern words; leaving them off looks like an oversight. Set to add.", true],
 ["likely", "Likely", "Common general words, a bit more written or narrower in use. Set to add.", false],
 ["unsure", "Unsure", "High mainly because the frequency list leans on news, official papers, law and finance, or borderline. Your call: the suggested level is shown.", true],
 ["no", "No", "Not a learner's word on its own: suffix or counter readings (年 ねん), pieces of longer words, title fragments, fillers, counter compounds (三人). Set to skip.", false]];
const LV = ["N5", "N4", "N3", "N2", "N1"];
const KEY = "jlpt_word_confidence_v1";
let saved = {};
try { saved = JSON.parse(localStorage.getItem(KEY) || "{}"); } catch (e) {}
const dflt = r => r.t === "unsure" ? "?" : r.s;
const val = r => (r.k in saved) ? saved[r.k] : dflt(r);
function save() { try { localStorage.setItem(KEY, JSON.stringify(saved)); } catch (e) {} }
function esc(s) { return String(s).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c])); }
function opts(r) {
  const v = val(r), list = (r.t === "unsure" ? ["?"] : []).concat(LV, ["skip"]);
  return list.map(o => `<option value="${o}"${o === v ? " selected" : ""}>${o === "?" ? "? decide" : o === "skip" ? "Skip" : o}</option>`).join("");
}
function cls(v) { return v === "?" ? "lvl-q" : "lvl-" + v; }
function render() {
  const main = document.getElementById("main"); main.innerHTML = "";
  for (const [t, name, why, open] of TIERS) {
    const rs = ROWS.filter(r => r.t === t);
    const d = document.createElement("details"); if (open) d.open = true;
    d.innerHTML = `<summary><span class="dot" style="background:var(--${t})"></span><h2>${name}</h2>
      <span class="n">${rs.length} words</span><span class="why">${why}</span></summary>
      <div class="bulk">${t === "no" ? "" : `<button data-bulk="sug">All → suggested level</button>`}
      <button data-bulk="skip">All → Skip</button><button data-bulk="reset">Reset this group</button></div>
      <table><thead><tr><th>Word</th><th class="m">Meaning</th><th>Rank</th><th>Level</th></tr></thead><tbody></tbody></table>`;
    const tb = d.querySelector("tbody");
    for (const r of rs) {
      const tr = document.createElement("tr"); tr.dataset.k = r.k;
      const v = val(r);
      if (v !== dflt(r)) tr.className = "changed";
      tr.innerHTML = `<td class="w">${esc(r.d)}${r.r ? `<small>${esc(r.r)}</small>` : ""}</td>
        <td class="m">${esc(r.m)}</td><td class="k">#${r.rank.toLocaleString()}</td>
        <td class="c"><select class="${cls(v)}">${opts(r)}</select>
        ${t === "unsure" ? `<div class="sug">suggested ${r.s}</div>` : ""}</td>`;
      tr.querySelector("select").addEventListener("change", e => {
        const nv = e.target.value;
        if (nv === dflt(r)) delete saved[r.k]; else saved[r.k] = nv;
        save(); e.target.className = cls(nv); tr.className = nv !== dflt(r) ? "changed" : ""; tally();
      });
      tb.appendChild(tr);
    }
    d.querySelectorAll("[data-bulk]").forEach(b => b.addEventListener("click", () => {
      for (const r of rs) {
        const nv = b.dataset.bulk === "sug" ? r.s : b.dataset.bulk === "skip" ? "skip" : dflt(r);
        if (nv === dflt(r)) delete saved[r.k]; else saved[r.k] = nv;
      }
      save(); render();
    }));
    main.appendChild(d);
  }
  tally();
}
function result() { const o = {}; for (const r of ROWS) o[r.k] = val(r); return o; }
function tally() {
  const res = Object.values(result());
  const add = res.filter(v => LV.includes(v));
  document.getElementById("t-add").textContent = add.length;
  document.getElementById("t-skip").textContent = res.filter(v => v === "skip").length;
  document.getElementById("t-q").textContent = res.filter(v => v === "?").length;
  document.getElementById("t-lv").textContent = LV.map(l => `${l} ${add.filter(v => v === l).length}`).join(" · ");
}
window.reviewResult = result;
document.getElementById("copy").addEventListener("click", async () => {
  const txt = JSON.stringify(result());
  try { await navigator.clipboard.writeText(txt); document.getElementById("copied").textContent = "Copied"; }
  catch (e) { document.getElementById("copied").textContent = "Copy failed; I can read it from the page"; }
});
render();
</script></body></html>"""

out = os.path.join(os.path.dirname(HERE), "missing_words_confidence.html")
open(out, "w", encoding="utf-8").write(PAGE.replace("__ROWS__", json.dumps(rows, ensure_ascii=False)))
print("wrote", out)
