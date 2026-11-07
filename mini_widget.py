"""
mini_widget.py
An optional, always-on mini version of the Overview progress bars,
shown on Anki's main (deck list) screen.

Implementation: injected as HTML/CSS into the deck browser via
gui_hooks.deck_browser_will_render_content. The glow effect from
LevelBar (progress_dialog.py) is approximated with layered CSS
box-shadows, driven by the same percentage -> glow-params curve.
"""

import re

from aqt import mw, gui_hooks

from . import card_state
from .card_state import hook_guard
from . import jlpt_data
from . import rank_data
from .jlpt_data import LEVELS, LEVEL_COLORS as LEVEL_FG, LEVEL_BG
from .overrides import Overrides


# ── glow curve (mirrors LevelBar._glow_params, expressed for CSS) ──────────────

# LevelBar's glow pixel values were tuned for its 32px-tall bar. The mini
# widget's bar is 14px tall, so scale all glow spread/blur distances by the
# same ratio to keep the glow proportionally similar in size.
_GLOW_SCALE = 14 / 32


def _glow_box_shadow(pct: float, color: str, scale: float = _GLOW_SCALE) -> str:
    """
    Build a CSS box-shadow value approximating LevelBar's layered glow halo,
    using the same percentage -> (layers, max_spread, peak_alpha) curve,
    scaled down to match the mini bar's height.
    """
    if pct <= 0.0:
        return "none"

    if pct >= 1.0:
        # Laser: bright multi-layer glow + soft wide bloom
        def s(px):
            return max(1, round(px * scale))
        return (
            f"0 0 {s(4)}px {s(1)}px rgba(255,255,255,0.9), "
            f"0 0 {s(10)}px {s(3)}px {color}, "
            f"0 0 {s(22)}px {s(8)}px {color}AA, "
            f"0 0 {s(38)}px {s(14)}px {color}55"
        )

    t = min(pct, 0.999) ** 0.55
    layers     = 2 + int(t * 6)        # 2 .. 7
    max_spread = int(3 + t * 22)       # 3 .. 24
    peak_alpha = int(40 + t * 195)     # 40 .. 235

    shadows = []
    for i in range(1, layers + 1):
        frac   = i / layers
        spread = max(1, int(max_spread * (1.0 - frac * 0.75)))
        spread = max(1, round(spread * scale))
        alpha  = min(int(peak_alpha * (frac ** 1.4)), 255)
        alpha_hex = format(alpha, "02x")
        shadows.append(f"0 0 {spread * 2}px {spread}px {color}{alpha_hex}")

    return ", ".join(shadows)


# ── HTML generation ─────────────────────────────────────────────────────────

def _bar_html(level: str, known: int, total: int, force_max_gold: bool = False) -> str:
    pct   = (known / total) if total else 0.0
    if force_max_gold:
        # Use the Amaterasu fill color (rank_color_a) as the main fill, and
        # the accent color (rank_color_b, near-white gold) as both the gradient
        # dark stop and the glow color — matches the desktop RankBar exactly and
        # prevents the bar from looking gold-to-black (which reads as dim/dark).
        fg         = rank_data.MAX_RANK_FILL_COLOR              # "#f5c518"
        bg         = rank_data.RANK_COLORS["Amaterasu"][1]      # "#fff8c5" near-white gold
        glow_color = rank_data.RANK_COLORS["Amaterasu"][1]
    else:
        fg         = LEVEL_FG[level]
        bg         = LEVEL_BG[level]
        glow_color = fg
    pct_w = max(0.0, min(pct, 1.0)) * 100
    glow  = _glow_box_shadow(pct, glow_color)
    # Amaterasu: text black (like her hair) over the gold fill and gold over
    # the empty track — a hard-stop gradient clipped to the text, which
    # spans the whole track, so the switch lines up with the fill's end.
    text_style = (
        f" style=\"color: transparent; text-shadow: none;"
        f" background: linear-gradient(90deg, #0d0b08 {pct_w:.2f}%, #f5c518 {pct_w:.2f}%);"
        f" -webkit-background-clip: text; background-clip: text;\""
        if force_max_gold else "")
    # Laser border: white for normal 100%, gold-outline for Amaterasu 100%
    laser_border = (
        "border: 1px solid rgba(255,255,255,0.85);"
        if pct >= 1.0 and not force_max_gold else
        f"border: 1px solid {rank_data.RANK_COLORS['Amaterasu'][1]}CC;" if force_max_gold else ""
    )

    return f"""
    <div class="jlpt-mini-row">
      <span class="jlpt-mini-label" style="color:{fg};">{level}</span>
      <div class="jlpt-mini-track">
        <div class="jlpt-mini-fill" style="
              width:{pct_w:.2f}%;
              background: linear-gradient(180deg, {fg} 0%, {bg} 100%);
              box-shadow: {glow};
              {laser_border}
        "></div>
        <span class="jlpt-mini-text"{text_style}>{jlpt_data.format_pct(known, total)} ({known:,} / {total:,})</span>
      </div>
    </div>
    """


def _goal_html(results: dict, deck_name: str, gold: bool) -> str:
    """JLPT goal (goal.py): "Today: 9 / 14 words" under the level bars, with
    a thin bar that fills as you go. Vocab only (owner: one number here).
    Nothing without a goal or outside its learning phase."""
    try:
        from . import goal
        st = goal.status(results, deck_name)
        text = goal.today_line(st, ja=gold) if st else None
    except Exception:
        return ""
    if not text:
        return ""
    v = st["kinds"]["vocab"]
    got, need = (v["week"], v["per_week"]) if v.get("weekly") else (v["today"], v["per_day"])
    pct = min(1.0, got / need) * 100 if need else 100.0
    done = goal.done_today(v)
    if gold:
        fill, col = "#f5c518", "#f5c518"
    else:
        fill = "#7bd88f" if done else LEVEL_FG[st["level"]]
        col = "#7bd88f" if done else "#cfcfcf"
    return f"""
    <div class="jlpt-mini-goal" title="JLPT {st['level']} goal: new words learned today / today's share">
      <div class="jlpt-mini-goal-text" style="color:{col};">{text}</div>
      <div class="jlpt-mini-goal-track"><div class="jlpt-mini-goal-fill"
           style="width:{pct:.1f}%; background:{fill}; box-shadow: 0 0 6px {fill}88;"></div></div>
    </div>
    """


def _darker(color: str, factor: int) -> str:
    """Hex colour darkened like QColor.darker(factor)."""
    import colorsys
    h = color.lstrip("#")
    r, g, b = (int(h[k:k + 2], 16) / 255 for k in (0, 2, 4))
    hh, ss, vv = colorsys.rgb_to_hsv(r, g, b)
    r, g, b = colorsys.hsv_to_rgb(hh, ss, vv * 100 / factor)
    return "#" + "".join(f"{round(c * 255):02x}" for c in (r, g, b))


# The two small rank bars are 6px tall: scale the glow to match.
_SMALL_GLOW_SCALE = 8 / 32


def _small_bar_html(pct: float, top: str, bottom: str, glow_color: str, title: str,
                    centred: bool = False) -> str:
    """Thin bar with the same vertical gradient and glow language as the
    main window's bars. Fills left→right like RankBar, or (centred=True)
    from the middle outwards like BeltBar."""
    pct   = max(0.0, min(pct, 1.0))
    glow  = _glow_box_shadow(pct, glow_color, _SMALL_GLOW_SCALE)
    return f"""
      <div class="jlpt-mini-small-track" title="{title}">
        <div class="jlpt-mini-small-fill{' centred' if centred else ''}" style="width:{pct * 100:.2f}%;
             background: linear-gradient(180deg, {top} 0%, {bottom} 100%);
             box-shadow: {glow};"></div>
      </div>"""


_ART_URIS: dict[str, str] = {}   # rank name → data: URI, built once per rank


def _art_uri(rank_name_en: str) -> str:
    """The rank's art as a data: URI ("" if it has none). The JPEGs are
    small (≤ 42 KB), so they're embedded as they are."""
    if rank_name_en not in _ART_URIS:
        uri = ""
        try:
            import base64
            from . import rank_images
            data = rank_images.get_rank_art(rank_name_en)
            if data:
                uri = "data:image/jpeg;base64," + base64.b64encode(data).decode("ascii")
        except Exception:
            pass
        _ART_URIS[rank_name_en] = uri
    return _ART_URIS[rank_name_en]


def _loop_url(rank_name_en: str) -> str:
    """Web address of the rank's animated loop ("" if it has none), served
    from media/ by Anki (setWebExports in __init__)."""
    try:
        from . import rank_video
        if rank_video.clip(rank_name_en, "loop") is None:
            return ""
        folder = mw.addonManager.addonFromModule(__name__)
        return f"/_addons/{folder}/media/{rank_name_en.lower()}_loop.webm"
    except Exception:
        return ""


def _hex_rgba(color: str, alpha: int) -> str:
    h = color.lstrip("#")
    return f"rgba({int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)},{alpha / 255:.2f})"


def _art_badge_style(info: dict) -> str:
    """Inline style for the rank section as a mini RankBadge: the badge's
    gradient (rank colour → accent at alpha 160 → 100), accent border, and
    its glow scaled down (glow starts at Nihonjin, peaks at Amaterasu)."""
    from .progress_dialog import _rank_glow_params
    a, b = info["rank_color_a"], info["rank_color_b"]
    if info.get("is_max_amaterasu"):          # Amaterasu MODE (20,000), not the rank
        # Divine mode (owner 2026-10-09: at 20,000 everything is maxed, so
        # it should feel like a god, not stay subtle). She is the source of
        # light, so the whole badge is bright light gold — no dark gold
        # anywhere (owner); its text is dark gold instead of white. The glow
        # is the jlpt-divine animation (CSS), so no static box-shadow here.
        return ("background: radial-gradient(ellipse at 50% 38%, #ffffff 0%,"
                " #fffbea 35%, #fff3c4 70%, #ffe99a 100%);"
                "border: 1px solid #fffbe6;")
    blur, alpha = _rank_glow_params(info["rank_index"])
    glow = (f"box-shadow: 0 0 {max(4, blur // 4)}px {max(1, blur // 16)}px "
            f"{_hex_rgba(b, alpha)};" if blur else "")
    return (f"background: linear-gradient(90deg, {_hex_rgba(a, 160)}, {_hex_rgba(b, 100)});"
            f"border: 1px solid {_hex_rgba(b, 120)}; {glow}")


def _rank_html(info: dict, show_art: bool = False) -> str:
    """Rank + belt line, then a main-rank bar (0–20,000, rank colours, like
    RankBar) and a current-belt bar (belt colour, like BeltBar). show_art:
    the rank picture on the rank's badge background above them (a mini
    version of the Overview's RankBadge)."""
    rank_top  = info["rank_color_a"]
    # Amaterasu keeps a light-gold bottom stop instead of a dark one (RankBar).
    rank_bot  = (info["rank_color_b"] if info["rank_name_en"] == "Amaterasu"
                 else _darker(rank_top, 260))
    belt_top  = info["belt_bar_color"]
    if info["is_max"]:
        rank_tip = belt_tip = "Max rank reached"
    else:
        rank_tip = (f"{jlpt_data.format_progress(info['count'], info['max_cards'])}"
                    f" learned words toward 20,000")
        belt_tip = f"{info['cards_to_next']:,} more learned words to the next belt"
    # Gold mode (20,000): Japanese like the rest of the add-on.
    rank_line = ("<b>天照</b> · 十段 黒帯" if info.get("is_max_amaterasu") else
                 f"<b>{info['rank_name_jp']}</b> {info['rank_name_en']} · "
                 f"{info['belt_display_name']} Belt")
    art = _art_uri(info["rank_name_en"]) if show_art else ""
    if show_art:
        divine = " jlpt-divine" if info.get("is_max_amaterasu") else ""
        img = f'<img class="jlpt-mini-art" src="{art}" alt="" draggable="false">' if art else ''
        # Animated like the Overview: every rank with a loop clip (Nihonjin
        # and up, owner 2026-10-31), Amaterasu only in Amaterasu mode
        # (owner 2026-10-16); the still picture is the poster until it
        # plays, and stays if it can't.
        moves = info["rank_name_en"] != "Amaterasu" or info.get("is_max_amaterasu")
        video = _loop_url(info["rank_name_en"]) if moves and art else ""
        if video:
            img = (f'<video class="jlpt-mini-art" src="{video}" poster="{art}" '
                   f'autoplay loop muted playsinline disablepictureinpicture></video>')
        if divine and art:
            # Rays turn behind her from her hair bun (::before), spilling
            # past the badge; her picture's edges are feathered so she floats.
            img = f'<div class="jlpt-divine-art-wrap">{img}</div>'
        return f"""
    <div class="jlpt-mini-rank jlpt-mini-rank-art{divine}" style="{_art_badge_style(info)}">
      {img}
      <div class="jlpt-mini-rank-row">
        <span class="jlpt-mini-rank-text">{rank_line}</span>
        <span class="jlpt-mini-rank-count">{info['count']:,}</span>
      </div>
      {_small_bar_html(info['overall_pct'], rank_top, rank_bot, info['rank_color_b'], rank_tip)}
      {_small_bar_html(info['belt_pct'], belt_top, _darker(belt_top, 280), belt_top, belt_tip,
                       centred=True)}
    </div>
    """
    return f"""
    <div class="jlpt-mini-rank">
      <div class="jlpt-mini-rank-row">
        <span class="jlpt-mini-rank-text">{rank_line}</span>
        <span class="jlpt-mini-rank-count">{info['count']:,}</span>
      </div>
      {_small_bar_html(info['overall_pct'], rank_top, rank_bot, info['rank_color_b'], rank_tip)}
      {_small_bar_html(info['belt_pct'], belt_top, _darker(belt_top, 280), belt_top, belt_tip,
                       centred=True)}
    </div>
    """


def _rankup_html(info: dict, new_rank: bool) -> str:
    """Reminder of a rank-up that happened while reviewing. Stays until the
    ✕ is clicked, the add-on is opened from the widget, or the next review
    session starts (rank_toast.peek_unseen)."""
    head = "New rank!" if new_rank else "Belt up!"
    return f"""
    <div class="jlpt-mini-rankup">
      <span class="jlpt-mini-rankup-x" title="Dismiss"
            onclick="event.stopPropagation(); event.preventDefault();
                     pycmd('jlpt_dismiss_rankup'); return false;">✕</span>
      <b>⬆ {head}</b> {info['rank_name_jp']} {info['rank_name_en']} ·
      {info['belt_display_name']} Belt
    </div>
    """


def _widget_html(results: dict, deck_name: str = "", ignore_suspended: bool = False,
                 show_rank: bool = True, rankup=None, show_art: bool = False,
                 neon: bool = False, neon_hold: bool = False,
                 corner: str = "tr") -> str:
    # Black Belt Amaterasu global override: when the configured deck has
    # reached 20,000 learned words, every JLPT bar in the mini widget
    # turns bright gold, matching the main Overview tab's rank bars.
    force_max_gold = False
    rank_info      = None
    # DEBUG "Force Amaterasu": exactly 20,000 and every bar full.
    full = card_state.DEBUG_FULL["on"]
    try:
        if deck_name:
            rank_info = rank_data.get_rank_info(
                rank_data.MAX_CARDS if full else card_state.rank_count(deck_name, ignore_suspended))
            force_max_gold = rank_info["is_max_amaterasu"]
    except Exception:
        force_max_gold = False
        rank_info      = None

    rows = []
    for lvl in LEVELS:
        d     = results.get(lvl, {"known_words": [], "missing_words": []})
        known = len(d["known_words"])
        total = known + len(d["missing_words"])
        if full:
            known = total
        rows.append(_bar_html(lvl, known, total, force_max_gold=force_max_gold))
    goal_row = _goal_html(results, deck_name, force_max_gold)
    if goal_row:
        rows.append(goal_row)
    if rankup is not None:
        rows.insert(0, _rankup_html(*rankup))
    if show_rank and rank_info is not None:
        rows.append(_rank_html(rank_info, show_art))
    rows_html, neon_css = ''.join(rows), ""
    if neon and not force_max_gold and _flicker_on():
        rows_html, neon_css = _neon(rows_html, hold=neon_hold)

    return f"""
    <style>
      /* Nothing in the widget can be dragged (owner 2026-10-26: a click that
         slipped dragged the rank picture or the link, and dropping it on Anki
         gave "Unsupported file type"). */
      #jlpt-mini-widget, #jlpt-mini-widget * {{
        -webkit-user-drag: none;
        user-select: none;
      }}
      #jlpt-mini-widget {{
        position: absolute;
        top: 0;
        right: 0;
        width: 220px;
        margin: 8px 12px;
        padding: 10px 12px;
        background: rgba(20,20,20,0.55);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 8px;
        font-family: inherit;
        pointer-events: auto;
        cursor: pointer;
        box-sizing: border-box;
        z-index: 10;
        text-decoration: none;
        display: block;
        /* Anki wraps the deck list in <center>, whose -webkit-center
           alignment centres every block inside (it centred the rank bar's
           fill). The belt bar centres itself with margin: auto. */
        text-align: left;
        transition: background 0.15s ease, border-color 0.15s ease;
      }}
      #jlpt-mini-widget:hover {{
        background: rgba(35,35,35,0.7);
        border-color: rgba(255,255,255,0.18);
      }}
      .jlpt-mini-row {{
        display: flex;
        align-items: center;
        margin-bottom: 4px;
      }}
      .jlpt-mini-row:last-child {{
        margin-bottom: 0;
      }}
      .jlpt-mini-label {{
        width: 24px;
        font-size: 11px;
        font-weight: bold;
        text-align: center;
        flex-shrink: 0;
      }}
      .jlpt-mini-track {{
        position: relative;
        flex: 1;
        height: 14px;
        border-radius: 4px;
        background: #1e1e1e;
        overflow: visible;
        margin-left: 6px;
      }}
      .jlpt-mini-fill {{
        position: absolute;
        top: 0; left: 0; bottom: 0;
        border-radius: 4px;
        min-width: 0;
        transition: width 0.2s ease;
      }}
      .jlpt-mini-goal {{
        margin: 6px 0 2px;
      }}
      .jlpt-mini-goal-text {{
        font-size: 11px;
        font-weight: 600;
        margin-bottom: 3px;
      }}
      .jlpt-mini-goal-track {{
        height: 4px;
        border-radius: 2px;
        background: #1e1e1e;
        position: relative;
      }}
      .jlpt-mini-goal-fill {{
        position: absolute;
        top: 0; left: 0; bottom: 0;
        border-radius: 2px;
      }}
      .jlpt-mini-rank {{
        margin-top: 8px;
        padding-top: 6px;
        border-top: 1px solid rgba(255,255,255,0.08);
      }}
      .jlpt-mini-rank-art {{
        /* Mini RankBadge: background, border and glow set inline per rank */
        margin-top: 10px;
        padding: 6px 8px 8px;
        border-radius: 8px;
      }}
      .jlpt-mini-rank-art .jlpt-mini-rank-text {{
        color: #fff;
        text-shadow: 0 1px 2px rgba(0,0,0,0.9);
      }}
      .jlpt-mini-rank-art .jlpt-mini-rank-count {{
        color: #eee;
        text-shadow: 0 1px 2px rgba(0,0,0,0.9);
      }}
      .jlpt-mini-art {{
        display: block;
        width: 100%;
        height: auto;
        margin: 0 auto 6px;
        border-radius: 5px;
      }}
      video.jlpt-mini-art {{
        aspect-ratio: 3 / 2;      /* sized before the video loads */
        object-fit: cover;
        pointer-events: none;
      }}
      /* Amaterasu: a breathing divine glow on the badge and her picture */
      .jlpt-divine {{
        animation: jlpt-divine-glow 3.2s ease-in-out infinite;
      }}
      .jlpt-divine .jlpt-mini-art {{
        animation: jlpt-divine-art 3.2s ease-in-out infinite;
      }}
      .jlpt-divine-art-wrap {{
        position: relative;
      }}
      /* Ray fan centred on her bun (49.4% / 19% of the picture), turning
         slowly, fading out with distance; drawn behind her picture but over
         the N5–N1 bars above, so it breaks out of the badge. */
      .jlpt-divine-art-wrap::before {{
        content: "";
        position: absolute;
        left: 49.4%; top: 19%;
        width: 460px; height: 460px;
        margin: -230px 0 0 -230px;
        background: repeating-conic-gradient(from 0deg,
                      rgba(255,255,255,0.75) 0deg 4deg, rgba(255,246,200,0.25) 4deg 7deg,
                      rgba(255,255,255,0) 7deg 15deg);
        -webkit-mask-image: radial-gradient(circle, #000 0%, rgba(0,0,0,0.7) 22%,
                                            rgba(0,0,0,0.25) 40%, transparent 62%);
        animation: jlpt-rays 48s linear infinite, jlpt-rays-breathe 3.2s ease-in-out infinite;
        pointer-events: none;
        z-index: 0;
      }}
      .jlpt-divine-art-wrap .jlpt-mini-art {{
        position: relative;
        z-index: 1;
        border-radius: 0;
        animation: none;
        /* feathered edges: she floats in the light */
        -webkit-mask-image: linear-gradient(to right, transparent 0%, #000 14%, #000 86%, transparent 100%),
                            linear-gradient(to bottom, transparent 0%, #000 12%, #000 78%, transparent 100%);
        -webkit-mask-composite: source-in;
        mask-composite: intersect;
      }}
      .jlpt-divine .jlpt-mini-rank-row, .jlpt-divine .jlpt-mini-small-track {{
        position: relative;
        z-index: 1;
      }}
      @keyframes jlpt-rays {{
        to {{ transform: rotate(360deg); }}
      }}
      @keyframes jlpt-rays-breathe {{
        0%, 100% {{ opacity: 0.65; }}
        50%      {{ opacity: 1; }}
      }}
      .jlpt-divine .jlpt-mini-rank-text, .jlpt-divine .jlpt-mini-rank-count {{
        color: #6b4a00;
        text-shadow: 0 1px 0 rgba(255,255,255,0.7);
      }}
      .jlpt-divine .jlpt-mini-rank-text b {{
        color: #5a3c00;
      }}
      .jlpt-divine .jlpt-mini-small-track {{
        background: #f3dc8a;
        box-shadow: inset 0 1px 2px rgba(120,80,0,0.35);
      }}
      @keyframes jlpt-divine-glow {{
        0%, 100% {{ box-shadow: 0 0 8px 2px #ffffff, 0 0 22px 8px rgba(255,248,197,0.95),
                               0 0 44px 16px rgba(245,197,24,0.75), 0 0 80px 30px rgba(245,197,24,0.35); }}
        50%      {{ box-shadow: 0 0 12px 4px #ffffff, 0 0 32px 12px rgba(255,248,197,1),
                               0 0 64px 24px rgba(245,197,24,0.9), 0 0 120px 46px rgba(245,197,24,0.5); }}
      }}
      @keyframes jlpt-divine-art {{
        0%, 100% {{ box-shadow: 0 0 8px 2px rgba(255,255,255,0.9), 0 0 18px 6px rgba(255,248,197,0.8); }}
        50%      {{ box-shadow: 0 0 14px 4px #ffffff, 0 0 30px 10px rgba(255,248,197,1); }}
      }}
      .jlpt-dust {{
        position: absolute; inset: 0;
        pointer-events: none;
        overflow: visible;
        z-index: 3;
      }}
      .jlpt-dust span {{
        position: absolute;
        bottom: -6px;
        border-radius: 50%;
        background: radial-gradient(circle, #ffffff 0%, #fff3c4 35%, rgba(255,215,90,0.35) 65%,
                                    rgba(255,200,60,0) 100%);
        animation-name: jlpt-dust-rise, jlpt-dust-twinkle;
        animation-timing-function: linear, ease-in-out;
        animation-iteration-count: infinite, infinite;
      }}
      @keyframes jlpt-dust-rise {{
        0%   {{ bottom: -6px; transform: translateX(0); opacity: 0; }}
        10%  {{ opacity: 1; }}
        50%  {{ transform: translateX(var(--sway)); }}
        90%  {{ opacity: 0.9; }}
        100% {{ bottom: 100%; transform: translateX(0); opacity: 0; }}
      }}
      @keyframes jlpt-dust-twinkle {{
        0%, 100% {{ filter: brightness(0.8); }}
        50%      {{ filter: brightness(1.4); }}
      }}
      #jlpt-mini-widget.jlpt-divine-aura {{
        border-color: rgba(255,248,197,0.7);
        box-shadow: 0 0 18px 4px rgba(245,197,24,0.45), inset 0 0 18px rgba(245,197,24,0.18);
      }}
      .jlpt-mini-rank-row {{
        display: flex;
        align-items: baseline;
        font-size: 10px;
      }}
      .jlpt-mini-rank-text {{
        flex: 1;
        min-width: 0;
        color: #ddd;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }}
      .jlpt-mini-rank-count {{
        flex-shrink: 0;
        margin-left: 6px;
        color: #999;
      }}
      .jlpt-mini-small-track {{
        height: 6px;
        margin-top: 5px;
        /* Full widget width (owner preferred this over lining up with the
           N5–N1 tracks). */
        border-radius: 3px;
        background: #1e1e1e;
      }}
      .jlpt-mini-small-fill {{
        height: 100%;
        border-radius: 3px;
      }}
      .jlpt-mini-small-fill.centred {{
        margin: 0 auto;   /* grows outwards both ways */
      }}
      .jlpt-mini-rankup {{
        margin-bottom: 8px;
        padding: 5px 8px;
        border-radius: 6px;
        border: 1px solid {rank_data.MAX_RANK_FILL_COLOR};
        background: rgba(245,197,24,0.12);
        color: #fff3c4;
        font-size: 10px;
        animation: jlpt-rankup-pulse 1.4s ease-in-out 4;
      }}
      .jlpt-mini-rankup-x {{
        float: right;
        margin-left: 6px;
        color: #c9b26a;
        cursor: pointer;
      }}
      .jlpt-mini-rankup-x:hover {{
        color: #ffffff;
      }}
      .jlpt-mini-rankup b {{
        color: {rank_data.MAX_RANK_FILL_COLOR};
      }}
      @keyframes jlpt-rankup-pulse {{
        0%, 100% {{ box-shadow: 0 0 2px 0 rgba(245,197,24,0.3); }}
        50%      {{ box-shadow: 0 0 12px 3px rgba(245,197,24,0.8); }}
      }}
      .jlpt-mini-text {{
        position: absolute;
        top: 0; left: 0; right: 0; bottom: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 9px;
        font-weight: bold;
        color: #fff;
        text-shadow: 0 1px 1px rgba(0,0,0,0.8);
        white-space: nowrap;
        pointer-events: none;
      }}
      /* Corners (owner 2026-11-07): drag the widget and it snaps to the
         corner of the quarter you drop it in. The top ones scroll with the
         page as before; the bottom ones stay at the window's bottom edge. */
      #jlpt-mini-widget.jlpt-c-tl {{ right: auto; left: 0; }}
      #jlpt-mini-widget.jlpt-c-bl, #jlpt-mini-widget.jlpt-c-br {{
        position: fixed; top: auto; bottom: 0;
      }}
      #jlpt-mini-widget.jlpt-c-bl {{ right: auto; left: 0; }}
      #jlpt-mini-widget.jlpt-mini-dragging {{
        position: fixed; right: auto; bottom: auto;
        z-index: 1000; cursor: grabbing; opacity: 0.85;
      }}
      /* Narrow window (owner 2026-10-28): the corner widget would cover the
         deck list, so it drops into the page under the stats instead. */
      #jlpt-mini-widget.jlpt-mini-docked {{
        position: static;
        margin: 16px auto 8px;
      }}
      {neon_css}
    </style>
    <a id="jlpt-mini-widget" href="#" class="jlpt-c-{corner}{' jlpt-divine-aura' if force_max_gold else ''}"
       onclick="if (!window.jlptMiniDragged) pycmd('jlpt_open_progress'); return false;"
       draggable="false" ondragstart="return false;"
       title="Open Kotodama">
      {rows_html}
      {_dust_html() if force_max_gold else ''}
    </a>
    <script>(function(){{
      function fit(){{
        var w = document.getElementById('jlpt-mini-widget');
        var t = document.getElementById('decktable') || document.querySelector('table');
        if (!w || !t) return;
        w.classList.remove('jlpt-mini-docked');
        var a = w.getBoundingClientRect(), b = t.getBoundingClientRect();
        // the bottom corners stay put while the list scrolls under them,
        // so any sideways overlap counts there
        var bottom = /jlpt-c-b/.test(w.className);
        if (a.left < b.right && b.left < a.right
            && (bottom || (a.top < b.bottom && b.top < a.bottom)))
          w.classList.add('jlpt-mini-docked');
      }}
      fit();
      window.addEventListener('resize', fit);

      // Drag to another corner: a press that moves more than a few pixels
      // drags (and doesn't open the window); the drop picks the quarter of
      // the window the widget's centre is in.
      var w = document.getElementById('jlpt-mini-widget');
      if (!w) return;
      var drag = null;
      w.addEventListener('pointerdown', function(e){{
        if (e.button !== 0 || w.classList.contains('jlpt-mini-docked')) return;
        var r = w.getBoundingClientRect();
        drag = {{x: e.clientX, y: e.clientY, dx: e.clientX - r.left,
                 dy: e.clientY - r.top, on: false}};
        window.jlptMiniDragged = false;
      }});
      document.addEventListener('pointermove', function(e){{
        if (!drag) return;
        if (!drag.on) {{
          if (Math.abs(e.clientX - drag.x) + Math.abs(e.clientY - drag.y) < 6) return;
          drag.on = true;
          w.classList.add('jlpt-mini-dragging');
        }}
        var m = 12;   // keep it inside the window
        var x = Math.max(-m, Math.min(window.innerWidth - w.offsetWidth - m, e.clientX - drag.dx - m));
        var y = Math.max(-8, Math.min(window.innerHeight - w.offsetHeight - 8, e.clientY - drag.dy - 8));
        w.style.left = x + 'px'; w.style.top = y + 'px';
      }});
      function drop(e){{
        if (!drag) return;
        var was = drag.on; drag = null;
        if (!was) return;
        window.jlptMiniDragged = true;   // the click that follows is the drop
        setTimeout(function(){{ window.jlptMiniDragged = false; }}, 0);
        var r = w.getBoundingClientRect();
        var c = (r.top + r.height / 2 < window.innerHeight / 2 ? 't' : 'b')
              + (r.left + r.width / 2 < window.innerWidth / 2 ? 'l' : 'r');
        w.classList.remove('jlpt-mini-dragging', 'jlpt-c-tl', 'jlpt-c-tr', 'jlpt-c-bl', 'jlpt-c-br');
        w.style.left = ''; w.style.top = '';
        w.classList.add('jlpt-c-' + c);
        // glide from where it was dropped into the corner
        var n = w.getBoundingClientRect();
        w.style.transition = 'none';
        w.style.transform = 'translate(' + (r.left - n.left) + 'px,' + (r.top - n.top) + 'px)';
        w.getBoundingClientRect();
        w.style.transition = 'transform 0.18s ease-out';
        w.style.transform = '';
        setTimeout(function(){{ w.style.transition = ''; fit(); }}, 200);
        pycmd('{CORNER_MSG}' + c);
      }}
      document.addEventListener('pointerup', drop);
      document.addEventListener('pointercancel', drop);
    }})();</script>
    """


# Neon intro (owner 2026-10-19): whenever you come to the home screen
# (from startup, a review, a deck overview …) the widget's bars open unlit
# and flicker on like the main window's (theme.flicker_pattern, as CSS step
# keyframes, a fresh random pattern per bar per draw). Not on refreshes
# while you stay there (sync, recount), and never in Amaterasu mode.
# "armed" is set on entering the deck browser and used up by the first draw
# that shows the widget.
_NEON = {"armed": True, "until": 0.0}
# Anki redraws the home screen 2–4 times within a moment of arriving (seen in
# a debug log, 2026-10-19), each draw replacing the page before it is shown:
# every draw within NEON_WINDOW s of the first neon one gets the flicker too,
# so the page that finally shows still plays it.
NEON_WINDOW = 1.2
# CSS only (no script): the animation starts when the page is built, before
# Anki paints it, so it waits NEON_DELAY s (unlit) first. A draw with old
# numbers while a recount runs waits NEON_HOLD_DELAY s instead — the fresh
# draw ~1 s later replaces it and flickers; if none comes, it lights anyway.
NEON_DELAY = 0.3
NEON_HOLD_DELAY = 4.0
_NEON_TARGETS = re.compile(r'class="(jlpt-mini-fill|jlpt-mini-small-fill(?: centred)?|jlpt-mini-text'
                           r'|jlpt-mini-goal-text|jlpt-mini-goal-fill)"')
# The goal line (owner 2026-10-21) flickers on as one more bar: its text
# comes before its fill, so the text starts the bar and the fill follows.
_NEON_TEXTS = ("jlpt-mini-text", "jlpt-mini-goal-text")
_NEON_FOLLOWERS = ("jlpt-mini-text", "jlpt-mini-goal-fill")


# Not while Anki is in the background (owner 2026-10-22: "not do the flicker
# animation and sound effects until you tab in … if you open the app and
# it's minimized"): a draw made then has its animations paused (unlit, CSS
# class jlpt-neon-wait; the sound waits for the first animationstart, so it
# waits too) until the main window is activated (_ActivationWatch).
NEON_WAIT_CLASS = "jlpt-neon-wait"
# Message the widget sends when it's dropped in another corner ("tl" … "br").
CORNER_MSG = "jlpt_mini_corner:"
_WAKE = {"pending": False, "watch": None}


def _in_front() -> bool:
    """Anki's main window is the active, un-minimised window (True when it
    can't tell, so the flicker never stays paused by mistake)."""
    try:
        return bool(mw.isActiveWindow()) and not mw.isMinimized()
    except Exception:
        return True


def _wake_page():
    """Start a paused flicker on the deck list (the window came to the front)."""
    if not _WAKE["pending"]:
        return
    _WAKE["pending"] = False
    try:
        mw.deckBrowser.web.eval(
            f"document.querySelectorAll('.{NEON_WAIT_CLASS}')"
            f".forEach(function(e){{e.classList.remove('{NEON_WAIT_CLASS}');}});")
    except Exception:
        pass


def _watch_activation():
    """Once: wake a paused flicker when the main window is activated or
    restored from minimised."""
    if _WAKE["watch"] is not None:
        return
    try:
        from aqt.qt import QObject, QEvent, QTimer

        class _ActivationWatch(QObject):
            def eventFilter(self, obj, event):
                if event.type() in (QEvent.Type.WindowActivate, QEvent.Type.WindowStateChange) \
                        and _WAKE["pending"]:
                    # A beat later: activation arrives before the window is
                    # painted / un-minimised.
                    QTimer.singleShot(60, lambda: _in_front() and _wake_page())
                return False

        _WAKE["watch"] = _ActivationWatch(mw)
        mw.installEventFilter(_WAKE["watch"])
    except Exception:
        _WAKE["watch"] = False                   # no Qt here (tools): never wait
        _WAKE["pending"] = False


def _flicker_on() -> bool:
    """Settings → Animations → neon flicker (effects.py); on if unreadable."""
    try:
        from . import effects
        return effects.animations_on()
    except Exception:
        return True


def _neon(rows_html: str, hold: bool = False) -> tuple[str, str]:
    """(rows with each bar's fill/text animated, the @keyframes CSS)."""
    from .theme import NEON_OFF_FILL, NEON_OFF_TEXT, flicker_pattern
    import random
    run = random.randrange(1 << 30)
    delay = NEON_HOLD_DELAY if hold else NEON_DELAY
    wait = not _in_front()
    if wait:
        _watch_activation()
        wait = _WAKE["watch"] is not False
    _WAKE["pending"] = wait
    tag = f" {NEON_WAIT_CLASS}" if wait else ""
    css, bar = [], [0]
    css.append(f".{NEON_WAIT_CLASS} {{ animation-play-state: paused !important; }}")
    pats = {}                           # bar → its pattern, for the sound

    def opacity(v):
        return f"opacity: {v:.2f};"

    def frames(name, pat, off, prop=opacity):
        end = pat[-1][0]
        steps, prev = [], 0.0
        for t, level in pat:
            steps.append(f"{prev / end * 100:.2f}% {{ {prop(off + (1 - off) * level)} }}")
            prev = t
        steps.append(f"100% {{ {prop(1.0)} }}")
        css.append(f"@keyframes {name} {{ {' '.join(steps)} }}")
        return f"{name} {end:.2f}s step-end {delay:.2f}s 1 both"

    def sub(m):
        cls = m.group(1)
        if cls not in _NEON_FOLLOWERS:
            bar[0] += 1                 # a fill starts a new bar; its text follows
        pat = flicker_pattern(run + bar[0])
        pats[bar[0]] = pat
        kind, off = ("t", NEON_OFF_TEXT) if cls in _NEON_TEXTS else ("f", NEON_OFF_FILL)
        name = f"jlpt-neon-{kind}{bar[0]}"
        css.append(f".{name} {{ animation: {frames(name + 'k', pat, off)}; }}")
        return f'class="{cls} {name}{tag}"'

    rows_html = _NEON_TARGETS.sub(sub, rows_html)

    # The rank badge flickers on like a lit billboard (owner 2026-10-20):
    # its coloured background and glow are the light source, so the whole
    # badge (background, glow, outline, picture) is one sign whose light
    # stutters up to full on its own pattern; the rank / belt bars inside
    # keep their own neon flicker on top. Brightness, not opacity, so
    # nothing behind shows through. Not in Amaterasu mode (no neon there).
    def billboard(v):
        return f"filter: brightness({v:.2f}) saturate({0.4 + 0.6 * v:.2f});"

    def badge(m):
        pat = flicker_pattern(run + 97)
        pats[97] = pat
        css.append(f".jlpt-neon-badge {{ animation: {frames('jlpt-neon-badgek', pat, BILLBOARD_OFF, billboard)}; }}")
        return f'<div class="jlpt-mini-rank jlpt-mini-rank-art jlpt-neon-badge{tag}"'

    rows_html = re.sub(r'<div class="jlpt-mini-rank jlpt-mini-rank-art"', badge, rows_html, count=1)

    # Its sound, a lot quieter than the main window's (owner 2026-10-22,
    # neon_sound.py): rendered now in the background; the page that ends up
    # showing asks for it when its first bar starts (after the delay), so
    # draws replaced before they show stay silent. Not for a held draw
    # (old numbers): the fresh one comes, else it lights silently.
    from . import effects
    if not hold and pats and effects.mini_sound_on():
        from . import neon_sound
        neon_sound.queue(pats.values(), run)
        rows_html += (
            "<script>(function(){var asked=false;"
            "document.addEventListener('animationstart',function(e){"
            "if(asked||e.animationName.indexOf('jlpt-neon-')!==0)return;"
            f"asked=true;pycmd('{NEON_SOUND_MSG}{run}');}});}})();</script>")
    return rows_html, "\n".join(css)


NEON_SOUND_MSG = "jlpt_neon_sound:"


BILLBOARD_OFF = 0.15      # the rank badge's brightness while unlit (a dark sign, outline just visible)


def _dust_html() -> str:
    """Amaterasu mode: golden dust rising through the widget, like the
    Overview's (pure CSS; fixed pseudo-random positions, sizes, speeds)."""
    specks = []
    for i in range(16):
        x = (i * 61.8034) % 100
        size = 2 + (i * 0.7549) % 1 * 3          # 2–5 px
        dur = 9 + (i * 0.5698) % 1 * 9            # 9–18 s to rise
        delay = -((i * 0.3819) % 1) * dur         # start mid-flight
        sway = 6 + (i * 0.2451) % 1 * 10
        specks.append(
            f"<span style='left:{x:.1f}%; width:{size:.1f}px; height:{size:.1f}px;"
            f" animation-duration:{dur:.1f}s, {dur / 3:.1f}s; animation-delay:{delay:.1f}s, 0s;"
            f" --sway:{sway:.0f}px;'></span>")
    return f"<div class='jlpt-dust'>{''.join(specks)}</div>"


# ── results computation (cached) ──────────────────────────────────────────────

_cache = {"results": None, "key": None}
_bg = {"running": False}


def _cfg_key(cfg: dict):
    """Cheap fingerprint of the settings that affect analysis, so the cache
    is invalidated immediately if the user changes settings."""
    import json
    return json.dumps({
        "deck_name":      cfg.get("deck_name", ""),
        "field_mappings": cfg.get("field_mappings", []),
        "ignore_suspended_cards": cfg.get("ignore_suspended_cards", False),
        "lists":          cfg.get("lists", {}),
    }, sort_keys=True)


def _change_key(cfg: dict):
    """What the widget's numbers (and the history snapshot it records)
    depend on: the settings; the cards' states (added / deleted, new →
    learning → review → relearning, suspended, mature, moved to another
    deck); the notes (added / deleted / edited: count + sum of modification
    times); the found / suspended marks. A review that changes none of that
    (most of them) doesn't recount. Two table scans: a few ms on a 60k
    collection. Was a 5-minute timer, which re-ran the whole multi-second
    scan on the deck list even when nothing had changed (speed report
    2026-10-17)."""
    import os
    from .overrides import Overrides
    try:
        cards = tuple(mw.col.db.first(
            "select count(), sum(type), sum(queue = -1), sum(ivl >= 21), sum(did), sum(odid) "
            "from cards") or ())
        notes = tuple(mw.col.db.first("select count(), sum(mod) from notes") or ())
    except Exception:
        return None                       # no collection: never "unchanged"
    try:
        marks = os.stat(Overrides.path).st_mtime_ns
    except Exception:
        marks = 0
    return (_cfg_key(cfg), cards, notes, marks)


def _compute_results(force: bool = False):
    """Re-run the same analysis used by the main dialog, using saved config
    and overrides. Returns None if not configured yet. Runs wherever it's
    called (the widget calls it off the main thread, see _refresh_async).

    Cached until something it depends on changes (_change_key), since this
    rescans the whole deck and can be slow on large collections — the main
    screen renders this on every navigation back to the deck list."""
    from . import (
        _cfg, collect_words, analyse, _build_unique_readings,
    )

    cfg = _cfg()
    key = _change_key(cfg)
    if not force and key is not None and _cache["key"] == key:
        return _cache["results"]
    # Not configured / failed is remembered too (until something changes),
    # so the deck list doesn't start a recount on every redraw.
    _cache["results"], _cache["key"] = None, key

    deck_name      = cfg.get("deck_name", "")
    field_mappings = cfg.get("field_mappings", [])
    lists_cfg      = cfg.get("lists", {})

    if not deck_name or not field_mappings:
        return None

    lists = jlpt_data.build_lists(lists_cfg)
    if not any(lists.values()):
        return None

    overrides       = Overrides()
    unique_readings = _build_unique_readings(lists)

    try:
        display_index, reading_index, nid_to_display, nid_to_reading =             collect_words(deck_name, field_mappings,
                          bool(cfg.get("ignore_suspended_cards", False)))
    except Exception:
        return None

    results = analyse(
        display_index, reading_index,
        nid_to_display, nid_to_reading,
        lists, unique_readings,
        overrides=overrides,
    )
    # Words marked found count toward the rank.
    card_state.set_found_extra(deck_name, card_state.found_parts(results))
    # Loanwords the rank doesn't count yet: off the bars too.
    card_state.hold_back_loans(results, deck_name, bool(cfg.get("ignore_suspended_cards", False)), lists)

    # The key from before the scan: a change during it shows up next time.
    _cache["results"] = results
    _cache["key"]     = key

    # Every fresh analysis updates today's progress-history snapshot.
    from . import history
    history.record_auto(results, cfg, lists)
    try:                                   # your Nakama card's word bars
        from . import nakama
        nakama.store_partial(results, deck_name, bool(cfg.get("ignore_suspended_cards", False)))
    except Exception:
        pass
    return results


def cached_results():
    """The widget's results if they're still current (None if not
    configured), else None and a background recount starts; the deck list
    redraws when it's done."""
    from . import _cfg
    cfg = _cfg()
    key = _change_key(cfg)
    if key is not None and _cache["key"] == key:
        _prepare_dialog()                        # if the window's count is behind
        return _cache["results"]
    _refresh_async()
    return None


def _refresh_async():
    """Recount off the main thread (Anki's QueryOp, silently: no progress
    window, an error is only printed), then redraw the deck list."""
    if _bg["running"]:
        return           # its redraw recounts again if things changed meanwhile
    _bg["running"] = True

    def work():
        try:
            return _compute_results(force=True)
        finally:
            _bg["running"] = False

    def done(_results):
        if mw.state == "deckBrowser":
            mw.deckBrowser.refresh()
        _prepare_dialog()

    try:
        card_state.run_in_background(mw, work, done, quiet=True)
    except Exception:
        _bg["running"] = False
        raise


_last_shown: dict = {}   # cfg key → the results last drawn


# How long after a deck-list draw the main window's count may start: its
# seconds of Python work starved the widget's flicker and its sound (rendered
# in a thread with 0.15 s to spare), so they didn't play at Anki's start
# (owner 2026-10-25). Every draw pushes it back.
PREPARE_AFTER_MS = 4000
_prep_timer = {"t": None}


def _prepare_dialog():
    """The main window's own count, made ahead in the background so a
    click on the widget opens it at once (owner 2026-10-24) — once the
    deck list has been quiet for PREPARE_AFTER_MS."""
    try:
        from aqt.qt import QTimer
        t = _prep_timer["t"]
        if t is None:
            t = _prep_timer["t"] = QTimer(mw)
            t.setSingleShot(True)
            t.timeout.connect(_prepare_now)
        t.start(PREPARE_AFTER_MS)
    except Exception:
        import traceback
        traceback.print_exc()


def _prepare_now():
    try:
        from . import prepare_dialog
        prepare_dialog()
    except Exception:
        import traceback
        traceback.print_exc()


def invalidate_cache():
    _cache["results"] = None
    _cache["key"]     = None


# ── hook ─────────────────────────────────────────────────────────────────────

# Never let a problem here break the main deck browser screen (the widget is
# built whole and only then added, so an error leaves no half widget).
@hook_guard()
def _on_deck_browser_will_render_content(deck_browser, content):
    from . import _cfg

    cfg = _cfg()
    if not cfg.get("mini_widget_enabled", True):
        return

    results = cached_results()
    ck = _cfg_key(cfg)
    fresh = results is not None
    if results is None:
        # Not counted yet / something changed: the last numbers (same
        # settings) while the recount runs in the background, nothing
        # before the first one.
        stale = _last_shown.get(ck)
        if stale is None:
            return
        results = stale
    _last_shown.clear()
    _last_shown[ck] = results

    from . import rank_toast
    import time
    now = time.monotonic()
    neon = _NEON["armed"] or now < _NEON["until"]   # just came to the home screen
    # Old numbers while a recount runs (it redraws in ~1 s): show the bars
    # unlit and keep the flicker for the fresh draw (4 s fallback in JS).
    hold = neon and not fresh
    if neon and not hold and _NEON["armed"]:
        _NEON["armed"] = False
        _NEON["until"] = now + NEON_WINDOW
    content.stats += _widget_html(
        results, deck_name=cfg.get("deck_name", ""),
        ignore_suspended=bool(cfg.get("ignore_suspended_cards", False)),
        show_rank=bool(cfg.get("mini_widget_show_rank", True)),
        rankup=rank_toast.peek_unseen(),
        show_art=bool(cfg.get("mini_widget_show_rank_art", True)),
        neon=neon, neon_hold=hold,
        corner=cfg.get("mini_widget_corner", "tr") if cfg.get("mini_widget_corner") in _CORNERS else "tr")


_OUR_MESSAGES = ("jlpt_open_progress", "jlpt_dismiss_rankup")
_CORNERS = ("tl", "tr", "bl", "br")


# Anki passes every webview message through this filter: other add-ons' and
# Anki's own messages must get `handled` back untouched, ours count as
# handled even if opening the window fails.
@hook_guard(fallback=lambda handled, message, context:
            (True, None) if message in _OUR_MESSAGES
            or str(message).startswith((NEON_SOUND_MSG, CORNER_MSG))
            else handled)
def _on_webview_did_receive_js_message(handled, message, context):
    if isinstance(message, str) and message.startswith(NEON_SOUND_MSG):
        from . import neon_sound
        neon_sound.play_queued(int(message[len(NEON_SOUND_MSG):]))
        return True, None
    if isinstance(message, str) and message.startswith(CORNER_MSG):
        corner = message[len(CORNER_MSG):]
        if corner in _CORNERS:
            from . import _cfg, _save
            cfg = _cfg()
            if cfg.get("mini_widget_corner") != corner:
                cfg["mini_widget_corner"] = corner
                _save(cfg)
        return True, None
    if message == "jlpt_open_progress":
        from . import open_progress_dialog_direct, rank_toast
        rank_toast.dismiss_unseen()
        open_progress_dialog_direct()
        return True, None
    if message == "jlpt_dismiss_rankup":
        from . import rank_toast
        rank_toast.dismiss_unseen()
        if mw.state == "deckBrowser":
            mw.deckBrowser.refresh()
        return True, None
    return handled


@hook_guard()
def _on_state_will_change(new_state, old_state):
    # Coming to the home screen from anywhere else: flicker on again.
    if new_state == "deckBrowser" and old_state != "deckBrowser":
        _NEON["armed"] = True
        _NEON["until"] = 0.0


def setup():
    gui_hooks.state_will_change.append(_on_state_will_change)
    gui_hooks.deck_browser_will_render_content.append(
        _on_deck_browser_will_render_content
    )
    gui_hooks.webview_did_receive_js_message.append(
        _on_webview_did_receive_js_message
    )
