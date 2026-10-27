exec(open("loans.py", encoding="utf-8").read().split("from jlpt_progress import jlpt_data")[0])
from jlpt_progress import history
# recorded: 5,750 a week ago (with 2,540 marks), 3,161 today after unmarking; rebuilt: marks from day one
s = {"values": {"rank": [5620, 5700, 5751, 3161]}, "gains": {"rank": [3030, 3080, 3110, 3161]}}
print("delta 1 day / 3 days:", history.delta(s, "rank", 1), history.delta(s, "rank", 3), "| since start:", history.since_start(s, "rank"), "| best week:", history.best_week(s, "rank"))
print("old cached series (no gains):", history.delta({"values": {"rank": [5751, 3161]}}, "rank", 1))
