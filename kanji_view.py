"""
kanji_view.py
Kanji & Grammar tab (backlog #5): small, deemphasised bars that open the
kanji and grammar grids. Kanji and grammar don't affect the rank or the word
counts, so their bars are compact and live on their own tab. Grammar tiles
(GrammarCell) are as wide as their pattern and use the same heatmap.

Kanji tiles are coloured by a heatmap of how well each kanji is known
(kanji_data: the mean FSRS-based score of its learned cards), not by
maturity; unseen kanji use the word grids' dark "missing" tile.

Tile interactions (as on word tiles):
  Left-click        → a window with your cards that use the kanji and the
                      common words with it to learn (copy, Browser, Jisho)
  Shift+Click       → Jisho kanji page
  Middle-click      → toggle marked as found (kanji without a learned card)
  Ctrl+Middle-click → toggle suspended (left out of the counts)
"""

import html
import re

from aqt.qt import *

from . import card_state
from .theme import SECTION_CSS, HINT_CSS
from . import grammar_data
from . import jlpt_data
from . import kanji_data
from . import rank_data
from .jlpt_data import LEVELS, LEVEL_COLORS as LEVEL_FG
from .progress_dialog import (
    CELL_W, CELL_H, CELL_R, UNLISTED_FG, MISSING_GLOW, LevelBar, WordGridPanel, _TileCanvas, DivineOverlay,
    _GOLD_MODE, MISSING_GOLD, _gold_item, _Tile,
    _hl_register, _paint_gold_highlight, _regold,
    _copy_word, count_deck_notes, MATURITY_LABELS, _copy_to_clipboard, _fill_table,
    _quiet_button_style, _paint_in_deck, _section_card, set_empty_hint, _ButtonColumn,
)

# Weak → strong heatmap (score 0 … 1). Red → orange → yellow → green → teal,
# the usual reading of a retention heatmap; drawn as the word tiles' gradient.
# The stops are packed into 0.45–0.82, where most scores fall (owner's deck:
# median 0.58, deciles 0.26 … 0.84), so the middle of the range spans
# yellow → green → teal instead of one muddy yellow-green (owner 2026-10-09:
# "the colour range is too compressed"). Blended by hue (HSV), not RGB, so
# in-between shades stay vivid.
HEAT_STOPS = [
    (0.00, "#e53935"),   # red
    (0.25, "#fb8c00"),   # orange
    (0.45, "#fdd835"),   # yellow
    (0.65, "#5fd43a"),   # green
    (0.82, "#1fcf9f"),   # teal
    (1.00, "#22c8f0"),   # cyan
]
HEAT_NAMES = [(0.25, "Weak"), (0.50, "Low moderate"), (0.75, "High moderate"), (1.01, "Strong")]


# Amaterasu gold mode: strength as the depth of the gold (pale = weak, rich
# = strong) instead of the red → cyan ramp; tiles get bronze text.
GOLD_WEAK, GOLD_STRONG = QColor("#fff1bf"), QColor("#e0a200")
BRONZE = "#3b2600"


def heat_color(score: float) -> QColor:
    s = min(max(score, 0.0), 1.0)
    if _GOLD_MODE["on"]:
        a, b = GOLD_WEAK, GOLD_STRONG
        return QColor.fromRgbF(a.redF() + (b.redF() - a.redF()) * s,
                               a.greenF() + (b.greenF() - a.greenF()) * s,
                               a.blueF() + (b.blueF() - a.blueF()) * s)
    for (a, ca), (b, cb) in zip(HEAT_STOPS, HEAT_STOPS[1:]):
        if s <= b:
            t = (s - a) / (b - a) if b > a else 0
            h1, s1, v1, _ = QColor(ca).getHsvF()
            h2, s2, v2, _ = QColor(cb).getHsvF()
            return QColor.fromHsvF(h1 + (h2 - h1) * t, s1 + (s2 - s1) * t,
                                   v1 + (v2 - v1) * t)
    return QColor(HEAT_STOPS[-1][1])


def heat_name(score: float) -> str:
    for limit, name in HEAT_NAMES:
        if score < limit:
            return name
    return HEAT_NAMES[-1][1]


def _heat_legend_html(unseen: str) -> str:
    blocks = "".join(f"<span style='color:{heat_color(i / 12).name()}'>■</span>"
                     for i in range(13))
    # The dashed "in your deck, not learned yet" tile (owner 2026-10-17).
    in_deck = "<span style='color:#9a9a9a'>⬚</span> In your deck, not learned &nbsp;&nbsp;"
    return (f"Weak {blocks} Strong &nbsp;&nbsp;"
            f"<span style='color:#555'>■</span> {unseen} &nbsp;&nbsp;" + in_deck +
            "<span style='color:#ffe066'>★</span> Marked found &nbsp;&nbsp;"
            "<span style='color:#e05a5a'>✕</span> Suspended")


def _tile_glow(cell, level_fg: str) -> str:
    """A kanji / grammar tile's glow colour: as its fill (owner 2026-10-26:
    the glow follows the grid's gradient, not the N colour)."""
    if cell._is_suspended:
        return MISSING_GLOW
    if cell._known:
        return heat_color(cell._score).name()
    if cell._is_found:
        return level_fg
    return MISSING_GLOW


def _heat_legend(unseen: str = "Unseen (no learned card)") -> QLabel:
    lbl = QLabel(_heat_legend_html(unseen))
    lbl.setStyleSheet(HINT_CSS)
    # divine_text re-renders it (gold ramp ↔ heat ramp) when gold mode changes
    lbl.setProperty("jlpt_heat_legend", unseen)
    return lbl


def _source_text(kres: dict) -> str:
    """Where the kanji come from, in the Settings options' words. Kanji are
    read straight from the text, so "parser" isn't mentioned (it's only
    involved for grammar)."""
    src = kres["source"]
    if src.get("mode") == "fields":
        fields = ", ".join(kanji_data.field_labels(src.get("mappings", []), "field"))
        return f"from a field: {fields} (deck {src.get('deck', '')})"
    if src.get("mode") == "sentence":
        return "from your sentence fields: " + (", ".join(kres.get("sentence_fields", []))
                                                or "none set")
    text = "from your vocab words: " + (", ".join(kres.get("word_fields", [])) or "none set")
    if kres.get("sentence_only_fields"):
        text += " · sentence cards: " + ", ".join(kres["sentence_only_fields"])
    return text


def _open_kanji_browser(deck: str, char: str):
    from aqt import dialogs, mw
    b = dialogs.open("Browser", mw)
    b.search_for(f'{card_state.deck_query(deck)} {char}' if deck else char)
    b.activateWindow()


def _open_jisho_kanji(char: str):
    QDesktopServices.openUrl(QUrl(f"https://jisho.org/search/{char}%20%23kanji"))


# ── tile ──────────────────────────────────────────────────────────────────────

class KanjiCell(_Tile):
    """A kanji tile, painted on its grid's _TileCanvas (not a widget)."""

    def __init__(self, char: str, level: str, kres: dict, overrides, parent=None):
        super().__init__()
        self._char      = char
        self._level     = level        # "N5".."N1" or "offlist"
        self._info      = kanji_data.data().get(char, {})
        self._stat      = kres["stats"].get(char) or {}
        self._deck      = kres.get("deck", "")
        self._kres      = kres
        self._score     = self._stat.get("score")
        self._known     = bool(self._stat.get("cards"))
        # Only in new / learning cards: the dashed "in your deck, not
        # learned yet" tile, like grammar's (owner 2026-10-17).
        self._in_deck   = not self._known and bool(self._stat.get("pending"))
        self._overrides = overrides
        self._highlighted = False
        # (the tooltip is built on first hover: _Tile.toolTip)

    # ── state ────────────────────────────────────────────────────────────────

    @property
    def _can_override(self) -> bool:
        return self._level != "offlist" and not self._known

    @property
    def _is_found(self) -> bool:
        return self._can_override and self._overrides.is_found(self._char, "")

    @property
    def _is_suspended(self) -> bool:
        return self._level != "offlist" and self._overrides.is_suspended(self._char, "")

    def _level_fg(self) -> str:
        return UNLISTED_FG if self._level == "offlist" else LEVEL_FG.get(self._level, "#888")

    def glow_color(self) -> str:
        """Its share of the grid's glow (_TileCanvas glow="blend"): its heat
        colour when known, its level's when marked found, else dim grey."""
        return _tile_glow(self, self._level_fg())

    # ── hover ────────────────────────────────────────────────────────────────

    def _refresh_tooltip(self):
        esc = html.escape
        lvl = "Off-list" if self._level == "offlist" else self._level
        head = (f"<span style='font-size:30px;'><b>{esc(self._char)}</b></span>"
                f"&nbsp;&nbsp;<span style='color:{self._level_fg()};'><b>{lvl}</b></span>")
        blocks = [head]
        info = self._info
        if info.get("meanings"):
            blocks.append(esc(", ".join(info["meanings"][:6])))
        rd = []
        if info.get("on"):
            rd.append("On: " + esc("、".join(info["on"])))
        if info.get("kun"):
            rd.append("Kun: " + esc("、".join(info["kun"])))
        if rd:
            blocks.append("<br>".join(rd))

        status = []
        if self._is_suspended:
            status.append("✕ Suspended (left out of the counts)")
        elif self._known:
            pct = round(self._score * 100)
            status.append(f"Strength: <b>{heat_name(self._score)}</b> ({pct}%) — "
                          f"from {self._stat['cards']} learned card"
                          f"{'s' if self._stat['cards'] != 1 else ''}")
            status.append(f"Best card: {MATURITY_LABELS[self._stat['best']]}")
        elif self._is_found:
            status.append("★ Marked as found")
        elif self._in_deck:
            status.append("In your deck, not learned yet: it counts once you study one of these cards")
        else:
            status.append("Unseen — no learned card contains it yet")
        blocks.append("<br>".join(status))

        words = self._stat.get("words") or []
        if words:
            shown = [f"{esc(w[:24])} <span style='color:#9a9a9a;'>"
                     f"({card_state.STATE_NAMES[st].lower()})</span>" for w, st, _ in words[:10]]
            more = f"<br>(+{len(words) - 10} more)" if len(words) > 10 else ""
            blocks.append("Your cards:<br>" + "<br>".join(shown) + more)

        learn = (self._kres.get("learn") or {}).get(self._char, [])
        if learn:
            blocks.append("Common words to learn with it:<br>" + esc("、".join(
                d for _r, d, _rd, _l in learn[:6])))

        hints = ["Click: your words and words to learn with this kanji",
                 "Shift+Click: Jisho kanji page"]
        if self._can_override:
            hints += ["Middle-click: toggle marked as found",
                      "Ctrl+Middle-click: toggle suspended"]
        blocks.append("<span style='color:#9a9a9a; font-size:14px;'>"
                      + "<br>".join(hints) + "</span>")
        self.setToolTip("<br><br>".join(blocks))

    # ── search (used by WordGridPanel's search box) ──────────────────────────

    def set_highlighted(self, val: bool):
        if self._highlighted != val:
            self._highlighted = val
            _hl_register(self, val)
            self.update()

    def matches_search(self, text: str) -> bool:
        t = (text or "").strip().lower()
        if not t:
            return False
        if t in self._char:
            return True
        info = self._info
        hay = info.get("meanings", []) + info.get("on", []) + info.get("kun", [])
        if any(t in h.lower() for h in hay):
            return True
        return any(t in w for w, _, _ in self._stat.get("words") or [])

    def status_text(self) -> str:
        lvl = "Off-list" if self._level == "offlist" else self._level
        if self._is_suspended:
            st = "✕ Suspended"
        elif self._known:
            st = f"{heat_name(self._score)} ({round(self._score * 100)}%)"
        elif self._is_found:
            st = "★ Marked as found"
        elif self._in_deck:
            st = "In your deck, not learned yet"
        else:
            st = "Unseen"
        mean = ", ".join(self._info.get("meanings", [])[:2])
        return f"{self._char}  {mean}  —  {lvl}  —  {st}"

    # ── events (from the _TileCanvas) ────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            if not self._can_override:
                return
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                self._overrides.toggle_suspended(self._char, "")
            else:
                self._overrides.toggle_found(self._char, "")
            self._refresh_tooltip()
            self.update()
            self.override_changed.emit()
        elif event.button() == Qt.MouseButton.LeftButton:
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                _open_jisho_kanji(self._char)
            else:
                open_kanji_words(self.window(), self._char, self._kres)

    # ── paint ────────────────────────────────────────────────────────────────

    def paint(self, p: QPainter):
        """Paint the tile; p's origin is its top-left corner."""
        w = h = CELL_W
        suspended, found, known, hov = (self._is_suspended, self._is_found,
                                        self._known, self._hovered)
        gold = _GOLD_MODE["on"] and (known or found) and not suspended
        if suspended:
            p.setBrush(QColor("#1a1a1a"))
            p.setPen(QPen(QColor("#5a1a1a"), 1.5))
            text_col = QColor("#4a4a4a")
        elif known:
            top = heat_color(self._score)          # gold depth in gold mode
            grad = QLinearGradient(0, 0, 0, h)
            grad.setColorAt(0, top.lighter(106))
            grad.setColorAt(1, top.darker(112))   # subtle, so tiles match the legend
            p.setBrush(grad)
            if gold:
                p.setPen(QPen(QColor("#fffbe6" if hov else "#fff2b8"), 1.5))
                text_col = QColor(BRONZE)
            else:
                p.setPen(QPen(top.lighter(140) if hov else top, 1.5))
                text_col = QColor("#ffffff")   # owner: white on every heat colour
        elif found:
            fg = QColor(GOLD_STRONG) if gold else QColor(self._level_fg())
            grad = QLinearGradient(0, 0, 0, h)
            grad.setColorAt(0, fg.lighter(125) if gold else fg)
            grad.setColorAt(1, fg.darker(110) if gold else fg.darker(170))
            p.setBrush(grad)
            p.setPen(QPen(QColor("#fff176" if hov else "#ffe066"), 2.5))
            text_col = QColor(BRONZE) if gold else QColor("#ffffff")
        elif self._in_deck:
            _paint_in_deck(p, hov, QColor(self._level_fg()))
            text_col = QColor(MISSING_GOLD if _GOLD_MODE["on"] else self._level_fg())
        else:
            p.setBrush(QColor("#333333") if hov else QColor("#252525"))
            p.setPen(QPen(QColor("#666"), 1.0))
            text_col = QColor(MISSING_GOLD if _GOLD_MODE["on"] else self._level_fg())
        p.drawRoundedRect(1, 1, w - 2, h - 2, CELL_R, CELL_R)

        f = QFont(); f.setPointSize(15); f.setBold(True)
        f.setStrikeOut(suspended)
        p.setFont(f)
        if gold:
            # light engraved edge under the bronze
            p.setPen(QColor(255, 250, 220, 150))
            p.drawText(QRect(0, 1, w, h), Qt.AlignmentFlag.AlignCenter, self._char)
        elif known and not suspended:
            # Drop shadow so white stays readable on yellow / light green.
            p.setPen(QColor(0, 0, 0, 150))
            p.drawText(QRect(1, 1, w, h), Qt.AlignmentFlag.AlignCenter, self._char)
        p.setPen(text_col)
        p.drawText(QRect(0, 0, w, h), Qt.AlignmentFlag.AlignCenter, self._char)

        badge = "★" if found else "✕" if suspended else ""
        if badge:
            f2 = QFont(); f2.setPointSize(7); f2.setBold(True)
            p.setFont(f2)
            p.setPen(QColor("#8a5a00" if gold else "#ffe066" if found else "#8b2020"))
            p.drawText(QRect(w - 13, 2, 11, 11), Qt.AlignmentFlag.AlignCenter, badge)

        if self._highlighted and _GOLD_MODE["on"]:
            _paint_gold_highlight(p, w, h)
        elif self._highlighted:
            # Search match: white outline (heat tiles span every hue, so a
            # per-tile complement like the word tiles' isn't needed).
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(QColor(BRONZE if gold else "#ffffff"), 3))
            p.drawRoundedRect(1, 1, w - 2, h - 2, CELL_R, CELL_R)


# ── grid ──────────────────────────────────────────────────────────────────────

class KanjiGridPanel(WordGridPanel):
    """Kanji grid for one level, or "All" (every level + Off-list kanji).
    Reuses WordGridPanel's search box behaviour."""

    def __init__(self, kres: dict, level: str, overrides, on_override_changed=None,
                 parent=None):
        QWidget.__init__(self, parent)
        self._kres = kres
        self._level = level
        self._overrides = overrides
        self._on_override_changed = on_override_changed
        self._build()

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        row = QHBoxLayout()
        row.setContentsMargins(8, 8, 8, 4)
        row.setSpacing(6)
        row.addWidget(QLabel("🔍"))
        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("Find a kanji, reading, meaning or word…")
        self._search_edit.setClearButtonEnabled(True)
        self._search_edit.setFixedWidth(300)
        row.addWidget(self._search_edit)
        self._search_status = QLabel("")
        self._search_status.setStyleSheet(HINT_CSS)
        self._search_status.setWordWrap(True)
        row.addWidget(self._search_status, 1)
        outer.addLayout(row)

        self._all_cells = []
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll = scroll
        container = QWidget()
        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(8, 8, 8, 8)
        vbox.setSpacing(8)
        vbox.setAlignment(Qt.AlignmentFlag.AlignTop)

        kres = self._kres
        vbox.addWidget(_heat_legend())
        order = QLabel(
            f"Kanji source: {_source_text(kres)}. Colour = how well you know it: the "
            "average strength of the studied cards that contain it, "
            "from their FSRS stability, difficulty and lapses. Known kanji first, strongest "
            "to weakest (★ marked found last), then kanji only in cards you haven't learned "
            "yet (dashed outline); unseen kanji follow. "
            "Hover: meaning, readings and your cards  ·  Shift+Click: Jisho  ·  "
            "Middle-click: mark as found  ·  Ctrl+Middle-click: suspend.")
        order.setWordWrap(True)
        order.setStyleSheet(HINT_CSS)
        vbox.addWidget(order)

        suspended = {k.split("\t", 1)[0] for k in self._overrides.suspended}
        counts = kanji_data.level_counts(kres, suspended)
        for lvl in (LEVELS if self._level == "All" else [self._level]):
            chars = kres["levels"].get(lvl, [])
            k, n = counts[lvl]
            n_susp = len(chars) - n
            hdr = QLabel(
                f"<span style='color:{LEVEL_FG[lvl]}; font-size:16px; font-weight:bold;'>{lvl} Kanji</span>"
                f"<span style='color:#aaa; font-size:13px;'>  {k:,} / {n:,} known "
                f"({jlpt_data.format_pct(k, n)}) — {n - k:,} unseen"
                + (f" · {n_susp:,} suspended" if n_susp else "") + "</span>")
            hdr.setContentsMargins(0, 4, 0, 0)
            hdr.setProperty("jlpt_sticky", True)      # pinned while scrolling its section
            vbox.addWidget(hdr)
            stats = kres["stats"]
            # Strongest first (owner 2026-10-09).
            learned = sorted((c for c in chars if stats.get(c, {}).get("cards")),
                             key=lambda c: -stats[c]["score"])
            marked = [c for c in chars if c in kres["known"] and c not in learned]
            rest = [c for c in chars if c not in kres["known"]]
            # In your deck, not learned yet: right after the known ones.
            coming = [c for c in rest if stats.get(c, {}).get("pending")]
            rest = [c for c in rest if not stats.get(c, {}).get("pending")]
            self._add_tiles(vbox, learned + marked + coming + rest, lvl)

        if self._level == "All" and kres["offlist"]:
            off = kres["offlist"]
            hdr = QLabel(
                f"<span style='color:{UNLISTED_FG}; font-size:16px; font-weight:bold;'>Off-list Kanji</span>"
                f"<span style='color:#aaa; font-size:13px;'>  {len(off):,} kanji in your cards "
                "that aren't on any JLPT level (not counted in the bars)</span>")
            hdr.setContentsMargins(0, 4, 0, 0)
            hdr.setProperty("jlpt_sticky", True)      # pinned while scrolling its section
            vbox.addWidget(hdr)
            # Same order as the level grids (owner 2026-10-18: it wasn't
            # sorted): strongest first, then only in new / learning cards.
            stats = kres["stats"]
            learned = sorted((c for c in off if stats.get(c, {}).get("cards")),
                             key=lambda c: -stats[c]["score"])
            rest = [c for c in off if not stats.get(c, {}).get("cards")]
            coming = [c for c in rest if stats.get(c, {}).get("pending")]
            rest = [c for c in rest if not stats.get(c, {}).get("pending")]
            self._add_tiles(vbox, learned + coming + rest, "offlist")

        vbox.addStretch()
        scroll.setWidget(container)
        outer.addWidget(scroll)
        self._install_sticky(scroll)
        self._search_edit.textChanged.connect(self._on_search_changed)
        self._search_edit.returnPressed.connect(self._on_search_next)
        self._search_edit.installEventFilter(self)

    def _add_tiles(self, vbox, chars, level):
        cells = [KanjiCell(c, level, self._kres, self._overrides) for c in chars]
        if self._on_override_changed:
            for c in cells:
                c.override_changed.connect(self._on_override_changed)
        self._all_cells.extend(cells)
        vbox.addWidget(_TileCanvas(cells, glow="blend"))


# ── grammar tile ──────────────────────────────────────────────────────────────

class GrammarCell(_Tile):
    """A grammar point: as tall as a word tile, as wide as its pattern. The
    pattern's first form is the label; an English hint (〜で（means）) goes
    on a small second line. Painted on its grid's _TileCanvas."""
    TOOLTIP_CSS = "QToolTip { font-size: 16px; padding: 8px; }"   # on the _TileCanvas

    def __init__(self, gid: str, gres: dict, overrides, parent=None):
        super().__init__()
        self._gid = gid
        self._p = grammar_data.data()[gid]
        self._stat = gres["stats"].get(gid) or {}
        self._deck = gres.get("deck", "")
        self._score = self._stat.get("score")
        self._known = bool(self._stat.get("cards"))
        # In a card of yours that isn't learned yet (new or learning): its own
        # tile look, so you can see it's coming (owner 2026-10-17).
        self._in_deck = not self._known and bool(self._stat.get("words"))
        self._overrides = overrides
        self._highlighted = False
        first = re.split(r"\s+/\s+", self._p["pattern"])[0]
        self._hint = grammar_data._hint(first)
        self._label = re.sub(r"\s*[（(][^）)]*[）)]\s*$", "", first) if self._hint else first
        self._label = self._label.replace("（", "(").replace("）", ")")
        f = QFont(); f.setPointSize(11); f.setBold(True)
        w = QFontMetrics(f).horizontalAdvance(self._label) + 16
        if self._hint:
            f2 = QFont(); f2.setPointSize(7)
            w = max(w, QFontMetrics(f2).horizontalAdvance(self._hint) + 12)
        self.setFixedSize(max(CELL_W, w), CELL_H)
        # (the tooltip is built on first hover: _Tile.toolTip)

    @property
    def _can_override(self) -> bool:
        """Marking found / suspending: points without a learned card."""
        return not self._known

    def glow_color(self) -> str:
        """Its share of the grid's glow, as KanjiCell.glow_color."""
        return _tile_glow(self, LEVEL_FG[self._p["level"]])

    @property
    def _can_mark_found(self) -> bool:
        return not self._known

    @property
    def _is_found(self) -> bool:
        return self._can_mark_found and self._overrides.is_found(self._gid, "")

    @property
    def _is_suspended(self) -> bool:
        return self._overrides.is_suspended(self._gid, "")

    def _refresh_tooltip(self):
        esc = html.escape
        p = self._p
        lvl = p["level"]
        blocks = [f"<span style='font-size:22px;'><b>{esc(p['pattern'])}</b></span>"
                  f"&nbsp;&nbsp;<span style='color:{LEVEL_FG[lvl]};'><b>{lvl}</b></span>",
                  esc(p["meaning"])]
        if p.get("formation"):
            blocks.append("<span style='color:#9a9a9a;'>Formation:</span> " + esc(p["formation"]))
        if p.get("ex_ja"):
            blocks.append(esc(p["ex_ja"]) + "<br><span style='color:#9a9a9a;'><i>"
                          + esc(p.get("ex_en", "")) + "</i></span>")
        status = []
        if self._is_suspended:
            status.append("✕ Suspended (left out of the counts)")
        elif self._known:
            status.append(f"Strength: <b>{heat_name(self._score)}</b> "
                          f"({round(self._score * 100)}%) — from {self._stat['cards']} "
                          f"learned card{'s' if self._stat['cards'] != 1 else ''}")
            status.append(f"Best card: {MATURITY_LABELS[self._stat['best']]}")
        elif self._is_found:
            status.append("★ Marked as found")
        elif self._in_deck:
            status.append("In your deck, not learned yet: it counts once you study one of these cards")
        else:
            status.append("Not learned yet")
        blocks.append("<br>".join(status))
        words = self._stat.get("words") or []
        if words:
            shown = [f"{esc(w)} <span style='color:#9a9a9a;'>({card_state.STATE_NAMES[st].lower()})</span>"
                     for w, st, _ in words[:6]]
            blocks.append("Your cards:<br>" + "<br>".join(shown))
        hints = (["Click: open these cards in the Browser",
                  "Ctrl+Click: find every form of it in your deck"] if words else
                 ["Click: find every form of it in your deck"])
        hints.append("Shift+Click: search the web for this grammar point")
        if p.get("ex_ja"):
            hints.append("Right-click: copy the example sentence")
        if self._can_mark_found:
            hints.append("Middle-click: toggle marked as found")
        if self._can_override:
            hints.append("Ctrl+Middle-click: toggle suspended")
        blocks.append("<span style='color:#9a9a9a; font-size:13px;'>" + "<br>".join(hints) + "</span>")
        self.setToolTip("<br><br>".join(blocks))

    def set_highlighted(self, val: bool):
        if self._highlighted != val:
            self._highlighted = val
            _hl_register(self, val)
            self.update()

    def matches_search(self, text: str) -> bool:
        t = (text or "").strip().lower()
        if not t:
            return False
        p = self._p
        return any(t in (p.get(k) or "").lower() for k in ("pattern", "romaji", "meaning"))

    def status_text(self) -> str:
        p = self._p
        if self._is_suspended:
            st = "✕ Suspended"
        elif self._known:
            st = f"{heat_name(self._score)} ({round(self._score * 100)}%)"
        elif self._is_found:
            st = "★ Marked as found"
        elif self._in_deck:
            st = "In your deck, not learned yet"
        else:
            st = "Not learned"
        return f"{p['pattern']}  {p['meaning'][:40]}  —  {p['level']}  —  {st}"

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            if not self._can_override:
                return
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                self._overrides.toggle_suspended(self._gid, "")
            elif self._can_mark_found:
                self._overrides.toggle_found(self._gid, "")
            else:
                return
            self._refresh_tooltip()
            self.update()
            self.override_changed.emit()
        elif event.button() == Qt.MouseButton.RightButton:
            if self._p.get("ex_ja"):
                _copy_word(self._p["ex_ja"], self.window())   # tooltips can't be selected (owner 2026-10-16)
        elif event.button() == Qt.MouseButton.LeftButton:
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                q = QUrl.toPercentEncoding(f"{self._p['pattern']} 文法 JLPT {self._p['level']}")
                QDesktopServices.openUrl(QUrl("https://www.google.com/search?q=" + bytes(q).decode()))
            elif self._stat.get("words") and not (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
                from aqt import dialogs, mw
                b = dialogs.open("Browser", mw)
                b.search_for("nid:" + ",".join(str(n) for _, _, n in self._stat["words"]))
                b.activateWindow()
            else:
                search_grammar_in_deck(self._gid, self.window())

    def paint(self, p: QPainter):
        """Paint the tile; p's origin is its top-left corner."""
        w, h = self.width(), self.height()
        suspended, found, known, hov = (self._is_suspended, self._is_found,
                                        self._known, self._hovered)
        lvl_fg = QColor(LEVEL_FG[self._p["level"]])
        gold = _GOLD_MODE["on"] and (known or found) and not suspended
        if suspended:
            p.setBrush(QColor("#1a1a1a"))
            p.setPen(QPen(QColor("#5a1a1a"), 1.5))
            text_col = QColor("#4a4a4a")
        elif known:
            top = heat_color(self._score)          # gold depth in gold mode
            grad = QLinearGradient(0, 0, 0, h)
            grad.setColorAt(0, top.lighter(106))
            grad.setColorAt(1, top.darker(112))
            p.setBrush(grad)
            if gold:
                p.setPen(QPen(QColor("#fffbe6" if hov else "#fff2b8"), 1.5))
                text_col = QColor(BRONZE)
            else:
                p.setPen(QPen(top.lighter(140) if hov else top, 1.5))
                text_col = QColor("#ffffff")
        elif found:
            fg = QColor(GOLD_STRONG) if gold else lvl_fg
            grad = QLinearGradient(0, 0, 0, h)
            grad.setColorAt(0, fg.lighter(125) if gold else fg)
            grad.setColorAt(1, fg.darker(110) if gold else fg.darker(170))
            p.setBrush(grad)
            p.setPen(QPen(QColor("#fff176" if hov else "#ffe066"), 2.5))
            text_col = QColor(BRONZE) if gold else QColor("#ffffff")
        elif self._in_deck:
            _paint_in_deck(p, hov, lvl_fg)
            text_col = QColor(MISSING_GOLD) if _GOLD_MODE["on"] else lvl_fg
        else:
            p.setBrush(QColor("#333333") if hov else QColor("#252525"))
            p.setPen(QPen(QColor("#666"), 1.0))
            text_col = QColor(MISSING_GOLD) if _GOLD_MODE["on"] else lvl_fg
        p.drawRoundedRect(1, 1, w - 2, h - 2, CELL_R, CELL_R)

        f = QFont(); f.setPointSize(11); f.setBold(True); f.setStrikeOut(suspended)
        p.setFont(f)
        main = QRect(0, 0, w, h - 10) if self._hint else QRect(0, 0, w, h)
        if gold:
            p.setPen(QColor(255, 250, 220, 150))
            p.drawText(main.translated(0, 1), Qt.AlignmentFlag.AlignCenter, self._label)
        elif known and not suspended:
            p.setPen(QColor(0, 0, 0, 150))
            p.drawText(main.translated(1, 1), Qt.AlignmentFlag.AlignCenter, self._label)
        p.setPen(text_col)
        p.drawText(main, Qt.AlignmentFlag.AlignCenter, self._label)
        if self._hint:
            f2 = QFont(); f2.setPointSize(7)
            p.setFont(f2)
            hint_col = QColor(text_col); hint_col.setAlpha(190)
            p.setPen(hint_col)
            p.drawText(QRect(0, h - 17, w, 13), Qt.AlignmentFlag.AlignCenter, self._hint)

        badge = "★" if found else "✕" if suspended else ""
        if badge:
            f3 = QFont(); f3.setPointSize(7); f3.setBold(True)
            p.setFont(f3)
            p.setPen(QColor("#8a5a00" if gold else "#ffe066" if found else "#8b2020"))
            p.drawText(QRect(w - 13, 2, 11, 11), Qt.AlignmentFlag.AlignCenter, badge)
        if self._highlighted and _GOLD_MODE["on"]:
            _paint_gold_highlight(p, w, h)
        elif self._highlighted:
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(QColor(BRONZE if gold else "#ffffff"), 3))
            p.drawRoundedRect(1, 1, w - 2, h - 2, CELL_R, CELL_R)


def _grammar_source_text(gres: dict) -> str:
    """Where the grammar comes from: the parser (and which fields it reads)
    or a grammar deck's field."""
    src = gres["source"]
    if src.get("mode") == "fields":
        fields = ", ".join(kanji_data.field_labels(src.get("mappings", []), "field"))
        return f"field: {fields or 'none set'} (deck {src.get('deck', '') or 'none'})"
    return "parser · sentence fields: " + (
        ", ".join(gres.get("sentence_fields", []))
        or "none set (add one in Settings → Deck & Fields)")


class GrammarGridPanel(WordGridPanel):
    """Grammar grid for one level or "All"."""

    def __init__(self, gres: dict, level: str, overrides, on_override_changed=None,
                 parent=None):
        QWidget.__init__(self, parent)
        self._gres = gres
        self._level = level
        self._overrides = overrides
        self._on_override_changed = on_override_changed
        self._build()

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        row = QHBoxLayout()
        row.setContentsMargins(8, 8, 8, 4)
        row.setSpacing(6)
        row.addWidget(QLabel("🔍"))
        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("Find a pattern, romaji or meaning…")
        self._search_edit.setClearButtonEnabled(True)
        self._search_edit.setFixedWidth(300)
        row.addWidget(self._search_edit)
        self._search_status = QLabel("")
        self._search_status.setStyleSheet(HINT_CSS)
        self._search_status.setWordWrap(True)
        row.addWidget(self._search_status, 1)
        outer.addLayout(row)

        self._all_cells = []
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll = scroll
        container = QWidget()
        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(8, 8, 8, 8)
        vbox.setSpacing(8)
        vbox.setAlignment(Qt.AlignmentFlag.AlignTop)

        gres = self._gres
        vbox.addWidget(_heat_legend(unseen="Not learned"))
        order = QLabel(
            f"Grammar source: {_grammar_source_text(gres)}. Colour = how well you know it "
            "(the average strength of its learned cards). Learned points first, strongest to "
            "weakest (★ marked found last); the rest follow in OpenJLPT's order. "
            "Hover: meaning, formation and an example  ·  Click: find it in your deck  ·  "
            "Shift+Click: web search  ·  Middle-click: mark as found  ·  Ctrl+Middle-click: suspend.")
        order.setWordWrap(True)
        order.setStyleSheet(HINT_CSS)
        vbox.addWidget(order)

        suspended = {k.split("\t", 1)[0] for k in self._overrides.suspended}
        counts = grammar_data.level_counts(gres, suspended)
        stats = gres["stats"]
        for lvl in (LEVELS if self._level == "All" else [self._level]):
            ids = gres["levels"].get(lvl, [])
            k, n = counts[lvl]
            n_susp = len(ids) - n
            hdr = QLabel(
                f"<span style='color:{LEVEL_FG[lvl]}; font-size:16px; font-weight:bold;'>{lvl} Grammar</span>"
                f"<span style='color:#aaa; font-size:13px;'>  {k:,} / {n:,} known "
                f"({jlpt_data.format_pct(k, n)}) — {n - k:,} not learned"
                + (f" · {n_susp:,} suspended" if n_susp else "") + "</span>")
            hdr.setContentsMargins(0, 4, 0, 0)
            hdr.setProperty("jlpt_sticky", True)      # pinned while scrolling its section
            vbox.addWidget(hdr)
            learned = sorted((g for g in ids if stats.get(g, {}).get("cards")),
                             key=lambda g: -stats[g]["score"])
            marked = [g for g in ids if g in gres["known"] and g not in learned]
            # in your deck, not learned yet: right after the known ones
            coming = [g for g in ids if g not in gres["known"] and stats.get(g, {}).get("words")]
            rest = [g for g in ids if g not in gres["known"] and g not in coming]
            cells = [GrammarCell(g, gres, self._overrides) for g in learned + marked + coming + rest]
            if self._on_override_changed:
                for c in cells:
                    c.override_changed.connect(self._on_override_changed)
            self._all_cells.extend(cells)
            vbox.addWidget(_TileCanvas(cells, glow="blend"))

        if gres.get("unmatched"):
            um = gres["unmatched"]
            lbl = QLabel(f"{len(um):,} grammar card{'s' if len(um) != 1 else ''} didn't match a "
                         "grammar point (or matched several and couldn't be told apart): "
                         + html.escape("、".join(um[:40])) + ("…" if len(um) > 40 else ""))
            lbl.setWordWrap(True)
            lbl.setStyleSheet(HINT_CSS)
            vbox.addWidget(lbl)

        vbox.addStretch()
        scroll.setWidget(container)
        outer.addWidget(scroll)
        self._install_sticky(scroll)
        self._search_edit.textChanged.connect(self._on_search_changed)
        self._search_edit.returnPressed.connect(self._on_search_next)
        self._search_edit.installEventFilter(self)


# ── tab ───────────────────────────────────────────────────────────────────────

class KanjiGrammarTab(QWidget):
    open_kanji_grid = pyqtSignal(str)
    open_grammar_grid = pyqtSignal(str)
    refresh_requested = pyqtSignal()

    def __init__(self, kres: dict, gres: dict, deck_name: str, kanji_overrides,
                 grammar_overrides, parent=None, series_fn=None):
        super().__init__(parent)
        self._deck_name = deck_name
        # () → the progress history series, for the "+N this week" lines
        self._series_fn = series_fn or (lambda: None)
        self._kanji_overrides = kanji_overrides
        self._grammar_overrides = grammar_overrides
        self._bars = []
        self._labels = []
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll)
        self._body = QWidget()
        scroll.setWidget(self._body)
        self._build(kres, gres)
        # Amaterasu: breathing halos past the gold bars and light from above
        # (idle unless the bars are gold).
        self._divine_overlay = DivineOverlay(self._body)

    def update_results(self, kres: dict, gres: dict):
        # Every old widget, not just the layout's direct ones: the intro and
        # its ⟳ sit in a row layout and were left behind, drawn over the new
        # page (owner's screenshot 2026-10-27).
        for w in self._body.findChildren(QWidget):
            if w.parent() is self._body and w is not self._divine_overlay:
                w.hide()
                w.deleteLater()
        old = self._body.layout()
        if old is not None:
            QWidget().setLayout(old)
        self._bars, self._labels = [], []
        self._build(kres, gres)
        self._divine_overlay.raise_()     # new bars were stacked above it

    def set_force_max_gold(self, gold: bool):
        for bar in self._bars:
            bar.set_force_max_gold(gold)
        self._tint_labels(gold)

    def _build(self, kres: dict, gres: dict):
        v = QVBoxLayout(self._body)
        v.setContentsMargins(12, 10, 12, 10)
        v.setSpacing(2)
        v.setAlignment(Qt.AlignmentFlag.AlignTop)
        gold = rank_data.get_rank_info(count_deck_notes(self._deck_name))["is_max_amaterasu"]

        intro = QLabel("Kanji and grammar are tracked separately from your words: "
                       "they don't affect your rank or the word counts. "
                       "Click a bar to open its grid.")
        intro.setWordWrap(True)
        intro.setStyleSheet(HINT_CSS + " margin-bottom: 6px;")
        # Refresh, like the Overview's (owner 2026-10-15)
        top = QHBoxLayout()
        top.addWidget(intro, 1)
        refresh_btn = QPushButton("⟳")
        refresh_btn.setObjectName("kicon")
        refresh_btn.setToolTip("Refresh: recalculate progress to include any kanji, grammar or words\n"
                               "you've marked as found or suspended since this was opened.")
        refresh_btn.clicked.connect(self.refresh_requested)
        top.addWidget(refresh_btn, 0, Qt.AlignmentFlag.AlignTop)
        v.addLayout(top)

        page = v
        page.setSpacing(12)
        # ── Kanji ────────────────────────────────────────────────────────────
        if kres:
            v = _section_card(page)          # section cards (owner 2026-10-18)
            v.setSpacing(2)
            title = QLabel(
                f"<b>JLPT Kanji</b> <span style='color:#888; font-size:12px;'>— "
                f"{html.escape(_source_text(kres))}</span>")
            title.setStyleSheet(SECTION_CSS)
            v.addWidget(title)
            suspended = {k.split("\t", 1)[0] for k in self._kanji_overrides.suspended}
            counts = kanji_data.level_counts(kres, suspended)
            for lvl in ["All"] + LEVELS:
                k, n = counts[lvl]
                self._add_bar_row(v, lvl, "All Kanji" if lvl == "All" else lvl, k, n, gold,
                                  self.open_kanji_grid,
                                  tip=(f"{'All levels' if lvl == 'All' else lvl}: {k:,} of "
                                       f"{n:,} kanji are in a learned card or marked found"
                                       "\nClick to open the kanji grid"))
                if lvl == "All":
                    self._add_delta(v, "kanji", "#ffb74d", "known kanji (all levels)")
            if kres["offlist"]:
                off = QLabel(f"{len(kres['offlist']):,} more kanji in your cards aren't on any "
                             "JLPT level; they're at the end of the All Kanji grid.")
                off.setStyleSheet(HINT_CSS)
                v.addWidget(off)

        # ── Grammar ──────────────────────────────────────────────────────────
        if gres:
            v = _section_card(page)
            v.setSpacing(2)
            title = QLabel(
                f"<b>JLPT Grammar</b> <span style='color:#888; font-size:12px;'>— "
                f"{html.escape(_grammar_source_text(gres))}</span>")
            title.setStyleSheet(SECTION_CSS)
            v.addWidget(title)
            suspended = {k.split("\t", 1)[0] for k in self._grammar_overrides.suspended}
            counts = grammar_data.level_counts(gres, suspended)
            for lvl in ["All"] + LEVELS:
                k, n = counts[lvl]
                self._add_bar_row(v, lvl, "All Grammar" if lvl == "All" else lvl, k, n, gold,
                                  self.open_grammar_grid,
                                  tip=(f"{'All levels' if lvl == 'All' else lvl}: {k:,} of "
                                       f"{n:,} grammar points learned or marked found"
                                       "\nClick to open the grammar grid"))
                if lvl == "All":
                    self._add_delta(v, "grammar", "#ce93d8", "known grammar points (all levels)")
        self._tint_labels(gold)

    def _add_delta(self, v, key, color, what):
        """"+N this week · +N this month" under the All Kanji / All Grammar
        bar (owner 2026-10-15)."""
        from .history_view import delta_label
        lbl = delta_label(self._series_fn(), key, color, what)
        if lbl is not None:
            v.addWidget(lbl)

    def _add_bar_row(self, v, key, text, known, total, gold, signal, tip):
        row_w = QWidget()
        row = QHBoxLayout(row_w)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)
        lbl = QLabel()
        lbl.setFixedWidth(84)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        row.addWidget(lbl)
        bar = LevelBar(key, known, total, force_max_gold=gold, compact=True)
        bar.setToolTip(tip)
        bar.clicked.connect(signal)
        row.addWidget(bar)
        v.addWidget(row_w)
        self._bars.append(bar)
        self._labels.append((text, lbl, "#e0e0e0" if key == "All" else LEVEL_FG[key]))

    def _tint_labels(self, gold: bool):
        for text, lbl, color in self._labels:
            c = rank_data.MAX_RANK_FILL_COLOR if gold else color
            lbl.setText(f"<span style='color:{c}; font-size:12px;'><b>{text}</b></span>")


def _open_grid_window(parent, title: str, panel_factory):
    from .busy import busy
    with busy(parent, "Building the grid…"):     # owner 2026-10-25
        return _build_grid_window(parent, title, panel_factory)


def _build_grid_window(parent, title: str, panel_factory):
    dlg = QDialog(parent)
    dlg.setWindowFlags(dlg.windowFlags() | Qt.WindowType.Window
                       | Qt.WindowType.WindowMinMaxButtonsHint
                       | Qt.WindowType.WindowCloseButtonHint)
    dlg.setWindowTitle(title)
    from .progress_dialog import size_grid_window, place_grid_window
    size_grid_window(dlg, parent)
    v = QVBoxLayout(dlg)
    v.addWidget(panel_factory())
    btn = QPushButton("Close")
    btn.clicked.connect(dlg.accept)
    row = QHBoxLayout(); row.addStretch(); row.addWidget(btn)
    v.addLayout(row)
    from .progress_dialog import _GOLD_MODE, attach_rain, attach_sky
    from . import theme
    theme.apply(dlg, gold=_GOLD_MODE["on"])
    if _GOLD_MODE["on"]:
        from . import divine_text
        divine_text.gold_palette(dlg, True)
        divine_text.apply(dlg, True)
    attach_sky(dlg)                      # stars behind, like every Kotodama window
    attach_rain(dlg)                     # rain on the glass, like every Kotodama window
    dlg.show()
    place_grid_window(dlg, parent)
    if _GOLD_MODE["on"]:
        divine_text.gold_titlebar(dlg, True)    # needs the native window
    return dlg


def open_kanji_words(parent, char: str, kres: dict):
    """Kanji → words (owner 2026-10-14): your cards that use this kanji, and
    the most common words with it you don't know yet (click to copy)."""
    from .progress_dialog import (
        _GOLD_MODE, _open_in_browser, _copy_or_jisho, _meaning_tip, _shown_reading,
        _kanji_form, FREQ_FG,
    )
    from . import freq_data
    info = kanji_data.data().get(char, {})
    stat = kres["stats"].get(char) or {}
    deck = kres.get("deck", "")
    mine = stat.get("words") or []
    learn = (kres.get("learn") or {}).get(char, [])

    dlg = QDialog(parent)
    dlg.setWindowFlags(dlg.windowFlags() | Qt.WindowType.Window
                       | Qt.WindowType.WindowCloseButtonHint)
    dlg.setWindowTitle(f"Words with {char}")
    dlg.resize(560, 640)
    v = QVBoxLayout(dlg)

    lvl = kanji_data.data().get(char, {}).get("level") or ""
    head = QLabel(f"<span style='font-size:34px;'><b>{html.escape(char)}</b></span>"
                  + (f"&nbsp;&nbsp;<span style='color:{LEVEL_FG.get(lvl, '#888')};'>"
                     f"<b>{lvl}</b></span>" if lvl in LEVEL_FG else ""))
    v.addWidget(head)
    if info.get("meanings"):
        mean = QLabel(html.escape(", ".join(info["meanings"][:6])))
        mean.setWordWrap(True)
        v.addWidget(mean)

    def table(headers):
        t = QTableWidget()
        t.setColumnCount(len(headers))
        t.setHorizontalHeaderLabels(headers)
        hh = t.horizontalHeader()
        for c in range(len(headers)):
            hh.setSectionResizeMode(c, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(len(headers) - 2, QHeaderView.ResizeMode.Stretch)
        hh.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        t.verticalHeader().setVisible(False)
        t.setAlternatingRowColors(True)
        return t

    v.addWidget(QLabel(f"<b>Your cards with this kanji</b> ({len(mine):,})"))
    if mine:
        t1 = table(["Word", "Card"])
        _fill_table(t1, [((w, None), (card_state.STATE_NAMES[st], "#9a9a9a")) for w, st, _n in mine])
        t1.itemClicked.connect(lambda item: _open_in_browser(mine[item.row()][2]))
        t1.setMaximumHeight(200)
        v.addWidget(t1)
    else:
        v.addWidget(QLabel("None yet."))

    v.addWidget(QLabel("<b>Words to learn with this kanji</b> — most common first"))
    if learn:
        t2 = table(["Rank", "Level", "Word", "Reading"])
        _fill_table(t2, [
            ((freq_data.rank_text(rank, False) if rank else "—", FREQ_FG if rank else "#777777"),
             (lv or "—", LEVEL_FG.get(lv, "#777777")),
             (d, None),
             (_shown_reading(d, r) or (f"〔{k}〕" if (k := _kanji_form(d, r)) else ""), None))
            for rank, d, r, lv in learn
        ], tooltips=[_meaning_tip(d, r) for _rk, d, r, _lv in learn])
        t2.itemClicked.connect(
            lambda item: _copy_or_jisho(learn[item.row()][1], dlg, learn[item.row()][2]))
        v.addWidget(t2, 1)
        hint = QLabel("Click a word to copy it · Shift+Click to open it on Jisho.org. "
                      "Your cards: click to open the card in the Browser.")
        hint.setWordWrap(True)
        hint.setStyleSheet(HINT_CSS)
        v.addWidget(hint)
    else:
        v.addWidget(QLabel("None: you know every common word with this kanji."))
        v.addStretch()

    row = QHBoxLayout()
    if mine:
        b = QPushButton("Search cards in Browser")
        b.clicked.connect(lambda: _open_kanji_browser(deck, char))
        row.addWidget(b)
    b = QPushButton("Copy kanji")
    b.clicked.connect(lambda: _copy_word(char, dlg))
    row.addWidget(b)
    b = QPushButton("Jisho")
    b.clicked.connect(lambda: _open_jisho_kanji(char))
    row.addWidget(b)
    row.addStretch()
    b = QPushButton("Close")
    b.clicked.connect(dlg.accept)
    row.addWidget(b)
    v.addLayout(row)

    from . import theme
    theme.apply(dlg, gold=_GOLD_MODE["on"])
    if _GOLD_MODE["on"]:
        from . import divine_text
        divine_text.gold_palette(dlg, True)
        divine_text.apply(dlg, True)
    dlg.show()
    if _GOLD_MODE["on"]:
        divine_text.gold_titlebar(dlg, True)


def open_kanji_grid(parent, kres: dict, level: str, overrides, deck_name: str,
                    on_override_changed=None):
    name = "All Kanji" if level == "All" else f"{level} Kanji"
    return _open_grid_window(parent, f"Kanji Grid — {name}  ({deck_name})",
                      lambda: KanjiGridPanel(kres, level, overrides, on_override_changed))


def open_grammar_grid(parent, gres: dict, level: str, overrides, deck_name: str,
                      on_override_changed=None):
    name = "All Grammar" if level == "All" else f"{level} Grammar"
    return _open_grid_window(parent, f"Grammar Grid — {name}  ({deck_name})",
                      lambda: GrammarGridPanel(gres, level, overrides, on_override_changed))


# ── Missing / Marked & Suspended for kanji and grammar ────────────────────────
# The Missing Words and Marked & Suspended tabs get a Vocab / Kanji / Grammar
# dropdown (owner 2026-10-09); these are the kanji and grammar pages.

def _search_grammar_web(p: dict):
    q = QUrl.toPercentEncoding(f"{p['pattern']} 文法 JLPT {p['level']}")
    QDesktopServices.openUrl(QUrl("https://www.google.com/search?q=" + bytes(q).decode()))


def search_grammar_in_deck(gid: str, parent=None):
    """Open the Browser on every note in the analysed deck that contains any
    form of the grammar point (grammar_data.search_regex), to check by eye
    and mark it found (owner 2026-10-14). Finds more than the detection,
    since it's the user who decides."""
    from aqt import dialogs, mw
    from aqt.utils import tooltip
    p = grammar_data.data()[gid]
    deck = (mw.addonManager.getConfig(__name__.split(".")[0]) or {}).get("deck_name", "")
    if not deck:
        tooltip(f"Can't search for {p['pattern']}", parent=parent)
        return
    deck_q = card_state.deck_query(deck)
    rx = grammar_data.search_regex(gid)
    if rx:
        query = '{} "re:{}"'.format(deck_q, rx.replace("\\", "\\\\").replace('"', '\\"'))
    else:
        # No search pattern for this point: its plain written form.
        form = min(grammar_data.pattern_keys(p["pattern"]) or {""}, key=len)
        query = '{} "{}"'.format(deck_q, form.replace('"', '\\"')) if form else deck_q
    try:
        found = mw.col.find_notes(query)
    except Exception:
        found = []
    # The Browser opens even when nothing matches (owner 2026-10-17): the
    # search is there to loosen or edit by hand.
    b = dialogs.open("Browser", mw)
    b.search_for(query)
    b.activateWindow()
    if not found:
        tooltip(f"None of your notes contain {p['pattern']}: the search is in the Browser to edit",
                parent=b)


def _shift_held() -> bool:
    return bool(QApplication.keyboardModifiers() & Qt.KeyboardModifier.ShiftModifier)


def _kg_item(kind: str, key: str):
    """(level, label, meaning, extra columns) for a kanji char / grammar id."""
    if kind == "kanji":
        info = kanji_data.data().get(key, {})
        return (info.get("level", "Off-list"), key, ", ".join(info.get("meanings", [])[:4]),
                ["、".join(info.get("on", [])), "、".join(info.get("kun", []))])
    p = grammar_data.data().get(key, {})
    return (p.get("level", ""), p.get("pattern", key), p.get("meaning", ""),
            [p.get("formation", "")])


def _kg_tip(kind: str, key: str) -> str:
    esc = html.escape
    if kind == "kanji":
        info = kanji_data.data().get(key, {})
        return (f"<b style='font-size:20px;'>{esc(key)}</b><br>{esc(', '.join(info.get('meanings', [])))}"
                f"<br>On: {esc('、'.join(info.get('on', [])))}<br>Kun: {esc('、'.join(info.get('kun', [])))}")
    p = grammar_data.data().get(key, {})
    tip = f"<b>{esc(p.get('pattern', ''))}</b><br>{esc(p.get('meaning', ''))}"
    if p.get("formation"):           # its table column can be cut short ("…")
        tip += f"<br><span style='color:#9a9a9a;'>Formation:</span> {esc(p['formation'])}"
    if p.get("ex_ja"):
        tip += f"<br><br>{esc(p['ex_ja'])}<br><i>{esc(p.get('ex_en', ''))}</i>"
    return tip


def _kg_copy(kind: str, key: str, parent):
    if kind == "kanji":
        _copy_word(key, parent)
    else:
        _copy_word(grammar_data.data()[key]["pattern"].split(" / ")[0].replace("〜", ""), parent)


def _kg_lookup(kind: str, key: str):
    if kind == "kanji":
        _open_jisho_kanji(key)
    else:
        _search_grammar_web(grammar_data.data()[key])


class KGMissingPanel(QWidget):
    """Missing kanji (no learned card, not marked found) or grammar points,
    each with a ★ Found button."""
    changed = pyqtSignal()
    CAPPED_PX = 220          # widest the On / Kun / Formation columns get by themselves

    def __init__(self, kind: str, res: dict, overrides, parent=None):
        super().__init__(parent)
        self._kind, self._overrides = kind, overrides
        self._res = res
        outer = QVBoxLayout(self)
        if kind == "grammar":
            note = QLabel(
                "<b>Why are some obvious points here?</b> Short forms like に, で or が have "
                "several meanings that OpenJLPT lists as separate points (に: time, destination, "
                "place, target, frequency). A sentence can't always tell the parser which one "
                "it is, so only clear cases are detected (3時に → time, 学校に行く → "
                "destination). Mark the ones you know with ★ Found.")
            note.setWordWrap(True)
            note.setStyleSheet(HINT_CSS + " margin-bottom: 4px;")
            outer.addWidget(note)
        ctrl = QHBoxLayout()
        ctrl.addWidget(QLabel("Level:"))
        self._level_combo = QComboBox()
        ctrl.addWidget(self._level_combo)
        self._sort_combo = None
        if kind == "kanji":
            ctrl.addSpacing(16)
            ctrl.addWidget(QLabel("Sort:"))
            self._sort_combo = QComboBox()
            self._sort_combo.addItem("Most common first", "freq")
            self._sort_combo.addItem("By level", "level")
            self._sort_combo.setToolTip("Most common first: KANJIDIC2 newspaper frequency")
            ctrl.addWidget(self._sort_combo)
        ctrl.addSpacing(16)
        self._filter = QLineEdit()
        self._filter.setPlaceholderText("Filter kanji, readings, meanings…" if kind == "kanji"
                                        else "Filter patterns, meanings…")
        self._filter.setMaximumWidth(220)
        ctrl.addWidget(self._filter)
        ctrl.addStretch()
        copy_btn = QPushButton("Copy all to clipboard")
        copy_btn.clicked.connect(self._copy_all)
        ctrl.addWidget(copy_btn)
        outer.addLayout(ctrl)

        headers = (["Level", "Kanji", "Meaning", "On", "Kun", ""] if kind == "kanji"
                   else ["Level", "Pattern", "Meaning", "Formation", ""])
        self._table = QTableWidget()
        self._table.setColumnCount(len(headers))
        self._table.setHorizontalHeaderLabels(headers)
        set_empty_hint(self._table, "Nothing missing to show (or nothing matches the filter).")
        hh = self._table.horizontalHeader()
        # On / Kun (kanji) and Formation (grammar) fit their text only up to
        # CAPPED_PX (owner 2026-11-10: a long kun list made its column ~870 px
        # and pushed ★ Found off the right edge); longer text ends in "…",
        # the row's hover has all of it, and the column can be dragged wider.
        self._capped = (3, 4) if kind == "kanji" else (3,)
        for c in range(len(headers)):
            hh.setSectionResizeMode(c, QHeaderView.ResizeMode.Stretch if c == 2
                                    else QHeaderView.ResizeMode.Interactive if c in self._capped
                                    else QHeaderView.ResizeMode.ResizeToContents)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.verticalHeader().setVisible(False)
        self._table.setAlternatingRowColors(True)
        self._table.itemClicked.connect(self._on_click)
        outer.addWidget(self._table)
        hint = QLabel(("Click a row to copy the kanji · Shift+Click to open it on Jisho."
                       if kind == "kanji" else
                       "Click a row to find every form of it in your deck · Shift+Click to search "
                       "the web for it · Right-click to copy the example sentence."))
        if kind == "grammar":
            # tooltips can't be selected, so right-click copies the example (owner 2026-10-16)
            self._table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            self._table.customContextMenuRequested.connect(self._copy_example)
        hint.setStyleSheet(HINT_CSS)
        outer.addWidget(hint)

        self._level_combo.currentIndexChanged.connect(self._refresh)
        if self._sort_combo:
            self._sort_combo.currentIndexChanged.connect(self._refresh)
        self._filter.textChanged.connect(self._refresh)
        self.update_results(res)

    def _missing(self) -> list:
        if not self._res:
            return []
        out_ = {k.split("\t", 1)[0] for k in self._overrides.suspended | self._overrides.found}
        return [(lvl, key) for lvl in LEVELS for key in self._res["levels"].get(lvl, [])
                if key not in self._res["known"] and key not in out_]

    def _mark_found(self, key: str):
        self._overrides.add_found_many([(key, "")])
        self.update_results(self._res)
        self.changed.emit()

    def update_results(self, res: dict):
        self._res = res
        miss = self._missing()
        cur = self._level_combo.currentData()
        self._level_combo.blockSignals(True)
        self._level_combo.clear()
        self._level_combo.addItem(f"All levels  ({len(miss):,} missing)", "All")
        for lvl in LEVELS:
            self._level_combo.addItem(f"{lvl}  ({sum(1 for l, _ in miss if l == lvl):,} missing)", lvl)
        i = self._level_combo.findData(cur)
        self._level_combo.setCurrentIndex(max(i, 0))
        self._level_combo.blockSignals(False)
        self._refresh()

    def _rows(self) -> list:
        lvl = self._level_combo.currentData() or "All"
        rows = [(l, k) for l, k in self._missing() if lvl == "All" or l == lvl]
        if self._sort_combo and self._sort_combo.currentData() == "freq":
            fr = lambda k: kanji_data.data().get(k, {}).get("freq") or 99_999
            rows.sort(key=lambda r: fr(r[1]))
        t = self._filter.text().strip().lower()
        if t:
            def hit(k):
                _l, label, meaning, extra = _kg_item(self._kind, k)
                return any(t in x.lower() for x in [label, meaning] + extra)
            rows = [r for r in rows if hit(r[1])]
        return rows

    def _refresh(self):
        self._shown = self._rows()
        cells = []
        for lvl, key in self._shown:
            _l, label, meaning, extra = _kg_item(self._kind, key)
            cells.append([(lvl, LEVEL_FG.get(lvl, "#888")), (label, None), (meaning, None)]
                         + [(x, "#aaa") for x in extra])
        _fill_table(self._table, [c + [("", None)] for c in cells],
                    tooltips=[_kg_tip(self._kind, k) for _, k in self._shown])
        for c in self._capped:
            self._table.setColumnWidth(c, min(self._table.sizeHintForColumn(c), self.CAPPED_PX))
        # ★ Found buttons, painted (_ButtonColumn: one template, not a
        # button per row)
        shown = self._shown
        _ButtonColumn.on(self._table, self._table.columnCount() - 1, "★ Found",
                         "font-size: 12px; padding: 1px 6px; color: #ffe066; "
                         "background: #333; border: 1px solid #665a1f; border-radius: 3px;",
                         lambda row: self._mark_found(shown[row][1]),
                         tooltip="Mark as found (counts as known)")

    def _on_click(self, item):
        key = self._shown[item.row()][1]
        if _shift_held():
            _kg_lookup(self._kind, key)
        elif self._kind == "grammar":
            search_grammar_in_deck(key, self.window())
        else:
            _kg_copy(self._kind, key, self.window())

    def _copy_example(self, pos):
        row = self._table.rowAt(pos.y())
        if 0 <= row < len(self._shown):
            ex = grammar_data.data().get(self._shown[row][1], {}).get("ex_ja")
            if ex:
                _copy_word(ex, self.window())

    def _copy_all(self):
        lines = []
        for lvl, key in getattr(self, "_shown", []):
            _l, label, meaning, _x = _kg_item(self._kind, key)
            lines.append(f"{lvl}\t{label}\t{meaning}")
        _copy_to_clipboard("\n".join(lines))


class KGOverridesPanel(QWidget):
    """Kanji or grammar points marked found / suspended by hand, with Revert
    and Reset All (they live in their own override files)."""
    changed = pyqtSignal()

    def __init__(self, kind: str, overrides, parent=None):
        super().__init__(parent)
        self._kind, self._overrides = kind, overrides
        noun = "kanji" if kind == "kanji" else "grammar points"
        outer = QVBoxLayout(self)
        self._found_hdr = QLabel()
        outer.addWidget(self._found_hdr)
        self._found_table = self._make_table()
        set_empty_hint(self._found_table, f"No {noun} marked as found yet. Middle-click a tile in "
                       "the grids to count one you know without a card.")
        outer.addWidget(self._found_table)
        row = QHBoxLayout()
        b = QPushButton("Reset All Found")
        b.setStyleSheet(_quiet_button_style("#f5c518", (245, 197, 24)))
        b.clicked.connect(lambda: self._reset(True))
        row.addWidget(b); row.addStretch()
        outer.addLayout(row)
        self._susp_hdr = QLabel()
        outer.addWidget(self._susp_hdr)
        self._susp_table = self._make_table()
        set_empty_hint(self._susp_table, "Nothing suspended. Ctrl+Middle-click a tile in the grids "
                       "to leave one out of the counts.")
        outer.addWidget(self._susp_table)
        row = QHBoxLayout()
        b = QPushButton("Reset All Suspended")
        b.setStyleSheet(_quiet_button_style("#e05a5a", (224, 90, 90)))
        b.clicked.connect(lambda: self._reset(False))
        row.addWidget(b); row.addStretch()
        outer.addLayout(row)
        hint = QLabel(f"Mark {noun} found or suspended with middle-click / Ctrl+middle-click in "
                      "the grids (Kanji & Grammar tab). Press Refresh to update the bars.")
        hint.setWordWrap(True)
        hint.setStyleSheet(HINT_CSS)
        outer.addWidget(hint)
        self.refresh()

    def _make_table(self) -> QTableWidget:
        headers = ["Level", "Kanji" if self._kind == "kanji" else "Pattern", "Meaning", ""]
        t = QTableWidget()
        t.setColumnCount(len(headers))
        t.setHorizontalHeaderLabels(headers)
        for c in range(len(headers)):
            t.horizontalHeader().setSectionResizeMode(
                c, QHeaderView.ResizeMode.Stretch if c == 2 else QHeaderView.ResizeMode.ResizeToContents)
        t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        t.verticalHeader().setVisible(False)
        t.setAlternatingRowColors(True)
        t.setMinimumHeight(120)
        return t

    def refresh(self):
        self._overrides.reload()
        for table, keys, hdr, found in (
                (self._found_table, self._overrides.found, self._found_hdr, True),
                (self._susp_table, self._overrides.suspended, self._susp_hdr, False)):
            items = sorted((k.split("\t", 1)[0] for k in keys),
                           key=lambda k: (LEVELS.index(_kg_item(self._kind, k)[0])
                                          if _kg_item(self._kind, k)[0] in LEVELS else 9, k))
            color = "#f5c518" if found else "#e05a5a"
            hdr.setText(f"<b style='color:{color};'>{'★ Marked found' if found else '✕ Suspended'}"
                        f"</b> <span style='color:gray;'>({len(items):,})</span>")
            table.setRowCount(len(items))
            # Revert buttons, painted (_ButtonColumn)
            _ButtonColumn.on(table, 3, "Revert",
                             "font-size: 12px; padding: 1px 6px; color: #ccc; "
                             "background: #333; border: 1px solid #555; border-radius: 3px;",
                             lambda row, items=items, f=found: self._revert(items[row], f))
            for i, key in enumerate(items):
                lvl, label, meaning, _x = _kg_item(self._kind, key)
                for c, (text, col) in enumerate(((lvl, LEVEL_FG.get(lvl, "#888")),
                                                  (label, None), (meaning, None))):
                    it = QTableWidgetItem(text)
                    if col:
                        it.setForeground(QColor(col))
                        _gold_item(it)
                    it.setToolTip(_kg_tip(self._kind, key))
                    table.setItem(i, c, it)
        _regold(self)          # the headers were just rewritten

    def _revert(self, key: str, found: bool):
        if found:
            self._overrides.remove_found(key, "")
        else:
            self._overrides.remove_suspended(key, "")
        self.refresh()
        self.changed.emit()

    def _reset(self, found: bool):
        n = len(self._overrides.found if found else self._overrides.suspended)
        if not n:
            return
        what = "marked-found" if found else "suspended"
        noun = "kanji" if self._kind == "kanji" else "grammar points"
        if QMessageBox.question(self, "Reset", f"Remove all {n:,} {what} {noun}?") \
                != QMessageBox.StandardButton.Yes:
            return
        if found:
            self._overrides.clear_found()
        else:
            self._overrides.clear_suspended()
        self.refresh()
        self.changed.emit()


class KindSwitcher(QWidget):
    """A Show: Vocab / Kanji / Grammar dropdown over a stack of pages."""

    def __init__(self, pages: list, parent=None):
        super().__init__(parent)
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        row = QHBoxLayout()
        row.setContentsMargins(8, 6, 8, 0)
        row.addWidget(QLabel("<b>Show:</b>"))
        self.combo = QComboBox()
        self.stack = QStackedWidget()
        for label, w in pages:
            self.combo.addItem(label)
            self.stack.addWidget(w)
        self.combo.currentIndexChanged.connect(self.stack.setCurrentIndex)
        row.addWidget(self.combo)
        row.addStretch()
        v.addLayout(row)
        v.addWidget(self.stack)
