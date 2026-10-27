// Kotodama Nakama 仲間: the friends board's tiny profile store.
//
// A profile is a name + a small JSON snapshot of the add-on's bars. No
// accounts: creating a profile returns a friend code (the profile's id,
// shared with friends) and a secret key (kept only in the user's Anki;
// needed to update or delete). Anyone with a code can read that profile;
// there is no listing or search, so a profile is only seen by people who
// were given its code.
//
//   POST   /profile            {name, data}           → {id, key}   create
//   PUT    /profile/<id>       {key, name, data}      → {ok}        update
//   POST   /profile/<id>/leave {key}                  → {ok}        leave, keep the code
//   DELETE /profile/<id>       {key}                  → {ok}        delete
//   GET    /profiles?ids=A,B   → {profiles: [{id, name, data, updated}]}
//
// Leaving (2026-10-20) erases the name and snapshot (data "{}") but keeps the
// row: the code stays reserved for its key, so rejoining (a PUT with the key)
// gets the same code back at once. Left profiles are never listed, and the
// daily cron frees them after STALE_DAYS like any unused profile. DELETE
// (older add-on versions' Leave) still removes the row.
//
// Free-plan friendly: one D1 row per user, updates at most once a minute,
// small bodies, creation rate-limited per IP, profiles unused for 400 days
// removed by the daily cron.

const CODE_CHARS = "23456789ABCDEFGHJKMNPQRSTUVWXYZ";   // no 0/O, 1/I/L
const CODE_LEN = 8;
const MAX_BODY = 8192;
const MAX_DATA = 6000;
const MAX_NAME = 32;
const MAX_IDS = 60;
const MIN_UPDATE_GAP = 60;                 // seconds
const STALE_DAYS = 400;
const LEFT = "{}";                         // the data of a profile that left

const JSON_HEADERS = { "content-type": "application/json", "cache-control": "no-store" };

function reply(obj, status = 200) {
  return new Response(JSON.stringify(obj), { status, headers: JSON_HEADERS });
}

function err(msg, status = 400) {
  return reply({ error: msg }, status);
}

function newCode() {
  const b = crypto.getRandomValues(new Uint8Array(CODE_LEN));
  let s = "";
  for (const x of b) s += CODE_CHARS[x % CODE_CHARS.length];
  return s;
}

function newKey() {
  return [...crypto.getRandomValues(new Uint8Array(32))]
    .map((x) => x.toString(16).padStart(2, "0")).join("");
}

async function sha256(s) {
  const h = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(s));
  return [...new Uint8Array(h)].map((x) => x.toString(16).padStart(2, "0")).join("");
}

function cleanCode(s) {
  s = String(s || "").toUpperCase().replace(/[^0-9A-Z]/g, "");
  return s.length === CODE_LEN && [...s].every((c) => CODE_CHARS.includes(c)) ? s : null;
}

function cleanName(s) {
  // printable text only, trimmed, capped
  s = String(s || "").replace(/[\u0000-\u001f\u007f-\u009f​-‏‪-‮⁦-⁩]/g, "")
    .replace(/\s+/g, " ").trim();
  return [...s].slice(0, MAX_NAME).join("");
}

function cleanData(d) {
  if (!d || typeof d !== "object" || Array.isArray(d)) return null;
  const s = JSON.stringify(d);
  return s.length <= MAX_DATA ? s : null;
}

async function readBody(request) {
  const len = Number(request.headers.get("content-length") || 0);
  if (len > MAX_BODY) return null;
  const text = await request.text();
  if (text.length > MAX_BODY) return null;
  try {
    const v = JSON.parse(text);
    return v && typeof v === "object" ? v : null;
  } catch {
    return null;
  }
}

async function checkKey(env, id, key) {
  if (typeof key !== "string" || key.length !== 64) return null;
  const row = await env.DB.prepare("SELECT key_hash, updated, data FROM profiles WHERE id = ?")
    .bind(id).first();
  if (!row) return { missing: true };
  return row.key_hash === (await sha256(key)) ? row : null;
}

async function create(request, env) {
  if (env.CREATE_LIMIT) {
    const ip = request.headers.get("cf-connecting-ip") || "unknown";
    const { success } = await env.CREATE_LIMIT.limit({ key: ip });
    if (!success) return err("Too many new profiles from here. Try again in a minute.", 429);
  }
  const body = await readBody(request);
  if (!body) return err("Bad request");
  const name = cleanName(body.name);
  const data = cleanData(body.data);
  if (!name || !data) return err("A name and progress data are needed");
  const key = newKey();
  const hash = await sha256(key);
  const now = Math.floor(Date.now() / 1000);
  for (let tries = 0; tries < 5; tries++) {
    const id = newCode();
    const r = await env.DB.prepare(
      "INSERT OR IGNORE INTO profiles (id, key_hash, name, data, created, updated) VALUES (?, ?, ?, ?, ?, ?)"
    ).bind(id, hash, name, data, now, now).run();
    if (r.meta.changes === 1) return reply({ id, key });
  }
  return err("Couldn't make a code. Try again.", 500);
}

async function update(request, env, id) {
  const body = await readBody(request);
  if (!body) return err("Bad request");
  const row = await checkKey(env, id, body.key);
  if (!row) return err("Wrong key", 403);
  if (row.missing) return err("No such profile", 404);
  const name = cleanName(body.name);
  const data = cleanData(body.data);
  if (!name || !data) return err("A name and progress data are needed");
  const now = Math.floor(Date.now() / 1000);
  // (rejoining after Leave isn't held back by the once-a-minute limit)
  if (row.data !== LEFT && now - row.updated < MIN_UPDATE_GAP) return err("Updated a moment ago", 429);
  await env.DB.prepare("UPDATE profiles SET name = ?, data = ?, updated = ? WHERE id = ?")
    .bind(name, data, now, id).run();
  return reply({ ok: true });
}

async function leave(request, env, id) {
  const body = await readBody(request);
  if (!body) return err("Bad request");
  const row = await checkKey(env, id, body.key);
  if (!row) return err("Wrong key", 403);
  if (row.missing) return err("No such profile", 404);
  const now = Math.floor(Date.now() / 1000);
  await env.DB.prepare("UPDATE profiles SET name = '', data = ?, updated = ? WHERE id = ?")
    .bind(LEFT, now, id).run();
  return reply({ ok: true });
}

async function remove(request, env, id) {
  const body = await readBody(request);
  if (!body) return err("Bad request");
  const row = await checkKey(env, id, body.key);
  if (!row) return err("Wrong key", 403);
  if (!row.missing) await env.DB.prepare("DELETE FROM profiles WHERE id = ?").bind(id).run();
  return reply({ ok: true });
}

async function list(url, env) {
  const ids = [...new Set((url.searchParams.get("ids") || "").split(",").map(cleanCode).filter(Boolean))]
    .slice(0, MAX_IDS);
  if (!ids.length) return reply({ profiles: [] });
  const q = `SELECT id, name, data, updated FROM profiles WHERE id IN (${ids.map(() => "?").join(",")}) AND data != ?`;
  const { results } = await env.DB.prepare(q).bind(...ids, LEFT).all();
  return reply({
    profiles: results.map((r) => ({ id: r.id, name: r.name, data: JSON.parse(r.data), updated: r.updated })),
  });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const parts = url.pathname.split("/").filter(Boolean);
    try {
      if (parts[0] === "profiles" && parts.length === 1 && request.method === "GET") return await list(url, env);
      if (parts[0] === "profile") {
        if (parts.length === 1 && request.method === "POST") return await create(request, env);
        const id = cleanCode(parts[1]);
        if (parts.length === 3 && id && parts[2] === "leave" && request.method === "POST") return await leave(request, env, id);
        if (parts.length === 2 && id) {
          if (request.method === "PUT") return await update(request, env, id);
          if (request.method === "DELETE") return await remove(request, env, id);
        }
      }
      if (parts.length === 0) return new Response("Kotodama Nakama", { headers: { "content-type": "text/plain" } });
      return err("Not found", 404);
    } catch (e) {
      return err("Server error", 500);
    }
  },

  async scheduled(event, env) {
    const cutoff = Math.floor(Date.now() / 1000) - STALE_DAYS * 86400;
    await env.DB.prepare("DELETE FROM profiles WHERE updated < ?").bind(cutoff).run();
  },
};
