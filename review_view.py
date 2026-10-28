"""
review_view.py
The Progress Review window (review.py; owner 2026-10-27, mock-up A): today on
the left (words, kanji, grammar), the last 7 or 30 days on the right
(totals, pace, a bar per day, then words by day, kanji, grammar).

Everything is a link to the Browser (owner): a heading opens everything
under it (Today → all of today's cards, Words · 12 → today's words), an
item opens just its own card, a day line or bar that day's. No buttons.

Opened by the goal card's "Today" (goal_view; the +N today / week / month
links open the Browser instead, owner 2026-10-28) and, once a day, by itself when the word
target is reached (ProgressDialog). One window per main window: opening it
again rebuilds it.
"""

from __future__ import annotations

import html

from aqt.qt import *

from . import review
from .jlpt_data import LEVEL_COLORS
from .theme import BODY_CSS, HINT_CSS, SECTION_CSS

KANJI_COLOR = "#4fc3a1"          # the share card's kanji / grammar bar colours (owner 2026-10-28)
GRAMMAR_COLOR = "#a493f0"
ALL_COLOR = "#ffffff"            # words without a goal
DIM_BAR = "#4a2a2a"              # a day under the word target
DIM_GOLD = "#4a3c10"
DAY_WORDS = 10                   # words shown on a day line before "…"
HOVER = "rgba(255,255,255,0.07)"


def _gold() -> bool:
    from .progress_dialog import _GOLD_MODE
    return bool(_GOLD_MODE["on"])


def _c(color: str) -> str:
    """A colour, or gold in Amaterasu mode (gold, black and white only)."""
    if _gold():
        from .divine_text import GOLD
        return GOLD
    return color


def open_nids(nids, parent=None):
    """These notes in Anki's Browser, or a tooltip when there are none."""
    from aqt import mw, dialogs
    from aqt.utils import tooltip
    nids = list(dict.fromkeys(n for n in nids if n is not None))
    if not nids:
        tooltip("No cards here (words marked found have none).", parent=parent)
        return
    b = dialogs.open("Browser", mw)
    b.search_for("nid:" + ",".join(str(n) for n in nids))


def _nids(*lists) -> list:
    return [x["nid"] for items in lists for x in items]


class _Hover(QObject):
    """Clickable labels: a hand cursor, a faint highlight on hover (a
    property the window's style sheet keys on, so a label's own style,
    gold included, is untouched), a click calls the label's _rv_click."""

    def eventFilter(self, obj, ev):
        t = ev.type()
        if t in (QEvent.Type.Enter, QEvent.Type.Leave):
            obj.setProperty("rvhover", t == QEvent.Type.Enter)
            obj.style().unpolish(obj)
            obj.style().polish(obj)
        elif (t == QEvent.Type.MouseButtonRelease and ev.button() == Qt.MouseButton.LeftButton
              and obj.rect().contains(ev.position().toPoint())):
            fn = getattr(obj, "_rv_click", None)
            if fn:
                fn()
            return True
        return False


def _label(text: str, css: str = BODY_CSS, wrap: bool = False) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(css)
    lbl.setWordWrap(wrap)
    return lbl


class ReviewWindow(QDialog):
    def __init__(self, parent, results: dict, deck: str, days_back: int = 7):
        super().__init__(parent)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.Window
                            | Qt.WindowType.WindowMinMaxButtonsHint
                            | Qt.WindowType.WindowCloseButtonHint)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setWindowTitle("Progress Review")
        self._hover = _Hover(self)
        self._data = review.build(results, deck, days_back)
        self._days_back = days_back
        self.resize(1060, 860)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 16, 20, 12)
        outer.setSpacing(8)
        self._header(outer)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        body = QWidget()
        body.setObjectName("rvbody")
        row = QHBoxLayout(body)
        row.setContentsMargins(0, 0, 6, 0)
        row.setSpacing(14)
        cols = []
        for stretch in (11, 10):
            w = QWidget()
            # The stretch alone sets the widths (a long line wraps instead
            # of widening its column).
            w.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            c = QVBoxLayout(w)
            c.setContentsMargins(0, 0, 0, 0)
            c.setSpacing(10)
            row.addWidget(w, stretch, Qt.AlignmentFlag.AlignTop)
            cols.append(c)
        if self._data:
            self._today(cols[0])
            self._period(cols[1])
        scroll.setWidget(body)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        outer.addWidget(scroll, 1)
        outer.addWidget(_label("Click any heading or item to see its cards in the Browser.", HINT_CSS))

        from . import theme
        gold = _gold()
        theme.apply(self, gold=gold)
        self.setStyleSheet(self.styleSheet()
                           + f"\nQLabel[rvhover=\"true\"], QWidget#rvline[rvhover=\"true\"] "
                             f"{{ background: {HOVER}; border-radius: 4px; }}"
                           + "\nQWidget#rvbody { background: transparent; }"
                           + "\nQScrollArea { background: transparent; }"
                           + "\nQScrollArea > QWidget > QWidget { background: transparent; }")
        if gold:
            from . import divine_text
            self.setWindowTitle("振り返り")
            divine_text.gold_palette(self, True)
            divine_text.apply(self, True)
            divine_text.gold_titlebar(self, True)
        theme.fit_on_screen(self)

    # ── pieces ────────────────────────────────────────────────────────────

    def _click(self, lbl: QLabel, fn, tip: str = "") -> QLabel:
        lbl._rv_click = fn
        lbl.setCursor(Qt.CursorShape.PointingHandCursor)
        lbl.installEventFilter(self._hover)
        if tip:
            lbl.setToolTip(tip)
        return lbl

    def _open(self, items_or_nids) -> callable:
        nids = list(items_or_nids)
        return lambda: open_nids(nids, self)

    def _card(self, col: QVBoxLayout) -> QVBoxLayout:
        from .progress_dialog import _section_card
        lay = _section_card(col)
        lay.setSpacing(6)
        return lay

    def _heading(self, lay, text: str, color: str, nids, tip: str):
        h = _label(text, SECTION_CSS + f" color: {_c(color)};")
        lay.addWidget(self._click(h, self._open(nids), tip))

    def _header(self, outer: QVBoxLayout):
        d = self._data
        top = QHBoxLayout()
        top.setSpacing(10)
        top.addWidget(_label("Progress Review", f"font-size: 22px; color: {_c('#ffffff')};"))
        sub = _label("振り返り", f"font-size: 14px; color: {_c('#d4a017')};")
        sub.setProperty("jlpt_gold_skip", True)
        if not _gold():
            top.addWidget(sub, 0, Qt.AlignmentFlag.AlignBottom)
        top.addStretch()
        outer.addLayout(top)
        if not d:
            outer.addWidget(_label("No history yet: the review fills in as you study.", HINT_CSS))
            return
        st = d["goal"]
        line = QHBoxLayout()
        line.setSpacing(10)
        from . import goal
        today = goal.today_line(st, ja=_gold()) if st else None
        if today:
            v = st["kinds"]["vocab"]
            color = LEVEL_COLORS[st["level"]]
            line.addWidget(_label(today, f"font-size: 15px; color: {_c(color)};"))
            if goal.done_today(v) and v["per_day"]:
                line.addWidget(_label("Goal reached", f"font-size: 15px; color: {_c('#7bd88f')};"))
        else:
            n = len(review.on_day(d["words"] + d["words_out"], len(d["days"]) - 1))
            line.addWidget(_label(f"+{n:,} word today" if n == 1 else f"+{n:,} words today",
                                  f"font-size: 15px; color: {_c('#ffffff')};"))
        if st:
            line.addWidget(_label(goal.aiming_line(st, ja=_gold()), HINT_CSS))
        line.addStretch()
        outer.addLayout(line)

    def _word_color(self) -> str:
        lvl = self._data["level"]
        return LEVEL_COLORS[lvl] if lvl else ALL_COLOR

    def _outside_line(self, lay, items: list, kind: str):
        """"+3 words outside your N2 goal" (a link to them all)."""
        if not items:
            return
        n, lvl = len(items), self._data["level"]
        unit = {"words": ("word", "words"), "kanji": ("kanji", "kanji"),
                "grammar": ("grammar point", "grammar points")}[kind][n != 1]
        text = (f"+{n:,} {unit} outside your {lvl} goal" if lvl
                else f"+{n:,} {unit} on no JLPT list")
        head = _label(text, HINT_CSS)
        self._click(head, self._open(_nids(items)), "Open them all in the Browser")
        lay.addWidget(head)

    def _word_row(self, x: dict) -> QLabel:
        reading = x["reading"] if x["reading"] and x["reading"] != x["text"] else ""
        meaning = ""
        from . import meanings
        hit = meanings.lookup(x["text"], x["reading"])
        if hit and hit[1] and not _gold():
            meaning = hit[1][0][1]
            if len(meaning) > 48:
                meaning = meaning[:46] + "…"
        lbl = QLabel(f"<span style='font-size:17px; color:{_c('#ffffff')};'>{html.escape(x['text'])}</span>"
                     f"&nbsp;&nbsp;<span style='color:{_c('#aaaaaa')}; font-size:12px;'>{html.escape(reading)}</span>"
                     f"&nbsp;&nbsp;<span style='color:#888888; font-size:12px;'>{html.escape(meaning)}</span>")
        lbl.setWordWrap(True)
        lbl.setProperty("jlpt_gold_skip", True)
        tip = self._level_tip(x) + meanings.tooltip_html(x["text"], x["reading"])
        return self._click(lbl, self._open([x["nid"]]), tip)

    def _level_tip(self, x: dict) -> str:
        """The hover's first line (owner 2026-10-28): the word's JLPT level,
        or its frequency rank for a goal's step-2 word."""
        if x.get("level"):
            return (f"<b style='color:{_c(LEVEL_COLORS[x['level']])};'>{x['level']}</b>"
                    "<br>")
        if x.get("rank"):
            if _gold():
                return f"<b>よく使われる語 #{x['rank']:,}</b>（JLPTリスト外）<br>"
            return f"<b>Common word #{x['rank']:,}</b> (not on the JLPT lists)<br>"
        return "<b>JLPTリスト外</b><br>" if _gold() else "<b>Not on the JLPT lists</b><br>"

    def _kanji_line(self, lay, items: list, big: bool):
        """The kanji in one wrapping line, each a link (its hover: where it
        was learned)."""
        size = 26 if big else 24
        parts = []
        for i, x in enumerate(items):
            frm = (f"<span style='color:#888888; font-size:12px;'> {html.escape(x['from'])}</span>"
                   if big and x["from"] else "")
            parts.append(f"<a href='{i}' style='color:{_c(KANJI_COLOR)}; text-decoration:none; "
                         f"font-size:{size}px;'>{html.escape(x['text'])}</a>{frm}")
        lbl = QLabel(("&nbsp;&nbsp;&nbsp;" if big else "&nbsp;&nbsp;").join(parts))
        lbl.setWordWrap(True)
        lbl.setProperty("jlpt_gold_skip", True)
        lbl.linkActivated.connect(lambda href: open_nids([items[int(href)]["nid"]], self))

        def hovered(href):
            if not href:
                QToolTip.hideText()
                return
            x = items[int(href)]
            bits = [x["level"] or ""] + ([f"learned from {x['from']}"] if x["from"] else [])
            QToolTip.showText(QCursor.pos(), f"{x['text']}  " + " · ".join(b for b in bits if b))
        lbl.linkHovered.connect(hovered)
        lay.addWidget(lbl)

    def _grammar_row(self, x: dict, sentence: bool) -> QLabel:
        mean = "" if _gold() else html.escape(x["meaning"])
        text = (f"<span style='color:{_c(GRAMMAR_COLOR)}; font-size:15px; font-weight:600;'>"
                f"{html.escape(x['pattern'])}</span>&nbsp;&nbsp;"
                f"<span style='color:#888888; font-size:12px;'>{mean}</span>")
        if sentence and x["sentence"]:
            s, out, pos = x["sentence"], [], 0
            for a, b in x["spans"]:
                if a < pos:
                    continue
                out.append(html.escape(s[pos:a]))
                out.append(f"<span style='color:{_c(GRAMMAR_COLOR)}; text-decoration:underline;'>"
                           f"{html.escape(s[a:b])}</span>")
                pos = b
            out.append(html.escape(s[pos:]))
            text += f"<br><span style='font-size:16px; color:{_c('#cccccc')};'>{''.join(out)}</span>"
        lbl = QLabel(text)
        lbl.setWordWrap(True)
        lbl.setProperty("jlpt_gold_skip", True)
        tip = "Open the card with this sentence in the Browser" if sentence else "Open its card in the Browser"
        return self._click(lbl, self._open([x["nid"]]), tip)

    # ── today ─────────────────────────────────────────────────────────────

    def _today(self, col: QVBoxLayout):
        d = self._data
        t = len(d["days"]) - 1
        w, wo = review.on_day(d["words"], t), review.on_day(d["words_out"], t)
        k, ko = review.on_day(d["kanji"], t), review.on_day(d["kanji_out"], t)
        g, go = review.on_day(d["grammar"], t), review.on_day(d["grammar_out"], t)
        head = _label("Today", SECTION_CSS + f" color: {_c('#ffffff')};")
        col.addWidget(self._click(head, self._open(_nids(w, wo, k, ko, g, go)),
                                  "Open all of today's cards in the Browser"))
        if not (w or wo or k or ko or g or go):
            col.addWidget(_label("Nothing new yet today.", HINT_CSS))
            return

        lay = self._card(col)
        self._heading(lay, f"Words · {len(w):,}", self._word_color(), _nids(w),
                      "Open all of today's words in the Browser")
        for x in w:
            lay.addWidget(self._word_row(x))
        self._outside_line(lay, wo, "words")

        if k or ko:
            lay = self._card(col)
            self._heading(lay, f"Kanji · {len(k):,}", KANJI_COLOR, _nids(k),
                          "Open all of today's kanji in the Browser")
            if k:
                self._kanji_line(lay, k, big=True)
            self._outside_line(lay, ko, "kanji")
        if g or go:
            lay = self._card(col)
            self._heading(lay, f"Grammar · {len(g):,}", GRAMMAR_COLOR, _nids(g),
                          "Open all of today's grammar in the Browser")
            for x in g:
                lay.addWidget(self._grammar_row(x, sentence=True))
            self._outside_line(lay, go, "grammar")

    # ── the period ────────────────────────────────────────────────────────

    def _period(self, col: QVBoxLayout):
        d = self._data
        n_days = len(d["days"])
        everything = _nids(d["words"], d["words_out"], d["kanji"], d["kanji_out"],
                           d["grammar"], d["grammar_out"])
        head = _label(f"Past {self._days_back} days", SECTION_CSS + f" color: {_c('#ffffff')};")
        col.addWidget(self._click(head, self._open(everything),
                                  "Open all of these days' cards in the Browser"))

        # Totals, pace and a bar per day.
        lay = self._card(col)
        tot = QHBoxLayout()
        tot.setSpacing(14)
        nw, nk, ng = len(d["words"]), len(d["kanji"]), len(d["grammar"])
        for text, color, items in ((f"{nw:,} {'word' if nw == 1 else 'words'}", self._word_color(), d["words"]),
                                   (f"{nk:,} kanji", KANJI_COLOR, d["kanji"]),
                                   (f"{ng:,} grammar", GRAMMAR_COLOR, d["grammar"])):
            lbl = _label(text, f"font-size: 15px; color: {_c(color)};")
            tot.addWidget(self._click(lbl, self._open(_nids(items)), "Open them all in the Browser"))
        tot.addStretch()
        lay.addLayout(tot)
        st = d["goal"]
        per = st["kinds"]["vocab"]["per_day"] if st and st["phase"] == "plan" and "vocab" in st["kinds"] else 0
        if per:
            # every kind's pace over the period (owner 2026-10-28), from the goal's per day
            def over(k):                # a weekly kind (goal.status): its week's share
                if k.get("weekly"):
                    return -(-k["per_week"] * self._days_back // 7)
                return k["per_day"] * self._days_back
            need = [f"{over(k):,} {name}"
                    for kind, name in (("vocab", "words"), ("kanji", "kanji"), ("grammar", "grammar"))
                    for k in [st["kinds"].get(kind)] if k and k["per_day"]]
            lay.addWidget(_label(f"Needed in {self._days_back} days: " + " · ".join(need), HINT_CSS))
        self._bars(lay, per)

        # Words, day by day (newest first).
        lay = self._card(col)
        self._heading(lay, f"Words · {nw:,}", self._word_color(), _nids(d["words"]),
                      "Open all of these days' words in the Browser")
        any_day = False
        for i in range(n_days - 1, -1, -1):
            items = review.on_day(d["words"], i)
            if not items:
                continue
            any_day = True
            row = QHBoxLayout()
            row.setSpacing(8)
            row.addWidget(_label(review.day_name(d["days"][i]) if i < n_days - 1 else "Today",
                                 f"color: {_c('#aaaaaa')}; font-size: 12px;"))
            row.addWidget(_label(f"{len(items):,} {'word' if len(items) == 1 else 'words'}",
                                 f"color: {_c(self._word_color())}; font-size: 12px;"))
            ws = "、".join(html.escape(x["text"]) for x in items[:DAY_WORDS])
            wl = _label(ws + ("、…" if len(items) > DAY_WORDS else ""),
                        f"font-size: 15px; color: {_c('#dddddd')};")
            wl.setWordWrap(True)
            wl.setProperty("jlpt_gold_skip", True)
            row.addWidget(wl, 1)
            line = QWidget()
            line.setLayout(row)
            row.setContentsMargins(2, 1, 2, 1)
            self._click(line, self._open(_nids(items)), "Open this day's words in the Browser")
            line.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            line.setObjectName("rvline")
            lay.addWidget(line)
        if not any_day:
            lay.addWidget(_label("Nothing new in these days.", HINT_CSS))
        self._outside_line(lay, d["words_out"], "words")

        if d["kanji"] or d["kanji_out"]:
            lay = self._card(col)
            self._heading(lay, f"Kanji · {nk:,}", KANJI_COLOR, _nids(d["kanji"]),
                          "Open all of these days' kanji in the Browser")
            if d["kanji"]:
                self._kanji_line(lay, list(reversed(d["kanji"])), big=False)
            self._outside_line(lay, d["kanji_out"], "kanji")
        if d["grammar"] or d["grammar_out"]:
            lay = self._card(col)
            self._heading(lay, f"Grammar · {ng:,}", GRAMMAR_COLOR, _nids(d["grammar"]),
                          "Open all of these days' grammar in the Browser")
            for x in reversed(d["grammar"]):
                lay.addWidget(self._grammar_row(x, sentence=False))
            self._outside_line(lay, d["grammar_out"], "grammar")

    def _bars(self, lay, per: int):
        """A bar per day (words learned), dimmed under the day's target; a
        click opens that day's cards."""
        d = self._data
        n_days = len(d["days"])
        counts = [len(review.on_day(d["words"], i)) for i in range(n_days)]
        top = max(counts + [per, 1])
        wide = n_days <= 7
        row = QHBoxLayout()
        row.setSpacing(6 if wide else 2)
        color = self._word_color()
        for i, n in enumerate(counts):
            box = QVBoxLayout()
            box.setSpacing(2)
            bar = QLabel()
            bar.setFixedSize(30 if wide else 12, 4 + int(56 * n / top))
            lit = n >= per if per else n > 0
            dim = DIM_GOLD if _gold() else DIM_BAR
            fill = "transparent" if n == 0 else _c(color) if lit else dim
            bar.setStyleSheet(f"background: {fill}; border-radius: 3px;")
            day = d["days"][i]
            items = [x for key in ("words", "words_out", "kanji", "kanji_out", "grammar", "grammar_out")
                     for x in review.on_day(d[key], i)]
            self._click(bar, self._open(_nids(items)),
                        f"{review.day_name(day)}: {n:,} {'word' if n == 1 else 'words'}. "
                        "Click to open that day's cards in the Browser.")
            box.addStretch()
            box.addWidget(bar, 0, Qt.AlignmentFlag.AlignHCenter)
            if wide:
                name = "Today" if i == n_days - 1 else review.WEEKDAYS[day.weekday()]
            else:
                name = str(day.day) if (n_days - 1 - i) % 5 == 0 else ""
            box.addWidget(_label(name, f"color: {_c('#999999')}; font-size: 11px;"),
                          0, Qt.AlignmentFlag.AlignHCenter)
            row.addLayout(box)
        row.addStretch()
        lay.addLayout(row)


def open_review(parent: QWidget, results: dict, deck: str, days_back: int = 7) -> ReviewWindow:
    """Open (or rebuild) the review over the main window `parent`."""
    old = getattr(parent, "_review_window", None)
    if old is not None:
        try:
            old.close()
        except RuntimeError:
            pass
    win = ReviewWindow(parent, results, deck, days_back)
    parent._review_window = win
    win.show()
    win.raise_()
    win.activateWindow()
    return win


def open_from(widget: QWidget, days_back: int) -> bool:
    """From a link inside the main window: its results and deck. False if
    `widget` isn't in one (the caller falls back to the Browser)."""
    win = widget.window() if widget is not None else None
    results = getattr(win, "_results", None)
    if results is None or not hasattr(win, "_deck_name"):
        return False
    open_review(win, results, win._deck_name, days_back)
    return True
