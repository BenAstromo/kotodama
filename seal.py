"""
seal.py
Amaterasu mode, optional (Settings, off by default): a small gold seal in
the corner of the review screen, like a traditional Japanese seal (hanko /
落款, owner's reference: a red 白文 seal with four characters, two columns
read right to left). Ours is gold with 天照大神 carved out in light colour:
right column 天照, left column 大神. Slightly worn edges (an SVG noise
displacement) so it reads as stamped, not drawn.

Injected into the reviewer page once when it's set up
(gui_hooks.webview_will_set_content), only in Amaterasu mode (20,000).
"""

from aqt import gui_hooks

SEAL_HTML = """
<div id="jlpt-amaterasu-seal" title="天照大神" style="position: fixed; right: 14px; bottom: 14px;
     width: 62px; height: 62px; z-index: 9999; pointer-events: none; opacity: 0.92;">
  <svg viewBox="0 0 100 100" width="62" height="62" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <filter id="jlpt-worn" x="-5%" y="-5%" width="110%" height="110%">
        <feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="2" seed="7" result="n"/>
        <feDisplacementMap in="SourceGraphic" in2="n" scale="3.2"/>
      </filter>
      <linearGradient id="jlpt-gold" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0" stop-color="#ffe680"/>
        <stop offset="0.5" stop-color="#e0a800"/>
        <stop offset="1" stop-color="#a87400"/>
      </linearGradient>
    </defs>
    <g filter="url(#jlpt-worn)">
      <rect x="5" y="5" width="90" height="90" rx="5" fill="url(#jlpt-gold)"/>
      <g fill="#fff6dc" font-family="'Yu Mincho', 'MS Mincho', 'Hiragino Mincho ProN', serif"
         font-weight="700" font-size="39" text-anchor="middle">
        <text x="71" y="46">天</text><text x="71" y="88">照</text>
        <text x="29" y="46">大</text><text x="29" y="88">神</text>
      </g>
    </g>
  </svg>
</div>
"""


def _in_amaterasu_mode() -> bool:
    from . import _cfg, card_state, rank_data
    if card_state.DEBUG_FULL["on"]:          # DEBUG "Force Amaterasu"
        return True
    cfg = _cfg()
    deck = cfg.get("deck_name", "")
    if not deck:
        return False
    return card_state.rank_count(deck, bool(cfg.get("ignore_suspended_cards", False))) \
        >= rank_data.MAX_CARDS


def _on_webview_will_set_content(web_content, context):
    try:
        from aqt.reviewer import Reviewer
        if not isinstance(context, Reviewer):
            return
        from . import _cfg
        if not _cfg().get("review_seal", False) or not _in_amaterasu_mode():
            return
        web_content.body += SEAL_HTML
    except Exception:
        pass            # never break the reviewer


def setup():
    gui_hooks.webview_will_set_content.append(_on_webview_will_set_content)
