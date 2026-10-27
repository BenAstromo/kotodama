import os, sys, datetime
exec(open("qt_goal.py", encoding="utf-8").read().split("from jlpt_progress import goal, history")[0])
from jlpt_progress import share_card, rank_data
info = rank_data.get_rank_info(3412)
data = {"levels": [("N5", 600, 900), ("N4", 500, 900), ("N3", 700, 1500), ("N2", 400, 1800), ("N1", 300, 3000)],
        "freq": (5000, 20000), "info": info, "date": datetime.date(2026, 10, 21), "loyal": 0, "sun": False,
        "goal": None, "loans": 251}
share_card.render(data, "Ben").copy(0, 330, 520, 260).save(os.path.join(OUT, "loan_share.png"))
prof = {"name": "Friend", "data": {"rank": 3412, "jlpt": {"N5": [600, 900]}, "freq": [5000, 20000],
        "week": 40, "month": 120, "found": 1, "found_loan": 251, "loan_marked": 2536}}
share_card.render_profile(prof, None, "synced").copy(0, 330, 520, 330).save(os.path.join(OUT, "loan_nakama.png"))
print("saved")
