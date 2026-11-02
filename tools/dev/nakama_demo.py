"""Fake Nakama friends for screenshots (owner 2026-11-02).

    python tools/dev/nakama_demo.py          write user_files/nakama_demo.json
    python tools/dev/nakama_demo.py --clear  delete it

nakama.demo_members() lists these after your real friends. They're local
only: never sent to the server, fetched or synced. Reopen the Kotodama
window (or press Refresh on the Nakama tab) to see them.
"""

import json
import os
import sys
import time

ADDON = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PATH = os.path.join(ADDON, "user_files", "nakama_demo.json")

LEVEL_SIZES = {"N5": 686, "N4": 704, "N3": 2031, "N2": 2575, "N1": 3800}
KANJI_SIZES = {"N5": 84, "N4": 169, "N3": 387, "N2": 398, "N1": 1345}
GRAMMAR_SIZES = {"N5": 81, "N4": 98, "N3": 101, "N2": 123, "N1": 123}

# name, rank (learned words), week, month, hours since sync, goal
PEOPLE = [
    ("Mochi_Reads",   7420, 168, 610,   2, "N1 2027-07-04"),
    ("kenta.jp",      4630, 95,  402,   5, "N2 2027-07-04"),
    ("NihongoNate",   2980, 211, 744,   1, "N2 2026-12-06"),
    ("Sakura_Study",  1890, 57,  233,  20, "N3 2026-12-06"),
    ("yuzu",          1120, 132, 498,   3, "N3 2027-07-04"),
    ("TofuTimmy",      640, 74,  260,  30, "N4 2026-12-06"),
    ("lin_learns",     310, 41,  150,  48, "N5 2026-12-06"),
]


# How fast each level fills as the word count grows: known = size ×
# (1 − e^(−rank / T)), T fitted on the owner's own numbers (rank 3,672:
# N5 95 %, N4 86 %, N3 44 %, N2 16 %, N1 11 %; kanji and grammar likewise).
WORDS_T = {"N5": 1230, "N4": 1870, "N3": 6340, "N2": 21000, "N1": 31500}
KANJI_T = {"N5": 600, "N4": 800, "N3": 1230, "N2": 2800, "N1": 11200}
GRAMMAR_T = {"N5": 1520, "N4": 2000, "N3": 5800, "N2": 26000, "N1": 108000}


def _fill(sizes: dict, spans: dict, rank: int) -> dict:
    import math
    return {lvl: [round(n * (1 - math.exp(-rank / spans[lvl]))), n] for lvl, n in sizes.items()}


def profile(i: int, name: str, rank: int, week: int, month: int, hours: int, goal: str) -> dict:
    jlpt = _fill(LEVEL_SIZES, WORDS_T, rank)
    kanji = _fill(KANJI_SIZES, KANJI_T, rank)
    grammar = _fill(GRAMMAR_SIZES, GRAMMAR_T, rank)
    kanji["All"] = [sum(k for k, _ in kanji.values()), sum(KANJI_SIZES.values())]
    grammar["All"] = [sum(k for k, _ in grammar.values()), sum(GRAMMAR_SIZES.values())]
    return {"id": f"DEMO{i:04d}", "name": name, "supporter": None,
            "updated": int(time.time()) - hours * 3600,
            "data": {"v": 1, "rank": rank, "loan_marked": 0, "found": 0, "found_loan": 0,
                     "loyal": 1, "sun": False, "goal": goal, "week": week, "month": month,
                     "jlpt": jlpt, "freq": [int(rank * 0.82), 20000],
                     "kanji": kanji, "grammar": grammar}}


def main():
    if "--clear" in sys.argv:
        if os.path.exists(PATH):
            os.remove(PATH)
        print("removed", PATH)
        return
    os.makedirs(os.path.dirname(PATH), exist_ok=True)
    with open(PATH, "w", encoding="utf-8") as f:
        json.dump([profile(i, *p) for i, p in enumerate(PEOPLE, 1)], f, ensure_ascii=False, indent=1)
    print(f"wrote {len(PEOPLE)} demo friends to {PATH}")


if __name__ == "__main__":
    main()
