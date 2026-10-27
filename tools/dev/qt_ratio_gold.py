exec(open("qt_overview.py", encoding="utf-8").read().split("# the \"Hide other spellings")[0].replace("for gold in (False,):", "for gold in (False,):"))
# gold mode: rank 20,000 (Amaterasu) → gold bars; the ghost in pale gold
pd.count_deck_notes = lambda d: 20000
tab = pd.OverviewTab(R, "Deck")
pd._GOLD_MODE["on"] = True
dlg = QtWidgets.QDialog(); v = QtWidgets.QVBoxLayout(dlg); v.addWidget(tab)
theme.apply(dlg, gold=True)
from jlpt_progress import divine_text
divine_text.apply(dlg, True)
dlg.resize(900, 2600); dlg.show(); app.processEvents()
inner = tab._scroll.widget(); inner.resize(880, inner.sizeHint().height()); app.processEvents()
img = inner.grab(); h = img.height(); img.copy(0, h - 1250, 880, 520).save(os.path.join(OUT, "ov_freq_gold.png"))
lbls = [w.text() for w in tab.findChildren(QtWidgets.QLabel) if "最頻出20,000語" in w.text() or "ランク：" in w.text()]
print("\n".join(lbls))
