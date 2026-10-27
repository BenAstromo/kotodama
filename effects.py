"""
effects.py
Settings → "Sound effects" volume (owner 2026-10-22): one level for every
sound the add-on makes (the neon flicker in the window and the mini widget,
the ascension chime, the star's sound). 0–100 %, 100 % = each sound's own
quiet level as designed; 0 % = none at all. Each player multiplies its own
volume by volume().
"""

KEY = "effects_volume"
DEFAULT = 50                   # owner 2026-10-26 (was 100)


def volume() -> float:
    """0.0 … 1.0 from the settings (1.0 if they can't be read)."""
    try:
        from . import _cfg
        return max(0, min(100, int(_cfg().get(KEY, DEFAULT)))) / 100
    except Exception:
        return DEFAULT / 100


def muted() -> bool:
    return volume() <= 0


# Settings → Sound effects → "Mini widget sounds" (owner 2026-10-26: some
# people want the main window's sounds but a silent deck list). On by default.
MINI_SOUND_KEY = "mini_widget_sound"


def mini_sound_on() -> bool:
    """The mini widget may play its flicker sound (volume above 0 and its switch on)."""
    if muted():
        return False
    try:
        from . import _cfg
        return bool(_cfg().get(MINI_SOUND_KEY, True))
    except Exception:
        return True


# Settings → "Animations" (owner 2026-10-22: "a setting for disabling
# animations and rain"): the neon flicker-on (main window, its grids, the
# mini widget; off: everything lit at once, so no flicker sound or rare
# stutter) and the rain on the glass (with its sparks). Both on by default.
ANIM_KEY = "neon_flicker"
RAIN_KEY = "rain"


_FLAGS = {}                    # key → (read at, value): the rain asks every frame


def _flag(key) -> bool:
    import time
    now = time.monotonic()
    hit = _FLAGS.get(key)
    if hit is not None and now - hit[0] < 1.0:
        return hit[1]
    try:
        from . import _cfg
        value = bool(_cfg().get(key, True))
    except Exception:
        value = True
    _FLAGS[key] = (now, value)
    return value


def animations_on() -> bool:
    return _flag(ANIM_KEY)


def rain_on() -> bool:
    return _flag(RAIN_KEY)


# Settings → "Night look" (owner 2026-10-25: moon mode's effects, "make
# you can individually turn all of these off and on in the settings"):
# each one its own switch, all on by default; read at paint time (cached
# 1 s), so a change shows within a second. None of them in Amaterasu mode.
FX = {
    # the tubes' light on the wall behind them (+ its flicker) and each bar's
    # puddle reflection below it (owner 2026-10-26: one switch for both)
    "fx_spill": "Light spill",
    "fx_bokeh": "Bokeh",                  # out-of-focus city lights far behind
    "fx_vignette": "Vignette",            # darker corners
    "fx_condensation": "Condensation",    # mist on the glass; running drops clear it
}
# Stars and moon have no switch: always there behind the night (owner 2026-10-26).


def fx(key) -> bool:
    return _flag(key)
