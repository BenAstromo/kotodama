"""
progress_dialog.py
Main results window.  Four tabs:
  1. Overview        — progress bars per level + All combined
  2. Word Grid       — JLPT grid (all levels: known, then missing); Off-list
                       deck cards have their own tab
                       deck cards sorted by frequency
  3. Missing Words   — filterable table
  4. Marked & Suspended — user-managed overrides with revert buttons

Middle-click a tile      → toggle "marked as found"  (yellow outline)
Ctrl + Middle-click      → toggle "suspended"         (tile struck-through / dimmed)
Shift + Click            → look the word up on Jisho (any tile)
Hover                    → meaning (meanings.py, from Jitendex)
Click a missing tile     → copy the word (paste into the browser, add with Yomitan)
"""

from __future__ import annotations

import html
import math

from aqt.qt import *
from aqt import mw
from . import jlpt_data
from .theme import SECTION_CSS, BODY_CSS, HINT_CSS
from . import rank_data
from . import freq_data
from . import card_state
from . import history
from . import meanings
from .jlpt_data import LEVELS, LEVEL_COLORS as LEVEL_FG, LEVEL_BG
from .overrides import Overrides

# Off-list deck words: navy tiles (see STATE_COLORS). UNLISTED_FG is the
# text/legend colour, a lighter navy-blue so it stays readable on the dark
# UI without drifting toward the frequency sky blue.
UNLISTED_FG = "#5a82c8"
UNLISTED_BG = "#00284d"

# Frequency Check bars, labels and grids: light sky blue, so frequency
# words (many of them JLPT words) don't read as "Off-list". FREQ_BG is the
# bars' dark gradient stop.
FREQ_FG = "#6ad0fb"
FOUND_ROW_TEXT = ("Counted as found through another spelling or reading of this word "
                  "(marked on its JLPT entry or the other form). Unmark it there.")
MISSING_GLOW = "#6a6a6a"     # the grids' glow around missing / new tiles
EXTRA_HEIGHT = 210           # px the main window opens above its layout's minimum height
REVIEW_POP_MS = 2500         # the once-a-day Progress Review opens this long after the window
FREQ_BG = "#1f86b3"

# Search-match outlines use each tile's complementary colour — see
# WordCell._highlight_color.

CELL_W   = 42
CELL_H   = 42
CELL_GAP = 3
CELL_R   = 4

# Word tiles have four states (owner 2026-10-17: the desaturated young and
# learning looks were too hard to tell apart): Mature (full colour), Young
# (young, learning and relearning cards: one look), New (in the deck but
# never studied: dashed outline, _paint_in_deck; not counted) and Not found.
MATURITY_SATURATION = {
    card_state.NEW:      0.60,
    card_state.LEARNING: 0.60,
    card_state.YOUNG:    0.60,
    card_state.MATURE:   1.00,
}
# Frequency and Off-list tiles use the owner's explicit palettes instead of
# the saturation scale: frequency gets lighter (whiter) when less mature;
# Off-list is navy, darkest when mature.
STATE_COLORS = {
    "freq": {
        card_state.NEW:      "#b6e7fc",
        card_state.LEARNING: "#b6e7fc",
        card_state.YOUNG:    "#b6e7fc",
        card_state.MATURE:   "#6ad0fb",
    },
    "unlisted": {
        card_state.NEW:      "#003265",
        card_state.LEARNING: "#003265",
        card_state.YOUNG:    "#003265",
        card_state.MATURE:   "#00284d",
    },
}

MATURITY_LABELS = {
    card_state.NEW:      "New",
    card_state.LEARNING: "Young",
    card_state.YOUNG:    "Young",
    card_state.MATURE:   "Mature",
}


# Known tiles are grouped Mature → Young; words marked found by hand (no
# card, so no maturity) come last.
GROUPING_TEXT = "Mature → Young"
_INF = float("inf")


def maturity_group(maturity: dict, nid) -> int:
    """Sort key for grouping known tiles: 0 mature, 1 young (incl.
    learning), 3 marked found (no card) or unknown."""
    if nid is None:
        return 3
    m = maturity.get(nid)
    if m == card_state.MATURE:
        return 0
    if m in (card_state.YOUNG, card_state.LEARNING, card_state.NEW):
        return 1
    return 3


def _paint_in_deck(p, hovered: bool, level_fg: QColor):
    """Brush and pen of a "New / in your deck, not learned yet" tile (word,
    kanji and grammar grids): dark like a missing tile, a dashed outline in
    the level's colour (muted gold in gold mode). The caller draws the
    rounded rect."""
    edge = QColor(MISSING_GOLD) if _GOLD_MODE["on"] else QColor(level_fg)
    p.setBrush(QColor("#424242") if hovered else QColor("#363636"))
    p.setPen(QPen(edge.lighter(130) if hovered else edge, 2.2, Qt.PenStyle.DashLine))


def _jlpt_rank(display: str, reading: str) -> float:
    """Frequency rank of a JLPT list entry, including ranks beyond the top
    20,000 and estimated compound ranks (unranked → infinity)."""
    info = freq_data.word_rank_info(display, reading, jlpt_data.alt_forms(display, reading))
    return _INF if info is None else info[0]


def _is_light(c: QColor) -> bool:
    """True when white text would be hard to read on this fill."""
    r, g, b = c.redF(), c.greenF(), c.blueF()
    return 0.2126 * r + 0.7152 * g + 0.0722 * b > 0.45


def _scale_saturation(color: str, k: float) -> QColor:
    c = QColor(color)
    h, s, l, a = c.getHslF()
    if h < 0:   # achromatic
        return c
    return QColor.fromHslF(h, s * k, l, a)


# ── Amaterasu reward message ────────────────────────────────────────────────

_AMATERASU_MESSAGE_JP = (
    "「言葉は光そのものにあらず。されど、光に照らされて初めてその姿を現す影なり。\n"
    "その意味で、言葉は世界そのものにあらず。世界を覗き見るために与えられし窓にすぎぬ。\n"
    "ゆえに汝よ、言葉の数を数えることなかれ。汝が見つめ得る世界の広さこそ、\n"
    "真に数うべきものなり。」"
)

# The owner's own English localisation (not a translation): always shown
# under the Japanese, in gold mode too — exempt from the "no JA + EN
# duplicates" rule and from tools/check_gold_text.py.
_AMATERASU_MESSAGE_EN = (
    "\u201cWords are not light itself. They are the shadows revealed only when "
    "light falls upon them.\n"
    "In this sense, words are not the world itself. They are merely a window "
    "granted to gaze upon it.\n"
    "Therefore, do not count the words you know. Count instead the breadth "
    "of the world you are able to see.\u201d"
)


def _mystery_pixmap(px: QPixmap) -> QPixmap:
    """Blurred art with a faint "?" on top — hides the top rank's picture
    in the legend until it's reached. The "?" is translucent white with a
    soft dark outline, so it reads on the bright gold parts and the black
    hair alike."""
    w, h = px.width(), px.height()
    # Blur: shrink hard, then scale back up smoothly (twice for softness).
    out = px
    for factor in (18, 9, 4):
        small = out.scaled(max(1, w // factor), max(1, h // factor),
                           Qt.AspectRatioMode.IgnoreAspectRatio,
                           Qt.TransformationMode.SmoothTransformation)
        out = small.scaled(w, h, Qt.AspectRatioMode.IgnoreAspectRatio,
                           Qt.TransformationMode.SmoothTransformation)

    p = QPainter(out)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    font = QFont()
    font.setBold(True)
    font.setPixelSize(int(h * 0.92))
    path = QPainterPath()
    path.addText(0, 0, font, "?")
    br = path.boundingRect()
    path.translate((w - br.width()) / 2 - br.left(), (h - br.height()) / 2 - br.top())
    # Soft dark halo, then a thin dark outline, then the faint white fill.
    for width, alpha in ((7, 18), (2, 55)):
        pen = QPen(QColor(0, 0, 0, alpha), width)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.strokePath(path, pen)
    p.fillPath(path, QColor(255, 255, 255, 95))
    p.end()
    return out


# Separator lines in the rank "?" window: faint, like the main window's card edges.
_INFO_SEP_CSS = "color: rgba(255,255,255,0.08);"


def _add_loyalty_section(vbox):
    """The rank "?" window's "Time with Kotodama" ladder (loyalty.py): every
    tier's gem, name and time, the ones not reached yet dimmed (like
    Discord's badge ladder), the current one outlined, and what's next.
    Written in Japanese directly in Amaterasu mode, like the body text."""
    from . import loyalty
    ja = _GOLD_MODE["on"]
    sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
    sep.setStyleSheet(_INFO_SEP_CSS)
    vbox.addWidget(sep)
    hdr = QLabel("言霊と過ごした時間" if ja else "Time with Kotodama")
    hf = QFont(); hf.setBold(True); hf.setPointSize(12)
    hdr.setFont(hf)
    hdr.setStyleSheet("color: #d4a017; font-size: 12pt; font-weight: bold;")   # the theme's font-size beats setFont
    vbox.addWidget(hdr)
    months, sun = loyalty.shown_months(), loyalty.shown_sun()
    current = loyalty.tier_index(months, sun)
    if ja:
        intro = ("言霊を使った月ごとに数えるバッジです（その月に一度でも使えば1か月）。"
                 "休んでも減りません。お金とは関係なく、ランクとも別です：ランクは覚えた語彙、"
                 "このバッジは言霊と過ごした時間を表します。")
        now = (f"あなた：<b>{loyalty.line(months, True, sun)}</b>" if current is not None
               else "最初のバッジは、言霊を使い始めて1か月後にもらえます。")
    else:
        intro = ("A badge for every month you study with Kotodama (using it at least once in a "
                 "month counts that month). Breaks pause it; it never goes down. It has nothing to "
                 "do with money and is separate from the rank: the rank is the vocabulary you "
                 "know, this badge is your time with Kotodama.")
        now = (f"You: <b>{loyalty.line(months, sun=sun)}</b>" if current is not None
               else "Your first badge comes after your first month with Kotodama.")
    nxt = loyalty.next_step(months, ja, sun)
    text = QLabel(f"<p style='font-size:12px; line-height:150%; color:#cccccc;'>{intro}<br><br>"
                  f"{now}" + (f" &nbsp;·&nbsp; {nxt}" if nxt else "") + "</p>")
    text.setWordWrap(True)
    text.setTextFormat(Qt.TextFormat.RichText)
    vbox.addWidget(text)
    grid = QGridLayout()
    grid.setSpacing(8)
    for i, (m, en, jp, _cols) in enumerate(loyalty.TIERS):
        tile = QFrame()
        reached = current is not None and i <= current
        border = "#d4a017" if i == current else "rgba(255,255,255,0.06)"
        # the main window's dark see-through cards, not grey (owner 2026-10-26)
        tile.setStyleSheet(f"QFrame {{ background: rgba(0,0,0,0.55); border: 1px solid {border}; border-radius: 8px; }}"
                           "QLabel { border: none; background: transparent; }")
        tile.setMinimumHeight(114)                   # gem + name + time, never overlapping
        col = QVBoxLayout(tile)
        col.setContentsMargins(6, 8, 6, 8)
        col.setSpacing(2)
        icon = QLabel()
        icon.setPixmap(loyalty.gem_pixmap(40, i, dim=not reached))
        icon.setFixedHeight(58)                      # never squashed; room for Sun Diamond's rays
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        col.addWidget(icon)
        name = QLabel(jp if ja else en)
        name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name.setStyleSheet(f"color: {'#ffffff' if reached else '#888888'}; font-weight: bold; font-size: 12px;")
        col.addWidget(name)
        # the secret Sun Diamond shows "?" until reached (owner 2026-10-20)
        when = QLabel(loyalty.duration(m, ja) if i != loyalty.SUN or reached else "?")
        when.setAlignment(Qt.AlignmentFlag.AlignCenter)
        when.setStyleSheet("color: #9a9a9a; font-size: 11px;")
        col.addWidget(when)
        grid.addWidget(tile, i // 6, i % 6)          # 12 tiers: 6 + 6
    vbox.addLayout(grid)


FREQ_INFO_EN = (
    "How many of the 20,000 most common words in written Japanese your deck covers: about the "
    "vocabulary of a near-native reader. The bars below are the top 6,000 and 13,800: their sizes "
    "follow modern estimates of the vocabulary N2 and N1 ask for, but the words are the most "
    "common in written Japanese, not the test's words. For the test's words, use the JLPT "
    "Vocabulary bars above; up to N3 they're the guide. Written Japanese matters more from N2 on, "
    "whose reading sections are newspaper-style articles and essays: an N2 or N1 JLPT goal fills "
    "its second step from these bars. The top 13,800 includes the top 6,000. The rank counts how "
    "many words you've learned; this shows whether they're the words that matter.")


LOANWORD_INFO_EN = [
    "English loanwords (カメラ, テーブル, データ…) are words most English speakers understand after "
    "seeing them once or twice in context, so they're marked as found from the start and you don't "
    "need cards for them. It's your choice: if you'd rather learn them like any other word, or "
    "English isn't your first language, press the button to unmark them.",
    "<b>Your JLPT, frequency and goal numbers</b> count marked loanwords straight away, so those "
    "bars stay accurate.",
    "<b>Your rank</b> counts them gradually, as your vocabulary reaches them. Sorted from most to "
    "least common, each marked loanword joins once your learned cards reach its frequency rank "
    "minus the loanwords already counted. Very common ones like テレビ count almost at once; one "
    "ranked 8,000 counts once your rank reaches about 8,000.",
    "Why: marking about 2,500 loanwords at once would skip the early ranks, but you shouldn't need "
    "thousands of cards for words you already understand to reach 20,000. With every loanword "
    "marked, the last one joins at about 17,500 learned cards, exactly where marking them all at "
    "once would have reached 20,000. It also keeps ranks fair to compare: the share image and your "
    "Nakama card say how many loanwords are counted.",
    "Left out: wasei-eigo (サラリーマン), false friends (マンション), Japanese-made shortenings "
    "(パソコン) and loanwords from other languages (パン, アルバイト).",
]


def size_grid_window(dlg, parent):
    """Word / Kanji / Grammar grid pop-ups: tall enough for ~15 tile rows
    (owner 2026-10-26), within the screen."""
    scr = parent.screen().availableGeometry() if parent.screen() else None
    dlg.resize(900, min(890, scr.height() - 40) if scr is not None else 890)


def place_grid_window(dlg, parent):
    """After show(): centred across the main window and level with its bottom
    edge, so the Kotodama title stays in view above it (owner 2026-10-26)."""
    main, fr = parent.window().frameGeometry(), dlg.frameGeometry()
    x = main.center().x() - fr.width() // 2
    y = main.bottom() - fr.height()
    scr = parent.screen().availableGeometry() if parent.screen() else None
    if scr is not None:
        x = max(scr.left(), min(x, scr.right() - fr.width()))
        y = max(scr.top(), min(y, scr.bottom() - fr.height()))
    dlg.move(x, y)


def _show_loanword_info_dialog(parent=None):
    """The "?" beside "Mark English Loanwords as Found": how marked loanwords
    count (owner 2026-10-21: the rank's gradual schedule, card_state)."""
    dlg = QDialog(parent)
    dlg.setWindowTitle("English loanwords")
    dlg.setMinimumWidth(540)
    v = QVBoxLayout(dlg)
    v.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)   # wrapped text gets its full height
    for i, text in enumerate(LOANWORD_INFO_EN):
        lbl = QLabel(text)
        lbl.setWordWrap(True)
        lbl.setFixedWidth(520)          # a fixed width: Qt then gives wrapped text its full height
        lbl.setStyleSheet(BODY_CSS if i < 4 else HINT_CSS)
        v.addWidget(lbl)
    close = QPushButton("Close")
    close.clicked.connect(dlg.accept)
    row = QHBoxLayout()
    row.addStretch()
    row.addWidget(close)
    v.addLayout(row)
    from . import theme
    theme.apply(dlg, gold=_GOLD_MODE["on"])
    if _GOLD_MODE["on"]:
        from . import divine_text
        dlg.setWindowTitle("英語の外来語")
        divine_text.gold_palette(dlg, True)
        divine_text.apply(dlg, True)
        divine_text.gold_titlebar(dlg, True)
    dlg.exec()


def _show_freq_info_dialog(parent=None):
    """The Frequency Check's "?" (owner 2026-10-20): the explanation that used
    to sit above the bars."""
    dlg = QDialog(parent)
    dlg.setWindowTitle("About the Frequency Check")
    dlg.setMinimumWidth(520)
    v = QVBoxLayout(dlg)
    v.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)   # wrapped text gets its full height
    for text, css in ((FREQ_INFO_EN, BODY_CSS),
                      ("The percentage at the top is how much of everyday written text your known "
                       "words cover, weighted by how often each word is used.", HINT_CSS),
                      ("Source: BCCWJ (Balanced Corpus of Contemporary Written Japanese, NINJAL) — "
                       "top 20,000 content words; particles, numerals and proper nouns excluded.", HINT_CSS)):
        lbl = QLabel(text)
        lbl.setWordWrap(True)
        lbl.setFixedWidth(520)          # a fixed width: Qt then gives wrapped text its full height
        lbl.setStyleSheet(css)
        v.addWidget(lbl)
    close = QPushButton("Close")
    close.clicked.connect(dlg.accept)
    row = QHBoxLayout()
    row.addStretch()
    row.addWidget(close)
    v.addLayout(row)
    from . import theme
    theme.apply(dlg, gold=_GOLD_MODE["on"])
    if _GOLD_MODE["on"]:
        from . import divine_text
        dlg.setWindowTitle("頻度チェックについて")
        divine_text.gold_palette(dlg, True)
        divine_text.apply(dlg, True)
        divine_text.gold_titlebar(dlg, True)
    dlg.exec()


def _show_rank_info_dialog(parent=None):
    """Info popup explaining the Kotodama Japanese Rank,
    including all ranks with their artwork and card thresholds.
    The top rank's picture stays blurred behind a "?" until the user's
    (previewed) count reaches it."""

    from . import rank_images

    user_count = (getattr(parent, "_rank_real_total", 0)
                  + getattr(parent, "_rank_debug_offset", 0))

    # Compute the card threshold for the WHITE belt of each rank
    # (i.e. the first belt, global index = rank_idx * 8)
    rank_thresholds = {}
    for i, name_en in enumerate(rank_data.MAIN_RANKS_EN):
        global_belt_idx = i * rank_data.BELTS_PER_RANK   # White Belt of this rank
        rank_thresholds[name_en] = rank_data.BELT_THRESHOLDS[global_belt_idx]

    dlg = QDialog(parent)
    dlg.setWindowTitle("About the Kotodama 言霊 Japanese Rank")
    dlg.setMinimumWidth(820)
    dlg.setMinimumHeight(560)
    dlg.resize(860, 700)
    # the main window's night look (owner 2026-10-26): theme, stars and rain;
    # the scroll area is see-through so the sky shows behind the text
    from . import theme
    theme.apply(dlg, gold=_GOLD_MODE["on"])

    outer = QVBoxLayout(dlg)
    outer.setContentsMargins(0, 0, 0, 8)
    outer.setSpacing(0)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    inner = QWidget()
    vbox = QVBoxLayout(inner)
    vbox.setContentsMargins(32, 24, 32, 24)
    vbox.setSpacing(12)
    scroll.setWidget(inner)
    outer.addWidget(scroll)

    # ── Title ─────────────────────────────────────────────────────────────
    title_lbl = QLabel("About the Kotodama 言霊 Japanese Rank")
    tf = QFont(); tf.setBold(True); tf.setPointSize(14)
    title_lbl.setFont(tf)
    title_lbl.setStyleSheet("color: #d4a017; font-size: 14pt; font-weight: bold;")   # Kotodama gold; size here: the theme beats setFont
    title_lbl.setWordWrap(True)
    vbox.addWidget(title_lbl)

    sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
    sep.setStyleSheet(_INFO_SEP_CSS)
    vbox.addWidget(sep)

    # ── Body text ─────────────────────────────────────────────────────────
    level_counts = {lvl: len(jlpt_data._load_bundled(lvl)) for lvl in LEVELS}
    upto_n2 = sum(level_counts[l] for l in LEVELS[:4])     # cumulative N5–N2 (the "fall short" line)
    level_lines = "".join(
        f"&nbsp;&nbsp;• <b>{lvl}:</b> {n:,} words<br>" for lvl, n in level_counts.items()
    )
    body_text = f"""<p style="font-size:12px; line-height:160%; color:#cccccc;">
<b style="color:#fff;">Why does this rank system exist?</b><br>
The JLPT tracking in this add-on relies on community vocabulary lists.
Because the JLPT organizers stopped publishing official lists in 2010, every available list is an
educated reconstruction of the pre-2010 official lists.<br><br>

The Kotodama JLPT lists (OpenJLPT, based on Jonathan Waller's JLPT lists) contain a total of
{sum(level_counts.values()):,} words
<i>(discrete per-level counts — words appear in only one level)</i>:<br>
{level_lines}<br>

Up to N3, these lists cover most of the vocabulary the test asks for, since the lower levels are written for learners.
From N2 on, these lists are still the words most relevant to the test, but they aren't enough on their own:
the tests use real written Japanese (newspaper-style articles and essays), and if you only study the words
on these lists, you will fall short. They hold {upto_n2:,} words up to N2 against an estimated 6,000,
and {sum(level_counts.values()):,} up to N1 against 10,000–13,800.
So for N2 and N1, learn these lists first, then keep going with the most common words of written Japanese
(the JLPT goal does this in two steps).
At every level, vocabulary is only part of passing: grammar, reading and listening count too.<br><br>

<b style="color:#fff;">How the Rank System Works</b><br>
To give you a realistic map of your progress toward N1 and beyond, this section ignores dictionary tags entirely.
Instead, it calculates your rank based purely on the total volume of cards you have actually learned:
every note in your deck with a card you've studied at least once counts (learning, young or mature),
and so does every word you've marked as found (words you already know without a card).
New cards count once you study them, so adding cards alone doesn't raise your rank.
By measuring your overall raw vocabulary size, this system helps you track the "invisible" words required for native-level comprehension.<br><br>

<b style="color:#fff;">Progress Tiers &amp; Milestones</b><br>
<i style="color:#aaa;">Cumulative: each milestone includes the vocabulary below it. The sizes follow modern estimates for each JLPT level.</i><br>
&nbsp;&nbsp;• <b>0 – 799 Words:</b> The core of the language: greetings, numbers, and the everyday nouns and verbs every sentence leans on.<br>
&nbsp;&nbsp;• <b>800 Words (about N5):</b> Simple everyday Japanese: introducing yourself, shopping, times and dates. The N5 word list covers this level well.<br>
&nbsp;&nbsp;• <b>1,500 Words (about N4):</b> Daily-life basics: short conversations and simple texts about everyday things. The N4 word list covers this level well.<br>
&nbsp;&nbsp;• <b>3,900 Words (about N3):</b> Everyday Japanese starts to open up: casual conversation, simple articles, easier manga and games. The JLPT lists still cover most of what N3 asks for.<br>
&nbsp;&nbsp;• <b>6,000 Words (about N2):</b> Real written Japanese: newspaper-style articles and essays, plus most manga, games and light novels. N2 tests authentic texts, so learn the JLPT lists first, then the most common written words (the Top 6,000 bar).<br>
&nbsp;&nbsp;• <b>13,800 Words (about N1):</b> The entry point for the highest rank. Editorials, novels and work documents, with room to spare at N1. The lists fall well short here; the most common written words (the Top 13,800 bar) fill the gap.<br>
&nbsp;&nbsp;• <b>20,000 Words (Max Rank / Near-Native):</b> The ceiling of the rank: roughly the active vocabulary of an average Japanese adult (the words they use themselves). Most words in everyday reading (news, novels, the web) are familiar. Native speakers recognise far more, often 40,000 or more, so specialist fields and literary Japanese still bring new words.<br><br>

<b style="color:#fff;">Frequency Check</b><br>
Card count alone can be misleading: 13,800 obscure words match the modern N1 vocabulary estimate in number without preparing you for N1.
The Frequency Check below the rank compares your deck against the most common words in written Japanese
(the BCCWJ corpus) — showing how many of the top 13,800 words you know and roughly how much of everyday
text your vocabulary covers.<br><br>

Use this rank to measure your true distance to fluency, independent of whether a card has an official JLPT tag or not.
Keep adding cards, keep reviewing, and watch your rank climb!
</p>"""

    if _GOLD_MODE["on"]:
        # Amaterasu mode: the same explanation in Japanese (owner 2026-10-14).
        level_lines_ja = "".join(
            f"&nbsp;&nbsp;• <b>{lvl}：</b>{n:,} 語<br>" for lvl, n in level_counts.items()
        )
        body_text = f"""<p style="font-size:12px; line-height:160%; color:#cccccc;">
<b style="color:#fff;">このランク制度がある理由</b><br>
このアドオンのJLPT集計は、有志が作った語彙リストに基づいています。
JLPTの主催者は2010年に公式の語彙リストの公開をやめたため、手に入るリストはどれも
2010年以前の公式リストを推定して作り直したものです。<br><br>

言霊のJLPTリスト（OpenJLPT。Jonathan Waller氏のJLPTリストに基づく）は合計
{sum(level_counts.values()):,} 語です
<i>（レベルごとの語数。各語は一つのレベルにだけ入っています）</i>：<br>
{level_lines_ja}<br>

N3までは、試験が求める語彙の大部分をこのリストがカバーしています。下のレベルは学習者向けに書かれているからです。
N2からも、このリストは試験に最も関係の深い語ですが、それだけでは足りません。
試験には本物の書き言葉（新聞のような記事や評論）が使われ、このリストの単語だけを勉強していては届きません：リストはN2までで {upto_n2:,} 語（推定は6,000語）、N1までで {sum(level_counts.values()):,} 語（推定は10,000〜13,800語）です。
そのためN2とN1では、まずこのリストを、次に書き言葉の最頻出語を学びましょう（JLPT目標はこの2段階です）。
どのレベルでも、語彙は合格に必要なものの一部にすぎません。文法・読解・聴解も大切です。<br><br>

<b style="color:#fff;">ランク制度の仕組み</b><br>
N1、そしてその先までの進み具合を現実的に示すため、ここでは辞書のタグを一切使いません。
ランクは、実際に覚えたカードの総数だけで決まります。
デッキ内で一度でも学習したカード（学習中・若い・成熟）を持つノートがすべて数えられ、
発見済みにした単語（カードがなくても知っている単語）も数えられます。
新規カードは学習してから数えられるので、カードを追加するだけではランクは上がりません。
語彙の総量を測ることで、ネイティブ並みの理解に必要な「見えない」単語まで追うことができます。<br><br>

<b style="color:#fff;">段階と節目</b><br>
<i style="color:#aaa;">累計です。各節目はそれ以前の語彙をすべて含みます。語数は各JLPTレベルの現代の推定に合わせています。</i><br>
&nbsp;&nbsp;• <b>0〜799語：</b>言葉の核：あいさつ、数、どの文にも出てくる日常の名詞や動詞。<br>
&nbsp;&nbsp;• <b>800語（N5相当）：</b>簡単な日常の日本語：自己紹介、買い物、時刻や日付。このレベルはN5の語彙リストで十分カバーできます。<br>
&nbsp;&nbsp;• <b>1,500語（N4相当）：</b>日常生活の基本：身の回りのことについての短い会話や簡単な文章。このレベルはN4の語彙リストで十分カバーできます。<br>
&nbsp;&nbsp;• <b>3,900語（N3相当）：</b>日常の日本語が開けてくる段階：くだけた会話、簡単な記事、易しめの漫画やゲーム。N3が求める語彙の大部分は、まだJLPTリストでカバーできます。<br>
&nbsp;&nbsp;• <b>6,000語（N2相当）：</b>本物の書き言葉：新聞のような記事や評論、そして多くの漫画・ゲーム・ライトノベル。N2では本物の文章が出るので、まずJLPTリストを、次に書き言葉の最頻出語を（上位6,000のバー）。<br>
&nbsp;&nbsp;• <b>13,800語（N1相当）：</b>最高ランクの入口。社説、小説、仕事の文書。N1にも余裕を持って臨めます。ここではリストだけでは大きく足りず、書き言葉の最頻出語（上位13,800のバー）がその差を埋めます。<br>
&nbsp;&nbsp;• <b>20,000語（最高ランク・ネイティブ級）：</b>ランクの頂点：平均的な日本人の大人が自分で使う語彙（使用語彙）のおよその量です。日常の読み物（ニュース・小説・ネット）の語はほとんど見覚えがあります。ネイティブが理解できる語（理解語彙）はさらに多く、4万語以上とも言われるので、専門分野や文学的な日本語ではまだ新しい語に出会います。<br><br>

<b style="color:#fff;">頻度チェック</b><br>
カードの数だけでは誤解を招くことがあります。めったに使われない13,800語でも「必要なN1語彙（現代の推定）」と数の上では同じですが、それでN1の準備ができるわけではありません。
ランクの下にある頻度チェックは、あなたのデッキを書き言葉の日本語（BCCWJコーパス）で最もよく使われる語と比べ、
上位13,800語のうちいくつを知っているか、そして日常の文章のおよそどれだけを理解できるかを示します。<br><br>

カードに公式のJLPTタグがあるかどうかに関係なく、このランクで流暢さまでの本当の距離を測りましょう。
カードを足し続け、復習を続けて、ランクが上がっていくのを見届けてください。
</p>"""

    body_lbl = QLabel(body_text)
    body_lbl.setWordWrap(True)
    body_lbl.setTextFormat(Qt.TextFormat.RichText)
    vbox.addWidget(body_lbl)

    sep2 = QFrame(); sep2.setFrameShape(QFrame.Shape.HLine)
    sep2.setStyleSheet(_INFO_SEP_CSS)
    vbox.addWidget(sep2)

    ranks_hdr = QLabel("All Ranks")
    rh_font = QFont(); rh_font.setBold(True); rh_font.setPointSize(12)
    ranks_hdr.setFont(rh_font)
    ranks_hdr.setStyleSheet("color: #d4a017; font-size: 12pt; font-weight: bold;")
    vbox.addWidget(ranks_hdr)

    # ── Rank cards ────────────────────────────────────────────────────────
    # For each rank: coloured band with rank name + threshold + art if available
    for i, name_en in enumerate(rank_data.MAIN_RANKS_EN):
        name_jp     = rank_data.MAIN_RANKS_JP[i]
        col_a, col_b = rank_data.RANK_COLORS[name_en]
        threshold   = rank_thresholds[name_en]
        next_thresh = (rank_thresholds[rank_data.MAIN_RANKS_EN[i + 1]]
                       if i + 1 < len(rank_data.MAIN_RANKS_EN) else rank_data.MAX_CARDS)

        card_widget = QWidget()

        def _rgba(hex_col: str, alpha: int) -> str:
            h = hex_col.lstrip("#")
            r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            return f"rgba({r},{g},{b},{alpha})"

        ca_full  = _rgba(col_a, 255)
        ca_mid   = _rgba(col_a, 180)
        cb_right = _rgba(col_b, 160)

        if name_en == "Nihonjin":
            card_widget.setStyleSheet(
                f"background: qlineargradient(x1:0, y1:0, x2:1, y2:0, "
                f"stop:0 {ca_full}, stop:0.5 {ca_mid}, stop:1 {cb_right}); "
                f"border: 1px solid rgba(200,200,200,200); border-radius: 8px;"
            )
        elif name_en == "Amaterasu":
            cb_bright = _rgba(col_b, 200)
            card_widget.setStyleSheet(
                f"background: qlineargradient(x1:0, y1:0, x2:1, y2:0, "
                f"stop:0 {ca_full}, stop:0.5 {ca_mid}, stop:1 {cb_bright}); "
                f"border: 2px solid {_rgba(col_a, 240)}; border-radius: 8px;"
            )
        else:
            card_widget.setStyleSheet(
                f"background: qlineargradient(x1:0, y1:0, x2:1, y2:0, "
                f"stop:0 {ca_full}, stop:0.6 {ca_mid}, stop:1 {cb_right}); "
                f"border: 1px solid {_rgba(col_b, 140)}; border-radius: 8px;"
            )

        # Glow: Nihonjin (index 5) → Amaterasu (index 9), escalating intensity.
        # Uses the shared helper so values stay consistent with the live badge.
        glow_blur, glow_alpha = _rank_glow_params(i)
        if glow_blur > 0:
            glow_col = QColor(col_b)
            glow_col.setAlpha(glow_alpha)
            shadow = QGraphicsDropShadowEffect(card_widget)
            shadow.setBlurRadius(glow_blur)
            shadow.setOffset(0, 0)
            shadow.setColor(glow_col)
            card_widget.setGraphicsEffect(shadow)
        card_layout = QHBoxLayout(card_widget)
        card_layout.setContentsMargins(14, 10, 14, 10)
        card_layout.setSpacing(16)

        # Text column
        text_col = QVBoxLayout()
        text_col.setSpacing(2)

        # Japanese name (primary, large) with English subtitle inline after it
        name_lbl = QLabel(
            f"<span style='font-size:18px; font-weight:bold; color:#ffffff;'>{name_jp}</span>"
            f"&nbsp;&nbsp;<span style='font-size:10px; color:rgba(255,255,255,180);'>{name_en}</span>"
        )
        name_lbl.setTextFormat(Qt.TextFormat.RichText)
        name_lbl.setStyleSheet("background: transparent;")
        name_ds = QGraphicsDropShadowEffect(name_lbl)
        name_ds.setBlurRadius(8); name_ds.setOffset(1, 2)
        name_ds.setColor(QColor(0, 0, 0, 220))
        name_lbl.setGraphicsEffect(name_ds)
        text_col.addWidget(name_lbl)

        if threshold == 0:
            range_txt = f"0 – {next_thresh - 1:,} cards"
        elif name_en == "Amaterasu":
            range_txt = f"{threshold:,} – {rank_data.MAX_CARDS:,} cards"
        else:
            range_txt = f"{threshold:,} – {next_thresh - 1:,} cards"

        thresh_lbl = QLabel(
            f"Starts at <b>{threshold:,} cards</b>  ·  {range_txt}"
        )
        thresh_lbl.setStyleSheet(
            "color: #ffffff; font-size: 12px; background: rgba(0,0,0,140); "
            "border-radius: 4px; padding: 2px 6px;"
        )
        text_col.addWidget(thresh_lbl)
        card_layout.addLayout(text_col, 1)

        # Art thumbnail (right side)
        art_bytes = rank_images.get_rank_art(name_en)
        if art_bytes:
            px = QPixmap()
            px.loadFromData(art_bytes, "JPEG")
            if not px.isNull():
                scaled = px.scaledToHeight(80, Qt.TransformationMode.SmoothTransformation)
                if name_en == rank_data.MAIN_RANKS_EN[-1] and user_count < threshold:
                    scaled = _mystery_pixmap(scaled)
                    card_widget.setToolTip("Reach this rank to reveal it")
                art_lbl = QLabel()
                art_lbl.setPixmap(scaled)
                art_lbl.setStyleSheet("background: transparent; border: none;")
                art_lbl.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight)
                card_layout.addWidget(art_lbl)

        vbox.addWidget(card_widget)

    _add_loyalty_section(vbox)
    vbox.addStretch()

    # ── Close button ──────────────────────────────────────────────────────
    close_row = QHBoxLayout()
    close_row.setContentsMargins(16, 0, 16, 0)
    close_row.addStretch()
    close_btn = QPushButton("Close")
    close_btn.setFixedWidth(90)
    close_btn.clicked.connect(dlg.accept)
    close_row.addWidget(close_btn)
    outer.addLayout(close_row)

    if _GOLD_MODE["on"]:
        from . import divine_text
        dlg.setWindowTitle("言霊 日本語ランクについて")
        divine_text.gold_palette(dlg, True)
        divine_text.apply(dlg, True)
        dlg.winId()
        divine_text.gold_titlebar(dlg, True)
    attach_sky(dlg)                      # stars behind, like every Kotodama window
    attach_rain(dlg)                     # rain on the glass, like every Kotodama window
    dlg.exec()


# Seconds into the Amaterasu intro (7.5 s clip; her light peaks at 0.55 s)
# when the message window opens. Was the intro's end (owner 2026-10-26:
# "slightly too long").
AMATERASU_MESSAGE_AT = 5.5


def _show_amaterasu_dialog(parent=None):
    """One-time reward shown when the user's REAL deck count reaches
    20,000 cards — Tenth-Degree Black Belt Amaterasu, the top of the rank ladder."""
    dlg = QDialog(parent)
    dlg.setWindowTitle("天照大神")
    dlg.setMinimumWidth(800)          # 660 → 800 with the larger Japanese message
    dlg.setStyleSheet(
        "QDialog { background-color: #14110a; }"
        "QLabel#amaterasuTitle { font-size: 28pt; font-weight: bold; }"   # owner 2026-10-26: title too small
    )

    layout = QVBoxLayout(dlg)
    layout.setSpacing(18)
    layout.setContentsMargins(36, 32, 36, 28)

    title = QLabel("天照大神")
    title.setObjectName("amaterasuTitle")
    title_font = QFont()
    title_font.setBold(True)
    title_font.setPointSize(28)
    title.setFont(title_font)
    title.setAlignment(Qt.AlignmentFlag.AlignCenter)
    # Sizes go in the label's own style sheet: the main window's theme rule
    # (QDialog#kotodama QWidget { font-size }) reaches this owned pop-up and
    # beats setFont (owner 2026-10-26: the title had shrunk).
    title.setStyleSheet(f"color: {rank_data.MAX_RANK_FILL_COLOR}; font-size: 28pt; font-weight: bold;")
    # Gold glow matching the Amaterasu bars' accent color (near-white gold),
    # not black — the kanji should radiate light like the progress bars do.
    glow = QGraphicsDropShadowEffect(title)
    glow.setBlurRadius(40)
    glow.setOffset(0, 0)
    glow_col = QColor(rank_data.RANK_COLORS["Amaterasu"][1])
    glow_col.setAlpha(220)
    glow.setColor(glow_col)
    title.setGraphicsEffect(glow)
    layout.addWidget(title)

    sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
    sep.setStyleSheet(f"color: {rank_data.MAX_RANK_FILL_COLOR};")
    layout.addWidget(sep)

    jp_lbl = QLabel(_AMATERASU_MESSAGE_JP)
    jp_lbl.setWordWrap(True)
    jp_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    jp_font = QFont()
    jp_font.setPointSize(13)
    jp_lbl.setFont(jp_font)
    # Japanese leads, the English is the quiet aside (owner 2026-10-26: by
    # Amaterasu the user reads Japanese). The window is wide enough that each
    # line fits on its own row: wrapped lines got clipped at this size.
    jp_lbl.setStyleSheet("color: #f5f0e0; line-height: 150%; font-size: 13pt;")
    layout.addWidget(jp_lbl)

    # The owner's own English localisation of the message — deliberately
    # kept even though Amaterasu is otherwise all Japanese (owner
    # 2026-10-09: it was written, not machine-translated). Not a "duplicate".
    en_lbl = QLabel(_AMATERASU_MESSAGE_EN)
    en_lbl.setWordWrap(True)
    en_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    en_lbl.setStyleSheet("color: #a89f8a; font-size: 12px; font-style: italic;")
    layout.addWidget(en_lbl)

    btn_row = QHBoxLayout()
    btn_row.addStretch()
    close_btn = QPushButton("閉じる")
    close_btn.setStyleSheet(
        f"QPushButton {{ background-color: {rank_data.MAX_RANK_FILL_COLOR}; "
        "color: #14110a; font-weight: bold; padding: 6px 22px; "
        "border-radius: 4px; border: none; }}"
        f"QPushButton:hover {{ background-color: #ffe45c; }}"
    )
    close_btn.clicked.connect(dlg.accept)
    btn_row.addWidget(close_btn)
    btn_row.addStretch()
    layout.addLayout(btn_row)

    from . import divine_text
    dlg.winId()                                   # native window for the title bar
    divine_text.gold_titlebar(dlg, True)
    dlg.exec()


class _AscensionFlash(QWidget):
    """A white-gold burst over the whole window: fades up fast, holds, then
    the page slowly fades back in from the light (owner 2026-10-09). Centred
    on `center` (the light behind Amaterasu) when given."""

    RISE = 0.288                       # seconds to full brightness (8 % of 3.6 s)

    def __init__(self, window: QWidget, center: QPointF | None = None):
        super().__init__(window)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setGeometry(window.rect())
        self._center = center
        self._a = 0.0
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(3600)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.valueChanged.connect(self._step)
        self._anim.finished.connect(self.deleteLater)
        self.raise_()
        self.show()
        self._anim.start()

    def _step(self, t):
        # 0–8 %: flash up · 8–25 %: hold · 25–100 %: ease back out
        t = float(t)
        if t < 0.08:
            self._a = t / 0.08
        elif t < 0.25:
            self._a = 1.0
        else:
            self._a = (1.0 - (t - 0.25) / 0.75) ** 1.6
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        r = self.rect()
        c = self._center if self._center is not None else QPointF(r.center())
        # Reach every corner from an off-centre light too.
        reach = max(math.hypot(c.x() - x, c.y() - y)
                    for x in (r.left(), r.right()) for y in (r.top(), r.bottom()))
        g = QRadialGradient(c, max(reach, max(r.width(), r.height()) * 0.75))
        g.setColorAt(0.0, QColor(255, 255, 255, int(255 * self._a)))
        g.setColorAt(0.5, QColor(255, 250, 225, int(250 * self._a)))
        g.setColorAt(1.0, QColor(255, 232, 150, int(235 * self._a)))
        p.fillRect(r, QBrush(g))
        p.end()


# Set while an ascension is about to play: a badge built meanwhile (the real
# crossing is detected before the Overview's badge exists) waits in the dark
# instead of starting on the bright loop.
_ASCENSION = {"pending": False}


def _scroll_to_badge(overview, badge):
    """Ascension (owner 2026-10-17, to-do 2c): show the Vocabulary tab and
    glide its scroll so Amaterasu's badge sits in the middle of the view —
    on the first open past 20,000 and when a Refresh crosses it with the
    window already open."""
    try:
        win = overview.window()
        tabs = getattr(win, "_tabs", None)
        if tabs is not None and tabs.indexOf(overview) >= 0:
            tabs.setCurrentWidget(overview)
        scroll = getattr(overview, "_scroll", None)
        if scroll is None or badge is None:
            return
    except RuntimeError:
        return
    # a moment later: the window has just appeared and may not be laid out
    QTimer.singleShot(40, lambda: _glide_to(overview, scroll, badge))


def _glide_to(overview, scroll, badge, tries: int = 0):
    try:
        y = badge.mapTo(scroll.widget(), QPoint(0, 0)).y()
        vp = scroll.viewport().height()
        sb = scroll.verticalScrollBar()
        if sb.maximum() == 0 and y + badge.height() > vp and tries < 25:
            # the scroll range isn't laid out yet: try again shortly
            QTimer.singleShot(60, lambda: _glide_to(overview, scroll, badge, tries + 1))
            return
        target = max(sb.minimum(), min(sb.maximum(), int(y - (vp - badge.height()) / 2)))
        anim = QPropertyAnimation(sb, b"value", overview)
        anim.setDuration(650)
        anim.setStartValue(sb.value())
        anim.setEndValue(target)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.start()
        overview._scroll_anim = anim          # kept alive while it runs
    except RuntimeError:
        pass


def _ascend(parent: QWidget):
    """Crossing into Amaterasu: the ascension flash over the window, then
    (while it fades) the Amaterasu message. Waits until the window is on
    screen, since crossings are detected while the Overview is built.

    With her animated picture (owner 2026-10-15): the intro plays in the
    badge, dark at first with the divine light held back; the flash, centred
    on the light behind her, peaks as that light blooms; the message comes
    when the intro ends.

    Sound (owner 2026-10-16, ambience.py): the star ignition starts with
    the intro's first frame, so its bell strike lands with the bloom and the
    flash; the Ringing Sun and the heartbeat follow from it. The old chime
    only plays if the ambience can't."""
    _ASCENSION["pending"] = True

    def go(tries=0):
        try:
            win = parent.window() if parent is not None else None
        except RuntimeError:          # the dialog was closed meanwhile
            _ASCENSION["pending"] = False
            return
        if win is None or not win.isVisible():
            if tries < 25:
                QTimer.singleShot(120, lambda: go(tries + 1))
            else:
                _ASCENSION["pending"] = False
                _show_amaterasu_dialog(parent)
            return
        _ASCENSION["pending"] = False
        badge = getattr(parent, "_rank_badge", None)
        _scroll_to_badge(parent, badge)       # to-do (2c): bring her on screen first
        try:
            intro = badge is not None and badge.start_intro()
        except RuntimeError:
            intro = False

        sound = {"ok": None}

        def ignite():
            if sound["ok"] is None:
                from . import ambience
                sound["ok"] = ambience.get().ascend()

        def flash():
            ignite()
            center = None
            try:
                if intro and badge.isVisible():
                    center = QPointF(badge.mapTo(win, badge.halo_point().toPoint()))
            except RuntimeError:
                pass
            _AscensionFlash(win, center)
            if not sound["ok"] and kotodama_in_front():
                from . import chime
                chime.play()                 # quiet bell (no ambience)

        def message():
            try:
                _show_amaterasu_dialog(parent)
            except RuntimeError:      # closed during the flash
                pass

        if not intro:
            # No intro: the flash peaks with the ignition's strike.
            from . import ambience
            ignite()
            lead = int((ambience.STRIKE - _AscensionFlash.RISE) * 1000)
            QTimer.singleShot(lead, flash)
            QTimer.singleShot(lead + 1300, message)
            return

        from . import rank_video
        bloom = rank_video.INTRO_BLOOM.get(badge._video.rank, (0.0, 0.0))[1]

        def intro_time():
            try:
                return badge.intro_time()
            except RuntimeError:
                return None

        def wait_bloom(n=0):
            # The ignition starts with the intro's first frame on screen; the
            # flash starts so it's at full brightness as her light is.
            try:
                if badge.intro_shown():
                    ignite()
            except RuntimeError:
                pass
            t = intro_time()
            if t is None or t >= bloom - _AscensionFlash.RISE or n >= 300:
                flash()
                wait_end()
            else:
                QTimer.singleShot(10, lambda: wait_bloom(n + 1))

        def wait_end(n=0):
            t = intro_time()
            if t is None or t >= AMATERASU_MESSAGE_AT or n >= 120:
                message()
            else:
                QTimer.singleShot(100, lambda: wait_end(n + 1))

        wait_bloom()
    QTimer.singleShot(0, go)


# ── helpers ───────────────────────────────────────────────────────────────────

def _rank_glow_params(rank_index: int) -> tuple:
    """Return (blur_radius, alpha 0-255) for the rank card/badge glow effect.

    Glowing starts at Nihonjin (rank_index 5) and escalates each rank.
    Amaterasu (index 9) is dramatically more intense — a strong visible spike
    that reads as "this is the max" without covering text or art.

    rank_index:  5     6     7     8     9
    rank:        Niho  Sam   Sho   Emp   Ama
    blur:        28    40    52    64    110
    alpha:       150   175   200   225   255
    """
    if rank_index < 5:
        return 0, 0   # no glow for ranks below Nihonjin
    if rank_index == 9:
        return 110, 255   # Amaterasu: exaggerated
    t = rank_index - 5   # 0..3 for Nihonjin..Emperor
    blur  = 28 + t * 12   # 28 → 64
    alpha = 150 + t * 25  # 150 → 225
    return blur, alpha


def _open_in_browser(nid: int):
    from aqt import dialogs
    b = dialogs.open("Browser", mw)
    b.search_for(f"nid:{card_state.real_nid(nid)}")   # parsed sentence words → their note
    b.activateWindow()

def _copy_to_clipboard(text: str):
    QApplication.clipboard().setText(text)

def _open_jisho(word: str, reading: str = ""):
    # A kana word is searched by its kanji spelling, so the right entry
    # comes first (かく → 掻く, not 書く).
    QDesktopServices.openUrl(QUrl(f"https://jisho.org/search/{_kanji_form(word, reading) or word}"))

def _copy_word(word: str, parent=None):
    """Copy a missing word so the user can paste it into the browser and
    make the card with Yomitan (owner's choice over creating notes here)."""
    from aqt.utils import tooltip
    _copy_to_clipboard(word)
    tooltip(f"Copied {word}", parent=parent)

def _copy_or_jisho(word: str, parent=None, reading: str = ""):
    """Row/chip click: Shift+click opens Jisho (as on tiles), else copy."""
    if QApplication.keyboardModifiers() & Qt.KeyboardModifier.ShiftModifier:
        _open_jisho(word, reading)
    else:
        _copy_word(word, parent)

def _search_term_in_browser(display: str, reading: str):
    """Open the Anki Browser and search for this word's text across the
    whole collection — useful for checking whether a 'missing' word
    actually exists under a different note type or field than configured."""
    from aqt import dialogs
    terms = []
    for t in (display, reading):
        if t:
            t_escaped = t.replace('"', '\\"')
            term = f'"{t_escaped}"'
            if term not in terms:
                terms.append(term)
    if not terms:
        return
    query = " or ".join(terms)
    b = dialogs.open("Browser", mw)
    b.search_for(query)
    b.activateWindow()


def count_deck_notes(deck_name: str) -> int:
    """Note count for the Vocabulary Rank System.

    Deliberately independent of JLPT field mappings/note-type filters —
    every note in the deck (and its sub-decks) with a studied card
    counts toward the 20,000 rank target, whether or not it's a JLPT-listed
    word, a different note type, or has any of the mapped fields at all.
    New cards count once studied (owner 2026-10-21). Words marked
    found (with no card) count too (owner 2026-10-10; card_state.rank_count).
    """
    from . import _cfg
    return card_state.rank_count(
        deck_name, bool(_cfg().get("ignore_suspended_cards", False)))


# ── Custom progress bar ───────────────────────────────────────────────────────

# ── Amaterasu silhouette (fractions of her 480×320 picture) ───────────────────
# The light comes from behind her: DivineOverlay cuts these feathered
# ellipses out of its light so her bun, face and body sit in shadow on top of
# it, with the light creeping back in at their edges (rim light). Hand-fitted
# to the art: (centre x, centre y, radius x, radius y, how much light is
# removed at the centre 0–1, where the feather starts 0–1).
AMATERASU_BUN = (0.494, 0.19)        # also the rays' vanishing point
AMATERASU_SHADOW = (
    (0.494, 0.19, 0.135, 0.205, 1.00, 0.70),   # hair bun: fully hides the ray origin
    (0.494, 0.33, 0.070, 0.120, 0.97, 0.60),   # face
    (0.494, 0.40, 0.130, 0.170, 0.93, 0.60),   # hair falling to the shoulders
    (0.500, 0.56, 0.180, 0.180, 0.90, 0.65),   # torso, crossed arms
    (0.500, 0.78, 0.290, 0.240, 0.88, 0.70),   # robe
    (0.200, 0.72, 0.320, 0.400, 0.82, 0.60),   # long hair sweeping out to the left
    (0.800, 0.72, 0.320, 0.400, 0.82, 0.60),   # … and to the right
)
# The sky of her picture is blown out to white-gold (fading in from just
# outside the picture so its top and side edges vanish into the badge), down
# to this fraction of the picture's height, then fading out by
# AMATERASU_SKY_END so the hair along the lower edges isn't washed.
AMATERASU_SKY_FULL, AMATERASU_SKY_END = 0.36, 0.62
# With her animated picture only the top edge melts away, by this fraction.
AMATERASU_VIDEO_SKY_END = 0.14


# ── Amaterasu gold mode (shared) ─────────────────────────────────────────────
# Set by ProgressDialog._apply_gold (real 20,000 or the debug preview). Grids
# read it at paint time, so tiles built before it was known still follow it.
_GOLD_MODE = {"on": False}

# Gold word tiles (top, bottom) by card maturity: mature = deepest gold;
# None = marked found (no card) or unknown maturity.
_GOLD_TILE = {
    card_state.MATURE:   ("#ffe270", "#d9a400"),
    card_state.YOUNG:    ("#ffeb99", "#e6b92e"),
    card_state.LEARNING: ("#ffeb99", "#e6b92e"),   # learning looks young (owner 2026-10-17)
    card_state.NEW:      ("#ffeb99", "#e6b92e"),
    None:                ("#ffe270", "#d9a400"),
}


HAIR_BLACK = "#0d0b08"     # gold mode: text on gold is black, like her hair
MISSING_GOLD = "#d4ad3c"   # gold mode: missing tiles' text (7.2:1 on the dark tile)


def _bar_text(p: QPainter, rect: QRect, text: str, fill: QRect, gold: bool) -> bool:
    """Gold mode bar text (owner): black like her hair over the gold fill,
    with a soft light edge; gold over the dark empty track (black wouldn't
    show there). Returns False outside gold mode so the caller draws its
    usual white text."""
    if not gold:
        return False
    p.save()
    p.setClipRegion(QRegion(rect).subtracted(QRegion(fill)))
    p.setPen(QColor(0, 0, 0, 200))
    p.drawText(rect.adjusted(1, 1, 1, 1), Qt.AlignmentFlag.AlignCenter, text)
    p.setPen(QColor("#f5c518"))
    p.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
    p.setClipRect(fill)
    p.setPen(QColor(255, 250, 220, 170))
    p.drawText(rect.translated(0, 1), Qt.AlignmentFlag.AlignCenter, text)
    p.setPen(QColor(HAIR_BLACK))
    p.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
    p.restore()
    return True


# Search-match highlight in gold mode: an animated gold ring (owner), the
# same for every level. Only the highlighted tiles are repainted, by one
# shared timer that runs only while there are highlighted tiles in gold mode.
_HL_CELLS: set = set()
_HL_TIMER = {"t": None}


def _hl_register(cell, on: bool):
    (_HL_CELLS.add if on else _HL_CELLS.discard)(cell)
    t = _HL_TIMER["t"]
    if _HL_CELLS and _GOLD_MODE["on"]:
        if t is None:
            t = _HL_TIMER["t"] = QTimer()
            t.setInterval(50)
            t.timeout.connect(_hl_tick)
        if not t.isActive():
            t.start()
    elif t is not None:
        t.stop()


def _hl_tick():
    if not _HL_CELLS or not _GOLD_MODE["on"]:
        _HL_TIMER["t"].stop()
        return
    for c in list(_HL_CELLS):
        try:
            c.update()
        except RuntimeError:          # tile deleted (grid rebuilt / closed)
            _HL_CELLS.discard(c)


def _paint_gold_highlight(p: QPainter, w: int, h: int):
    """A pulsing ring, deep amber ↔ white-gold, with a thin dark inner line
    so it reads on gold tiles and dark (missing) tiles alike."""
    import time
    k = 0.5 + 0.5 * math.sin(time.monotonic() * 5.0)
    a, b = QColor("#c98a00"), QColor("#fff6cc")
    ring = QColor.fromRgbF(a.redF() + (b.redF() - a.redF()) * k,
                           a.greenF() + (b.greenF() - a.greenF()) * k,
                           a.blueF() + (b.blueF() - a.blueF()) * k)
    p.save()
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(QPen(ring, 4))
    p.drawRoundedRect(QRectF(2, 2, w - 4, h - 4), CELL_R, CELL_R)
    p.setPen(QPen(QColor(HAIR_BLACK), 1.2))
    p.drawRoundedRect(QRectF(4.5, 4.5, w - 9, h - 9), max(1, CELL_R - 3), max(1, CELL_R - 3))
    p.restore()


def _regold(*widgets):
    """Gold mode: re-translate / re-gild widgets whose text was just
    rewritten in English after the gold pass (toggle buttons, counts)."""
    if _GOLD_MODE["on"]:
        from . import divine_text
        for w in widgets:
            divine_text.apply(w, True)


def _gold_item(item):
    """A coloured table cell in gold mode turns gold (divine_text keeps the
    original, so leaving gold mode restores it)."""
    if _GOLD_MODE["on"]:
        from . import divine_text
        divine_text.tint_item(item, True)


def _gold_hover(widget):
    """On hovering a tile: its tooltip goes gold in gold mode (or back)."""
    if _GOLD_MODE["on"] or widget.property("jlpt_tip_gold") is not None:
        from . import divine_text
        divine_text.gold_tooltip(widget, _GOLD_MODE["on"])


def _gold_tile_edge(p: QPainter, w: int, h: int):
    """Gold mode: a thin gold inner edge on a known / found tile. Part of
    the tile's normal paint, so it costs nothing extra (grids stay fast)."""
    if not _GOLD_MODE["on"]:
        return
    p.save()
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(QPen(QColor(255, 226, 120, 200), 1.2))
    p.drawRoundedRect(QRectF(2.5, 2.5, w - 5, h - 5), max(1, CELL_R - 2), max(1, CELL_R - 2))
    p.restore()


class GridSheen(QWidget):
    """Gold mode: a soft diagonal sheen that sweeps across a grid page every
    ~8 s. Built to cost nothing while idle (no timer runs between sweeps)
    and little during one: each frame repaints only the strip the sheen
    covers, so only the tiles under it redraw. Mouse-transparent; covers the
    whole grid page (owner: on the scroll viewport alone it was clipped),
    with its top and bottom ends faded."""

    _EVERY_MS, _SWEEP_MS, _FRAME_MS, _BAND = 8000, 1400, 33, 140

    def __init__(self, viewport: QWidget):
        super().__init__(viewport)
        self._vp = viewport
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self._x = None                    # band centre while sweeping
        self._t0 = 0.0
        self._frame = QTimer(self)
        self._frame.setInterval(self._FRAME_MS)
        self._frame.timeout.connect(self._step)
        self._next = QTimer(self)
        self._next.setSingleShot(True)
        self._next.timeout.connect(self._start)
        viewport.installEventFilter(self)
        self.setGeometry(viewport.rect())
        self.raise_()
        self._next.start(2500)

    def eventFilter(self, obj, event):
        if obj is self._vp and event.type() == QEvent.Type.Resize:
            self.setGeometry(self._vp.rect())
        return False

    def _start(self):
        if _GOLD_MODE["on"] and self.isVisible():
            import time
            self._t0 = time.monotonic()
            self._frame.start()
        else:
            self._next.start(self._EVERY_MS)

    def _band_rect(self, x: float) -> QRect:
        """Bounding box of the band at x: it leans right by h/3 at the top."""
        h = self.height()
        return QRect(int(x - self._BAND) - 1, 0, int(2 * self._BAND + h / 3) + 3, h)

    def _step(self):
        import time
        t = (time.monotonic() - self._t0) * 1000 / self._SWEEP_MS
        old = self._x
        if t >= 1.0 or not _GOLD_MODE["on"]:
            self._x = None
            self._frame.stop()
            self._next.start(self._EVERY_MS)
        else:
            self._x = -self._BAND + t * (self.width() + 2 * self._BAND + self.height() / 3)
        dirty = QRect()
        for x in (old, self._x):
            if x is not None:
                dirty = dirty.united(self._band_rect(x))
        if not dirty.isEmpty():
            self.update(dirty)

    def paintEvent(self, event):
        if self._x is None:
            return
        h = self.height()
        strip = self._band_rect(self._x).intersected(event.rect())
        if strip.isEmpty():
            return
        # Draw the band into an image of just its strip, fade its top and
        # bottom ends there (so it never ends in a hard line), then blit it.
        # Scaled explicitly, not through the image's devicePixelRatio: some
        # Qt builds round that to a whole number, which misplaced everything
        # at 125%/150% Windows scaling (a friend's PC, 2026-10-10).
        dpr = self.devicePixelRatioF()
        img = QImage(max(1, int(strip.width() * dpr)), max(1, int(strip.height() * dpr)),
                     QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(Qt.GlobalColor.transparent)
        ip = QPainter(img)
        ip.scale(dpr, dpr)
        ip.translate(-strip.x(), -strip.y())
        ip.save()
        # Lean the band: x' = x + (h - y) / 3 (top shifted right by h/3).
        ip.translate(h / 3, 0)
        ip.shear(-1 / 3, 0)
        x0, x1 = self._x - self._BAND, self._x + self._BAND
        g = QLinearGradient(x0, 0, x1, 0)
        g.setColorAt(0.0, QColor(255, 240, 180, 0))
        g.setColorAt(0.42, QColor(255, 246, 210, 50))
        g.setColorAt(0.5, QColor(255, 255, 255, 85))
        g.setColorAt(0.58, QColor(255, 246, 210, 50))
        g.setColorAt(1.0, QColor(255, 240, 180, 0))
        ip.fillRect(QRectF(x0, 0, x1 - x0, h), QBrush(g))
        ip.restore()
        ip.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
        fade = QLinearGradient(0, 0, 0, h)
        fade.setColorAt(0.0, QColor(0, 0, 0, 0))
        fade.setColorAt(0.12, QColor(0, 0, 0, 255))
        fade.setColorAt(0.88, QColor(0, 0, 0, 255))
        fade.setColorAt(1.0, QColor(0, 0, 0, 0))
        ip.fillRect(QRectF(strip), QBrush(fade))
        ip.end()
        p = QPainter(self)
        p.drawImage(QRectF(strip), img, QRectF(img.rect()))
        p.end()


# ── Amaterasu divine clock ────────────────────────────────────────────────────
# One phase shared by every Amaterasu animation (badge, gold bars, overlay),
# advanced by DivineOverlay's timer so everything breathes together.
_DIVINE = {"phase": 0.0}


def _divine_pulse(widget=None) -> float:
    """0..1 breath. Widgets higher on the page breathe a little later, so
    the light travels up from Amaterasu's badge in a slow wave."""
    off = 0.0
    if widget is not None:
        try:
            off = widget.mapTo(widget.window(), QPoint(0, 0)).y() * 0.006
        except Exception:
            pass
    return 0.5 + 0.5 * math.sin(_DIVINE["phase"] + off)


# DEBUG (Overview's "Force Amaterasu" button): every LevelBar draws full,
# here and on the Kanji & Grammar tab (and the mini widget). In memory only.
_DEBUG_FULL = card_state.DEBUG_FULL
# Whether the Overview's debug row is shown (toggled by an invisible button).
_DEBUG_ROW = {"shown": False}


# Neon intro (owner 2026-10-19: "they are off when you open and flicker on
# like neon lights"): the bars keep their real length from the first frame;
# each starts as an unlit tube and flickers on with its own random pattern
# (a short delay, 2–4 stutters, sometimes a dim half-lit buzz, then on).
# The pattern and the unlit levels live in theme.py (shared with the mini
# widget's CSS version).
from .theme import NEON_OFF_FILL, NEON_OFF_TEXT, flicker_pattern as _flicker_pattern

# Each element lights when it's first SEEN (owner 2026-10-22: "the flicker
# animation doesn't happen for things that aren't visible in the window
# yet … actual visibility, not a set scroll distance"): every neon widget
# registers itself (_neon_register) and stays an unlit tube until enough
# of it is really on screen — its tab showing, not scrolled out of any
# scroll area, inside its window at whatever size — then flickers on with
# its own pattern. The grids flicker the same way the first time they're
# seen. What comes into view together is one batch with one sound
# (neon_sound); the batch holds dark until its sound is ready (≤ SOUND_WAIT,
# else it lights silently, never out of step). One timer (_NEON) runs the
# clock, advancing at most two frames a tick, so a busy main thread pauses
# the flicker instead of skipping it (to-do 2e). "run" changes per window,
# for fresh patterns. Widgets rebuilt by a refresh (_neon_quiet) light at
# once on a page already seen; on a page not seen yet they still wait.
_INTRO = {"run": 0}
_NEON = {"on": False, "items": [], "clock": 0.0, "last": None, "timer": None,
         "batches": [], "quiet": 0, "seq": 0, "seen_pages": set(), "lights": []}
SOUND_WAIT = 0.6            # s the first batch waits for its sound
SOUND_WAIT_LATER = 0.3      # s a batch scrolled into view waits (snappier)
REVEAL_PX = 40              # this much on screen (or half of a smaller element) lights it
LATER_DELAY = 0.15          # s of dark before the first spark, after the window's first look
SOUND_GAP = 0.8             # s after a batch's sound in which later batches stay silent


def _trim_delay(pat, most: float):
    """The pattern with its opening dark spell scaled into 0…`most` s
    (theme.flicker_pattern's is 0.05–0.75 s), so elements lit together
    still spark one after another, just sooner."""
    if pat and pat[0][1] == 0:
        shift = pat[0][0] * (1 - most / 0.75)
        if shift > 0:
            return [(end - shift, level) for end, level in pat]
    return pat


def _neon_register(widget, state: str = None):
    """A neon element: unlit until first seen (a refresh's rebuild: _neon_quiet).
    state: start "lit" / "quiet" / "pending" instead (a grid's re-flowed zones)."""
    import weakref
    widget._neon_state = state or ("quiet" if _NEON["quiet"] else "pending")
    if _NEON.get("instant"):                     # Settings: flicker off → lit at once
        widget._neon_state = "lit"
    _NEON["items"].append(weakref.ref(widget))
    _NEON["lights"].append(weakref.ref(widget))     # rain.py: drops catch its light
    if _NEON["on"]:
        _neon_wake()


class _neon_quiet:
    """with _neon_quiet(): widgets built inside are a rebuild, not a first look."""
    def __enter__(self):
        _NEON["quiet"] += 1

    def __exit__(self, *exc):
        _NEON["quiet"] -= 1


def _intro_light(widget) -> float:
    """0 (off) … 1 (lit) for this element now. Always lit outside a neon
    window and in Amaterasu mode (it has its own intro)."""
    if not _NEON["on"] or _GOLD_MODE["on"]:
        return 1.0
    st = getattr(widget, "_neon_state", "lit")
    if st == "lit":
        return 1.0
    if not isinstance(st, tuple) or st[0] is None:
        return 0.0                              # not seen yet / holding for its sound
    now = _NEON["clock"] - st[0]
    for end, level in st[1]:
        if now < end:
            return level
    return 1.0


def _neon_page(w):
    """The tab page (a QStackedWidget's page) or window a widget is on."""
    a = w
    while a is not None:
        p = a.parentWidget()
        if p is None or isinstance(p, QStackedWidget):
            return a
        a = p
    return w


def _visible_rect(w, cache: dict = None):
    """(w's rectangle, its part on screen), both in its window's
    coordinates, or None when none of it shows: hidden (its tab too), or
    clipped away by a parent (scroll viewports included) or the window."""
    key = id(w)
    if cache is not None and key in cache:
        return cache[key]
    out = None
    if w.isVisible() and w.width() > 0 and w.height() > 0:
        win = w.window()
        if win is not None and not win.isMinimized():
            full = QRect(w.mapTo(win, QPoint(0, 0)), w.size()) if w is not win else win.rect()
            r = full
            a = w.parentWidget()
            while a is not None and a is not win and not r.isEmpty():
                r = r.intersected(QRect(a.mapTo(win, QPoint(0, 0)), a.size()))
                a = a.parentWidget()
            r = r.intersected(win.rect())
            out = None if r.isEmpty() else (full, r)
    if cache is not None:
        cache[key] = out
    return out


def _on_screen(w, cache: dict = None) -> bool:
    """Enough of `w` is actually on screen: at least REVEAL_PX of it each
    way (half of a smaller element). A grid's zone (_NeonZone) is measured
    through its grid, once per grid per tick (`cache`): big grids have
    hundreds of zones."""
    canvas = getattr(w, "_neon_canvas", None)
    if canvas is not None:
        vr = _visible_rect(canvas, cache)
        if vr is None:
            return False
        full, shown = vr
        r = QRect(full.topLeft() + w.pos(), w.size()).intersected(shown)
    else:
        vr = _visible_rect(w)
        if vr is None:
            return False
        r = vr[1]
    return (not r.isEmpty()
            and r.height() >= min(REVEAL_PX, max(1, w.height() // 2))
            and r.width() >= min(REVEAL_PX, max(1, w.width() // 2)))


def _neon_at(widgets, seconds):
    """Dev tools (tools/dev/qt_title.py, qt_tabline.py): show these elements
    `seconds` into their flicker, or lit with None."""
    _NEON["on"] = seconds is not None
    for w in widgets:
        w._neon_state = "lit" if seconds is None else (
            _NEON["clock"] - seconds, _flicker_pattern(_INTRO["run"] * 1_000_003 + id(w)))
        _neon_repaint(w)


def neon_lights(win) -> list:
    """The lit neon on screen in window `win`, for the rain (rain.py):
    [(rect in window coordinates, colour, strength 0–1, widget)]. Each
    element keeps its lit part in `_lit` (rect in its own coordinates,
    colour[, strength]) from its last paint; its flicker dims it. None in
    Amaterasu mode."""
    if _GOLD_MODE["on"]:
        return []
    cache, wins, out, alive = {}, {}, [], []
    for ref in _NEON["lights"]:
        w = ref()
        if w is None:
            continue
        alive.append(ref)
        try:
            lit = getattr(w, "_lit", None)
            if lit is None:
                continue
            canvas = getattr(w, "_neon_canvas", None)
            host = canvas if canvas is not None else w
            hw = wins.get(id(host))
            if hw is None:
                hw = wins[id(host)] = host.window()
            if hw is not win:
                continue
            vr = _visible_rect(host, cache)
            if vr is None:
                continue
            origin = vr[0].topLeft() + (w.pos() if canvas is not None else QPoint(0, 0))
            light = _intro_light(w)
            if light <= 0:
                continue
            r = lit[0].translated(origin).intersected(vr[1])
            if r.isEmpty():
                continue
            out.append((r, lit[1], light * (lit[2] if len(lit) > 2 else 1.0), w))
        except RuntimeError:
            continue
    _NEON["lights"] = alive
    return out


RARE_FLICKER_VOLUME = 0.05     # × the Settings level: "very very quiet" (owner 2026-10-22)
# A bar that has just flickered on sparks this often (owner 2026-10-22:
# "50 percent chance of sparking when they initially turn on"; 25 % since
# 2026-10-26).
FIRST_LIGHT_SPARK = 0.25


def _first_light_spark(w):
    """A bar has just come on: maybe a spark off it (its window's rain)."""
    import random
    try:
        if not isinstance(w, (LevelBar, RankBar, BeltBar)) or random.random() >= FIRST_LIGHT_SPARK:
            return
        rain = getattr(w.window(), "_rain", None)
        if rain is not None:
            rain.spark_from(w)
    except Exception:
        pass


def _neon_stutter(w):
    """Very rarely (rain.py picks when and which): one lit tube stutters —
    a couple of quick dips, then steady — with a very quiet buzz."""
    if (not _NEON["on"] or _GOLD_MODE["on"] or _NEON.get("instant")
            or getattr(w, "_neon_state", "lit") != "lit"):
        return
    import random, time, weakref
    rnd = random.Random()
    t, pat = rnd.uniform(0.02, 0.08), []
    pat.append((t, 1.0))
    for _ in range(rnd.randint(2, 4)):
        t += rnd.uniform(0.03, 0.08)
        pat.append((t, rnd.choice((0.0, 0.25, 0.5))))
        t += rnd.uniform(0.03, 0.12)
        pat.append((t, 1.0))
    w._neon_pat = pat
    w._neon_state = (None, pat)
    w._neon_stutter = True                       # not a first light: no spark after
    _NEON["items"].append(weakref.ref(w))
    _neon_batch([w], time.monotonic(), volume=RARE_FLICKER_VOLUME, gap=False)
    _neon_wake()


def kotodama_in_front() -> bool:
    """Anki has the focus: a Kotodama window (the main one or one it opened)
    or any other Anki window. Every sound of the window plays only then
    (owner 2026-10-22: "mute if focus is not on kotodama or on anki");
    another app in front → no active window of ours."""
    return QApplication.activeWindow() is not None


_FOCUS = {"watching": False, "away": None}


def _on_focus_changed(*_args):
    """Focus moved: silence the window's sounds when it's no longer in front
    (and let the star's sound back in when it is)."""
    try:
        away = not kotodama_in_front()
        if away == _FOCUS["away"]:
            return
        _FOCUS["away"] = away
        from . import neon_sound, ambience
        if away:
            neon_sound.stop_window_sounds()
        ambience.get().set_away(away)
    except Exception:
        pass


def _watch_focus():
    """Once per session: follow which window has the focus."""
    if _FOCUS["watching"]:
        return
    try:
        QApplication.instance().focusWindowChanged.connect(_on_focus_changed)
        _FOCUS["watching"] = True
    except Exception:
        pass


def attach_rain(window):
    """Rain on this window's glass (rain.py), not in Amaterasu mode."""
    try:
        from .rain import RainGlass
        from . import neon_sound, effects
        if not neon_sound._SPARKS:                # the sparks' crackle, rendered once
            import threading
            threading.Thread(target=neon_sound.prepare_sparks, daemon=True).start()
        window._rain = RainGlass(window, lambda: neon_lights(window), _neon_stutter,
                                 off_fn=lambda: _GOLD_MODE["on"] or not _NEON["on"],
                                 spark_fn=lambda: kotodama_in_front() and neon_sound.play_spark(),
                                 rain_fn=effects.rain_on, fx_fn=effects.fx)
    except Exception:
        import traceback
        traceback.print_exc()


def _neon_repaint(w):
    own = getattr(w, "_neon_refresh", None)      # a grid zone: its veil and glow band
    if own is not None:
        own()
        return
    w.update()
    if isinstance(w, LevelBar):
        _spill_update(w)                         # its light on the wall follows it
    veil = getattr(w, "_neon_veil", None)
    if veil is not None:
        veil.refresh()


def _neon_wake():
    t = _NEON["timer"]
    if t is None:
        t = _NEON["timer"] = QTimer()
        t.timeout.connect(_neon_tick)
    busy = bool(_NEON["batches"]) or any(
        isinstance(getattr(r(), "_neon_state", None), tuple) for r in _NEON["items"] if r() is not None)
    t.setInterval(16 if busy else 50)
    if not t.isActive():
        t.start()


def _neon_stop(closing=None):
    """The window closed: everything lit, nothing left waiting — unless
    another Kotodama window is still open (2026-10-25: closing one cleared
    the shared state, and the other window's rain lost its lights or went
    off). Then only the closing window's elements are dropped."""
    others = [w for w in QApplication.topLevelWidgets()
              if isinstance(w, ProgressDialog) and w is not closing and w.isVisible()]
    if others and closing is not None:
        def mine(ref):
            w = ref()
            try:
                return w is None or w.window() is closing
            except RuntimeError:
                return True
        _NEON["items"] = [r for r in _NEON["items"] if not mine(r)]
        _NEON["lights"] = [r for r in _NEON["lights"] if not mine(r)]
        return
    _NEON.update(on=False, items=[], batches=[], last=None, lights=[])
    _NEON["seen_pages"] = set()
    if _NEON["timer"] is not None:
        _NEON["timer"].stop()


def _neon_tick():
    import time
    now = time.monotonic()
    if _NEON["last"] is not None:
        _NEON["clock"] += min(now - _NEON["last"], 0.034)     # a stall pauses, never skips
    _NEON["last"] = now
    if not _NEON["on"]:
        _NEON["timer"].stop()
        return
    gold = _GOLD_MODE["on"]
    alive, fresh, busy = [], [], False
    seen = {}                                    # _visible_rect per grid, this tick
    for ref in _NEON["items"]:
        w = ref()
        if w is None:
            continue
        try:
            st = getattr(w, "_neon_state", "lit")
            if st == "lit":
                continue
            if st == "quiet":                    # rebuilt by a refresh
                st = w._neon_state = "lit" if id(_neon_page(w)) in _NEON["seen_pages"] else "pending"
                if st == "lit":
                    _neon_repaint(w)
                    continue
            if st == "pending" and _NEON.get("instant"):
                w._neon_state = "lit"
                _neon_repaint(w)
                continue
            if st == "pending":
                if not gold and _on_screen(w, seen):
                    _NEON["seen_pages"].add(id(_neon_page(w)))
                    w._neon_pat = _flicker_pattern(_INTRO["run"] * 1_000_003 + id(w))
                    if _NEON["seq"]:             # scrolled / switched into view: start sooner
                        w._neon_pat = _trim_delay(w._neon_pat, LATER_DELAY)
                    w._neon_state = (None, w._neon_pat)
                    fresh.append(w)
            elif st[0] is not None:
                light = _intro_light(w)
                if _NEON["clock"] - st[0] >= st[1][-1][0]:
                    w._neon_state = "lit"
                    _neon_repaint(w)
                    if not getattr(w, "_neon_stutter", False):
                        _first_light_spark(w)
                    w._neon_stutter = False
                    done = getattr(w, "_neon_lit_cb", None)
                    if done is not None:
                        done()
                    continue
                busy = True
                if light != getattr(w, "_neon_seen", None):      # repaint only on a step
                    w._neon_seen = light
                    _neon_repaint(w)
            else:
                busy = True
        except RuntimeError:                     # deleted underneath us
            continue
        alive.append(ref)
    _NEON["items"] = alive
    if fresh:
        _neon_batch(fresh, now)
    for b in list(_NEON["batches"]):
        if _neon_batch_ready(b, now):
            _NEON["batches"].remove(b)
            for w in b["widgets"]:
                try:
                    st = w._neon_state
                    if isinstance(st, tuple) and st[0] is None:
                        w._neon_state = (_NEON["clock"], st[1])
                        _neon_repaint(w)
                except RuntimeError:
                    pass
            busy = True
    busy = busy or bool(_NEON["batches"])
    if not alive and not _NEON["batches"]:
        _NEON["timer"].stop()
        return
    _NEON["timer"].setInterval(16 if busy else 50)


def _neon_batch(widgets, now, volume=None, gap=True):
    """These came into view together: render their sound on a worker thread.
    volume: its own level (the rare stutter's); gap=False: not held back by
    SOUND_GAP (and doesn't count toward it)."""
    import threading, random
    from . import neon_sound, effects
    if gap:
        _NEON["seq"] += 1
    b = {"widgets": widgets, "thread": None, "path": None, "since": now, "volume": volume,
         "wait": SOUND_WAIT if _NEON["seq"] == 1 else SOUND_WAIT_LATER}
    # One buzz at a time: scrolling a grid lights a zone every few rows, and
    # a sound for each would be a racket. A batch soon after the last sound
    # lights silently (and at once).
    if gap and now - _NEON.get("sound_at", -1e9) < SOUND_GAP:
        _NEON["batches"].append(b)
        return
    if not effects.muted():                      # Settings → Sound effects at 0 %: silent
        if gap:
            _NEON["sound_at"] = now
        pats = [w._neon_state[1] for w in widgets]
        seed = _INTRO["run"] * 1000 + _NEON["seq"] + (0 if gap else 500 + random.randrange(400))

        def work():
            b["path"] = neon_sound.prepare(pats, seed)
        b["thread"] = threading.Thread(target=work, daemon=True)
        b["thread"].start()
    _NEON["batches"].append(b)


def _neon_batch_ready(b, now) -> bool:
    """True when the batch should light: its sound started, or no sound."""
    if b["thread"] is None:
        return True
    if not b["thread"].is_alive():
        from . import neon_sound
        if kotodama_in_front():                  # muted while the window isn't focused
            if b.get("volume") is not None:
                neon_sound.play_file(b["path"], b["volume"], window=True)
            else:
                neon_sound.play_file(b["path"], window=True)
        return True
    return now - b["since"] >= b["wait"]


class _NeonVeil(QWidget):
    """An unlit sign's darkness over an element whose children can't dim
    themselves (a grid's tiles, the rank badge's picture and text): the
    window's background laid over shape_fn()'s path (or the element's
    rounded rectangle) at 1 − light, down to `off` (how much shows while
    unlit). Hidden once lit; mouse-transparent."""

    def __init__(self, target: QWidget, off: float, shape_fn=None, radius: float = 0):
        super().__init__(target)
        self._t, self._off, self._shape_fn, self._radius = target, off, shape_fn, radius
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        target.installEventFilter(self)
        target._neon_veil = self
        self.setGeometry(target.rect())
        self.raise_()

    def eventFilter(self, obj, event):
        if obj is self._t and event.type() == QEvent.Type.Resize:
            self.setGeometry(self._t.rect())
        return False

    def refresh(self):
        lit = _intro_light(self._t) >= 1.0
        self.setVisible(not lit)
        if not lit:
            self.raise_()
            self.update()

    def paintEvent(self, event):
        light = _intro_light(self._t)
        a = 1.0 - (self._off + (1.0 - self._off) * light)
        if a <= 0:
            return
        from . import theme
        c = QColor(theme.BG_BOTTOM)
        c.setAlphaF(min(1.0, a))
        path = self._shape_fn() if self._shape_fn is not None else None
        if path is None:
            path = QPainterPath()
            path.addRoundedRect(QRectF(self.rect()), self._radius, self._radius)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(c)
        p.drawPath(path)
        p.end()


class _TabUnderline(QWidget):
    """The selected tab's gold underline as a neon tube during the window's
    intro (owner 2026-10-20): drawn over the tab bar with _intro_light while
    the style sheet's own underline is hidden; removed when the intro ends."""

    def __init__(self, bar: QTabBar):
        super().__init__(bar)
        self._bar = bar
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setGeometry(bar.rect())
        # A bound method, not a lambda: Qt drops the connection when this
        # widget is deleted at the end of the intro (a lambda kept calling
        # the deleted widget on every later tab switch: owner's log 2026-10-21).
        bar.currentChanged.connect(self._tab_changed)
        self.show()
        self.raise_()
        _neon_register(self)

    def _tab_changed(self, _index):
        try:
            self.update()
        except RuntimeError:            # already deleted
            pass

    def paintEvent(self, event):
        i = self._bar.currentIndex()
        if i < 0:
            return
        self.setGeometry(self._bar.rect())
        r = self._bar.tabRect(i)
        light = _intro_light(self)
        if light <= 0:
            return
        from . import theme
        c = QColor(theme.accent())
        p = QPainter(self)
        for h, alpha in ((6, 40), (2, 255)):            # a soft glow, then the 2 px line
            cc = QColor(c)
            cc.setAlpha(int(alpha * light))
            p.fillRect(QRectF(r.left(), r.bottom() - h + 1, r.width(), h), cc)
        p.end()


class NeonTitle(QWidget):
    """Part of the window's title card as a neon sign (owner 2026-10-20):
    each part's text with a soft glow in its own colour, flickering on with
    the bars' intro (_intro_light: its own random pattern), then lit.
    parts: [(text, pixel size, bold, colour, glow colour)]."""

    def __init__(self, parts, parent=None):
        super().__init__(parent)
        self._parts = parts
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        _neon_register(self)

    def set_parts(self, parts):
        self._parts = parts
        self.updateGeometry()
        self.update()

    @staticmethod
    def _font(px, bold):
        f = QFont()
        f.setPixelSize(px)
        if bold:
            f.setWeight(QFont.Weight.DemiBold)
        f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1)
        return f

    _GAP, _GLOW = 10, 8          # px between parts; room for the glow around the text

    def sizeHint(self):
        w = h = 0
        for text, px, bold, _c, _g in self._parts:
            fm = QFontMetricsF(self._font(px, bold))
            w += fm.horizontalAdvance(text)
            h = max(h, fm.height())
        w += self._GAP * (len(self._parts) - 1) + self._GLOW * 2
        return QSize(int(w + 1), int(h + self._GLOW))

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        light = _intro_light(self)
        fill_k = NEON_OFF_TEXT + (1 - NEON_OFF_TEXT) * light
        x = self._GLOW
        base_y = self.height() / 2
        for text, px, bold, color, glow in self._parts:
            font = self._font(px, bold)
            fm = QFontMetricsF(font)
            path = QPainterPath()
            path.addText(QPointF(x, base_y + (fm.ascent() - fm.descent()) / 2), font, text)
            if glow and light > 0:
                for width, alpha in ((9, 22), (5.5, 45), (2.6, 85)):
                    c = QColor(glow)
                    c.setAlpha(int(alpha * light))
                    pen = QPen(c, width)
                    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
                    p.setPen(pen)
                    p.drawPath(path)
            c = QColor(color)
            c.setAlphaF(fill_k)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(c)
            p.drawPath(path)
            x += fm.horizontalAdvance(text) + self._GAP
        p.end()


# Title card parts: Kotodama 言霊 (white + gold) | JLPT Tracker (red neon);
# in Amaterasu mode the Japanese title, all gold (was divine_text's EXACT).
TITLE_LEFT = [("Kotodama", 22, True, "#f2f2f2", "#ffffff"), ("言霊", 22, False, "#d4a017", "#f5c518")]
TITLE_RIGHT = [("JLPT Tracker", 18, False, "#ff5a5a", "#ff1744")]
TITLE_LEFT_GOLD = [("言霊", 22, True, "#f5c518", "#fff8c5"), ("ことだま", 22, False, "#f5c518", "#fff8c5")]
TITLE_RIGHT_GOLD = [("JLPT 進捗", 18, False, "#f5c518", "#fff8c5")]


# The N5–N1 signs as one long box on the side of a building (owner
# 2026-10-26, mock-ups A + C: each panel its own neon outline, softly lit from
# behind in its colour). The building is only its edge, poking in from the
# card's left side, no windows. In Amaterasu mode there's no building, box or
# brackets: just the five glowing panels, floating.
FACE_W = 8              # px of building face inside the sign column (wall coords)
SIGN_X, SIGN_PW = 16, 34   # the sign box's left edge and width (wall coords)
SIGN_STEEL = 3          # steel showing round the box's lit panels (owner 2026-10-26: one piece)
SIGN_GAP = 3            # the seam between two levels' panels
ROW_GAP = 10            # the gap between the bars (the card's spacing), kept as it was
SIGN_BACKLIT = 0.22     # each panel's colour glow from behind (0–1)
FACADE_ALPHA = 0.45     # owner 2026-10-26; how much of the tubes' bloom the dark building blocks (0–1)
STEEL, STEEL_DARK = "#3a3a40", "#222226"


class LevelSign(QWidget):
    """A JLPT level's panel in the building's long neon sign (owner
    2026-10-26; was a separate plate, 2026-10-22): "N" over "5" in tube
    lettering; it flickers on like the bars. The box, the brackets and the
    building are _SignWall's, behind the rows."""

    W = 56
    _neon_tube = True

    def __init__(self, level: str, parent=None):
        super().__init__(parent)
        self._level = level
        self._gold = False
        # taller than its bar by the gap the seam doesn't use, so the panels
        # nearly touch while the bars keep their spacing
        self.setFixedSize(self.W, 72 + ROW_GAP - SIGN_GAP)
        _neon_register(self)

    def set_gold(self, on: bool):
        self._gold = bool(on)
        self.update()

    def _plate(self) -> QRectF:
        """This level's lit panel: its whole row, with SIGN_STEEL of the box
        showing at each side; the SIGN_GAP between rows is the seam between
        panels (owner 2026-10-26: one piece, thin steel, a thin seam)."""
        return QRectF(SIGN_X + SIGN_STEEL, 0.5, SIGN_PW - 2 * SIGN_STEEL, self.height() - 1)

    def paintEvent(self, event):
        c = QColor(rank_data.MAX_RANK_FILL_COLOR if self._gold else LEVEL_FG[self._level])
        plate = self._plate()
        self._lit = (plate.toRect(), c)
        light = _intro_light(self)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#0d0b08" if self._gold else "#0e0e10"))   # the panel's dark face
        p.drawRoundedRect(plate, 3, 3)
        wash = QColor(c)                                         # backlit, like acrylic (mock-ups A + C)
        wash.setAlphaF(SIGN_BACKLIT * (0.25 + 0.75 * light))
        p.setBrush(wash)
        p.drawRoundedRect(plate, 3, 3)
        for width, a in ((5, 30), (3, 60)):                      # the panel's own neon outline
            cc = QColor(c)
            cc.setAlpha(int(a * light))
            p.setPen(QPen(cc, width))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(plate, 3, 3)
        edge = QColor(c.lighter(115))
        edge.setAlphaF(NEON_OFF_FILL + (1 - NEON_OFF_FILL) * light)
        p.setPen(QPen(edge, 1.4))
        p.drawRoundedRect(plate, 3, 3)
        # the tube lettering, N over the number
        f = QFont()
        f.setPixelSize(16)
        f.setWeight(QFont.Weight.Bold)
        fm = QFontMetricsF(f)
        lh = fm.height() * 0.82
        y0 = plate.center().y() - lh * len(self._level) / 2
        p.setOpacity(NEON_OFF_TEXT + (1 - NEON_OFF_TEXT) * light)
        for i, ch in enumerate(self._level):
            path = QPainterPath()
            x = plate.center().x() - fm.horizontalAdvance(ch) / 2
            path.addText(QPointF(x, y0 + i * lh + fm.ascent() * 0.95 + (lh - fm.height()) / 2), f, ch)
            for width, alpha in ((8, 22), (5, 42), (3, 85), (1.8, 140)):
                cc = QColor(c)
                cc.setAlpha(int(alpha * light))
                p.strokePath(path, QPen(cc, width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                                        Qt.PenJoinStyle.RoundJoin))
            p.fillPath(path, c.lighter(150))
        p.end()


class _Facade(QWidget):
    """The building's edge behind the level signs, a narrow strip from the
    card's left edge to the sign's brackets (owner 2026-10-26): a dark wall
    with a ledge on top; no windows and no light from the sign on it (both
    tried, removed). It sits just above the tubes' light spill (_SpillLayer)
    as near-black at FACADE_ALPHA, so the bloom shows on it, dimmer than on
    the open wall: a dark building catching some of the light (owner
    2026-10-26). A child of the card (_SignWall places it and hides it in
    Amaterasu mode)."""

    def __init__(self, parent):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def paintEvent(self, event):
        p = QPainter(self)
        w, h = self.width(), self.height()
        p.setOpacity(FACADE_ALPHA)
        p.fillRect(QRect(0, 0, w, h), QColor("#050506"))
        p.fillRect(QRect(w - 1, 0, 1, h), QColor("#222227"))          # the building's corner
        p.fillRect(QRect(0, 0, w, 3), QColor("#232328"))              # the ledge on top
        p.end()


class _SignWall(QWidget):
    """Behind the N5–N1 rows: the long sign box (frame and dividers; each
    panel's lettering is its LevelSign's) on brackets, and the building's
    face (_Facade) reaching left to the card's edge (owner 2026-10-26)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._facade = None
        self._gold = False

    def set_gold(self, on: bool):
        self._gold = bool(on)
        if self._facade is not None:
            self._facade.setVisible(not self._gold)  # Amaterasu: no building, the panels float
        self.update()

    def _place_facade(self):
        card = self.parentWidget()
        if card is None:
            return
        if self._facade is None:
            self._facade = _Facade(card)
            self._facade.setVisible(not self._gold)
        self._facade.setGeometry(1, self.y() - 8, self.x() + FACE_W - 1, self.height() + 8)
        self._facade.stackUnder(self)                # above the light spill, under the sign

    def moveEvent(self, event):
        super().moveEvent(event)
        self._place_facade()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._place_facade()

    def _panels(self):
        """Each LevelSign's rows, top to bottom, in this widget's coordinates."""
        out = []
        for s in self.findChildren(LevelSign):
            top = s.mapTo(self, QPoint(0, 0)).y()
            out.append((top, top + s.height()))
        return sorted(out)

    def paintEvent(self, event):
        panels = self._panels()
        if not panels:
            return
        if self._gold:
            return                                   # Amaterasu: no box or brackets, the panels float
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        top, bottom = panels[0][0] - SIGN_STEEL, panels[-1][1] + SIGN_STEEL
        box = QRectF(SIGN_X, top, SIGN_PW, bottom - top)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(STEEL))                                    # brackets to the building
        ys = [top + 10] + [(a[1] + b[0]) / 2 for a, b in zip(panels, panels[1:])] + [bottom - 10]
        for y in ys:
            p.drawRect(QRectF(FACE_W, y - 1.5, SIGN_X - FACE_W, 3))
        # the steel box: the lit panels (LevelSign) cover all but SIGN_STEEL
        # round each of them, the same on every side
        p.setBrush(QColor(STEEL_DARK))
        p.setPen(QPen(QColor(STEEL), 1.2))
        p.drawRoundedRect(box.adjusted(0.6, 0.6, -0.6, -0.6), 5, 5)
        p.end()


class LevelBar(QWidget):
    clicked = pyqtSignal(str)
    _neon_tube = True              # rain.py: sparks / stutters come off bars

    # Horizontal padding so glow halos bleed outward without widget clipping.
    # The bar is drawn inset by this amount on each side.
    _PAD = 28

    def __init__(self, level: str, known: int, total: int,
                 force_max_gold: bool = False, parent=None,
                 colors: tuple = None, clickable: bool = True,
                 compact: bool = False):
        super().__init__(parent)
        # compact: the smaller, deemphasised bars of the Kanji & Grammar tab.
        self._pad, self._bar_h, self._radius, self._font_pt, self._glow_k = (
            (16, 18, 6, 8, 0.5) if compact else (self._PAD, 32, 8, 10, 1.0))
        self._level = level
        self._known = known
        self._total = total
        self._pct   = known / total if total else 0
        # colors: optional (fg, bg) override for bars that aren't a JLPT
        # level (e.g. the frequency bars); defaults to the level's colours.
        if colors:
            self._fg, self._bg = colors
        elif level == "All":
            # All Levels Combined: white fill with a red glow.
            self._fg, self._bg = "#ffffff", "#c8c8c8"
        else:
            self._fg, self._bg = LEVEL_FG[level], LEVEL_BG[level]
        self._glow = "#ff1744" if level == "All" and not colors else self._fg
        # Black Belt Amaterasu (20,000 cards) global override: every bar
        # in the add-on except the belt bar itself turns bright gold.
        self._force_max_gold = force_max_gold
        self._clickable = clickable
        self._ghost = None          # set_ghost: a second count, pale, behind the fill
        self.setFixedHeight(36 if compact else 72)
        self.setMinimumWidth(200)
        if clickable:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            self.setToolTip(f"Click to open {level} word grid")
        _neon_register(self)

    def set_ghost(self, count):
        """A pale fill up to `count` behind the bar's own fill, ending in a
        thin line: the Near Native bar shows the rank (learned words) behind
        the common words you know (owner 2026-10-20). None = no ghost."""
        self._ghost = count
        self.update()

    def set_force_max_gold(self, force_max_gold: bool):
        """Toggle the Amaterasu gold override without rebuilding the bar —
        used so the debug ±250 rank-preview buttons can flip every JLPT
        bar live, and so reaching real 20,000 cards updates instantly."""
        if force_max_gold != self._force_max_gold:
            self._force_max_gold = force_max_gold
            self.update()

    # ── glow helpers ──────────────────────────────────────────────────────────

    def _glow_params(self):
        """Compute (layers, spread_px, peak_alpha) purely from self._pct.

        Uses a concave curve (exponent < 1) so the low-to-mid range gets a
        clearly visible, steadily increasing glow — each ~15-25 percentage
        point step (e.g. 13% → 30% → 54% → 80% → 100%) should look
        noticeably brighter than the last, with no hard "off" zone above 0%.

          ~13%  →  faint but visible halo
          ~30%  →  clearly brighter halo
          ~54%  →  strong medium glow
          ~80%  →  very bright glow
          100%  →  laser special (extra layers + white border)
        """
        pct = self._pct

        if pct <= 0.0:
            return 0, 0, 0

        if pct >= 1.0:
            return 9, 30, 255   # laser

        t = min(pct, 0.999) ** 0.55   # concave: boosts low/mid range

        layers     = 2 + int(t * 6)        # 2 .. 7
        max_spread = int(3 + t * 22)       # 3 .. 24
        peak_alpha = int(40 + t * 195)     # 40 .. 235

        return layers, max_spread, peak_alpha

    def _glow_color(self) -> QColor:
        if self._force_max_gold:
            # Use the Amaterasu accent color (near-white gold) for the glow,
            # matching exactly what RankBar uses — this is what makes the halo
            # look bright/luminous rather than a flat saturated gold glow.
            return QColor(rank_data.RANK_COLORS["Amaterasu"][1])
        return QColor(self._glow)

    # ── paint ─────────────────────────────────────────────────────────────────

    def paintEvent(self, event):
        # DEBUG "Force Amaterasu": draw every bar full (display only).
        if not _DEBUG_FULL["on"] or not self._total:
            return self._paint(event)
        saved = self._known, self._pct
        self._known, self._pct = self._total, 1.0
        try:
            self._paint(event)
        finally:
            self._known, self._pct = saved

    def _paint(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

        w, h  = self.width(), self.height()
        pad   = self._pad
        bar_x = pad
        bar_w = w - pad * 2
        bar_h = self._bar_h
        bar_y = (h - bar_h) // 2
        r     = self._radius

        fg   = self._fg
        bg_d = self._bg
        if self._force_max_gold:
            fg   = rank_data.MAX_RANK_FILL_COLOR
            # Use the same dark-amber stop as RankBar rather than a computed
            # darker() value — keeps the gradient looking rich gold, not
            # gold-to-near-black which reads as dim on smaller bars.
            bg_d = rank_data.RANK_COLORS["Amaterasu"][1]

        fill_w   = max(int(bar_w * self._pct), r * 2 if self._pct > 0 else 0)
        fill_w   = min(fill_w, bar_w)
        is_laser = self._pct >= 1.0
        self._lit = (QRect(bar_x, bar_y, fill_w, bar_h), self._glow_color()) if fill_w > 0 else None

        light = _intro_light(self)
        p.setOpacity(light)                  # neon intro: no glow while off
        # ── 1. glow halos (below everything) ─────────────────────────────────
        layers, max_spread, peak_alpha = self._glow_params()
        max_spread = int(max_spread * self._glow_k)
        # Amaterasu: the glow breathes (same look, swelling and easing);
        # DivineOverlay carries it on past the widget's edges.
        breathe = _divine_pulse(self) if (self._force_max_gold and is_laser) else None
        if breathe is not None:
            max_spread = int(max_spread * (1.0 + 0.45 * breathe))
        if layers > 0 and fill_w > 0:
            glow_col = self._glow_color()

            # Paint from outermost (faintest) to innermost (brightest)
            for i in range(1, layers + 1):
                frac   = i / layers          # 1/layers = outermost, 1.0 = innermost
                # Spread shrinks as we go inward
                spread = max(1, int(max_spread * (1.0 - frac * 0.75)))
                # Alpha: power curve so inner layers dominate
                alpha  = int(peak_alpha * (frac ** 1.4))
                alpha  = min(alpha, 255)

                gx = max(0,     bar_x - spread)
                gy = max(0,     bar_y - spread)
                gx2 = min(w,    bar_x + fill_w + spread)
                gy2 = min(h,    bar_y + bar_h  + spread)
                gw = gx2 - gx
                gh = gy2 - gy
                gr = r + spread

                c = QColor(glow_col)
                c.setAlpha(alpha)
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(c)
                p.drawRoundedRect(gx, gy, gw, gh, gr, gr)

            # Laser-only: extra soft wide bloom (clamped to widget)
            if is_laser:
                bloom_s   = max_spread + 8
                bx  = max(0, bar_x - bloom_s)
                by  = max(0, bar_y - bloom_s)
                bx2 = min(w, bar_x + fill_w + bloom_s)
                by2 = min(h, bar_y + bar_h  + bloom_s)
                bloom_col = QColor(glow_col)
                bloom_col.setAlpha(45 if breathe is None else int(45 + 75 * breathe))
                p.setBrush(bloom_col)
                p.drawRoundedRect(bx, by, bx2 - bx, by2 - by,
                                  r + bloom_s, r + bloom_s)

        p.setOpacity(1.0)
        # ── 2. track ─────────────────────────────────────────────────────────
        _paint_bar_track(p, bar_x, bar_y, bar_w, bar_h, r)

        p.setOpacity(NEON_OFF_FILL + (1 - NEON_OFF_FILL) * light)   # neon intro: unlit tube
        # ── 2b. ghost: a second count behind the fill (set_ghost) ────────────
        if self._ghost and self._total and self._ghost > self._known and not _DEBUG_FULL["on"]:
            gw = min(bar_w, max(r * 2, int(bar_w * min(1.0, self._ghost / self._total))))
            gc = QColor(rank_data.RANK_COLORS["Amaterasu"][1] if self._force_max_gold else fg)
            gc.setAlpha(105)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(gc)
            p.drawRoundedRect(bar_x, bar_y, gw, bar_h, r, r)
            gc.setAlpha(230)
            p.setPen(QPen(gc, 2))
            p.drawLine(QPointF(bar_x + gw - 1, bar_y + 2), QPointF(bar_x + gw - 1, bar_y + bar_h - 2))
            p.setPen(Qt.PenStyle.NoPen)
        # ── 3. filled portion ─────────────────────────────────────────────────
        if fill_w > 0:
            fg_col = QColor(fg)
            bg_col = QColor(bg_d)
            grad   = QLinearGradient(0, bar_y, 0, bar_y + bar_h)

            if self._pct >= 0.75:
                grad.setColorAt(0.0, fg_col.lighter(145))
                grad.setColorAt(0.4, fg_col)
                grad.setColorAt(1.0, bg_col)
            elif self._pct >= 0.45:
                grad.setColorAt(0.0, fg_col.lighter(115))
                grad.setColorAt(1.0, bg_col)
            else:
                grad.setColorAt(0.0, fg_col)
                grad.setColorAt(1.0, bg_col)

            p.setBrush(grad)
            p.drawRoundedRect(bar_x, bar_y, fill_w, bar_h, r, r)

            # Specular top sheen
            sheen = QLinearGradient(0, bar_y, 0, bar_y + bar_h // 2)
            sheen.setColorAt(0.0, QColor(255, 255, 255, 60))
            sheen.setColorAt(1.0, QColor(255, 255, 255, 0))
            p.setBrush(sheen)
            p.drawRoundedRect(bar_x, bar_y, fill_w, bar_h // 2, r, r)

            # Laser: glowing white/yellow border outline (no center stripe)
            if is_laser:
                for border_w, border_alpha, border_color in [
                    (3, 180, QColor(255, 255, 200)),   # outer glow ring
                    (2, 230, QColor(255, 255, 255)),   # bright white edge
                ]:
                    border_color.setAlpha(border_alpha)
                    pen = QPen(border_color)
                    pen.setWidth(border_w)
                    p.setPen(pen)
                    p.setBrush(Qt.BrushStyle.NoBrush)
                    p.drawRoundedRect(
                        bar_x + border_w // 2,
                        bar_y + border_w // 2,
                        fill_w - border_w,
                        bar_h  - border_w,
                        r, r
                    )
                p.setPen(Qt.PenStyle.NoPen)

        p.setOpacity(NEON_OFF_TEXT + (1 - NEON_OFF_TEXT) * light)
        # ── 4. text ───────────────────────────────────────────────────────────
        font = QFont()
        font.setBold(True)
        font.setPointSize(self._font_pt)
        p.setFont(font)

        # format_progress never rounds up to 100.0% unless known == total
        # (19,999/20,000 shows 99.9%).
        text      = jlpt_data.format_progress(self._known, self._total)
        text_rect = QRect(bar_x, bar_y, bar_w, bar_h)

        if _bar_text(p, text_rect, text, QRect(bar_x, bar_y, fill_w, bar_h),
                     self._force_max_gold):
            p.end()
            return

        # Drop shadow
        p.setPen(QColor(0, 0, 0, 200))
        p.drawText(text_rect.adjusted(1, 1, 1, 1), Qt.AlignmentFlag.AlignCenter, text)
        # Main
        p.setPen(QColor("#ffffff"))
        p.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, text)

        # On a very light fill (the white All Levels bar) white text would
        # vanish — redraw the part of the text over the fill in dark grey.
        if fill_w > 0 and QColor(fg).lightnessF() > 0.8:
            p.save()
            p.setClipRect(QRect(bar_x, bar_y, fill_w, bar_h))
            p.setPen(QColor("#1a1a1a"))
            p.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, text)
            p.restore()

        p.end()

    def mousePressEvent(self, event):
        if self._clickable and event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._level)


# ── Rank badge (belt + main rank name) ─────────────────────────────────────────

def _luma(c: QColor) -> float:
    return 0.2126 * c.redF() + 0.7152 * c.greenF() + 0.0722 * c.blueF()


def rank_outline_color(color_a: str, color_b: str) -> QColor:
    """Outline colour for the rank picture / badge / cards: the lighter of
    the rank's two colours, brightened when both are dark (Samurai's dark
    red and dark blue vanished on the dark UI)."""
    c = max((QColor(color_a), QColor(color_b)), key=_luma)
    return c.lighter(175) if _luma(c) < 0.22 else c


def _section_card(outer: QVBoxLayout, title: str = None) -> QVBoxLayout:
    """A rounded panel for one section of a tab (owner 2026-10-18: section
    cards); theme.py styles QFrame#kcard. Returns the layout to fill."""
    card = QFrame()
    card.setObjectName("kcard")
    _SpillLayer(card)
    lay = QVBoxLayout(card)
    lay.setContentsMargins(14, 10, 14, 12)
    lay.setSpacing(10)
    if title:
        t = QLabel(f"<b>{title}</b>")
        t.setStyleSheet(SECTION_CSS)
        lay.addWidget(t)
    outer.addWidget(card)
    return lay


# ── moon mode: the night behind the tubes (owner 2026-10-25, mock-up M2) ─────
# Amaterasu mode is the sun; the default is the moon (Tsukuyomi): a near-black
# sky with distant stars and a thin crescent, and every tube's light spilling
# onto the wall behind it. None of it in gold mode.

SPILL = 0.38            # light spill strength (0–1) at the pool's centre
SPILL_REACH = 420       # px the pool reaches past the lit part's ends
SKY_STARS = 140         # stars on a 1916 × 1004 window (scaled by area)
MOON_ALPHA = 0.75
STAR_PARALLAX = 0.5     # the stars move with the page at this fraction of its scroll (far away)
BOKEH = 8               # out-of-focus city lights far behind (scaled by area)
BOKEH_ALPHA = 8         # their brightest (0–255): barely there (owner 2026-10-25: 16 was too much)
BOKEH_STEP_MS = 4000    # they drift a pixel or two this often (a whole-window repaint)
PAGE_FADE = 24          # px: the page melts into the dark under the tab bar (owner 2026-10-26, mock-up A)
BOKEH_PARALLAX = 0.25   # they move with the page at this fraction of its scroll (0 = fixed; owner 2026-10-26)
REFLECTION_ROOM = 26    # px under the last tube of a section for its reflection
REFLECTION_DEPTH = 26   # px each tube's reflection reaches below it
REFLECTION_ALPHA = 110


def _fx(key) -> bool:
    """Settings → Night look: this effect on (effects.FX)."""
    from . import effects
    return effects.fx(key)


class _SpillLayer(QWidget):
    """The light the tubes (LevelBars) in one section card throw on the wall
    behind them: a wide soft pool in each one's glow colour, under every
    other widget of the card (the bar tracks are see-through for it). It
    follows the tubes' flicker (_neon_repaint → _spill_update)."""

    def __init__(self, card: QWidget):
        super().__init__(card)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        card._spill_layer = self
        card.installEventFilter(self)
        self.lower()

    def eventFilter(self, obj, event):
        if event.type() in (QEvent.Type.Resize, QEvent.Type.Show):
            self.setGeometry(obj.rect())
            self.lower()
        return False

    def pool(self, b):
        """(centre, rx, ry, colour, alpha) of bar b's pool in this layer's
        coordinates, or None when it throws no light."""
        if _GOLD_MODE["on"] or b._pct <= 0 or not b.isVisible() or not _fx("fx_spill"):
            return None
        light = _intro_light(b)
        if light <= 0:
            return None
        tl = b.mapTo(self.parentWidget(), QPoint(0, 0))
        bw = b.width() - 2 * b._pad
        fw = max(bw * min(b._pct, 1.0), 8)
        compact = b.height() <= 40
        c = QPointF(tl.x() + b._pad + fw / 2, tl.y() + b.height() / 2)
        a = 255 * SPILL * (0.5 + 0.5 * min(b._pct, 1.0)) * light * (0.6 if compact else 1.0)
        rx = fw / 2 + SPILL_REACH * (0.5 if compact else 1.0)
        return c, rx, (45 if compact else 95), QColor(b._glow), a

    def _reflect(self, p, bars):
        """Every tube mirrored just below it, broken into ripples like wet
        pavement (Settings → Night look → Puddle reflection; owner
        2026-10-25: under all the bars, not only the last)."""
        if _GOLD_MODE["on"] or not _fx("fx_spill"):     # reflections go with the light spill (owner 2026-10-26)
            return
        card = self.parentWidget()
        for b in bars:
            if b.isVisible() and b.height() > 40 and b._pct > 0:
                self._reflect_one(p, card, b)

    def _reflect_one(self, p, card, b):
        light = _intro_light(b)
        if light <= 0:
            return
        tl = b.mapTo(card, QPoint(0, 0))
        bw = b.width() - 2 * b._pad
        fw = max(bw * min(b._pct, 1.0), 8)
        x0 = tl.x() + b._pad
        top = tl.y() + (b.height() - b._bar_h) // 2 + b._bar_h + 3
        depth = REFLECTION_DEPTH
        col = QColor(b._fg)
        import math
        for i in range(0, int(depth), 2):
            k = 1 - i / depth
            a = REFLECTION_ALPHA * light * k * k * (0.55 + 0.45 * math.sin(i * 1.7 + x0) ** 2)
            if a < 2:
                continue
            c = QColor(col)
            c.setAlpha(int(a))
            wob = 3 * math.sin(i * 0.9 + fw * 0.01)            # the water moves the line
            p.fillRect(QRectF(x0 + wob + i * 0.4, top + i, fw - i * 0.8, 1.4), c)

    def paintEvent(self, event):
        try:
            p = QPainter(self)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.setPen(Qt.PenStyle.NoPen)
            bars = self.parentWidget().findChildren(LevelBar)
            self._reflect(p, bars)
            for b in bars:
                pool = self.pool(b)
                if pool is None:
                    continue
                c, rx, ry, col, a = pool
                if not event.rect().intersects(QRectF(c.x() - rx, c.y() - ry, 2 * rx, 2 * ry).toRect()):
                    continue
                g = QRadialGradient(QPointF(0, 0), 1.0)
                for at, k in ((0.0, 1.0), (0.5, 0.7), (0.8, 0.3), (1.0, 0.0)):
                    cc = QColor(col)
                    cc.setAlpha(int(a * k))
                    g.setColorAt(at, cc)
                p.save()
                p.translate(c)
                p.scale(rx, ry)
                p.setBrush(QBrush(g))
                p.drawEllipse(QPointF(0, 0), 1.0, 1.0)
                p.restore()
            p.end()
        except Exception:                        # never raise out of a paint (PyQt6 aborts)
            pass


def _spill_update(bar):
    """A tube's light changed (flicker, stutter, a new count): repaint its
    pool on the wall."""
    w = bar.parentWidget()
    while w is not None and getattr(w, "_spill_layer", None) is None:
        w = w.parentWidget()
    if w is None:
        return
    tl = bar.mapTo(w, QPoint(0, 0))
    w._spill_layer.update(QRect(tl.x() - SPILL_REACH, tl.y() - 100,
                                bar.width() + 2 * SPILL_REACH, bar.height() + 200))


class _PageFade(QWidget):
    """A band at the top of a page scroller, from the window's background
    to clear: the page melts into the dark under the tab bar instead of
    being cut along a line (owner 2026-10-26: the header and the page felt
    split). Stays put while the page scrolls under it."""

    def __init__(self, viewport: QWidget, window: QWidget):
        super().__init__(viewport)
        self._win = window
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        viewport.installEventFilter(self)
        self.setGeometry(0, 0, viewport.width(), PAGE_FADE)
        self.raise_()
        self.show()

    def eventFilter(self, obj, event):
        if event.type() in (QEvent.Type.Resize, QEvent.Type.ChildAdded):
            self.setGeometry(0, 0, obj.width(), PAGE_FADE)
            self.raise_()                        # above a page widget set later
        return False

    def paintEvent(self, event):
        try:
            from . import theme
            top, bottom = ((theme.GOLD_BG_TOP, theme.GOLD_BG_BOTTOM) if _GOLD_MODE["on"]
                           else (theme.BG_TOP, theme.BG_BOTTOM))
            # the window's gradient, at the height of this band
            k = min(max(self.mapTo(self._win, QPoint(0, 0)).y() / max(self._win.height(), 1), 0.0), 1.0)
            a, b = QColor(top), QColor(bottom)
            c = QColor(int(a.red() + (b.red() - a.red()) * k), int(a.green() + (b.green() - a.green()) * k),
                       int(a.blue() + (b.blue() - a.blue()) * k))
            g = QLinearGradient(0, 0, 0, self.height())
            g.setColorAt(0, c)
            c2 = QColor(c)
            c2.setAlpha(0)
            g.setColorAt(1, c2)
            p = QPainter(self)
            p.fillRect(self.rect(), QBrush(g))
            p.end()
        except RuntimeError:
            pass


class _NightSky(QWidget):
    """Distant stars (and, in the main window, a thin crescent moon top
    right) behind everything: drawn once per size into a pixmap. Few and
    dim, so text stays easy to read; hidden in gold mode."""

    def __init__(self, window: QWidget, moon: bool):
        super().__init__(window)
        self._moon = moon
        self._pm = None
        self._pm_key = None
        self._win = window
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        window.installEventFilter(self)
        self.setGeometry(window.rect())
        self.lower()
        self.show()
        import random, time
        rnd = random.Random()            # a different city every window (owner 2026-10-25)
        palette = ("#ff2e88", "#2ec5ff", "#ffb02e", "#9b5cff", "#2eff9a", "#ff5e3a")
        # (x, y as 0–1, radius px, colour, drift phase): far city lights
        self._bokeh = [(rnd.random(), rnd.uniform(0.05, 0.95), rnd.uniform(40, 110),
                        QColor(rnd.choice(palette)), rnd.uniform(0, 6.3)) for _ in range(BOKEH * 3)]
        self._t0 = time.monotonic()
        self._drift = QTimer(self)
        self._drift.setInterval(BOKEH_STEP_MS)
        self._drift.timeout.connect(self._step)
        self._drift.start()
        # The stars scroll with the page, a little slower (owner 2026-10-25):
        # each page scroller's bar is followed once it exists (tabs build late).
        self._off = 0.0
        self._boff = 0.0                 # the bokeh's scroll offset (BOKEH_PARALLAX)
        self._bars = {}
        self._watch = QTimer(self)
        self._watch.setInterval(1000)
        self._watch.timeout.connect(self._follow_pages)
        self._watch.start()
        QTimer.singleShot(0, self._follow_pages)

    def _follow_pages(self):
        try:
            from .rain import page_scroll_areas
            for area in page_scroll_areas(self._win):
                bar = area.verticalScrollBar()
                if id(bar) not in self._bars:
                    self._bars[id(bar)] = bar.value()
                    _PageFade(area.viewport(), self._win)
                    bar.valueChanged.connect(lambda v, a=area, b=bar: self._scrolled(a, b, v))
        except RuntimeError:
            pass

    def _scrolled(self, area, bar, value):
        try:
            dy = value - self._bars.get(id(bar), value)
            self._bars[id(bar)] = value
            if dy and area.isVisible() and not _GOLD_MODE["on"]:
                self._off += dy * STAR_PARALLAX          # stars: no switch (owner 2026-10-26)
                if _fx("fx_bokeh"):
                    self._boff += dy * BOKEH_PARALLAX
                self.update()
        except RuntimeError:
            pass

    def _step(self):
        """The bokeh drifts: a whole-window repaint, so only now and then,
        and only while it can be seen."""
        try:
            w = self._win
            if (w.isVisible() and not w.isMinimized() and w.isActiveWindow()
                    and not _GOLD_MODE["on"] and _fx("fx_bokeh")):
                self.update()
        except RuntimeError:
            pass

    def _paint_bokeh(self, p, rect):
        import math, time
        w, h = self.width(), self.height()
        t = time.monotonic() - self._t0
        n = int(BOKEH * w * h / (1916 * 1004) + 0.5)
        for fx_, fy, r, col, ph in self._bokeh[:max(n, 3)]:
            x = fx_ * w + 60 * math.sin(t * 0.01 + ph)
            y = fy * h + 25 * math.cos(t * 0.008 + ph * 1.3) - self._boff
            y = (y + r) % (h + 2 * r) - r           # scrolled off one edge, back in at the other
            if not rect.intersects(QRect(int(x - r), int(y - r), int(2 * r), int(2 * r))):
                continue
            g = QRadialGradient(QPointF(x, y), r)
            for at, k in ((0.0, 0.55), (0.82, 0.8), (0.93, 1.0), (1.0, 0.0)):   # the brighter rim of a lens disc
                c = QColor(col)
                c.setAlpha(int(BOKEH_ALPHA * k))
                g.setColorAt(at, c)
            p.setBrush(QBrush(g))
            p.drawEllipse(QPointF(x, y), r, r)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Resize:
            self.setGeometry(obj.rect())
            self._pm = None
            self.lower()
        return False

    def _render(self):
        import random
        w, h = max(self.width(), 1), max(self.height(), 1)
        pm = QPixmap(w, h)
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        rnd = random.Random(7)                   # the same sky every time
        for _ in range(int(SKY_STARS * w * h / (1916 * 1004))):
            x, y = rnd.random() * w, rnd.random() * h      # even: it wraps round as the page scrolls
            r = rnd.choice((0.5, 0.6, 0.7, 0.8, 1.0, 1.2))
            a = rnd.randint(50, 150) if r < 1 else rnd.randint(120, 200)
            tint = rnd.choice(((255, 255, 255), (220, 230, 255), (255, 240, 220)))
            p.setBrush(QColor(*tint, a))
            p.drawEllipse(QPointF(x, y), r, r)
        p.end()
        return pm

    def _paint_moon(self, p):
        if self._moon:
            w = self.width()
            mx, my, mr = w - 150, 34, 15
            g = QRadialGradient(QPointF(mx, my), mr * 5)
            g.setColorAt(0, QColor(200, 210, 235, int(28 * MOON_ALPHA)))
            g.setColorAt(1, QColor(200, 210, 235, 0))
            p.setBrush(QBrush(g))
            p.drawEllipse(QPointF(mx, my), mr * 5, mr * 5)
            disc = QPainterPath()
            disc.addEllipse(QPointF(mx, my), mr, mr)
            bite = QPainterPath()
            bite.addEllipse(QPointF(mx + mr * 0.55, my - mr * 0.25), mr * 0.95, mr * 0.95)
            p.setBrush(QColor(225, 230, 242, int(255 * MOON_ALPHA)))
            p.drawPath(disc.subtracted(bite))

    def paintEvent(self, event):
        if _GOLD_MODE["on"]:
            return
        try:
            p = QPainter(self)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.setPen(Qt.PenStyle.NoPen)
            if _fx("fx_bokeh"):
                self._paint_bokeh(p, event.rect())
            # stars and moon: always, no switch (owner 2026-10-26)
            if self._pm is None or self._pm.size() != self.size():
                self._pm = self._render()
            o = int(self._off) % max(self.height(), 1)      # the sky wraps round
            p.drawPixmap(0, -o, self._pm)
            p.drawPixmap(0, self.height() - o, self._pm)
            self._paint_moon(p)
            p.end()
        except Exception:
            pass


def attach_sky(window, moon: bool = False):
    """Moon mode's night sky behind this window (main window: with the moon)."""
    try:
        window._sky = _NightSky(window, moon)
    except Exception:
        import traceback
        traceback.print_exc()


class _EmptyHint(QObject):
    """A friendly line in the middle of an empty table (owner 2026-10-18:
    empty states), hidden as soon as it has rows."""

    def __init__(self, view, text: str):
        super().__init__(view)
        self._view = view
        self.label = QLabel(text, view.viewport())
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setWordWrap(True)
        self.label.setStyleSheet("color: #8a8a8a; font-size: 13px; background: transparent;"
                                 " padding: 0 24px;")
        self.label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        view.viewport().installEventFilter(self)
        m = view.model()
        for sig in (m.rowsInserted, m.rowsRemoved, m.modelReset, m.layoutChanged):
            sig.connect(self.update_state)
        self.update_state()

    def update_state(self, *_):
        try:
            empty = self._view.model().rowCount() == 0
            self.label.setGeometry(self._view.viewport().rect())
            self.label.setVisible(empty)
        except RuntimeError:
            pass

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Resize:
            self.update_state()
        return False


def set_empty_hint(view, text: str) -> "_EmptyHint":
    """Show text in the middle of view (a table or list) while it's empty."""
    hint = _EmptyHint(view, text)
    view._jlpt_empty_hint = hint            # kept alive with the view
    return hint


def _paint_bar_track(p, x, y, w, h, r):
    """The empty part of a progress bar: near-black with a faint light edge
    (owner 2026-10-18: #1e1e1e melted into the window's gradient)."""
    p.setPen(QPen(QColor(255, 255, 255, 18), 1))
    # see-through (owner 2026-10-25, moon mode): the tubes' light spill and
    # the stars show through it, like light on a wall behind dark glass
    p.setBrush(QColor(8, 8, 10, 130))
    p.drawRoundedRect(QRectF(x, y, w, h).adjusted(0.5, 0.5, -0.5, -0.5), r, r)
    p.setPen(Qt.PenStyle.NoPen)


class _RankKanji(QWidget):
    """The badge's rank kanji in the rank's own two colours (lighter one on
    top; owner 2026-10-18, as on the share image), wrapped sticker-style in
    a white rim inside a dark rim, so it reads on the rank-coloured badge
    whatever the colours."""

    def __init__(self, text: str, color_a: str, color_b: str, pt: int = 26, parent=None):
        super().__init__(parent)
        self._text = text
        ca, cb = QColor(color_a), QColor(color_b)
        self._top, self._bottom = (cb, ca) if _luma(cb) >= _luma(ca) else (ca, cb)
        # A light badge (Amaterasu below 20,000: gold → pale gold): the
        # sticker flips — dark gold rim inside, white glow outside, and a
        # deeper gold at the bottom, or the kanji melts into the badge.
        self._light = (_luma(ca) + _luma(cb)) / 2 > 0.6
        if self._light:
            self._bottom = QColor(self._bottom).darker(135)
        self._font = QFont()
        self._font.setBold(True)
        self._font.setPointSize(pt)
        fm = QFontMetricsF(self._font)
        self.setFixedHeight(int(fm.height() + 12))
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        fm = QFontMetricsF(self._font)
        w = fm.horizontalAdvance(self._text)
        r = QRectF(self.rect())
        base = QPointF(r.center().x() - w / 2, r.center().y() + (fm.ascent() - fm.descent()) / 2)
        path = QPainterPath()
        path.addText(base, self._font, self._text)
        p.setBrush(Qt.BrushStyle.NoBrush)
        rims = (((10, QColor(255, 252, 235, 150)),    # light glow
                 (6.5, QColor(255, 255, 255, 230)),   # white rim
                 (3.4, QColor(107, 74, 0, 245)))      # dark gold rim
                if self._light else
                ((9, QColor(0, 0, 0, 70)),             # soft shadow
                 (6.5, QColor(0, 0, 0, 200)),          # dark rim
                 (3.2, QColor(255, 255, 255, 235))))   # white rim
        for width, col in rims:
            pen = QPen(col, width)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            p.setPen(pen)
            p.drawPath(path.translated(0, 1.5) if (width == 9 and not self._light) else path)
        top = base.y() - fm.ascent()
        g = QLinearGradient(0, top, 0, base.y() + fm.descent() * 0.3)
        g.setColorAt(0, self._top)
        g.setColorAt(1, self._bottom)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(g))
        p.drawPath(path)
        p.end()


BELT_STRIP_H = 24   # px, the cloth belt behind "BLUE BELT"


class _BeltStrip(QWidget):
    """The badge's belt line as an actual belt (owner 2026-10-26): a cloth
    band in the belt's colour, rows of stitching along its edges and square
    cut ends, the name in plain white or black on it. Coloured text on the
    rank's colour (purple on orange, black on dark red) vanished. Degree
    black belts (Amaterasu, second degree on) carry gold bars at the end,
    one per degree.
    Two fixed lengths (owner): every plain belt as long as the longest
    name, every degree belt as long as the longest degree name plus room
    for ten bars, so the belt doesn't change size from belt to belt.
    The name is a child QLabel so divine_text still translates it."""

    _PAD = 26
    _BARS_W = 10 * 5 + 8     # ten degree bars and a gap
    _lengths: dict = {}      # degree belt? → width, measured once

    def __init__(self, text: str, color: str, degree: int = 0, gold: bool = False, parent=None):
        super().__init__(parent)
        self._cloth = QColor(color)
        self._degree = degree
        self._light = _luma(self._cloth) > 0.55
        ink = "#f5c518" if gold else ("#1a1a1a" if self._light else "#ffffff")
        self.label = QLabel(text, self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # size in the style sheet: theme.py's QDialog#kotodama font-size beats setFont
        self.label.setStyleSheet(f"color: {ink}; background: transparent; font-size: 9pt;"
                                 " font-weight: bold; letter-spacing: 1px;")
        if gold:
            self.label.setProperty("jlpt_keep_color", True)
        w = self._length(bool(degree))
        bars = self._BARS_W if degree else 0
        self.setFixedSize(w, BELT_STRIP_H)
        # the name centred in the cloth left of the bars
        self.label.setGeometry(self._PAD, 0, w - 2 * self._PAD - bars, BELT_STRIP_H)

    def _length(self, degree: bool) -> int:
        if degree not in self._lengths:
            names = ([f"{o.upper()}-DEGREE BLACK BELT" for o in rank_data.DEGREE_ORDINALS[1:]]
                     if degree else [f"{b.upper()} BELT" for b in rank_data.BELTS])
            probe = QLabel(styleSheet=self.label.styleSheet())
            tw = 0
            for n in names:
                probe.setText(n)
                tw = max(tw, probe.sizeHint().width())
            probe.deleteLater()
            _BeltStrip._lengths[degree] = tw + 2 * self._PAD + (self._BARS_W if degree else 0)
        return self._lengths[degree]

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -1.5)
        # a soft drop shadow lifts it off the badge
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 0, 0, 90))
        p.drawRoundedRect(r.translated(0, 1.5), 2, 2)
        # cloth: lighter on top, darker below, as if folded round a waist
        c = self._cloth
        g = QLinearGradient(0, r.top(), 0, r.bottom())
        g.setColorAt(0, c.lighter(118))
        g.setColorAt(0.5, c)
        g.setColorAt(1, c.darker(135))
        p.setBrush(QBrush(g))
        edge = c.darker(170) if self._light or _luma(c) > 0.2 else QColor(90, 90, 90)
        p.setPen(QPen(edge, 1))
        p.drawRoundedRect(r, 2, 2)
        # stitching: two rows along each edge, the full length
        st = QColor(0, 0, 0, 55) if self._light else QColor(255, 255, 255, 38)
        p.setPen(QPen(st, 1))
        for y in (r.top() + 3, r.top() + 5.5, r.bottom() - 5.5, r.bottom() - 3):
            p.drawLine(QPointF(r.left() + 2, y), QPointF(r.right() - 2, y))
        # degree bars (black belts in Amaterasu): gold, at the right end
        if self._degree:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor("#d4a017"))
            x = r.right() - 6
            for _ in range(self._degree):
                p.drawRect(QRectF(x - 3, r.top() + 1, 3, r.height() - 2))
                x -= 5
        p.end()


class RankBadge(QWidget):
    """
    Badge showing belt + rank identity, with a gradient background that
    uses each rank's own signature colors.

        ┌─────────────────────────────────┐
        │  ░░░░ gradient bg ░░░░░░░░░░░  │
        │       BLUE BELT                 │
        │           侍                    │
        │         Samurai                 │
        └─────────────────────────────────┘

    The gradient runs left→right using (rank_color_a, rank_color_b).
    The text glows with the accent color (rank_color_b).
    """

    clicked = pyqtSignal()   # emitted only when the current rank is Amaterasu

    def __init__(self, info: dict, parent=None):
        super().__init__(parent)
        self._info        = info
        self._art_pixmap  = None
        self._art_label   = None
        # Initialize paint attributes before _build so paintEvent never
        # fires on a partially-constructed object and hits AttributeError.
        self._color_a = info.get("rank_color_a", "#1565c0")
        self._color_b = info.get("rank_color_b", "#42a5f5")
        self._glow_blur   = 0
        self._glow_alpha  = 0
        self._glow_color_b = self._color_b
        self._art_avail      = 480
        self._video          = None   # rank_video.RankVideo: animated picture
        self._video_img      = None   # its latest frame
        self._intro_pending  = False  # ascension intro about to play: stay dark
        self._build(info)
        self._update_cursor()
        # Flickers on like a lit billboard, as on the mini widget (owner
        # 2026-10-22): the whole badge (background, glow, picture, title)
        # is one sign, darkened by a veil until it's on screen and lit.
        from .mini_widget import BILLBOARD_OFF
        _NeonVeil(self, BILLBOARD_OFF, radius=8)
        _neon_register(self)

    @property
    def _divine(self) -> bool:
        # Amaterasu MODE (exactly 20,000), not the Amaterasu rank that starts
        # at 13,800 (owner: all divine effects only in Amaterasu mode).
        return bool(self._info.get("is_max_amaterasu"))

    def art_rect(self) -> QRectF | None:
        """Where the rank picture is drawn, in badge coordinates (the pixmap
        is centred inside its label, which can be wider)."""
        art = getattr(self, "_art_label", None)
        pm = art.pixmap() if art is not None and art.isVisible() else None
        if pm is None or pm.isNull():
            return None
        dpr = pm.devicePixelRatio() or 1.0
        w, h = pm.width() / dpr, pm.height() / dpr
        g = art.geometry()
        return QRectF(g.x() + (g.width() - w) / 2, g.y() + (g.height() - h) / 2, w, h)

    def halo_point(self) -> QPointF:
        """The centre of Amaterasu's hair bun (where the light behind her
        is): the rays' vanishing point, tucked behind the bun by the
        overlay's silhouette mask. The badge centre without art."""
        ar = self.art_rect()
        if ar is not None:
            return QPointF(ar.x() + ar.width() * AMATERASU_BUN[0],
                           ar.y() + ar.height() * AMATERASU_BUN[1])
        return QPointF(self.rect().center())

    def divine_tick(self):
        """Called by DivineOverlay's clock: repaint (the sunburst and inner
        glow breathe)."""
        self.update()

    def _update_cursor(self):
        """Show a pointer cursor when the badge is clickable (Amaterasu only)."""
        if self._info.get("is_max_amaterasu"):
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            self.setToolTip("Click to relive the ascension")
        else:
            self.unsetCursor()
            self.setToolTip("")

    def mousePressEvent(self, event):
        if (event.button() == Qt.MouseButton.LeftButton
                and self._info.get("is_max_amaterasu")):
            self.clicked.emit()
        else:
            super().mousePressEvent(event)

    def _build(self, info: dict):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(2)

        color_a = info["rank_color_a"]   # dominant
        color_b = info["rank_color_b"]   # accent / glow
        rank_idx = info["rank_index"]    # 0–9

        # bars from the second degree on; the first is a plain black belt
        degree = (info.get("degree_index") or 0) + 1 if info.get("is_amaterasu_black") else 0
        degree = degree if degree >= 2 else 0
        belt = _BeltStrip(f"{info['belt_display_name'].upper()} BELT", info["belt_color"],
                          degree, gold=bool(info.get("is_max_amaterasu")))
        layout.addWidget(belt, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addSpacing(2)

        # On a White belt the badge background uses the rank's light accent
        # color (e.g. Amaterasu's near-white gold #fff8c5), making white or
        # light-grey text invisible.  Force a solid dark shadow on both the
        # kanji and subtitle labels so they always read regardless of bg.
        is_white_belt = info["belt_name"] == "White"

        # Japanese rank name — glow scales with rank using shared helper
        jp_lbl = QLabel(info["rank_name_jp"])
        jp_font = QFont()
        jp_font.setBold(True)
        jp_font.setPointSize(26)
        jp_lbl.setFont(jp_font)
        # size in the style sheet: theme.py's QDialog#kotodama font-size beats setFont (owner 2026-10-26)
        jp_lbl.setStyleSheet("color: #ffffff; background: transparent; font-size: 26pt; font-weight: bold;")
        jp_blur, jp_alpha = _rank_glow_params(rank_idx)
        jp_blur  = max(jp_blur,  22)
        jp_alpha = max(jp_alpha, 200)
        # Always apply a dark drop shadow so the kanji reads on any badge
        # background (including light ones like White Belt Amaterasu).
        # On non-white belts the shadow is subtle; on white belt it's stronger
        # since the background is brightest there.
        shadow = QGraphicsDropShadowEffect(jp_lbl)
        shadow.setBlurRadius(10 if is_white_belt else 8)
        shadow.setOffset(1, 2)
        shadow.setColor(QColor(0, 0, 0, 230))
        if info.get("is_max_amaterasu"):
            # Dark gold kanji with a bright light-gold glow (owner): reads
            # on the blown-out light and still radiates.
            jp_lbl.setStyleSheet("color: #6b4a00; background: transparent; font-size: 26pt; font-weight: bold;")
            jp_lbl.setProperty("jlpt_keep_color", True)
            shadow.setBlurRadius(26)
            shadow.setOffset(0, 0)
            shadow.setColor(QColor(255, 250, 215, 255))
            jp_lbl.setGraphicsEffect(shadow)
            jp_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(jp_lbl)
        else:
            # Below Amaterasu mode: the kanji in the rank's colours.
            jp_lbl.deleteLater()
            layout.addWidget(_RankKanji(info["rank_name_jp"], color_a, color_b))

        # English subtitle — always has a dark drop shadow for legibility on
        # any badge background. Smaller blur/offset than the kanji since the
        # font is much smaller and a heavy shadow would look muddy.
        en_lbl = QLabel(info["rank_name_en"])
        en_font = QFont()
        en_font.setPointSize(11)
        en_lbl.setFont(en_font)
        en_lbl.setStyleSheet("color: #cccccc; background: transparent;")
        en_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        en_shadow = QGraphicsDropShadowEffect(en_lbl)
        en_shadow.setBlurRadius(4)
        en_shadow.setOffset(1, 1)
        en_shadow.setColor(QColor(0, 0, 0, 200))
        en_lbl.setGraphicsEffect(en_shadow)
        layout.addWidget(en_lbl)
        if not info.get("is_max_amaterasu") and (
                _luma(QColor(color_a)) + _luma(QColor(color_b))) / 2 > 0.6:
            # Light badge (Amaterasu below 20,000): grey text washed out on
            # the pale gold — dark gold with a light glow, as in 20,000 mode.
            en_lbl.setStyleSheet("color: #6b4a00; background: transparent;")
            en_shadow.setOffset(0, 0)
            en_shadow.setBlurRadius(8)
            en_shadow.setColor(QColor(255, 250, 215, 230))
        if info.get("is_max_amaterasu"):
            # Gold mode is all Japanese: 天照 above already says it (owner:
            # no Japanese + English duplicates).
            en_lbl.hide()

        # ── Rank art image ────────────────────────────────────────────────────
        try:
            from . import rank_images
            art_bytes = rank_images.get_rank_art(info["rank_name_en"])
        except Exception:
            art_bytes = None

        if art_bytes:
            pixmap = QPixmap()
            pixmap.loadFromData(art_bytes, "JPEG")
            if not pixmap.isNull():
                self._art_pixmap = pixmap
                self._art_label  = QLabel()
                self._art_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self._art_label.setStyleSheet("background: transparent;")

                # Glow behind the art image, scaling with rank
                art_blur, art_alpha = _rank_glow_params(rank_idx)
                self._art_glow = None
                if art_blur > 0:
                    art_glow = QGraphicsDropShadowEffect(self._art_label)
                    art_glow.setBlurRadius(art_blur)
                    art_glow.setOffset(0, 0)
                    art_col = QColor(color_b)
                    art_col.setAlpha(art_alpha)
                    art_glow.setColor(art_col)
                    # Amaterasu: no blur effect — DivineOverlay's blown-out
                    # sky and feathered edges replace it, and a big blur
                    # re-rendered under the overlay every frame was the
                    # main source of lag.
                    if not info.get("is_max_amaterasu"):
                        self._art_label.setGraphicsEffect(art_glow)

                spacer = QWidget(); spacer.setFixedHeight(6)
                spacer.setStyleSheet("background: transparent;")
                layout.addWidget(spacer)
                layout.addWidget(self._art_label)
                self._rescale_art(480)
                # Amaterasu moves only in Amaterasu mode (20,000; owner
                # 2026-10-15); below it her still picture stays.
                if info["rank_name_en"] != "Amaterasu" or info.get("is_max_amaterasu"):
                    self._setup_video(info["rank_name_en"])
                else:
                    self._drop_video()
        else:
            self._art_pixmap = None
            self._art_label  = None
            self._drop_video()

        # ── Badge-level background glow ───────────────────────────────────────
        # We store the glow params and draw extra halo passes in paintEvent
        # rather than using self.setGraphicsEffect(), because Qt disables child
        # widget effects (jp_lbl glow, art_label glow) when a QGraphicsEffect
        # is applied to the parent — so paintEvent handles the outer glow.
        self._glow_blur, self._glow_alpha = _rank_glow_params(rank_idx)
        self._glow_color_b = color_b

    def paintEvent(self, event):
        """Draw gradient background + halo glow rings for Nihonjin→Amaterasu."""
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect()

        # ── outer halo rings (drawn before the fill so they appear behind) ──
        blur  = getattr(self, "_glow_blur",   0)
        alpha = getattr(self, "_glow_alpha",  0)
        gcol  = getattr(self, "_glow_color_b", "#ffffff")
        if blur > 0:
            n_rings = 5 if blur >= 80 else 3   # Amaterasu gets more rings
            for i in range(n_rings, 0, -1):
                frac    = i / n_rings
                spread  = int(blur * frac * 0.45)
                ring_a  = int(alpha * (frac ** 1.6))
                c = QColor(gcol)
                c.setAlpha(min(ring_a, 220))
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(c)
                rr = r.adjusted(-spread, -spread, spread, spread)
                p.drawRoundedRect(rr, 10 + spread, 10 + spread)

        # ── gradient fill ────────────────────────────────────────────────────
        grad = QLinearGradient(r.left(), 0, r.right(), 0)
        ca = QColor(self._color_a)
        cb = QColor(self._color_b)
        ca.setAlpha(160)
        cb.setAlpha(100)
        grad.setColorAt(0.0, ca)
        grad.setColorAt(1.0, cb)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(grad)
        p.drawRoundedRect(r, 8, 8)

        if self._divine and not getattr(self, "_divine_failed", False):
            try:
                self._paint_divine(p, r)
            except Exception:
                # Never let the effect break the badge (or raise every frame).
                import traceback
                traceback.print_exc()
                self._divine_failed = True

        # ── border ───────────────────────────────────────────────────────────
        # 2 px in the rank's accent colour, like the share image's outline
        # (owner 2026-10-18; was 1 px at half strength). Amaterasu mode keeps
        # the soft one: its light spills past the edge.
        border_col = (QColor(self._color_b) if self._divine
                      else rank_outline_color(self._color_a, self._color_b))
        border_col.setAlpha(120 if self._divine else 255)
        pen = QPen(border_col, 1 if self._divine else 2)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(r).adjusted(1, 1, -1, -1), 8, 8)

        p.end()
        super().paintEvent(event)

    def _paint_divine(self, p: QPainter, r: QRect):
        """Amaterasu, inside the badge: brighter gold base, a sunburst on the
        light behind her head, and a breathing inner glow along the edge.
        The rays and the light that spills past the badge are drawn on top
        of the whole page by DivineOverlay. Legibility matters less here
        (owner 2026-10-09: everything reads "max" at 20,000)."""
        pulse = _divine_pulse(self)
        c = self.halo_point()
        reach = max(r.width(), r.height()) * 0.75
        clip = QPainterPath()
        clip.addRoundedRect(QRectF(r), 8, 8)
        p.save()
        p.setClipPath(clip)

        # Brighter gold base: the plain badge gradient reads muddy at max.
        base = QLinearGradient(r.left(), 0, r.right(), 0)
        base.setColorAt(0.0, QColor(245, 197, 24, 200))
        base.setColorAt(0.5, QColor(255, 236, 150, 210))
        base.setColorAt(1.0, QColor(255, 248, 197, 220))
        p.fillRect(r, QBrush(base))
        p.setOpacity(self.intro_light())   # held back in the intro's dark opening

        # Sunburst: white core → pale gold → clear, breathing in size.
        sun = QRadialGradient(c, reach * (0.5 + 0.15 * pulse))
        sun.setColorAt(0.0, QColor(255, 255, 255, 255))
        sun.setColorAt(0.35, QColor(255, 251, 225, int(200 + 40 * pulse)))
        sun.setColorAt(0.7, QColor(255, 236, 150, 90))
        sun.setColorAt(1.0, QColor(255, 236, 150, 0))
        p.fillRect(r, QBrush(sun))

        # Breathing inner glow along the edge.
        for i in range(6, 0, -1):
            pen = QPen(QColor(255, 250, 220, int((40 + 70 * pulse) * (i / 6) ** 2)))
            pen.setWidth(i * 3)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(QRectF(r).adjusted(1, 1, -1, -1), 8, 8)
        p.restore()

    def showEvent(self, event):
        super().showEvent(event)
        self._rescale_art(self.width())
        if self._video is not None and not self._intro_pending:
            self._video.resume()

    def hideEvent(self, event):
        if self._video is not None:
            self._video.pause()        # no decoding while nobody sees it
        super().hideEvent(event)

    def _art_size(self, w: int, h: int) -> tuple:
        """Picture size for a w×h source: the badge width less 40 px,
        max 220 px tall."""
        MAX_ART_H = 220
        target_w = max(120, self._art_avail - 40)
        if h * target_w / w > MAX_ART_H:
            return max(1, round(w * MAX_ART_H / h)), MAX_ART_H
        return target_w, max(1, round(h * target_w / w))

    def _rescale_art(self, available_width: int):
        """Scale the stored pixmap to fit available_width, max 220px tall."""
        self._art_avail = available_width
        if not getattr(self, "_art_pixmap", None) or self._art_label is None:
            return
        if self._intro_pending:
            self._show_dark()
            return
        if self._video_img is not None:
            self._show_video_img()
            return
        w, h = self._art_size(self._art_pixmap.width(), self._art_pixmap.height())
        self._art_label.setPixmap(self._framed(self._art_pixmap.scaled(
            w, h, Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation)))

    def _framed(self, pm: QPixmap) -> QPixmap:
        """The picture with rounded corners and a 2 px rank-colour outline,
        as on the share image (owner 2026-10-18). Amaterasu mode keeps its
        feathered, frameless picture (DivineOverlay blends it into the
        light)."""
        if self._divine or pm.isNull():
            return pm
        out = QPixmap(pm.size())
        out.setDevicePixelRatio(pm.devicePixelRatio())
        out.fill(Qt.GlobalColor.transparent)
        dpr = pm.devicePixelRatio() or 1.0
        r = QRectF(0, 0, pm.width() / dpr, pm.height() / dpr)
        p = QPainter(out)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        clip = QPainterPath()
        clip.addRoundedRect(r.adjusted(1, 1, -1, -1), 8, 8)
        p.setClipPath(clip)
        p.drawPixmap(r.toRect(), pm)
        p.setClipping(False)
        p.setPen(QPen(rank_outline_color(self._color_a, self._color_b), 2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(r.adjusted(1, 1, -1, -1), 8, 8)
        p.end()
        return out

    # ── Animated picture (rank_video; owner 2026-10-15) ───────────────────
    def _setup_video(self, rank_en: str):
        """Play the rank's animated picture in the art label if it has one
        (otherwise the still picture stays). Kept across update_info for
        the same rank, so the debug ±250 doesn't restart it."""
        if self._video is not None and self._video.rank != rank_en:
            self._drop_video()
        if self._video is None:
            try:
                from . import rank_video
                if rank_video.clip(rank_en, "loop") is None:
                    return
                video = rank_video.RankVideo(rank_en, self)
            except Exception:
                return
            if not video.ok:
                video.deleteLater()
                return
            video.frame.connect(self._on_video_frame)
            self._video = video
        if _ASCENSION["pending"] and self._video.has_intro():
            # Built for an ascension that's about to play: start dark, not
            # on the bright loop, until _ascend starts the intro.
            self._intro_pending = True
        self._rescale_art(self._art_avail)
        if self.isVisible() and not self._intro_pending:
            self._video.resume()

    def _drop_video(self):
        if self._video is not None:
            self._video.stop()
            self._video.deleteLater()
            self._video, self._video_img, self._intro_pending = None, None, False
            self._rescale_art(self._art_avail)     # back to the still picture

    def _on_video_frame(self, img: QImage):
        self._video_img = img
        if not self._intro_pending:
            self._show_video_img()

    def _show_video_img(self):
        if self._art_label is None:
            return
        img = self._video_img
        w, h = self._art_size(img.width(), img.height())
        self._art_label.setPixmap(self._framed(QPixmap.fromImage(img.scaled(
            w, h, Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation))))

    def _show_dark(self):
        """The intro's first frame is near black: hold that until it plays."""
        if self._art_label is None or not self._art_pixmap:
            return
        w, h = self._art_size(720, 480)
        pm = QPixmap(w, h)
        pm.fill(QColor(10, 8, 6))
        self._art_label.setPixmap(pm)

    def start_intro(self) -> bool:
        """The ascension: play the intro, then the loop. False without one."""
        self._intro_pending = False
        if self._video is None or not self._video.play_intro():
            self._rescale_art(self._art_avail)
            return False
        return True

    def intro_time(self) -> float | None:
        """Seconds into the intro on screen, or None when it isn't playing."""
        return self._video.intro_time() if self._video is not None else None

    def intro_shown(self) -> bool:
        """The intro is playing and its first frame is on screen."""
        return self._video is not None and self._video.intro_shown()

    def intro_light(self) -> float:
        """How much divine light to show (0–1): none in the intro's dark
        opening, rising as the light behind her blooms, full otherwise."""
        if self._intro_pending:
            return 0.0
        t = self.intro_time()
        if t is None:
            return 1.0
        from . import rank_video
        a, b = rank_video.INTRO_BLOOM.get(self._video.rank, (0.0, 0.0))
        return 0.0 if t <= a else 1.0 if t >= b else (t - a) / (b - a)

    def has_video(self) -> bool:
        return self._video is not None and self._video_img is not None

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._rescale_art(self.width())

    def update_info(self, info: dict):
        self._info = info
        self._color_a = info["rank_color_a"]
        self._color_b = info["rank_color_b"]
        self._art_pixmap = None
        self._art_label  = None
        self._art_glow   = None
        for child in self.findChildren(QWidget):
            child.deleteLater()
        old_layout = self.layout()
        if old_layout is not None:
            while old_layout.count():
                old_layout.takeAt(0)
            QWidget().setLayout(old_layout)
        self._build(info)
        self._update_cursor()
        self.update()


# ── Rank progress bar ───────────────────────────────────────────────────────────

def split_html(total: int, verb: str, cards: int, loans: int, hand: int, show_loans: bool) -> str:
    """The one "what this number is made of" line, shared by the JLPT bars,
    the Frequency Check and the rank (owner 2026-10-22: "unify how we show
    these"): "<b>5,194</b> known = 2,655 from your cards + 2,536 English
    loanwords + 3 marked found". The loanword part shows once any are marked."""
    return (f"<b>{total:,}</b> {verb} = {cards:,} from your cards"
            + (f" + {loans:,} English loanwords" if show_loans else "")
            + f" + {hand:,} marked found")


def _found_loans_jlpt(known_words) -> tuple[int, int]:
    """(English loanwords, other words) among a JLPT list's words marked found."""
    from . import jlpt_data
    found = [(d, r) for d, r, nid in known_words if nid is None]
    loans = sum(1 for d, r in found if jlpt_data.is_english_loanword(d, r))
    return loans, len(found) - loans


def _overview_add_delta(self, layout, key, color, what):
    """"+N this week · +N this month" under one of the Overview's main bars
    (owner 2026-10-15), from the history series the dialog computed."""
    from .history_view import delta_label
    lbl = delta_label(self._results.get("history_series"), key, color, what)
    if lbl is not None:
        layout.addWidget(lbl)


class RankBar(QWidget):
    _neon_tube = True
    """
    Progress bar for the OVERALL 0-20,000 Vocabulary Rank System total —
    paired with BeltBar below it, which shows progress within the current
    belt only.

    Visually similar to LevelBar (same glow language) but:
      - fill color comes from the CURRENT MAIN RANK (gradient blend of
        rank_color_a -> rank_color_b), not a fixed level color or belt
      - percentage shown is overall progress toward 20,000, not the
        current belt's local progress
      - at Black Belt Amaterasu (20,000 cards) this naturally renders
        bright gold, since that's Amaterasu's own rank color
      - tooltip explains cards remaining to the next belt/rank
    """

    _PAD = 28

    def __init__(self, info: dict, parent=None):
        super().__init__(parent)
        self.setFixedHeight(40)
        self.setMinimumWidth(200)
        self._apply_info(info)
        _neon_register(self)

    def _apply_info(self, info: dict):
        self._info = info
        self._pct  = info["overall_pct"]
        if info["is_max"]:
            tip = "Max rank reached — Tenth-Degree Black Belt Amaterasu (20,000 cards)"
        else:
            nxt = info["next_belt_name"]
            if info["next_rank_name"]:
                nxt_desc = f"{nxt} Belt {info['next_rank_name']}"
            else:
                nxt_desc = f"{nxt} Belt {info['rank_name']}"
            tip = (
                f"{info['cards_to_next']:,} cards to {nxt_desc}\n"
                f"({info['count']:,} / {info['max_cards']:,} total)"
            )
        self.setToolTip(tip)
        self.update()

    def update_info(self, info: dict):
        self._apply_info(info)

    def _glow_params(self):
        pct = self._pct
        if pct <= 0.0:
            return 0, 0, 0
        if pct >= 1.0:
            return 9, 30, 255
        t = min(pct, 0.999) ** 0.55
        layers     = 2 + int(t * 6)
        max_spread = int(3 + t * 22)
        peak_alpha = int(40 + t * 195)
        return layers, max_spread, peak_alpha

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

        w, h  = self.width(), self.height()
        pad   = self._PAD
        bar_x = pad
        bar_w = w - pad * 2
        bar_h = 24
        bar_y = (h - bar_h) // 2
        r     = 7

        # Use RANK colors (not belt colors) for fill and glow
        fg        = self._info["rank_color_a"]   # dominant rank color
        fg_accent = self._info["rank_color_b"]   # accent rank color
        fg_col    = QColor(fg)

        # Amaterasu uses the same bright gold gradient as LevelBar's
        # force_max_gold mode (light gold top -> light accent gold bottom)
        # instead of the generic darker() bottom stop every other rank uses —
        # otherwise Amaterasu's bar reads as muddy/dark instead of luminous.
        is_amaterasu = self._info["rank_name_en"] == "Amaterasu"
        if is_amaterasu:
            dark_col = QColor(fg_accent)   # light gold, not darkened
        else:
            dark_col = fg_col.darker(260)

        fill_w   = max(int(bar_w * self._pct), r * 2 if self._pct > 0 else 0)
        fill_w   = min(fill_w, bar_w)
        is_laser = self._pct >= 1.0
        self._lit = (QRect(bar_x, bar_y, fill_w, bar_h), QColor(fg)) if fill_w > 0 else None

        light = _intro_light(self)
        p.setOpacity(light)                  # neon intro: no glow while off
        # ── glow halos ───────────────────────────────────────────────────
        layers, max_spread, peak_alpha = self._glow_params()
        if layers > 0 and fill_w > 0:
            glow_col = QColor(fg_accent)   # glow uses the accent rank color
            for i in range(1, layers + 1):
                frac   = i / layers
                spread = max(1, int(max_spread * (1.0 - frac * 0.75)))
                alpha  = int(peak_alpha * (frac ** 1.4))
                alpha  = min(alpha, 255)

                gx  = max(0, bar_x - spread)
                gy  = max(0, bar_y - spread)
                gx2 = min(w, bar_x + fill_w + spread)
                gy2 = min(h, bar_y + bar_h + spread)
                gw  = gx2 - gx
                gh  = gy2 - gy
                gr  = r + spread

                c = QColor(glow_col)
                c.setAlpha(alpha)
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(c)
                p.drawRoundedRect(gx, gy, gw, gh, gr, gr)

            if is_laser:
                bloom_s = max_spread + 8
                bx  = max(0, bar_x - bloom_s)
                by  = max(0, bar_y - bloom_s)
                bx2 = min(w, bar_x + fill_w + bloom_s)
                by2 = min(h, bar_y + bar_h + bloom_s)
                bloom_col = QColor(glow_col)
                bloom_col.setAlpha(45)
                p.setBrush(bloom_col)
                p.drawRoundedRect(bx, by, bx2 - bx, by2 - by,
                                  r + bloom_s, r + bloom_s)

        p.setOpacity(1.0)
        # ── track ────────────────────────────────────────────────────────
        _paint_bar_track(p, bar_x, bar_y, bar_w, bar_h, r)

        p.setOpacity(NEON_OFF_FILL + (1 - NEON_OFF_FILL) * light)   # neon intro: unlit tube
        # ── filled portion ──────────────────────────────────────────────
        if fill_w > 0:
            # Gradient blends dominant → accent horizontally for rank identity
            h_grad = QLinearGradient(bar_x, 0, bar_x + fill_w, 0)
            h_grad.setColorAt(0.0, fg_col)
            h_grad.setColorAt(1.0, QColor(fg_accent))
            # Vertical lightness gradient overlaid via top-to-bottom
            v_grad = QLinearGradient(0, bar_y, 0, bar_y + bar_h)
            if self._pct >= 0.75:
                v_grad.setColorAt(0.0, fg_col.lighter(145))
                v_grad.setColorAt(0.4, fg_col)
                v_grad.setColorAt(1.0, dark_col)
            elif self._pct >= 0.45:
                v_grad.setColorAt(0.0, fg_col.lighter(115))
                v_grad.setColorAt(1.0, dark_col)
            else:
                v_grad.setColorAt(0.0, fg_col)
                v_grad.setColorAt(1.0, dark_col)

            p.setBrush(v_grad)
            p.drawRoundedRect(bar_x, bar_y, fill_w, bar_h, r, r)

            sheen = QLinearGradient(0, bar_y, 0, bar_y + bar_h // 2)
            sheen.setColorAt(0.0, QColor(255, 255, 255, 60))
            sheen.setColorAt(1.0, QColor(255, 255, 255, 0))
            p.setBrush(sheen)
            p.drawRoundedRect(bar_x, bar_y, fill_w, bar_h // 2, r, r)

            if is_laser:
                for border_w, border_alpha, border_color in [
                    (3, 180, QColor(255, 255, 200)),
                    (2, 230, QColor(255, 255, 255)),
                ]:
                    border_color.setAlpha(border_alpha)
                    pen = QPen(border_color)
                    pen.setWidth(border_w)
                    p.setPen(pen)
                    p.setBrush(Qt.BrushStyle.NoBrush)
                    p.drawRoundedRect(
                        bar_x + border_w // 2,
                        bar_y + border_w // 2,
                        fill_w - border_w,
                        bar_h - border_w,
                        r, r
                    )
                p.setPen(Qt.PenStyle.NoPen)

        p.setOpacity(NEON_OFF_TEXT + (1 - NEON_OFF_TEXT) * light)
        # ── text ─────────────────────────────────────────────────────────
        font = QFont()
        font.setBold(True)
        font.setPointSize(9)
        p.setFont(font)

        info = self._info
        if info["is_max"]:
            text = (f"極  ({info['count']:,} / {info['max_cards']:,})" if _GOLD_MODE["on"]
                    else f"MAX  ({info['count']:,} / {info['max_cards']:,})")
        else:
            # format_progress never rounds up to 100% before max_cards is
            # actually reached (19,999/20,000 shows 99.9%).
            text = jlpt_data.format_progress(info["count"], info["max_cards"])
        text_rect = QRect(bar_x, bar_y, bar_w, bar_h)

        if not _bar_text(p, text_rect, text, QRect(bar_x, bar_y, fill_w, bar_h),
                         _GOLD_MODE["on"] and info.get("is_max_amaterasu")):
            p.setPen(QColor(0, 0, 0, 200))
            p.drawText(text_rect.adjusted(1, 1, 1, 1), Qt.AlignmentFlag.AlignCenter, text)
            p.setPen(QColor("#ffffff"))
            p.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, text)

        p.end()



# ── Belt progress bar ────────────────────────────────────────────────────────────

class BeltBar(QWidget):
    _neon_tube = True
    """
    Shows progress through the CURRENT BELT only:
      fill = (count - belt_start) / (belt_end - belt_start)
      color = current belt color (BELT_BAR_COLORS)

    Sits below RankBar and replaces the "X cards to next belt" text label.
    The bar text reads "current / total  (N to go)" so the label is self-contained.
    The fill is centred and grows outwards in both directions.
    """

    _PAD = 28

    def __init__(self, info: dict, parent=None):
        super().__init__(parent)
        self.setFixedHeight(38)
        self.setMinimumWidth(200)
        self._apply_info(info)
        _neon_register(self)

    def _apply_info(self, info: dict):
        self._info = info
        self._pct  = info["belt_pct"]
        self.update()

    def update_info(self, info: dict):
        self._apply_info(info)

    def _glow_params(self):
        pct = self._pct
        if pct <= 0.0:
            return 0, 0, 0
        if pct >= 1.0:
            return 8, 26, 245
        t = pct ** 0.6
        layers     = 2 + int(t * 5)
        max_spread = int(3 + t * 17)
        peak_alpha = int(45 + t * 180)
        return layers, max_spread, peak_alpha

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

        w, h  = self.width(), self.height()
        pad   = self._PAD
        bar_x = pad
        bar_w = w - pad * 2
        bar_h = 22
        bar_y = (h - bar_h) // 2
        r     = 6

        fg       = self._info["belt_bar_color"]
        fg_col   = QColor(fg)
        dark_col = fg_col.darker(280)

        fill_w = max(int(bar_w * self._pct), r * 2 if self._pct > 0 else 0)
        fill_w = min(fill_w, bar_w)
        fill_x = bar_x + (bar_w - fill_w) // 2   # centred
        self._lit = (QRect(fill_x, bar_y, fill_w, bar_h), QColor(fg)) if fill_w > 0 else None

        light = _intro_light(self)
        p.setOpacity(light)                  # neon intro: no glow while off
        # ── glow ────────────────────────────────────────────────────────
        layers, max_spread, peak_alpha = self._glow_params()
        if layers > 0 and fill_w > 0:
            for i in range(1, layers + 1):
                frac   = i / layers
                spread = max(1, int(max_spread * (1.0 - frac * 0.75)))
                alpha  = min(int(peak_alpha * (frac ** 1.4)), 255)
                gx  = max(0, fill_x - spread)
                gy  = max(0, bar_y - spread)
                gx2 = min(w, fill_x + fill_w + spread)
                gy2 = min(h, bar_y + bar_h + spread)
                c = QColor(fg_col)
                c.setAlpha(alpha)
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(c)
                p.drawRoundedRect(gx, gy, gx2 - gx, gy2 - gy, r + spread, r + spread)

        p.setOpacity(1.0)
        # ── track ───────────────────────────────────────────────────────
        _paint_bar_track(p, bar_x, bar_y, bar_w, bar_h, r)

        p.setOpacity(NEON_OFF_FILL + (1 - NEON_OFF_FILL) * light)   # neon intro: unlit tube
        # ── fill ────────────────────────────────────────────────────────
        if fill_w > 0:
            grad = QLinearGradient(0, bar_y, 0, bar_y + bar_h)
            if self._pct >= 0.7:
                grad.setColorAt(0.0, fg_col.lighter(140))
                grad.setColorAt(0.5, fg_col)
                grad.setColorAt(1.0, dark_col)
            else:
                grad.setColorAt(0.0, fg_col)
                grad.setColorAt(1.0, dark_col)
            p.setBrush(grad)
            p.drawRoundedRect(fill_x, bar_y, fill_w, bar_h, r, r)

            # Sheen
            sheen = QLinearGradient(0, bar_y, 0, bar_y + bar_h // 2)
            sheen.setColorAt(0.0, QColor(255, 255, 255, 55))
            sheen.setColorAt(1.0, QColor(255, 255, 255, 0))
            p.setBrush(sheen)
            p.drawRoundedRect(fill_x, bar_y, fill_w, bar_h // 2, r, r)

        p.setOpacity(NEON_OFF_TEXT + (1 - NEON_OFF_TEXT) * light)
        # ── text ────────────────────────────────────────────────────────
        info = self._info
        if info["is_max"]:
            text = "十段 黒帯 · 極" if _GOLD_MODE["on"] else "MAX BELT"
        else:
            in_belt  = info["count"] - info["belt_start"]
            belt_sz  = info["belt_end"] - info["belt_start"]
            to_go    = info["cards_to_next"]
            text = f"{in_belt:,} / {belt_sz:,}  ({to_go:,} to go)"

        font = QFont()
        font.setBold(True)
        font.setPointSize(8)
        p.setFont(font)
        tr = QRect(bar_x, bar_y, bar_w, bar_h)
        if not _bar_text(p, tr, text, QRect(fill_x, bar_y, fill_w, bar_h),
                         _GOLD_MODE["on"] and info["is_max"]):
            p.setPen(QColor(0, 0, 0, 190))
            p.drawText(tr.adjusted(1, 1, 1, 1), Qt.AlignmentFlag.AlignCenter, text)
            p.setPen(QColor("#ffffff"))
            p.drawText(tr, Qt.AlignmentFlag.AlignCenter, text)
        p.end()


# ── Word → JLPT level lookup (for tile tooltips) ─────────────────────────────

# Frequency rank (1-based) → easiest JLPT level whose word IS that row: each
# JLPT entry maps to its best-ranked row only (word_rank, alternate
# spellings included), so a rare homograph spelled the same (なる #13,349,
# not the N5 なる #6) doesn't claim the level. Set by ProgressDialog.
_JLPT_LEVEL_OF_RANK: dict = {}


def _set_jlpt_levels(lists: dict):
    _JLPT_LEVEL_OF_RANK.clear()
    for lvl in LEVELS:
        for d, r in lists.get(lvl, []):
            rank = freq_data.word_rank(d, r, jlpt_data.alt_forms(d, r))
            if rank is not None:
                _JLPT_LEVEL_OF_RANK.setdefault(rank, lvl)


def _freq_band(rank: int) -> int | None:
    """The smallest frequency bar (6,000 / 13,800 / 20,000) a 1-based rank
    falls in, or None past 20,000."""
    for n in freq_data.BAR_TIERS + [freq_data.TIERS[-1]]:
        if rank <= n:
            return n
    return None


def _level_size(lvl: str) -> int:
    """The frequency bar a JLPT level's words are compared with: N1 its own
    size; N5–N2 the first bar, 6,000 (the 800 / 1,500 / 3,900 bars are
    gone, 2026-10-20)."""
    return {"N1": freq_data.N1_VOCAB_TARGET}.get(lvl, 6_000)


# ── Word cell ─────────────────────────────────────────────────────────────────

class WordCell(QWidget):
    """
    A single vocabulary tile.

    Visual states (mutually exclusive overrides take priority):
      suspended  → very dim, strikethrough character, dark-red border
      found      → normal bg + bright yellow border + ★ badge
      known      → level-colour gradient  (matched in deck)
      missing    → dark grey

    Interactions:
      Left-click        → open in browser (known), copy the word (missing),
                          or Jisho (marked found with no card)
      Shift+Click       → Jisho (any tile, e.g. to read a known word's full entry)
      Middle-click      → toggle marked-as-found
      Ctrl+Middle-click → toggle suspended
    """

    # Emitted so the parent dialog can refresh the Marked & Suspended tab
    override_changed = pyqtSignal()

    def __init__(self, display: str, reading: str, nid, level: str,
                 overrides: "Overrides", parent=None, overridable: bool = True,
                 rank: int = None, maturity: int = None, rank_est: bool = False,
                 new_nid=None, found_row: bool = False):
        super().__init__(parent)
        # found_row: the frequency count has this row marked found through
        # another spelling or reading (a JLPT word's mark, freq_data's loose
        # key), so it's counted and sorted as found; show it that way too
        # (owner's Top 6,000 grid 2026-10-22: がん / おお / いや drawn as
        # missing among the found tiles).
        self._found_row  = found_row
        self._display    = display
        self._reading    = reading
        self._nid        = nid
        self._level      = level   # "N5".."N1", "unlisted", or "freq"
        self._known      = nid is not None
        # Missing, but a never-studied card in the deck has it: the dashed
        # "New" tile (not counted anywhere; owner 2026-10-17).
        self._new_nid    = new_nid if nid is None else None
        self._overrides  = overrides
        self._hovered     = False
        self._highlighted = False
        self._overridable = overridable
        self._rank        = rank   # frequency rank, for "freq" tiles
        self._rank_est    = rank_est   # True: estimated (≈) compound rank
        # Readings merged into this frequency row (明日 あす: あした, みょうにち),
        # shown in the hover and matched by search.
        self._other_readings = (freq_data.merged_readings(display, reading)
                                if level == "freq" else [])
        # card_state.NEW..MATURE for known tiles; None = full colour
        # (marked-found words with no card).
        self._maturity    = maturity

        self.setFixedSize(CELL_W, CELL_H)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._refresh_tooltip()
        self.setStyleSheet("QToolTip { font-size: 18px; padding: 8px; }")

    # ── state helpers ─────────────────────────────────────────────────────────

    @property
    def _can_override(self) -> bool:
        """Found/suspend toggling is only available for words the plugin did
        NOT match in the deck. Words the plugin already counts as known
        can't be (un-)marked found (redundant) or suspended."""
        return self._overridable and not self._known

    @property
    def _is_found(self):
        if not self._overridable:
            return False
        return self._found_row or self._overrides.is_found(self._display, self._reading)

    @property
    def _is_suspended(self):
        if not self._overridable:
            return False
        return self._overrides.is_suspended(self._display, self._reading)

    def _colors(self) -> tuple:
        """(foreground, dark gradient stop) for this tile's level."""
        if self._level == "unlisted":
            return UNLISTED_FG, UNLISTED_BG
        if self._level == "freq":
            return FREQ_FG, FREQ_BG
        return LEVEL_FG.get(self._level, "#888888"), LEVEL_BG.get(self._level, "#333333")

    def glow_color(self) -> str:
        """Its section's glow in the Word Grid (_TileCanvas glow=True): its
        level's colour when known or marked found, a dim grey when missing."""
        if self._known or self._is_found:
            return self._colors()[0]
        return MISSING_GLOW

    def _known_colors(self) -> tuple:
        """(top, bottom) fill for a known tile: the frequency / Off-list
        palettes by maturity, or the level colour with its saturation scaled
        by maturity."""
        palette = STATE_COLORS.get(self._level)
        if palette is not None:
            c = QColor(palette[card_state.MATURE if self._maturity is None
                               else self._maturity])
            return c, c.darker(118)
        fg, bg = self._colors()
        if self._maturity is None:
            return QColor(fg), QColor(bg)
        k = MATURITY_SATURATION[self._maturity]
        return _scale_saturation(fg, k), _scale_saturation(bg, k)

    def _highlight_color(self) -> QColor:
        """Search-match outline: the complement (opposite hue on the colour
        wheel) of this tile's own colour, so it stands out on every tile —
        each tile computes its own, so mixed grids work too."""
        c = QColor(self._colors()[0])
        h, s, l, _ = c.getHslF()
        if h < 0:   # achromatic — no opposite hue, fall back to white
            return QColor("#ffffff")
        # Keep it vivid and bright enough to read against the dark grid —
        # the muted N5/N4 greens would otherwise give washed-out complements.
        return QColor.fromHslF((h + 0.5) % 1.0, max(s, 0.85), max(l, 0.55))

    def _refresh_tooltip(self):
        esc = html.escape
        head = f"<b>{esc(self._display)}</b>"
        if self._reading and self._reading != self._display:
            head += f"&nbsp;&nbsp;{esc('・'.join([self._reading, *self._other_readings]))}"
        # JLPT level in its colour, like the kanji/grammar tiles; frequency
        # tiles look it up so a JLPT word shows its level there too.
        lvl = self._level if self._level in LEVELS else (
            _JLPT_LEVEL_OF_RANK.get(self._rank) if self._level == "freq" else None)
        if lvl:
            head += f"&nbsp;&nbsp;<span style='color:{LEVEL_FG[lvl]};'><b>{lvl}</b></span>"
        blocks = [head]
        meaning = meanings.tooltip_html(self._display, self._reading)
        if meaning:
            blocks.append(meaning)

        info = []
        if self._rank is not None:
            info.append(f"Frequency rank {freq_data.rank_text(self._rank, self._rank_est)}"
                        + (" (estimated from compound frequency)" if self._rank_est else ""))
            # JLPT level and frequency range disagree: say why, so an N5 word
            # in the N1 range (or the reverse) doesn't look like a bug.
            band = _freq_band(self._rank)
            if lvl in LEVELS:
                size = _level_size(lvl)
                if self._rank > size:
                    info.append(f"JLPT {lvl}, but past the top {size:,} words: the "
                                "frequency list counts written Japanese, so words mostly used in "
                                "speech rank lower")
                elif band is not None and band < size:
                    info.append(f"JLPT {lvl}, but common enough in written Japanese "
                                f"for the top {band:,}")
        if self._is_suspended:
            info.append("Suspended (excluded from lists)")
        elif self._is_found:
            info.append("★ Marked as found" if self._overrides.is_found(self._display, self._reading)
                        else "★ " + FOUND_ROW_TEXT)
        elif self._known:
            info.append("In your deck — click to open in browser")
            if self._maturity is not None:
                info.append(f"Card: {MATURITY_LABELS[self._maturity]}")
        elif self._new_nid is not None:
            info.append("New — in your deck, not studied yet: it counts once you study "
                        "its card. Click to open it in the browser")
        else:
            info.append("Missing — click to copy the word")
        blocks.append("<br>".join(esc(t) for t in info))

        hints = ["Shift+Click: look up on Jisho",
                 "Ctrl+Click: search this word's text in Browser"]
        if self._can_override:
            hints.append("Middle-click: toggle marked as found")
            hints.append("Ctrl+Middle-click: toggle suspended")
        blocks.append("<span style='color:#9a9a9a; font-size:14px;'>"
                      + "<br>".join(hints) + "</span>")
        self.setToolTip("<br><br>".join(blocks))

    # ── events ────────────────────────────────────────────────────────────────

    def enterEvent(self, e):
        self._hovered = True
        _gold_hover(self)
        self.update()
    def leaveEvent(self, e):  self._hovered = False; self.update()

    # ── search support ───────────────────────────────────────────────────────

    def set_highlighted(self, val: bool):
        if self._highlighted != val:
            self._highlighted = val
            _hl_register(self, val)
            self.update()

    def matches_search(self, text: str) -> bool:
        if not text:
            return False
        t = text.strip().lower()
        return (t in self._display.lower() or t in self._reading.lower()
                or any(t in r for r in self._other_readings))

    def status_text(self) -> str:
        if self._level == "unlisted":
            lvl_label = "Off-list"
        elif self._rank is not None:
            lvl_label = f"rank {freq_data.rank_text(self._rank, self._rank_est)}"
            parent = freq_data.shared_with(self._display, self._reading)
            if parent:     # 聴く: the corpus counts it together with 聞く
                lvl_label += f" (frequency shared with {parent})"
        else:
            lvl_label = self._level
        if self._is_suspended:
            status = "✕ Suspended"
        elif self._is_found:
            status = "★ Marked as found"
        elif self._known:
            status = "✓ Known — in your deck"
        elif self._new_nid is not None:
            status = "New — in your deck, not studied yet"
        else:
            status = "Missing"
        reading_part = (
            f"  【{self._reading}】"
            if self._reading and self._reading != self._display else ""
        )
        kanji = _kanji_form(self._display, self._reading)
        if kanji:                        # usually-kana word: which one it is
            reading_part += f"  〔{kanji}〕"
        return f"{self._display}{reading_part}  —  {lvl_label}  —  {status}"

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            if not self._can_override:
                return
            mods = event.modifiers()
            if (self._found_row and not mods & Qt.KeyboardModifier.ControlModifier
                    and not self._overrides.is_found(self._display, self._reading)):
                pos = (event.globalPosition().toPoint() if hasattr(event, "globalPosition")
                       else event.globalPos())          # Qt5 builds of Anki
                QToolTip.showText(pos, FOUND_ROW_TEXT, self)
                return
            if mods & Qt.KeyboardModifier.ControlModifier:
                self._overrides.toggle_suspended(self._display, self._reading)
            else:
                self._overrides.toggle_found(self._display, self._reading)
            self._refresh_tooltip()
            self.update()
            self.override_changed.emit()

        elif event.button() == Qt.MouseButton.LeftButton:
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                # Any tile, known ones included: the hover only fits the
                # first meanings.
                _open_jisho(self._display, self._reading)
            elif event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                _search_term_in_browser(self._display, self._reading)
            elif self._known or self._is_found:
                if self._nid is not None:
                    _open_in_browser(self._nid)
                else:
                    _open_jisho(self._display, self._reading)
            elif self._new_nid is not None:
                _open_in_browser(self._new_nid)
            else:
                _copy_word(self._display, self.window())

    # ── painting ──────────────────────────────────────────────────────────────

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = h = CELL_W

        suspended  = self._is_suspended
        found      = self._is_found
        known      = self._known
        hov        = self._hovered

        # Amaterasu gold mode: known / found word tiles turn gold with dark
        # bronze text (owner: "all gold with golden text", but readable).
        # Maturity still shows as how deep the gold is.
        gold_tile = _GOLD_MODE["on"] and (known or found) and not suspended

        # ── background & border ───────────────────────────────────────────────
        if suspended:
            p.setBrush(QColor("#1a1a1a"))
            p.setPen(QPen(QColor("#5a1a1a"), 1.5))
        elif gold_tile:
            top, bottom = _GOLD_TILE.get(self._maturity if known and not found else None,
                                         _GOLD_TILE[None])
            grad = QLinearGradient(0, 0, 0, h)
            grad.setColorAt(0, QColor(top))
            grad.setColorAt(1, QColor(bottom))
            p.setBrush(grad)
            p.setPen(QPen(QColor("#fffbe6" if hov else "#fff2b8"), 1.5))
        elif found:
            # use the level colour but add a gold border
            fg, bg_d = self._colors()
            grad = QLinearGradient(0, 0, 0, h)
            grad.setColorAt(0, QColor(fg))
            grad.setColorAt(1, QColor(bg_d))
            p.setBrush(grad)
            border_col = "#ffe066" if not hov else "#fff176"
            p.setPen(QPen(QColor(border_col), 2.5))
        elif known:
            fg, bg_d = self._known_colors()
            grad = QLinearGradient(0, 0, 0, h)
            grad.setColorAt(0, fg)
            grad.setColorAt(1, bg_d)
            p.setBrush(grad)
            # Navy Off-list tiles need a lighter edge to stand off the dark UI.
            edge = QColor(UNLISTED_FG) if self._level == "unlisted" else fg
            border = edge.lighter(140) if hov else edge
            p.setPen(QPen(border, 1.5))
        elif self._new_nid is not None:
            _paint_in_deck(p, hov, QColor(self._colors()[0]))
        else:
            p.setBrush(QColor("#333333") if hov else QColor("#252525"))
            p.setPen(QPen(QColor("#666"), 1.0))

        p.drawRoundedRect(1, 1, w - 2, h - 2, CELL_R, CELL_R)

        # ── character ─────────────────────────────────────────────────────────
        # The first two characters at equal size, so tiles like 大人 / 大学 /
        # 大切 can be told apart at a glance; one-character words stay large.
        label = self._display[:2] if self._display else "?"

        if suspended:
            text_col = QColor("#4a4a4a")
        elif gold_tile:
            text_col = QColor("#3b2600")    # dark bronze: 6.3–12.9 : 1 on every gold
        elif (known and self._level == "freq"
              and self._maturity in (card_state.NEW, card_state.LEARNING,
                                     card_state.YOUNG)):
            # Pale young (incl. learning) frequency tiles get a dark blue
            # text (a little lighter than the earlier #0d3550); mature
            # frequency tiles, like JLPT and Off-list tiles, use white text
            # (owner's choice).
            text_col = QColor("#1f4f70")
        elif found or known:
            text_col = QColor("#ffffff")
        elif _GOLD_MODE["on"]:
            text_col = QColor(MISSING_GOLD)   # missing tiles: muted gold text
        else:
            # Not-found tiles: tint the character with this word's level
            # colour (background stays the same dark "missing" shade).
            text_col = QColor(self._colors()[0])

        f1 = QFont(); f1.setPointSize(14 if len(label) == 1 else 10); f1.setBold(True)
        if suspended:
            f1.setStrikeOut(True)
        p.setFont(f1)
        if gold_tile:
            # a soft light edge under the bronze, like engraved gold
            p.setPen(QColor(255, 250, 220, 150))
            p.drawText(QRect(0, 1, w, h), Qt.AlignmentFlag.AlignCenter, label)
        p.setPen(text_col)
        p.drawText(QRect(0, 0, w, h), Qt.AlignmentFlag.AlignCenter, label)

        # ── ★ badge for found ─────────────────────────────────────────────────
        if found:
            f2 = QFont(); f2.setPointSize(7); f2.setBold(True)
            p.setFont(f2)
            p.setPen(QColor("#8a5a00" if gold_tile else "#ffe066"))
            p.drawText(QRect(w - 13, 2, 11, 11), Qt.AlignmentFlag.AlignCenter, "★")

        # ── ✕ badge for suspended ─────────────────────────────────────────────
        if suspended:
            f3 = QFont(); f3.setPointSize(7); f3.setBold(True)
            p.setFont(f3)
            p.setPen(QColor("#8b2020"))
            p.drawText(QRect(w - 13, 2, 11, 11), Qt.AlignmentFlag.AlignCenter, "✕")

        # ── search-match highlight ────────────────────────────────────────────
        if self._highlighted and _GOLD_MODE["on"]:
            _paint_gold_highlight(p, w, h)
        elif self._highlighted:
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(self._highlight_color(), 3))
            p.drawRoundedRect(1, 1, w - 2, h - 2, CELL_R, CELL_R)

        p.end()


# ── Tile canvas ───────────────────────────────────────────────────────────────

class _NeonZone(QWidget):
    """A few rows of a grid as one neon element (owner 2026-10-22: "make the
    tile light up as you can see them, right now the whole grid"): it waits
    until it's on screen, then flickers on with its own pattern; while
    unlit it veils its tiles (theme.BG_BOTTOM, 25 % showing) and its part
    of the grid's glow is dark. `rows`: [(y, x0, x1, first tile, end)]."""

    _OFF = 0.25

    def __init__(self, canvas, rows, color, first: bool, last: bool):
        super().__init__(canvas)
        self._canvas = canvas
        self._neon_canvas = canvas           # _on_screen: measured through the grid
        self.color = color
        self.tiles = (rows[0][3], rows[-1][4])
        y0, y1 = rows[0][0], rows[-1][0] + CELL_H + (0 if last else CELL_GAP)
        # Its band of the glow: its rows' top to the next zone's; open-ended
        # at the grid's own top and bottom.
        self.band = (-1e6 if first else y0, 1e6 if last else y1)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setGeometry(0, y0, canvas.width(), y1 - y0)
        self._lit = (QRect(0, 0, canvas.width(), y1 - y0), QColor(color), 0.45)
        self._veil = QPainterPath()
        self._veil.setFillRule(Qt.FillRule.WindingFill)
        for y, x0, x1, _a, _b in rows:
            self._veil.addRoundedRect(QRectF(x0, y - y0, x1 - x0, CELL_H), CELL_R, CELL_R)
        # Glow layers: its rows, stretched past the band's inner edges so
        # the glow runs straight on into the next zone (the band clips it).
        ext = 40
        self.layers = []
        for spread, alpha in _TileCanvas._GLOW:
            path = QPainterPath()
            path.setFillRule(Qt.FillRule.WindingFill)
            for i, (y, x0, x1, _a, _b) in enumerate(rows):
                top = y - (ext if (i == 0 and not first) else 0)
                bot = y + CELL_H + (CELL_GAP if i < len(rows) - 1 else (0 if last else ext))
                path.addRoundedRect(QRectF(x0 - spread, top - spread, x1 - x0 + 2 * spread,
                                           bot - top + 2 * spread), CELL_R + spread, CELL_R + spread)
            self.layers.append((path.simplified(), alpha))

    def _neon_refresh(self):
        lit = _intro_light(self) >= 1.0
        self.setVisible(not lit)
        if not lit:
            self.raise_()
            self.update()
        g = self.geometry()
        self._canvas.update(QRect(0, g.top() - 20, self._canvas.width(), g.height() + 40))

    def paintEvent(self, event):
        a = 1.0 - (self._OFF + (1.0 - self._OFF) * _intro_light(self))
        if a <= 0:
            return
        from . import theme
        c = QColor(theme.BG_BOTTOM)
        c.setAlphaF(min(1.0, a))
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(c)
        p.drawPath(self._veil)
        p.end()


class _TileCanvas(QWidget):
    """A grid's tiles, flowed in rows. With `glow`, the shape all the tiles
    make together glows like the bars (owner 2026-10-22: "not each
    individual tile but the shape that all the tiles together make", so
    the small words stay readable): drawn under the tiles, only outside
    the shape. glow=True: each section in its tiles' colour (glow_color(),
    the N5 … N1 / frequency / missing runs of the Word Grid); "blend": each
    row in its tiles' average colour (the kanji / grammar heatmaps); a
    colour string: one colour. The rows are split into _NeonZone pieces that
    flicker on as they come into view."""

    # (spread px, alpha) from the faint outside in; the pad leaves it room
    _GLOW = ((13, 14), (10, 24), (7, 38), (4, 60), (2, 95))
    _GLOW_PAD = 15
    ZONE_ROWS = 3                    # rows per zone at most

    def __init__(self, cells: list, parent=None, glow=None):
        super().__init__(parent)
        self._cells = cells
        self._glow = glow
        self._pad = self._GLOW_PAD if glow else 8
        self._rows = []              # [y, x0, x1, first tile, end] per row
        self._zones = []
        self._outside = None         # cached: everything but the tiles' shape
        self._lit = set()            # tiles whose zone has lit (kept over a re-flow)
        self._quiet = bool(_NEON["quiet"])     # built by a refresh (_neon_quiet)
        for c in cells:
            c.setParent(self)
            c.show()
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

    def _reflow(self, available_width: int):
        if not self._cells:
            return 0
        pad   = self._pad
        x     = pad
        y     = pad
        max_x = available_width - pad
        rows  = []
        for i, cell in enumerate(self._cells):
            # Word and kanji tiles are CELL_W wide; grammar tiles are wider.
            cw = cell.width()
            if x + cw > max_x and x > pad:
                x  = pad
                y += CELL_H + CELL_GAP
            cell.move(x, y)
            if not rows or rows[-1][0] != y:
                rows.append([y, x, x + cw, i, i + 1])
            else:
                rows[-1][2] = x + cw
                rows[-1][4] = i + 1
            x += cw + CELL_GAP
        self._rows = rows
        return y + CELL_H + pad

    def _tile_color(self, cell) -> str:
        if self._glow is True or self._glow == "blend":
            fn = getattr(cell, "glow_color", None)
            return fn() if fn is not None else "#888888"
        return self._glow

    def _rebuild_zones(self):
        """New zones for the current rows (a width change re-flows them):
        a zone whose tiles have all lit before starts lit."""
        for z in self._zones:
            z._neon_state = "lit"
            z.hide()
            z.deleteLater()
        self._zones, self._outside, self._inside_rows = [], None, None
        if not self._glow or not self._rows:
            return
        # A row's colour = its tiles' most common; a zone = up to ZONE_ROWS
        # rows of one colour.
        # glow="blend" (the kanji / grammar heatmaps): a row's colour = the
        # average of its tiles', so the glow follows the grid's gradient.
        from collections import Counter
        groups = []
        for row in self._rows:
            cols = [self._tile_color(self._cells[i]) for i in range(row[3], row[4])]
            if self._glow == "blend":
                qs = [QColor(c) for c in cols]
                col = QColor(sum(q.red() for q in qs) // len(qs),
                             sum(q.green() for q in qs) // len(qs),
                             sum(q.blue() for q in qs) // len(qs)).name()
            else:
                col = Counter(cols).most_common(1)[0][0]
            if groups and groups[-1][0] == col and len(groups[-1][1]) < self.ZONE_ROWS:
                groups[-1][1].append(row)
            else:
                groups.append((col, [row]))
        for k, (col, rows) in enumerate(groups):
            z = _NeonZone(self, rows, col, k == 0, k == len(groups) - 1)
            done = all(i in self._lit for i in range(*z.tiles))
            _neon_register(z, "lit" if done else ("quiet" if self._quiet else None))
            z._neon_lit_cb = (lambda zz=z: self._lit.update(range(*zz.tiles)))
            self._zones.append(z)
            z._neon_refresh()
        self._quiet = False          # a later re-flow is the same grid, already built

    def _outside_path(self):
        if self._outside is None:
            shape = QPainterPath()
            shape.setFillRule(Qt.FillRule.WindingFill)
            for k, (y, x0, x1, _a, _b) in enumerate(self._rows):
                gap = CELL_GAP if k < len(self._rows) - 1 else 0
                shape.addRoundedRect(QRectF(x0, y, x1 - x0, CELL_H + gap), CELL_R, CELL_R)
            outside = QPainterPath()
            outside.addRect(QRectF(self.rect()).adjusted(-50, -50, 50, 50))
            self._outside = outside.subtracted(shape.simplified())
        return self._outside

    def _inside(self) -> QRegion:
        """The tiles' rows as a region: no glow is drawn in there."""
        if getattr(self, "_inside_rows", None) is None:
            reg = QRegion()
            for k, (y, x0, x1, _a, _b) in enumerate(self._rows):
                gap = CELL_GAP if k < len(self._rows) - 1 else 0
                reg += QRect(x0 + CELL_R, y, max(0, x1 - x0 - 2 * CELL_R), CELL_H + gap)
            self._inside_rows = reg
        return self._inside_rows

    def paintEvent(self, event):
        if not self._zones:
            return
        # A repaint well inside the tiles (the rain's drops, a hovered tile)
        # has no glow in it: skip the glow's costly clipping.
        if event.region().subtracted(self._inside()).isEmpty():
            return
        gold = _GOLD_MODE["on"]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        outside = self._outside_path()
        er = QRectF(event.rect())
        for z in self._zones:
            top, bot = z.band
            t, b = max(top, er.top() - 1), min(bot, er.bottom() + 1)
            if b <= t:
                continue
            light = _intro_light(z)
            if light <= 0:
                continue
            col = QColor(rank_data.RANK_COLORS["Amaterasu"][1] if gold else z.color)
            p.save()
            p.setClipRect(QRectF(er.left(), t, er.width(), b - t))
            p.setClipPath(outside, Qt.ClipOperation.IntersectClip)
            for path, alpha in z.layers:
                c = QColor(col)
                c.setAlpha(int(alpha * light))
                p.setBrush(c)
                p.drawPath(path)
            p.restore()
        p.end()

    def resizeEvent(self, event):
        old = [r[:] for r in self._rows]
        h = self._reflow(event.size().width())
        self.setMinimumHeight(h)
        if self._rows != old or not self._zones or event.size().width() != event.oldSize().width():
            self._rebuild_zones()
        super().resizeEvent(event)

    def sizeHint(self):
        w = self.width() if self.width() > 0 else 800
        h = self._reflow(w)
        return QSize(w, h)


def _maturity_legend(palette: str = None) -> QLabel:
    """Legend for the known-tile colour by card maturity: the JLPT
    saturation scale (sampled on the N3 orange), or a STATE_COLORS palette
    ("freq" / "unlisted")."""
    lbl = QLabel(_maturity_legend_html(palette))
    lbl.setStyleSheet(HINT_CSS)
    # divine_text swaps in the gold version (the tiles' gold depths)
    lbl.setProperty("jlpt_maturity_legend", palette or "")
    return lbl


def _maturity_legend_html(palette: str = None, gold: bool = False) -> str:
    parts = []
    for state in (card_state.YOUNG, card_state.MATURE):
        if gold:
            c = _GOLD_TILE[state][1]
        elif palette:
            c = STATE_COLORS[palette][state]
        else:
            c = _scale_saturation(LEVEL_FG["N3"], MATURITY_SATURATION[state]).name()
        parts.append(f"<span style='color:{c}'>■</span> {MATURITY_LABELS[state]}")
    if palette != "unlisted":        # Off-list tiles are all studied cards
        parts.append("<span style='color:#9a9a9a'>⬚</span> New (in your deck, not studied yet)")
    intro = {
        None:       "Known tiles get more vivid as cards mature:  ",
        "freq":     "Known tiles by card maturity:  ",
        "unlisted": "Off-list tiles by card maturity:  ",
    }[palette]
    return intro + "  ".join(parts)


# ── Section header ────────────────────────────────────────────────────────────

def _make_section_header(lvl: str, known: int, total: int) -> QWidget:
    w    = QWidget()
    w.setProperty("jlpt_sticky", True)      # pinned while scrolling its section
    vbox = QVBoxLayout(w)
    vbox.setContentsMargins(0, 4, 0, 0)
    vbox.setSpacing(2)
    miss = total - known
    hdr  = QLabel(
        f"<span style='color:{LEVEL_FG[lvl]}; font-size:16px; font-weight:bold;'>{lvl}</span>"
        f"<span style='color:#aaa; font-size:13px;'>"
        f"  {known:,} / {total:,} known  ({jlpt_data.format_pct(known, total)}) — {miss:,} missing</span>"
    )
    vbox.addWidget(hdr)
    leg = QHBoxLayout()
    lk  = QLabel(f"<span style='color:{LEVEL_FG[lvl]}'>■</span> Known ({known}) — click to open in browser")
    lk.setStyleSheet(BODY_CSS)
    lm  = QLabel(f"<span style='color:#555'>■</span> Missing ({miss}) — click to copy")
    lm.setStyleSheet(BODY_CSS)
    leg.addWidget(lk); leg.addWidget(lm); leg.addStretch()
    vbox.addLayout(leg)
    return w


# ── Grid panel ────────────────────────────────────────────────────────────────

class WordGridPanel(QWidget):
    """
    flat=True  → one unbroken tile canvas (all levels mixed).
    flat=False → per-level sections with header.
    overrides  → shared Overrides instance so middle-click saves correctly.
    on_override_changed → callable invoked after any cell override toggles.
    """

    def __init__(self, results: dict, level: str, overrides: Overrides,
                 flat: bool = False, on_override_changed=None, parent=None,
                 freq_limit: int = None):
        super().__init__(parent)
        self._results             = results
        self._level               = level   # "N5".."N1", "All", or "freq"
        self._freq_limit          = freq_limit   # "freq": show ranks 1..freq_limit
        self._flat                = flat
        self._overrides           = overrides
        self._on_override_changed = on_override_changed
        self._build()

    def update_results(self, results: dict):
        """Rebuild the panel (headers/counts) with freshly computed results."""
        self._results = results
        for child in self.findChildren(QWidget):
            child.hide()
            child.deleteLater()
        old_layout = self.layout()
        if old_layout is not None:
            while old_layout.count():
                old_layout.takeAt(0)
            QWidget().setLayout(old_layout)
        self._build()

    def _new_words(self) -> dict:
        """(display, reading) → nid of a never-studied card with that word."""
        return (self._results.get("new_cards") or {}).get("words") or {}

    def _split_new(self, missing) -> tuple[list, list]:
        """Missing words → (in a new card, not in the deck): New tiles go
        right after the known ones."""
        new = self._new_words()
        return ([m for m in missing if tuple(m) in new],
                [m for m in missing if tuple(m) not in new])

    def _make_cell(self, display, reading, nid, level, rank=None):
        cell = WordCell(display, reading, nid, level, self._overrides, rank=rank,
                        maturity=self._results.get("maturity", {}).get(nid),
                        new_nid=self._new_words().get((display, reading)) if nid is None else None)
        if self._on_override_changed:
            cell.override_changed.connect(self._on_override_changed)
        return cell

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Search bar ───────────────────────────────────────────────────────
        search_row = QHBoxLayout()
        search_row.setContentsMargins(8, 8, 8, 4)
        search_row.setSpacing(6)
        search_icon = QLabel("🔍")
        search_row.addWidget(search_icon)
        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("Find a word in this grid (kanji or kana)…")
        self._search_edit.setClearButtonEnabled(True)
        # Fixed width so the status text beside it can't squeeze it.
        self._search_edit.setMinimumWidth(300)
        self._search_edit.setMaximumWidth(300)
        search_row.addWidget(self._search_edit)
        self._search_status = QLabel("")
        self._search_status.setStyleSheet(HINT_CSS)
        self._search_status.setWordWrap(True)
        search_row.addWidget(self._search_status, 1)
        outer.addLayout(search_row)

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

        levels_to_show = LEVELS if self._level == "All" else [self._level]

        if self._level == "freq":
            self._build_freq_sections(vbox)

        elif self._flat:
            leg = QHBoxLayout()
            for lvl in LEVELS:
                lbl = QLabel(f"<span style='color:{LEVEL_FG[lvl]}'>■</span> {lvl}")
                lbl.setStyleSheet(BODY_CSS)
                leg.addWidget(lbl)
            lm = QLabel("<span style='color:#555'>■</span> Missing JLPT")
            lm.setStyleSheet(BODY_CSS)
            leg.addWidget(lm)
            lf = QLabel("<span style='color:#ffe066'>★</span> Marked found")
            lf.setStyleSheet(BODY_CSS)
            leg.addWidget(lf)
            ls = QLabel("<span style='color:#e05a5a'>✕</span> Suspended")
            ls.setStyleSheet(BODY_CSS)
            leg.addWidget(ls)
            leg.addStretch()
            vbox.addLayout(leg)

            hint = QLabel(
                "Hover: meaning  ·  Shift+Click: Jisho  ·  "
                "Middle-click: mark as found  ·  Ctrl+Middle-click: suspend (exclude from list)"
            )
            hint.setStyleSheet(HINT_CSS)
            vbox.addWidget(hint)
            order = QLabel(
                f"Known words are shown level by level; within each level they're grouped "
                f"{GROUPING_TEXT} (★ marked found last), most common first in each group. "
                "New words (dashed: in your deck, not studied yet), then missing words, follow."
            )
            order.setWordWrap(True)
            order.setStyleSheet(HINT_CSS)
            vbox.addWidget(order)
            vbox.addWidget(_maturity_legend())

            tk  = sum(len(self._results[l]["known_words"])   for l in LEVELS)
            tm  = sum(len(self._results[l]["missing_words"]) for l in LEVELS)
            ta  = tk + tm
            vbox.addWidget(QLabel(
                f"<span style='color:#aaa; font-size:13px;'>"
                f"{tk:,} / {ta:,} known across all levels  ({jlpt_data.format_pct(tk, ta)})</span>"
            ))

            # JLPT grid: known words by level, each level grouped by maturity
            # (most common first inside each group), then missing words.
            maturity = self._results.get("maturity", {})
            known_all = [(lvl_i, lvl, disp, read, nid)
                         for lvl_i, lvl in enumerate(LEVELS)
                         for disp, read, nid in self._results[lvl]["known_words"]]
            known_all.sort(key=lambda k: (k[0], maturity_group(maturity, k[4]),
                                          _jlpt_rank(k[2], k[3])))
            cells = []
            for _, lvl, disp, read, nid in known_all:
                cells.append(self._make_cell(disp, read, nid, lvl))
            # New (in a never-studied card) next, then missing, each by level.
            split = {lvl: self._split_new(self._results[lvl]["missing_words"]) for lvl in LEVELS}
            for part in (0, 1):
                for lvl in LEVELS:
                    for disp, read in split[lvl][part]:
                        cells.append(self._make_cell(disp, read, None, lvl))
            self._all_cells.extend(cells)
            vbox.addWidget(_TileCanvas(cells, glow=True))      # each level's run in its colour
            # (Off-list deck cards are shown in their own tab, not here.)

        else:
            order = QLabel(
                f"Known words are grouped {GROUPING_TEXT} (★ marked found last), "
                "most common first in each group. New words (dashed: in your deck, not studied yet), "
                "then missing words, follow."
            )
            # Wrapped: unwrapped, its width pushed the tiles past the grid
            # window's right edge (owner 2026-10-22).
            order.setWordWrap(True)
            order.setStyleSheet(HINT_CSS)
            vbox.addWidget(order)
            vbox.addWidget(_maturity_legend())
            maturity = self._results.get("maturity", {})
            for lvl in levels_to_show:
                d       = self._results[lvl]
                known   = sorted(d["known_words"],
                                 key=lambda k: (maturity_group(maturity, k[2]),
                                                _jlpt_rank(k[0], k[1])))
                missing = d["missing_words"]
                vbox.addWidget(_make_section_header(lvl, len(known), len(known) + len(missing)))

                cells = []
                for disp, read, nid in known:
                    cells.append(self._make_cell(disp, read, nid, lvl))
                new, rest = self._split_new(missing)
                for disp, read in new + rest:
                    cells.append(self._make_cell(disp, read, None, lvl))
                self._all_cells.extend(cells)
                vbox.addWidget(_TileCanvas(cells, glow=True))

        vbox.addStretch()
        scroll.setWidget(container)
        outer.addWidget(scroll)
        self._install_sticky(scroll)
        # Gold mode: an occasional light sheen over the whole grid page
        # (idle otherwise). Created last, so it sits above everything.
        self._sheen = GridSheen(self)

        self._search_edit.textChanged.connect(self._on_search_changed)
        self._search_edit.returnPressed.connect(self._on_search_next)
        # Prevent Enter from propagating to the QDialog and triggering Accept/close
        self._search_edit.installEventFilter(self)

    def _build_freq_sections(self, vbox: QVBoxLayout):
        """Frequency grid: ranks 1..freq_limit in rank order, split into the
        same bands as the Frequency Check bars (N5 #1–800, N4 #801–1,500 …).
        Found/suspended marks apply here too (shared with the JLPT lists):
        found words count as known (★), suspended words are left out after a
        Refresh, as in the JLPT grids."""
        freq = self._results.get("frequency") or {}
        entries = freq.get("entries", [])
        entries = entries[:self._freq_limit] if self._freq_limit else entries
        found = freq.get("found_ranks", set())
        suspended = freq.get("suspended_ranks", set())
        # rank → nid of a never-studied card with that word (New tiles)
        new_ranks = (self._results.get("new_cards") or {}).get("ranks") or {}

        def is_known(e):
            return e[3] is not None or (e[0] - 1) in found

        leg = QHBoxLayout()
        for text in (f"<span style='color:{FREQ_FG}'>■</span> In your deck — click to open in browser",
                     "<span style='color:#555'>■</span> Missing — click to copy",
                     "<span style='color:#ffe066'>★</span> Marked found",
                     "<span style='color:#e05a5a'>✕</span> Suspended"):
            lbl = QLabel(text)
            lbl.setStyleSheet(BODY_CSS)
            leg.addWidget(lbl)
        leg.addStretch()
        vbox.addLayout(leg)
        hint = QLabel(f"Known words first, grouped {GROUPING_TEXT} (★ marked found last), "
                      "most common first in each group; then new words (dashed) and missing words in frequency order. "
                      "Hover: meaning and rank  ·  Shift+Click: Jisho  ·  "
                      "Middle-click: mark as found  ·  Ctrl+Middle-click: suspend (left out of "
                      "the counts). Marks are shared with the JLPT lists; Refresh updates the bars.")
        hint.setWordWrap(True)
        hint.setStyleSheet(HINT_CSS)
        vbox.addWidget(hint)
        vbox.addWidget(_maturity_legend("freq"))

        start = 0
        for end in freq_data.BAR_TIERS + [freq_data.TIERS[-1]]:      # bands = the bars
            raw = entries[start:end]
            if not raw:
                break
            band = [e for e in raw if (e[0] - 1) not in suspended]
            n_susp = len(raw) - len(band)
            known = sum(1 for e in band if is_known(e))
            name = freq_data.TIER_NAMES.get(end, "")
            hdr = QLabel(
                f"<span style='color:{FREQ_FG}; font-size:16px; font-weight:bold;'>"
                f"{name + ' · ' if name else ''}#{start + 1:,} – {start + len(raw):,}</span>"
                f"<span style='color:#aaa; font-size:13px;'>"
                f"  {known:,} / {len(band):,} known  ({jlpt_data.format_pct(known, len(band))})"
                f" — {len(band) - known:,} missing"
                + (f" · {n_susp:,} suspended" if n_susp else "") + "</span>"
            )
            hdr.setContentsMargins(0, 4, 0, 0)
            hdr.setProperty("jlpt_sticky", True)
            vbox.addWidget(hdr)
            # Known words first, grouped by maturity (rank order inside each
            # group; marked found last), then missing words in rank order.
            maturity = self._results.get("maturity", {})
            ordered = (sorted((e for e in band if is_known(e)),
                              key=lambda e: (maturity_group(maturity, e[3]), e[0]))
                       + [e for e in band if not is_known(e) and e[0] in new_ranks]
                       + [e for e in band if not is_known(e) and e[0] not in new_ranks])
            cells = [
                WordCell(display, reading, nid, "freq", self._overrides,
                         rank=rank, maturity=maturity.get(nid),
                         new_nid=None if nid is not None else new_ranks.get(rank),
                         found_row=nid is None and (rank - 1) in found)
                for rank, display, reading, nid in ordered
            ]
            if self._on_override_changed:
                for c in cells:
                    c.override_changed.connect(self._on_override_changed)
            self._all_cells.extend(cells)
            vbox.addWidget(_TileCanvas(cells, glow=True))
            start = end

    # ── pinned section header (owner 2026-10-18) ──────────────────────────
    # While scrolling, the header of the section you're in (N3, N3 Kanji,
    # a frequency band …) stays pinned at the top of the grid. Headers are
    # the widgets with the "jlpt_sticky" property.

    def _install_sticky(self, scroll):
        self._sticky_scroll = scroll
        self._pin = QLabel(scroll.viewport())
        self._pin.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._pin.hide()
        scroll.verticalScrollBar().valueChanged.connect(self._update_sticky)

    def _update_sticky(self, value: int):
        try:
            scroll = self._sticky_scroll
            container = scroll.widget()
            heads = [w for w in container.findChildren(QWidget) if w.property("jlpt_sticky")]
        except (AttributeError, RuntimeError):
            return
        current = None
        for w in heads:
            y = w.mapTo(container, QPoint(0, 0)).y()
            if y < value - 2:
                if current is None or y > current[0]:
                    current = (y, w)
        if current is None:
            self._pin.hide()
            return
        w = current[1]
        lbl = w if isinstance(w, QLabel) else (w.findChildren(QLabel) or [None])[0]
        if lbl is None:
            self._pin.hide()
            return
        bg = "#14110a" if _GOLD_MODE["on"] else "#171717"
        self._pin.setStyleSheet(f"background: {bg}; border-bottom: 1px solid #333333;"
                                " padding: 6px 10px;")
        self._pin.setText(lbl.text())
        self._pin.setGeometry(0, 0, scroll.viewport().width(), self._pin.sizeHint().height())
        self._pin.show()
        self._pin.raise_()

    def eventFilter(self, obj, event):
        if obj is self._search_edit and event.type() == QEvent.Type.KeyPress:
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                self._on_search_next()
                return True   # consume — don't let the dialog see it
        return super().eventFilter(obj, event)

    def _on_search_next(self):
        """Cycle to the next search match on Enter key."""
        text = self._search_edit.text().strip()
        if not text:
            return
        matches = [c for c in self._all_cells if c.matches_search(text)]
        if not matches:
            return
        # Find which match is currently visible in the viewport, advance by 1
        if not hasattr(self, "_search_match_idx"):
            self._search_match_idx = 0
        else:
            self._search_match_idx = (self._search_match_idx + 1) % len(matches)
        target = matches[self._search_match_idx]
        self._scroll.ensureWidgetVisible(target, 60, 100)
        n = len(matches)
        self._set_status(f"Match {self._search_match_idx + 1} / {n}: {target.status_text()}")

    def _set_status(self, text: str):
        """Search status line (re-gilded in gold mode: it's rewritten after
        the gold pass)."""
        self._search_status.setText(text)
        _regold(self._search_status)

    def _on_search_changed(self, text: str):
        self._search_match_idx = 0
        text = text.strip()
        matches = []
        for cell in self._all_cells:
            is_match = cell.matches_search(text)
            cell.set_highlighted(is_match)
            if is_match:
                matches.append(cell)

        if not text:
            self._set_status("")
            return

        if not matches:
            self._set_status("No matches found.")
            return

        first = matches[0]
        if len(matches) == 1:
            self._set_status(first.status_text())
        else:
            self._set_status(f"{len(matches)} matches — first: {first.status_text()}")

        self._scroll.ensureWidgetVisible(first, 60, 100)


# ── Missing words table ───────────────────────────────────────────────────────

def _meaning_tip(display: str, reading: str) -> str:
    """Hover text for a table row or chip: the word, its reading and its
    meaning, or "" when there's no meaning."""
    meaning = meanings.tooltip_html(display, reading)
    if not meaning:
        return ""
    head = f"<b>{html.escape(display)}</b>"
    if reading and reading != display:
        head += f"&nbsp;&nbsp;{html.escape(reading)}"
    return f"{head}<br>{meaning}"


def _has_kanji(s: str) -> bool:
    return any(0x3400 <= ord(c) <= 0x9FFF or 0xF900 <= ord(c) <= 0xFAFF or ord(c) in (0x3005, 0x3006)
               for c in s)


def _shown_reading(display: str, reading: str) -> str:
    """Reading column text: blank for a word written without kanji (テレビ,
    ある), where the reading only repeats the word."""
    if not _has_kanji(display):
        return ""
    return reading


_freq_kana_forms = None   # kana headword → that frequency row's spellings


def _kanji_form(display: str, reading: str = "") -> str:
    """A kana-written word's usual kanji spelling (かく → 掻く), or "".
    From its own JLPT entry, else the frequency row headed by exactly this
    kana — never by spelling alone, which would turn かく into 書く (the 書く
    row lists かく too). Owner 2026-10-12: Jisho searches for かく put 書く
    first, so you had to guess which かく a missing word was."""
    global _freq_kana_forms
    if not display or _has_kanji(display):
        return ""
    for f in jlpt_data.alt_forms(display, reading or display):
        if _has_kanji(f):
            return f
    if _freq_kana_forms is None:
        _freq_kana_forms = {}
        for d, _r, _p, forms in freq_data.load():
            if not _has_kanji(d):
                _freq_kana_forms.setdefault(d, forms)
    for f in _freq_kana_forms.get(display, ()):
        if _has_kanji(f):
            return f
    return ""


def _fill_table(table: QTableWidget, rows: list, tooltips: list = None):
    """Fill a QTableWidget with rows of (text, colour or None) cells, left-aligned.
    tooltips (optional): one hover text per row, shown on every cell.

    Thousands of setItem calls on a visible table are very slow while any
    column auto-fits its contents (Qt re-measures the column after every
    cell), which can freeze Anki. So repaints and auto-fitting are paused
    during the fill, and the auto-fit columns are measured once at the end.
    """
    header = table.horizontalHeader()
    auto = [c for c in range(table.columnCount())
            if header.sectionResizeMode(c) == QHeaderView.ResizeMode.ResizeToContents]
    table.setUpdatesEnabled(False)
    for c in auto:
        header.setSectionResizeMode(c, QHeaderView.ResizeMode.Interactive)
    try:
        left = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        table.setRowCount(0)          # drop old items in one go
        table.setRowCount(len(rows))
        for i, cells in enumerate(rows):
            for col, (text, color) in enumerate(cells):
                item = QTableWidgetItem(text)
                item.setTextAlignment(left)
                if color:
                    item.setForeground(QColor(color))
                    _gold_item(item)
                if tooltips and tooltips[i]:
                    item.setToolTip(tooltips[i])
                table.setItem(i, col, item)
    finally:
        for c in auto:
            table.resizeColumnToContents(c)
            header.setSectionResizeMode(c, QHeaderView.ResizeMode.ResizeToContents)
        table.setUpdatesEnabled(True)


class MissingWordsPanel(QWidget):
    def __init__(self, results: dict, parent=None):
        super().__init__(parent)
        self._results = results
        self._build()

    def update_results(self, results: dict):
        """Rebuild the panel with freshly computed results (e.g. after a word
        is suspended, it should disappear from the missing-words list)."""
        self._results = results
        self._ranked  = None   # recompute frequency ranks for the new results
        for child in self.findChildren(QWidget):
            child.hide()
            child.deleteLater()
        old_layout = self.layout()
        if old_layout is not None:
            while old_layout.count():
                old_layout.takeAt(0)
            QWidget().setLayout(old_layout)
        self._build()

    def _build(self):
        outer = QVBoxLayout(self)
        ctrl  = QHBoxLayout()
        ctrl.addWidget(QLabel("Level:"))
        self._level_combo = QComboBox()
        self._level_combo.addItem("All levels", "All")
        for lvl in LEVELS:
            n = len(self._results[lvl]["missing_words"])
            self._level_combo.addItem(f"{lvl}  ({n} missing)", lvl)
        ctrl.addWidget(self._level_combo)
        ctrl.addSpacing(16)
        ctrl.addWidget(QLabel("Sort:"))
        self._sort_combo = QComboBox()
        self._sort_combo.addItem("Most common first", "freq")
        self._sort_combo.addItem("By level", "level")
        self._sort_combo.setToolTip(
            "Most common first: sorted by frequency rank in written Japanese (BCCWJ),\n"
            "so the words worth learning next are at the top."
        )
        ctrl.addWidget(self._sort_combo)
        ctrl.addSpacing(16)
        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("Filter words…")
        self._search_edit.setMaximumWidth(200)
        ctrl.addWidget(self._search_edit)
        ctrl.addStretch()
        self._export_btn = QPushButton("Copy all to clipboard")
        ctrl.addWidget(self._export_btn)
        outer.addLayout(ctrl)

        self._table = QTableWidget()
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels(["Rank", "Level", "Word", "Reading"])
        set_empty_hint(self._table, "No missing words to show: they're all in your deck or marked "
                       "found (or none match the filter).")
        hh = self._table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        hh.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self._table.horizontalHeaderItem(0).setToolTip(
            "Frequency rank in written Japanese (BCCWJ) — lower is more common. "
            "≈ = estimated rank for a compound the frequency list splits apart "
            "(e.g. 日本語). — means not ranked."
        )
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.verticalHeader().setVisible(False)
        self._table.setAlternatingRowColors(True)
        self._table.itemClicked.connect(self._on_click)
        outer.addWidget(self._table)

        hint = QLabel("Click a row to copy the word · Shift+Click to open it on Jisho.org.")
        hint.setStyleSheet(HINT_CSS)
        outer.addWidget(hint)

        self._level_combo.currentIndexChanged.connect(self._refresh)
        self._sort_combo.currentIndexChanged.connect(self._refresh)
        self._search_edit.textChanged.connect(self._refresh)
        self._export_btn.clicked.connect(self._export)
        self._refresh()

    def _collect_rows(self):
        """(rank or None, level, display, reading) in the chosen sort order."""
        # Frequency ranks are looked up once per panel build, not on every
        # refresh (each keystroke in the filter box triggers a refresh).
        if getattr(self, "_ranked", None) is None:
            self._ranked = [
                (freq_data.word_rank_info(d, r, jlpt_data.alt_forms(d, r)), lvl, d, r)
                for lvl in LEVELS
                for d, r in self._results[lvl]["missing_words"]
            ]
        level = self._level_combo.currentData()
        rows  = [row for row in self._ranked if level == "All" or row[1] == level]
        if self._sort_combo.currentData() == "freq":
            # Unranked last, in level order.
            rows.sort(key=lambda r: (r[0] is None, r[0][0] if r[0] else 0))
        return rows

    def _refresh(self):
        filt = self._search_edit.text().strip().lower()
        rows = self._collect_rows()
        if filt:
            rows = [r for r in rows if filt in r[2].lower() or filt in r[3].lower()]
        self._rows = rows
        _fill_table(self._table, [
            (
                (freq_data.rank_text(*rank) if rank else "—", FREQ_FG if rank else "#777777"),
                (lvl, LEVEL_FG.get(lvl, "#888")),
                (display, None),
                # A kana word's reading just repeats it: show its usual kanji
                # spelling there instead (かく 〔掻く〕), else leave it blank.
                (_shown_reading(display, reading)
                 or (f"〔{k}〕" if (k := _kanji_form(display, reading)) else ""), None),
            )
            for rank, lvl, display, reading in rows
        ], tooltips=[_meaning_tip(display, reading) for _r, _l, display, reading in rows])

    def _on_click(self, item):
        rows = getattr(self, "_rows", [])
        if 0 <= item.row() < len(rows):
            _r, _l, display, reading = rows[item.row()]
            _copy_or_jisho(display, self.window(), reading)

    def _export(self):
        lines = [f"{d}\t{r}" for _, _, d, r in getattr(self, "_rows", [])]
        _copy_to_clipboard("\n".join(lines))


# ── Marked & Suspended tab ────────────────────────────────────────────────────

def _tinted_button_style(color: str, rgb: tuple) -> str:
    """Button tinted in a table's colour: gold for found (★), red for
    suspended (✕)."""
    r, g, b = rgb
    return (
        f"QPushButton {{ color: {color}; border: 1px solid {color}; border-radius: 4px; "
        f"background: rgba({r},{g},{b},20); padding: 3px 12px; }}"
        f"QPushButton:hover {{ background: rgba({r},{g},{b},55); }}"
        f"QPushButton:pressed {{ background: rgba({r},{g},{b},90); }}"
    )


SUPPORT_URL = "https://ko-fi.com/benastromo"     # the owner's Ko-fi (2026-10-20)


def _quiet_button_style(color: str, rgb: tuple) -> str:
    """A rarely used, destructive button (Reset All …): grey and quiet
    until hovered, then in its table's colour (owner 2026-10-18: button
    hierarchy)."""
    r, g, b = rgb
    return (
        "QPushButton { color: #8a8a8a; border: 1px solid #333333; border-radius: 7px; "
        "background: transparent; padding: 3px 12px; }"
        f"QPushButton:hover {{ color: {color}; border-color: {color}; background: rgba({r},{g},{b},30); }}"
        f"QPushButton:pressed {{ background: rgba({r},{g},{b},70); }}"
    )


class MarkedSuspendedPanel(QWidget):
    """
    Shows two tables: words the user marked as found, and words they suspended.
    Each row has a revert button to undo the override.
    """

    changed = pyqtSignal()   # emitted when user reverts an entry
    refresh_requested = pyqtSignal()

    def __init__(self, overrides: Overrides, results: dict, lists: dict, parent=None):
        super().__init__(parent)
        self._overrides = overrides
        self._results   = results
        self._lists     = lists
        self._build()

    # ── build word→level lookup once ─────────────────────────────────────────

    # Found-table filters: (label, data). "freq" = on the frequency list but
    # no JLPT list (mostly the loanword button's words).
    _FOUND_SHOW = [("All levels", "all")] + [(l, l) for l in LEVELS] + \
                  [("Frequency list only", "freq")]
    _FOUND_SORT = [("Most common first", "rank"), ("By level", "level"), ("A–Z", "alpha")]

    def _level_of(self, display: str, reading: str) -> str:
        """"N5".."N1" (the easiest list the word is on), "Freq" for a
        frequency-list word on no JLPT list, or "—". One dict lookup: the
        found table can hold thousands of rows."""
        if getattr(self, "_level_map", None) is None:
            self._level_map = {}
            for lvl in LEVELS:
                for d, r in self._lists.get(lvl, []):
                    self._level_map.setdefault((d, r), lvl)
        lvl = self._level_map.get((display, reading))
        if lvl:
            return lvl
        return "Freq" if freq_data.word_rank(display, reading) else "—"

    def _rank_of(self, display: str, reading: str):
        """(rank, estimated) or None, as in the Missing Words tab."""
        return freq_data.word_rank_info(display, reading,
                                        jlpt_data.alt_forms(display, reading))

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setSpacing(12)

        hint = QLabel(
            "<b>Middle-click</b> any tile to mark a word as found  "
            "(★ yellow border) — it will count toward your progress without "
            "being in your Anki deck.<br>"
            "<b>Ctrl+Middle-click</b> to suspend a word "
            "(✕ dim tile) — it will be hidden from the JLPT lists entirely.<br>"
            "Use the <b>Revert</b> buttons below to undo an override."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet(HINT_CSS)
        outer.addWidget(hint)

        from .overrides import _PATH as _overrides_path
        path_lbl = QLabel(
            f"<span style='color:#888; font-size:12px;'>"
            f"overrides.json location: {_overrides_path}</span>"
        )
        path_lbl.setWordWrap(True)
        path_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        outer.addWidget(path_lbl)

        refresh_row = QHBoxLayout()
        refresh_row.addStretch()
        refresh_btn = QPushButton("⟳ Refresh Progress")
        refresh_btn.setToolTip(
            "Recalculate the Overview, Word Grid, and Missing Words tabs\n"
            "to reflect your found/suspended changes."
        )
        refresh_btn.clicked.connect(self.refresh_requested)
        refresh_row.addWidget(refresh_btn)
        outer.addLayout(refresh_row)

        # ── Marked as Found table ─────────────────────────────────────────────
        fcard = _section_card(outer)   # owner 2026-10-26, mock-up C (see the Suspended card)
        found_row = QHBoxLayout()
        found_hdr = QLabel("<span style='color:#ffe066; font-size:14px;'>"
                           "★  Marked as Found</span>")
        found_row.addWidget(found_hdr)
        found_row.addStretch()
        self._reset_found_btn = QPushButton("Reset All Found")
        self._reset_found_btn.setToolTip("Remove all 'marked as found' overrides.")
        self._reset_found_btn.clicked.connect(self._reset_found)
        self._reset_found_btn.setStyleSheet(_quiet_button_style("#ffe066", (255, 224, 102)))
        found_row.addWidget(self._reset_found_btn)
        fcard.addLayout(found_row)

        # ── Bulk toggle: English loanwords ────────────────────────────────────
        loan_row = QHBoxLayout()
        self._loan_btn = QPushButton()           # label set by _refresh_bulk_btns
        self._loan_btn.setMinimumWidth(260)
        self._loan_btn.setToolTip(
            "Marks English loanwords as found, since English speakers can usually "
            "guess them (カメラ, テーブル …).\nExcludes wasei-eigo (サラリーマン), "
            "false friends (マンション), Japanese-made shortenings (パソコン)\n"
            "and loanwords from other languages (パン, アルバイト).\n"
            "Covers the JLPT lists and the 20,000-word frequency list."
        )
        self._loan_btn.clicked.connect(self._toggle_loanwords)
        loan_row.addWidget(self._loan_btn)
        loan_help = QPushButton("?")              # the loanword schedule explained (owner 2026-10-21)
        loan_help.setObjectName("kicon")
        loan_help.setStyleSheet("font-weight: bold;")
        loan_help.setToolTip("How marked English loanwords count")
        loan_help.clicked.connect(lambda: _show_loanword_info_dialog(self))
        loan_row.addWidget(loan_help)
        loan_row.addStretch()
        fcard.addLayout(loan_row)

        self._found_search = QLineEdit()
        self._found_search.setPlaceholderText("Search marked as found…")
        self._found_search.setClearButtonEnabled(True)
        self._found_search.setMaximumWidth(280)
        copy_hint_f = QLabel("Click a row to copy the word to clipboard.")
        copy_hint_f.setStyleSheet(HINT_CSS)
        found_search_row = QHBoxLayout()
        found_search_row.addWidget(QLabel("Show:"))
        self._found_show = QComboBox()
        for label, data in self._FOUND_SHOW:
            self._found_show.addItem(label, data)
        self._found_show.setToolTip("Frequency list only: words on the 20,000-word "
                                    "frequency list but on no JLPT list")
        found_search_row.addWidget(self._found_show)
        found_search_row.addSpacing(8)
        found_search_row.addWidget(QLabel("Sort:"))
        self._found_sort = QComboBox()
        for label, data in self._FOUND_SORT:
            self._found_sort.addItem(label, data)
        found_search_row.addWidget(self._found_sort)
        found_search_row.addSpacing(16)
        found_search_row.addWidget(self._found_search)
        found_search_row.addWidget(copy_hint_f)
        found_search_row.addStretch()
        fcard.addLayout(found_search_row)
        self._found_count = QLabel()
        self._found_count.setStyleSheet(HINT_CSS)
        fcard.addWidget(self._found_count)

        self._found_table = self._make_table(["Level", "Word", "Reading", "Rank", ""])
        self._found_table.setToolTip("Click any row to copy the word to clipboard.")
        set_empty_hint(self._found_table, "No words marked as found yet. Middle-click a tile in a word "
                       "grid to count a word you know without a card.")
        fcard.addWidget(self._found_table)

        # ── Suspended table ───────────────────────────────────────────────────
        # each list in its own card, its Reset button inside it (owner 2026-10-26, mock-up C:
        # Reset All Suspended read as part of the Found list)
        scard = _section_card(outer)
        susp_row = QHBoxLayout()
        susp_hdr = QLabel("<span style='color:#e05a5a; font-size:14px;'>"
                          "✕  Suspended (excluded from lists)</span>")
        susp_row.addWidget(susp_hdr)
        susp_row.addStretch()
        self._reset_susp_btn = QPushButton("Reset All Suspended")
        self._reset_susp_btn.setToolTip("Remove all 'suspended' overrides.")
        self._reset_susp_btn.clicked.connect(self._reset_suspended)
        self._reset_susp_btn.setStyleSheet(_quiet_button_style("#e05a5a", (224, 90, 90)))
        susp_row.addWidget(self._reset_susp_btn)
        scard.addLayout(susp_row)

        self._susp_search = QLineEdit()
        self._susp_search.setPlaceholderText("Search suspended…")
        self._susp_search.setClearButtonEnabled(True)
        self._susp_search.setMaximumWidth(280)
        copy_hint_s = QLabel("Click a row to copy the word to clipboard.")
        copy_hint_s.setStyleSheet(HINT_CSS)
        susp_search_row = QHBoxLayout()
        susp_search_row.addWidget(self._susp_search)
        susp_search_row.addWidget(copy_hint_s)
        susp_search_row.addStretch()
        scard.addLayout(susp_search_row)

        self._susp_table = self._make_table(["Level", "Word", "Reading", ""])
        self._susp_table.setToolTip("Click any row to copy the word to clipboard.")
        set_empty_hint(self._susp_table, "Nothing suspended. Ctrl+Middle-click a tile in a word grid "
                       "to leave a word out of the lists.")
        scard.addWidget(self._susp_table)

        self.refresh()

        # Wire search bars and click-to-copy after tables exist
        self._found_search.textChanged.connect(
            lambda t: self._filter_table(self._found_table, t))
        self._found_show.currentIndexChanged.connect(lambda _i: self._refresh_found_busy())
        self._found_sort.currentIndexChanged.connect(lambda _i: self._refresh_found_busy())
        self._susp_search.textChanged.connect(
            lambda t: self._filter_table(self._susp_table, t))
        self._found_table.cellClicked.connect(
            lambda r, c: self._copy_word(self._found_table, r))
        self._susp_table.cellClicked.connect(
            lambda r, c: self._copy_word(self._susp_table, r))

    # ── bulk toggle helpers ───────────────────────────────────────────────────

    def _list_pairs(self, predicate) -> list:
        """All (display, reading) pairs across the JLPT lists matching
        predicate, skipping words already matched to a note in the deck
        (overrides only matter for words the deck doesn't have)."""
        in_deck = {
            (d, r)
            for lvl in LEVELS
            for d, r, nid in self._results.get(lvl, {}).get("known_words", [])
            if nid is not None
        }
        seen = set()
        pairs = []
        for lvl in LEVELS:
            for display, reading in self._lists.get(lvl, []):
                key = (display, reading)
                if key in seen or key in in_deck or not predicate(display, reading):
                    continue
                seen.add(key)
                pairs.append(key)
        return pairs

    def _loanword_pairs(self) -> list:
        """English loanwords the deck doesn't have, from the JLPT lists and
        the frequency list (same word on both = one mark, as far as the
        spelling and reading agree)."""
        pairs = self._list_pairs(jlpt_data.is_english_loanword)
        seen = {(d, freq_data._kata_to_hira(r)) for d, r in pairs}
        for _rank, d, r, nid in (self._results.get("frequency") or {}).get("entries", []):
            key = (d, freq_data._kata_to_hira(r))
            if nid is None and key not in seen and freq_data.is_english_loanword(d, r):
                seen.add(key)
                pairs.append((d, r))
        return pairs

    def _refresh_bulk_btns(self):
        loans = self._loanword_pairs()
        loans_on = bool(loans) and all(self._overrides.is_found(d, r) for d, r in loans)
        on_style  = "color: #4caf50; font-weight: bold; padding: 4px 10px;"
        self._loan_btn.setText(
            f"✓ Unmark English Loanwords ({len(loans)})" if loans_on
            else f"★ Mark English Loanwords as Found ({len(loans)})"
        )
        self._loan_btn.setStyleSheet(on_style if loans_on else "color: #ffe066; font-weight: bold; padding: 4px 10px;")
        _regold(self._loan_btn)        # rewritten after the gold pass: Japanese + gold again

    def _toggle_loanwords(self):
        pairs = self._loanword_pairs()
        if not pairs:
            return
        if all(self._overrides.is_found(d, r) for d, r in pairs):
            self._overrides.remove_found_many(pairs)
        else:
            self._overrides.add_found_many(pairs)
        self.refresh()
        self.changed.emit()

    def _reset_found(self):
        if not self._overrides.found:
            return
        n = len(self._overrides.found)
        if QMessageBox.question(
            self, "Reset All Found",
            f"Remove all {n} 'marked as found' word(s)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        ) != QMessageBox.StandardButton.Yes:
            return
        self._overrides.clear_found()
        self.refresh()
        self.changed.emit()

    def _reset_suspended(self):
        if not self._overrides.suspended:
            return
        n = len(self._overrides.suspended)
        if QMessageBox.question(
            self, "Reset All Suspended",
            f"Remove all {n} 'suspended' word(s)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        ) != QMessageBox.StandardButton.Yes:
            return
        self._overrides.clear_suspended()
        self.refresh()
        self.changed.emit()

    def _filter_table(self, table: QTableWidget, text: str):
        """Show/hide rows whose word or reading contains the search text."""
        q = text.strip().lower()
        for row in range(table.rowCount()):
            word_item    = table.item(row, 1)
            reading_item = table.item(row, 2)
            word    = (word_item.text()    if word_item    else "").lower()
            reading = (reading_item.text() if reading_item else "").lower()
            table.setRowHidden(row, bool(q) and q not in word and q not in reading)

    def _copy_word(self, table: QTableWidget, row: int):
        """Copy the word (column 1) of the clicked row to the clipboard."""
        item = table.item(row, 1)
        if item:
            QApplication.clipboard().setText(item.text())

    def _make_table(self, headers: list) -> QTableWidget:
        t = QTableWidget()
        t.setColumnCount(len(headers))
        t.setHorizontalHeaderLabels(headers)
        for c in range(len(headers)):   # Word and Reading stretch
            t.horizontalHeader().setSectionResizeMode(
                c, QHeaderView.ResizeMode.Stretch if c in (1, 2)
                else QHeaderView.ResizeMode.ResizeToContents)
        t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        t.verticalHeader().setVisible(False)
        t.setAlternatingRowColors(True)
        t.setMinimumHeight(120)
        return t

    def refresh(self):
        self._refresh_found()
        self._populate(
            self._susp_table,
            [(d, r, None) for d, r in sorted(self._overrides.suspended_pairs())],
            is_found=False,
        )
        self._refresh_bulk_btns()
        # Re-apply any active search filters
        if hasattr(self, "_susp_search"):
            self._filter_table(self._susp_table, self._susp_search.text())

    def _refresh_found_busy(self):
        """Show / sort changed: a long list takes ~1 s to refill."""
        from .busy import busy
        with busy(self, "Updating the list…"):
            self._refresh_found()

    def _refresh_found(self):
        """Found table: filtered by the Show box, ordered by the Sort box
        (most common first by default, like Missing Words)."""
        show = self._found_show.currentData()
        sort = self._found_sort.currentData()
        rows = []
        for d, r in self._overrides.found_pairs():
            lvl = self._level_of(d, r)
            if show == "freq" and lvl != "Freq":
                continue
            if show not in ("all", "freq") and lvl != show:
                continue
            rows.append((d, r, self._rank_of(d, r)))
        total = len(self._overrides.found)
        level_order = {l: i for i, l in enumerate(LEVELS + ["Freq", "—"])}
        rank_key = lambda row: (row[2] is None, row[2][0] if row[2] else 0)
        if sort == "alpha":
            rows.sort(key=lambda row: (row[0], row[1]))
        elif sort == "level":
            rows.sort(key=lambda row: (level_order[self._level_of(row[0], row[1])],) + rank_key(row))
        else:
            rows.sort(key=lambda row: rank_key(row) + (row[0],))
        self._populate(self._found_table, rows, is_found=True)
        self._found_count.setText(
            f"Showing {len(rows):,} of {total:,} found words" if len(rows) != total
            else f"{total:,} found words")
        _regold(self._found_count)
        self._filter_table(self._found_table, self._found_search.text())

    def _populate(self, table: QTableWidget, rows: list, is_found: bool):
        """rows: [(display, reading, rank info or None)], already ordered.
        The table's last column holds the Revert button; a table with a
        Rank column (the found table) shows the rank before it."""
        has_rank = table.columnCount() == 5
        table.setUpdatesEnabled(False)
        table.setRowCount(0)
        table.setRowCount(len(rows))
        try:
            self._fill_override_rows(table, rows, is_found, has_rank)
        finally:
            table.setUpdatesEnabled(True)

    def _fill_override_rows(self, table, rows, is_found, has_rank):
        for i, (display, reading, rank) in enumerate(rows):
            lvl   = self._level_of(display, reading)
            color = LEVEL_FG.get(lvl, FREQ_FG if lvl == "Freq" else "#888")

            if has_rank:
                rk = QTableWidgetItem(freq_data.rank_text(*rank) if rank else "—")
                rk.setForeground(QColor(FREQ_FG if rank else "#777777"))
                _gold_item(rk)
                rk.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                table.setItem(i, 3, rk)

            li = QTableWidgetItem(lvl)
            li.setForeground(QColor(color))
            _gold_item(li)
            li.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            di = QTableWidgetItem(display)
            di.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            ri = QTableWidgetItem(_shown_reading(display, reading))
            ri.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            table.setItem(i, 0, li)
            table.setItem(i, 1, di)
            table.setItem(i, 2, ri)

            # Gold mode: born Japanese and gold (thousands of rows — cheaper
            # than re-walking them after every refill).
            gold = _GOLD_MODE["on"]
            btn = QPushButton("元に戻す" if gold else "Revert")
            btn.setFixedHeight(22)
            btn.setStyleSheet(
                "font-size: 12px; padding: 1px 6px; "
                + ("color: #f5c518; background: #2a2410; border: 1px solid #6b5a1a;"
                   if gold else "color: #ccc; background: #333; border: 1px solid #555;")
                + " border-radius: 3px;"
            )
            # capture loop vars
            def _make_revert(d, r, found):
                def _revert():
                    if found:
                        self._overrides.remove_found(d, r)
                    else:
                        self._overrides.remove_suspended(d, r)
                    self.changed.emit()
                return _revert

            btn.clicked.connect(_make_revert(display, reading, is_found))
            table.setCellWidget(i, table.columnCount() - 1, btn)


# ── Off-list words panel (deck cards on no Kotodama JLPT list) ──────────────────────────────────────────────────────

class _UnlistedPanel(QWidget):
    def __init__(self, words: list, overrides: Overrides,
                 on_override_changed=None, parent=None, nid_rank: dict = None,
                 maturity: dict = None, nid_rank_extra: dict = None):
        super().__init__(parent)
        # Most common first (frequency rank); cards outside the list last.
        self._nid_rank            = nid_rank or {}         # nid → 0-based top-20,000 rank
        self._nid_rank_extra      = nid_rank_extra or {}   # nid → (rank, estimated)
        self._maturity            = maturity or {}
        self._words               = sorted(words, key=lambda w: self._sort_rank(w[2]))
        self._overrides           = overrides
        self._on_override_changed = on_override_changed
        self._build()

    def _rank_of(self, nid):
        """(1-based rank, estimated) for a note, or None if unranked."""
        r = self._nid_rank.get(nid)
        if r is not None:
            return r + 1, False
        return self._nid_rank_extra.get(nid)

    def _sort_rank(self, nid) -> float:
        info = self._rank_of(nid)
        return _INF if info is None else info[0]

    def _build(self):
        outer = QVBoxLayout(self)
        n_common = sum(1 for _, _, nid in self._words if nid in self._nid_rank)
        info  = QLabel(
            f"<b>Off-list words</b> — {len(self._words):,} cards in your deck aren't on "
            "the Kotodama JLPT lists. The lists are old and incomplete, so many of these "
            "can still appear on the test. "
            f"{n_common:,} of them are among the {freq_data.TIERS[-1]:,} most common words, "
            "and they all count toward your rank and the Frequency Check.<br>"
            "<span style='color:#aaa; font-size:13px;'>"
            f"Tiles are grouped {GROUPING_TEXT}, most common first in each group; "
            "the list is most common first (≈ = estimated rank for a compound the "
            "frequency list splits apart, e.g. 日本語). Drag the divider to resize. "
            "Click a tile (or double-click a row) to open it in the browser. "
            "These cannot be marked as found or suspended.</span>"
        )
        info.setWordWrap(True)
        outer.addWidget(info)
        outer.addWidget(_maturity_legend("unlisted"))

        # Tile grid on the left, word list on the right; the user can drag
        # the divider to change the proportions.
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        outer.addWidget(splitter, 1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setMinimumWidth(160)

        container = QWidget()
        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(4, 4, 4, 4)
        vbox.setAlignment(Qt.AlignmentFlag.AlignTop)

        cells = []
        tiles = sorted(self._words, key=lambda w: (maturity_group(self._maturity, w[2]),
                                                   self._sort_rank(w[2])))
        for d, r, nid in tiles:
            info = self._rank_of(nid)
            cell = WordCell(d, r, nid, "unlisted", self._overrides, overridable=False,
                            rank=None if info is None else info[0],
                            rank_est=bool(info and info[1]),
                            maturity=self._maturity.get(nid))
            cells.append(cell)
        vbox.addWidget(_TileCanvas(cells, glow=UNLISTED_FG))
        scroll.setWidget(container)
        splitter.addWidget(scroll)

        right = QWidget()
        right.setMinimumWidth(200)
        rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        ctrl = QHBoxLayout()
        self._search = QLineEdit()
        self._search.setPlaceholderText("Filter…")
        self._search.textChanged.connect(self._refresh)
        ctrl.addWidget(self._search, 1)
        copy_btn = QPushButton("Copy all")
        copy_btn.setToolTip("Copy every off-list word (word TAB reading) to the clipboard")
        copy_btn.clicked.connect(self._copy_all)
        ctrl.addWidget(copy_btn)
        rv.addLayout(ctrl)

        self._table = QTableWidget()
        self._table.setColumnCount(3)
        self._table.setHorizontalHeaderLabels(["Rank", "Word", "Reading"])
        hh = self._table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        hh.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.verticalHeader().setVisible(False)
        self._table.setAlternatingRowColors(True)
        self._table.itemDoubleClicked.connect(self._on_double_click)
        rv.addWidget(self._table)
        splitter.addWidget(right)
        # Start with the grid taking about two thirds of the width.
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)
        self._refresh()

    def _refresh(self):
        filt = self._search.text().strip().lower()
        rows = [(d, r, nid) for d, r, nid in self._words
                if not filt or filt in d.lower() or filt in r.lower()]
        cells = []
        for d, r, nid in rows:
            info = self._rank_of(nid)
            cells.append((
                (freq_data.rank_text(*info) if info else "—",
                 FREQ_FG if info else "#777777"),
                (d, None),
                (_shown_reading(d, r), None),
            ))
        _fill_table(self._table, cells,
                    tooltips=[_meaning_tip(d, r) for d, r, _ in rows])
        self._shown = rows   # row index → (display, reading, nid), for double-click

    def _on_double_click(self, item):
        shown = getattr(self, "_shown", [])
        if 0 <= item.row() < len(shown):
            nid = shown[item.row()][2]
            if nid:
                _open_in_browser(nid)

    def _copy_all(self):
        lines = [f"{d}\t{r}" for d, r, _ in self._words]
        _copy_to_clipboard("\n".join(lines))


# ── Overview tab ──────────────────────────────────────────────────────────────

class DivineOverlay(QWidget):
    """Amaterasu (owner 2026-10-09: "a god has permeated the plugin", and
    the rules don't apply to her): light drawn on top of the whole Overview
    page, ignoring the mouse —
      - light rays fanning out from the light behind her head, turning
        slowly, spilling over the bars and text above and below the badge;
      - a sunburst on the same point that reaches past the badge;
      - a few soft lens-flare ghosts;
      - a breathing halo around every gold bar, beyond the bar widget's own
        edges (the bar's in-widget glow breathes too, in LevelBar).
    Its timer is the divine clock (_DIVINE): it also breathes the badge and
    repaints the gold bars. Idle (no painting) below Amaterasu.

    Without a badge (the Kanji & Grammar tab) it's active while that page's
    bars are gold, and the light pours down from just above the top of the
    view ("light from heaven"), a little softer, with no silhouette."""

    def __init__(self, host: QWidget, badge: "RankBadge" = None):
        super().__init__(host)
        self._host, self._badge = host, badge
        self._failed = False
        self._was_active = False
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self._timer = QTimer(self)
        self._timer.setInterval(50)
        self._timer.timeout.connect(self._tick)
        host.installEventFilter(self)
        self.setGeometry(host.rect())
        self.raise_()

    def eventFilter(self, obj, event):
        if obj is self._host and event.type() == QEvent.Type.Resize:
            self.setGeometry(self._host.rect())
            self.raise_()
        return False

    def showEvent(self, event):
        super().showEvent(event)
        self._timer.start()

    def hideEvent(self, event):
        self._timer.stop()
        super().hideEvent(event)

    def _active(self) -> bool:
        if self._failed:
            return False
        if self._badge is not None:
            return getattr(self._badge, "_divine", False)
        return any(b._force_max_gold for b in self._host.findChildren(LevelBar))

    def _light_source(self) -> QPointF:
        """Behind Amaterasu's bun, or (no badge) above the top of the view."""
        if self._badge is not None:
            return QPointF(self._badge.mapTo(self._host, self._badge.halo_point().toPoint()))
        view = self._host.visibleRegion().boundingRect()
        if view.isEmpty():
            view = self.rect()
        return QPointF(view.center().x(), view.top() - 140)

    def _gold_bars(self) -> list:
        """(widget, bar rect in host coordinates) for every gold bar."""
        out = []
        for b in self._host.findChildren(LevelBar):
            if b._force_max_gold and b.isVisible():
                h = b.height()
                rect = QRect(b._pad, (h - b._bar_h) // 2, b.width() - 2 * b._pad, b._bar_h)
                out.append((b, rect.translated(b.mapTo(self._host, QPoint(0, 0)))))
        for b in self._host.findChildren(RankBar):
            if b.isVisible() and getattr(b, "_info", {}).get("is_max_amaterasu"):
                h = b.height()
                rect = QRect(b._PAD, (h - 24) // 2, b.width() - 2 * b._PAD, 24)
                out.append((b, rect.translated(b.mapTo(self._host, QPoint(0, 0)))))
        return out

    def _tick(self):
        active = self._active()
        self._bars_cache = self._gold_bars() if active else []
        if active:
            _DIVINE["phase"] += 0.1          # one breath ≈ 3.1 s
            if self._badge is not None:
                self._badge.divine_tick()
            for b, _r in self._bars_cache:
                b.update()
        if active or self._was_active:
            self.update()                    # (one last repaint clears it)
        self._was_active = active

    # Light is soft, so it's rendered at this fraction of the screen
    # resolution and scaled up smoothly: ~¼ of the pixel work, no visible loss.
    _SCALE = 0.5

    def paintEvent(self, event):
        if not self._active():
            return
        # The ascension intro's dark opening: no light until hers blooms.
        light = self._badge.intro_light() if self._badge is not None else 1.0
        if light <= 0.0:
            return
        # Only the part on screen: the page can be much taller than the view.
        view = self.visibleRegion().boundingRect()
        vis = view.intersected(event.rect())
        if vis.isEmpty():
            return
        p = QPainter(self)
        try:
            # Light is drawn off-screen first so her silhouette can be cut
            # out of it (DestinationOut) before it lands on the page.
            # Scaled explicitly (see GridSheen): an image devicePixelRatio of
            # 0.75 got rounded to 1 on a friend's PC at 150% scaling, pushing
            # the light 1.5× away from her.
            # The whole view is rendered once per tick of the divine clock and
            # reused until the next one: her animated picture repaints its
            # spot ~30×/s, and re-rendering the light for each frame starved
            # the video (owner 2026-10-15: "fps a little low").
            s = self.devicePixelRatioF() * self._SCALE
            key = (_DIVINE["phase"], view, s, self._badge is not None and self._badge.has_video())
            if getattr(self, "_cache_key", None) != key:
                img = QImage(max(1, int(view.width() * s)), max(1, int(view.height() * s)),
                             QImage.Format.Format_ARGB32_Premultiplied)
                img.fill(Qt.GlobalColor.transparent)
                ip = QPainter(img)
                try:
                    ip.setRenderHint(QPainter.RenderHint.Antialiasing)
                    ip.scale(s, s)
                    ip.translate(-view.x(), -view.y())
                    self._paint(ip)
                    if self._badge is not None:
                        self._shade_amaterasu(ip)
                    self._paint_dust(ip, view)
                finally:
                    ip.end()
                self._cache, self._cache_key = img, key
            p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            p.setOpacity(light)
            p.drawImage(QRectF(vis), self._cache,
                        QRectF((vis.x() - view.x()) * s, (vis.y() - view.y()) * s,
                               vis.width() * s, vis.height() * s))
        except Exception:
            import traceback
            traceback.print_exc()
            self._failed = True              # never raise every frame
        finally:
            p.end()

    # Golden dust: specks of light drifting up the view, swaying and
    # twinkling. Fixed pseudo-random parameters per speck (x, start y,
    # speed, size, sway, twinkle phase) so nothing is allocated per frame.
    _DUST = [((i * 0.6180339) % 1.0, (i * 0.3819660 + 0.17) % 1.0,
              0.012 + 0.02 * ((i * 0.7548776) % 1.0), 2.0 + 4.0 * ((i * 0.5698403) % 1.0),
              0.01 + 0.025 * ((i * 0.2451223) % 1.0), i * 1.7)
             for i in range(70)]
    _sprite = None

    @classmethod
    def _dust_sprite(cls) -> QPixmap:
        """One soft gold speck, drawn once and reused (cheap to blit)."""
        if cls._sprite is None:
            pm = QPixmap(32, 32)
            pm.fill(Qt.GlobalColor.transparent)
            sp = QPainter(pm)
            g = QRadialGradient(QPointF(16, 16), 16)
            g.setColorAt(0.0, QColor(255, 255, 255, 255))
            g.setColorAt(0.25, QColor(255, 246, 200, 220))
            g.setColorAt(0.6, QColor(255, 215, 90, 70))
            g.setColorAt(1.0, QColor(255, 200, 60, 0))
            sp.setPen(Qt.PenStyle.NoPen)
            sp.setBrush(QBrush(g))
            sp.drawEllipse(QRectF(0, 0, 32, 32))
            sp.end()
            cls._sprite = pm
        return cls._sprite

    def _paint_dust(self, p: QPainter, vis: QRect):
        sprite = self._dust_sprite()
        phase = _DIVINE["phase"]
        view = self._host.visibleRegion().boundingRect()
        if view.isEmpty():
            view = vis
        for x0, y0, speed, size, sway, tw in self._DUST:
            # phase grows ~2/s, so a speck crosses the view in ~15–40 s
            y = view.top() + ((y0 - phase * speed) % 1.0) * view.height()
            x = view.left() + ((x0 + sway * math.sin(phase * 0.4 + tw)) % 1.0) * view.width()
            p.setOpacity(0.35 + 0.65 * (0.5 + 0.5 * math.sin(phase * 1.1 + tw)))
            d = size * 1.3          # ~3–8 px (owner: the first ones were too big)
            p.drawPixmap(QRectF(x - d / 2, y - d / 2, d, d), sprite, QRectF(sprite.rect()))
        p.setOpacity(1.0)

    def _blow_out_sky(self, p: QPainter, ar: QRectF):
        """Blow her picture's sky out to white-gold so the picture's top and
        side edges vanish into the badge (owner 2026-10-09). Opaque over the
        upper picture, fading in from PAD px outside its edges, and fading
        out towards the bottom (AMATERASU_SKY_*). Her silhouette is cut out
        of it afterwards with the rest of the light."""
        PAD = 36.0
        full, end = AMATERASU_SKY_FULL, AMATERASU_SKY_END
        if self._badge.has_video():
            # Her animated sky is already light and has its own moving rays
            # and shimmer: only melt the top edge into the badge.
            full, end = 0.0, AMATERASU_VIDEO_SKY_END
        rect = ar.adjusted(-PAD, -PAD, PAD, 0)
        # At logical resolution (plenty: the overlay itself is half-res),
        # drawn into an explicit target rect — no image devicePixelRatio.
        w, h = rect.width(), rect.height()
        tmp = QImage(max(1, int(w)), max(1, int(h)), QImage.Format.Format_ARGB32_Premultiplied)
        tmp.fill(Qt.GlobalColor.transparent)
        tp = QPainter(tmp)
        try:
            # White at the light behind her bun, warm cream further out.
            c = QPointF(PAD + ar.width() * AMATERASU_BUN[0], PAD + ar.height() * AMATERASU_BUN[1])
            sky = QRadialGradient(c, max(w, h) * 0.8)
            sky.setColorAt(0.0, QColor(255, 255, 255, 255))
            sky.setColorAt(0.45, QColor(255, 252, 236, 255))
            sky.setColorAt(1.0, QColor(255, 246, 212, 255))
            tp.fillRect(QRectF(0, 0, w, h), QBrush(sky))
            tp.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
            # Fade in from outside the picture's left / right edges …
            lr = QLinearGradient(0, 0, w, 0)
            lr.setColorAt(0.0, QColor(0, 0, 0, 0))
            lr.setColorAt(PAD / w, QColor(0, 0, 0, 255))
            lr.setColorAt(1 - PAD / w, QColor(0, 0, 0, 255))
            lr.setColorAt(1.0, QColor(0, 0, 0, 0))
            tp.fillRect(QRectF(0, 0, w, h), QBrush(lr))
            # … and its top edge, then fade out down the picture.
            tb = QLinearGradient(0, 0, 0, h)
            tb.setColorAt(0.0, QColor(0, 0, 0, 0))
            tb.setColorAt(PAD / h, QColor(0, 0, 0, 255))
            tb.setColorAt((PAD + ar.height() * full) / h, QColor(0, 0, 0, 255))
            tb.setColorAt((PAD + ar.height() * end) / h, QColor(0, 0, 0, 0))
            tb.setColorAt(1.0, QColor(0, 0, 0, 0))
            tp.fillRect(QRectF(0, 0, w, h), QBrush(tb))
        finally:
            tp.end()
        p.drawImage(rect, tmp, QRectF(tmp.rect()))

    def _shade_amaterasu(self, p: QPainter):
        """The light is behind her: remove it from her bun, face and body
        with feathered ellipses (so she isn't a hard cut-out), then add a
        thin rim of light just inside each outline. The picture's border
        keeps the full overlay, which blends it into the scene."""
        badge = self._badge
        ar = badge.art_rect()
        if ar is None:
            return
        tl = badge.mapTo(self._host, ar.topLeft().toPoint())
        ar = QRectF(QPointF(tl), ar.size())
        pulse = _divine_pulse()
        self._blow_out_sky(p, ar)

        def ellipse(shape, stops, mode):
            cx, cy, rx, ry = shape[:4]
            p.save()
            p.setCompositionMode(mode)
            p.translate(ar.x() + cx * ar.width(), ar.y() + cy * ar.height())
            p.scale(rx * ar.width(), ry * ar.height())
            g = QRadialGradient(QPointF(0, 0), 1.0)
            for pos, col in stops:
                g.setColorAt(pos, col)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(g))
            p.drawEllipse(QPointF(0, 0), 1.0, 1.0)
            p.restore()

        # Rim light first: a soft bright ring where each shape's feather
        # ends. Drawn before the cut so a ring crossing another shape's
        # solid core (the face ring inside the hair) is erased again, and
        # only her outline keeps its rim.
        over = QPainter.CompositionMode.CompositionMode_SourceOver
        rim = int(80 + 60 * pulse)
        for shape in AMATERASU_SHADOW:
            ellipse(shape, ((0.0, QColor(255, 250, 225, 0)), (0.80, QColor(255, 250, 225, 0)),
                            (0.92, QColor(255, 250, 225, rim)), (1.0, QColor(255, 250, 225, 0))),
                    over)
        out = QPainter.CompositionMode.CompositionMode_DestinationOut
        for shape in AMATERASU_SHADOW:
            strength, feather = shape[4], shape[5]
            a = int(255 * strength)
            ellipse(shape, ((0.0, QColor(0, 0, 0, a)), (feather, QColor(0, 0, 0, a)),
                            (1.0, QColor(0, 0, 0, 0))), out)
        p.setCompositionMode(over)
        self._feather_edges(p, ar)

    def _feather_edges(self, p: QPainter, ar: QRectF):
        """Blend the picture's left, right and bottom edges (her dark hair
        and robe meeting the badge) into the scene: cream across each edge,
        opaque on the edge itself and fading out 14% (sides) / 22% (bottom)
        of the picture inside it and 36 px outside it. Drawn after the silhouette
        cut, so the cut doesn't take it away again. (The top edge is
        already gone under the blown-out sky.)"""
        # One soft frame (no seams at the corners): a cream layer over the
        # picture plus OUT px around it, faded out towards its outer edge,
        # with a feathered hole cut in the middle. Each fade is two linear
        # ramps multiplied (DestinationIn), which rounds the corners.
        OUT = 36.0
        fx, fy = ar.width() * 0.14, ar.height() * 0.22
        R = QRectF(ar.left() - OUT, ar.top(), ar.width() + 2 * OUT, ar.height() + OUT)
        w, h = R.width(), R.height()

        def layer():
            # logical resolution, drawn into an explicit rect (see _blow_out_sky)
            img = QImage(max(1, int(w)), max(1, int(h)), QImage.Format.Format_ARGB32_Premultiplied)
            img.fill(Qt.GlobalColor.transparent)
            return img

        def ramp(painter, horizontal: bool, stops):
            g = (QLinearGradient(0, 0, w, 0) if horizontal else QLinearGradient(0, 0, 0, h))
            for pos, a in stops:
                g.setColorAt(min(max(pos, 0.0), 1.0), QColor(0, 0, 0, a))
            painter.fillRect(QRectF(0, 0, w, h), QBrush(g))

        frame, hole = layer(), layer()
        fp = QPainter(frame)
        try:
            # Opaque on the edge line itself: the picture's last rows are a
            # light grey strip that showed through anything less.
            fp.fillRect(QRectF(0, 0, w, h), QColor(255, 246, 212, 255))
            fp.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
            # Fade out beyond the left / right / bottom edges; fade in from
            # the top (the blown-out sky already covers the upper part).
            ramp(fp, True, ((0, 0), (OUT / w, 255), (1 - OUT / w, 255), (1, 0)))
            ramp(fp, False, ((0, 0), (0.35, 255), ((h - OUT) / h, 255), (1, 0)))
        finally:
            fp.end()
        hp = QPainter(hole)
        try:
            # Clear in the middle of the picture, feathering to nothing at
            # its left, right and bottom edges (open at the top).
            hp.fillRect(QRectF(0, 0, w, h), QColor(0, 0, 0, 255))
            hp.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
            ramp(hp, True, ((OUT / w, 0), ((OUT + fx) / w, 255),
                            ((w - OUT - fx) / w, 255), ((w - OUT) / w, 0)))
            ramp(hp, False, ((0, 255), ((ar.height() - fy) / h, 255), (ar.height() / h, 0)))
        finally:
            hp.end()
        fp = QPainter(frame)
        try:
            fp.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationOut)
            fp.drawImage(QPointF(0, 0), hole)
        finally:
            fp.end()
        p.drawImage(R, frame, QRectF(frame.rect()))

    def _paint(self, p: QPainter):
        phase = _DIVINE["phase"]
        pulse = _divine_pulse()
        c = self._light_source()
        soft = 1.0 if self._badge is not None else 0.7   # heaven light: a bit gentler
        W, H = self.width(), self.height()
        p.setPen(Qt.PenStyle.NoPen)

        # 1. Breathing halos past every gold bar (outside the bar only, so
        #    the fill and its text aren't washed out). Scaled to the bar's
        #    height, so the compact Kanji & Grammar bars get smaller halos.
        for b, br in getattr(self, "_bars_cache", []):
            bp = _divine_pulse(b)
            k = max(0.55, br.height() / 32)
            inner = QPainterPath()
            inner.addRoundedRect(QRectF(br).adjusted(-10 * k, -10 * k, 10 * k, 10 * k),
                                 16 * k, 16 * k)
            for i in range(5, 0, -1):
                s = (10 + i * 9) * k * (0.75 + 0.55 * bp)
                ring = QPainterPath()
                ring.addRoundedRect(QRectF(br).adjusted(-s, -s, s, s), 8 + s, 8 + s)
                p.setBrush(QColor(255, 240, 170, int((14 + 26 * bp) * (1.2 - i / 5))))
                p.drawPath(ring.subtracted(inner))

        # 2. Sunburst reaching past the badge (or down from above).
        reach = max(W, 600) * (0.75 + 0.2 * pulse)
        sun = QRadialGradient(c, reach)
        sun.setColorAt(0.0, QColor(255, 255, 255, int((150 + 60 * pulse) * soft)))
        sun.setColorAt(0.12, QColor(255, 252, 230, int((110 + 50 * pulse) * soft)))
        sun.setColorAt(0.35, QColor(255, 240, 170, 45))
        sun.setColorAt(1.0, QColor(255, 236, 150, 0))
        p.fillRect(self.rect(), QBrush(sun))

        # 3. Light rays: two fans turning opposite ways; each ray has its own
        #    width, length and shimmer so the fan looks alive, not mechanical.
        R = max(W, H, 900) * 1.1
        for layer, (n, speed, base_a, width_k) in enumerate(((22, 3.0, 95, 1.0),
                                                             (11, -1.7, 55, 2.2))):
            rot = math.radians(phase * speed)
            for i in range(n):
                a = rot + i * 2 * math.pi / n + 0.35 * math.sin(i * 2.3 + layer)
                half = (0.035 + 0.03 * (0.5 + 0.5 * math.sin(i * 1.7 + layer * 4))) * width_k
                length = R * (0.45 + 0.55 * abs(math.sin(i * 1.3 + phase * 0.05 + layer)))
                shimmer = 0.6 + 0.4 * math.sin(phase * 1.3 + i * 0.9 + layer * 2)
                alpha = int(base_a * shimmer * (0.6 + 0.4 * pulse) * soft)
                grad = QRadialGradient(c, length)
                grad.setColorAt(0.0, QColor(255, 255, 255, alpha))
                grad.setColorAt(0.25, QColor(255, 250, 215, int(alpha * 0.75)))
                grad.setColorAt(0.6, QColor(255, 236, 150, int(alpha * 0.3)))
                grad.setColorAt(1.0, QColor(255, 236, 150, 0))
                poly = QPolygonF([
                    c,
                    c + QPointF(math.cos(a - half) * length, math.sin(a - half) * length),
                    c + QPointF(math.cos(a + half) * length, math.sin(a + half) * length),
                ])
                p.setBrush(QBrush(grad))
                p.drawPolygon(poly)

        # 4. Lens-flare ghosts along the line from her light through the
        #    middle of the view, drifting slightly.
        view = self._host.visibleRegion().boundingRect()
        mid = QPointF(view.center()) if not view.isEmpty() else QPointF(W / 2, H / 2)
        d = mid - c
        for k, (t, rad, al) in enumerate(((0.55, 26, 40), (0.9, 12, 55), (1.3, 44, 28),
                                          (1.7, 18, 45))):
            q = c + d * (t + 0.04 * math.sin(phase * 0.7 + k))
            g = QRadialGradient(q, rad * (0.9 + 0.2 * pulse))
            g.setColorAt(0.0, QColor(255, 250, 220, int(al * (0.7 + 0.3 * pulse) * soft)))
            g.setColorAt(0.7, QColor(255, 225, 140, int(al * 0.4)))
            g.setColorAt(1.0, QColor(255, 225, 140, 0))
            p.setBrush(QBrush(g))
            p.drawEllipse(q, rad * 1.2, rad * 1.2)


class _Inscription(QWidget):
    """Amaterasu mode, bottom of the Overview: the message from the last
    20,000 share image (the built-in message until one is written),
    engraved — gold letters cut into the page (a dark edge above, a light
    edge below), between thin gold rules with a ✦."""

    _PAD = 26

    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self._text = text
        f = QFont()
        f.setFamilies(["Yu Mincho", "MS Mincho", "Hiragino Mincho ProN", "Noto Serif CJK JP", "serif"])
        f.setPointSize(13)
        self._font = f
        sp = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sp.setHeightForWidth(True)
        self.setSizePolicy(sp)

    def set_text(self, text: str):
        self._text = text
        self.updateGeometry()
        self.update()

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, w: int) -> int:
        fm = QFontMetrics(self._font)
        r = fm.boundingRect(QRect(0, 0, max(50, w - 4 * self._PAD), 10_000),
                            int(Qt.AlignmentFlag.AlignHCenter) | int(Qt.TextFlag.TextWordWrap),
                            self._text)
        return r.height() + 2 * self._PAD + 30

    def sizeHint(self):
        return QSize(600, self.heightForWidth(600))

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        # gold rules with a ✦ in the middle, above and below
        for y in (12, h - 12):
            g = QLinearGradient(0, 0, w, 0)
            g.setColorAt(0, QColor(245, 197, 24, 0))
            g.setColorAt(0.5, QColor(245, 197, 24, 200))
            g.setColorAt(1, QColor(245, 197, 24, 0))
            p.setPen(QPen(QBrush(g), 1))
            p.drawLine(QPointF(w * 0.1, y), QPointF(w * 0.9, y))
            p.setPen(QColor("#f5c518"))
            p.drawText(QRectF(w / 2 - 10, y - 9, 20, 18), Qt.AlignmentFlag.AlignCenter, "✦")
        p.setFont(self._font)
        r = QRectF(2 * self._PAD, self._PAD + 4, w - 4 * self._PAD, h - 2 * self._PAD - 8)
        flags = int(Qt.AlignmentFlag.AlignCenter) | int(Qt.TextFlag.TextWordWrap)
        # engraved: dark edge above-left, light edge below-right, gold face
        for dx, dy, col in ((-1, -1, QColor(40, 26, 0, 220)),
                            (1, 1, QColor(255, 246, 210, 150)),
                            (0, 0, QColor("#d9a400"))):
            p.setPen(col)
            p.drawText(r.translated(dx, dy), flags, self._text)
        p.end()


class _ShowWatcher(QObject):
    """Calls on_show (after the event) when a watched widget is shown."""

    def __init__(self, on_show, parent=None):
        super().__init__(parent)
        self._on_show = on_show

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Show:
            QTimer.singleShot(0, self._on_show)
        return False


class _LazyTab(QWidget):
    """A tab page that builds its contents the first time it's shown
    (owner 2026-10-24: opening took seconds, mostly building tabs nobody
    had looked at yet), under a "please wait" note (busy.py, owner
    2026-10-25). build() returns the real page."""

    def __init__(self, build, busy_title: str, parent=None):
        super().__init__(parent)
        self._build_fn = build
        self._busy_title = busy_title
        self.page = None
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)

    def ensure(self):
        if self.page is None:
            self.page = self._build_fn()
            self.layout().addWidget(self.page)
            dlg = self.window()
            if getattr(dlg, "_gold", False):     # built after gold mode came on
                from . import divine_text
                divine_text.apply(self.page, True)
        return self.page

    def showEvent(self, event):
        super().showEvent(event)
        if self.page is None:
            # After the tab switch is handled; the note is drawn first.
            QTimer.singleShot(0, self._build_shown)

    def _build_shown(self):
        try:
            if self.page is not None or not self.isVisible():
                return
            from .busy import busy
            with busy(self, self._busy_title):
                self.ensure()
        except RuntimeError:
            pass                           # window closed meanwhile


class OverviewTab(QWidget):
    open_grid = pyqtSignal(str)
    refresh_requested = pyqtSignal()
    share_requested = pyqtSignal()
    goal_changed = pyqtSignal()        # the JLPT goal was set / changed / removed (goal_view)
    # Debug ±250 rank preview crossed in or out of gold mode (Kanji tab bars).
    gold_preview = pyqtSignal(bool)

    _add_delta = _overview_add_delta

    def __init__(self, results: dict, deck_name: str = "", parent=None):
        super().__init__(parent)
        self._results   = results
        self._deck_name = deck_name
        # DEBUG offset persists across Refresh so preview state survives rebuild.
        self._rank_debug_offset = 0
        # Edge-trigger tracking for the Amaterasu popup.
        # _rank_real_prev_was_max: whether the REAL count was already at max the
        #   last time we checked — used to fire popup only on the crossing edge,
        #   not on every build while sitting at/above 20,000.
        # _rank_debug_prev_was_max: same thing but for the debug-simulated count,
        #   so nudging back below and then above 20,000 re-fires the popup.
        self._rank_real_prev_was_max  = None   # None = "not yet checked"
        self._rank_debug_prev_was_max = None
        # Frequency Check details open/closed — persists across Refresh.
        self._build()

    def update_results(self, results: dict, deck_name: str = None):
        """Rebuild the progress bars with freshly computed results.
        deck_name is optional — pass it when the deck might have changed,
        otherwise the previously-set deck name is reused."""
        self._results = results
        if deck_name is not None:
            self._deck_name = deck_name
        # Delete ALL child widgets first so no orphaned buttons remain
        # visible as floating ghosts over the rebuilt layout.
        for child in self.findChildren(QWidget):
            child.hide()
            child.deleteLater()
        old_layout = self.layout()
        if old_layout is not None:
            # Drain items (already deleted above) then detach
            while old_layout.count():
                old_layout.takeAt(0)
            QWidget().setLayout(old_layout)
        self._build()

    def _build(self):
        # The overview can be taller than the window — wrap everything in a
        # scroll area so the user can scroll down to the rank section.
        page_layout = QVBoxLayout(self)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        inner = QWidget()
        page = QVBoxLayout(inner)
        page.setSpacing(12)
        page.setContentsMargins(8, 8, 8, 8)

        scroll.setWidget(inner)
        self._scroll = scroll                 # _scroll_to_badge (ascension)
        page_layout.addWidget(scroll)

        # Section cards (owner 2026-10-18): JLPT Vocabulary, Rank, Frequency.
        outer = _section_card(page)
        note_row = QHBoxLayout()
        vtitle = QLabel("<b>JLPT Vocabulary</b>")
        vtitle.setStyleSheet(SECTION_CSS)
        note_row.addWidget(vtitle)
        note_row.addSpacing(10)
        note = QLabel("Click any bar to open that level's word grid.")
        note.setStyleSheet(HINT_CSS)
        note_row.addWidget(note)
        note_row.addStretch()
        refresh_btn = QPushButton("⟳")
        refresh_btn.setObjectName("kicon")
        refresh_btn.setToolTip(
            "Refresh: recalculate progress to include any words you've\n"
            "marked as found or suspended since this was opened."
        )
        refresh_btn.clicked.connect(self.refresh_requested)
        note_row.addWidget(refresh_btn)
        outer.addLayout(note_row)

        # Compute the rank/belt state FIRST: every JLPT bar below needs to
        # know is_max_amaterasu before it's constructed, since reaching
        # Black Belt Amaterasu (20,000 cards) turns every bar in the
        # add-on except the belt bar bright gold.
        real_total = count_deck_notes(self._deck_name)
        self._rank_real_total = real_total
        if _DEBUG_FULL["on"]:           # Force Amaterasu stays exactly at the top
            self._rank_debug_offset = rank_data.MAX_CARDS - real_total
        total_cards = max(0, real_total + self._rank_debug_offset)
        info = rank_data.get_rank_info(total_cards)
        force_max_gold = info["is_max_amaterasu"]

        # Edge-trigger: fire the popup the moment the REAL count crosses
        # into max (19,999 → 20,000). Pass is_max based on REAL total only —
        # never mix in the debug offset, which would corrupt the real tracker.
        real_is_max = rank_data.get_rank_info(real_total)["is_max_amaterasu"]
        self._check_amaterasu_crossing(real_is_max, is_debug=False)
        # The debug track starts from what's previewed now, so the first
        # Force Amaterasu / +250 into 20,000 is a crossing too (it was None
        # here, and None → max didn't count: owner 2026-10-16).
        self._rank_debug_prev_was_max = force_max_gold

        all_known = sum(len(self._results[l]["known_words"]) for l in LEVELS)
        all_total = sum(
            len(self._results[l]["known_words"]) + len(self._results[l]["missing_words"])
            for l in LEVELS
        )

        # Known = matched by a card (nid) or marked found (nid None); the
        # split line under the All bar and each tooltip spell it out, like
        # the frequency and rank lines (split_html).
        show_loans = bool(card_state.found_extra(self._deck_name)["loans"])

        def _split(known_words):
            loans, hand = _found_loans_jlpt(known_words)
            return split_html(len(known_words), "known", len(known_words) - loans - hand,
                              loans, hand, show_loans)

        def _known_tip(name, known_words, total):
            return (f"{name}: {len(known_words):,} of {total:,} known\n"
                    + _split(known_words).replace("<b>", "").replace("</b>", "")
                    + "\nClick to open the word grid")

        all_words = [w for l in LEVELS for w in self._results[l]["known_words"]]
        outer.addWidget(QLabel("<b>All N Levels Combined</b>"))
        all_bar = LevelBar("All", all_known, all_total, force_max_gold=force_max_gold)
        all_bar.setToolTip(_known_tip("All levels", all_words, all_total))
        all_bar.clicked.connect(self.open_grid)
        outer.addWidget(all_bar)
        self._all_bar = all_bar
        jlpt_split = QLabel(_split(all_words))
        jlpt_split.setAlignment(Qt.AlignmentFlag.AlignCenter)
        jlpt_split.setStyleSheet(BODY_CSS + " color: #cccccc;")
        outer.addWidget(jlpt_split)
        self._add_delta(outer, "jlpt", "#ffffff", "JLPT words known (all levels)")

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #444; margin: 4px 0;")
        outer.addWidget(sep)

        self._level_bars = []
        self._level_labels = []
        self._level_signs = []
        # The N5–N1 labels are neon signs on a strip of wall (owner 2026-10-22)
        wall = _SignWall()
        self._sign_wall = wall
        wall_l = QVBoxLayout(wall)
        wall_l.setContentsMargins(0, SIGN_STEEL, 0, 0)     # room for the box's top edge
        wall_l.setSpacing(SIGN_GAP)                         # the rows are taller instead (LevelSign)
        for lvl in LEVELS:
            d     = self._results[lvl]
            known = len(d["known_words"])
            total = known + len(d["missing_words"])
            row_w = QWidget()
            row_l = QHBoxLayout(row_w)
            row_l.setContentsMargins(0, 0, 0, 0)
            row_l.setSpacing(4)
            sign = LevelSign(lvl)
            row_l.addWidget(sign)
            bar = LevelBar(lvl, known, total, force_max_gold=force_max_gold)
            bar.setToolTip(_known_tip(lvl, d["known_words"], total))
            bar.clicked.connect(self.open_grid)
            row_l.addWidget(bar)
            wall_l.addWidget(row_w)
            self._level_bars.append(bar)
            self._level_signs.append(sign)
        wall_l.addSpacing(REFLECTION_ROOM)          # N1's reflection, like wet pavement
        outer.addWidget(wall)

        self._set_level_label_gold(force_max_gold)

        # ── JLPT goal (goal.py, owner 2026-10-20): per-day numbers to the test
        from .goal_view import add_goal_card
        add_goal_card(page, self)

        # ── Vocabulary Rank System ──────────────────────────────────────
        outer = _section_card(page)
        rank_hdr_row = QHBoxLayout()
        rank_hdr = QLabel("<b>Kotodama 言霊 Japanese Rank</b>")
        rank_hdr.setStyleSheet(SECTION_CSS)
        rank_hdr_row.addWidget(rank_hdr)
        # "?" and "Share image…" right after the title, like the Frequency
        # Check's "?" (owner 2026-10-20; they sat at the far right).
        info_btn = QPushButton("?")
        info_btn.setObjectName("kicon")      # the theme's icon button, gold in Amaterasu mode
        info_btn.setToolTip("About the Kotodama 言霊 Japanese Rank")
        info_btn.setStyleSheet("font-weight: bold;")
        info_btn.clicked.connect(lambda: _show_rank_info_dialog(self))
        share_btn = QPushButton("Share image…")
        share_btn.setToolTip("Make a picture of your progress to share: your name, rank, "
                             "belt, the JLPT levels and the 20,000-word bar")
        share_btn.clicked.connect(self.share_requested)
        rank_hdr_row.addWidget(info_btn)
        rank_hdr_row.addWidget(share_btn)
        # Time with Kotodama (loyalty.py): the tier's gem + "Jade · 6 months
        # with Kotodama", beside the rank but separate from it; hidden before
        # the first month.
        rank_hdr_row.addSpacing(16)
        self._loyal_icon = QLabel()
        self._loyal_icon.setFixedSize(28, 28)        # room for Sun Diamond's rays; text stays put
        self._loyal_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._loyal_lbl = QLabel()
        self._loyal_lbl.setStyleSheet("color: #b0b0b0; font-size: 12px; font-weight: 600;")
        rank_hdr_row.addWidget(self._loyal_icon)
        rank_hdr_row.addWidget(self._loyal_lbl)
        self._update_loyalty()
        rank_hdr_row.addStretch()
        outer.addLayout(rank_hdr_row)

        rank_sub = QLabel(
            "Counts every card you've studied in the selected deck, plus every word "
            "you've marked as found, toward 20,000 — "
            "the vocabulary size associated with native-like fluency. "
            "New cards count once you study them, like the JLPT bars and goal."
        )
        rank_sub.setWordWrap(True)
        rank_sub.setStyleSheet(HINT_CSS)
        outer.addWidget(rank_sub)
        count_all = card_state.debug_count_all()
        if count_all:
            warn = QLabel("DEBUG: the rank is counting every note in the deck, learned or not "
                          "(Count all notes is on). Progress history still uses the real count.")
            warn.setWordWrap(True)
            warn.setStyleSheet("color: #ff6b6b; font-size: 12px; font-weight: bold;")
            outer.addWidget(warn)

        # DEBUG nudge buttons: hidden until the invisible switch at the left
        # of this row is clicked (owner 2026-10-10). Stays as set until restart.
        debug_line = QHBoxLayout()
        debug_line.setSpacing(0)
        secret = QPushButton()
        secret.setFixedSize(28, 22)
        secret.setFlat(True)
        secret.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        secret.setStyleSheet("QPushButton, QPushButton:hover, QPushButton:pressed "
                             "{ background: transparent; border: none; }")
        secret.setProperty("jlpt_gold_skip", True)   # no gold border in Amaterasu mode
        debug_line.addWidget(secret)
        debug_box = QWidget()
        debug_box.setVisible(_DEBUG_ROW["shown"])
        debug_line.addWidget(debug_box, 1)

        def _toggle_debug():
            _DEBUG_ROW["shown"] = not _DEBUG_ROW["shown"]
            debug_box.setVisible(_DEBUG_ROW["shown"])
        secret.clicked.connect(_toggle_debug)

        debug_row = QHBoxLayout(debug_box)
        debug_row.setContentsMargins(0, 0, 0, 0)
        debug_lbl = QLabel("Debug preview:")
        debug_lbl.setStyleSheet(HINT_CSS)
        debug_row.addWidget(debug_lbl)
        left_btn = QPushButton("◀ -250")
        left_btn.setToolTip("Preview 250 fewer cards (display only)")
        left_btn.setMinimumWidth(80)
        left_btn.clicked.connect(lambda: self._nudge_rank(-250))
        debug_row.addWidget(left_btn)
        right_btn = QPushButton("+250 ▶")
        right_btn.setToolTip("Preview 250 more cards (display only)")
        right_btn.setMinimumWidth(80)
        right_btn.clicked.connect(lambda: self._nudge_rank(250))
        debug_row.addWidget(right_btn)
        loyal_btn = QPushButton("Loyalty ▶")
        loyal_btn.setToolTip("Preview the next 'time with Kotodama' tier: real → 1 month → … → "
                             "5 years → real (display only; the share image and your own "
                             "Nakama card follow it, nothing is sent)")
        loyal_btn.clicked.connect(self._cycle_loyalty)
        debug_row.addWidget(loyal_btn)
        mark_btn = QPushButton("★ Mark All JLPT Found")
        mark_btn.setToolTip(
            "DEBUG: instantly mark every word, kanji and grammar point on the JLPT lists "
            "as 'found' via the overrides system. Useful for previewing "
            "the fully-complete grids and progress bars."
        )
        mark_btn.setStyleSheet(
            "color: #ffe066; font-size: 10px; padding: 2px 8px;"
        )
        mark_btn.clicked.connect(self._mark_all_jlpt_found)
        debug_row.addWidget(mark_btn)
        all_btn = QPushButton("Count all notes")
        all_btn.setCheckable(True)
        all_btn.setChecked(count_all)
        all_btn.setToolTip(
            "DEBUG: the rank counts every note in the deck, not only learned "
            "(young / mature) ones, so a test deck of 20,000 new cards shows "
            "Amaterasu mode. Applies to the Overview, the main-screen widget "
            "and rank-up toasts; saved until you turn it off. Progress history "
            "always uses the real count.")
        all_btn.setStyleSheet(
            "QPushButton { font-size: 10px; padding: 2px 8px; }"
            "QPushButton:checked { color: #ff6b6b; border: 1px solid #ff6b6b; font-weight: bold; }")
        all_btn.toggled.connect(self._set_count_all)
        debug_row.addWidget(all_btn)
        force_btn = QPushButton("☀ Force Amaterasu")
        force_btn.setCheckable(True)
        force_btn.setChecked(_DEBUG_FULL["on"])
        force_btn.setToolTip(
            "DEBUG: preview Amaterasu mode with every bar full (JLPT, frequency, "
            "kanji and grammar). Display only; nothing is saved, and it turns off "
            "when Anki restarts.")
        force_btn.setStyleSheet(
            "QPushButton { font-size: 10px; padding: 2px 8px; }"
            "QPushButton:checked { color: #ffd700; border: 1px solid #ffd700; font-weight: bold; }")
        force_btn.toggled.connect(self._set_force_amaterasu)
        debug_row.addWidget(force_btn)
        for label, to_rank in (("Test belt-up toast", False), ("Test rank-up toast", True)):
            toast_btn = QPushButton(label)
            toast_btn.setToolTip(
                "DEBUG: show the review-time rank-up message as if a card "
                "had just been studied past the next "
                + ("rank" if to_rank else "belt") + " (uses the previewed count).")
            toast_btn.setStyleSheet("font-size: 10px; padding: 2px 8px;")
            toast_btn.clicked.connect(lambda _=False, r=to_rank: self._test_rank_toast(r))
            debug_row.addWidget(toast_btn)
        debug_row.addStretch()
        outer.addLayout(debug_line)

        # ── Rank progress bars ABOVE the badge ───────────────────────────
        self._rank_bar = RankBar(info)
        outer.addWidget(self._rank_bar)

        self._belt_bar = BeltBar(info)
        outer.addWidget(self._belt_bar)

        # What the rank is made of (owner: like the frequency line) — learned
        # cards + words marked found. Updated by the debug ±250 too.
        self._rank_split = QLabel()
        self._rank_split.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._rank_split.setStyleSheet(BODY_CSS + " color: #cccccc;")
        self._rank_split.setToolTip("Your rank counts studied (learning, young or mature) cards plus "
                                    "every word you've marked as found")
        self._set_rank_split(info["count"])
        outer.addWidget(self._rank_split)

        # This week / month, from the progress history (History tab).
        self._add_delta(outer, "rank", "#ff5c8a", "learned notes (the rank count)")

        # ── Rank badge (art + title) below the bars ───────────────────────
        self._rank_badge = RankBadge(info)
        # Clicking her badge replays the ascension (flash, then the message).
        self._rank_badge.clicked.connect(lambda: _ascend(self))
        outer.addWidget(self._rank_badge)

        # ── Frequency check (below the rank) ─────────────────────────────
        self._freq_bars = []
        self._freq_labels = []
        self._build_frequency_section(page, force_max_gold)
        self._set_level_label_gold(force_max_gold)

        # Amaterasu mode: the last share message, engraved (built-in message
        # until one is written). Shown/hidden with gold mode.
        from . import share_card
        self._inscription = _Inscription(share_card.saved_message() or _AMATERASU_MESSAGE_JP)
        self._inscription.setVisible(force_max_gold)
        page.addWidget(self._inscription)

        page.addStretch()

        # Amaterasu light over the whole page (idle below Amaterasu; follows
        # the debug ±250 preview through the badge).
        self._divine_overlay = DivineOverlay(inner, self._rank_badge)
        # Tell the dialog (gold tab frame) and the Kanji tab after a rebuild.
        self.gold = force_max_gold
        self.gold_preview.emit(force_max_gold)

    def _build_frequency_section(self, outer: QVBoxLayout, force_max_gold: bool):
        """How many of the deck's words are COMMON words. The rank counts
        every card; this shows whether those cards are the words that
        actually matter, using the BCCWJ written-Japanese frequency list."""
        freq = self._results.get("frequency") or {}
        if not freq.get("available"):
            return

        outer = _section_card(outer)          # its own section card
        # Redesigned for three bars (owner 2026-10-20): a headline coverage
        # number, one ladder smallest first, one stats line, the long
        # explanation behind "?".
        target   = freq_data.TIERS[-1]
        tiers    = dict(freq["tiers"])
        in_top   = freq["notes_in_top"].get(target, 0)
        total    = freq["notes_total"]
        coverage = freq["text_coverage"] * 100

        head = QHBoxLayout()
        head_l = QVBoxLayout()
        head_l.setSpacing(2)
        title_row = QHBoxLayout()
        fhdr = QLabel("<b>Frequency Check</b>")
        fhdr.setStyleSheet(SECTION_CSS)
        title_row.addWidget(fhdr)
        info_btn = QPushButton("?")
        info_btn.setObjectName("kicon")
        info_btn.setStyleSheet("font-weight: bold;")
        info_btn.setToolTip("About the Frequency Check")
        info_btn.clicked.connect(lambda: _show_freq_info_dialog(self))
        title_row.addWidget(info_btn)
        title_row.addStretch()
        head_l.addLayout(title_row)
        sub = QLabel("The most common words in written Japanese, and how many you know.")
        sub.setWordWrap(True)
        sub.setStyleSheet(HINT_CSS)
        head_l.addWidget(sub)
        head.addLayout(head_l, 1)
        cov_l = QVBoxLayout()
        cov_l.setSpacing(0)
        cov_num = QLabel(f"<span style='font-size:24px; font-weight:bold; color:{FREQ_FG};'>"
                         f"{coverage:.1f}%</span>")
        cov_num.setAlignment(Qt.AlignmentFlag.AlignRight)
        cov_num.setToolTip("Your known words make up about this share of the words in everyday "
                           "written Japanese (weighted by how often each word is used).")
        cov_sub = QLabel("of everyday written text")
        cov_sub.setAlignment(Qt.AlignmentFlag.AlignRight)
        cov_sub.setStyleSheet(HINT_CSS)
        cov_l.addWidget(cov_num)
        cov_l.addWidget(cov_sub)
        head.addLayout(cov_l)
        outer.addLayout(head)

        colors = (FREQ_FG, FREQ_BG)
        # Clicking a frequency bar opens a grid of its words; the "freq:N"
        # level string tells ProgressDialog how many ranks to show.
        # Suspended words leave the totals (tier_totals), like the JLPT bars.
        totals = freq.get("tier_totals", {})
        details = QWidget()
        dl = QVBoxLayout(details)
        dl.setContentsMargins(0, 0, 0, 0)
        dl.setSpacing(0)

        # One ladder, largest first (owner 2026-10-20): Near Native 20,000
        # right under the rank card, so the two 20,000 bars can be compared
        # (how many of your learned words are common words), then Top 13,800
        # (the N1 size) and Top 6,000 (the N2 size). Each bar's tooltip still
        # gives its own band (#13,801–20,000 …).
        ladder = freq_data.BAR_TIERS + [target]                  # smallest first
        below = {n: (ladder[i - 1] if i else 0) for i, n in enumerate(ladder)}
        for n in reversed(ladder):
            known = tiers.get(n, 0)
            prev_n = below[n]
            prev_known = tiers.get(prev_n, 0) if prev_n else 0
            prev_total = totals.get(prev_n, prev_n) if prev_n else 0
            row_w = QWidget()
            row_l = QHBoxLayout(row_w)
            row_l.setContentsMargins(0, 0, 0, 0)
            row_l.setSpacing(10)
            if n == target:
                name = freq_data.TIER_NAMES[target]
                label = f"{name}<br><span style='font-size:9px; letter-spacing:1px;'>{n:,}</span>"
            else:
                # Captioned with the size it follows (owner 2026-10-20: the
                # bars exist because they're the N2 / N1 sizes; the words
                # still aren't the test's).
                name = f"Top {n:,}"
                label = (f"Top {n:,}<br><span style='font-size:9px; letter-spacing:1px;'>"
                         f"{freq_data.TIER_LEVEL[n]} size</span>")
            lbl = QLabel()
            lbl.setFixedWidth(84)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setToolTip(f"{freq_data.tier_description(n)} — about {n:,} words")
            self._freq_labels.append((label, lbl))
            row_l.addWidget(lbl)
            total_n = totals.get(n, n)
            bar = LevelBar(f"freq:{n}", known, total_n, force_max_gold=force_max_gold,
                           colors=colors)
            bar.clicked.connect(self.open_grid)
            band_known, band_size = known - prev_known, total_n - prev_total
            bar.setToolTip(
                f"{freq_data.tier_description(n)}\n"
                f"{name}: {known:,} / {total_n:,} known (cumulative)  ·  "
                f"words #{prev_n + 1:,}–{n:,}: {band_known:,} / {band_size:,}\n"
                f"{freq['notes_in_top'].get(n, 0):,} of your {total:,} cards have a word in the top {n:,}"
                + (f"\n{n - total_n:,} suspended (not counted)" if total_n < n else "")
                + "\nClick to see these words"
            )
            row_l.addWidget(bar)
            dl.addWidget(row_w)
            self._freq_bars.append(bar)
            if n == target:
                self._add_rank_ratio(dl, bar, known)
        dl.addSpacing(REFLECTION_ROOM)              # the last tube's reflection

        # One stats line: known words (cards + marked found) and the gain.
        # (The card count moved into the bars' tooltips: it counts cards,
        # not words, and next to the word counts it confused.)
        known_top = tiers.get(target, 0)
        found_top = [r for r in freq.get("found_ranks", ()) if r < target]
        by_rank = {e[0] - 1: e for e in freq.get("entries", ())}
        loans_top = sum(1 for r in found_top
                        if r in by_rank and freq_data.is_english_loanword(by_rank[r][1], by_rank[r][2]))
        from .history_view import delta_html
        gain = delta_html(self._results.get("history_series"), f"f{target}", "#a8e6ff", "#cccccc")
        stats = QLabel(
            split_html(known_top, "known", known_top - len(found_top), loans_top,
                       len(found_top) - loans_top,
                       bool(card_state.found_extra(self._deck_name)["loans"]))
            + (f" &nbsp;·&nbsp; {gain}" if gain else "")
        )
        stats.setToolTip(
            f"{in_top:,} of your {total:,} cards match a top-{target:,} word.\n"
            "Words and cards aren't always one-to-one, so the two numbers can differ:\n"
            "• several cards can be one word (所 + ところ, 出来る + できる, duplicate cards)\n"
            "• one card can be two list words (明後日 also covers the kana-written あさって row)\n"
            "• a sentence card counts every listed word in its sentence")
        stats.setWordWrap(True)
        stats.setStyleSheet(BODY_CSS + " color: #cccccc; margin-top: 4px;")
        if gain:
            from .history_view import connect_gain_links
            connect_gain_links(stats, lambda: self._results.get("history_series"))
        dl.addWidget(stats)

        miss_lbl = QLabel(
            "<b>Most common words not in your deck</b> "
            "<span style='color:#888; font-size:12px;'>— click to copy · Shift+Click to look up on Jisho</span>"
        )
        miss_lbl.setStyleSheet("margin-top: 10px;")
        miss_row = QHBoxLayout()
        miss_row.addWidget(miss_lbl)
        miss_row.addStretch()
        # Owner 2026-10-20: optional, off by default, remembered.
        from . import _cfg, _save
        hide_cb = QCheckBox("Hide other spellings and readings of words you know")
        hide_cb.setChecked(bool(_cfg().get("freq_hide_variants", False)))
        hide_cb.setToolTip("Leaves out tiles that are another reading of a word you know "
                           "(私 わたくし when you know 私 わたし, 月 がつ) and the split tiles "
                           "whose main word you know (聴く beside 聞く, 在る beside 有る, "
                           "診る / 観る / 看る beside 見る).\nThey're still in the grid and still counted.")
        hide_cb.setStyleSheet("font-size: 12px; margin-top: 10px;")
        miss_row.addWidget(hide_cb)
        dl.addLayout(miss_row)
        miss = QListWidget()
        miss.setFlow(QListView.Flow.LeftToRight)
        miss.setWrapping(True)
        miss.setResizeMode(QListView.ResizeMode.Adjust)
        miss.setSpacing(4)
        miss.setFixedHeight(150)
        miss.setProperty("jlpt_gold_list", True)     # gold chips in gold mode (divine_text)

        def fill_missing():
            miss.clear()
            rows = freq.get("missing_lean", freq["missing"]) if hide_cb.isChecked() else freq["missing"]
            for rank, display, reading in rows:
                # Show the reading for kanji words — it explains homographs like
                # 私（わたくし）showing as missing when you know 私（わたし）.
                k = _kanji_form(display, reading)
                shown = (f"{display}（{reading}）" if reading != display
                         else f"{display} 〔{k}〕" if k else display)
                item = QListWidgetItem(f"#{rank:,}  {shown}")
                item.setToolTip(_meaning_tip(display, reading) + f"<br><br>Rank {rank:,}"
                                if meanings.lookup(display, reading)
                                else f"{display}【{reading}】  —  rank {rank:,}")
                item.setData(Qt.ItemDataRole.UserRole, display)
                item.setData(Qt.ItemDataRole.UserRole + 1, reading)
                miss.addItem(item)
            _regold(miss)

        def on_hide(on):
            c = _cfg()
            c["freq_hide_variants"] = bool(on)
            _save(c)
            fill_missing()

        fill_missing()
        hide_cb.toggled.connect(on_hide)
        miss.itemClicked.connect(
            lambda it: _copy_or_jisho(it.data(Qt.ItemDataRole.UserRole), self.window(),
                                      it.data(Qt.ItemDataRole.UserRole + 1) or "")
        )
        dl.addWidget(miss)

        src = QLabel(
            "Source: BCCWJ (Balanced Corpus of Contemporary Written Japanese, NINJAL) — "
            "top 20,000 content words; particles, numerals and proper nouns excluded."
        )
        src.setWordWrap(True)
        src.setStyleSheet(HINT_CSS + " margin-top: 2px;")
        dl.addWidget(src)
        outer.addWidget(details)

    def _add_rank_ratio(self, layout, bar, common: int):
        """Rank vs common words (owner 2026-10-20): the rank shown as a pale
        ghost on the Near Native bar, and the share of your learned words
        that are among the 20,000 most common in written Japanese. Not a
        quality score: names, slang, words newer than the corpus and genre
        words fall outside it, and immersion learners will have more."""
        rank = getattr(self, "_rank_real_total", 0) or 0
        if rank <= 0:
            return
        bar.set_ghost(rank)
        # Like with like: marked loanwords the rank doesn't count yet (they
        # join on a schedule) are on the bar but not in the rank (2026-10-21).
        pending = card_state.loans_not_yet_counted(rank, card_state.found_extra(self._deck_name))
        common = max(0, common - pending)
        pct = min(100, round(common / rank * 100))
        outside = max(0, rank - common)
        pale = "#9fd8f2"
        ratio = QLabel(
            f"<b style='color:{FREQ_FG}; font-size:16px;'>{pct}%</b> of your learned words are "
            f"among the 20,000 most common in written Japanese &nbsp;·&nbsp; {outside:,} are outside it "
            f"(names, slang, words newer than the corpus like スマホ, genre words, other spellings)")
        ratio.setWordWrap(True)
        # lined up with the bar (label column 84 + spacing 10 + the bar's own inset)
        ratio.setStyleSheet(BODY_CSS + f" color: #cccccc; margin: 0 {LevelBar._PAD}px 2px {94 + LevelBar._PAD}px;")
        ratio.setToolTip(
            "The frequency list comes from written Japanese of about 1976–2006, so spoken, newer and "
            "genre vocabulary ranks lower than you'd hear it. A lower share isn't worse: it shows how "
            "much of your vocabulary is written-Japanese core.\n"
            "About: the rank counts cards and marked words, this bar counts words (duplicate cards, "
            "one card for two spellings), so the match is approximate."
            + (f"\n{pending:,} marked English loanwords the rank doesn't count yet are left out "
               "here (they join the rank as your vocabulary reaches them)." if pending else ""))
        legend = QLabel(
            f"<span style='color:{FREQ_FG};'>■</span> common words you know &nbsp;&nbsp; "
            f"<span style='color:{pale};'>■</span> your rank: {rank:,} words learned")
        legend.setStyleSheet(HINT_CSS + f" margin: 0 {LevelBar._PAD}px 8px {94 + LevelBar._PAD}px;")
        legend.setToolTip(ratio.toolTip())
        layout.addWidget(ratio)
        layout.addWidget(legend)

    def _set_level_label_gold(self, gold: bool):
        """Tint the N5/N4/N3/N2/N1 level labels gold (with a soft glow) when
        Black Belt Amaterasu is active, matching the bars themselves; revert
        to each level's normal color otherwise."""
        gold_color = rank_data.MAX_RANK_FILL_COLOR        # "#f5c518"
        glow_color = rank_data.RANK_COLORS["Amaterasu"][1]  # light accent gold
        # (text, label, normal colour, font size) — the N5–N1 labels plus the
        # Frequency Check tier labels ("N5 / 800" …), which may not exist yet.
        for sign in getattr(self, "_level_signs", []):
            sign.set_gold(gold)
        if getattr(self, "_sign_wall", None) is not None:
            self._sign_wall.set_gold(gold)
        labels = [(lvl, lbl, LEVEL_FG[lvl], 16) for lvl, lbl in self._level_labels]
        labels += [(text, lbl, FREQ_FG, 12) for text, lbl in getattr(self, "_freq_labels", [])]
        for text, lbl, normal_color, size in labels:
            color = gold_color if gold else normal_color
            lbl.setText(f"<span style='color:{color}; font-size:{size}px;'><b>{text}</b></span>")
            if gold:
                shadow = QGraphicsDropShadowEffect(lbl)
                shadow.setBlurRadius(10)
                shadow.setOffset(0, 0)
                shadow.setColor(QColor(glow_color))
                lbl.setGraphicsEffect(shadow)
            else:
                lbl.setGraphicsEffect(None)


    def _update_loyalty(self):
        """The Vocabulary tab's time-with-Kotodama gem and line (loyalty.py)."""
        from . import loyalty
        if not hasattr(self, "_loyal_lbl"):
            return
        months, sun = loyalty.shown_months(), loyalty.shown_sun()
        i = loyalty.tier_index(months, sun)
        self._loyal_icon.setVisible(i is not None)
        self._loyal_lbl.setVisible(i is not None)
        if i is None:
            return
        self._loyal_icon.setPixmap(loyalty.gem_pixmap(20, i))
        self._loyal_lbl.setText(loyalty.line(months, sun=sun))
        nxt = loyalty.next_step(months, sun=sun)
        self._loyal_lbl.setToolTip("Time with Kotodama: months in which you used the add-on at least "
                                   "once. It never goes down." + (f"\n{nxt}." if nxt else ""))
        self._loyal_icon.setToolTip(self._loyal_lbl.toolTip())
        if _GOLD_MODE["on"]:
            from . import divine_text
            divine_text.apply(self._loyal_lbl, True)

    def _cycle_loyalty(self):
        """Debug row: preview the next loyalty tier (display only)."""
        from . import loyalty
        loyalty.cycle_preview()
        self._update_loyalty()

    def _nudge_rank(self, delta: int):
        """Shift the previewed card count by `delta` (±250) and repaint
        every bar live. Uses the same edge-triggered crossing logic as the
        real card count, so nudging through 20,000 fires the Amaterasu popup
        just like actually reaching 20,000 cards — and nudging back below and
        then above again re-fires it, which is exactly what you want for QA."""
        self._rank_debug_offset += delta
        total_cards = max(0, self._rank_real_total + self._rank_debug_offset)
        info = rank_data.get_rank_info(total_cards)
        force_max_gold = info["is_max_amaterasu"]

        self._rank_badge.update_info(info)
        self._rank_bar.update_info(info)
        self._belt_bar.update_info(info)
        self._set_rank_split(info["count"])
        self._all_bar.set_force_max_gold(force_max_gold)
        for bar in self._level_bars + self._freq_bars:
            bar.set_force_max_gold(force_max_gold)
        self._set_level_label_gold(force_max_gold)
        self._inscription.setVisible(force_max_gold)
        # Only on a gold flip: the dialog's gold pass restyles the whole
        # window (~1.2 s), which made every ±250 click lag (owner 2026-10-24).
        if force_max_gold != self.gold:
            self.gold = force_max_gold
            self.gold_preview.emit(force_max_gold)

        # Fire popup on the crossing edge (debug track, independent of real).
        self._check_amaterasu_crossing(
            info["is_max_amaterasu"], is_debug=True
        )

    def _mark_all_jlpt_found(self):
        """DEBUG: mark every word across all JLPT level lists as 'found' via
        the overrides system, so you can preview the fully-complete state of
        the word grid and progress bars without having 20,000 real cards.

        This does exactly what middle-clicking every tile would do, writing
        to overrides.json immediately. Hit Refresh afterward to recompute
        results and see the bars update."""
        # OverviewTab doesn't hold a direct reference to overrides or lists —
        # walk up to the parent ProgressDialog to get them.
        dlg = self.parent()
        while dlg is not None and not hasattr(dlg, "_overrides"):
            dlg = dlg.parent()
        if dlg is None:
            return
        overrides = dlg._overrides
        lists     = dlg._lists
        overrides.add_found_many(
            pair for lvl in LEVELS for pair in lists.get(lvl, [])
        )
        # … and every JLPT kanji and grammar point (owner 2026-10-09), so the
        # Kanji & Grammar tab can be previewed complete too.
        from . import grammar_data
        kres = (dlg._results or {}).get("kanji") or {}
        dlg._kanji_overrides.add_found_many(
            (ch, "") for lvl in LEVELS for ch in kres.get("levels", {}).get(lvl, []))
        dlg._grammar_overrides.add_found_many(
            (gid, "") for ids in grammar_data.level_ids().values() for gid in ids)
        # Trigger a full refresh so the UI picks up the changes immediately.
        self.refresh_requested.emit()

    def _set_rank_split(self, total: int):
        """"3,411 counted = 3,160 from your cards + 251 English loanwords + 0
        marked found" (split_html; the debug ±250 offset shows up on the cards
        side). Marked loanwords join the rank on their schedule (card_state)."""
        extra = card_state.found_extra(self._deck_name)
        cards, loans = card_state.cards_for_rank(total, extra)
        self._rank_split.setText(
            split_html(total, "counted", cards, loans, extra["hand"], bool(extra["loans"])))
        if extra["loans"]:
            self._rank_split.setToolTip(
                f"{loans:,} of your {len(extra['loans']):,} English loanwords marked found count "
                "toward the rank so far. They join as your vocabulary reaches them: a loanword at "
                "frequency rank 8,000 counts once your rank reaches 8,000 (8,000 minus the "
                "loanwords already counted, in learned cards). The JLPT and frequency bars count "
                "them all at once.")
        else:
            self._rank_split.setToolTip("")
        _regold(self._rank_split)          # rewritten on ±250 after the gold pass

    def set_inscription(self, message: str):
        """A new share message was saved: engrave it (built-in one if empty)."""
        self._inscription.set_text(message or _AMATERASU_MESSAGE_JP)

    def _set_count_all(self, on: bool):
        """DEBUG: switch the rank between learned notes and every note
        (card_state.debug_count_all), then rebuild this tab and the main
        screen widget so both show the new count."""
        from . import _cfg, _save
        cfg = _cfg()
        cfg["debug_rank_count_all"] = bool(on)
        _save(cfg)
        self.refresh_requested.emit()
        if mw.state == "deckBrowser":
            mw.deckBrowser.refresh()

    def _set_force_amaterasu(self, on: bool):
        """DEBUG: jump the previewed count to exactly 20,000 (or back to the
        real count) and draw every bar full, everywhere in the window."""
        _DEBUG_FULL["on"] = bool(on)
        target = rank_data.MAX_CARDS if on else self._rank_real_total
        self._nudge_rank(target - (self._rank_real_total + self._rank_debug_offset))
        for bar in self.window().findChildren(LevelBar):
            bar.update()
        if mw.state == "deckBrowser":          # the main-screen widget too
            mw.deckBrowser.refresh()

    def _test_rank_toast(self, to_rank: bool):
        """DEBUG: show the rank-up toast for the next belt (or next main
        rank) above the currently previewed count, without reviewing."""
        from . import rank_toast
        count  = max(0, self._rank_real_total + self._rank_debug_offset)
        before = rank_data.get_rank_info(count)
        if before["is_max"]:
            target = rank_data.MAX_CARDS
        elif to_rank:
            nxt = (before["rank_index"] + 1) * rank_data.BELTS_PER_RANK
            target = (rank_data.BELT_THRESHOLDS[nxt]
                      if nxt < len(rank_data.BELT_THRESHOLDS) else rank_data.MAX_CARDS)
        else:
            target = before["belt_end"]
        after = rank_data.get_rank_info(target)
        rank_toast.show_toast(after, new_rank=after["rank_index"] > before["rank_index"],
                              parent=self.window())

    def _check_amaterasu_crossing(self, is_now_max: bool, is_debug: bool):
        """Fire the Amaterasu popup when the card count crosses INTO max.

        Two completely independent tracking paths:

        DEBUG (is_debug=True):
          Uses a pure in-memory tracker (_rank_debug_prev_was_max).
          Fires when nudging through 20,000; resets when nudging back below;
          re-fires on the next upward crossing. No persistence needed since
          the debug offset resets to 0 whenever the dialog is closed.

        REAL (is_debug=False):
          Must work across separate openings of the plugin — the user adds
          their 20,000th card, then opens the plugin fresh; there is no
          in-memory "prev" from a previous session. We solve this by
          persisting the last-known real card count in the add-on config.
          On each check we compare the CURRENT count against the stored
          previous count:
            - prev < 20,000 and now >= 20,000  →  crossing edge  →  fire
            - prev >= 20,000 already           →  already past   →  no fire
            - no stored prev (first ever open) →  no fire, just store
          After checking we always write the current count back so the
          next open has an accurate baseline.
        """
        if is_debug:
            prev = self._rank_debug_prev_was_max
            self._rank_debug_prev_was_max = is_now_max
            crossed = is_now_max and (prev is False)
            if crossed:
                _ascend(self)
            return

        # Real path: use persisted previous count from config
        MAX = rank_data.MAX_CARDS
        current_real = self._rank_real_total   # already read by _build()

        try:
            from . import _cfg, _save
            cfg = _cfg()
            prev_count = cfg.get("rank_last_real_count", None)

            # Detect crossing: was below max before, at/above max now
            if prev_count is not None and prev_count < MAX and current_real >= MAX:
                _ascend(self)

            # Always persist the current count for next time
            changed = cfg.get("rank_last_real_count") != current_real
            if changed:
                cfg["rank_last_real_count"] = current_real
            # Amaterasu reached for real at least once (never cleared, even if
            # the rank drops later): part of the Sun Diamond loyalty tier.
            # Never from the debug "Count all notes" switch (a test deck).
            if (current_real >= MAX and not cfg.get("amaterasu_reached")
                    and not card_state.debug_count_all()):
                import datetime as _dt
                cfg["amaterasu_reached"] = _dt.date.today().isoformat()
                changed = True
            if changed:
                _save(cfg)
        except Exception:
            pass


# ── Main progress dialog ──────────────────────────────────────────────────────

def _compute_kanji_into(results: dict, deck_name: str, analysis_inputs: dict,
                        kanji_overrides: Overrides, grammar_overrides: Overrides):
    """Kanji and grammar results for the Kanji & Grammar tab. A failure
    here must not take the word tabs down with it, so it's logged and
    that part of the tab skipped."""
    from . import _cfg
    from . import kanji_data, grammar_data
    import traceback
    cfg = _cfg()
    try:
        results["kanji"] = kanji_data.analyse(
            cfg, deck_name, analysis_inputs.get("nid_to_display", {}), kanji_overrides,
            new_notes=(results.get("new_cards") or {}).get("notes"))
    except Exception:
        traceback.print_exc()
        results["kanji"] = None
    if results.get("kanji"):
        # Kanji → words: common words with each kanji you don't know yet.
        try:
            from . import text_check
            results["kanji"]["learn"] = text_check.kanji_learn_index(results)
        except Exception:
            traceback.print_exc()
    try:
        results["grammar"] = grammar_data.analyse(cfg, grammar_overrides)
    except Exception:
        traceback.print_exc()
        results["grammar"] = None


class ProgressDialog(QDialog):
    def __init__(self, parent, results: dict, deck_name: str, lists: dict,
                 overrides: Overrides = None, analysis_inputs: dict = None,
                 extras: dict = None):
        super().__init__(parent)
        # Dialogs only get a close button by default on Windows — add
        # minimize/maximize like the pop-up grid windows.
        self.setWindowFlags(
            self.windowFlags()
            | Qt.WindowType.Window
            | Qt.WindowType.WindowMinMaxButtonsHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self.setWindowTitle(f"Kotodama 言霊 — {deck_name}")
        # Freed when closed: a closed window used to stay in memory, hidden,
        # one more for every open (found 2026-10-24).
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.resize(900, 680)
        self._results         = results
        self._deck_name       = deck_name
        self._lists           = lists
        _set_jlpt_levels(lists or {})
        self._overrides       = overrides or Overrides()
        self._analysis_inputs = analysis_inputs or {}
        self._refreshing = False
        if extras is None:
            # Not precomputed in the background: do it here.
            extras = self.compute_extras(results, deck_name, lists, self._analysis_inputs)
        self._kanji_overrides = extras["kanji_overrides"]
        self._grammar_overrides = extras["grammar_overrides"]
        self._history = extras["history"]
        self._build()
        attach_sky(self, moon=True)             # moon mode's night sky (owner 2026-10-25)
        # Kotodama's own theme, gold-accented (set now, so the window never
        # shows Anki's look first).
        from . import theme
        theme.apply(self, gold=bool(getattr(self._overview, "gold", False)))
        # Wide enough for every tab on one row (owner 2026-10-18), within
        # the screen.
        self._tabs.tabBar().ensurePolished()
        want = self._tabs.tabBar().sizeHint().width() + 80
        scr = self.screen().availableGeometry() if self.screen() else None
        if scr is not None:
            want = min(want, scr.width() - 40)
        # A little taller than the layout's minimum (which the 680 above
        # never reaches): the Kanji & Grammar tab's last bar, N1 grammar,
        # sat just below the edge (owner 2026-10-22).
        self.layout().activate()
        want_h = max(self.height(), self.minimumSizeHint().height()) + EXTRA_HEIGHT
        if scr is not None:
            want_h = min(want_h, scr.height() - 40)
        if want > self.width() or want_h > self.height():
            self.resize(max(want, self.width()), max(want_h, self.height()))

    @staticmethod
    def compute_extras(results: dict, deck_name: str, lists: dict, analysis_inputs: dict,
                       kanji_overrides: Overrides = None, grammar_overrides: Overrides = None,
                       manual_snapshot: bool = False) -> dict:
        """Everything after the word analysis: kanji and grammar (into
        results), the found-words count, today's history snapshot and the
        history series. No widgets are touched, so it runs off the main
        thread (Anki's QueryOp, under card_state.ANALYSIS_LOCK, which also
        keeps history.json writes one at a time)."""
        from .overrides import KANJI_PATH, GRAMMAR_PATH
        kanji_overrides = kanji_overrides or Overrides(KANJI_PATH)
        grammar_overrides = grammar_overrides or Overrides(GRAMMAR_PATH)
        # Never-studied cards: the grids' "New" tiles (display only).
        try:
            from . import new_card_words
            results["new_cards"] = new_card_words(results, deck_name, lists, analysis_inputs)
        except Exception:
            import traceback
            traceback.print_exc()
            results["new_cards"] = {"words": {}, "ranks": {}, "notes": {}}
        _compute_kanji_into(results, deck_name, analysis_inputs, kanji_overrides, grammar_overrides)
        # Words marked found count toward the rank (before anything reads it).
        card_state.set_found_extra(deck_name, card_state.found_parts(results))
        fm = analysis_inputs.get("field_mappings", [])
        ign = bool(analysis_inputs.get("ignore_suspended", False))
        history.record(results, deck_name, lists, fm, ign, manual=manual_snapshot)
        # The series after the record: today's snapshot is part of it.
        try:
            series = history.build_series(results, deck_name, lists, fm, ign)
        except Exception:
            series = None
        results["history_week"] = history.delta(series, "rank", 7) if series else None
        results["history_series"] = series
        # Your Nakama card (sent after Anki syncs, once you've joined).
        try:
            from . import nakama
            nakama.store_full(results, deck_name, ign, kanji_overrides, grammar_overrides)
        except Exception:
            import traceback
            traceback.print_exc()
        return {"kanji_overrides": kanji_overrides, "grammar_overrides": grammar_overrides,
                "history": series}

    def showEvent(self, event):
        super().showEvent(event)
        _watch_focus()                      # its sounds go quiet when it loses the focus
        if not getattr(self, "_fitted", False):
            self._fitted = True
            from . import theme
            QTimer.singleShot(0, lambda: theme.fit_on_screen(self))   # whole on screen (owner 2026-10-26)
        # Neon elements flicker on as they're first seen (_NEON; not in
        # Amaterasu mode, which has its own intro). Once per window.
        if getattr(self, "_intro_done", False):
            return
        self._intro_done = True
        # The day's word target reached: the Progress Review, once a day,
        # after the window's intro (owner 2026-10-27).
        QTimer.singleShot(REVIEW_POP_MS, self._maybe_review)
        if self._gold:
            return
        _INTRO["run"] += 1
        from . import effects
        _NEON.update(on=True, clock=0.0, last=None, batches=[], seq=0, sound_at=-1e9,
                     instant=not effects.animations_on())
        _NEON["seen_pages"] = set()
        # Veils and grid zones built before now drew themselves lit (no
        # neon window yet): show them unlit.
        for r in _NEON["items"]:
            w = r()
            if w is not None:
                try:
                    _neon_repaint(w)
                except RuntimeError:
                    pass
        # The selected tab's gold underline flickers on too: hide the style
        # sheet's line, draw it as a neon tube, put it back once it's lit.
        bar = self._tabs.tabBar()
        bar.setStyleSheet("QTabBar::tab:selected { border-bottom-color: transparent; }")
        underline = _TabUnderline(bar)

        def end_underline():
            try:
                underline.deleteLater()
                bar.setStyleSheet("")
            except RuntimeError:
                pass
        underline._neon_lit_cb = end_underline
        # First tick once the event loop is idle (the window has painted).
        QTimer.singleShot(0, _neon_wake)
        attach_rain(self)                   # rain on the glass (rain.py)

    def _maybe_review(self):
        try:
            if not self.isVisible():
                return
            from . import review
            if review.should_pop(self._results, self._deck_name):
                review.mark_popped()
                from .review_view import open_review
                open_review(self, self._results, self._deck_name, 7)
        except RuntimeError:
            pass                            # closed meanwhile
        except Exception:
            import traceback
            traceback.print_exc()           # never in the way of the window

    def done(self, result):
        # Every way of closing ends here (Close button → accept, Esc →
        # reject, the window's X → closeEvent → reject); closeEvent alone
        # missed the Close button.
        # Overrides (found/suspended) may have changed since this dialog was
        # opened — make sure the main-screen mini widget picks them up (and
        # any rank-up banner from the debug test buttons).
        from . import mini_widget, ambience
        from aqt import mw
        _neon_stop(self)                    # closed mid-flicker: nothing stays dark
        ambience.get().leave(fade_ms=700)   # the star goes quiet with the window
        mini_widget.invalidate_cache()
        if mw.state == "deckBrowser":
            mw.deckBrowser.refresh()
        super().done(result)

    def _build(self):
        outer = QVBoxLayout(self)

        # Title card, top centre (owner 2026-10-15: the add-on's name): two
        # neon signs that flicker on with the bars (owner 2026-10-20),
        # "Kotodama 言霊" and a red "JLPT Tracker".
        title_row = QHBoxLayout()
        title_row.setSpacing(6)
        title_row.addStretch()
        self._title_left = NeonTitle(TITLE_LEFT)
        self._title_right = NeonTitle(TITLE_RIGHT)
        sep = QLabel("|")
        sep.setStyleSheet("font-size: 18px; color: #555555;")
        title_row.addWidget(self._title_left)
        title_row.addWidget(sep)
        title_row.addWidget(self._title_right)
        title_row.addStretch()
        outer.addLayout(title_row)

        # The active deck(s), shown above every tab (owner 2026-10-18: the old
        # "JLPT Vocabulary Coverage" read as if it belonged to one tab).
        decks = [self._deck_name]
        try:
            from . import _cfg
            cfg = _cfg()
            for key in ("kanji_source", "grammar_source"):
                src = cfg.get(key) or {}
                if src.get("mode") == "fields" and src.get("deck") and src["deck"] not in decks:
                    decks.append(src["deck"])
        except Exception:
            pass
        hdr = QLabel(("Decks: " if len(decks) > 1 else "Deck: ")
                     + "  ·  ".join(f"<b>{html.escape(d)}</b>" for d in decks))
        hdr.setStyleSheet("font-size: 13px; color: #aaaaaa; padding: 4px 0 2px 0;")
        outer.addWidget(hdr)

        self._tabs = QTabWidget()
        self._tabs.setObjectName("kmaintabs")      # theme.py: no line along the top of its page (owner 2026-10-26)
        outer.addWidget(self._tabs)
        self._gold = False

        self._overview = OverviewTab(self._results, self._deck_name)
        self._overview.open_grid.connect(self._open_grid_for_level)
        self._overview.refresh_requested.connect(self._do_full_refresh)
        self._overview.gold_preview.connect(self._apply_gold)
        self._overview.share_requested.connect(self._open_share)
        self._overview.goal_changed.connect(self._on_goal_changed)
        self._tabs.addTab(self._overview, "Vocabulary")

        # Word Grid, Missing, Marked & Suspended and Off-list are built the
        # first time they're shown (_LazyTab; owner 2026-10-24: together
        # they were ~3 s of the ~4.5 s it took the window to open).
        self._grid_flat = self._missing_panel = self._ms_panel = None
        self._kanji_missing = self._grammar_missing = None
        self._kanji_ms = self._grammar_ms = self._unlisted_panel = None
        # Tables refreshed lazily after a mark (owner 2026-10-15: marking a
        # tile froze the grid ~4 s while all five were rebuilt): a hidden
        # table is rebuilt when it's next shown. Entries appear as their
        # tabs are built.
        self._dirty = set()
        self._lazy = {}
        self._show_watch = _ShowWatcher(self._flush_dirty, self)
        self._grid_windows = {}         # kept grid windows (_reuse_grid)
        self._grid_stale = set()

        def watch(name, widget, rebuild):
            self._lazy[name] = (widget, rebuild)
            widget.installEventFilter(self._show_watch)

        def build_grid():
            self._grid_flat = WordGridPanel(
                self._results, "All", self._overrides,
                flat=True, on_override_changed=self._on_override_changed
            )
            return self._grid_flat
        self._tabs.addTab(_LazyTab(build_grid, "Building the Word Grid…"), "Word Grid")

        # Missing and Marked & Suspended: a Vocab / Kanji / Grammar dropdown
        # on top of each (owner 2026-10-09).
        from .kanji_view import KindSwitcher, KGMissingPanel, KGOverridesPanel

        def build_missing():
            self._missing_panel = MissingWordsPanel(self._results)
            self._kanji_missing = KGMissingPanel("kanji", self._results.get("kanji"),
                                                 self._kanji_overrides)
            self._grammar_missing = KGMissingPanel("grammar", self._results.get("grammar"),
                                                   self._grammar_overrides)
            self._kanji_missing.changed.connect(self._on_override_changed)
            self._grammar_missing.changed.connect(self._on_override_changed)
            watch("kanji_missing", self._kanji_missing,
                  lambda: self._kanji_missing.update_results(self._results.get("kanji")))
            watch("grammar_missing", self._grammar_missing,
                  lambda: self._grammar_missing.update_results(self._results.get("grammar")))
            return KindSwitcher([("Vocab", self._missing_panel),
                                 ("Kanji", self._kanji_missing),
                                 ("Grammar", self._grammar_missing)])
        self._tabs.addTab(_LazyTab(build_missing, "Building the Missing list…"), "Missing")

        def build_ms():
            self._ms_panel = MarkedSuspendedPanel(self._overrides, self._results, self._lists)
            self._ms_panel.changed.connect(self._on_override_changed)
            self._ms_panel.refresh_requested.connect(self._do_full_refresh)
            self._kanji_ms = KGOverridesPanel("kanji", self._kanji_overrides)
            self._grammar_ms = KGOverridesPanel("grammar", self._grammar_overrides)
            self._kanji_ms.changed.connect(self._on_override_changed)
            self._grammar_ms.changed.connect(self._on_override_changed)
            watch("ms", self._ms_panel, self._ms_panel.refresh)
            watch("kanji_ms", self._kanji_ms, self._kanji_ms.refresh)
            watch("grammar_ms", self._grammar_ms, self._grammar_ms.refresh)
            return KindSwitcher([("Vocab", self._ms_panel), ("Kanji", self._kanji_ms),
                                 ("Grammar", self._grammar_ms)])
        self._ms_tab = _LazyTab(build_ms, "Building Marked & Suspended…")
        self._tabs.addTab(self._ms_tab, "Marked && Suspended")
        self._update_ms_label()

        # Unlisted tab
        unlisted_data = self._results.get("unlisted", {}).get("known_words", [])
        if unlisted_data:
            def build_unlisted():
                freq = self._results.get("frequency") or {}
                self._unlisted_panel = _UnlistedPanel(
                    self._results.get("unlisted", {}).get("known_words", []), self._overrides,
                    on_override_changed=self._on_override_changed,
                    nid_rank=freq.get("nid_rank", {}),
                    nid_rank_extra=freq.get("nid_rank_extra", {}),
                    maturity=self._results.get("maturity", {}),
                )
                return self._unlisted_panel
            self._tabs.addTab(_LazyTab(build_unlisted, "Building the Off-list tab…"), f"Off-list ({len(unlisted_data):,})")

        # Kanji & Grammar tab (separate from words and rank)
        self._kanji_tab = None
        if self._results.get("kanji") or self._results.get("grammar"):
            from .kanji_view import KanjiGrammarTab
            self._kanji_tab = KanjiGrammarTab(
                self._results.get("kanji"), self._results.get("grammar"), self._deck_name,
                self._kanji_overrides, self._grammar_overrides,
                series_fn=lambda: self._results.get("history_series"))
            self._kanji_tab.open_kanji_grid.connect(self._open_kanji_grid)
            self._kanji_tab.open_grammar_grid.connect(self._open_grammar_grid)
            self._kanji_tab.refresh_requested.connect(self._do_full_refresh)
            self._overview.gold_preview.connect(self._kanji_tab.set_force_max_gold)
            self._tabs.addTab(self._kanji_tab, "Kanji && Grammar")

        # Text Check tab: how much of a pasted text / subtitle file you know
        from .text_check_view import TextCheckTab
        self._tabs.addTab(TextCheckTab(lambda: self._results), "Text Check")

        # History tab
        from .history_view import HistoryTab
        self._history_tab = HistoryTab(self._history or {}, self._deck_name,
                                       results_fn=lambda: self._results)
        self._history_tab.snapshot_requested.connect(self._take_snapshot)
        self._tabs.addTab(self._history_tab, "History")

        # Nakama: friends' cards next to yours (owner 2026-10-17)
        from .nakama_view import NakamaTab
        self._nakama_tab = NakamaTab()
        self._tabs.addTab(self._nakama_tab, "Nakama 仲間")

        btn_row = QHBoxLayout()
        # ♥ Support (owner 2026-10-16 / 2026-10-20): a voluntary tip, nothing
        # unlocked by it; quiet until hovered, always in the bottom row,
        # never a popup.
        support_btn = QPushButton("♥ Support")
        support_btn.setToolTip("Kotodama is free. If it helps you, you can leave a tip on Ko-fi "
                               "(opens your browser). Nothing is unlocked by it: thank you!")
        support_btn.setStyleSheet(_quiet_button_style("#ff5e5b", (255, 94, 91)))
        support_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(SUPPORT_URL)))
        btn_row.addWidget(support_btn)
        btn_row.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        outer.addLayout(btn_row)
        # The Overview announced its gold state while being built, before
        # this connection existed.
        self._apply_gold(self._overview.gold)

    def _on_goal_changed(self):
        """A new / changed / removed JLPT goal: the Overview's goal card, the
        History chart's goal lines and the mini widget's "Today" line."""
        with _neon_quiet():
            self._overview.update_results(self._results)
        self._history_tab._refresh_chart()
        from . import mini_widget
        from aqt import mw
        mini_widget.invalidate_cache()
        if mw.state == "deckBrowser":
            mw.deckBrowser.refresh()

    def _open_share(self):
        """The Overview's "Share image…": a PNG of the current progress (the
        rank as shown, so the debug preview works too)."""
        from . import share_card
        data = share_card.gather(self._results, self._overview._rank_badge._info,
                                 self._kanji_overrides, self._grammar_overrides)
        share_card.ShareDialog(data, self, on_message_saved=self._overview.set_inscription).exec()

    def _apply_gold(self, gold: bool):
        """Amaterasu gold mode (real 20,000 or the debug preview): gold tab
        frame, gold Japanese text (divine_text), gold tile edges + sheen in
        the grids (_GOLD_MODE). Deferred one event-loop turn so widgets that
        re-label themselves on the same signal (Kanji tab bar labels) are
        done first."""
        self._gold = bool(gold)
        _GOLD_MODE["on"] = self._gold
        QTimer.singleShot(0, self._apply_gold_now)
        # The star's sound plays in Amaterasu mode (owner 2026-10-16); an
        # ascension about to play starts it itself, with the ignition.
        from . import ambience
        if not self._gold:
            ambience.get().leave()
        elif not _ASCENSION["pending"]:
            ambience.get().enter()

    def _apply_gold_now(self):
        from . import divine_text
        try:
            from . import theme
            theme.apply(self, gold=self._gold)       # the window's own look, or gold's background
            self._tabs.setStyleSheet("")             # tabs: theme.py in both modes (to-do 2d; was divine_text.TAB_SS)
            divine_text.gold_palette(self, self._gold)
            divine_text.gold_titlebar(self, self._gold)
            if getattr(self, "_title_left", None) is not None:      # the neon title card
                self._title_left.set_parts(TITLE_LEFT_GOLD if self._gold else TITLE_LEFT)
                self._title_right.set_parts(TITLE_RIGHT_GOLD if self._gold else TITLE_RIGHT)
            self.setWindowTitle(f"言霊 — {self._deck_name}" if self._gold
                                else f"Kotodama 言霊 — {self._deck_name}")
            # History chart lines: gold shades ↔ their normal colours
            if getattr(self, "_history_tab", None) is not None:
                self._history_tab._refresh_chart()
            # The widget walk only matters once gold mode has been on: a
            # window that was never gold is already English (and the walk
            # right after opening stalled the bar intro, to-do 2e).
            if self._gold or getattr(self, "_was_gold", False):
                divine_text.apply(self, self._gold)
                self._was_gold = True
        except RuntimeError:
            pass                      # dialog closed meanwhile

    def _on_override_changed(self, keep: str = None):
        """Lightweight update after a tile is marked found/suspended or an
        override is reverted: the tab label now; the Marked & Suspended and
        missing kanji / grammar tables when they're next shown (only a table
        on screen right now is rebuilt at once). The Overview/Word Grid/
        Missing Words tabs are NOT rebuilt here (that would re-sort/re-flow
        the whole grid on every click) — use the Refresh button for those.
        Kept grid windows other than `keep` (the one marked in) are rebuilt
        when next opened."""
        self._grid_stale.update(k for k in self._grid_windows if k != keep)
        self._dirty.update(self._lazy)
        self._update_ms_label()
        self._flush_dirty()

    def _flush_dirty(self):
        """Rebuild the out-of-date tables that are visible now."""
        for name in list(self._dirty):
            widget, rebuild = self._lazy[name]
            if widget.isVisible():
                self._dirty.discard(name)
                rebuild()

    def _update_ms_label(self):
        """Marked & Suspended tab label: found / suspended counts over
        vocab, kanji and grammar."""
        sets = (self._overrides, self._kanji_overrides, self._grammar_overrides)
        n_found = sum(len(o.found) for o in sets)
        n_susp  = sum(len(o.suspended) for o in sets)
        idx = self._tabs.indexOf(self._ms_tab)
        if idx >= 0:
            label = "Marked && Suspended"
            if n_found or n_susp:
                label += f"  ({n_found}★ / {n_susp}✕)"
            self._tabs.setTabText(idx, label)
            if getattr(self, "_gold", False):
                from . import divine_text
                divine_text.apply_tabs(self._tabs, True)

    def _do_full_refresh(self, manual_snapshot: bool = False, on_done=None):
        """Recompute results from the current override state and rebuild the
        Overview, Word Grid, Missing Words and History tabs. Triggered via the
        Refresh buttons on the Overview and Marked & Suspended tabs, and by
        the History tab's "Take snapshot now" (manual_snapshot=True). The
        counting runs off the main thread; a click while it runs is ignored."""
        if self._refreshing:
            return
        self._refreshing = True
        # Re-read overrides.json from disk so a manually placed file is
        # picked up without restarting Anki.
        self._overrides.reload()
        self._kanji_overrides.reload()
        self._grammar_overrides.reload()

        # Our own note, not Anki's progress bar (owner 2026-10-26).
        from .busy import show_note, close_note
        note = show_note(self, "Counting your deck…")

        def work():
            try:
                return self._recompute_results(manual_snapshot)
            except BaseException:
                self._refreshing = False
                mw.taskman.run_on_main(lambda: close_note(note))
                raise

        def done(out):
            self._refreshing = False
            close_note(note)
            if out is None:
                return
            try:
                self._apply_refresh(*out)
            except RuntimeError:
                return                    # dialog closed meanwhile
            if on_done:
                on_done()

        card_state.run_in_background(self, work, done)

    def _apply_refresh(self, results: dict, analysis_inputs: dict, series):
        """Show a finished recount (main thread; seconds with every tab
        built, so under a "please wait" note)."""
        from .busy import busy
        with busy(self, "Updating the window…"):
            self._apply_refresh_now(results, analysis_inputs, series)

    def _apply_refresh_now(self, results: dict, analysis_inputs: dict, series):
        self._grid_stale.update(self._grid_windows)     # new counts: rebuilt when reopened
        self._results = results
        self._analysis_inputs.update(analysis_inputs)
        self._history = series
        self._history_tab.update_series(self._history or {})
        with _neon_quiet():             # a rebuild, not a first look: no flicker again
            self._overview.update_results(self._results)
            if self._kanji_tab is not None:
                self._kanji_tab.update_results(self._results.get("kanji"),
                                               self._results.get("grammar"))
            if self._grid_flat is not None:          # tabs not built yet read
                self._grid_flat.update_results(self._results)   # the new results
        if self._missing_panel is not None:                     # when they are
            self._missing_panel.update_results(self._results)
            self._kanji_missing.update_results(self._results.get("kanji"))
            self._grammar_missing.update_results(self._results.get("grammar"))
        if self._ms_panel is not None:
            self._ms_panel._results = self._results
            self._ms_panel.refresh()
            self._kanji_ms.refresh()
            self._grammar_ms.refresh()
        self._dirty.clear()             # all just rebuilt
        self._update_ms_label()
        self._nakama_tab._fill_list()   # your card's new numbers

        # Keep the main-screen mini widget in sync with this refresh too.
        from . import mini_widget
        from aqt import mw
        mini_widget.invalidate_cache()
        if mw.state == "deckBrowser":
            mw.deckBrowser.refresh()

    def _take_snapshot(self):
        def saved():
            from aqt.utils import tooltip
            tooltip("Snapshot saved for today", parent=self)
        self._do_full_refresh(manual_snapshot=True, on_done=saved)

    def _recompute_results(self, manual_snapshot: bool = False):
        """Re-scan the deck for new/removed cards, then re-run analyse()
        and the kanji / grammar / history parts. Runs off the main thread:
        returns (results, analysis inputs, history) and changes nothing on
        the dialog (_apply_refresh does that).

        Re-scanning (collect_words) is necessary so that cards added to the
        deck after the dialog was opened are reflected when the user hits
        Refresh. The updated indices go back into analysis_inputs so
        subsequent refreshes stay current without reopening the dialog.
        """
        ai = dict(self._analysis_inputs)
        if not ai:
            return None
        import sys
        # Import functions directly from the addon's __init__ module
        pkg = __name__.rsplit(".", 1)[0]   # e.g. "jlpt_progress"
        addon_mod = sys.modules.get(pkg)
        if addon_mod is None:
            return None
        analyse       = getattr(addon_mod, "analyse")
        collect_words = getattr(addon_mod, "collect_words")

        # Re-scan the deck — picks up any cards added since the dialog opened
        field_mappings   = ai.get("field_mappings", [])
        ignore_suspended = ai.get("ignore_suspended", False)
        if field_mappings:
            display_index, reading_index, nid_to_display, nid_to_reading = \
                collect_words(self._deck_name, field_mappings, ignore_suspended)
            ai["display_index"]  = display_index
            ai["reading_index"]  = reading_index
            ai["nid_to_display"] = nid_to_display
            ai["nid_to_reading"] = nid_to_reading

        results = analyse(
            ai["display_index"], ai["reading_index"],
            ai["nid_to_display"], ai["nid_to_reading"],
            self._lists, ai["unique_readings"],
            overrides=self._overrides,
        )
        results["maturity"] = card_state.with_pseudo(
            card_state.note_maturity(self._deck_name, ignore_suspended),
            ai.get("nid_to_display", {}))
        extras = self.compute_extras(results, self._deck_name, self._lists, ai,
                                     self._kanji_overrides, self._grammar_overrides,
                                     manual_snapshot=manual_snapshot)
        return results, ai, extras["history"]

    # Grid windows are kept once built (owner 2026-10-25: reopening a bar's
    # grid rebuilt it every time): closing only hides one, the next click
    # on its bar shows it again. Rebuilt after a Refresh, a gold-mode change,
    # or a mark made somewhere else (another grid, a tab), since it would
    # show the old state; all freed with the main window.

    def _reuse_grid(self, key: str) -> bool:
        w = self._grid_windows.get(key)
        if w is None:
            return False
        try:
            if key in self._grid_stale or w.property("kgold") != _GOLD_MODE["on"]:
                w.hide()
                w.deleteLater()
            else:
                if w.isMinimized():
                    w.showNormal()
                w.show()
                w.raise_()
                w.activateWindow()
                return True
        except RuntimeError:
            pass
        self._grid_windows.pop(key, None)
        self._grid_stale.discard(key)
        return False

    def _keep_grid(self, key: str, w):
        if w is not None:
            w.setProperty("kgold", _GOLD_MODE["on"])
            self._grid_windows[key] = w

    def _grid_marked(self, key: str):
        """A tile marked in grid window `key`: the other kept grids are out
        of date, that one isn't."""
        self._on_override_changed(keep=key)

    def _open_kanji_grid(self, level: str):
        key = "kanji:" + level
        if self._reuse_grid(key):
            return
        from .kanji_view import open_kanji_grid
        self._keep_grid(key, open_kanji_grid(
            self, self._results["kanji"], level, self._kanji_overrides,
            self._deck_name, lambda: self._grid_marked(key)))

    def _open_grammar_grid(self, level: str):
        key = "grammar:" + level
        if self._reuse_grid(key):
            return
        from .kanji_view import open_grammar_grid
        self._keep_grid(key, open_grammar_grid(
            self, self._results["grammar"], level, self._grammar_overrides,
            self._deck_name, lambda: self._grid_marked(key)))

    def _open_grid_for_level(self, level: str):
        """level is "N5".."N1"/"All", or "freq:N" for the top-N frequency
        words. Large grids (up to 20,000 tiles) take a few seconds to build:
        a "please wait" note meanwhile (busy.py, owner 2026-10-25)."""
        key = "word:" + level
        if self._reuse_grid(key):
            return
        from .busy import busy
        with busy(self, "Building the grid…"):
            self._keep_grid(key, self._build_grid_window(level, key))

    def _build_grid_window(self, level: str, key: str):
        freq_limit = None
        if level.startswith("freq:"):
            freq_limit = int(level.split(":", 1)[1])
            name  = freq_data.TIER_NAMES.get(freq_limit)
            title = (f"Most Common Words — {name} (Top {freq_limit:,})" if name == "Near Native"
                     else f"Most Common Words — Top {freq_limit:,}")
            level = "freq"
        else:
            title = f"Word Grid — {level}"
        dlg = QDialog(self)
        # Dialogs only get a close button by default on Windows — add
        # minimize/maximize so large grids can fill the screen.
        dlg.setWindowFlags(
            dlg.windowFlags()
            | Qt.WindowType.Window
            | Qt.WindowType.WindowMinMaxButtonsHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        dlg.setWindowTitle(f"{title}  ({self._deck_name})")
        size_grid_window(dlg, self)
        v    = QVBoxLayout(dlg)
        grid = WordGridPanel(
            self._results, level, self._overrides,
            flat=False, on_override_changed=lambda: self._grid_marked(key),
            freq_limit=freq_limit,
        )
        v.addWidget(grid)
        btn = QPushButton("Close")
        btn.clicked.connect(dlg.accept)
        row = QHBoxLayout(); row.addStretch(); row.addWidget(btn)
        v.addLayout(row)
        from . import theme
        theme.apply(dlg, gold=_GOLD_MODE["on"])
        if _GOLD_MODE["on"]:
            from . import divine_text
            divine_text.gold_palette(dlg, True)
            divine_text.apply(dlg, True)
        attach_sky(dlg)
        attach_rain(dlg)
        dlg.show()
        place_grid_window(dlg, self)
        if _GOLD_MODE["on"]:
            divine_text.gold_titlebar(dlg, True)    # needs the native window
        return dlg
