// Ko-fi supporter webhook (server/worker.js POST /kofi), with a fake D1.
// Run: node tools/dev/maint/t_kofi.mjs
import worker from "../../../server/worker.js";
const rows = { ABCD2345: { supporter: null, data: '{"rank":1}', name: "Ben", updated: 1 }, WXYZ6789: { supporter: null, data: '{"rank":2}', name: "W", updated: 1 } };
const DB = { prepare(sql) { let args = []; const st = {
  bind(...a) { args = a; return st; },
  async run() { if (sql.startsWith("UPDATE profiles SET supporter")) { const r = rows[args[1]]; if (r && r.supporter == null) r.supporter = args[0]; } return { meta: { changes: 1 } }; },
  async all() { const ids = args.slice(0, -1); return { results: ids.filter((i) => rows[i]).map((i) => ({ id: i, ...rows[i] })) }; },
}; return st; } };
const env = { DB, KOFI_TOKEN: "tok-123" };
async function hook(data) {
  const body = new URLSearchParams({ data: JSON.stringify(data) });
  const r = await worker.fetch(new Request("https://x/kofi", { method: "POST", body }), env);
  return r.status;
}
let fails = 0; const check = (n, ok) => { console.log((ok ? "ok   " : "FAIL ") + n); if (!ok) fails++; };
check("wrong token refused", (await hook({ verification_token: "nope", message: "ABCD-2345" })) === 403 && rows.ABCD2345.supporter === null);
check("no token configured refused", (await worker.fetch(new Request("https://x/kofi", { method: "POST", body: new URLSearchParams({ data: "{}" }) }), { DB })).status === 403);
check("genuine tip with code in text", (await hook({ verification_token: "tok-123", message: "thanks! my code is abcd-2345 :)" })) === 200 && rows.ABCD2345.supporter > 0);
const first = rows.ABCD2345.supporter;
await hook({ verification_token: "tok-123", message: "ABCD2345 again" });
check("first tip's date stays", rows.ABCD2345.supporter === first);
check("unknown code ignored, 200", (await hook({ verification_token: "tok-123", message: "QQQQ-QQQQ" })) === 200);
check("no code in message, 200", (await hook({ verification_token: "tok-123", message: "love the app", from_name: "x" })) === 200 && rows.WXYZ6789.supporter === null);
check("code inside a longer word not taken", (await hook({ verification_token: "tok-123", message: "XWXYZ6789" })) === 200 && rows.WXYZ6789.supporter === null);
const lr = await (await worker.fetch(new Request("https://x/profiles?ids=ABCD2345,WXYZ6789"), env)).json();
check("list carries supporter", lr.profiles.find((p) => p.id === "ABCD2345").supporter === first && lr.profiles.find((p) => p.id === "WXYZ6789").supporter === null);
check("bad body → 400", (await worker.fetch(new Request("https://x/kofi", { method: "POST", body: "garbage" }), env)).status === 400);
// rate limits (guide item 17): over the limit → 429 with a readable message; under → normal
const no = { limit: async () => ({ success: false }) }, yes = { limit: async () => ({ success: true }) };
const r429 = await worker.fetch(new Request("https://x/profiles?ids=ABCD2345"), { ...env, READ_LIMIT: no });
check("list over the read limit → 429", r429.status === 429 && /Too many requests/.test((await r429.json()).error || ""));
check("list under the read limit works", (await worker.fetch(new Request("https://x/profiles?ids=ABCD2345"), { ...env, READ_LIMIT: yes })).status === 200);
check("update over the write limit → 429", (await worker.fetch(new Request("https://x/profile/ABCD2345", { method: "PUT", body: "{}" }), { ...env, WRITE_LIMIT: no })).status === 429);
check("leave over the write limit → 429", (await worker.fetch(new Request("https://x/profile/ABCD2345/leave", { method: "POST", body: "{}" }), { ...env, WRITE_LIMIT: no })).status === 429);
check("kofi isn't held by the read/write limits", (await hook({ verification_token: "tok-123", message: "x" })) === 200);
console.log(fails ? fails + " failed" : "all passed");
