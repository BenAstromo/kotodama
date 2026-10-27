import os, sys, re
exec(open("qt_goal.py", encoding="utf-8").read().split("from jlpt_progress import goal, history")[0])
from jlpt_progress import progress_dialog as pd
QtWidgets.QDialog.exec = lambda self: (self.show(), app.processEvents(), setattr(sys.modules[__name__], "DLG", self))[-1]
for gold in (False, True):
    pd._GOLD_MODE["on"] = gold
    pd._show_rank_info_dialog(None)
    labels = [w.text() for w in DLG.findChildren(QtWidgets.QLabel)]
    t = next(x for x in labels if "N2" in x and ("fall short" in x or "足りません" in x))
    m = re.search(r"(Up to N3.*?three|N3までは.*?大切です。)", re.sub(r"<[^>]+>", "", t), re.S)
    para = re.sub(r"<[^>]+>", "", t)
    i = para.find("Up to N3") if not gold else para.find("N3までは")
    print(("GOLD: " if gold else "EN: ") + " ".join(para[i:i + 700].split()))
    DLG.close()
