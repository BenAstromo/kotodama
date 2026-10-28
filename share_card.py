"""
share_card.py
A shareable PNG of your progress (owner 2026-10-09), from the Overview's
"Share image…" button:

  - every milestone: your name (typed in, remembered), the rank picture,
    rank name and belt, one bar per JLPT level combining vocab + kanji +
    grammar (known / total over all three), and the 20,000-word frequency
    bar; normal colours, no gold, no extra glow — also for the Amaterasu rank
    below 20,000;
  - Amaterasu mode (20,000): the gold scheme with light rays, her picture
    floating in the light, Japanese text, and a message of your own (also
    remembered; the Overview's engraved inscription shows the last one).

Drawn with QPainter into a QImage (1200 px wide); saved as PNG or copied.
"""

from __future__ import annotations

import datetime
import math

from aqt.qt import *

from . import jlpt_data, rank_data
from .jlpt_data import LEVELS, LEVEL_COLORS as LEVEL_FG

W = 1200
GOLD, GOLD_DEEP, GOLD_DARK, HAIR_BLACK = "#f5c518", "#d9a400", "#6b4a00", "#0d0b08"
FREQ_FG = "#7ec8f0"


def _cfg():
    from . import _cfg as cfg
    return cfg()


def _save_cfg(**kv):
    from . import _cfg as cfg, _save
    c = cfg()
    c.update(kv)
    _save(c)


def saved_name() -> str:
    return _cfg().get("share_name", "")


def saved_message() -> str:
    """The last message written for a 20,000 share (shown as the Overview's
    engraved inscription too)."""
    return _cfg().get("share_message", "")


# ── data ────────────────────────────────────────────────────────────────────

def gather(results: dict, info: dict, kanji_overrides=None, grammar_overrides=None) -> dict:
    """What the card shows: per JLPT level, known / total over vocab + kanji
    + grammar; the 20,000 frequency bar; the rank."""
    from . import kanji_data, grammar_data
    k_sus = {k.split("\t", 1)[0] for k in (kanji_overrides.suspended if kanji_overrides else ())}
    g_sus = {k.split("\t", 1)[0] for k in (grammar_overrides.suspended if grammar_overrides else ())}
    kc = kanji_data.level_counts(results["kanji"], k_sus) if results.get("kanji") else {}
    gc = grammar_data.level_counts(results["grammar"], g_sus) if results.get("grammar") else {}
    levels = []
    for lvl in LEVELS:
        d = results.get(lvl, {"known_words": [], "missing_words": []})
        k = len(d["known_words"])
        n = k + len(d["missing_words"])
        for c in (kc, gc):
            if lvl in c:
                k += c[lvl][0]
                n += c[lvl][1]
        levels.append((lvl, k, n))
    freq = results.get("frequency") or {}
    tiers = dict(freq.get("tiers", []))
    top = 20_000
    fk, fn = tiers.get(top, 0), (freq.get("tier_totals") or {}).get(top, top)
    from . import card_state
    if card_state.DEBUG_FULL["on"]:          # DEBUG "Force Amaterasu": every bar full
        levels = [(lvl, n, n) for lvl, _k, n in levels]
        fk = fn
    from . import loyalty, goal
    # Marked English loanwords counted in the rank shown (card_state schedule)
    loans = 0
    try:
        extra = card_state.found_extra(_cfg().get("deck_name", ""))
        loans = card_state.cards_for_rank(int(info.get("count") or 0), extra)[1]
    except Exception:
        pass
    g = goal.get()
    if g is not None and g["date"] < datetime.date.today():
        g = None                              # that test is over
    try:
        from . import nakama
        supporter = nakama.is_supporter()
    except Exception:
        supporter = False
    c = _cfg()
    return {"levels": levels, "freq": (fk, fn), "info": info,
            "date": datetime.date.today(), "loyal": loyalty.shown_months(), "sun": loyalty.shown_sun(),
            "goal": g, "loans": loans, "supporter": supporter,
            # the share pop-up's checkboxes (owner 2026-10-20), remembered
            "show_loyal": c.get("share_show_loyalty", True), "show_goal": c.get("share_show_goal", True)}


# ── drawing ─────────────────────────────────────────────────────────────────

def _font(pt: float, bold=False, serif=False, italic=False) -> QFont:
    f = QFont("Yu Mincho" if serif else QFont().family())
    if serif:
        f.setFamilies(["Yu Mincho", "MS Mincho", "Hiragino Mincho ProN", "Noto Serif CJK JP", "serif"])
    f.setPointSizeF(pt)
    f.setBold(bold)
    f.setItalic(italic)
    return f


def _bar(p: QPainter, r: QRectF, known: int, total: int, fg: str, gold: bool, label_text: str):
    """One progress bar with its text: gold (black text) or the level colour."""
    pct = known / total if total else 0.0
    rad = r.height() / 2
    fill = QRectF(r.x(), r.y(), max(r.height(), r.width() * pct) if pct else 0, r.height())
    laser = pct >= 1.0
    p.setPen(Qt.PenStyle.NoPen)
    # Glow halos, as on the add-on's bars (LevelBar._glow_params): stronger
    # with progress, a wide bloom at 100%. Spread scaled to the tighter
    # spacing here. Gold mode glows deep gold (the add-on's near-white glow
    # vanishes on the light background).
    if fill.width():
        if laser:
            layers, spread_max, peak = 9, 30, 255
        else:
            t = min(pct, 0.999) ** 0.55
            layers, spread_max, peak = 2 + int(t * 6), int(3 + t * 22), int(40 + t * 195)
        spread_max *= 0.6
        glow_c = QColor(GOLD if gold else fg)
        for i in range(1, layers + 1):
            frac = i / layers
            s = max(1.0, spread_max * (1.0 - frac * 0.75))
            c = QColor(glow_c)
            c.setAlpha(min(255, int(peak * frac ** 1.4 * (0.55 if gold else 1.0))))
            p.setBrush(c)
            p.drawRoundedRect(fill.adjusted(-s, -s, s, s), rad + s, rad + s)
        if laser:
            b = spread_max + 6
            c = QColor(glow_c)
            c.setAlpha(45)
            p.setBrush(c)
            p.drawRoundedRect(fill.adjusted(-b, -b, b, b), rad + b, rad + b)
    p.setBrush(QColor("#f3e3a6" if gold else "#1e1e1e"))
    p.drawRoundedRect(r, rad, rad)
    if fill.width():
        g = QLinearGradient(0, r.top(), 0, r.bottom())
        if gold:
            g.setColorAt(0, QColor("#fff3b0"))
            g.setColorAt(0.5, QColor(GOLD))
            g.setColorAt(1, QColor(GOLD_DEEP))
        else:
            c = QColor(fg)
            g.setColorAt(0, c.lighter(130))
            g.setColorAt(1, c.darker(150))
        p.setBrush(QBrush(g))
        p.drawRoundedRect(fill, rad, rad)
        # top sheen
        sh = QLinearGradient(0, r.top(), 0, r.top() + r.height() / 2)
        sh.setColorAt(0, QColor(255, 255, 255, 60))
        sh.setColorAt(1, QColor(255, 255, 255, 0))
        p.setBrush(QBrush(sh))
        p.drawRoundedRect(QRectF(fill.x(), fill.y(), fill.width(), fill.height() / 2), rad, rad)
        # 100%: white-hot rim
        if laser:
            p.setBrush(Qt.BrushStyle.NoBrush)
            for bw, a, col in ((3, 180, QColor(255, 255, 200)), (2, 230, QColor(255, 255, 255))):
                col.setAlpha(a)
                p.setPen(QPen(col, bw))
                p.drawRoundedRect(fill.adjusted(bw / 2, bw / 2, -bw / 2, -bw / 2), rad, rad)
            p.setPen(Qt.PenStyle.NoPen)
    p.setFont(_font(12, bold=True))
    text = f"{jlpt_data.format_pct(known, total)}   ({known:,} / {total:,})"
    if gold:
        p.setPen(QColor(HAIR_BLACK))
    else:
        p.setPen(QColor(0, 0, 0, 170))
        p.drawText(r.translated(1, 1), Qt.AlignmentFlag.AlignCenter, text)
        p.setPen(QColor("#ffffff"))
    p.drawText(r, Qt.AlignmentFlag.AlignCenter, text)
    # level label to the left
    # clear of the 100% glow halo (≈24 px)
    p.setFont(_font(19, bold=True))
    p.setPen(QColor(GOLD_DARK if gold else fg))
    p.drawText(QRectF(r.x() - 170, r.y() - 4, 140, r.height() + 8),
               Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, label_text)


def _luma(c: QColor) -> float:
    return 0.2126 * c.redF() + 0.7152 * c.greenF() + 0.0722 * c.blueF()


def _outline(info: dict) -> QColor:
    """Picture / card outline: the lighter rank colour, brightened when both
    are dark (same rule as progress_dialog.rank_outline_color)."""
    c = max((QColor(info.get("rank_color_a", "#888888")),
             QColor(info.get("rank_color_b", "#888888"))), key=_luma)
    return c.lighter(175) if _luma(c) < 0.22 else c


def _glow_text(p: QPainter, r: QRectF, text: str, font: QFont, fill, glow: QColor | None):
    """Centred text as a path: an optional soft glow (wide translucent
    strokes, so dark colours read on the dark card), then the fill (a colour
    or a gradient brush)."""
    fm = QFontMetricsF(font)
    w = fm.horizontalAdvance(text)
    base = QPointF(r.center().x() - w / 2, r.center().y() + (fm.ascent() - fm.descent()) / 2)
    path = QPainterPath()
    path.addText(base, font, text)
    p.save()
    p.setBrush(Qt.BrushStyle.NoBrush)
    if glow is not None:
        for width, alpha in ((9, 28), (6, 50), (3.5, 90), (1.6, 150)):
            c = QColor(glow)
            c.setAlpha(alpha)
            pen = QPen(c, width)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            p.setPen(pen)
            p.drawPath(path)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(fill if isinstance(fill, QBrush) else QBrush(QColor(fill)))
    p.drawPath(path)
    p.restore()


def _art(info: dict):
    try:
        from . import rank_images
        data = rank_images.get_rank_art(info["rank_name_en"])
    except Exception:
        data = None
    img = QImage()
    if data:
        img.loadFromData(data, "JPEG")
    return img if not img.isNull() else None


def _feathered(img: QImage, w: int, h: int) -> QImage:
    """The picture scaled to w×h with its edges fading out (Amaterasu: she
    floats in the light, as on the Overview)."""
    out = QImage(w, h, QImage.Format.Format_ARGB32_Premultiplied)
    out.fill(Qt.GlobalColor.transparent)
    p = QPainter(out)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    p.drawImage(QRectF(0, 0, w, h), img)
    p.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
    for horizontal, a, b in ((True, 0.14, 0.86), (False, 0.10, 0.80)):
        g = QLinearGradient(0, 0, w, 0) if horizontal else QLinearGradient(0, 0, 0, h)
        g.setColorAt(0, QColor(0, 0, 0, 0))
        g.setColorAt(a, QColor(0, 0, 0, 255))
        g.setColorAt(b, QColor(0, 0, 0, 255))
        g.setColorAt(1, QColor(0, 0, 0, 0))
        p.fillRect(QRectF(0, 0, w, h), QBrush(g))
    p.end()
    return out


def _loans_line(loans: int, gold: bool) -> str:
    """The marked English loanwords counted in the rank: one line, the same
    on the share image and the Nakama card (owner 2026-10-27)."""
    return (f"英語の外来語 {loans:,} 語" if gold
            else f"{loans:,} English {'loanword' if loans == 1 else 'loanwords'}")


def _supporter_line(gold: bool) -> str:
    """A Ko-fi tip confirmed by the Nakama server (nakama.is_supporter):
    one plain line, the same for any amount (owner 2026-10-27)."""
    return "♥ 言霊サポーター" if gold else "♥ Supported Kotodama"


def render(data: dict, name: str, message: str = "") -> QImage:
    info = data["info"]
    gold = bool(info.get("is_max_amaterasu"))
    msg = (message or "").strip() if gold else ""
    H = 675           # the message fits in the space under the bars (owner: less dead space)
    img = QImage(W, H, QImage.Format.Format_ARGB32_Premultiplied)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    y = _draw_frame(p, info, gold, H)
    # Marked English loanwords counted in the rank (owner 2026-10-20: people
    # compare ranks, so the image says how many of them are loanwords)
    loans = data.get("loans") or 0
    if loans:
        p.setFont(_font(13))
        p.setPen(QColor(GOLD_DARK if gold else "#aaaaaa"))
        p.drawText(QRectF(50, y + 4, 400, 22), Qt.AlignmentFlag.AlignCenter, _loans_line(loans, gold))
    if data.get("supporter"):
        p.setFont(_font(13))
        p.setPen(QColor(GOLD_DARK if gold else "#aaaaaa"))
        p.drawText(QRectF(50, y + (28 if loans else 4), 400, 22), Qt.AlignmentFlag.AlignCenter,
                   _supporter_line(gold))
    x1 = W - 60
    _draw_right(p, data, name, gold, x1)
    # ── message (Amaterasu mode only) ──
    if msg:
        # just under the rank text (ends ≈ y 525) and the frequency bar (≈ 485),
        # above the footer
        p.setFont(_font(17, serif=True))
        p.setPen(QColor(GOLD_DARK))
        p.drawText(QRectF(80, 540, W - 160, H - 540 - 48),
                   Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, msg)
    if data.get("show_loyal", True):
        _draw_loyalty(p, data.get("loyal"), gold, H, data.get("sun"))
    _draw_footer(p, gold, H)
    p.end()
    return img


def _draw_frame(p: QPainter, info: dict, gold: bool, H: int, framed: bool = True):
    """Background, rank picture, rank name, belt and count (the left half),
    shared by the share image and the Nakama profile card."""
    art = _art(info)
    art_rect = QRectF(50, 70, 400, 267)
    bun = QPointF(art_rect.x() + art_rect.width() * 0.494, art_rect.y() + art_rect.height() * 0.19)

    # ── background ──
    if gold:
        bg = QRadialGradient(bun, W * 0.9)
        bg.setColorAt(0, QColor("#ffffff"))
        bg.setColorAt(0.25, QColor("#fffbea"))
        bg.setColorAt(0.6, QColor("#fff0bd"))
        bg.setColorAt(1, QColor("#f2d77f"))
        p.fillRect(QRectF(0, 0, W, H), QBrush(bg))
        # rays from behind her bun
        p.setPen(Qt.PenStyle.NoPen)
        R = W * 1.3
        for i in range(22):
            a = i * 2 * math.pi / 22 + 0.35 * math.sin(i * 2.3)
            half = 0.03 + 0.025 * (0.5 + 0.5 * math.sin(i * 1.7))
            g = QRadialGradient(bun, R)
            g.setColorAt(0, QColor(255, 255, 255, 120))
            g.setColorAt(0.5, QColor(255, 246, 200, 45))
            g.setColorAt(1, QColor(255, 236, 150, 0))
            p.setBrush(QBrush(g))
            p.drawPolygon(QPolygonF([bun,
                                     bun + QPointF(math.cos(a - half) * R, math.sin(a - half) * R),
                                     bun + QPointF(math.cos(a + half) * R, math.sin(a + half) * R)]))
    else:
        bg = QLinearGradient(0, 0, 0, H)
        bg.setColorAt(0, QColor("#202020"))
        bg.setColorAt(1, QColor("#121212"))
        if framed:
            p.fillRect(QRectF(0, 0, W, H), QBrush(bg))
            p.setPen(QPen(_outline(info), 2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(QRectF(8, 8, W - 16, H - 16), 14, 14)
        else:
            # In the Nakama tab: a plain rounded panel, no outline (the
            # window already frames it; owner 2026-10-18).
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(bg))
            p.drawRoundedRect(QRectF(0, 0, W, H), 22, 22)

    # ── rank picture ──
    if art is not None:
        if gold:
            p.drawImage(art_rect, _feathered(art, int(art_rect.width()), int(art_rect.height())))
        else:
            path = QPainterPath()
            path.addRoundedRect(art_rect, 10, 10)
            p.save()
            p.setClipPath(path)
            p.drawImage(art_rect, art)
            p.restore()
            p.setPen(QPen(_outline(info), 2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(art_rect, 10, 10)

    # ── rank name, English name, belt, count ──
    y = art_rect.bottom() + 14
    # The rank kanji in the rank's two colours (owner 2026-10-18: the card
    # has no rank-coloured badge, only the art), top → bottom; a soft white
    # glow when a colour is too dark for the card (Nihonjin, Samurai, Shogun).
    jr = QRectF(art_rect.x(), y, art_rect.width(), 64)
    if gold:
        _glow_text(p, jr, info.get("rank_name_jp", ""), _font(40, bold=True), GOLD_DARK, None)
    else:
        ca = QColor(info.get("rank_color_a", "#ffffff"))
        cb = QColor(info.get("rank_color_b", "#ffffff"))
        g = QLinearGradient(0, jr.top() + 8, 0, jr.bottom() - 8)
        g.setColorAt(0, cb if _luma(cb) > _luma(ca) else ca)   # the lighter one on top
        g.setColorAt(1, ca if _luma(cb) > _luma(ca) else cb)
        dark = min(_luma(ca), _luma(cb)) < 0.22
        _glow_text(p, jr, info.get("rank_name_jp", ""), _font(40, bold=True), QBrush(g),
                   QColor(255, 255, 255) if dark else QColor(0, 0, 0))
    y += 64
    p.setFont(_font(16))
    p.setPen(QColor(GOLD_DARK if gold else "#d8d8d8"))
    p.drawText(QRectF(art_rect.x(), y, art_rect.width(), 26), Qt.AlignmentFlag.AlignCenter,
               "天照大神" if gold else info.get("rank_name_en", ""))
    y += 28
    # The belt on its own line, bigger, in the main rank badge's colours
    # (owner 2026-10-18): white belt light grey, black belt with a white glow,
    # the others with a dark shadow.
    belt_r = QRectF(art_rect.x(), y, art_rect.width(), 32)
    p.setFont(_font(20, bold=True))
    if gold:
        p.setPen(QColor(GOLD_DARK))
        p.drawText(belt_r, Qt.AlignmentFlag.AlignCenter, "十段 黒帯")
    else:
        belt_text = f"{info.get('belt_display_name', '').upper()} BELT"
        name = info.get("belt_name", "")
        colour = QColor("#e0e0e0" if name == "White" else info.get("belt_color", "#ffffff"))
        _glow_text(p, belt_r, belt_text, _font(20, bold=True), colour,
                   QColor(255, 255, 255) if name == "Black" else QColor(0, 0, 0))
    y += 36
    # A short faint rule in the rank's colour: the rank above, the numbers
    # below (owner 2026-10-18: it read as one block).
    y += 8
    if gold:
        rule = QColor(GOLD_DARK)
    else:                                  # the lighter rank colour; grey if both are dark
        rule = max((QColor(info.get("rank_color_a", "#888888")),
                    QColor(info.get("rank_color_b", "#888888"))), key=_luma)
        if _luma(rule) < 0.22:
            rule = QColor("#888888")
    rule.setAlpha(110)
    p.setPen(QPen(rule, 1.5))
    cx = art_rect.center().x()
    p.drawLine(QPointF(cx - 110, y), QPointF(cx + 110, y))
    y += 12
    p.setFont(_font(14))
    p.setPen(QColor(GOLD_DARK if gold else "#aaaaaa"))
    count = info.get("count", 0)
    p.drawText(QRectF(art_rect.x(), y, art_rect.width(), 26), Qt.AlignmentFlag.AlignCenter,
               f"{count:,} 語を習得" if gold else f"{count:,} words learned")
    return y + 26


def _draw_loyalty(p: QPainter, months, gold: bool, H: int, sun: bool = False):
    """Time with Kotodama (loyalty.py), bottom left opposite the footer:
    the tier's gem and "Jade · 6 months with Kotodama". Nothing before
    the first month."""
    from . import loyalty
    try:
        months = int(months or 0)
    except (TypeError, ValueError):
        return
    i = loyalty.tier_index(months, bool(sun))
    if i is None:
        return
    loyalty.paint_gem(p, QRectF(30, H - 42, 26, 26), i)
    p.setFont(_font(11, bold=True))
    p.setPen(QColor(GOLD_DARK if gold else "#b0b0b0"))
    p.drawText(QRectF(62, H - 40, 420, 22), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
               loyalty.line(months, ja=gold, sun=bool(sun)))


def _draw_footer(p: QPainter, gold: bool, H: int):
    p.setFont(_font(10))
    p.setPen(QColor(GOLD_DARK if gold else "#666666"))
    p.drawText(QRectF(0, H - 34, W - 30, 20), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
               "Kotodama 言霊 · JLPT progress for Anki")


def _draw_right(p: QPainter, data: dict, name: str, gold: bool, x1: float):
    """The share image's right column: name, date, bars."""
    x0 = 660
    p.setFont(_font(32, bold=True))
    p.setPen(QColor(GOLD_DARK if gold else "#ffffff"))
    title = name.strip() or ("日本語の旅" if gold else "My Japanese journey")
    p.drawText(QRectF(510, 60, x1 - 510, 50), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
               title)
    d = data["date"]
    p.setFont(_font(13))
    p.setPen(QColor(GOLD_DARK if gold else "#9a9a9a"))
    p.drawText(QRectF(510, 108, x1 - 510, 24), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
               f"JLPT 進捗 · {d.year}年{d.month}月{d.day}日" if gold
               else f"JLPT progress · {d.strftime('%B %d, %Y').replace(' 0', ' ')}")
    p.setFont(_font(12, bold=True))
    p.drawText(QRectF(510, 156, x1 - 510, 22), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
               "JLPT · 語彙・漢字・文法" if gold else "JLPT · vocab + kanji + grammar")
    by = 188
    for lvl, k, n in data["levels"]:
        _bar(p, QRectF(x0, by, x1 - x0, 30), k, n, LEVEL_FG[lvl], gold, lvl)
        by += 44
    by += 14
    p.setFont(_font(12, bold=True))
    p.setPen(QColor(GOLD_DARK if gold else "#9a9a9a"))
    p.drawText(QRectF(510, by, x1 - 510, 22), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
               "頻度 · 書き言葉の最頻出 20,000 語" if gold
               else "Frequency · the 20,000 most common written words")
    by += 30
    fk, fn = data["freq"]
    # The label says what the bar counts; "near-native" marks its far end as
    # the goal, so a half-full bar doesn't read as "Near Native" achieved
    # (owner 2026-10-10).
    _bar(p, QRectF(x0, by, x1 - x0, 30), fk, fn, FREQ_FG, gold, "上位2万語" if gold else "Top 20k")
    goal_c = QColor(GOLD_DARK if gold else FREQ_FG)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(goal_c)
    tip = QPointF(x1 - 12, by + 33)
    p.drawPolygon(QPolygonF([tip, tip + QPointF(-5, 7), tip + QPointF(5, 7)]))
    p.setFont(_font(11, italic=True))
    p.setPen(goal_c)
    p.drawText(QRectF(x0, by + 33, x1 - x0 - 24, 18),
               Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
               "ネイティブ級の語彙" if gold else "near-native vocabulary")
    # JLPT goal (goal.py): "Aiming for JLPT N3 · December 2026", under the bars
    g = data.get("goal")
    if g and data.get("show_goal", True):
        from . import goal
        p.setFont(_font(13, bold=True))
        p.setPen(QColor(GOLD_DARK if gold else LEVEL_FG[g["level"]]))
        p.drawText(QRectF(510, by + 58, x1 - 510, 24), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                   goal.aiming_line(g, ja=gold))


# ── Nakama profile card ─────────────────────────────────────────────────────

def _pair(v):
    """[known, total] from a snapshot, or None."""
    try:
        k, n = int(v[0]), int(v[1])
        return (max(0, k), max(0, n)) if n > 0 else None
    except Exception:
        return None


def render_profile(profile: dict, mine: dict | None, synced: str = "", framed: bool = True) -> QImage:
    """A Nakama member's card (nakama.py): the share image's left half and,
    on the right, separate bars for JLPT vocab (per level), the top 20,000
    frequency words, JLPT kanji and JLPT grammar. mine (your own snapshot,
    None on your own card): a tick on every bar where you are, and the
    difference beside it ("you +40")."""
    data = profile.get("data") or {}
    count = int(data.get("rank") or 0)
    info = rank_data.get_rank_info(count)
    gold = bool(info.get("is_max_amaterasu"))
    rows = []                    # (section label or None, bar label, pair, my pair, colour)
    jl = data.get("jlpt") or {}
    mjl = (mine or {}).get("jlpt") or {}
    for lvl in LEVELS:
        pr = _pair(jl.get(lvl))
        if pr:
            section = None if rows else ("JLPT 語彙" if gold else "JLPT vocabulary")
            rows.append((section, lvl, pr, _pair(mjl.get(lvl)), LEVEL_FG[lvl]))
    fr = _pair(data.get("freq"))
    if fr:
        rows.append(("頻度 · 書き言葉の最頻出 20,000 語" if gold
                     else "Frequency · the 20,000 most common written words",
                     "上位2万語" if gold else "Top 20k", fr, _pair((mine or {}).get("freq")), FREQ_FG))
    for kind, en, ja, short_en, short_ja, col in (
            ("kanji", "JLPT kanji", "JLPT 漢字", "Kanji", "漢字", "#4fc3a1"),
            ("grammar", "JLPT grammar", "JLPT 文法", "Grammar", "文法", "#a493f0")):
        pr = _pair((data.get(kind) or {}).get("All"))
        if pr:
            rows.append((ja if gold else en, short_ja if gold else short_en, pr,
                         _pair(((mine or {}).get(kind) or {}).get("All")), col))

    step, sect = 40, 34
    n_sect = sum(1 for r in rows if r[0])
    # left column + 3 lines (4 with a JLPT goal) + the loyalty line fit
    H = max(714 if data.get("goal") else 690, 170 + len(rows) * step + n_sect * sect + 70)
    img = QImage(W, H, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(Qt.GlobalColor.transparent)        # unframed: rounded corners show through
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    y = _draw_frame(p, info, gold, H, framed) + 8

    # under the rank: this week / month, synced, marked found
    dim = QColor(GOLD_DARK if gold else "#aaaaaa")
    lines = []
    wk, mo = data.get("week"), data.get("month")
    if wk is not None or mo is not None:
        # signed: a week the rank dropped reads -1, not +-1 (owner's screenshot 2026-10-20)
        lines.append((f"今週 {wk or 0:+,} · 今月 {mo or 0:+,}" if gold
                      else f"{wk or 0:+,} this week · {mo or 0:+,} this month"))
    # Marked found: by hand, and English loanwords (the one-click button
    # everyone uses) on their own line, so the hand count means something.
    found, loans = int(data.get("found") or 0), int(data.get("found_loan") or 0)
    if found:
        lines.append(f"発見済み {found:,} 語" if gold
                     else f"{found:,} {'word' if found == 1 else 'words'} marked found")
    if loans:
        # counted toward the rank so far (they join on a schedule); just
        # the number, like the share image (owner 2026-10-27: less clutter)
        lines.append(_loans_line(loans, gold))
    if profile.get("supporter"):      # from the server only (a Ko-fi tip with this code)
        lines.append(_supporter_line(gold))
    g = data.get("goal")              # "N3 2026-12-06" (goal.py); hidden once that day is over
    try:
        lvl, day = str(g).split()
        day = datetime.date.fromisoformat(day)
        if lvl in LEVELS and day >= datetime.date.today():
            from . import goal
            lines.append(goal.aiming_line({"level": lvl, "date": day}, ja=gold))
    except (ValueError, TypeError):
        pass
    p.setFont(_font(13))
    p.setPen(dim)
    for t in lines:
        p.drawText(QRectF(50, y, 400, 22), Qt.AlignmentFlag.AlignCenter, t)
        y += 24

    # right: name, synced, bars
    x0, x1 = 660, W - 175
    p.setFont(_font(32, bold=True))
    p.setPen(QColor(GOLD_DARK if gold else "#ffffff"))
    p.drawText(QRectF(510, 60, W - 60 - 510, 50), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
               profile.get("name") or "Nakama")
    p.setFont(_font(13))
    p.setPen(QColor(GOLD_DARK if gold else "#9a9a9a"))
    p.drawText(QRectF(510, 108, W - 60 - 510, 24), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
               "仲間 · " + synced if synced else "仲間 Nakama")
    if mine is not None:
        p.drawText(QRectF(510, 108, W - 60 - 510, 24), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                   "▏= あなた" if gold else "▏= you")
    by = 150
    for section, label, (k, n), me, col in rows:
        if section:
            by += 6
            p.setFont(_font(12, bold=True))
            p.setPen(QColor(GOLD_DARK if gold else "#9a9a9a"))
            p.drawText(QRectF(510, by, x1 - 510, 22), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                       section)
            by += sect - 6
        r = QRectF(x0, by, x1 - x0, 26)
        _bar(p, r, k, n, col, gold, label)
        if me is not None:
            mk, mn = me
            mx = r.x() + r.width() * min(1.0, mk / mn if mn else 0)
            p.setPen(QPen(QColor(0, 0, 0, 200), 5))
            p.drawLine(QPointF(mx, r.top() - 6), QPointF(mx, r.bottom() + 6))
            p.setPen(QPen(QColor("#ffffff"), 2.5))
            p.drawLine(QPointF(mx, r.top() - 6), QPointF(mx, r.bottom() + 6))
            d = mk - k
            p.setFont(_font(12, bold=True))
            p.setPen(QColor("#7a5a00" if gold else "#7bd88f" if d > 0 else "#ff8a80" if d < 0 else "#9a9a9a"))
            txt = (f"あなた {d:+,}" if gold else f"you {d:+,}") if d else ("同じ" if gold else "even")
            p.drawText(QRectF(x1 + 14, r.y(), W - 30 - x1 - 14, r.height()),
                       Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, txt)
        by += step
    loyal, sun = data.get("loyal"), data.get("sun")
    if mine is None:                # your own card: with the debug preview's months, if any
        from . import loyalty
        loyal, sun = loyalty.shown_months(loyal or 0), loyalty.shown_sun(sun)
    _draw_loyalty(p, loyal, gold, H, sun)
    _draw_footer(p, gold, H)
    p.end()
    return img


# ── dialog ──────────────────────────────────────────────────────────────────

class ShareDialog(QDialog):
    """Name (and, in Amaterasu mode, a message), a live preview, and
    Save PNG… / Copy image. Name and message are remembered."""

    def __init__(self, data: dict, parent=None, on_message_saved=None):
        super().__init__(parent)
        self._data = data
        self._gold = bool(data["info"].get("is_max_amaterasu"))
        self._on_message_saved = on_message_saved
        self.setWindowTitle("Share your progress")
        self.resize(760, 640)
        v = QVBoxLayout(self)

        row = QHBoxLayout()
        row.addWidget(QLabel("Name:"))
        self._name = QLineEdit(saved_name())
        self._name.setPlaceholderText("Your name (shown on the image)")
        row.addWidget(self._name, 1)
        v.addLayout(row)

        # What else the image shows (owner 2026-10-20): each only when there's
        # something to show; remembered.
        from . import loyalty
        opts = QHBoxLayout()
        self._show_loyal = self._show_goal = None
        if loyalty.tier_index(data.get("loyal") or 0, bool(data.get("sun"))) is not None:
            self._show_loyal = QCheckBox("Show time with Kotodama")
            self._show_loyal.setChecked(bool(data.get("show_loyal", True)))
            self._show_loyal.toggled.connect(lambda on: self._toggle("show_loyal", on))
            opts.addWidget(self._show_loyal)
        if data.get("goal"):
            self._show_goal = QCheckBox("Show JLPT goal")
            self._show_goal.setChecked(bool(data.get("show_goal", True)))
            self._show_goal.toggled.connect(lambda on: self._toggle("show_goal", on))
            opts.addWidget(self._show_goal)
        opts.addStretch()
        if self._show_loyal or self._show_goal:
            v.addLayout(opts)

        self._msg = None
        if self._gold:
            v.addWidget(QLabel("Message (shown on the image and engraved on the Overview):"))
            self._msg = QPlainTextEdit(saved_message())
            self._msg.setFixedHeight(84)
            self._msg.setPlaceholderText("A message of your own…")
            v.addWidget(self._msg)

        self._preview = QLabel()
        self._preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview.setMinimumHeight(360)
        v.addWidget(self._preview, 1)

        btns = QHBoxLayout()
        btns.addStretch()
        save = QPushButton("Save PNG…")
        save.clicked.connect(self._save_png)
        copy = QPushButton("Copy image")
        copy.clicked.connect(self._copy)
        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        for b in (save, copy, close):
            btns.addWidget(b)
        v.addLayout(btns)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(250)
        self._timer.timeout.connect(self._render)
        self._name.textChanged.connect(lambda _t: self._timer.start())
        if self._msg is not None:
            self._msg.textChanged.connect(self._timer.start)
        self._render()

        from . import theme
        theme.apply(self, gold=self._gold)
        if self._gold:
            from . import divine_text
            self.setWindowTitle("進捗を共有")
            divine_text.gold_palette(self, True)
            divine_text.apply(self, True)
            divine_text.gold_titlebar(self, True)

    def _toggle(self, key: str, on: bool):
        self._data[key] = on
        self._render()

    def _message(self) -> str:
        return self._msg.toPlainText() if self._msg is not None else ""

    def _render(self):
        self._img = render(self._data, self._name.text(), self._message())
        pm = QPixmap.fromImage(self._img).scaledToWidth(
            min(720, self.width() - 40), Qt.TransformationMode.SmoothTransformation)
        self._preview.setPixmap(pm)

    def _remember(self):
        kv = {"share_name": self._name.text().strip(),
              "share_show_loyalty": bool(self._data.get("show_loyal", True)),
              "share_show_goal": bool(self._data.get("show_goal", True))}
        if self._msg is not None:
            kv["share_message"] = self._message().strip()
        _save_cfg(**kv)
        if self._msg is not None and self._on_message_saved:
            self._on_message_saved(kv["share_message"])

    def _save_png(self):
        self._render()
        import os
        default = os.path.join(os.path.expanduser("~"), "Pictures",
                               f"jlpt-progress-{self._data['date'].isoformat()}.png")
        path, _f = QFileDialog.getSaveFileName(self, "Save image", default, "PNG image (*.png)")
        if path:
            self._img.save(path, "PNG")
            self._remember()

    def _copy(self):
        self._render()
        QApplication.clipboard().setImage(self._img)
        self._remember()
        from aqt.utils import tooltip
        tooltip("画像をコピーしました" if self._gold else "Image copied", parent=self)

    def done(self, r):
        self._remember()
        super().done(r)
