"""
goal_view.py
The JLPT goal (goal.py) on the Overview: a card under the JLPT Vocabulary
bars with the test, the days left and the daily numbers for words, kanji
and grammar (the one place that shows all three), and the dialog that
sets it (level + one of the next test dates, or another date).
"""

from __future__ import annotations

import datetime

from aqt.qt import *

from . import goal
from .jlpt_data import LEVELS, LEVEL_COLORS
from .theme import BODY_CSS, HINT_CSS

DONE_COLOR = "#7bd88f"        # today's share of this kind is learned
TIGHT_COLOR = "#ffb74d"
UNITS = {"vocab": ("word", "words"), "kanji": ("kanji", "kanji"),
         "grammar": ("grammar point", "grammar points")}


def _unit(kind: str, n: int) -> str:
    one, many = UNITS[kind]
    return one if n == 1 else many


def _num(n: int, color: str = None) -> str:
    style = f" style='color:{color};'" if color else ""
    return f"<b{style}>{n:,}</b>"


def _label(text: str, css: str = BODY_CSS) -> QLabel:
    lbl = QLabel(text)
    lbl.setWordWrap(True)
    lbl.setStyleSheet(css)
    return lbl


def add_goal_card(page: QVBoxLayout, tab) -> None:
    """The goal card (tab = the OverviewTab, which rebuilds on a change)."""
    from .progress_dialog import _section_card
    outer = _section_card(page)
    head = QHBoxLayout()
    title = QLabel("<b>JLPT Goal</b>")
    from .theme import SECTION_CSS
    title.setStyleSheet(SECTION_CSS)
    head.addWidget(title)
    head.addStretch()
    try:
        st = goal.status(tab._results, tab._deck_name)
    except Exception:
        # A goal problem must never stop the window from opening (owner's
        # crash 2026-10-20): print it, show the card without numbers.
        import traceback
        traceback.print_exc()
        st = None
    btn = QPushButton("Set a JLPT goal…" if st is None
                      else "Set your next goal…" if st["phase"] == "past" else "Change…")
    btn.clicked.connect(lambda: _open_dialog(tab))
    head.addWidget(btn)
    outer.addLayout(head)
    card = outer
    outer = QVBoxLayout()               # the lines below sit closer together than the card's sections
    outer.setSpacing(4)
    card.addLayout(outer)

    if st is None:
        outer.addWidget(_label("Taking the JLPT? Pick your level and test date, and Kotodama "
                               "works out how much to learn each day.", HINT_CSS))
        return

    lvl, color = st["level"], LEVEL_COLORS[st["level"]]
    date = goal.fmt_date(st["date"])
    if st["phase"] == "past":
        outer.addWidget(_label(f"Your JLPT {lvl} test was on {date}. How did it go?"))
        return

    if st["phase"] == "plan":
        line = (f"<b style='color:{color};'>JLPT {lvl}</b> · {date} · "
                f"<b>{st['days_left']:,}</b> {'day' if st['days_left'] == 1 else 'days'} left to learn")
    else:
        line = (f"<b style='color:{color};'>JLPT {lvl}</b> · {date} · "
                f"<b>{st['test_days']:,}</b> {'day' if st['test_days'] == 1 else 'days'} to the test")
    outer.addWidget(_label(line))

    kinds = st["kinds"]
    if st["phase"] == "done":
        outer.addWidget(_label(f"Everything up to {lvl} is learned. The rest is review."))
    elif st["phase"] == "review":
        outer.addWidget(_label("Review time: the last two weeks before the test are for "
                               "review and practice tests."))
        left = [f"{_num(k['left'])} {_unit(kind, k['left'])}"
                for kind, k in kinds.items() if k["left"]]
        if left:
            outer.addWidget(_label("Still to learn: " + " · ".join(left)))
        _add_waiting_line(outer, kinds)
        for line in _step_lines(st):
            outer.addWidget(_label(line))
    else:
        per, today, left = [], [], []
        from .history_view import gain_link
        text = QApplication.palette().color(QPalette.ColorRole.WindowText).name()
        for kind, k in kinds.items():
            c = DONE_COLOR if goal.done_today(k) else None
            per.append(f"{_num(k['per_day'], c)} {_unit(kind, k['per_day'])}")
            # a link: today's new cards of this kind in the Browser
            today.append(gain_link(f"today:{kind}", f"{_num(k['today'], c)} / {k['per_day']:,} "
                                   f"{_unit(kind, k['per_day'])}", text))
            left.append(f"{_num(k['left'])} {_unit(kind, k['left'])}")
        per_lbl = _label("Per day: " + " · ".join(per))
        per_lbl.setStyleSheet(BODY_CSS + " font-size: 15px;")
        outer.addWidget(per_lbl)
        today_lbl = _label("Today: " + " · ".join(today))
        today_lbl.setToolTip("Click a number for the Progress Review: what you learned today and "
                             "this week, each card a click away.")
        _connect_today(today_lbl, tab, lvl)
        outer.addWidget(today_lbl)
        outer.addWidget(_label("Still to learn: " + " · ".join(left), HINT_CSS))
        _add_waiting_line(outer, kinds)
        for line in _step_lines(st):
            outer.addWidget(_label(line))
        vocab = kinds.get("vocab")
        if vocab and vocab["per_day"]:
            _name, line = goal.pace(vocab["per_day"], st["days_left"], st["finish"])
            if st["tight"]:
                alt = goal.instead(vocab["left"], st["date"])
                outer.addWidget(_label(
                    f"<span style='color:{TIGHT_COLOR};'>{line}{' ' + alt if alt else ''}</span>"))
            else:
                outer.addWidget(_label(line, HINT_CSS))
        outer.addWidget(_label(_words_note(lvl), HINT_CSS))
        outer.addWidget(_label("The finish line is 14 days before the test: the last two weeks "
                               "are for review and practice tests. Fall behind and the daily "
                               "number goes up; get ahead and it goes down.", HINT_CSS))


def _connect_today(lbl: QLabel, tab, lvl: str):
    """The "Today" numbers' links: the notes first studied today (the
    rebuilt history's dates) of the goal's words / kanji / grammar."""
    lbl.setTextInteractionFlags(Qt.TextInteractionFlag.LinksAccessibleByMouse)
    lbl.setOpenExternalLinks(False)

    def activated(href: str):
        if not href.startswith("today:"):
            return
        from .review_view import open_from
        if open_from(lbl, 7):                   # the Progress Review (owner 2026-10-27)
            return
        from .history_view import open_gained
        kind = href.split(":", 1)[1]
        open_gained(tab._results.get("history_series"),
                    goal.today_parts(tab._results, lvl, kind), 0, lbl)
    lbl.linkActivated.connect(activated)


def _words_note(lvl: str) -> str:
    """Which words the goal counts, for the card (owner 2026-10-20)."""
    top = goal.vocab_source(lvl)
    if top:
        return (f"Why two steps: the JLPT word lists hold the words most likely on the test, so they "
                f"come first. {lvl} also asks for about {top:,} words in all, so the rest comes from "
                f"the most common words of written Japanese, which matter more at N2 and N1.")
    return f"Words: the JLPT word lists up to {lvl} (the JLPT Vocabulary bars above)."


def _add_waiting_line(outer, kinds: dict):
    """Under "Still to learn": the marked English loanwords it leaves out
    (goal.counts' "waiting", owner 2026-10-28)."""
    w = (kinds.get("vocab") or {}).get("waiting", 0)
    if w:
        outer.addWidget(_label(f"Not included: {w:,} English loanwords you marked found. "
                               f"They join on their own as your card count grows.", HINT_CSS))


def _step_lines(st: dict) -> list:
    """N2 / N1: "Step 1 · JLPT word lists up to N2: 3,100 / 4,853 …" and
    "Step 2 · then common words not on the lists: 0 / 1,147 …"."""
    steps = st.get("steps")
    if not steps:
        return []
    (k1, n1), (k2, n2) = steps["lists"], steps["common"]
    c1 = DONE_COLOR if k1 >= n1 else None
    c2 = DONE_COLOR if k2 >= n2 else None
    return [f"Step 1 · JLPT word lists up to {st['level']}: {_num(k1, c1)} / {n1:,} "
            f"(the JLPT Vocabulary bars and grids)",
            f"Step 2 · then common words not on the lists: {_num(k2, c2)} / {n2:,} "
            f"(the Frequency grid, most common first)"]


WORDS_EXPLAINED = (
    "Which words count: for N5 to N3, the JLPT word lists (the JLPT Vocabulary bars). For N2 and "
    "N1 the goal is the modern vocabulary size, about 6,000 words for N2 and 13,800 for N1, in two "
    "steps: first every word on the JLPT lists up to that level, since those are the words most "
    "likely on the test; then the rest from the most common words of written Japanese that aren't "
    "on the lists (the Frequency grid). The JLPT hasn't published word lists since 2010; ours build "
    "on the old pre-2010 lists, which are close enough up to N3 but stop well short of N2 and N1 "
    "(about 8,000 words up to N1). Written Japanese matters more at N2 and N1, whose reading "
    "sections are newspaper-style articles and essays, and these are the levels employers and "
    "schools rely on. Kanji and grammar always use the JLPT lists.")


def _open_dialog(tab):
    dlg = GoalDialog(tab)
    if dlg.exec():
        tab.goal_changed.emit()


class GoalDialog(QDialog):
    """Level + test date. Shows what that means per day before saving."""

    def __init__(self, tab):
        super().__init__(tab)
        self._tab = tab
        self.setWindowTitle("JLPT Goal")
        self.setMinimumWidth(460)
        v = QVBoxLayout(self)
        v.addWidget(_label("Which JLPT are you taking, and when? The test covers every level "
                           "up to yours, so N3 means N5, N4 and N3.", HINT_CSS))
        old = goal.get()
        if old is not None and old["date"] < goal._today():
            old = {"level": old["level"], "date": None}

        form = QGridLayout()
        form.addWidget(QLabel("Level:"), 0, 0)
        self._level = QComboBox()
        for lvl in LEVELS:
            self._level.addItem(lvl)
        self._level.setCurrentText(old["level"] if old else "N3")
        form.addWidget(self._level, 0, 1)

        form.addWidget(QLabel("Test date:"), 1, 0)
        self._date = QComboBox()
        self._dates = goal.test_dates(goal._today())
        for d in self._dates:
            self._date.addItem(goal.fmt_date(d))
        self._date.addItem("Other date…")
        form.addWidget(self._date, 1, 1)
        self._other = QDateEdit()
        self._other.setCalendarPopup(True)
        self._other.setDisplayFormat("yyyy-MM-dd")
        t = goal._today()
        self._other.setMinimumDate(QDate(t.year, t.month, t.day))
        nd = self._dates[0]
        self._other.setDate(QDate(nd.year, nd.month, nd.day))
        form.addWidget(self._other, 2, 1)
        if old and old.get("date"):
            if old["date"] in self._dates:
                self._date.setCurrentIndex(self._dates.index(old["date"]))
            else:
                self._date.setCurrentIndex(len(self._dates))
                od = old["date"]
                self._other.setDate(QDate(od.year, od.month, od.day))
        form.setColumnStretch(1, 1)
        v.addLayout(form)
        v.addWidget(_label(WORDS_EXPLAINED, HINT_CSS))

        self._preview = _label("")
        v.addWidget(self._preview)

        btns = QHBoxLayout()
        if goal.get() is not None:
            remove = QPushButton("Remove goal")
            remove.clicked.connect(self._remove)
            btns.addWidget(remove)
        btns.addStretch()
        save = QPushButton("Save")
        save.setDefault(True)
        save.clicked.connect(self._save)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        btns.addWidget(save)
        btns.addWidget(cancel)
        v.addLayout(btns)

        self._level.currentIndexChanged.connect(self._update)
        self._date.currentIndexChanged.connect(self._update)
        self._other.dateChanged.connect(self._update)
        self._update()

        from .progress_dialog import _GOLD_MODE
        from . import theme
        theme.apply(self, gold=_GOLD_MODE["on"])
        if _GOLD_MODE["on"]:
            from . import divine_text
            self.setWindowTitle("JLPT目標")
            divine_text.gold_palette(self, True)
            divine_text.apply(self, True)
            divine_text.gold_titlebar(self, True)

    def _chosen(self) -> datetime.date:
        i = self._date.currentIndex()
        if i < len(self._dates):
            return self._dates[i]
        q = self._other.date()
        return datetime.date(q.year(), q.month(), q.day())

    def _update(self, *_):
        self._other.setVisible(self._date.currentIndex() == len(self._dates))
        lvl, d = self._level.currentText(), self._chosen()
        finish = d - datetime.timedelta(days=goal.BUFFER_DAYS)
        days = (finish - goal._today()).days + 1
        try:
            cs = goal.counts(self._tab._results, lvl)
        except Exception:
            import traceback
            traceback.print_exc()
            cs = {}
        c = cs.get("vocab")
        # waiting English loanwords join on their own (goal.counts)
        left = c[1] - c[0] - cs.get("waiting", 0) if c else 0
        if c is None:
            text = ""
        elif left <= 0:
            text = f"You already know every word up to {lvl}."
        elif days <= 0:
            text = (f"{left:,} words still to learn, and the test is less than "
                    f"{goal.BUFFER_DAYS} days away: there's no time left before the finish line.")
        else:
            per = -(-left // days)
            text = (f"{left:,} words still to learn: about <b>{per:,}</b> a day "
                    f"until {goal.fmt_date(finish)}, 14 days before the test.")
            _name, line = goal.pace(per, days, finish)
            if per > goal.TIGHT_PER_DAY:
                alt = goal.instead(left, d)
                text += f"<br><span style='color:{TIGHT_COLOR};'>{line}{' ' + alt if alt else ''}</span>"
            else:
                text += f"<br>{line}"
        steps = cs.get("steps")
        if text and steps and left > 0:
            (k1, n1), (k2, n2) = steps["lists"], steps["common"]
            text += (f"<br>Step 1, JLPT word lists: {n1 - k1:,} to go · "
                     f"step 2, common words: {n2 - k2:,} to go.")
        self._preview.setText(text)
        from .progress_dialog import _regold
        _regold(self._preview, self._other)

    def _save(self):
        goal.save(self._level.currentText(), self._chosen())
        self.accept()

    def _remove(self):
        goal.save(None)
        self.accept()
