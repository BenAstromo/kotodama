"""
nakama.py
Nakama 仲間 (owner 2026-10-17): a friends-only board. Each member has a
profile = a small snapshot of their Kotodama bars (rank, JLPT vocab per
level, top-20k frequency words, JLPT kanji and grammar), shown in the
Nakama tab as a card in the share image's style, with your own position
marked on every bar.

  - Opt-in: nothing is sent until you press Join. Joining creates your
    profile on the Nakama server (server/worker.js, a Cloudflare Worker)
    and gives you a friend code; the server's secret key for your profile
    stays in user_files/nakama.json. Anyone you give your code to can see
    your card; there is no search or global list.
  - What is sent: your name and the snapshot below — numbers only, no
    cards, words or deck names.
  - Updates: your snapshot is refreshed after every count (the add-on
    window and the deck-list widget) and uploaded after Anki syncs, or when
    the Nakama tab opens, only if it changed. Friends' cards are fetched
    when the tab opens.
  - Leave erases your name and card from the server but keeps your code
    reserved for you (server: POST /profile/<id>/leave); joining again
    reuses it ("parked" in the local state). Codes unused for 400 days are
    freed by the server.
  - Your code, key, name and friends list are also kept in the collection
    (config "kotodama_nakama", synced by AnkiWeb; owner 2026-10-20), so a
    reinstall, a new computer or the AnkiWeb version keeps your membership.

Network calls run in Anki's background thread (mw.taskman) and never block
or break anything: a failure only shows in the tab.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import os
import time

from aqt import mw

from . import card_state
from .jlpt_data import LEVELS

SERVER = os.environ.get("KOTODAMA_NAKAMA_URL", "https://kotodama-nakama.kotodama-anki.workers.dev").rstrip("/")
SNAPSHOT_VERSION = 1
TIMEOUT = 12

_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "user_files", "nakama.json")
COL_KEY = "kotodama_nakama"
_state: dict | None = None


# ── local state ──────────────────────────────────────────────────────────────

def state() -> dict:
    """{"id", "key", "name", "friends": [codes], "cache": {code: profile},
    "mine": snapshot, "sent": signature of the last upload,
    "parked": {"id", "key"} after Leave (rejoining reuses the code)}"""
    global _state
    if _state is None:
        try:
            with open(_PATH, encoding="utf-8") as f:
                _state = json.load(f)
            if not isinstance(_state, dict):
                raise ValueError("not an object")
        except FileNotFoundError:
            _state = {}
        except Exception:
            from .overrides import keep_unreadable
            keep_unreadable(_PATH)
            _state = {}
        _state.setdefault("friends", [])
        _state.setdefault("cache", {})
        adopt_collection()
    return _state


def save():
    s = state()
    try:
        os.makedirs(os.path.dirname(_PATH), exist_ok=True)
        tmp = _PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(s, f, ensure_ascii=False)
        os.replace(tmp, _PATH)
    except Exception:
        pass
    _mirror(s)


# ── the collection's copy (survives reinstalls, syncs to other computers) ────

def _col():
    try:
        return mw.col
    except Exception:
        return None


def _identity(s: dict) -> dict | None:
    """What the collection keeps: code, key, whether you're in, name, friends."""
    if s.get("id") and s.get("key"):
        ident, key, active = s["id"], s["key"], True
    elif (s.get("parked") or {}).get("id"):
        ident, key, active = s["parked"]["id"], s["parked"].get("key"), False
    else:
        return None
    return {"id": ident, "key": key, "active": active, "name": s.get("name") or "",
            "friends": list(s.get("friends") or [])}


def _mirror(s: dict):
    """Keep the collection's copy current; written only when it changed."""
    col = _col()
    want = _identity(s)
    if col is None or want is None:
        return
    try:
        if col.get_config(COL_KEY, None) != want:
            col.set_config(COL_KEY, want)
    except Exception:
        pass


def adopt_collection() -> bool:
    """No membership here, but the collection has one (a reinstall, another
    computer after an AnkiWeb sync, the AnkiWeb version of the add-on):
    take it over, joined or left (parked) as it was, friends merged."""
    s = _state
    if s is None or s.get("id") or (s.get("parked") or {}).get("id"):
        return False
    col = _col()
    if col is None:
        return False
    try:
        v = col.get_config(COL_KEY, None)
    except Exception:
        return False
    if not isinstance(v, dict) or not clean_code(v.get("id") or "") or not v.get("key"):
        return False
    if v.get("active"):
        s["id"], s["key"] = v["id"], v["key"]
    else:
        s["parked"] = {"id": v["id"], "key": v["key"]}
    if v.get("name") and not s.get("name"):
        s["name"] = v["name"]
    s["friends"] = list(dict.fromkeys(list(s.get("friends") or []) +
                                      [c for c in v.get("friends") or [] if clean_code(c)]))
    save()
    return True


def parked_code() -> str | None:
    """The code you get back if you join again, after Leave."""
    return (state().get("parked") or {}).get("id") or None


def joined() -> bool:
    s = state()
    return bool(s.get("id") and s.get("key"))


def clean_code(text: str) -> str | None:
    """A friend code as typed (any case, with or without the dash) → its
    8 characters, or None."""
    c = "".join(ch for ch in (text or "").upper() if ch.isalnum())
    ok = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"
    return c if len(c) == 8 and all(ch in ok for ch in c) else None


def show_code(code: str) -> str:
    return f"{code[:4]}-{code[4:]}" if code else ""


# ── snapshot ─────────────────────────────────────────────────────────────────

def _gain(series: dict | None, days: int) -> int | None:
    # the rebuilt series: marking / unmarking words is never a gain or a drop
    vals = ((series or {}).get("gains") or (series or {}).get("values") or {}).get("rank")
    if not vals:
        return None
    return vals[-1] - vals[max(0, len(vals) - 1 - days)]


def _word_parts(results: dict, deck_name: str, ignore_suspended: bool) -> dict:
    jlpt = {}
    for lvl in LEVELS:
        d = results.get(lvl) or {}
        k = len(d.get("known_words", ()))
        jlpt[lvl] = [k, k + len(d.get("missing_words", ()))]
    freq = results.get("frequency") or {}
    top = 20_000
    fk = dict(freq.get("tiers", [])).get(top, 0)
    fn = (freq.get("tier_totals") or {}).get(top, top)
    # Marked English loanwords: how many count toward the rank so far (they
    # join on a schedule, card_state) and how many are marked (2026-10-20).
    extra = card_state.found_parts(results)
    rank = card_state.rank_count(deck_name, ignore_suspended, real=True)
    _cards, loans = card_state.cards_for_rank(rank, extra)
    hand = extra["hand"]
    from . import loyalty
    return {"rank": rank, "loan_marked": len(extra["loans"]),
            "loyal": loyalty.months_with_kotodama(),        # time with Kotodama (real, never the preview)
            "sun": loyalty.sun_reached(),                   # Amaterasu reached once (Sun Diamond)
            "found": hand, "found_loan": loans,     # marked by hand / English loanwords counted
            "goal": _goal(),                        # "N3 2026-12-06" or None (share pop-up's checkbox)
            "jlpt": jlpt, "freq": [fk, fn]}


def _goal():
    """The JLPT goal for the Nakama card (goal.py), as "N3 2026-12-06";
    None without one, after its test, or with "Show JLPT goal" unticked."""
    try:
        from . import goal
        g = goal.share_goal()
        return f"{g['level']} {g['date'].isoformat()}" if g else None
    except Exception:
        return None


def store_full(results: dict, deck_name: str, ignore_suspended: bool,
               kanji_overrides=None, grammar_overrides=None):
    """After a full count (the add-on window / Refresh): everything. Kept
    locally even before you join (Join sends it; nothing is sent before)."""
    from . import kanji_data, grammar_data
    snap = _word_parts(results, deck_name, ignore_suspended)
    for kind, mod, ov in (("kanji", kanji_data, kanji_overrides),
                          ("grammar", grammar_data, grammar_overrides)):
        res = results.get(kind)
        if res:
            sus = {k.split("\t", 1)[0] for k in (ov.suspended if ov else ())}
            c = mod.level_counts(res, sus)
            snap[kind] = {lvl: list(c[lvl]) for lvl in LEVELS + ["All"]}
    series = results.get("history_series")
    snap["week"], snap["month"] = _gain(series, 7), _gain(series, 30)
    _store(snap)


def store_partial(results: dict, deck_name: str, ignore_suspended: bool):
    """After the deck-list widget's recount: the word parts only (it
    doesn't count kanji, grammar or history)."""
    if not joined():
        return
    _store(_word_parts(results, deck_name, ignore_suspended))


def _store(parts: dict):
    s = state()
    snap = dict(s.get("mine") or {})
    snap.update(parts)
    snap["v"] = SNAPSHOT_VERSION
    s["mine"] = snap
    save()


def _signature(name: str, snap: dict) -> str:
    return hashlib.sha1(json.dumps([name, snap], sort_keys=True).encode()).hexdigest()


# ── network ──────────────────────────────────────────────────────────────────

class NakamaError(Exception):
    pass


def _request(method: str, path: str, body: dict | None = None) -> dict:
    import ssl
    import urllib.error
    import urllib.request
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(SERVER + path, data=data, method=method, headers={
        "content-type": "application/json", "user-agent": "Kotodama-Anki"})
    ctx = None
    if SERVER.startswith("https"):
        try:
            import certifi
            ctx = ssl.create_default_context(cafile=certifi.where())
        except Exception:
            ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=ctx) as r:
            return json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        try:
            msg = json.loads(e.read().decode()).get("error")
        except Exception:
            msg = None
        raise NakamaError(msg or f"Server error ({e.code})") from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise NakamaError("Couldn't reach the Nakama server. Check your internet connection.") from None


def _in_background(work, done):
    """work() in Anki's background thread; done(result, error) on the main
    thread. Without mw.taskman (tests) it runs here."""
    def finished(fut):
        try:
            res = fut.result()
        except NakamaError as e:
            done(None, str(e))
            return
        except Exception as e:
            done(None, f"Something went wrong ({type(e).__name__})")
            return
        done(res, None)
    tm = getattr(mw, "taskman", None)
    if tm is None:
        class _F:
            def __init__(self, f): self.f = f
            def result(self): return self.f()
        finished(_F(work))
        return
    tm.run_in_background(work, finished)


def join(name: str, done):
    """Join: with your old code if you left before (rejoin = an update with
    its key), else a new profile; done(ok, error)."""
    s = state()
    snap = dict(s.get("mine") or {"v": SNAPSHOT_VERSION})
    parked = dict(s.get("parked") or {})

    def work():
        if parked.get("id") and parked.get("key"):
            try:
                _request("PUT", f"/profile/{parked['id']}", {"key": parked["key"], "name": name, "data": snap})
                return {"id": parked["id"], "key": parked["key"]}
            except NakamaError as e:
                if "No such profile" not in str(e) and "Wrong key" not in str(e):
                    raise           # a network problem: try again later, keep the code
                # freed by the server (unused 400 days / deleted): a new code
        return _request("POST", "/profile", {"name": name, "data": snap})

    def finished(res, error):
        if error:
            done(False, error)
            return
        s.pop("parked", None)
        s["id"], s["key"], s["name"] = res["id"], res["key"], name
        s["sent"] = _signature(name, snap)
        save()
        done(True, None)
    _in_background(work, finished)


def upload_if_changed(done=None):
    """Send your snapshot if it (or your name) changed since the last
    upload. done(sent, error) is optional."""
    s = state()
    if not joined() or not s.get("mine"):
        if done:
            done(False, None)
        return
    name = s.get("name") or "Nakama"
    snap = s["mine"]
    sig = _signature(name, snap)
    if sig == s.get("sent"):
        if done:
            done(False, None)
        return
    ident, key = s["id"], s["key"]

    def work():
        return _request("PUT", f"/profile/{ident}", {"key": key, "name": name, "data": snap})

    def finished(_res, error):
        if not error:
            s["sent"] = sig
            save()
        elif "moment ago" in error:
            error = None             # the server's once-a-minute limit: next time
        if done:
            done(not error, error)
    _in_background(work, finished)


def fetch_friends(done):
    """Friends' (and your own) profiles from the server into the cache;
    done(error). Codes the server doesn't know are marked missing."""
    s = state()
    codes = list(dict.fromkeys(s["friends"] + ([s["id"]] if s.get("id") else [])))
    if not codes:
        done(None)
        return

    def work():
        return _request("GET", "/profiles?ids=" + ",".join(codes))

    def finished(res, error):
        if error:
            done(error)
            return
        got = {p["id"]: p for p in res.get("profiles", [])}
        for c in codes:
            if c in got:
                s["cache"][c] = got[c]
            else:
                s["cache"].setdefault(c, {"id": c})["missing"] = True
        save()
        done(None)
    _in_background(work, finished)


def add_friend(code: str) -> bool:
    s = state()
    if code in s["friends"] or code == s.get("id"):
        return False
    s["friends"].append(code)
    save()
    return True


def remove_friend(code: str):
    s = state()
    s["friends"] = [c for c in s["friends"] if c != code]
    s["cache"].pop(code, None)
    save()


def leave(done):
    """Erase your name and card from the server but keep the code reserved
    (parked here, so joining again reuses it; friends list kept);
    done(ok, error). An older server without /leave deletes the profile."""
    s = state()
    if not joined():
        done(True, None)
        return
    ident, key = s["id"], s["key"]

    def work():
        try:
            _request("POST", f"/profile/{ident}/leave", {"key": key})
            return {"kept": True}
        except NakamaError as e:
            if "Not found" not in str(e):
                raise
        _request("DELETE", f"/profile/{ident}", {"key": key})
        return {"kept": False}

    def finished(res, error):
        if error:
            done(False, error)
            return
        for k in ("id", "key", "sent"):
            s.pop(k, None)
        if res.get("kept"):
            s["parked"] = {"id": ident, "key": key}
        s["cache"].pop(ident, None)
        save()
        done(True, None)
    _in_background(work, finished)


def synced_text(updated) -> str:
    """"synced 3 h ago" for a profile's server timestamp."""
    if not updated:
        return "not synced yet"
    secs = max(0, int(time.time() - updated))
    if secs < 90:
        return "synced just now"
    if secs < 3600:
        return f"synced {secs // 60} min ago"
    if secs < 86400:
        return f"synced {secs // 3600} h ago"
    days = secs // 86400
    if days < 60:
        return f"synced {days} day{'s' if days != 1 else ''} ago"
    return "synced " + datetime.date.fromtimestamp(updated).strftime("%b %Y")


# ── hooks ────────────────────────────────────────────────────────────────────

@card_state.hook_guard()
def _on_sync_did_finish(*_args):
    if _state is not None:
        adopt_collection()      # a new computer: the membership arrives with the first sync
    upload_if_changed()


def setup():
    from aqt import gui_hooks
    hook = getattr(gui_hooks, "sync_did_finish", None)
    if hook is not None:
        hook.append(_on_sync_did_finish)
