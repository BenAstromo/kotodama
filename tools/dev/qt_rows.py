import os
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "qt_loyal.py"), encoding="utf-8").read().split("print(\"real months")[0])
from jlpt_progress import nakama_view as nv
w = QtWidgets.QWidget(); w.setStyleSheet("background: #161616; color: #e6e6e6;")
v = QtWidgets.QVBoxLayout(w)
for prof, me, dup in (({"id": "ABCDEFGH", "name": "Ben", "data": {"rank": 3000, "week": -1}}, True, False),
                      ({"id": "JKMNPQ2X", "name": "Yuki", "data": {"rank": 5200, "week": 12}}, False, True),
                      ({"id": "RSTU7Z9W", "name": "Yuki", "data": {"rank": 900, "week": 0}}, False, True)):
    v.addWidget(nv._Row(prof, me, "rank", show_code=dup))
w.resize(460, 170); w.show(); app.processEvents()
w.grab().save(os.path.join(OUT, "rows.png"))
from jlpt_progress import share_card
img = share_card.render_profile({"name": "Ben", "data": {"rank": 5750, "week": -1, "month": 131, "found": 7, "found_loan": 2583,
                                 "jlpt": {"N5": [661, 682]}}}, None, "synced just now")
img.copy(40, 560, 440, 120).save(os.path.join(OUT, "week_line.png"))
