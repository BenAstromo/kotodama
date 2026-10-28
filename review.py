"""
review.py
The Progress Review (owner 2026-10-27): what you learned today and over the
last 7 (or 30) days, word by word, kanji by kanji, grammar point by grammar
point, with each grammar point's own sentence. Built from the history
series' dated gains (history.rebuild), so it's the same notes the "+N
today / this week / this month" numbers count.

With a JLPT goal, the goal's words / kanji / grammar come first (the very
items behind the goal card's "Today", goal.today_parts) and the rest is
"outside your goal", each with its level. Without a goal every JLPT item
counts, and words on no list are the extra.

review_view.py shows it. It opens by itself the first time the main window
opens after the day's word target is reached (should_pop / mark_popped),
and from the +N links any time. Always rebuilt from the current results:
words learned after the pop-up show up the next time it opens.
"""

from __future__ import annotations

import datetime

from . import card_state, goal
from .jlpt_data import LEVELS


def _goal_status(results: dict, deck: str) -> dict | None:
    """The goal's status, or None without one (or once its test is over)."""
    try:
        st = goal.status(results, deck, record=False)
    except Exception:
        return None
    return st if st and st["phase"] != "past" else None


def _level_of(res: dict) -> dict:
    """item → its JLPT level, for kanji / grammar results."""
    out = {}
    for lvl in LEVELS:
        for x in (res.get("levels") or {}).get(lvl, ()):
            out.setdefault(x, lvl)
    return out


def _words_by_nid(results: dict) -> dict:
    """Any note id (parsed sentence words too) → its word (display, reading),
    for "learned from" lines."""
    out = {}
    for lvl in LEVELS + ["unlisted"]:
        for d, r, nid in (results.get(lvl) or {}).get("known_words", ()):
            if nid is not None:
                out.setdefault(nid, (d, r))
    for _rank, d, r, nid in (results.get("frequency") or {}).get("entries", ()):
        if nid is not None:
            out.setdefault(nid, (d, r))
    return out


def _sentence(nid: int, gid: str, fallback: str) -> tuple[str, list]:
    """(the note's sentence, [(start, end)] of the grammar point in it), or
    the grammar source's own text with no highlight."""
    try:
        from aqt import mw
        from . import _cfg, sentence_parser, grammar_data
        note = mw.col.get_note(card_state.real_nid(nid))
        model = note.note_type()["name"]
        for m in _cfg().get("field_mappings", []):
            if m.get("note_type") and m["note_type"] != model:
                continue
            sf = m.get("sentence_field", "")
            if sf and sf in note:
                text = sentence_parser.clean(note[sf])
                if text:
                    spans: dict = {}
                    grammar_data.sentence_ids(text, spans)
                    return text, sorted(set(spans.get(gid, ())))
            break
    except Exception:
        pass
    return fallback, []


def build(results: dict, deck: str, days_back: int = 7) -> dict | None:
    """Everything the review shows, or None without a history series.
    {"days": [date, …] (the period, oldest first; the last is today),
     "goal": goal status or None, "level": the goal's level or None,
     "words" / "words_out" / "kanji" / "kanji_out" / "grammar" / "grammar_out":
       [item, …] over the period, in the order learned (newest day last).
    An item: {"text", "reading", "level", "nid" (the note to open), "day"
    (0 = the period's first day), plus "rank" (a step-2 word's frequency
    rank), "from" (kanji) or "pattern",
    "meaning", "sentence", "spans" (grammar)}."""
    series = (results or {}).get("history_series") or {}
    days = series.get("days") or []
    gained = series.get("gained") or {}
    if not days:
        return None
    first = max(0, len(days) - days_back)
    st = _goal_status(results, deck)
    level = st["level"] if st else None
    in_goal = set(goal.levels_upto(level)) if level else set(LEVELS)

    def period(key):
        """The key's gains in the period, oldest first (marks never: no nid)."""
        return [(i - first, nid, item) for i, nid, item in gained.get(key, ())
                if i >= first and nid is not None]

    out = {"days": days[first:], "goal": st, "level": level,
           "words": [], "words_out": [], "kanji": [], "kanji_out": [],
           "grammar": [], "grammar_out": []}

    # Words of the lists: rebuild added one gain per known word, in the
    # results' order, so the n-th gain of a note is its n-th word there.
    pending: dict = {}
    for lvl in LEVELS:
        for d, r, nid in (results.get(lvl) or {}).get("known_words", ()):
            if nid is not None:
                pending.setdefault((lvl, nid), []).append((d, r))
    seen = set()
    for lvl in LEVELS:
        target = out["words"] if lvl in in_goal else out["words_out"]
        for day, nid, _item in period(lvl):
            left = pending.get((lvl, nid))
            if not left:
                continue
            d, r = left.pop(0)
            seen.add(d)
            target.append({"text": d, "reading": r, "level": lvl,
                           "nid": card_state.real_nid(nid), "day": day})

    # N2 / N1 goals, step 2: the common words not on the lists.
    top = goal.vocab_source(level) if level else None
    if top:
        listed = goal._list_ranks(results, level)
        by_rank = {e[0] - 1: e for e in (results.get("frequency") or {}).get("entries", ())}
        for day, nid, rank in period(f"f{top}"):
            if (rank + 1) in listed or rank not in by_rank:
                continue
            _r1, d, r, _n = by_rank[rank]
            if d in seen:
                continue
            seen.add(d)
            out["words"].append({"text": d, "reading": r, "level": None, "rank": rank + 1,
                                 "nid": card_state.real_nid(nid), "day": day})

    # Words on no list: the notes first studied in the period (the rank's
    # gains) whose word is off-list. Parsed sentence words are left out:
    # a sentence's every off-list word would flood the list.
    off = {}
    for d, r, nid in (results.get("unlisted") or {}).get("known_words", ()):
        if nid is not None and nid < card_state.PSEUDO_BASE:
            off.setdefault(nid, []).append((d, r))
    for day, nid, _item in period("rank"):
        for d, r in off.get(nid, ()):
            if d not in seen:
                seen.add(d)
                out["words_out"].append({"text": d, "reading": r, "level": None,
                                         "nid": nid, "day": day})
    out["words_out"].sort(key=lambda w: w["day"])

    # Kanji: dated by the first note that taught them.
    kres = results.get("kanji") or {}
    if kres:
        lv = _level_of(kres)
        words = _words_by_nid(results)
        for day, nid, k in period("kanji"):
            item = {"text": k, "reading": "", "level": lv.get(k), "nid": card_state.real_nid(nid),
                    "day": day, "from": (words.get(nid) or ("", ""))[0]}
            (out["kanji"] if lv.get(k) in in_goal else out["kanji_out"]).append(item)

    # Grammar: the point, and the sentence it was learned from.
    gres = results.get("grammar") or {}
    if gres:
        from . import grammar_data
        lv = _level_of(gres)
        data = grammar_data.data()
        stats = gres.get("stats") or {}
        for day, nid, gid in period("grammar"):
            p = data.get(gid) or {}
            src = next((t for t, _s, n in (stats.get(gid) or {}).get("words", ()) if n == nid), "")
            text, spans = _sentence(nid, gid, src)
            item = {"text": p.get("pattern") or gid, "reading": "", "level": lv.get(gid),
                    "nid": card_state.real_nid(nid), "day": day, "pattern": p.get("pattern") or gid,
                    "meaning": p.get("meaning", ""), "sentence": text, "spans": spans}
            (out["grammar"] if lv.get(gid) in in_goal else out["grammar_out"]).append(item)
    return out


def on_day(items: list, day: int) -> list:
    return [x for x in items if x["day"] == day]


# ── the once-a-day pop-up ─────────────────────────────────────────────────────

def should_pop(results: dict, deck: str) -> bool:
    """True the first time the main window opens after today's word
    target is reached (once a day; only while the goal's plan runs)."""
    from . import _cfg
    if _cfg().get("review_popped") == goal._today().isoformat():
        return False
    st = _goal_status(results, deck)
    v = st and st["phase"] == "plan" and st["kinds"].get("vocab")
    return bool(v) and v["per_day"] > 0 and goal.done_today(v)


def mark_popped():
    from . import _cfg, _save
    c = _cfg()
    c["review_popped"] = goal._today().isoformat()
    _save(c)


WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def day_name(d: datetime.date) -> str:
    """"Thu 22" (a day line)."""
    return f"{WEEKDAYS[d.weekday()]} {d.day}"
