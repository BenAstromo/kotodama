import os, sys, re
exec(open("qt_goal.py", encoding="utf-8").read().split("from jlpt_progress import goal, history")[0])
from jlpt_progress import progress_dialog as pd
QtWidgets.QDialog.exec = lambda self: (self.show(), app.processEvents(), setattr(sys.modules[__name__], "DLG", self))[-1]
for gold in (False, True):
    pd._GOLD_MODE["on"] = gold
    pd._show_loanword_info_dialog(None)
    texts = [w.text() for w in DLG.findChildren(QtWidgets.QLabel)]
    eng = [t for t in texts if re.search(r"[A-Za-z]{4,}", re.sub(r"<[^>]+>", "", t)) and gold]
    print("gold" if gold else "normal", "labels:", len(texts), "| still English in gold:", [e[:60] for e in eng])
    DLG.grab().save(os.path.join(OUT, f"loanhelp{'_gold' if gold else ''}.png")); DLG.close()
