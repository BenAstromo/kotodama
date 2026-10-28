"""
history.py
Progress history: one snapshot per day, plus the past rebuilt from Anki's
own data, for the History tab.

Recorded snapshots
  Saved to user_files/history.json (kept when Anki updates the add-on),
  keyed by deck and by Anki day (the day starts at Anki's "next day starts
  at" hour). Taken automatically whenever an analysis runs (deck list /
  mini widget, opening or refreshing the main window, and once a day on the
  deck list even with the mini widget off), or manually via the History
  tab's "Take snapshot now" button. Each day keeps its latest values.

Rebuilt past
  Recomputed from the CURRENT analysis every time the History tab is built,
  so it always uses the current word lists (owner's decision: a list change
  recalculates history rather than showing a jump).
  - Rank / mature: replayed from the review log (revlog). A card counts as
    young from the first review that gives it a day interval, mature while
    its last interval is ≥ 21 days, young while relearning, new again after
    a reset. A note uses its most mature card, like card_state.
  - JLPT / frequency: every known word is dated by when its note entered
    your studies: the note's first review, or its creation date if it has
    never been reviewed. (Shared decks such as Kaishi keep the author's
    creation date, so the first review is the better signal.) Words marked
    found with no card count from the first day of history.
  Limits: deleted notes and past found/suspended overrides aren't known.

Merging: a recorded day replaces the rebuilt value when it was taken with
the same word lists and settings (JLPT/frequency) or the same
ignore-suspended setting (rank/mature); otherwise the rebuilt value is used.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import os
import time

from aqt import mw

from . import card_state
from . import freq_data
from .jlpt_data import LEVELS
from .overrides import keep_unreadable

_HERE = os.path.dirname(os.path.abspath(__file__))
_PATH = os.path.join(_HERE, "user_files", "history.json")

RANK_KEYS = ["rank", "mature"]
JLPT_KEYS = list(LEVELS) + ["jlpt"]
FREQ_KEYS = [f"f{n}" for n in freq_data.TIERS]
KG_KEYS = ["kanji", "grammar"]          # known kanji / grammar points on the level lists (2026-10-15)
ALL_KEYS = RANK_KEYS + JLPT_KEYS + FREQ_KEYS + KG_KEYS


# ── Anki days ─────────────────────────────────────────────────────────────────

def _rollover_hour() -> int:
    try:
        return int(mw.col.get_config("rollover", 4))
    except Exception:
        return 4


def day_of(ts: float, rollover: int = None) -> datetime.date:
    """The Anki day a timestamp (seconds) belongs to."""
    if rollover is None:
        rollover = _rollover_hour()
    return (datetime.datetime.fromtimestamp(ts)
            - datetime.timedelta(hours=rollover)).date()


def today() -> datetime.date:
    return day_of(time.time())


# ── storage ───────────────────────────────────────────────────────────────────

def _load() -> dict:
    try:
        with open(_PATH, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and isinstance(data.get("decks"), dict):
            return data
        keep_unreadable(_PATH)
    except FileNotFoundError:
        pass
    except Exception:
        keep_unreadable(_PATH)
    return {"version": 1, "decks": {}}


def _save(data: dict):
    try:
        os.makedirs(os.path.dirname(_PATH), exist_ok=True)
        tmp = _PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1, sort_keys=True)
        os.replace(tmp, _PATH)
    except Exception:
        pass


def recorded_days(deck_name: str) -> dict:
    """{"YYYY-MM-DD": snapshot} recorded for this deck."""
    return _load()["decks"].get(deck_name, {}).get("days", {})


def signature(lists: dict, field_mappings: list, ignore_suspended: bool) -> str:
    """Fingerprint of everything the JLPT/frequency counts depend on except
    the deck's contents: the word lists, the frequency list, field mappings
    and the ignore-suspended setting."""
    h = hashlib.sha1()
    for lvl in LEVELS:
        h.update(lvl.encode())
        for d, r in sorted(lists.get(lvl, [])):
            h.update(f"{d}\t{r}\n".encode("utf-8"))
    h.update(f"freq:{len(freq_data.load())}:{freq_data.LIST_VERSION}".encode())
    h.update(json.dumps(field_mappings, sort_keys=True, ensure_ascii=False).encode("utf-8"))
    h.update(f"susp:{bool(ignore_suspended)}".encode())
    h.update(b"seen-only:1")        # new (never studied) cards stopped counting, 2026-10-10
    h.update(b"same-kanji:1")       # other kanji = other word (会う ↛ 遭う), 2026-10-14
    return h.hexdigest()[:16]


# ── kanji / grammar counts ──────────────────────────────────────────────────

def _kg_listed(res: dict, kind: str) -> set:
    """Kanji / grammar ids on the level lists, minus the ones the user
    suspended: what the All Kanji / All Grammar bars count."""
    from .overrides import Overrides, KANJI_PATH, GRAMMAR_PATH
    try:
        sus = {k.split("\t", 1)[0]
               for k in Overrides(KANJI_PATH if kind == "kanji" else GRAMMAR_PATH).suspended}
    except Exception:
        sus = set()
    return {x for lvl in LEVELS for x in res.get("levels", {}).get(lvl, []) if x not in sus}


def kg_counts(results: dict) -> dict:
    """{"kanji": known, "grammar": known} for the parts that were analysed."""
    out = {}
    for kind in KG_KEYS:
        res = results.get(kind)
        if res:
            out[kind] = len(set(res.get("known", ())) & _kg_listed(res, kind))
    return out


def kg_signature(results: dict) -> str:
    """Fingerprint of what the kanji / grammar counts depend on besides the
    cards: where they're read from and the level lists."""
    h = hashlib.sha1()
    for kind in KG_KEYS:
        res = results.get(kind) or {}
        h.update(json.dumps(res.get("source"), sort_keys=True, ensure_ascii=False, default=str).encode("utf-8"))
        for lvl in LEVELS:
            h.update(f"{kind}{lvl}:{len(res.get('levels', {}).get(lvl, []))}".encode())
    return h.hexdigest()[:16]


# ── snapshots ─────────────────────────────────────────────────────────────────

def snapshot_values(results: dict, deck_name: str, ignore_suspended: bool) -> dict:
    # rank_v 2: the rank includes words marked found (2026-10-10); older
    # snapshots' rank (cards only) isn't reused — the rebuilt value is.
    # rank_v 3: marked English loanwords join the rank on a schedule
    # (2026-10-20); older snapshots' rank isn't reused — the rebuilt one is.
    # rank_v 4: learning cards count too (2026-10-21), same again.
    vals = {"rank": card_state.rank_count(deck_name, ignore_suspended, real=True),
            "rank_v": 4}
    maturity = results.get("maturity")
    if maturity is None:
        maturity = card_state.note_maturity(deck_name, ignore_suspended)
    # Real notes only (parsed sentence words share their note's maturity).
    vals["mature"] = sum(1 for n, s in maturity.items()
                         if s == card_state.MATURE and n < card_state.PSEUDO_BASE)
    for lvl in LEVELS:
        vals[lvl] = len(results.get(lvl, {}).get("known_words", []))
    vals["jlpt"] = sum(vals[lvl] for lvl in LEVELS)
    freq = results.get("frequency") or {}
    if freq.get("available"):
        for n, known in freq["tiers"]:
            vals[f"f{n}"] = known
    kg = kg_counts(results)
    if kg:
        vals.update(kg)
        vals["kg_sig"] = kg_signature(results)
    return vals


_last_recorded: dict = {}   # deck → day string, so the deck-list check is cheap


def record(results: dict, deck_name: str, lists: dict, field_mappings: list,
           ignore_suspended: bool, manual: bool = False) -> dict | None:
    """Save today's snapshot (replacing an earlier one from today). Returns
    the snapshot, or None if there was nothing to record."""
    if not deck_name or not results:
        return None
    try:
        vals = snapshot_values(results, deck_name, ignore_suspended)
    except Exception:
        return None
    day = today().isoformat()
    snap = dict(vals)
    snap["sig"] = signature(lists, field_mappings, ignore_suspended)
    snap["ignore_suspended"] = bool(ignore_suspended)
    snap["t"] = int(time.time())
    snap["src"] = "manual" if manual else "auto"

    data = _load()
    days = data["decks"].setdefault(deck_name, {}).setdefault("days", {})
    old = days.get(day)
    if old is not None and "kg_sig" in old and "kg_sig" not in snap:
        # the deck-list snapshot doesn't analyse kanji / grammar: keep
        # today's values from the main window
        for k in KG_KEYS + ["kg_sig"]:
            if k in old:
                snap[k] = old[k]
    unchanged = (old is not None
                 and all(old.get(k) == snap.get(k) for k in ALL_KEYS + ["sig", "ignore_suspended", "kg_sig"]))
    if unchanged and not manual:
        _last_recorded[deck_name] = day
        return old
    days[day] = snap
    _save(data)
    _last_recorded[deck_name] = day
    return snap


def record_auto(results: dict, cfg: dict, lists: dict = None):
    """Automatic snapshot from an analysis run with the saved config."""
    try:
        if lists is None:
            from . import jlpt_data
            lists = jlpt_data.build_lists(cfg.get("lists", {}))
        record(results, cfg.get("deck_name", ""), lists,
               cfg.get("field_mappings", []),
               bool(cfg.get("ignore_suspended_cards", False)))
    except Exception:
        pass


def recorded_today(deck_name: str) -> bool:
    day = today().isoformat()
    if _last_recorded.get(deck_name) == day:
        return True
    if day in recorded_days(deck_name):
        _last_recorded[deck_name] = day
        return True
    return False


# ── rebuilt past ──────────────────────────────────────────────────────────────

def rebuild(results: dict, deck_name: str, ignore_suspended: bool) -> dict:
    """Daily values from the first day of study to today, from the review
    log and note dates. Returns {"days": [date, …], "values": {key: [int, …]},
    "gained": {key: [(day index, nid, item), …]}}: what was added on which
    day (item = the word's frequency rank, the kanji, the grammar id, or
    None), for the clickable "+N this week" (gained_nids)."""
    from anki.utils import ids2str

    rollover = _rollover_hour()
    end = today()
    cids = mw.col.find_cards(card_state.deck_search(deck_name, ignore_suspended))
    card_nid: dict[int, int] = {}
    if cids:
        for cid, nid in mw.col.db.all(f"select id, nid from cards where id in {ids2str(cids)}"):
            card_nid[cid] = nid
    revlog = mw.col.db.all(
        f"select cid, id, type, ivl from revlog where cid in {ids2str(list(card_nid))} "
        f"order by id") if card_nid else []

    # When each note entered your studies: first review, else creation.
    first_review: dict[int, datetime.date] = {}
    for cid, rid, _t, _i in revlog:
        nid = card_nid[cid]
        if nid not in first_review:
            first_review[nid] = day_of(rid / 1000, rollover)

    def note_day(nid) -> datetime.date:
        nid = card_state.real_nid(nid)   # a parsed sentence word → its note
        d = first_review.get(nid)
        if d is None:
            d = day_of(nid / 1000, rollover)
        return min(d, end)

    # Marked English loanwords the counts include (card_state.hold_back_loans
    # left only these): each joins on the day the learned cards reached it,
    # as for the rank, not from the first day (2026-10-27). key → its place
    # in the order they join.
    fkeys = card_state._found_keys(results)
    loan_order = {k: i for i, (_rk, _r, k) in enumerate(sorted(
        (rk, repr(k), k) for k, (is_loan, rk) in fkeys.items() if is_loan))}
    loan_incs: list[tuple[int, str, object]] = []      # (place, key, item)

    # Dated items: (day, key, nid, item) increments for the cumulative
    # JLPT/freq counts.
    increments: list[tuple[datetime.date | None, str, int | None, object]] = []
    for lvl in LEVELS:
        for _d, _r, nid in results.get(lvl, {}).get("known_words", []):
            if nid is None:
                k = card_state.found_key(_d, _r)
                if k in loan_order:
                    loan_incs += [(loan_order[k], lvl, None), (loan_order[k], "jlpt", None)]
                    continue
            day = note_day(nid) if nid else None   # None = marked found
            increments.append((day, lvl, nid, None))
            increments.append((day, "jlpt", nid, None))
    freq = results.get("frequency") or {}
    if freq.get("available"):
        dated_ranks = []
        for rank, nids in freq.get("known_nids", {}).items():
            first = min(nids, key=note_day)
            dated_ranks.append((rank, note_day(first), first))
        # Marked found with no card: from the first day, like JLPT words.
        for rank in freq.get("found_ranks", ()):
            if ("row", rank) in loan_order:
                loan_incs += [(loan_order[("row", rank)], f"f{n}", rank)
                              for n in freq_data.TIERS if rank < n]
            else:
                dated_ranks.append((rank, None, None))
        for rank, day, nid in dated_ranks:
            for n in freq_data.TIERS:
                if rank < n:
                    increments.append((day, f"f{n}", nid, rank))

    # Kanji / grammar: dated by the earliest note in your studies that has
    # them in a studied card; marked found = from the first day.
    kg_keys = []
    for kind in KG_KEYS:
        res = results.get(kind)
        if not res:
            continue
        kg_keys.append(kind)
        listed = _kg_listed(res, kind)
        for x in res.get("known", ()):
            if x not in listed:
                continue
            nids = [n for _t, st, n in res.get("stats", {}).get(x, {}).get("words", ())
                    if st >= card_state.LEARNING]
            first = min(nids, key=note_day) if nids else None
            increments.append((note_day(first) if nids else None, kind, first, x))

    # Card-state changes per day, replayed from the revlog.
    events: dict[datetime.date, list[tuple[int, int]]] = {}
    graduated: dict[int, bool] = {}
    for cid, rid, rtype, ivl in revlog:
        if ivl > 0:
            state = card_state.MATURE if ivl >= card_state.MATURE_IVL else card_state.YOUNG
            graduated[cid] = True
        elif ivl < 0:
            # A learning step (seconds); relearning counts as young.
            state = card_state.YOUNG if graduated.get(cid) else card_state.LEARNING
        elif rtype == 4:
            # Manual entry with no interval = reset to new ("Forget").
            state = card_state.NEW
            graduated[cid] = False
        elif rtype in (0, 1, 2):
            # An answer logged with no interval: still studied.
            state = card_state.YOUNG if graduated.get(cid) else card_state.LEARNING
        else:
            continue
        events.setdefault(day_of(rid / 1000, rollover), []).append((cid, state))

    dated = [inc[0] for inc in increments if inc[0] is not None]
    start_candidates = dated + list(events)
    start = min(start_candidates) if start_candidates else end
    start = min(start, end)
    n_days = (end - start).days + 1
    days = [start + datetime.timedelta(days=i) for i in range(n_days)]

    keys = RANK_KEYS + JLPT_KEYS + (FREQ_KEYS if freq.get("available") else []) + kg_keys
    values = {k: [0] * n_days for k in keys}
    adds: dict[str, list[int]] = {k: [0] * n_days for k in values if k not in RANK_KEYS}
    gained: dict[str, list] = {k: [] for k in values}
    for day, key, nid, item in increments:
        if key in adds:
            adds[key][0 if day is None else (day - start).days] += 1
            if day is not None:
                gained[key].append(((day - start).days, nid, item))
    for key, arr in adds.items():
        running = 0
        for i, a in enumerate(arr):
            running += a
            values[key][i] = running

    card_st: dict[int, int] = {}
    note_cards: dict[int, list[int]] = {}
    for cid, nid in card_nid.items():
        note_cards.setdefault(nid, []).append(cid)
    note_st: dict[int, int] = {}
    # Words marked found count toward the rank from the first day, as they
    # do for the JLPT / frequency lines (owner 2026-10-10); marked English
    # loanwords on their schedule, by that day's learned cards (2026-10-20).
    extra = card_state.found_parts(results)
    cards = 0
    mature = 0
    joined: list[int] = []             # loanwords counted on each day
    for i, day in enumerate(days):
        touched = set()
        for cid, state in events.get(day, ()):
            card_st[cid] = state
            touched.add(card_nid[cid])
        for nid in touched:
            new = max(card_st.get(c, card_state.NEW) for c in note_cards[nid])
            old = note_st.get(nid, card_state.NEW)
            if new == old:
                continue
            # Studied cards count, learning included (owner 2026-10-21).
            cards += (new >= card_state.LEARNING) - (old >= card_state.LEARNING)
            if new >= card_state.LEARNING > old:
                gained["rank"].append((i, nid, None))
            mature += (new == card_state.MATURE) - (old == card_state.MATURE)
            note_st[nid] = new
        values["rank"][i] = card_state.rank_split(cards, extra)[0]
        values["mature"][i] = mature
        joined.append(card_state.loans_counted(cards, extra["loans"]))

    # The counted loanwords on each day: those whose place is below that
    # day's count (it drops if cards are reset). All of them today: today's
    # count is the real one, the replayed cards can fall a little short.
    if loan_incs:
        import bisect
        places: dict[str, list[int]] = {}
        for place, key, _item in loan_incs:
            if key in values and key not in RANK_KEYS:
                places.setdefault(key, []).append(place)
        for key, ps in places.items():
            ps.sort()
            for i in range(n_days - 1):
                values[key][i] += bisect.bisect_left(ps, joined[i])
            values[key][-1] += len(ps)

    return {"days": days, "values": values, "gained": gained}


def build_series(results: dict, deck_name: str, lists: dict,
                 field_mappings: list, ignore_suspended: bool) -> dict:
    """Rebuilt past merged with recorded snapshots. Returns
    {"days": [date…], "values": {key: [int…]}, "recorded": [bool…]}."""
    data = rebuild(results, deck_name, ignore_suspended)
    days, values = data["days"], data["values"]
    # Gains ("+N this week", the summary table, Nakama) come from the rebuilt
    # series, where words marked found count from the first day: marking or
    # unmarking (the English-loanword button) is never a gain or a drop
    # (owner 2026-10-20: "-2,590 this week" after unmarking loanwords). The
    # chart keeps the recorded snapshots.
    data["gains"] = {k: list(v) for k, v in values.items()}
    recorded = [False] * len(days)
    sig = signature(lists, field_mappings, ignore_suspended)
    kg_sig = kg_signature(results)
    index = {d.isoformat(): i for i, d in enumerate(days)}
    for day, snap in recorded_days(deck_name).items():
        i = index.get(day)
        if i is None:
            continue
        used = False
        if snap.get("ignore_suspended") == bool(ignore_suspended):
            for k in RANK_KEYS:
                if k == "rank" and snap.get("rank_v") != 4:
                    continue              # an older definition of the rank
                if k in snap:
                    values[k][i] = snap[k]
                    used = True
        if snap.get("sig") == sig:
            for k in JLPT_KEYS + FREQ_KEYS:
                if k in snap and k in values:
                    values[k][i] = snap[k]
                    used = True
        if snap.get("kg_sig") is not None and snap.get("kg_sig") == kg_sig:
            for k in KG_KEYS:
                if k in snap and k in values:
                    values[k][i] = snap[k]
                    used = True
        recorded[i] = used
    data["recorded"] = recorded
    return data


def _gain_values(series: dict, key: str):
    """The series used for gains: the rebuilt one (marks count from day
    one), else the merged values (an older cached series)."""
    return (series.get("gains") or series.get("values") or {}).get(key)


def best_week(series: dict, key: str) -> int | None:
    """The largest gain over any 7 days in the series."""
    vals = _gain_values(series, key)
    if not vals:
        return None
    # vs day one, not 0: marked-found words count from the first day and
    # aren't a gain
    return max(vals[i] - vals[max(i - 7, 0)] for i in range(len(vals)))


def since_start(series: dict, key: str) -> int | None:
    """Gain since the first day of the history (marked-found words, which
    count from day one, aren't a gain)."""
    vals = _gain_values(series, key)
    return vals[-1] - vals[0] if vals else None


def gained_nids(series: dict, key: str, days_back: int, keep=None) -> list[int]:
    """The notes behind delta(): what started counting for `key` in the last
    `days_back` days (days_back=0: today), newest first. keep(item) filters
    by the frequency rank / kanji / grammar id. Marks never show (they
    count from day one), and a drop (a card reset to new) isn't listed."""
    days = (series or {}).get("days") or []
    first = len(days) - days_back if days_back else len(days) - 1
    out, seen = [], set()
    for i, nid, item in sorted(((series or {}).get("gained") or {}).get(key, ()),
                               key=lambda g: -g[0]):
        if i < first:
            break
        if nid is None or (keep is not None and not keep(item)):
            continue
        nid = card_state.real_nid(nid)          # a parsed sentence word → its note
        if nid not in seen:
            seen.add(nid)
            out.append(nid)
    return out


def gain_parts(series: dict, key: str, days_back: int) -> tuple[int, int, int] | None:
    """(change, from cards, marked loanwords that joined) behind delta(), or
    None without data (owner 2026-10-28: "+35 today" but 30 cards in the
    Browser). Each card's gain is one entry in "gained"; a joining loanword
    raises the values with no entry, so a gain above the cards is those (a
    gain below them: cards reset to new)."""
    d = delta(series, key, days_back)
    if d is None:
        return None
    days = (series or {}).get("days") or []
    first = len(days) - days_back
    cards = sum(1 for i, nid, _x in ((series or {}).get("gained") or {}).get(key, ())
                if i >= first and nid is not None)
    return d, cards, max(0, d - cards)


def delta(series: dict, key: str, days_back: int) -> int | None:
    """Change in `key` over the last `days_back` days (None if no data).
    Marks never count as change (the rebuilt series, _gain_values)."""
    vals = _gain_values(series, key)
    if not vals:
        return None
    i = len(vals) - 1 - days_back
    return vals[-1] - (vals[i] if i >= 0 else 0)


# ── automatic daily snapshot from the deck list ───────────────────────────────

def _on_deck_browser_will_render_content(deck_browser, content):
    """Make sure there's a snapshot for today even when the mini widget is
    off (when it's on, its own analysis already recorded one)."""
    try:
        from . import _cfg
        cfg = _cfg()
        deck = cfg.get("deck_name", "")
        if not deck or not cfg.get("field_mappings") or recorded_today(deck):
            return
        from . import mini_widget, card_state
        # Current results, or None while a background recount runs (that
        # recount records today's snapshot itself).
        results = mini_widget.cached_results()
        if results is not None and card_state.ANALYSIS_LOCK.acquire(blocking=False):
            try:                          # never wait on the main thread
                record_auto(results, cfg)
            finally:
                card_state.ANALYSIS_LOCK.release()
    except Exception:
        pass


def setup():
    from aqt import gui_hooks
    gui_hooks.deck_browser_will_render_content.append(
        _on_deck_browser_will_render_content)
