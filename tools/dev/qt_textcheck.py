import os, sys, re
exec(open("qt_goal.py", encoding="utf-8").read().split("from jlpt_progress import goal, history")[0])
from jlpt_progress import progress_dialog as pd, theme, divine_text
from jlpt_progress.text_check_view import TextCheckTab
text = ("昨日は雨が降っていたので、家で本を読んでいました。友達に会うわけにはいかなかったけれど、"
        "電話で話すことができました。経済の発展に伴い、生活は便利になりつつある。"
        "彼は約束を守るに違いない。雨が降ったら、試合は中止になるそうです。")
RES = {"kanji": {"known": set("昨日雨降家本読友達会話電")}, "grammar": {"known": {"te-iru", "node", "koto-ga-dekiru"}}}
for gold in (False, True):
    pd._GOLD_MODE["on"] = gold
    tab = TextCheckTab(lambda: RES)
    dlg = QtWidgets.QDialog(); v = QtWidgets.QVBoxLayout(dlg); v.addWidget(tab)
    theme.apply(dlg, gold=gold)
    dlg.resize(1000, 760); dlg.show(); app.processEvents()
    tab._edit.setPlainText(text); tab._check()
    if gold: divine_text.apply(dlg, True)
    for kind in (2, 1):
        tab._kind.setCurrentIndex(kind); app.processEvents()
        name = ["vocab", "kanji", "grammar"][kind]
        dlg.grab().save(os.path.join(OUT, f"tc_{name}{'_gold' if gold else ''}.png"))
        print(("GOLD " if gold else "") + name, tab._table.rowCount(), "rows | headers:",
              [tab._table.horizontalHeaderItem(c).text() for c in range(5)], "| show:", tab._show.currentText(), "| copy:", tab._copy_btn.text())
    print("summary:", re.sub(r"<[^>]+>|&nbsp;", " ", tab._kg.text()))
    tab._show.setCurrentIndex(1); app.processEvents(); print("all rows (kanji):", tab._table.rowCount())
