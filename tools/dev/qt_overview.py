import os, sys, datetime
exec(open("qt_goal.py", encoding="utf-8").read().split("from jlpt_progress import goal, history")[0])
from jlpt_progress import progress_dialog as pd, card_state, goal, history, theme
history.today = lambda: datetime.date(2026, 10, 20)
goal._DAYS_PATH = os.path.join(OUT, "goal_days_ov.json")
pd.count_deck_notes = lambda d: 5750
card_state.debug_count_all = lambda: False
def words(n, tag): return [(f"{tag}{i}", "", i) for i in range(n)]
def miss(n, tag): return [(f"{tag}{i}", "") for i in range(n)]
R = {l: {"known_words": words(k, l), "missing_words": miss(t - k, l + "m")}
     for l, k, t in (("N5", 600, 700), ("N4", 400, 650), ("N3", 300, 1600), ("N2", 50, 1800), ("N1", 10, 3000))}
R["frequency"] = {"available": True, "tiers": [(800, 500), (1500, 900), (3900, 2000), (6000, 2600), (13800, 4000), (20000, 5000)],
                  "tier_totals": {n: n for n in (800, 1500, 3900, 6000, 13800, 20000)}, "notes_in_top": {20000: 2800},
                  "notes_total": 3000, "text_coverage": 0.8, "missing": [(5, "東京", "とうきょう")], "entries": [],
                  "found_ranks": set(), "known_nids": {}, "suspended_ranks": set()}
goal.save("N2", datetime.date(2027, 7, 4))
for gold in (False,):
    try:
        tab = pd.OverviewTab(R, "Deck")
    except Exception:
        import traceback; traceback.print_exc(); raise SystemExit
    dlg = QtWidgets.QDialog(); v = QtWidgets.QVBoxLayout(dlg); v.addWidget(tab)
    theme.apply(dlg, gold=False)
    dlg.resize(900, 2600); dlg.show(); app.processEvents()
    inner = tab._scroll.widget(); inner.resize(880, inner.sizeHint().height()); app.processEvents()
    inner.grab().save(os.path.join(OUT, "overview.png"))
    print("saved", inner.height())
# the "Hide other spellings…" checkbox (owner 2026-10-20)
R["frequency"]["missing"] = [(5, "東京", "とうきょう"), (40, "在る", "ある"), (60, "私", "わたくし")]
R["frequency"]["missing_lean"] = [(5, "東京", "とうきょう")]
tab2 = pd.OverviewTab(R, "Deck")
cb = next(c for c in tab2.findChildren(QtWidgets.QCheckBox) if c.text().startswith("Hide other"))
lw = [w for w in tab2.findChildren(QtWidgets.QListWidget) if w.property("jlpt_gold_list")][0]
print("off:", lw.count(), "| checked saved:", CFG.get("freq_hide_variants"))
cb.setChecked(True); print("on:", lw.count(), "| saved:", CFG.get("freq_hide_variants"))
tab3 = pd.OverviewTab(R, "Deck")
cb3 = next(c for c in tab3.findChildren(QtWidgets.QCheckBox) if c.text().startswith("Hide other"))
lw3 = [w for w in tab3.findChildren(QtWidgets.QListWidget) if w.property("jlpt_gold_list")][0]
print("remembered after rebuild:", cb3.isChecked(), lw3.count())
cb3.setChecked(False); print("off again:", lw3.count(), CFG.get("freq_hide_variants"))
