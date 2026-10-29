"""
goal.py
JLPT goal (owner 2026-10-20): the level you're taking and the test date,
and from that how much to learn per day to make it.

  - The test covers every level up to the goal, so an N3 goal counts
    N5 + N4 + N3 (vocab, kanji, grammar), with the same "known" as the bars.
  - Words (owner 2026-10-20): N5–N3 goals count the JLPT word lists (the
    JLPT Vocabulary bars). N2 / N1 goals aim for the modern size estimate
    (6,000 / 13,800 words): step 1, the JLPT word lists up to that level
    (the words most likely on the test, so they come first); step 2, the
    rest from common words that aren't on those lists, most common first
    (the Frequency grid: the top 6,000 / 13,800). Common words count only
    toward step 2, never in place of list words. Why: the Waller-based
    lists stopped well short of N2 / N1 (≈ 4,850 / 8,070 words), and those
    are the tests jobs and schools rely on; but written frequency alone
    fits the test badly (the top 6,000 holds only 45% of the N2 list; 傘 is
    #4,943). Since the Word Addition Project (2026-10-29) the lists up to
    N2 hold 6,000 words (capped there), so an N2 goal has no step 2 (no steps shown);
    N1 (~9,800 listed) keeps both. Kanji and grammar always use the lists.
  - Finish line = 14 days before the test (owner: the last two weeks are for
    review and practice tests). Fixed, no setting.
  - Per day = what was still left at the start of today ÷ days left to the
    finish line (today included), rounded to the nearest (under half a day:
    a weekly number over the past 7 days instead). Worked out fresh every day, so falling
    behind raises tomorrow's number and getting ahead lowers it. It doesn't
    shrink while you learn during the day: "today" counts against it.
  - Marks (★ found, "Mark English loanwords as found")
    count as known but aren't study: they lower what's left at once (and
    so today's number), never "today" (owner 2026-10-20).
  - Vocab leads (it outnumbers kanji and grammar by far): one-number places
    (mini widget, share image) show only vocab; the Overview's goal card
    shows all three. Grammar only when the deck gives grammar at all.
  - No streaks, nothing lost for a missed day.

Stored: config "jlpt_goal" = {"level": "N3", "date": "2026-12-06",
"set": "2026-10-20"}; the day-start counts in user_files/goal_days.json
(the last card counts seen on an earlier day = where today started).
"""

from __future__ import annotations

import datetime
import json
import math
import os

from .jlpt_data import LEVELS
from .overrides import keep_unreadable

BUFFER_DAYS = 14         # finish this many days before the test (owner)
TIGHT_PER_DAY = 40       # more new words a day than this reads as "tight"
# What a daily number of new words feels like (owner 2026-10-22: "say more
# than 'That's tight'"), from what Anki learners commonly report
# (r/LearnJapanese, r/Anki): 10–12 seconds a review, 30–45 seconds a new card
# (its learning steps). Up to TIGHT_PER_DAY is a pace people keep for months;
# past it, most burn out within weeks; past UNREALISTIC (new words or
# minutes a day), few manage it at all.
PACES = [(10, "A gentle pace", "It fits around work or school."),
         (25, "A steady pace", "A common pace for serious learners."),
         (TIGHT_PER_DAY, "An intense pace",
          "Learners who keep this up for months usually call it their ceiling."),
         (None, "A sprint", "Most learners who try more than 40 new words a day burn out "
                            "within weeks or months.")]
UNREALISTIC = (100, 240)     # new words a day, or minutes a day (the low estimate)
UNREALISTIC_NAME = "Not realistic for most people"
UNREALISTIC_NOTE = "Few learners keep this up even for a few weeks."


def _reviews_per_new(days: int) -> float:
    """Reviews a day at the end of a plan of `days` days with ONE new card a
    day (the load scales with the number): an expected-value model, not
    FSRS itself. A review passes 90% of the time and the interval grows
    2.5× (at least 2 days); a lapse costs two presses and starts again at
    1 day. Short plans never reach the long-run ~10 a day (owner 2026-10-22:
    "is that time estimation still true?" for 85 a day over 33 days).
    The average of the plan's last 7 days, to smooth the model's steps."""
    days = max(1, min(int(days), 730))
    if days in _RPN:
        return _RPN[days]
    due: dict = {}                    # day → {interval: cards}
    last = []
    for t in range(days):
        n = 0.0
        for ivl, m in due.pop(t, {}).items():
            n += m * 1.1                       # a lapse is pressed twice
            ok = max(2, round(ivl * 2.5))
            b = due.setdefault(t + ok, {}); b[ok] = b.get(ok, 0) + m * 0.9
            b = due.setdefault(t + 1, {}); b[1] = b.get(1, 0) + m * 0.1
        b = due.setdefault(t + 1, {}); b[1] = b.get(1, 0) + 1.0     # today's new card
        if t >= days - 7:
            last.append(n)
    _RPN[days] = sum(last) / len(last)
    return _RPN[days]


_RPN: dict = {}


def _span(lo: float, hi: float) -> str:
    """Minutes as "40–75 minutes" or, from an hour up, "1.5–2.5 hours" (to
    the half hour)."""
    if lo < 60:
        lo, hi = max(5, round(lo / 5) * 5), max(5, round(hi / 5) * 5)
        return f"{lo}–{hi} minutes" if lo != hi else f"{lo} minutes"
    h = lambda m: f"{max(0.5, round(m / 30) / 2):g}"
    return f"{h(lo)}–{h(hi)} hours" if h(lo) != h(hi) else f"{h(lo)} hours"


def pace(per_day: int, days: int, finish: datetime.date) -> tuple[str, str]:
    """(name, sentence) for `per_day` new words a day over a plan of `days`
    days ending on `finish`, e.g. ("A sprint", "A sprint: by November 22,
    2026, about 430 reviews and 85 new cards a day, 2–2.5 hours (10–12 seconds a
    review, 30–45 seconds a new card). Most learners …"). The reviews are
    the load the plan builds up to by its finish line (_reviews_per_new)."""
    for top, name, note in PACES:
        if top is None or per_day <= top:
            break
    reviews = per_day * _reviews_per_new(days)
    lo = (reviews * 10 + per_day * 30) / 60
    hi = (reviews * 12 + per_day * 45) / 60
    if per_day > UNREALISTIC[0] or lo >= UNREALISTIC[1]:
        name, note = UNREALISTIC_NAME, UNREALISTIC_NOTE
    r = max(10, int(round(reviews, -1))) if reviews >= 5 else 0
    cards = "new card" if per_day == 1 else "new cards"
    return name, (f"{name}: by {fmt_date(finish)}, about {r:,} reviews and "
                  f"{per_day:,} {cards} a day, {_span(lo, hi)} (10–12 seconds a review, "
                  f"30–45 seconds a new card). {note}")


def instead(left: int, test: datetime.date) -> str | None:
    """For a sprint: the per-day number with the next test instead, e.g.
    "For the July 4, 2027 test instead: about 12 a day (a gentle pace)."."""
    nxt = next_test_after(test)
    days = (nxt - datetime.timedelta(days=BUFFER_DAYS) - _today()).days + 1
    if left <= 0 or days <= 0:
        return None
    per = -(-left // days)
    name, _ = pace(per, days, nxt - datetime.timedelta(days=BUFFER_DAYS))
    return f"For the {fmt_date(nxt)} test instead: about {per:,} a day ({name[0].lower() + name[1:]})."


KINDS = ("vocab", "kanji", "grammar")
# goal_days.json: 2 = card counts (marks left out); 3 = N2 / N1 words in two
# steps. Bump whenever what a count means changes.
DAYS_VERSION = 3
FREQ_GOALS = {"N2": 6_000, "N1": 13_800}   # word goals counted on the frequency list (freq_data.TIERS)


_LIST_RANKS: dict = {}       # (level, list sizes, list version) → ranks of the list words


def _list_ranks(results: dict, level: str) -> set:
    """1-based frequency ranks of every JLPT list word up to `level`
    (known or not), so step 2 can leave them out. Cached per list."""
    from . import freq_data, jlpt_data
    lv = levels_upto(level)
    sizes = tuple(len(results.get(l, {}).get("known_words", ())) + len(results.get(l, {}).get("missing_words", ()))
                  for l in lv)
    key = (level, sizes, freq_data.LIST_VERSION)
    if key not in _LIST_RANKS:
        ranks = set()
        for l in lv:
            d = results.get(l) or {}
            # known words are (word, reading, nid), missing ones (word, reading)
            for w in list(d.get("known_words", ())) + list(d.get("missing_words", ())):
                disp, read = w[0], w[1]
                r = freq_data.word_rank(disp, read, jlpt_data.alt_forms(disp, read))
                if r:
                    ranks.add(r)
        _LIST_RANKS.clear()
        _LIST_RANKS[key] = ranks
    return _LIST_RANKS[key]


def vocab_source(level: str) -> int | None:
    """The frequency tier an N2 / N1 goal's words are counted on, or None
    (N5–N3: the JLPT word lists)."""
    return FREQ_GOALS.get(level)

_HERE = os.path.dirname(os.path.abspath(__file__))
_DAYS_PATH = os.path.join(_HERE, "user_files", "goal_days.json")


# ── test dates ────────────────────────────────────────────────────────────────

def first_sunday(year: int, month: int) -> datetime.date:
    d = datetime.date(year, month, 1)
    return d + datetime.timedelta(days=(6 - d.weekday()) % 7)


def test_dates(after: datetime.date = None, n: int = 4) -> list:
    """The next n JLPT dates (first Sunday of July and December) from
    `after` (today) on."""
    after = after or datetime.date.today()
    out, y = [], after.year
    while len(out) < n:
        for m in (7, 12):
            d = first_sunday(y, m)
            if d >= after and len(out) < n:
                out.append(d)
        y += 1
    return out


def next_test_after(d: datetime.date) -> datetime.date:
    return test_dates(d + datetime.timedelta(days=1), 1)[0]


# ── stored goal ───────────────────────────────────────────────────────────────

def _cfg() -> dict:
    from . import _cfg as cfg
    return cfg()


def get() -> dict | None:
    """{"level", "date" (date), "set" (date)} or None."""
    try:
        g = _cfg().get("jlpt_goal")
        if not g or g.get("level") not in LEVELS:
            return None
        return {"level": g["level"],
                "date": datetime.date.fromisoformat(g["date"]),
                "set": datetime.date.fromisoformat(g.get("set") or g["date"])}
    except Exception:
        return None


def save(level: str | None, date: datetime.date = None):
    """Set the goal (level + test date), or clear it with level None."""
    from . import _save
    c = _cfg()
    if level is None:
        c.pop("jlpt_goal", None)
    else:
        old = get()
        keep = old and old["level"] == level and old["date"] == date
        c["jlpt_goal"] = {"level": level, "date": date.isoformat(),
                          "set": (old["set"] if keep else _today()).isoformat()}
    _save(c)


def levels_upto(level: str) -> list:
    return LEVELS[:LEVELS.index(level) + 1]


def _today() -> datetime.date:
    from . import history
    try:
        return history.today()
    except Exception:
        return datetime.date.today()


# ── counts ────────────────────────────────────────────────────────────────────

def _suspended(kind: str) -> set:
    from .overrides import Overrides, KANJI_PATH, GRAMMAR_PATH
    try:
        return {k.split("\t", 1)[0]
                for k in Overrides(KANJI_PATH if kind == "kanji" else GRAMMAR_PATH).suspended}
    except Exception:
        return set()


def counts(results: dict, level: str) -> dict:
    """{kind: (known, total, found)} over every level up to `level`, for the
    parts the results have (the deck-list count has no kanji / grammar).
    found = known only through a mark (★ found, the English-loanword or
    basic-particle buttons), with no card: they count as known, but they
    aren't today's study (see status). N2 / N1 also give "steps":
    {"lists": (known, total), "common": (known, needed)}."""
    lv = levels_upto(level)
    out = {}
    k = n = f = 0
    have = False
    # Marked English loanwords still waiting for the card count to reach
    # them (card_state.hold_back_loans): missing on the bars, but they join
    # on their own, so they aren't words to learn (owner 2026-10-28: the
    # goal's 12 a day became 14 when they were held back). "waiting" = how
    # many of the goal's missing words they are.
    held = results.get("loans_waiting") or {}
    held_pairs, held_ranks = held.get("pairs") or set(), held.get("ranks") or set()
    w = 0
    for l in lv:
        d = results.get(l)
        if d is None:
            continue
        have = True
        known = d.get("known_words", ())
        k += len(known)
        f += sum(1 for _d, _r, nid in known if nid is None)     # marked found, no card
        n += len(known) + len(d.get("missing_words", ()))
        w += sum(1 for p in d.get("missing_words", ()) if (p[0], p[1]) in held_pairs)
    if have:
        out["vocab"] = (k, n, f)
        out["waiting"] = w
    top = vocab_source(level)
    freq = results.get("frequency") or {}
    if have and top and not (freq.get("available", True) and freq.get("tiers")):
        out.pop("vocab")        # no frequency data: no N2 / N1 word number (never the lists alone)
        out.pop("waiting")
    elif have and top:
        # Step 2: common words (top N, 0-based ranks < N) not on the lists
        # up to this level, as many as it takes to reach the size estimate.
        listed = _list_ranks(results, level)
        cards = freq.get("known_nids") or {}
        found_r = freq.get("found_ranks") or set()
        sus = freq.get("suspended_ranks") or set()
        pool = [r for r in range(top) if (r + 1) not in listed and r not in sus]
        need = min(len(pool), max(0, top - n))
        known_x = [r for r in pool if r in cards or r in found_r]
        x = min(len(known_x), need)
        # Words from cards fill the needed count first, marks the rest: else
        # marking many common words pushed card words out of the cap, the
        # day's start dropped and "Today" jumped after unmarking (owner's
        # "Today: 359 / 16", 2026-10-21).
        xf = x - min(sum(1 for r in known_x if r in cards), x)
        # No steps when the lists alone reach the size estimate (owner
        # 2026-10-29): after the Word Addition Project the lists up to N2
        # hold 6,000 words (capped at the estimate), so N2 is just the lists. Only a
        # lot of suspended list words brings step 2 back.
        if need:
            out["steps"] = {"lists": (k, n), "common": (x, need)}
        out["vocab"] = (k + x, n + need, f + xf)
        # waiting loanwords among step 2's still-needed words
        waiting_x = sum(1 for r in pool if r in held_ranks and r not in cards and r not in found_r)
        out["waiting"] = w + min(waiting_x, need - x)
    from . import kanji_data, grammar_data
    for kind, mod in (("kanji", kanji_data), ("grammar", grammar_data)):
        res = results.get(kind)
        if not res:
            continue
        sus = _suspended(kind)
        try:
            c = mod.level_counts(res, sus)
        except Exception:
            continue
        k = sum(c[l][0] for l in lv)
        n = sum(c[l][1] for l in lv)
        # Grammar comes only from deck sentences or a grammar deck: with
        # nothing known at all there's no source, so no number for it.
        if kind == "grammar" and not res.get("known"):
            continue
        stats, known = res.get("stats") or {}, res.get("known") or set()
        f = sum(1 for l in lv for x in res["levels"].get(l, [])
                if x in known and x not in sus and not (stats.get(x) or {}).get("cards"))
        out[kind] = (k, n, f)
    return out


def today_parts(results: dict, level: str, kind: str) -> list:
    """[(history key, keep filter), …] behind a kind's "Today" number, for
    history_view.open_gained: the words of the lists up to `level` (plus the
    step-2 common words), the kanji / grammar of those levels."""
    lv = levels_upto(level)
    if kind == "vocab":
        parts = [(l, None) for l in lv]
        top = vocab_source(level)
        if top:
            listed = _list_ranks(results, level)
            parts.append((f"f{top}", lambda r: (r + 1) not in listed))
        return parts
    res = results.get(kind) or {}
    items = {x for l in lv for x in (res.get("levels") or {}).get(l, ())}
    return [(kind, lambda x: x in items)]


def _today_from_series(results: dict, level: str, now: dict, span: int = 1) -> dict:
    """{kind: items first studied today} from results["history_series"]
    (today_parts' keys and filters, so it matches the link), or {} without
    a series built today. Marks never count (they aren't in "gained").
    span=7: the past 7 days, today included (a weekly pace's count)."""
    series = results.get("history_series") or {}
    days = series.get("days") or []
    gained = series.get("gained") or {}
    if not days or days[-1] != _today():
        return {}
    last = len(days) - 1
    out = {}
    for kind in now:
        if kind not in KINDS:
            continue
        items, n = set(), 0
        for key, keep in today_parts(results, level, kind):
            for i, nid, item in gained.get(key, ()):
                if i <= last - span or nid is None or (keep is not None and not keep(item)):
                    continue
                if item is None:
                    n += 1
                elif (key, item) not in items:
                    items.add((key, item))
                    n += 1
        out[kind] = n
    return out


def _load_days() -> dict:
    try:
        with open(_DAYS_PATH, encoding="utf-8") as f:
            d = json.load(f)
        if isinstance(d, dict):
            return d
        keep_unreadable(_DAYS_PATH)
    except FileNotFoundError:
        pass
    except Exception:
        keep_unreadable(_DAYS_PATH)
    return {}


def _save_days(d: dict):
    try:
        os.makedirs(os.path.dirname(_DAYS_PATH), exist_ok=True)
        tmp = _DAYS_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=1, sort_keys=True)
        os.replace(tmp, _DAYS_PATH)
    except Exception:
        pass


def _day_start(level: str, now: dict, deck: str, record: bool, known: dict = None) -> dict:
    """How many were known FROM CARDS at the start of today: the last count
    seen on an earlier day (a kind first seen today, e.g. a new goal,
    starts at today's count). Marks are left out on purpose (status).
    known: day starts worked out from the history series (status), which
    replace the recorded ones, so the mini widget (no series) shows the
    same "Today" as the window (owner 2026-10-22: N2 → N1 mid-day, the
    window said 20 / 39, the mini widget 0 / 39)."""
    day = _today().isoformat()
    data = _load_days()
    rec = data.get(deck) or {}
    # DAYS_VERSION: how the counts are defined. A change starts the day over
    # rather than mixing two definitions (owner's "Today: 344 / 13" right
    # after N2 / N1 moved to the two steps, 2026-10-20).
    if rec.get("level") != level or rec.get("v") != DAYS_VERSION:
        rec = {"v": DAYS_VERSION, "level": level, "day": day, "prev": {}, "now": {}}
    if rec.get("day") != day:
        prev = dict(rec.get("prev") or {})
        prev.update(rec.get("now") or {})
        rec = {"v": DAYS_VERSION, "level": level, "day": day, "prev": prev, "now": {}}
    cards = {k: v[0] - v[2] for k, v in now.items() if k in KINDS}
    # A kind first seen today (a new goal) starts here; a count below the
    # start (a lapsed or suspended card) lowers it for the rest of the day.
    new = {k: v for k, v in cards.items() if k not in rec["prev"] or v < rec["prev"][k]}
    new.update({k: v for k, v in (known or {}).items()
                if k in cards and rec["prev"].get(k) != v})
    rec["prev"].update(new)
    start = {k: rec["prev"][k] for k in cards}
    if record and (new or any(rec["now"].get(k) != v for k, v in cards.items())):
        rec["now"].update(cards)
        data[deck] = rec
        _save_days(data)
    return start


# ── status ────────────────────────────────────────────────────────────────────

def status(results: dict, deck: str = "", record: bool = True) -> dict | None:
    """Everything the goal displays, or None without a goal.
    phase: "plan" (learning), "done" (everything learned before the finish
    line), "review" (in the last 14 days), "past" (the test day is over)."""
    g = get()
    if g is None or not results:
        return None
    today = _today()
    test = g["date"]
    finish = test - datetime.timedelta(days=BUFFER_DAYS)
    now = counts(results, g["level"])
    # With the window's history series, "Today" is what was first studied
    # today: the very notes its link lists (owner 2026-10-22: "Today: 2 kanji"
    # for one new kanji, the day's start recorded under the old rule). That
    # start is saved to goal_days.json for the mini widget, which has no series.
    known = {kind: max(0, now[kind][0] - now[kind][2] - got)
             for kind, got in _today_from_series(results, g["level"], now).items()}
    start = _day_start(g["level"], now, deck, record, known) if now else {}
    start.update(known)
    week = _today_from_series(results, g["level"], now, 7)
    days_left = (finish - today).days + 1             # today included
    kinds = {}
    for kind in KINDS:
        if kind not in now:
            continue
        k, n, f = now[kind]
        # Marks (★ found, the loanword / particle buttons) move the starting
        # point, not today's progress (owner 2026-10-20): what's left counts
        # them at once, so today's number drops as soon as you mark; "today"
        # counts only words / kanji / grammar learned from cards. Waiting
        # loanwords (counts) are left out of what's left the same way: as one
        # joins, it moves from waiting to found, and the number stays put.
        w = now.get("waiting", 0) if kind == "vocab" else 0
        left_start = max(0, n - f - w - start[kind])
        per_day, weekly, per_week = daily_share(left_start, days_left, weekly_ok=kind != "vocab")
        today_n = max(0, k - f - start[kind])
        kinds[kind] = {"known": k, "total": n, "left": max(0, n - k - w), "per_day": per_day,
                       "today": today_n, "found": f, "waiting": w,
                       "weekly": weekly, "per_week": per_week,
                       "week": max(today_n, week.get(kind, 0))}
    if today > test:
        phase = "past"
    elif kinds and all(v["left"] == 0 for v in kinds.values()):
        phase = "done"
    elif days_left <= 0:
        phase = "review"
    else:
        phase = "plan"
    v = kinds.get("vocab")
    return {"level": g["level"], "date": test, "set": g["set"], "finish": finish,
            "steps": now.get("steps"),
            "days_left": max(0, days_left), "test_days": (test - today).days,
            "phase": phase, "kinds": kinds,
            "tight": phase == "plan" and bool(v) and v["per_day"] > TIGHT_PER_DAY,
            "next_date": next_test_after(test)}


def daily_share(left: int, days_left: int, weekly_ok: bool = True) -> tuple:
    """(per day, weekly?, per week) for `left` over `days_left` days.
    Rounded to the nearest (owner 2026-10-28: 1.4 → 1, 1.5 → 2; rounding up
    made 1.02 a day "2"). It corrects itself: following it, what's left
    creeps up until the number rounds up for a day. The last day asks for
    everything left. Up to 6 a week: a weekly number instead (owner
    2026-10-28: "1 a day" doubled a 0.3-a-day pace; 7 a week is simply 1 a
    day), rounded up since it's small, counted over the past 7 days (no
    reset day); per day stays 1 for the places that show one number.
    Words never go weekly (weekly_ok=False, owner 2026-10-28): at least 1 a
    day while any are left."""
    if days_left <= 1:
        return left, False, left
    rate = left / days_left
    per_week = min(left, math.ceil(rate * 7))
    if weekly_ok and 0 < per_week <= 6:
        return 1, True, per_week
    per_day = max(1, math.floor(rate + 0.5)) if left else 0
    return per_day, False, per_day * 7


def done_today(k: dict) -> bool:
    """Today's part done. A weekly kind (owner 2026-10-28): one learned
    today (a full day's share under 1 a day), or the past 7 days already
    hold the week's number."""
    if k.get("weekly"):
        return k["today"] >= 1 or k["week"] >= k["per_week"]
    return k["today"] >= k["per_day"]


# ── text ──────────────────────────────────────────────────────────────────────

_EN_MONTHS = ["January", "February", "March", "April", "May", "June", "July",
              "August", "September", "October", "November", "December"]
_JA_DOW = "月火水木金土日"


def fmt_date(d: datetime.date, ja: bool = False, year: bool = True) -> str:
    if ja:
        return (f"{d.year}年" if year else "") + f"{d.month}月{d.day}日（{_JA_DOW[d.weekday()]}）"
    return f"{_EN_MONTHS[d.month - 1]} {d.day}" + (f", {d.year}" if year else "")


def aiming_line(st: dict, ja: bool = False) -> str:
    """"Aiming for JLPT N3 · December 2026" (share image, Nakama card)."""
    d = st["date"]
    if ja:
        return f"目標：JLPT {st['level']} · {d.year}年{d.month}月"
    return f"Aiming for JLPT {st['level']} · {_EN_MONTHS[d.month - 1]} {d.year}"


def today_line(st: dict, ja: bool = False) -> str | None:
    """"Today: 9 / 14 words" (mini widget), or None outside the plan."""
    v = st["kinds"].get("vocab")
    if st["phase"] != "plan" or not v:
        return None
    if v.get("weekly"):
        if ja:
            return f"今週：{v['week']:,} / {v['per_week']:,} 語"
        return f"This week: {v['week']:,} / {v['per_week']:,} words"
    if ja:
        return f"今日：{v['today']:,} / {v['per_day']:,} 語"
    return f"Today: {v['today']:,} / {v['per_day']:,} words"


def share_goal(results: dict = None) -> dict | None:
    """{"level", "date"} for the share image / Nakama card: a goal whose
    test isn't over yet, when the share pop-up's checkbox is on."""
    if not _cfg().get("share_show_goal", True):
        return None
    g = get()
    if g is None or g["date"] < _today():
        return None
    return {"level": g["level"], "date": g["date"]}
