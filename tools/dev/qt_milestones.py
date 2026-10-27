import os, sys, re
exec(open("qt_goal.py", encoding="utf-8").read().split("from jlpt_progress import goal, history")[0])
from jlpt_progress import progress_dialog as pd
QtWidgets.QDialog.exec = lambda self: (self.show(), app.processEvents(), setattr(sys.modules[__name__], "DLG", self))[-1]
for gold in (False, True):
    pd._GOLD_MODE["on"] = gold
    pd._show_rank_info_dialog(None)
    t = " ".join(re.sub(r"<[^>]+>|&nbsp;", " ", w.text()) for w in DLG.findChildren(QtWidgets.QLabel))
    i = t.find("Cumulative: each") if not gold else t.find("累計です。各節目")
    print(("EN: " if not gold else "JA: ") + " ".join(t[i:i + 260].split()))
    DLG.grab().save(os.path.join(OUT, f"milestones{'_gold' if gold else ''}.png"))
    DLG.close()
