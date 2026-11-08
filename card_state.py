"""
card_state.py
Anki card scheduling state, shared by every deck scan:

  - deck_search: the search used to find the deck's notes. With the
    "ignore suspended cards" option, a note whose cards are all suspended
    drops out of every count (JLPT, frequency, rank). Never-studied (new)
    cards don't count either: a note counts once any card has been seen.
  - note_maturity: new / learning / young / mature per note, for the tile
    saturation. A note with several cards uses its most mature card.
  - rank_count: the Kotodama Japanese Rank counts every note with a studied
    card (learning, young or mature), like the JLPT bars and the goal
    (owner 2026-10-21). A card reset to new ("Forget") drops out.
"""

from __future__ import annotations

import functools
import traceback

from aqt import mw


def hook_guard(fallback=None):
    """Decorator for every Anki hook / signal callback the add-on registers
    (reviewer answers, state changes, the deck browser, webview messages):
    an error never reaches Anki, so it can't interrupt reviewing. The first
    error of each callback is printed (visible in anki-console.bat) instead
    of being swallowed silently. fallback(*args) gives a filter hook's
    pass-through value (the answer's ease, the webview's `handled`)."""
    def wrap(fn):
        reported = []

        @functools.wraps(fn)
        def inner(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except Exception:
                if not reported:
                    reported.append(True)
                    print(f"Kotodama: error in {fn.__name__} (ignored, reviews continue):")
                    traceback.print_exc()
                return fallback(*args, **kwargs) if fallback else None
        return inner
    return wrap

NEW, LEARNING, YOUNG, MATURE = 0, 1, 2, 3
STATE_NAMES = {NEW: "New", LEARNING: "Learning", YOUNG: "Young", MATURE: "Mature"}

# Anki's own definition of a mature card.
MATURE_IVL = 21

# Anki card.type values
_TYPE_LEARN, _TYPE_REVIEW, _TYPE_RELEARN = 1, 2, 3


# Words parsed from a sentence card (a note-type mapping with only a sentence
# field) get their own id per word: note id × 1000 + word index. Real note
# ids are millisecond timestamps (~1.7e12), far below PSEUDO_BASE.
PSEUDO_BASE = 10 ** 14


def pseudo_nid(nid: int, index: int) -> int:
    return nid * 1000 + min(index, 999)


def real_nid(nid):
    """The note behind an id (a parsed sentence word's id → its note)."""
    return nid // 1000 if nid is not None and nid >= PSEUDO_BASE else nid


def with_pseudo(maturity: dict, ids) -> dict:
    """Give parsed sentence words their note's maturity."""
    for i in ids:
        if i >= PSEUDO_BASE and i not in maturity:
            m = maturity.get(i // 1000)
            if m is not None:
                maturity[i] = m
    return maturity


def deck_query(deck_name: str) -> str:
    """'"deck:NAME"' with Anki's search specials in the name escaped: _ and *
    are wildcards (Core_2k would match Core 2k too) and a " ends the quote
    (the search fails). The :: of sub-decks needs no escaping."""
    name = (deck_name.replace("\\", "\\\\").replace('"', '\\"')
            .replace("*", "\\*").replace("_", "\\_"))
    return f'"deck:{name}"'


def deck_search(deck_name: str, ignore_suspended: bool = False,
                seen_only: bool = True) -> str:
    # Only cards you've studied at least once count (owner 2026-10-10: a
    # deck full of never-seen new cards filled the JLPT bars). A note counts
    # once any of its cards has been seen.
    q = deck_query(deck_name)
    if seen_only:
        q += " -is:new"
    if ignore_suspended:
        q += " -is:suspended"
    return q


# ── deck notes: one bulk read shared by every scan ────────────────────────────
# The word, kanji and grammar scans each read the deck's fields. One
# col.get_note per note cost ~1.5 s per scan on a 30k deck (speed report
# 2026-10-17); one SQL read of the notes table is ~15× faster, and the scans
# of one analysis share it. Kept until a note in the deck is added, removed
# or edited (count + sum of note mod times).

class DeckNote:
    """A note's type name and raw fields; `name in note` / `note[name]`
    like Anki's Note."""
    __slots__ = ("type_name", "_idx", "_vals")

    def __init__(self, type_name: str, idx: dict, vals: list):
        self.type_name, self._idx, self._vals = type_name, idx, vals

    def __contains__(self, name) -> bool:
        i = self._idx.get(name)
        return i is not None and i < len(self._vals)

    def __getitem__(self, name) -> str:
        return self._vals[self._idx[name]]


_notes_memo: dict = {}   # seen_only → {"key", "notes"}


def deck_notes(deck_name: str, seen_only: bool = True) -> dict[int, DeckNote]:
    """nid → DeckNote for the deck's notes with a seen card (deck_search
    without the suspended filter; callers that skip suspended notes
    intersect with their own find_notes). seen_only=False: never-studied
    notes too (the grammar grid's "in your deck, not learned yet")."""
    from anki.utils import ids2str
    if not deck_name:
        return {}
    nids = mw.col.find_notes(deck_search(deck_name, seen_only=seen_only))
    if not nids:
        return {}
    ids = ids2str(nids)
    count, mods = mw.col.db.first(f"select count(), sum(mod) from notes where id in {ids}") or (0, 0)
    key = (deck_name, count, mods, hash(tuple(sorted(nids))))
    memo = _notes_memo.setdefault(seen_only, {"key": None, "notes": {}})
    if memo["key"] == key:
        return memo["notes"]
    types: dict[int, tuple[str, dict]] = {}
    out: dict[int, DeckNote] = {}
    for nid, mid, flds in mw.col.db.all(f"select id, mid, flds from notes where id in {ids}"):
        t = types.get(mid)
        if t is None:
            nt = mw.col.models.get(mid) or {}
            fl = sorted(nt.get("flds", []), key=lambda f: f.get("ord", 0))
            t = types[mid] = (nt.get("name", ""), {f["name"]: i for i, f in enumerate(fl)})
        out[nid] = DeckNote(t[0], t[1], flds.split("\x1f"))
    memo["key"], memo["notes"] = key, out
    return out


# ── analysis off the main thread ──────────────────────────────────────────────
# A full analysis takes seconds on a big deck (30k notes: ~35 s the first
# time), so it runs in Anki's background thread (QueryOp) and Anki stays
# responsive. One analysis at a time: the parser's and scans' caches aren't
# built for two threads at once.

import threading
ANALYSIS_LOCK = threading.RLock()


def run_in_background(parent, work, done, label: str | None = None, quiet: bool = False):
    """work() off the main thread (under ANALYSIS_LOCK), then done(result)
    on the main thread. label: Anki's progress window with that text.
    quiet: an error is printed instead of shown (background refreshes the
    user didn't ask for). Without QueryOp (old Anki) it just runs here."""
    def op(_col):
        with ANALYSIS_LOCK:
            return work()
    try:
        from aqt.operations import QueryOp
    except ImportError:
        done(op(None))
        return
    q = QueryOp(parent=parent, op=op, success=done)
    if quiet:
        def failed(exc):
            print("Kotodama: background analysis failed:", repr(exc))
            traceback.print_exception(type(exc), exc, exc.__traceback__)
        q = q.failure(failed)
    if label:
        q = q.with_progress(label)
    q.run_in_background()


def card_state(ctype: int, ivl: int) -> int:
    if ctype == _TYPE_REVIEW:
        return MATURE if ivl >= MATURE_IVL else YOUNG
    if ctype == _TYPE_RELEARN:
        return YOUNG
    if ctype == _TYPE_LEARN:
        return LEARNING
    return NEW


def note_maturity(deck_name: str, ignore_suspended: bool = False) -> dict[int, int]:
    """nid → most mature state among the note's cards in the deck."""
    if not deck_name:
        return {}
    from anki.utils import ids2str
    cids = mw.col.find_cards(deck_search(deck_name, ignore_suspended))
    if not cids:
        return {}
    out: dict[int, int] = {}
    for nid, ctype, ivl in mw.col.db.all(
            f"select nid, type, ivl from cards where id in {ids2str(cids)}"):
        s = card_state(ctype, ivl)
        if s > out.get(nid, -1):
            out[nid] = s
    return out


# DEBUG (Overview's "Force Amaterasu" button): rank shown as exactly 20,000
# and every bar drawn full, in the add-on window and the main-screen widget.
# In memory only.
DEBUG_FULL = {"on": False}


def debug_count_all() -> bool:
    """DEBUG switch (Overview's "Count all notes" button, config key
    debug_rank_count_all): the rank counts every note, learned or not, so a
    test deck of 20,000 new cards can preview Amaterasu mode."""
    try:
        from . import _cfg
        return bool(_cfg().get("debug_rank_count_all", False))
    except Exception:
        return False


# Words marked found count toward the rank, belts and Amaterasu too (owner
# 2026-10-10; reverses "the rank counts only learned cards"). How many there
# are needs the full analysis, so each analysis stores it here (per deck) and
# in user_files/found_count.json, so the rank includes them from startup
# (rank-up toasts, the review seal) before the add-on window is opened.
import json as _json
import os as _os
_FOUND_PATH = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)),
                            "user_files", "found_count.json")
_found_cache: dict | None = None


def _found_rank(d: str, r: str):
    """A marked JLPT word's frequency row (1-based), for counting each word
    once; a katakana word + する uses its stem's row (チェックする = チェック)."""
    from . import freq_data, jlpt_data
    rk = freq_data.word_rank(d, r, jlpt_data.alt_forms(d, r))
    if rk is None:
        stem = jlpt_data.suru_stem(d, r)
        if stem is not None:
            rk = freq_data.word_rank(*stem)
    return rk


def found_key(d: str, r: str):
    """The word a mark with no card is (one word on both lists counts once):
    its frequency row when it has one (JLPT おまえ = frequency お前), else
    its spelling."""
    from . import freq_data
    rk = _found_rank(d, r)
    return ("row", rk - 1) if rk is not None else freq_data._override_key(d, r)


def found_words_in(results: dict) -> int:
    """Distinct words marked found with no card behind them, over the JLPT
    lists and the frequency list (a word found on both counts once).
    Kanji and grammar marks aren't words, so they don't count."""
    from . import freq_data
    from .jlpt_data import LEVELS
    # A word is identified by its frequency row when it has one (so the JLPT
    # おまえ and the frequency お前 are one word), else by its spelling.
    keys = set()
    for lvl in LEVELS:
        for d, r, nid in results.get(lvl, {}).get("known_words", []):
            if nid is None:
                rk = _found_rank(d, r)
                keys.add(("row", rk - 1) if rk is not None else freq_data._override_key(d, r))
    freq = results.get("frequency") or {}
    for rank in freq.get("found_ranks", ()):
        keys.add(("row", rank))
    return len(keys)


def found_split(results: dict) -> tuple[int, int]:
    """found_words_in split into (English loanwords, the rest), for the
    Nakama card (owner 2026-10-18: everyone marks the loanwords with the
    one button, so the hand-marked count is shown without them). A word
    counts as a loanword by the same test the button uses, however it was
    marked."""
    from . import freq_data, jlpt_data
    from .jlpt_data import LEVELS
    keys: dict = {}                       # key → is a loanword
    for lvl in LEVELS:
        for d, r, nid in results.get(lvl, {}).get("known_words", []):
            if nid is None:
                rk = _found_rank(d, r)
                key = ("row", rk - 1) if rk is not None else freq_data._override_key(d, r)
                keys[key] = keys.get(key, False) or jlpt_data.is_english_loanword(d, r)
    freq = results.get("frequency") or {}
    found = freq.get("found_ranks", ())
    if found:
        by_rank = {e[0] - 1: e for e in freq.get("entries", ())}
        for rank in found:
            e = by_rank.get(rank)
            loan = bool(e) and freq_data.is_english_loanword(e[1], e[2])
            keys[("row", rank)] = keys.get(("row", rank), False) or loan
    loans = sum(1 for v in keys.values() if v)
    return loans, len(keys) - loans


# ── English loanwords join the rank gradually (owner 2026-10-20) ──────────────
# Marked English loanwords count only as your vocabulary reaches them, on
# the rank and (since 2026-10-27, hold_back_loans) on every bar: the k-th marked loanword (by frequency rank r, k = 0, 1, …) counts
# once your learned cards reach r − k ("rank 8,000 minus the loanwords
# already counted"). Early on the rank isn't inflated by ~2,500 words at
# once; with every loanword marked, the last one joins at 17,464 cards,
# exactly where marking them all at once would reach 20,000. Marking stays a
# choice (not everyone thinks loanwords are learned on sight, not everyone
# speaks English); words marked by hand that aren't loanwords count at once,
# as do loanwords middle-clicked to count now (overrides "counted").
_LEVEL_SIZE = {"N5": 800, "N4": 1500, "N3": 3900, "N2": 6000, "N1": 13800}


def found_parts(results: dict) -> dict:
    """{"hand": words marked found that aren't English loanwords, "loans":
    sorted frequency ranks of the marked English loanwords (a JLPT-only one
    uses its level's size)} — the distinct words of found_words_in. Kept in
    results from the first call, so it still sees every marked loanword
    after hold_back_loans."""
    if results.get("found_parts") is not None:
        return results["found_parts"]
    keys = _found_keys(results)
    loans = sorted(rk for is_loan, rk in keys.values() if is_loan)
    results["found_parts"] = {"hand": len(keys) - len(loans), "loans": loans}
    return results["found_parts"]


def is_loan(d: str, r: str) -> bool:
    """An English loanword by either list's test. The two lists flag words
    separately, so one word can pass one and not the other; the button marks
    by either, so a mark it made always counts as a loanword (owner
    2026-10-27: only the button pressed, yet "6 words marked found")."""
    from . import freq_data, jlpt_data
    return jlpt_data.is_english_loanword(d, r) or freq_data.is_english_loanword(d, r)


def _found_keys(results: dict) -> dict:
    """found_parts' words: key → (is an English loanword, rank for the schedule)."""
    from . import freq_data, jlpt_data
    from .jlpt_data import LEVELS
    keys: dict = {}                       # key → (is a loanword, rank for the schedule)
    for lvl in LEVELS:
        for d, r, nid in results.get(lvl, {}).get("known_words", []):
            if nid is None:
                rk = _found_rank(d, r)
                key = found_key(d, r)
                loan = is_loan(d, r)
                old = keys.get(key)
                keys[key] = ((old[0] if old else False) or loan, rk or _LEVEL_SIZE.get(lvl, 13800))
    freq = results.get("frequency") or {}
    found = freq.get("found_ranks", ())
    if found:
        by_rank = {e[0] - 1: e for e in freq.get("entries", ())}
        for rank in found:
            e = by_rank.get(rank)
            loan = bool(e) and is_loan(e[1], e[2])
            old = keys.get(("row", rank))
            keys[("row", rank)] = ((old[0] if old else False) or loan, rank + 1)
    # Loanwords marked to count at once (overrides "counted", owner
    # 2026-11-08): counted like any other marked word, off the schedule.
    for d, r in results.get("loans_now", ()):
        k = found_key(d, r)
        if k in keys:
            keys[k] = (False, keys[k][1])
    return keys


def hold_back_loans(results: dict, deck_name: str, ignore_suspended: bool, lists: dict = None):
    """Marked English loanwords the rank doesn't count yet come off every
    other count too (owner 2026-10-27: a Nakama card's 344 words with 850
    JLPT words beside it confused): out of the JLPT lists' known words and
    the frequency tiers, so the bars, history, goal and Nakama card grow
    with your vocabulary like the rank. The counted ones are the most
    common first. The marks themselves stay: the held ones are in
    results["loans_waiting"] ({"pairs": JLPT (display, reading), "ranks":
    0-based frequency rows}), drawn as missing tiles with a faint ★.
    lists: the JLPT lists, to put them back in list order among the missing."""
    from . import freq_data
    from .jlpt_data import LEVELS
    if results.get("loans_held"):
        return                            # once per analysis: a second pass would hold more
    results["loans_held"] = True
    parts = found_parts(results)          # before anything is held: every marked one
    if not parts["loans"] or not deck_name:
        return
    try:
        notes = len(mw.col.find_notes(deck_search(deck_name, ignore_suspended, True)))
    except Exception:
        return
    n = loans_counted(notes, parts["loans"])
    loans = sorted((rk, repr(k), k) for k, (is_loan, rk) in _found_keys(results).items() if is_loan)
    held = {k for _rk, _r, k in loans[n:]}
    if not held:
        return
    pairs = set()
    for lvl in LEVELS:
        d = results.get(lvl)
        if not d:
            continue
        keep, out = [], []
        for d_, r, nid in d.get("known_words", []):
            if nid is None:
                if found_key(d_, r) in held:
                    out.append((d_, r))
                    continue
            keep.append((d_, r, nid))
        if out:
            pairs.update(out)
            missing = list(d.get("missing_words", [])) + out
            order: dict = {}
            for i, (ld, lr) in enumerate((lists or {}).get(lvl, [])):
                order.setdefault((ld, lr), i)
            missing.sort(key=lambda p: order.get(tuple(p), len(order)))
            d["known_words"] = keep
            d["missing_words"] = missing
    ranks = {k[1] for k in held if k[0] == "row"}
    results["loans_waiting"] = {"pairs": pairs, "ranks": ranks}
    freq = results.get("frequency")
    if freq:
        freq_data.hold_found(freq, ranks)


def loans_counted(cards: int, loans: list) -> int:
    """How many of the marked loanwords (sorted ranks) count toward the rank
    with `cards` learned cards: the k-th joins at its rank minus k."""
    import bisect
    return bisect.bisect_right([r - k for k, r in enumerate(loans)], cards)


def _norm_found(v) -> dict:
    if isinstance(v, dict):
        return {"hand": int(v.get("hand", 0)), "loans": list(v.get("loans", ()))}
    return {"hand": int(v or 0), "loans": []}           # stored before 2026-10-20: a plain count


def found_extra(deck_name: str) -> dict:
    """The marked words of the last analysis: {"hand", "loans"} (found_parts)."""
    global _found_cache
    if _found_cache is None:
        try:
            with open(_FOUND_PATH, encoding="utf-8") as f:
                _found_cache = _json.load(f)
        except Exception:
            _found_cache = {}
    return _norm_found(_found_cache.get(deck_name, 0))


def rank_split(cards: int, extra: dict) -> tuple[int, int, int]:
    """(rank, loanwords counted, hand-marked) for `cards` learned cards."""
    n = loans_counted(cards, extra["loans"])
    return cards + n + extra["hand"], n, extra["hand"]


def cards_for_rank(total: int, extra: dict) -> tuple[int, int]:
    """The other way round, for a rank shown with the debug ±250 offset:
    (learned cards, loanwords counted) adding up (with the hand marks) to it."""
    target = max(0, total - extra["hand"])
    lo, hi = 0, target
    while lo < hi:                       # cards + loans_counted(cards) is increasing
        mid = (lo + hi + 1) // 2
        if mid + loans_counted(mid, extra["loans"]) <= target:
            lo = mid
        else:
            hi = mid - 1
    return lo, target - lo


def loans_not_yet_counted(rank: int, extra: dict, top: int = 20_000) -> int:
    """Marked loanwords within the top `top` that the rank (with this total)
    doesn't count yet: the frequency bars count them, the rank will later.
    The Near Native ratio line leaves them out, so it compares like with
    like (2026-10-21)."""
    _cards, n = cards_for_rank(rank, extra)
    in_top = sum(1 for r in extra["loans"] if r <= top)
    return max(0, in_top - min(n, in_top))     # the counted ones are the most common first


def set_found_extra(deck_name: str, parts: dict):
    """Called after every analysis (window, Refresh, mini widget) with
    found_parts(results)."""
    global _found_cache
    found_extra(deck_name)                     # load
    if _found_cache.get(deck_name) == parts:
        return
    _found_cache[deck_name] = parts
    try:
        _os.makedirs(_os.path.dirname(_FOUND_PATH), exist_ok=True)
        with open(_FOUND_PATH, "w", encoding="utf-8") as f:
            _json.dump(_found_cache, f, ensure_ascii=False)
    except Exception:
        pass


def rank_count(deck_name: str, ignore_suspended: bool = False, real: bool = False) -> int:
    """Notes with at least one studied card (-is:new: learning, young or
    mature, as the JLPT bars and the goal count words; owner 2026-10-21,
    was young / mature only), plus the words marked found (with no card)
    from the last analysis: marked English loanwords on their schedule
    (loans_counted), the rest at once. With the debug switch on, every note
    — unless real=True (progress history must never record a debug count)."""
    if not deck_name:
        return 0
    seen = real or not debug_count_all()
    try:
        notes = len(mw.col.find_notes(deck_search(deck_name, ignore_suspended, seen)))
    except Exception:
        notes = 0
    return rank_split(notes, found_extra(deck_name))[0]
