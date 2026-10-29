"""Offscreen test of the JLPT goal: maths, Japanese, and renders of every
place it shows. Never touches the owner's config or user_files (config is
in memory, goal_days.json goes to this folder)."""
import os, sys, types, datetime
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["QT_QPA_FONTDIR"] = r"C:\Windows\Fonts"
ADDON = r"C:\Users\benne\AppData\Roaming\Anki2\addons21\jlpt_progress"
OUT = os.path.dirname(os.path.abspath(__file__))
from PyQt6 import QtCore, QtGui, QtWidgets
qt = types.ModuleType("aqt.qt")
for m in (QtCore, QtGui, QtWidgets):
    for k in dir(m):
        if not k.startswith("_"): setattr(qt, k, getattr(m, k))
qt.pyqtSignal = QtCore.pyqtSignal
class _Any:
    def __init__(s, *a, **k): pass
    def __getattr__(s, n): return _Any()
    def __call__(s, *a, **k): return _Any()
    def __bool__(s): return False
    def __iter__(s): return iter(())
aqt = types.ModuleType("aqt"); aqt.qt = qt; aqt.mw = _Any(); aqt.gui_hooks = _Any()
utils = types.ModuleType("aqt.utils"); utils.showWarning = print; utils.tooltip = print; utils.askUser = lambda *a, **k: False
anki = types.ModuleType("anki"); au = types.ModuleType("anki.utils"); au.ids2str = lambda ids: ""
sys.modules.update({"aqt": aqt, "aqt.qt": qt, "aqt.utils": utils, "anki": anki, "anki.utils": au})
pkg = types.ModuleType("jlpt_progress"); pkg.__path__ = [ADDON]; sys.modules["jlpt_progress"] = pkg
CFG = {}
pkg._cfg = lambda: CFG
pkg._save = lambda c: CFG.update(c)
app = QtWidgets.QApplication([])
app.setFont(QtGui.QFont("Segoe UI", 9))

from jlpt_progress import goal, history, divine_text, share_card, rank_data, theme
from jlpt_progress.goal_view import WORDS_EXPLAINED as WORDS, FINISH_LINE, WAITING_EXPLAINED, TODAY_EXPLAINED
goal._DAYS_PATH = os.path.join(OUT, "goal_days_test.json")
if os.path.exists(goal._DAYS_PATH):
    os.remove(goal._DAYS_PATH)
TODAY = [datetime.date(2026, 10, 20)]
history.today = lambda: TODAY[0]
fails = []
def check(name, got, want):
    ok = got == want
    print(("ok  " if ok else "FAIL"), name, got, "" if ok else f"(want {want})")
    if not ok: fails.append(name)

# ── dates ──
check("test dates", goal.test_dates(datetime.date(2026, 10, 20)),
      [datetime.date(2026, 12, 6), datetime.date(2027, 7, 4), datetime.date(2027, 12, 5), datetime.date(2028, 7, 2)])
check("on the day itself", goal.test_dates(datetime.date(2026, 12, 6), 1), [datetime.date(2026, 12, 6)])
check("next after", goal.next_test_after(datetime.date(2026, 12, 6)), datetime.date(2027, 7, 4))

# ── fake results ──
def words(n, tag):
    return [(f"{tag}{i}", "", i) for i in range(n)]
def miss(n, tag):            # missing words are (word, reading), like the real results
    return [(f"{tag}{i}", "") for i in range(n)]
def results(n5, n4, n3, kanji=None, grammar=None):
    r = {"N5": {"known_words": words(n5, "a"), "missing_words": miss(700 - n5, "b")},
         "N4": {"known_words": words(n4, "c"), "missing_words": miss(650 - n4, "d")},
         "N3": {"known_words": words(n3, "e"), "missing_words": miss(1600 - n3, "f")},
         "N2": {"known_words": [], "missing_words": miss(1800, "g")},
         "N1": {"known_words": [], "missing_words": miss(3000, "h")},
         "frequency": {"available": True, "tiers": [(800, 500), (1500, 900), (3900, 2000), (6000, 2600),
                                                    (13800, 4000), (20000, 5000)],
                       "tier_totals": {n: n for n in (800, 1500, 3900, 6000, 13800, 20000)}}}
    if kanji is not None:
        levels = {l: [f"{l}k{i}" for i in range(100)] for l in ("N5", "N4", "N3", "N2", "N1")}
        r["kanji"] = {"levels": levels, "known": set(levels["N5"][:kanji[0]] + levels["N4"][:kanji[1]] + levels["N3"][:kanji[2]])}
    if grammar is not None:
        levels = {l: [f"{l}g{i}" for i in range(50)] for l in ("N5", "N4", "N3", "N2", "N1")}
        r["grammar"] = {"levels": levels, "known": set(levels["N5"][:grammar[0]] + levels["N4"][:grammar[1]])}
    return r

check("no goal", goal.status(results(600, 400, 300)), None)
goal.save("N3", datetime.date(2026, 12, 6))
check("saved", (goal.get()["level"], goal.get()["set"]), ("N3", datetime.date(2026, 10, 20)))
st = goal.status(results(600, 400, 300, (90, 50, 10), (40, 20)), "D")
v = st["kinds"]["vocab"]
check("finish", st["finish"], datetime.date(2026, 11, 22))
check("days left (today incl.)", st["days_left"], 34)
check("vocab", (v["known"], v["total"], v["left"]), (1300, 2950, 1650))
check("vocab per day = round(1650/34)", v["per_day"], 49)
check("tight", st["tight"], True)
check("kanji per day = round(150/34)", st["kinds"]["kanji"]["per_day"], 4)
check("grammar per day = round(90/34)", st["kinds"]["grammar"]["per_day"], 3)
check("today starts at 0", v["today"], 0)
# later the same day: per day stays, today counts up
st = goal.status(results(600, 400, 320), "D")       # deck-list count: no kanji / grammar
check("same day: per day fixed", st["kinds"]["vocab"]["per_day"], 49)
check("same day: today +20", st["kinds"]["vocab"]["today"], 20)
check("deck-list count: vocab only", sorted(st["kinds"]), ["vocab"])
# next day: started at 1320, fell behind → more per day
TODAY[0] = datetime.date(2026, 10, 21)
st = goal.status(results(600, 400, 320, (90, 50, 10), (40, 20)), "D")
check("next day: per day = round(1630/33)", st["kinds"]["vocab"]["per_day"], 49)
check("next day: today 0", st["kinds"]["vocab"]["today"], 0)
check("next day: kanji start from yesterday", st["kinds"]["kanji"]["today"], 0)
# no grammar source → no grammar number
st = goal.status(results(600, 400, 320, (90, 50, 10), (0, 0)), "D")
check("grammar without a source", "grammar" in st["kinds"], False)
# review phase / done / past
TODAY[0] = datetime.date(2026, 11, 25)
check("review phase", goal.status(results(600, 400, 900), "D")["phase"], "review")
check("done", goal.status(results(700, 650, 1600), "D")["phase"], "done")
TODAY[0] = datetime.date(2026, 12, 7)
check("past", goal.status(results(600, 400, 900), "D")["phase"], "past")
TODAY[0] = datetime.date(2026, 10, 20)

# Marks (the English-loanword button, ★ found) aren't today's study (owner 2026-10-20)
TODAY[0] = datetime.date(2026, 10, 25)
goal.save("N3", datetime.date(2026, 12, 6))
def marked(r, n):            # n N3 words marked found (no card)
    r["N3"]["known_words"] += [(f"m{i}", "", None) for i in range(n)]
    r["N3"]["missing_words"] = r["N3"]["missing_words"][n:]
    return r
st0 = goal.status(results(600, 400, 300), "D")           # day start: 1,300 from cards
check("before marking: per day = round(1650/29)", st0["kinds"]["vocab"]["per_day"], 57)
st = goal.status(marked(results(600, 400, 300), 200), "D")
check("marking 200: today stays 0", st["kinds"]["vocab"]["today"], 0)
check("marking 200: per day drops at once = round(1450/29)", st["kinds"]["vocab"]["per_day"], 50)
check("marking 200: left", st["kinds"]["vocab"]["left"], 1450)
st = goal.status(marked(results(600, 400, 310), 200), "D")
check("then 10 from cards: today 10", st["kinds"]["vocab"]["today"], 10)
check("then 10 from cards: per day unchanged", st["kinds"]["vocab"]["per_day"], 50)
TODAY[0] = datetime.date(2026, 10, 26)
st = goal.status(marked(results(600, 400, 310), 200), "D")
check("next day: per day = round(1440/28)", st["kinds"]["vocab"]["per_day"], 51)
check("next day: today 0", st["kinds"]["vocab"]["today"], 0)
st = goal.status(marked(results(600, 400, 310), 100), "D")
check("un-marking 100: per day up at once = round(1540/28)", st["kinds"]["vocab"]["per_day"], 55)
check("un-marking 100: today still 0", st["kinds"]["vocab"]["today"], 0)
# kanji marks
r = results(600, 400, 310, (90, 50, 10), (40, 20)); r = marked(r, 100)
st = goal.status(r, "D"); base_k = st["kinds"]["kanji"]["per_day"]
r2 = results(600, 400, 310, (90, 50, 10), (40, 20)); r2 = marked(r2, 100)
r2["kanji"]["known"] |= {f"N3k{i}" for i in range(50, 80)}     # 30 kanji marked found (no stats = no card)
st = goal.status(r2, "D")
check("kanji marks: today 0", st["kinds"]["kanji"]["today"], 0)
check("kanji marks: per day drops", st["kinds"]["kanji"]["per_day"] < base_k, True)
# frequency (N1) marks
goal.save("N1", datetime.date(2027, 12, 5))
def fres(found):
    r = results(600, 400, 300)
    r["frequency"]["known_nids"] = {i: [i] for i in range(3600)}
    r["frequency"]["found_ranks"] = set(range(3600, 3600 + found))
    r["frequency"]["tiers"] = [(t, min(t, 3600 + found)) for t, _ in r["frequency"]["tiers"]]
    return r
st0 = goal.status(fres(0), "D")
st = goal.status(fres(400), "D")
check("N1 marks: today 0", st["kinds"]["vocab"]["today"], 0)
check("N1 marks: left drops by 400", st0["kinds"]["vocab"]["left"] - st["kinds"]["vocab"]["left"], 400)
TODAY[0] = datetime.date(2026, 10, 20)
if os.path.exists(goal._DAYS_PATH):
    os.remove(goal._DAYS_PATH)

# N2 / N1 goals count words on the frequency list (owner 2026-10-20)
goal.save("N1", datetime.date(2027, 12, 5))
st = goal.status(results(600, 400, 300, (90, 50, 10), (40, 20)), "D")
check("N1 words: lists first, total = 13,800", (st["kinds"]["vocab"]["known"], st["kinds"]["vocab"]["total"]), (1300, 13800))
check("N1 steps", st["steps"], {"lists": (1300, 7750), "common": (0, 6050)})
check("N1 kanji still lists", st["kinds"]["kanji"]["total"], 500)
goal.save("N2", datetime.date(2027, 12, 5))
st = goal.status(results(600, 400, 300), "D")
check("N2 steps", st["steps"], {"lists": (1300, 4750), "common": (0, 1250)})
r = results(600, 400, 300); r["frequency"]["known_nids"] = {i: [i] for i in range(1000)}
st = goal.status(r, "D")
check("N2: 1,000 common words count toward step 2", st["steps"]["common"], (1000, 1250))
r["frequency"]["known_nids"] = {i: [i] for i in range(3000)}
st = goal.status(r, "D")
check("N2: step 2 capped, can't replace list words", (st["steps"]["common"], st["kinds"]["vocab"]["known"]), ((1250, 1250), 2550))
check("N2: not done while lists aren't", st["kinds"]["vocab"]["left"], 3450)
# Waiting English loanwords (card_state.hold_back_loans) aren't words to
# learn: left out of what's left and the per-day number (owner 2026-10-28)
r = results(600, 400, 300); r["frequency"]["known_nids"] = {i: [i] for i in range(1000)}
st0 = goal.status(r, "D")
r["loans_waiting"] = {"pairs": {tuple(p) for p in r["N3"]["missing_words"][:1000]},
                      "ranks": set(range(1000, 1150))}
st = goal.status(r, "D")
check("N2 waiting: 1,000 list + 150 step-2 loanwords", st["kinds"]["vocab"]["waiting"], 1150)
check("N2 waiting: left drops by 1,150", st0["kinds"]["vocab"]["left"] - st["kinds"]["vocab"]["left"], 1150)
check("N2 waiting: bars' known unchanged", st["kinds"]["vocab"]["known"], st0["kinds"]["vocab"]["known"])
check("N2 waiting: per day drops", st["kinds"]["vocab"]["per_day"] < st0["kinds"]["vocab"]["per_day"], True)
r["loans_waiting"]["ranks"] = set(range(1000, 1400))           # step 2 still needs only 250
check("N2 waiting: capped at step 2's need", goal.status(r, "D")["kinds"]["vocab"]["waiting"], 1250)
goal.save("N3", datetime.date(2026, 12, 6))
check("N3 words = lists", goal.status(results(600, 400, 300), "D")["kinds"]["vocab"]["total"], 2950)

# Real word lists in the real results' shape (owner's crash 2026-10-20:
# missing words are (word, reading) pairs, known ones (word, reading, nid))
from jlpt_progress import jlpt_data
real = jlpt_data.build_lists({})
RR = {l: {"known_words": [(d, r, 1) for d, r in real[l][:100]], "missing_words": [(d, r) for d, r in real[l][100:]]}
      for l in jlpt_data.LEVELS}
RR["frequency"] = {"available": True, "tiers": [(n, 0) for n in (800, 1500, 3900, 6000, 13800, 20000)],
                   "tier_totals": {}, "known_nids": {}, "found_ranks": set(), "suspended_ranks": set()}
for lvl in ("N2", "N1"):
    goal.save(lvl, datetime.date(2027, 12, 5))
    st = goal.status(RR, "D", record=False)
    n_lists = sum(len(real[l]) for l in goal.levels_upto(lvl))
    if lvl == "N2":
        # the lists up to N2 reach the 6,000 estimate (Word Addition Project,
        # 2026-10-29): no step 2, so no steps; the total is the lists
        check("real lists N2: no steps", st.get("steps"), None)
        check("real lists N2: words = lists", st["kinds"]["vocab"]["total"], n_lists)
        continue
    check(f"real lists {lvl}: step 1 total", st["steps"]["lists"], (100 * len(goal.levels_upto(lvl)), n_lists))
    print("    step 2 needed:", st["steps"]["common"][1])
# a day start saved under an older counting rule starts the day over (owner's "344 / 13")
import json as _json
goal.save("N2", datetime.date(2027, 7, 4))
_json.dump({"D2": {"v": 2, "level": "N2", "day": TODAY[0].isoformat(), "prev": {"vocab": 1000}, "now": {"vocab": 1000}}},
           open(goal._DAYS_PATH, "w"))
r = results(600, 400, 300); r["frequency"]["known_nids"] = {i: [i] for i in range(500)}
check("old-rule day start: today 0", goal.status(r, "D2")["kinds"]["vocab"]["today"], 0)
# "Today" from the history series = what its link lists (owner 2026-10-22:
# "Today: 2 kanji" for one new kanji, the day's start saved under the old rule)
goal.save("N3", datetime.date(2026, 12, 6))
r = results(600, 400, 300, (90, 50, 10), (40, 20))
for kind in ("kanji", "grammar"):
    r[kind]["stats"] = {x: {"cards": [1]} for x in r[kind]["known"]}
_json.dump({"D3": {"v": goal.DAYS_VERSION, "level": "N3", "day": TODAY[0].isoformat(),
                   "prev": {"vocab": 1290, "kanji": 148, "grammar": 60}, "now": {}}},
           open(goal._DAYS_PATH, "w"))
check("no series: day start from goal_days", goal.status(r, "D3", record=False)["kinds"]["kanji"]["today"], 2)
days = [TODAY[0] - datetime.timedelta(days=1), TODAY[0]]
r["history_series"] = {"days": days, "gained": {
    "kanji": [(0, 5, "N5k0"), (1, 7, "N3k9"), (1, 7, "N1k3"), (1, None, "N4k1")],   # N1 / a mark: not today's
    "N3": [(1, 7, None), (1, 8, None)], "N5": [(0, 9, None)], "grammar": []}}
st = goal.status(r, "D3", record=False)["kinds"]
check("series: today = first studied today", (st["vocab"]["today"], st["kanji"]["today"], st["grammar"]["today"]), (2, 1, 0))
check("series: per day unchanged by the old start", st["kanji"]["per_day"],
      int((150 - 1) / ((datetime.date(2026, 11, 22) - TODAY[0]).days + 1) + 0.5))
r["history_series"]["days"] = [d - datetime.timedelta(days=1) for d in days]   # built yesterday
check("stale series: goal_days again", goal.status(r, "D3", record=False)["kinds"]["kanji"]["today"], 2)
# under 1 a day → a weekly number over the past 7 days (owner 2026-10-28)
goal.save("N3", datetime.date(2027, 7, 4))
rw = results(600, 400, 300, (90, 50, 10), (40, 20))
for kind in ("kanji", "grammar"):
    rw[kind]["stats"] = {x: {"cards": [1]} for x in rw[kind]["known"]}
wdays = [TODAY[0] - datetime.timedelta(days=7 - i) for i in range(8)]
rw["history_series"] = {"days": wdays, "gained": {
    "grammar": [(0, 1, "N5g0"), (3, 2, "N5g1"), (5, 3, "N4g0")], "kanji": []}}   # day 0: 7 days ago
g = goal.status(rw, "W", record=False)["kinds"]["grammar"]
dl = (datetime.date(2027, 6, 20) - TODAY[0]).days + 1
check("weekly: grammar under 1 a day", (g["weekly"], g["per_week"]), (True, -(-90 * 7 // dl)))
check("weekly: past 7 days only", (g["week"], g["today"]), (2, 0))
check("weekly: nothing today, week short → not done", goal.done_today(g), False)
rw["history_series"]["gained"]["grammar"].append((7, 4, "N4g1"))
g = goal.status(rw, "W", record=False)["kinds"]["grammar"]
check("weekly: one today → done", (g["week"], g["today"], goal.done_today(g)), (3, 1, True))
check("weekly: one today, week short is still done",
      goal.done_today({"weekly": True, "today": 1, "week": 2, "per_week": 6, "per_day": 1}), True)
check("weekly: week reached, nothing today → done",
      goal.done_today({"weekly": True, "today": 0, "week": 6, "per_week": 6, "per_day": 1}), True)
check("rounding to the nearest; up to 6 a week weekly",
      [goal.daily_share(l, 700) for l in (980, 1050, 600, 601, 300, 10, 0)] + [goal.daily_share(5, 1)],
      [(1, False, 7), (2, False, 14), (1, True, 6), (1, False, 7), (1, True, 3), (1, True, 1), (0, False, 0), (5, False, 5)])
check("words never weekly: 1 a day", goal.daily_share(10, 700, weekly_ok=False), (1, False, 7))
check("weekly: vocab stays daily", goal.status(rw, "W", record=False)["kinds"]["vocab"]["weekly"], False)
check("weekly JA", divine_text.translate("Per day: <b>7</b> words · <b>3</b> grammar points a week"),
      "1日あたり：<b>7</b> 語 · <b>3</b> 文法（週あたり）")
check("weekly mini", goal.today_line({"phase": "plan", "kinds": {"vocab": {"weekly": True, "week": 2, "per_week": 5}}}),
      "This week: 2 / 5 words")
goal.save("N3", datetime.date(2026, 12, 6))
# the window's series start is saved, so the mini widget (no series) agrees
# (owner 2026-10-22: switched N2 → N1 mid-day, window 20 / 39, mini 0 / 39)
_json.dump({"D3": {"v": goal.DAYS_VERSION, "level": "N2", "day": TODAY[0].isoformat(),
                   "prev": {"vocab": 999}, "now": {}}}, open(goal._DAYS_PATH, "w"))
r["history_series"]["days"] = days
mini_r = dict(r); mini_r.pop("history_series")
check("level switch, no series yet: today 0", goal.status(mini_r, "D3")["kinds"]["kanji"]["today"], 0)
st = goal.status(r, "D3")["kinds"]
check("level switch, window: from the series", (st["vocab"]["today"], st["kanji"]["today"]), (2, 1))
st = goal.status(mini_r, "D3")["kinds"]
check("level switch, mini afterwards: same as the window", (st["vocab"]["today"], st["kanji"]["today"]), (2, 1))
goal.save("N2", datetime.date(2027, 7, 4))      # what the next checks expect
r2 = results(600, 400, 300); r2.pop("frequency")
check("N2 without frequency data: no word number", "vocab" in goal.status(r2, "D2")["kinds"], False)
goal.save("N3", datetime.date(2026, 12, 6))

# ── Japanese for the built texts ──
samples = [
    "<b style='color:#ffc107;'>JLPT N3</b> · December 6, 2026 · <b>34</b> days left to learn",
    "<b style='color:#ffc107;'>JLPT N3</b> · December 6, 2026 · <b>1</b> day to the test",
    "Your JLPT N3 test was on December 6, 2026. How did it go?",
    "Everything up to N3 is learned. The rest is review.",
    "Per day: <b>49</b> words · <b style='color:#7bd88f;'>5</b> kanji · <b>1</b> grammar point",
    "Today: <b>9</b> / 49 words · <b style='color:#7bd88f;'>5</b> / 5 kanji · <b>0</b> / 3 grammar points",
    "Still to learn: <b>1,650</b> words · <b>150</b> kanji · <b>90</b> grammar points",
    "<span style='color:#ffb74d;'>" + goal.pace(49, 33, datetime.date(2026, 11, 22))[1] + " " + goal.instead(1650, datetime.date(2026, 12, 6)) + "</span>",
    goal.pace(8, 250, datetime.date(2026, 11, 22))[1], goal.pace(25, 100, datetime.date(2026, 11, 22))[1], goal.pace(30, 200, datetime.date(2026, 11, 22))[1], goal.pace(1, 5, datetime.date(2026, 11, 22))[1],
    goal.pace(150, 20, datetime.date(2026, 11, 22))[1] + " " + goal.instead(3000, datetime.date(2026, 12, 6)),
    "You already know every word up to N3.",
    "1,650 words still to learn, and the test is less than 14 days away: there's no time left before the finish line.",
    "1,650 words still to learn: about <b>49</b> a day until November 22, 2026, 14 days before the test.<br><span style='color:#ffb74d;'>" + goal.pace(49, 33, datetime.date(2026, 11, 22))[1] + "</span>",
    "December 6, 2026",
    "<span style='color:#ffc107;'>■</span> Words up to N3",
    "<span style='color:#bdbdbd;'>┅</span> On track",
    FINISH_LINE, WAITING_EXPLAINED, TODAY_EXPLAINED,
    "Step 1 · JLPT word lists up to N2: <b>3,100</b> / 4,853 (the JLPT Vocabulary bars and grids)",
    "Step 2 · then common words not on the lists: <b style='color:#7bd88f;'>1,147</b> / 1,147 (the Frequency grid, most common first)",
    "1,650 words still to learn: about <b>49</b> a day until November 22, 2026, 14 days before the test.<br>Step 1, JLPT word lists: 1,200 to go · step 2, common words: 450 to go.",
    "<span style='color:#64ffda;'>■</span> Goal words (N2)", "Top<br><span style='font-size:9px;'>3,900</span>", "Most Common Words — Top 3,900",
    "<span style='color:#46b6e8;'>■</span> Top 3,900",
    "<span style='color:#64ffda;'>■</span> Top 13,800 words",
    WORDS,
]
import re
for t in samples:
    ja = divine_text.translate(t)
    left = [w for w in re.findall(r"[A-Za-z]{3,}", re.sub(r"<[^>]+>", " ", ja)) if w not in ("JLPT",)]
    print("JA  ", ja)
    if left or ja == t:
        fails.append("ja: " + t); print("FAIL still English:", left)

# ── renders ──
from jlpt_progress import progress_dialog as pd, goal_view, mini_widget
from jlpt_progress.history_view import HistoryTab

class FakeTab(QtWidgets.QDialog):
    goal_changed = QtCore.pyqtSignal()
    def __init__(self, res):
        super().__init__(); self._results = res; self._deck_name = "D"

def card_shot(res, gold, w=760):
    pd._GOLD_MODE["on"] = gold
    tab = FakeTab(res)
    v = QtWidgets.QVBoxLayout(tab)
    goal_view.add_goal_card(v, tab); v.addStretch(1)
    theme.apply(tab, gold=gold)
    if gold:
        divine_text.apply(tab, True)
    tab.resize(w, 10); tab.adjustSize(); tab.resize(w, tab.sizeHint().height()); tab.show(); app.processEvents()
    return tab.grab()

R = results(600, 400, 309, (90, 50, 10), (40, 20))
goal.status(results(600, 400, 300, (90, 50, 5), (40, 19)), "D")   # day start
shots = [card_shot(R, False), card_shot(R, True)]
CFG.pop("jlpt_goal"); shots.append(card_shot(R, False))           # no goal
goal.save("N3", datetime.date(2027, 7, 4)); shots.append(card_shot(R, False))   # relaxed pace
TODAY[0] = datetime.date(2026, 11, 28); goal.save("N3", datetime.date(2026, 12, 6)); shots.append(card_shot(R, False))  # review
TODAY[0] = datetime.date(2026, 12, 8); shots.append(card_shot(R, False))          # past
TODAY[0] = datetime.date(2026, 10, 20)
goal.save("N1", datetime.date(2027, 12, 5)); shots.append(card_shot(R, False))   # N1: frequency words
goal.save("N3", datetime.date(2026, 12, 6))
CFG["jlpt_goal"]["set"] = "2026-09-20"
h = sum(s.height() for s in shots) + 10 * len(shots)
img = QtGui.QPixmap(760, h); img.fill(QtGui.QColor("#101010"))
p = QtGui.QPainter(img); y = 0
for s in shots:
    p.drawPixmap(0, y, s); y += s.height() + 10
p.end(); img.save(os.path.join(OUT, "goal_cards.png"))

# dialog
for gold in (False, True):
    pd._GOLD_MODE["on"] = gold
    dlg = goal_view.GoalDialog(FakeTab(R)); dlg.show(); app.processEvents()
    dlg.grab().save(os.path.join(OUT, f"goal_dialog{'_gold' if gold else ''}.png"))
pd._GOLD_MODE["on"] = False

# history chart with 60 past days
days = [datetime.date(2026, 10, 20) - datetime.timedelta(days=59 - i) for i in range(60)]
vals = {"rank": [2000 + 12 * i for i in range(60)], "mature": [1500 + 8 * i for i in range(60)],
        "jlpt": [900 + 7 * i for i in range(60)]}
for l, base in (("N5", 560), ("N4", 340), ("N3", 0), ("N2", 0), ("N1", 0)):
    vals[l] = [base + (i * 2 if l == "N3" else i // 2 if l in ("N5", "N4") else 0) for i in range(60)]
vals["f13800"] = [3200 + 13 * i for i in range(60)]
series = {"days": days, "values": vals, "recorded": [i > 50 for i in range(60)]}
for gold in (False, True):
    pd._GOLD_MODE["on"] = gold
    ht = HistoryTab(series, "D", results_fn=lambda: R)
    theme.apply(ht, gold=gold)
    if gold: divine_text.apply(ht, True)
    ht.resize(1000, 720); ht.show(); app.processEvents()
    ht._chart._hover = 75; ht.grab().save(os.path.join(OUT, f"goal_history{'_gold' if gold else ''}.png"))
    for rng in (7,):
        ht._set_range(rng); app.processEvents(); ht.grab().save(os.path.join(OUT, f"goal_history_7{'_gold' if gold else ''}.png"))
pd._GOLD_MODE["on"] = False

# N1 goal on the chart: the top-13,800 line
goal.save("N1", datetime.date(2027, 12, 5)); CFG["jlpt_goal"]["set"] = "2026-09-20"
ht = HistoryTab(series, "D", results_fn=lambda: R); ht.resize(1000, 720); ht.show(); app.processEvents()
ht.grab().save(os.path.join(OUT, "goal_history_n1.png"))
dlg = goal_view.GoalDialog(FakeTab(R)); dlg.show(); app.processEvents(); dlg.grab().save(os.path.join(OUT, "goal_dialog_n1.png"))
goal.save("N3", datetime.date(2026, 12, 6)); CFG["jlpt_goal"]["set"] = "2026-09-20"

# share image + Nakama card
info = rank_data.get_rank_info(3000)
data = {"levels": [("N5", 600, 900), ("N4", 500, 900), ("N3", 700, 1500), ("N2", 400, 1800), ("N1", 300, 3000)],
        "freq": (5000, 20000), "info": info, "date": datetime.date(2026, 10, 20), "loyal": 6, "sun": False,
        "goal": goal.get(), "show_goal": True, "show_loyal": True}
share_card.render(data, "Ben").save(os.path.join(OUT, "goal_share.png"))
dg = dict(data, info=rank_data.get_rank_info(20000))
share_card.render(dg, "Ben", "がんばろう").save(os.path.join(OUT, "goal_share_gold.png"))
share_card.render(dict(data, show_goal=False, show_loyal=False), "Ben").save(os.path.join(OUT, "goal_share_off.png"))
sd = share_card.ShareDialog(dict(data)); sd.show(); app.processEvents(); sd.grab().save(os.path.join(OUT, "goal_share_dialog.png"))
prof = {"name": "Friend", "data": {"rank": 3000, "loyal": 6, "jlpt": {"N5": [600, 900], "N4": [400, 900]},
        "freq": [5000, 20000], "week": 40, "month": 120, "found": 12, "found_loan": 300, "goal": "N3 2026-12-06"}}
share_card.render_profile(prof, None, "synced 2 h ago").save(os.path.join(OUT, "goal_nakama.png"))
from jlpt_progress import nakama
print("nakama goal field:", nakama._goal())
CFG["share_show_goal"] = False
print("nakama goal field (unticked):", nakama._goal())
CFG["share_show_goal"] = True

# mini widget row
html = mini_widget._goal_html(results(600, 400, 309), "D", False)
html_g = mini_widget._goal_html(results(600, 400, 309), "D", True)
print("mini:", re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip(), "|",
      re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html_g)).strip())
full = mini_widget._widget_html(results(600, 400, 309), "", False, show_rank=False)
open(os.path.join(OUT, "goal_mini.html"), "w", encoding="utf-8").write(
    "<html><body style='background:#2a2a2a;margin:0;height:400px;position:relative'>" + full + "</body></html>")

print("\nFAILS:", fails or "none")
