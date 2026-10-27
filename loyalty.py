"""
loyalty.py
Time with Kotodama (owner 2026-10-20): a badge that grows with how long
you've studied with the add-on, the way Discord's Nitro badge grows with
time subscribed — but it has nothing to do with money (the rank stays
purely earned by learning; supporting the add-on is a separate thank-you).

Counting: calendar months in which the add-on recorded at least one day
(history.json, any deck); a month counts once it's over (October counts
from 1 November). A long break pauses the count, it never goes down. Only
days the add-on itself recorded count, not the past the History tab
rebuilds from Anki's review log.

Kept in the collection too (owner 2026-10-20), so a reinstall, a new
computer (after an AnkiWeb sync) or moving to the AnkiWeb version doesn't
reset it: collection config "kotodama_loyalty" = {"months": ["2026-10", …],
"sun": "YYYY-MM-DD"}. Active months from every computer are merged (a set,
so they add up instead of overwriting); written only when something new
is added (≈ once a month).

Sun Diamond (owner 2026-10-20): a secret top tier above Diamond, for 5 years
AND having reached Amaterasu (a real 20,000 at least once: config
"amaterasu_reached", set by the main window, never cleared). The "?" window
lists it with "?" instead of a time.

Shown on the Vocabulary tab (beside the rank header), in the rank "?"
window (the whole ladder), on the share image and on the Nakama card
(bottom left). Nothing before the first month: unlocked when earned.
Honour system, like found marks: a changed PC clock can fake it, and
nothing depends on it.
"""

from __future__ import annotations

import datetime
import math
import os

COL_KEY = "kotodama_loyalty"

# (months, English, Japanese, (light, mid, dark) colours of the gem)
TIERS = [
    (1, "Bronze", "銅", ("#f0b27a", "#c97b3c", "#7a4518")),
    (2, "Silver", "銀", ("#ffffff", "#c7ccd4", "#6f7782")),
    (3, "Gold", "金", ("#fff1a8", "#f2c230", "#9a6b06")),
    # owner 2026-10-20: the metals first, then the gems by preciousness
    (6, "Platinum", "プラチナ", ("#f4fbff", "#b9d3e0", "#5f7d8e")),
    (9, "Jade", "翡翠", ("#c8f0d0", "#5fb88a", "#2c6e4f")),
    (12, "Pearl", "真珠", ("#ffffff", "#efe6f2", "#a99bb8")),
    (18, "Amethyst", "アメジスト", ("#ead2ff", "#9b59d0", "#4b1f74")),
    (24, "Sapphire", "サファイア", ("#a9c4ff", "#3f6ee8", "#142f86")),
    (36, "Emerald", "エメラルド", ("#9effd0", "#12c27a", "#06603b")),
    (48, "Ruby", "ルビー", ("#ffb0bf", "#e8264f", "#7a0a22")),
    (60, "Diamond", "ダイヤモンド", ("#ffffff", "#bff0ff", "#4fb0d8")),
    # secret: 5 years + Amaterasu reached (SUN); its time is shown as "?"
    (60, "Sun Diamond", "太陽のダイヤモンド", ("#fffbe0", "#ffd84a", "#c98a00")),
]
SUN = len(TIERS) - 1          # index of the secret Sun Diamond
SUN_PAD = 0.2                 # its rays reach this far (× size) outside the gem's box

# Debug preview (the Vocabulary tab's hidden debug row): months to show
# instead of the real count, display only (never sent to Nakama).
PREVIEW = {"months": None, "sun": False}

_CACHE = {"key": None, "months": 0}


def _col():
    """The open collection, or None (tests, profile closing)."""
    try:
        from aqt import mw
        return mw.col
    except Exception:
        return None


def _stored() -> dict:
    col = _col()
    if col is None:
        return {}
    try:
        v = col.get_config(COL_KEY, None)
        return v if isinstance(v, dict) else {}
    except Exception:
        return {}


def _store(value: dict):
    col = _col()
    if col is None:
        return
    try:
        col.set_config(COL_KEY, value)
    except Exception:
        pass


def _month(d: datetime.date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def months_with_kotodama() -> int:
    """Calendar months that are over in which the add-on recorded at least
    one day (any deck, on this computer or, via the collection, another)."""
    from . import history
    today = history.today()
    try:
        key = (os.path.getmtime(history._PATH), today)
    except Exception:
        key = None
    if key is not None and key == _CACHE["key"]:
        return _CACHE["months"]
    active = set()
    for deck in history._load().get("decks", {}).values():
        for d in (deck or {}).get("days", {}):
            try:
                active.add(_month(datetime.date.fromisoformat(d)))
            except ValueError:
                pass
    stored = _stored()
    saved = {m for m in stored.get("months", []) if isinstance(m, str)}
    if active - saved:
        _store(dict(stored, months=sorted(active | saved)))
    current = _month(today)
    months = len({m for m in active | saved if m < current})
    _CACHE.update(key=key, months=months)
    return months


def sun_reached() -> bool:
    """Amaterasu reached for real at least once: the add-on's config (set by
    the main window) or the collection (another computer, a reinstall)."""
    flag = None
    try:
        from . import _cfg
        flag = _cfg().get("amaterasu_reached")
    except Exception:
        pass
    stored = _stored()
    if flag and not stored.get("sun"):
        _store(dict(stored, sun=flag if isinstance(flag, str) else "yes"))
    return bool(flag or stored.get("sun"))


def shown_months(real: int | None = None) -> int:
    """The debug preview's months if one is set, else real (or the real count)."""
    if PREVIEW["months"] is not None:
        return PREVIEW["months"]
    return months_with_kotodama() if real is None else real


def shown_sun(real: bool | None = None) -> bool:
    """The debug preview's Amaterasu flag while previewing, else real."""
    if PREVIEW["months"] is not None:
        return PREVIEW["sun"]
    return sun_reached() if real is None else bool(real)


def cycle_preview():
    """Debug row: real → 1 month → 2 → … → 5 years → Sun Diamond → real."""
    steps = [(None, False)] + [(t[0], False) for t in TIERS[:SUN]] + [(TIERS[SUN][0], True)]
    cur = (PREVIEW["months"], PREVIEW["sun"])
    i = steps.index(cur) if cur in steps else 0
    PREVIEW["months"], PREVIEW["sun"] = steps[(i + 1) % len(steps)]


def tier_index(months: int, sun: bool = False) -> int | None:
    """Index into TIERS of the tier reached, None before the first month.
    Sun Diamond needs sun (Amaterasu reached) as well as its time."""
    idx = None
    for i, t in enumerate(TIERS):
        if months >= t[0] and (i != SUN or sun):
            idx = i
    return idx


def duration(months: int, ja: bool = False) -> str:
    """1 month, 6 months, 1 year, 1.5 years, 5 years (1か月, 1年, 1年半)."""
    if months < 12:
        return f"{months}か月" if ja else f"{months} month{'s' if months != 1 else ''}"
    years, rest = divmod(months, 12)
    half = rest >= 6
    if ja:
        return f"{years}年半" if half else f"{years}年"
    text = f"{years}.5" if half else f"{years}"
    return f"{text} year{'s' if text != '1' else ''}"


def line(months: int, ja: bool = False, sun: bool = False) -> str:
    """"Jade · 6 months with Kotodama" (翡翠 · 言霊と6か月), "" before the first month."""
    i = tier_index(months, sun)
    if i is None:
        return ""
    t = TIERS[i]
    return f"{t[2]} · 言霊と{duration(months, True)}" if ja else f"{t[1]} · {duration(months)} with Kotodama"


def next_step(months: int, ja: bool = False, sun: bool = False) -> str:
    """"Next: Pearl at 9 months" / "Next: Sun Diamond at ?" / "" at the top."""
    for i, t in enumerate(TIERS):
        if i == SUN:
            if sun and months >= t[0]:
                return ""
            return f"次：{t[2]}（？）" if ja else f"Next: {t[1]} at ?"
        if months < t[0]:
            return f"次：{t[2]}（{duration(t[0], True)}）" if ja else f"Next: {t[1]} at {duration(t[0])}"
    return ""


# ── the gem ──────────────────────────────────────────────────────────────────

def paint_gem(p, rect, index: int, dim: bool = False):
    """A cut gem in the tier's colours inside rect (QRectF), one shape for
    every tier like Discord's badges; dim = a tier not reached yet."""
    from aqt.qt import QColor, QLinearGradient, QPen, QPointF, QPolygonF, Qt, QBrush
    light, mid, dark = (QColor(c) for c in TIERS[index][3])
    if dim:
        for c in (light, mid, dark):
            g = (c.red() + c.green() + c.blue()) // 3
            c.setRgb((c.red() + 2 * g) // 6, (c.green() + 2 * g) // 6, (c.blue() + 2 * g) // 6)
    x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()

    def pt(fx, fy):
        return QPointF(x + fx * w, y + fy * h)

    p.save()
    p.setRenderHint(p.RenderHint.Antialiasing)
    if index == SUN and not dim:
        # Sun Diamond: golden rays around a full-size gem (as big as Diamond;
        # owner 2026-10-20), reaching SUN_PAD outside rect — gem_pixmap
        # leaves that margin, the share card has room for it.
        ray = QColor("#ffd84a")
        ray.setAlpha(190)
        p.setPen(QPen(ray, max(1.0, w * 0.05), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        c = pt(0.5, 0.5)
        for k in range(12):
            a = k * math.pi / 6 + math.pi / 12
            r0, r1 = 0.54 * w, (0.5 + SUN_PAD) * w
            p.drawLine(QPointF(c.x() + math.cos(a) * r0, c.y() + math.sin(a) * r0),
                       QPointF(c.x() + math.cos(a) * r1, c.y() + math.sin(a) * r1))
    tl, tr = pt(0.30, 0.10), pt(0.70, 0.10)          # table
    gl, gr = pt(0.04, 0.36), pt(0.96, 0.36)          # girdle
    culet = pt(0.50, 0.94)
    # pavilion (lower part): darker
    g = QLinearGradient(pt(0.5, 0.36), culet)
    g.setColorAt(0, mid)
    g.setColorAt(1, dark)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(g))
    p.drawPolygon(QPolygonF([gl, gr, culet]))
    # crown (upper part): lighter
    g = QLinearGradient(pt(0.5, 0.10), pt(0.5, 0.36))
    g.setColorAt(0, light)
    g.setColorAt(1, mid)
    p.setBrush(QBrush(g))
    p.drawPolygon(QPolygonF([tl, tr, gr, gl]))
    # facet lines
    edge = QColor(dark)
    edge.setAlpha(150)
    p.setPen(QPen(edge, max(0.8, w * 0.025)))
    for a, b in ((tl, pt(0.20, 0.36)), (tr, pt(0.80, 0.36)), (tl, pt(0.40, 0.36)), (tr, pt(0.60, 0.36)),
                 (pt(0.20, 0.36), culet), (pt(0.40, 0.36), culet), (pt(0.60, 0.36), culet),
                 (pt(0.80, 0.36), culet), (gl, gr)):
        p.drawLine(a, b)
    # outline
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(QPen(dark.darker(130), max(1.0, w * 0.04)))
    p.drawPolygon(QPolygonF([tl, tr, gr, culet, gl]))
    if not dim:
        # a glint on the table
        glint = QColor(255, 255, 255, 210)
        p.setPen(QPen(glint, max(1.0, w * 0.05), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(pt(0.36, 0.18), pt(0.46, 0.18))
        if index >= SUN - 1:                       # Diamond and Sun Diamond sparkle
            for cx, cy, s in ((0.86, 0.10, 0.10), (0.12, 0.62, 0.07)):
                c = pt(cx, cy)
                d = s * w
                p.drawLine(QPointF(c.x() - d, c.y()), QPointF(c.x() + d, c.y()))
                p.drawLine(QPointF(c.x(), c.y() - d), QPointF(c.x(), c.y() + d))
    p.restore()


def gem_pixmap(size: int, index: int, dim: bool = False):
    """The gem as a QPixmap (labels), drawn at the screen's pixel ratio. The
    lit Sun Diamond's pixmap is bigger by its rays (SUN_PAD each side); its
    gem stays size, like every other tier's."""
    from aqt.qt import QPixmap, QPainter, QRectF, Qt, QApplication
    ratio = 2.0
    try:
        ratio = max(1.0, QApplication.primaryScreen().devicePixelRatio())
    except Exception:
        pass
    pad = round(size * SUN_PAD) if index == SUN and not dim else 0
    full = size + 2 * pad
    pm = QPixmap(int(full * ratio), int(full * ratio))
    pm.fill(Qt.GlobalColor.transparent)
    pm.setDevicePixelRatio(ratio)
    p = QPainter(pm)
    paint_gem(p, QRectF(pad, pad, size, size), index, dim)
    p.end()
    return pm
