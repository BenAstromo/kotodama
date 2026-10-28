"""
history_view.py
The History tab: a line chart of the progress history (history.py) in the
bars' glowing style, with a range selector (7 / 30 / 90 days / all time),
series toggles (rank / JLPT levels / kanji / grammar / frequency), hover
values, a summary table (now, this week / month / year, since the start,
best week) and a manual snapshot button. No projected dates (owner's
decision); a JLPT goal (goal.py) is the user's own date, not a projection:
with one set, the chart runs on to the test day with the goal's words and a
dashed "On track" line to the finish line. delta_label() makes the "+N this week · +N this month" line shown
under the main bars of the Overview and the Kanji & Grammar tab; each number
is a link (open_gained) to the notes behind it in the Browser.
"""

from __future__ import annotations

import datetime

from aqt.qt import *

from . import freq_data
from .theme import BODY_CSS, HINT_CSS
from . import history
from .jlpt_data import LEVELS, LEVEL_COLORS

RANK_COLOR   = "#ff5c8a"
ALL_JLPT     = "#ffffff"
ALL_JLPT_GLOW = "#ff1744"   # the All Levels bar's glow
# Frequency tiers: darker blue for the small tiers, the bars' sky blue
# (FREQ_FG) for Near Native.
FREQ_COLORS = ["#1f6f99", "#1f86b3", "#2b9fd0", "#46b6e8", "#6ad0fb", "#a8e6ff"]
KANJI_COLOR   = "#ffb74d"
GRAMMAR_COLOR = "#ce93d8"


# Amaterasu mode: only gold, black and white — each line its own gold shade
# (pale → deep), the frequency tiers dashed, so they stay distinguishable.
GOLD_RANK, GOLD_ALL = "#fffbe6", "#f5c518"
GOLD_LEVELS = {"N5": "#fff3c2", "N4": "#ffe27a", "N3": "#f5c518", "N2": "#d9a400", "N1": "#a87700"}
GOLD_FREQ = ["#8a6400", "#a87700", "#c99300", "#e0b225", "#f5cf55", "#fff0b0"]
GOLD_KANJI, GOLD_GRAMMAR = "#ffe9a8", "#c99300"


def _fmt(v: int) -> str:
    return f"{'+' if v >= 0 else '−'}{abs(v):,}"


def gain_link(href: str, inner: str, text_color: str = "#bbbbbb") -> str:
    """A link (no underline, the line's own colours) around `inner`; a
    Qt label needs an explicit colour or it draws links blue."""
    return (f"<a href='{href}' style='color:{text_color}; "
            f"text-decoration:none;'>{inner}</a>")


def delta_html(series: dict, key: str, color: str, text_color: str = "#bbbbbb") -> str | None:
    """"+N today · +N this week · +N this month" for one history line, or
    None (today added 2026-10-22). Each part links to "gain:<key>:<days>":
    connect the label with connect_gain_links."""
    day = history.delta(series or {}, key, 1)
    week = history.delta(series or {}, key, 7)
    month = history.delta(series or {}, key, 30)
    if week is None:
        return None
    return (gain_link(f"gain:{key}:1", f"<span style='color:{color};'><b>{_fmt(day)}</b></span> today",
                      text_color)
            + " &nbsp;·&nbsp; "
            + gain_link(f"gain:{key}:7", f"<span style='color:{color};'><b>{_fmt(week)}</b></span> this week",
                      text_color)
            + " &nbsp;·&nbsp; "
            + gain_link(f"gain:{key}:30", f"<span style='color:{color};'><b>{_fmt(month)}</b></span> this month",
                        text_color))


def open_gained(series: dict, parts, days_back: int, parent=None):
    """The notes behind a gain (owner 2026-10-21: "which cards for each day /
    week / month") in Anki's Browser, or a tooltip when there are none.
    parts: [(history key, keep filter or None), …], their notes together."""
    from aqt import mw, dialogs
    from aqt.utils import tooltip
    nids = []
    for key, keep in parts:
        nids += [n for n in history.gained_nids(series, key, days_back, keep) if n not in nids]
    if not nids:
        tooltip("No new cards in this period (words marked found aren't listed).",
                parent=parent)
        return
    b = dialogs.open("Browser", mw)
    b.search_for("nid:" + ",".join(str(n) for n in nids))


def gain_tip(parts, days: int) -> str:
    """A +N number's hover (owner 2026-10-28, every one): what it's made of.
    parts = history.gain_parts()."""
    d, cards, joined = parts
    when = {1: "today", 7: "this week", 30: "this month"}.get(days, f"in {days} days")
    lines = [f"{d:+,} {when}: {cards:,} learned from cards"
             + (f", {joined:,} marked English {'loanword' if joined == 1 else 'loanwords'} joined"
                if joined else "")
             + (f", {cards - d:,} lost (cards reset to new)" if d < cards else "") + "."]
    if joined:
        lines.append("Marked loanwords join as your learned words reach their place on the frequency "
                     "list. They have no card, so the Browser shows only the cards.")
    lines.append("Click to see the cards in the Browser.")
    return "\n".join(lines)


def connect_gain_links(lbl: QLabel, series_fn):
    """Make a label's "gain:<key>:<days>" links open those notes in the
    Browser (owner 2026-10-28: the Progress Review is only the JLPT goal's).
    series_fn() gives the current series (it's rebuilt on refresh)."""
    lbl.setTextInteractionFlags(Qt.TextInteractionFlag.LinksAccessibleByMouse)
    lbl.setOpenExternalLinks(False)

    def activated(href: str):
        if not href.startswith("gain:"):
            return
        _g, key, days = href.split(":")
        open_gained(series_fn(), [(key, None)], int(days), lbl)
    lbl.linkActivated.connect(activated)

    # Hovering a number: what it's made of, when marked loanwords joined
    # (owner 2026-10-28: "+35 today" opened 30 cards in the Browser).
    base_tip = [None]                   # the label's own tooltip, off the numbers

    def hovered(href: str):
        if base_tip[0] is None:
            base_tip[0] = lbl.toolTip()
        parts = None
        if href.startswith("gain:"):
            _g, key, days = href.split(":")
            parts = history.gain_parts(series_fn(), key, int(days))
        if not parts:
            lbl.setToolTip(base_tip[0])
            return
        lbl.setToolTip(gain_tip(parts, int(days)))
    lbl.linkHovered.connect(hovered)


def delta_label(series: dict, key: str, color: str, what: str) -> QLabel | None:
    """The line under a main bar (owner 2026-10-15): this bar's own gain.
    Click a number to see its notes in the Browser."""
    text = delta_html(series, key, color)
    if text is None:
        return None
    lbl = QLabel(text)
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl.setStyleSheet(BODY_CSS + " color: #bbbbbb; padding: 1px 0 3px 0;")
    lbl.setToolTip(f"Change in {what} today and over the last 7 and 30 days. "
                   "Click a number to see those cards in the Browser. "
                   "The History tab has the chart and lifetime numbers.")
    connect_gain_links(lbl, lambda: series)
    from .progress_dialog import _regold
    _regold(lbl)
    return lbl


def _series_defs():
    """(group, key, label, colour, glow colour, dashed)."""
    from .progress_dialog import _GOLD_MODE
    if _GOLD_MODE["on"]:
        defs = [
            ("rank", "rank", "Learned (rank)", GOLD_RANK, GOLD_ALL, False),
            ("rank", "mature", "Mature", GOLD_RANK, GOLD_ALL, True),
            ("jlpt", "jlpt", "All JLPT levels", GOLD_ALL, GOLD_RANK, False),
        ]
        for lvl in LEVELS:
            defs.append(("jlpt", lvl, lvl, GOLD_LEVELS[lvl], GOLD_LEVELS[lvl], False))
        defs.append(("kanji", "kanji", "JLPT Kanji", GOLD_KANJI, GOLD_ALL, True))
        defs.append(("grammar", "grammar", "JLPT Grammar", GOLD_GRAMMAR, GOLD_ALL, True))
        for n, col in zip(freq_data.TIERS, GOLD_FREQ):
            if n not in freq_data.BAR_TIERS and n != freq_data.TIERS[-1]:
                continue                  # top 800 / 1,500: recorded, not shown (2026-10-20)
            name = freq_data.TIER_NAMES.get(n, "")
            label = f"Top {n:,}" if name != "Near Native" else f"Near Native ({n:,})"
            defs.append(("freq", f"f{n}", label, col, col, True))
        return defs
    defs = [
        ("rank", "rank", "Learned (rank)", RANK_COLOR, RANK_COLOR, False),
        ("rank", "mature", "Mature", RANK_COLOR, RANK_COLOR, True),
        ("jlpt", "jlpt", "All JLPT levels", ALL_JLPT, ALL_JLPT_GLOW, False),
    ]
    for lvl in LEVELS:
        defs.append(("jlpt", lvl, lvl, LEVEL_COLORS[lvl], LEVEL_COLORS[lvl], False))
    defs.append(("kanji", "kanji", "JLPT Kanji", KANJI_COLOR, KANJI_COLOR, False))
    defs.append(("grammar", "grammar", "JLPT Grammar", GRAMMAR_COLOR, GRAMMAR_COLOR, False))
    for n, col in zip(freq_data.TIERS, FREQ_COLORS):
        if n not in freq_data.BAR_TIERS and n != freq_data.TIERS[-1]:
            continue                      # top 800 / 1,500: recorded, not shown (2026-10-20)
        name = freq_data.TIER_NAMES.get(n, "")
        label = f"Top {n:,}" if name != "Near Native" else f"Near Native ({n:,})"
        defs.append(("freq", f"f{n}", label, col, col, False))
    return defs


GROUPS = [("rank", "Rank"), ("jlpt", "JLPT levels"), ("kanji", "Kanji"), ("grammar", "Grammar"),
          ("freq", "Frequency"), ("goal", "JLPT goal")]
GOAL_TRACK = "#bdbdbd"      # the dashed "On track" line
GOAL_COLOR, GOLD_GOAL = "#64ffda", "#fff0b0"   # the goal's words: no other line uses these

# Rows of the summary table: (key, label, colour); gold mode swaps colours.
SUMMARY_ROWS = [("rank", "Learned (rank)", RANK_COLOR), ("mature", "Mature", RANK_COLOR),
                ("jlpt", "JLPT Words", ALL_JLPT), ("kanji", "JLPT Kanji", KANJI_COLOR),
                ("grammar", "JLPT Grammar", GRAMMAR_COLOR),
                (f"f{freq_data.TIERS[-1]}", "Near Native (20,000)", FREQ_COLORS[-1])]
SUMMARY_COLS = ["Now", "Today", "This week", "This month", "This year", "Since start", "Best week"]
RANGES = [(7, "7 days"), (30, "30 days"), (90, "90 days"), (None, "All time")]


def _nice_axis(v: float) -> tuple[float, float]:
    """(y-axis maximum, gridline step) for a chart whose highest value is v:
    the smallest 1 / 2 / 2.5 / 5 × 10^k step that covers v in at most 7
    gridline intervals, so the lines fill the chart (3,320 → 3,500 in steps
    of 500)."""
    import math
    if v <= 0:
        return 10, 2
    exp = 10 ** math.floor(math.log10(v / 7))
    for m in (1, 2, 2.5, 5, 10):
        step = m * exp
        if math.ceil(v / step) <= 7:
            break
    return math.ceil(v / step) * step, step


class HistoryChart(QWidget):
    _ML, _MR, _MT, _MB = 58, 18, 14, 30   # plot margins

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setMinimumHeight(320)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._days: list[datetime.date] = []
        self._recorded: list[bool] = []
        self._lines: list[tuple] = []   # (label, colour, glow, dashed, values; None = no value that day)
        self._markers: list[tuple] = [] # (day index, label, colour): the goal's finish line and test day
        self._hover: int | None = None

    def set_data(self, days, recorded, lines, markers=()):
        self._days, self._recorded, self._lines = days, recorded, lines
        self._markers = list(markers)
        self._hover = None
        self.update()

    # ── geometry ──────────────────────────────────────────────────────────
    def _plot_rect(self) -> QRectF:
        return QRectF(self._ML, self._MT,
                      max(1, self.width() - self._ML - self._MR),
                      max(1, self.height() - self._MT - self._MB))

    def _axis(self) -> tuple[float, float]:
        """Rescales to the highest visible line in the selected range."""
        top = max((max(x for x in v if x is not None) for *_x, v in self._lines
                   if any(x is not None for x in v)), default=0)
        return _nice_axis(top * 1.05)   # headroom for the glow

    def _x(self, i: int, r: QRectF) -> float:
        n = len(self._days)
        if n <= 1:
            return r.center().x()
        return r.left() + r.width() * i / (n - 1)

    def _y(self, v: float, r: QRectF, ymax: float) -> float:
        return r.bottom() - r.height() * (v / ymax if ymax else 0)

    # ── painting ──────────────────────────────────────────────────────────
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        # A rounded panel like the section cards (owner 2026-10-18), gold in
        # Amaterasu mode (was a flat #1b1b1b grey in both).
        from .progress_dialog import _GOLD_MODE
        gold = _GOLD_MODE["on"]
        p.setPen(QPen(QColor("#4a3d12" if gold else "#2c2c2c"), 1))
        p.setBrush(QColor(255, 226, 112, 9) if gold else QColor(255, 255, 255, 8))
        p.drawRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), 10, 10)
        p.setBrush(Qt.BrushStyle.NoBrush)      # the lines below must not be filled
        self._grid_col = "#2a2310" if gold else "#262626"
        self._grid_col_v = "#221c0c" if gold else "#1f1f1f"
        r = self._plot_rect()

        if not self._days:
            p.setPen(QColor("#888"))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No history yet")
            return
        if not self._lines:
            p.setPen(QColor("#888"))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                       "Turn on Rank, JLPT levels or Frequency above")
            return

        ymax, step = self._axis()
        font = p.font()
        font.setPointSize(8)
        p.setFont(font)
        fm = QFontMetrics(font)

        # Horizontal grid + y labels
        for k in range(round(ymax / step) + 1):
            v = step * k
            y = self._y(v, r, ymax)
            p.setPen(QPen(QColor(self._grid_col), 1))      # faint (owner 2026-10-18)
            p.drawLine(QPointF(r.left(), y), QPointF(r.right(), y))
            p.setPen(QColor("#999999"))
            txt = f"{v:,.0f}"
            p.drawText(QRectF(0, y - 8, self._ML - 8, 16),
                       Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, txt)

        # X labels: about one per 110px
        n = len(self._days)
        span = (self._days[-1] - self._days[0]).days
        fmt = "%b %Y" if span > 180 else "%b %d"
        n_labels = max(2, min(n, int(r.width() // 110) + 1))
        used = set()
        for k in range(n_labels):
            i = round(k * (n - 1) / (n_labels - 1)) if n_labels > 1 else 0
            if i in used:
                continue
            used.add(i)
            x = self._x(i, r)
            txt = self._days[i].strftime(fmt).replace(" 0", " ")
            w = fm.horizontalAdvance(txt)
            tx = min(max(x - w / 2, r.left() - 20), r.right() - w + 10)
            p.setPen(QPen(QColor(self._grid_col_v), 1))
            p.drawLine(QPointF(x, r.top()), QPointF(x, r.bottom()))
            p.setPen(QColor("#999999"))
            p.drawText(QPointF(tx, r.bottom() + 18), txt)

        # Amaterasu: once any line has reached 20,000, a glowing gold line
        # marks it across the chart (labelled 天照).
        if any(any(x is not None and x >= 20_000 for x in vals) for *_x, vals in self._lines) \
                and ymax >= 20_000:
            y = self._y(20_000, r, ymax)
            for width, alpha in ((14, 30), (8, 70), (4, 140)):
                p.setPen(QPen(QColor(255, 236, 150, alpha), width))
                p.drawLine(QPointF(r.left(), y), QPointF(r.right(), y))
            p.setPen(QPen(QColor("#fff8c5"), 1.5))
            p.drawLine(QPointF(r.left(), y), QPointF(r.right(), y))
            p.setPen(QColor("#f5c518"))
            p.drawText(QRectF(r.left() + 6, y - 18, 200, 14),
                       Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "天照  20,000")

        # JLPT goal: a faint vertical line at the finish line and the test day
        for i, label, col in self._markers:
            x = self._x(i, r)
            c = QColor(col)
            c.setAlpha(150)
            p.setPen(QPen(c, 1, Qt.PenStyle.DashLine))
            p.drawLine(QPointF(x, r.top()), QPointF(x, r.bottom()))
            p.setPen(QColor(col))
            w = fm.horizontalAdvance(label)
            p.drawText(QPointF(max(r.left() + 2, min(x + 4, r.right() - w)), r.top() + 10), label)

        # Lines: a soft glow under a crisp line, like the bars
        for label, color, glow, dashed, vals in self._lines:
            pts = [QPointF(self._x(i, r), self._y(v, r, ymax)) for i, v in enumerate(vals) if v is not None]
            if not pts:
                continue
            path = QPainterPath(pts[0])
            for pt in pts[1:]:
                path.lineTo(pt)
            for width, alpha in ((9, 28), (5, 60)):
                g = QColor(glow)
                g.setAlpha(alpha)
                pen = QPen(g, width)
                pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
                p.setPen(pen)
                p.drawPath(path)
            pen = QPen(QColor(color), 2)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            if dashed:
                pen.setStyle(Qt.PenStyle.DashLine)
            p.setPen(pen)
            p.drawPath(path)
            if len(pts) == 1:
                p.setBrush(QColor(color))
                p.drawEllipse(pts[0], 3, 3)
                p.setBrush(Qt.BrushStyle.NoBrush)

        if self._hover is not None:
            self._paint_hover(p, r, ymax, fm)

    def _paint_hover(self, p: QPainter, r: QRectF, ymax: float, fm: QFontMetrics):
        i = self._hover
        x = self._x(i, r)
        p.setPen(QPen(QColor(255, 255, 255, 90), 1, Qt.PenStyle.DashLine))
        p.drawLine(QPointF(x, r.top()), QPointF(x, r.bottom()))
        rows = []
        for label, color, _g, _d, vals in self._lines:
            v = vals[i]
            if v is None:
                continue
            p.setPen(QPen(QColor("#1b1b1b"), 1))
            p.setBrush(QColor(color))
            p.drawEllipse(QPointF(x, self._y(v, r, ymax)), 3.5, 3.5)
            rows.append((v, label, color))
        p.setBrush(Qt.BrushStyle.NoBrush)
        rows.sort(key=lambda t: -t[0])

        day = self._days[i]
        head = day.strftime("%a %b %d, %Y").replace(" 0", " ")
        sub = ("Your JLPT goal's plan" if self._recorded[i] is None
               else "Recorded snapshot" if self._recorded[i] else "Rebuilt from your review history")
        lines = [(head, "#ffffff"), (sub, "#999999")] + \
                [(f"{lbl}: {v:,}", col) for v, lbl, col in rows]
        lh = fm.height() + 2
        w = max(fm.horizontalAdvance(t) for t, _ in lines) + 26
        h = lh * len(lines) + 10
        bx = x + 14 if x + 14 + w < self.width() - 4 else x - 14 - w
        by = max(4, min(r.top() + 6, self.height() - h - 4))
        box = QRectF(bx, by, w, h)
        p.setPen(QPen(QColor("#555555"), 1))
        p.setBrush(QColor(20, 20, 20, 235))
        p.drawRoundedRect(box, 6, 6)
        p.setBrush(Qt.BrushStyle.NoBrush)
        for k, (txt, col) in enumerate(lines):
            ty = by + 5 + lh * k + fm.ascent()
            if k >= 2:
                p.fillRect(QRectF(bx + 8, ty - fm.ascent() + 3, 8, 8), QColor(col))
                p.setPen(QColor("#dddddd"))
                p.drawText(QPointF(bx + 20, ty), txt)
            else:
                p.setPen(QColor(col))
                p.drawText(QPointF(bx + 8, ty), txt)

    # ── hover ─────────────────────────────────────────────────────────────
    def mouseMoveEvent(self, event):
        if not self._days:
            return
        r = self._plot_rect()
        pos = event.position() if hasattr(event, "position") else QPointF(event.pos())
        if not r.adjusted(-6, -6, 6, 6).contains(pos):
            self.leaveEvent(None)
            return
        n = len(self._days)
        i = 0 if n <= 1 else round((pos.x() - r.left()) / r.width() * (n - 1))
        i = max(0, min(n - 1, i))
        if i != self._hover:
            self._hover = i
            self.update()

    def leaveEvent(self, event):
        if self._hover is not None:
            self._hover = None
            self.update()


class HistoryTab(QWidget):
    snapshot_requested = pyqtSignal()

    def __init__(self, series: dict, deck_name: str, parent=None, results_fn=None):
        super().__init__(parent)
        self._series = series
        self._deck_name = deck_name
        self._results_fn = results_fn       # the current results, for the JLPT goal's totals
        self._range = None
        self._groups = {"rank": True, "jlpt": True, "kanji": False, "grammar": False, "freq": False,
                        "goal": True}
        self._group_boxes = {}
        self._build()
        self._refresh_chart()

    def update_series(self, series: dict):
        self._series = series
        self._update_summary()
        self._refresh_chart()

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)
        outer.setSpacing(8)

        hdr_row = QHBoxLayout()
        hdr_row.addWidget(QLabel("<b>Progress History</b>"))
        hdr_row.addStretch()
        self._status = QLabel()
        self._status.setStyleSheet(HINT_CSS)
        hdr_row.addWidget(self._status)
        snap_btn = QPushButton("Take snapshot now")
        snap_btn.setToolTip(
            "Rescan the deck and save today's numbers right away.\n"
            "(A snapshot is also taken automatically every day.)")
        snap_btn.clicked.connect(self.snapshot_requested)
        hdr_row.addWidget(snap_btn)
        outer.addLayout(hdr_row)

        sub = QLabel(
            "One snapshot per day is saved automatically. Days before the first "
            "snapshot are rebuilt from your review history: rank and mature from "
            "your reviews, JLPT, kanji, grammar and frequency from when the first card "
            "with them was first reviewed (or added, if never reviewed), always using the "
            "current lists. Words marked found count from the first day. Deleted cards "
            "and past found/suspended marks can't be rebuilt.")
        sub.setWordWrap(True)
        sub.setStyleSheet(HINT_CSS)
        outer.addWidget(sub)

        # Summary table: every tracked number's gains (owner 2026-10-15)
        table = QWidget()
        self._grid = QGridLayout(table)
        self._grid.setContentsMargins(0, 2, 0, 2)
        self._grid.setHorizontalSpacing(18)
        self._grid.setVerticalSpacing(2)
        for c, name in enumerate(SUMMARY_COLS, start=1):
            h = QLabel(name)
            h.setStyleSheet(HINT_CSS)
            h.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._grid.addWidget(h, 0, c)
        self._cells = {}
        for r, (key, label, _color) in enumerate(SUMMARY_ROWS, start=1):
            name = QLabel()
            self._grid.addWidget(name, r, 0)
            row = [name]
            for c in range(1, len(SUMMARY_COLS) + 1):
                cell = QLabel()
                cell.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                cell.setStyleSheet("font-size: 12px;")
                self._grid.addWidget(cell, r, c)
                row.append(cell)
            self._cells[key] = row
        self._grid.setColumnStretch(len(SUMMARY_COLS) + 1, 1)
        outer.addWidget(table)
        self._since = QLabel()
        self._since.setStyleSheet(HINT_CSS)
        outer.addWidget(self._since)

        ctl = QHBoxLayout()
        ctl.addWidget(QLabel("Show:"))
        self._range_group = QButtonGroup(self)
        self._range_group.setExclusive(True)
        # One segmented control (owner 2026-10-18); theme.py styles [seg].
        seg = QWidget()
        seg_l = QHBoxLayout(seg)
        seg_l.setContentsMargins(0, 0, 0, 0)
        seg_l.setSpacing(0)
        for i, (days, label) in enumerate(RANGES):
            b = QPushButton(label)
            b.setCheckable(True)
            b.setChecked(days == self._range)
            b.setProperty("seg", "first" if i == 0 else "last" if i == len(RANGES) - 1 else "mid")
            b.clicked.connect(lambda _=False, d=days: self._set_range(d))
            self._range_group.addButton(b)
            seg_l.addWidget(b)
        ctl.addWidget(seg)
        ctl.addSpacing(18)
        for key, label in GROUPS:
            cb = QCheckBox(label)
            cb.setChecked(self._groups[key])
            cb.toggled.connect(lambda on, k=key: self._set_group(k, on))
            ctl.addWidget(cb)
            self._group_boxes[key] = cb
        ctl.addStretch()
        outer.addLayout(ctl)

        self._chart = HistoryChart()
        outer.addWidget(self._chart, 1)

        # Legend as small chips, one per line on the chart (owner 2026-10-18).
        self._legend = QWidget()
        self._legend_l = QHBoxLayout(self._legend)
        self._legend_l.setContentsMargins(0, 2, 0, 0)
        self._legend_l.setSpacing(6)
        outer.addWidget(self._legend)

        self._update_summary()

    def _set_range(self, days):
        self._range = days
        self._refresh_chart()

    def _set_group(self, key, on):
        self._groups[key] = on
        self._refresh_chart()

    def _update_summary(self):
        s = self._series or {}
        values = s.get("values", {})
        days = s.get("days", [])
        from .progress_dialog import _GOLD_MODE
        gold_cols = {"rank": GOLD_RANK, "mature": GOLD_RANK, "jlpt": GOLD_ALL, "kanji": GOLD_KANJI,
                     "grammar": GOLD_GRAMMAR}
        today = days[-1] if days else None
        year_back = (today - datetime.date(today.year, 1, 1)).days if today else 0
        for key, label, color in SUMMARY_ROWS:
            col = gold_cols.get(key, GOLD_FREQ[-1]) if _GOLD_MODE["on"] else color
            row = self._cells[key]
            have = key in values
            for w in row:
                w.setVisible(have)
            if not have:
                continue
            row[0].setText(f"<span style='color:{col};'>■</span> {label}")
            nums = [values[key][-1], history.delta(s, key, 1), history.delta(s, key, 7), history.delta(s, key, 30),
                    history.delta(s, key, year_back), history.since_start(s, key),
                    history.best_week(s, key)]
            for i, v in enumerate(nums):
                txt = f"{v:,}" if i == 0 else _fmt(v)
                row[i + 1].setText(f"<span style='color:{col};'><b>{txt}</b></span>" if i else txt)
        if days:
            self._since.setText(f"History starts {days[0].isoformat()} ({len(days):,} days). "
                                "This year = since January 1.")
        else:
            self._since.setText("")
        snap = history.recorded_days(self._deck_name)
        if snap:
            day = max(snap)
            t = snap[day].get("t")
            when = datetime.datetime.fromtimestamp(t).strftime("%b %d, %H:%M").replace(" 0", " ") if t else day
            kind = "manual" if snap[day].get("src") == "manual" else "automatic"
            self._status.setText(f"Last snapshot: {when} ({kind})")
        else:
            self._status.setText("No snapshot saved yet")
        from .progress_dialog import _regold
        _regold(self._status, self._since, *[w for row in self._cells.values() for w in row])
        _regold(*[self._grid.itemAtPosition(0, c).widget() for c in range(1, len(SUMMARY_COLS) + 1)])

    def _refresh_chart(self):
        s = self._series or {}
        days = s.get("days", [])
        values = s.get("values", {})
        recorded = s.get("recorded", [False] * len(days))
        start = 0 if self._range is None else max(0, len(days) - self._range)
        lines = []
        legend = []
        for group, key, label, color, glow, dashed in _series_defs():
            if not self._groups.get(group) or key not in values:
                continue
            lines.append((label, color, glow, dashed, values[key][start:]))
            mark = "┅" if dashed else "■"
            legend.append(f"<span style='color:{color};'>{mark}</span> {label}")
        days, recorded = list(days[start:]), list(recorded[start:])
        lines = [(lb, c, g, d, list(v)) for lb, c, g, d, v in lines]
        markers = self._add_goal(s, start, days, recorded, lines, legend)
        self._chart.set_data(days, recorded, lines, markers)
        while self._legend_l.count():
            item = self._legend_l.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        chips = []
        for text in legend:
            chip = QLabel(text)
            # its swatch carries the line's own (gold) shade: translate in
            # gold mode, but don't flatten it to one gold
            chip.setProperty("jlpt_keep_color", True)
            chip.setStyleSheet("font-size: 12px; background: rgba(255,255,255,0.05);"
                               " border: 1px solid #2e2e2e; border-radius: 9px; padding: 1px 8px;")
            self._legend_l.addWidget(chip)
            chips.append(chip)
        self._legend_l.addStretch()
        from .progress_dialog import _regold
        _regold(*chips)

    def _add_goal(self, s: dict, start: int, days: list, recorded: list, lines: list,
                  legend: list) -> list:
        """JLPT goal: the chart runs on to the test day, with the words up to
        the goal's level (solid) and a dashed "On track" line from the day
        the goal was set to everything learned at the finish line, flat after.
        Returns the markers. Its checkbox shows only while there's a goal."""
        from . import goal
        st = None
        try:
            if self._results_fn is not None and days:
                st = goal.status(self._results_fn(), self._deck_name, record=False)
        except Exception:
            st = None
        if st is not None and st["phase"] == "past":
            st = None
        box = self._group_boxes.get("goal")
        if box is not None:
            box.setVisible(st is not None)
        values = s.get("values", {})
        v = st["kinds"].get("vocab") if st else None
        lv = goal.levels_upto(st["level"]) if st else []
        top = goal.vocab_source(st["level"]) if st else None    # N2 / N1: two steps
        if st is None or v is None or not self._groups.get("goal"):
            return []
        if any(l not in values for l in lv) or (top and st.get("steps") and f"f{top}" not in values):
            return []
        from .progress_dialog import _GOLD_MODE
        gold = _GOLD_MODE["on"]
        col = GOLD_GOAL if gold else GOAL_COLOR
        track_col = GOLD_ALL if gold else GOAL_TRACK
        all_days = s.get("days", [])
        past = [sum(values[l][i] for l in lv) for i in range(len(all_days))]
        steps = st.get("steps")
        if top and steps:
            # N2 / N1: step 1 (the lists, recorded per level) + step 2 (common
            # words off the lists). History doesn't keep step 2 apart, so its
            # past is estimated: today's step 2 scaled by the top-N line.
            k2, n2 = steps["common"]
            fv = values[f"f{top}"]
            f_now = fv[-1] or 0
            past = [p + (min(n2, round(k2 * fv[i] / f_now)) if f_now else 0)
                    for i, p in enumerate(past)]
        today = days[-1]
        extra = max(0, (st["date"] - today).days)
        for k in range(1, extra + 1):
            days.append(today + datetime.timedelta(days=k))
            recorded.append(None)
        for line in lines:
            line[4].extend([None] * extra)
        mine = past[start:] + [None] * extra
        # On track, in whole-history day numbers: from the day the goal was
        # set (its words that day) to the total on the finish line.
        si = max(0, len(all_days) - 1 - (all_days[-1] - st["set"]).days)
        fi = len(all_days) - 1 + (st["finish"] - all_days[-1]).days
        total = v["total"]
        track = []
        if fi > si:
            v0 = past[min(si, len(past) - 1)]
            for j in range(start, start + len(days)):
                track.append(None if j < si else round(v0 + (total - v0) * min(1.0, (j - si) / (fi - si))))
        else:
            track = [None] * len(days)
        label = f"Goal words ({st['level']})" if top else f"Words up to {st['level']}"
        on_track = "On track"
        # painted on the chart: Japanese in Amaterasu mode (the legend chips
        # below are translated by divine_text)
        lines.append(((f"目標の単語（{st['level']}）" if top else f"{st['level']} までの単語") if gold else label,
                      col, col, False, mine))
        lines.append(("予定ライン" if gold else on_track, track_col, track_col, True, track))
        legend.append(f"<span style='color:{col};'>■</span> {label}")
        legend.append(f"<span style='color:{track_col};'>┅</span> {on_track}")
        markers = []
        fin_i = fi - start
        if 0 <= fin_i < len(days):
            markers.append((fin_i, "ゴール" if gold else "Finish line", track_col))
        markers.append((len(days) - 1, f"JLPT {st['level']}", col))
        return markers
