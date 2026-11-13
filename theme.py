"""
theme.py
Kotodama's own window theme (owner 2026-10-18: "the rest of the app looks
like an old Anki plugin"): the share image's black → grey gradient as the
background, flat underlined tabs, soft rounded buttons, inputs, tables,
thin scrollbars, tooltips and menus, independent of Anki's own theme (so
Anki's light mode no longer leaves the add-on half light).

One template, two palettes: NORMAL (accent = Kotodama gold, the colour of
the 言霊 in the title) and GOLD (Amaterasu mode, to-do 2d: the same modern
look in warm black and gold; divine_text still turns the texts Japanese
and gold). Every widget kind Anki's own style sheet colours is set here in
both palettes — anything left out shows Anki's grey through (the grey panel
the owner saw in gold mode, 2026-10-18).

Per-widget style sheets set elsewhere (label colours, coloured buttons)
still win over these defaults for the properties they set.
"""

from __future__ import annotations

from aqt.qt import QColor

# Night (owner 2026-10-25, "moon mode", mock-up M2): near-black, so the
# tubes' light spill, the stars and the moon read as night (was the share
# image's #202020 → #121212). Amaterasu mode (GOLD) is the sun.
BG_TOP, BG_BOTTOM = "#070708", "#020203"
GOLD_BG_TOP, GOLD_BG_BOTTOM = "#211a08", "#0e0b04"   # warm black → dark gold
# Kotodama gold (the 言霊 of the title; owner 2026-10-18: tie the window to
# the gold kanji theme instead of the rank's colour).
KOTODAMA_GOLD = "#d4a017"
_ACCENT = {"color": KOTODAMA_GOLD}

# Type scale (owner 2026-10-18: clearer typography): four text styles for
# every label, in place of the old mix of 9–14 px. Hint grey is #888 so
# divine_text's gray → gold pass still catches it in Amaterasu mode.
# Step 2 (owner 2026-10-19: "what aligns with modern UI design practice"):
# Fluent / macOS-style sizes — body 13 px, nothing readable below 12 px,
# section titles 16 px semibold. BASE_PX is every label, button and input
# that doesn't set its own size (theme sheet).
SECTION_CSS = "font-size: 16px; font-weight: 600;"     # section card titles, grid level headers
SUB_CSS     = "font-size: 14px;"                       # sub-headings (Found / Suspended …)
BODY_CSS    = "font-size: 13px;"                       # stats lines, table labels
HINT_CSS    = "color: #888; font-size: 12px;"          # notes, hints, sources, statuses
BASE_PX     = 13
TAB_PX      = 14

# Neon intro (owner 2026-10-19): bars open unlit at their real length and
# flicker on like neon tubes — the main window (progress_dialog, QPainter)
# and the deck-list mini widget (CSS keyframes) share this pattern.
NEON_OFF_FILL = 0.16      # an unlit tube: the fill's colour barely there
NEON_OFF_TEXT = 0.5
NEON_MAX_SECONDS = 1.6    # the longest pattern; progress_dialog's intro lasts longer


def flicker_pattern(seed) -> list:
    """[(end_seconds, level 0–1)] for one bar, then fully on. seed: an int
    or str (random.Random rejects tuples on Python 3.11+)."""
    import random
    rnd = random.Random(seed)
    # Owner 2026-10-19: more variety, so it isn't the same order each time.
    t = rnd.uniform(0.05, 0.75)                 # dark before the first spark
    out = [(t, 0.0)]
    if rnd.random() < 0.2:
        # A struggling tube: a fast, dim buzz before it catches.
        for _ in range(rnd.randint(4, 8)):
            t += rnd.uniform(0.02, 0.05)
            out.append((t, rnd.choice((0.3, 0.45, 0.6))))
            t += rnd.uniform(0.02, 0.06)
            out.append((t, 0.0))
    else:
        for _ in range(rnd.randint(1, 5)):
            t += rnd.uniform(0.03, 0.09)
            out.append((t, 1.0 if rnd.random() < 0.7 else 0.55))
            t += rnd.uniform(0.04, 0.2)
            out.append((t, 0.0 if rnd.random() < 0.8 else 0.25))
    if rnd.random() < 0.25:
        # Catches, holds a moment, then one last dip.
        t += rnd.uniform(0.15, 0.35)
        out.append((t, 1.0))
        t += rnd.uniform(0.04, 0.08)
        out.append((t, 0.0))
    if t > NEON_MAX_SECONDS:                    # keep it short: squeeze to fit
        k = NEON_MAX_SECONDS / t
        out = [(e * k, level) for e, level in out]
    return out

NORMAL = {
    "bg_top": BG_TOP, "bg_bottom": BG_BOTTOM, "text": "#e8e8ec",
    "tab": "#8a8a94", "tab_hover": "#e2e2ea", "tab_hover_line": "#2c2c34", "tab_sel": "#ffffff",
    "pane_border": "rgba(255,255,255,0.05)", "pane_bg": "transparent",
    "btn_bg": "#0d0d10", "btn_border": "#26262c", "btn_hover": "#16161a",
    "btn_hover_border": "#3c3c46", "btn_pressed": "#08080a", "btn_disabled": "#666666",
    "input_bg": "#161616", "input_border": "#353535",
    "popup_bg": "#1a1a1a", "popup_border": "#3a3a3a",
    "table_bg": "#151515", "table_alt": "#1a1a1a", "table_border": "#2c2c2c", "grid": "#262626",
    "head_bg": "#1e1e1e", "head_fg": "#b0b0b0", "head_line": "#333333",
    "scroll": "#26262e", "scroll_hover": "#363640",
    "card_bg": "rgba(0,0,0,0.55)", "card_border": "rgba(255,255,255,0.05)",
    "icon_border": "#26262c", "icon_hover": "#16161a", "split": "#16161a",
    "check_border": "#555555", "seg_sel_fg": "#ffffff",
    "tip_bg": "#1a1a1a", "tip_fg": "#eeeeee", "tip_border": "#444444",
}

GOLD = {
    "bg_top": GOLD_BG_TOP, "bg_bottom": GOLD_BG_BOTTOM, "text": "#ffe9a0",
    "tab": "#b8952a", "tab_hover": "#ffe066", "tab_hover_line": "#6b5a1a", "tab_sel": "#ffe066",
    "pane_border": "#4a3d12", "pane_bg": "rgba(255,226,112,0.02)",
    "btn_bg": "#221b09", "btn_border": "#6b5a1a", "btn_hover": "#2e2510",
    "btn_hover_border": "#a08420", "btn_pressed": "#171206", "btn_disabled": "#6b5a1a",
    "input_bg": "#14110a", "input_border": "#4a3d12",
    "popup_bg": "#14110a", "popup_border": "#6b5a1a",
    "table_bg": "#14110a", "table_alt": "#1a150b", "table_border": "#4a3d12", "grid": "#2a2310",
    "head_bg": "#1c170a", "head_fg": "#d9b84a", "head_line": "#4a3d12",
    "scroll": "#5a4a14", "scroll_hover": "#7a6420",
    "card_bg": "rgba(255,226,112,0.035)", "card_border": "#4a3d12",
    "icon_border": "#6b5a1a", "icon_hover": "#2e2510", "split": "#3a3114",
    "check_border": "#a08420", "seg_sel_fg": "#ffe066",
    "tip_bg": "#14110a", "tip_fg": "#ffe9a0", "tip_border": "#6b5a1a",
}
GOLD_ACCENT = "#f5c518"


def set_accent(color) -> None:
    """Override the normal theme's accent (a QColor or "#rrggbb")."""
    c = QColor(color)
    if c.isValid():
        _ACCENT["color"] = c.name()


def accent() -> str:
    return _ACCENT["color"]


def _rgba(hex_color: str, alpha: float) -> str:
    c = QColor(hex_color)
    return f"rgba({c.red()},{c.green()},{c.blue()},{alpha})"


def _sheet(c: dict, a: str) -> str:
    soft, faint = _rgba(a, 0.35), _rgba(a, 0.18)
    return f"""
QDialog#kotodama {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {c['bg_top']}, stop:1 {c['bg_bottom']});
}}
QDialog#kotodama QWidget {{ color: {c['text']}; font-size: {BASE_PX}px; }}
QDialog#kotodama QScrollArea, QDialog#kotodama QScrollArea > QWidget > QWidget,
QDialog#kotodama QStackedWidget, QDialog#kotodama QStackedWidget > QWidget,
QDialog#kotodama QSplitter {{ background: transparent; }}

QDialog#kotodama QTabWidget::pane {{
    border: 1px solid {c['pane_border']}; border-radius: 10px; top: -1px;
    background: {c['pane_bg']};
}}
QDialog#kotodama QTabWidget#kmaintabs::pane {{ border-top: none; }}
QDialog#kotodama QTabWidget::tab-bar {{ alignment: center; }}
QDialog#kotodama QTabBar {{ background: transparent; }}
QDialog#kotodama QTabBar::tab {{
    background: transparent; color: {c['tab']}; border: none;
    border-bottom: 2px solid transparent; padding: 6px 12px; margin: 0 2px;
    font-size: {TAB_PX}px;
}}
QDialog#kotodama QTabBar::tab:hover {{ color: {c['tab_hover']}; border-bottom: 2px solid {c['tab_hover_line']}; }}
QDialog#kotodama QTabBar::tab:selected {{
    color: {c['tab_sel']}; font-weight: bold; border-bottom: 2px solid {a};
}}
QDialog#kotodama QTabBar QToolButton {{
    background: {c['btn_bg']}; color: {c['tab']}; border: 1px solid {c['btn_border']};
    border-radius: 6px; margin: 1px;
}}
QDialog#kotodama QTabBar QToolButton:hover {{ color: {a}; border-color: {a}; background: {c['btn_hover']}; }}
QDialog#kotodama QTabBar QToolButton:disabled {{ color: {c['btn_disabled']}; }}

QDialog#kotodama QPushButton {{
    background: {c['btn_bg']}; color: {c['text']}; border: 1px solid {c['btn_border']};
    border-radius: 7px; padding: 4px 12px;
}}
QDialog#kotodama QPushButton:hover {{ background: {c['btn_hover']}; border-color: {c['btn_hover_border']}; }}
QDialog#kotodama QPushButton:pressed {{ background: {c['btn_pressed']}; }}
QDialog#kotodama QPushButton:focus {{ border-color: {soft}; }}
QDialog#kotodama QPushButton:disabled {{ color: {c['btn_disabled']}; }}
QDialog#kotodama QPushButton:checked {{ background: {faint}; border-color: {soft}; }}

QDialog#kotodama QLineEdit, QDialog#kotodama QPlainTextEdit, QDialog#kotodama QTextEdit,
QDialog#kotodama QSpinBox, QDialog#kotodama QComboBox {{
    background: {c['input_bg']}; color: {c['text']}; border: 1px solid {c['input_border']};
    border-radius: 7px; padding: 3px 8px; selection-background-color: {soft};
}}
QDialog#kotodama QLineEdit:focus, QDialog#kotodama QPlainTextEdit:focus,
QDialog#kotodama QTextEdit:focus, QDialog#kotodama QComboBox:focus,
QDialog#kotodama QComboBox:on {{ border-color: {a}; }}
QDialog#kotodama QComboBox QAbstractItemView {{
    background: {c['popup_bg']}; color: {c['text']}; border: 1px solid {c['popup_border']};
    selection-background-color: {soft}; outline: none;
}}
QDialog#kotodama QCheckBox, QDialog#kotodama QRadioButton {{ background: transparent; spacing: 6px; }}
QDialog#kotodama QCheckBox::indicator {{
    width: 13px; height: 13px; border: 1px solid {c['check_border']}; border-radius: 4px;
    background: {c['input_bg']};
}}
QDialog#kotodama QCheckBox::indicator:hover {{ border-color: {a}; }}
QDialog#kotodama QCheckBox::indicator:checked {{ background: {a}; border-color: {a}; }}

QDialog#kotodama QTableWidget, QDialog#kotodama QTableView,
QDialog#kotodama QListWidget, QDialog#kotodama QListView {{
    background: {c['table_bg']}; alternate-background-color: {c['table_alt']}; color: {c['text']};
    border: 1px solid {c['table_border']}; border-radius: 8px; gridline-color: {c['grid']};
    selection-background-color: {soft}; selection-color: {c['tab_sel']}; outline: none;
}}
QDialog#kotodama QListWidget::item:selected {{ background: {faint}; border-left: 3px solid {a}; }}
QDialog#kotodama QListWidget::item:hover {{ background: {_rgba(a, 0.08)}; }}
QDialog#kotodama QHeaderView, QDialog#kotodama QHeaderView::section {{
    background: {c['head_bg']}; color: {c['head_fg']}; border: none;
}}
QDialog#kotodama QHeaderView::section {{ border-bottom: 1px solid {c['head_line']}; padding: 4px 6px; }}
QDialog#kotodama QTableCornerButton::section {{ background: {c['head_bg']}; border: none; }}

QDialog#kotodama QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QDialog#kotodama QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QDialog#kotodama QScrollBar::handle:vertical {{ background: {c['scroll']}; border-radius: 4px; min-height: 30px; }}
QDialog#kotodama QScrollBar::handle:horizontal {{ background: {c['scroll']}; border-radius: 4px; min-width: 30px; }}
QDialog#kotodama QScrollBar::handle:hover {{ background: {c['scroll_hover']}; }}
QDialog#kotodama QScrollBar::add-line, QDialog#kotodama QScrollBar::sub-line {{ width: 0; height: 0; }}
QDialog#kotodama QScrollBar::add-page, QDialog#kotodama QScrollBar::sub-page {{ background: transparent; }}

QDialog#kotodama QFrame#kcard {{
    background: {c['card_bg']}; border: 1px solid {c['card_border']}; border-radius: 12px;
}}
QDialog#kotodama QFrame#kcard QLabel {{ background: transparent; border: none; }}
QDialog#kotodama QPushButton#kicon {{
    min-width: 30px; max-width: 30px; min-height: 26px; padding: 0; font-size: 15px;
    background: transparent; border: 1px solid {c['icon_border']};
}}
QDialog#kotodama QPushButton#kicon:hover {{ background: {c['icon_hover']}; border-color: {a}; color: {a}; }}
QDialog#kotodama QPushButton[seg] {{ border-radius: 0; margin: 0; padding: 4px 14px; }}
QDialog#kotodama QPushButton[seg="first"] {{ border-top-left-radius: 7px; border-bottom-left-radius: 7px; }}
QDialog#kotodama QPushButton[seg="last"] {{ border-top-right-radius: 7px; border-bottom-right-radius: 7px; }}
QDialog#kotodama QPushButton[seg="mid"], QDialog#kotodama QPushButton[seg="last"] {{ border-left: none; }}
QDialog#kotodama QPushButton[seg]:checked {{ background: {faint}; color: {c['seg_sel_fg']}; border-color: {soft}; }}
QDialog#kotodama QSplitter::handle {{ background: {c['split']}; }}
QDialog#kotodama QMenu {{ background: {c['popup_bg']}; color: {c['text']}; border: 1px solid {c['popup_border']}; }}
QDialog#kotodama QMenu::item:selected {{ background: {soft}; }}
QToolTip {{
    background: {c['tip_bg']}; color: {c['tip_fg']}; border: 1px solid {c['tip_border']};
    border-radius: 6px; padding: 6px;
}}
"""


def style_sheet() -> str:
    return _sheet(NORMAL, accent()) + _arrow_rules(NORMAL, accent())


def gold_style_sheet() -> str:
    """Amaterasu mode: the same modern look in warm black and gold."""
    return _sheet(GOLD, GOLD_ACCENT) + _arrow_rules(GOLD, GOLD_ACCENT)


def apply(widget, gold: bool = False) -> None:
    """Theme a top-level Kotodama window, normal or Amaterasu gold."""
    try:
        widget.setObjectName("kotodama")
        sheet = gold_style_sheet() if gold else style_sheet()
        # Re-setting the same sheet re-polishes every widget (≈1 s on a big
        # window, the bar intro's freeze: to-do 2e), so only on a change.
        if widget.styleSheet() != sheet:
            widget.setStyleSheet(sheet)
    except RuntimeError:
        pass                                     # window closed meanwhile



def _arrow_image(direction: str, color: str) -> str:
    """A small ‹ / › chevron PNG in color, drawn once and kept in
    user_files (the tab bar's scroll buttons draw Qt's grey arrows, which a
    style sheet colour can't reach; owner 2026-10-20: still grey in
    Amaterasu mode). Returns a style-sheet url path, "" if it can't be made."""
    import os
    from aqt.qt import QColor, QPainter, QPen, QPixmap, QPointF, Qt
    folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "user_files")
    path = os.path.join(folder, f"tab_arrow_{direction}_{color.lstrip('#')}.png")
    if not os.path.exists(path):
        try:
            os.makedirs(folder, exist_ok=True)
            pm = QPixmap(20, 20)
            pm.fill(Qt.GlobalColor.transparent)
            p = QPainter(pm)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            pen = QPen(QColor(color), 2.2)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            p.setPen(pen)
            x0, x1 = (12.5, 7.5) if direction == "left" else (7.5, 12.5)
            p.drawPolyline([QPointF(x0, 5), QPointF(x1, 10), QPointF(x0, 15)])
            p.end()
            pm.save(path, "PNG")
        except Exception:
            return ""
    return path.replace("\\", "/")


def _arrow_rules(c: dict, a: str) -> str:
    rules = ""
    # (no :hover::left-arrow image: Qt drew both chevrons on the left button;
    # the hover border in the accent colour is enough)
    for d in ("left", "right"):
        img = _arrow_image(d, c["tab"])
        if img:
            rules += (f"QDialog#kotodama QTabBar QToolButton::{d}-arrow {{ image: url(\"{img}\"); "
                      f"width: 14px; height: 14px; }}\n")
    return rules


def fit_on_screen(window, margin: int = 8) -> None:
    """Keep a window whole on its screen, above the taskbar (owner
    2026-10-26: Settings and the main window opened with their bottom cut
    off). Call right after it's shown: Windows' frame / title bar size is
    only known then. Shrinks it to the free area if it's taller or wider,
    then moves it in."""
    try:
        scr = window.screen().availableGeometry() if window.screen() else None
    except RuntimeError:
        return
    if scr is None or not window.isVisible():
        return
    frame, inner = window.frameGeometry(), window.geometry()
    extra_w, extra_h = frame.width() - inner.width(), frame.height() - inner.height()
    w = min(inner.width(), scr.width() - extra_w - 2 * margin)
    h = min(inner.height(), scr.height() - extra_h - 2 * margin)
    if (w, h) != (inner.width(), inner.height()):
        window.resize(max(w, 200), max(h, 200))
    frame = window.frameGeometry()
    # (wider / taller than the screen even at its minimum size: the
    # top-left corner stays on screen, title bar first)
    x = max(min(max(frame.x(), scr.left() + margin), scr.right() - frame.width() - margin + 1), scr.left())
    y = max(min(max(frame.y(), scr.top() + margin), scr.bottom() - frame.height() - margin + 1), scr.top())
    if (x, y) != (frame.x(), frame.y()):
        window.move(x, y)
