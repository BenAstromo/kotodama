"""
neon_sound.py
The neon intro's sound (owner 2026-10-22: picked drafts 1, 3 and 7 of
seven): synthesised from the flicker patterns of the bars on screen, so
every buzz and spark lands on a bar lighting up.
  - the window's sound is the soft hum (1) or the electric crackle (3),
    one or the other at random per opening;
  - a bar on the "struggling tube" pattern (theme.flicker_pattern's fast,
    dim buzz) adds its own transformer buzz with a tick per spark (7);
  - the sound fades out shortly after the last bar is lit.
Quiet like the chime (baked-in level, half volume), no setting; the
deck list's mini widget plays the same kind of sound a lot quieter
(MINI_VOLUME, queue / play_queued below). The WAV is
written into user_files/ each time (one file per window: Qt Multimedia
caches a sound by its file name). Never raises.
"""

from __future__ import annotations

import math
import os
import random
import wave
from array import array

_HERE = os.path.dirname(os.path.abspath(__file__))
_DIR = os.path.join(_HERE, "user_files")
SR = 44_100
MASTER = 0.6            # baked-in level of the mix's peak…
_VOLUME = 0.25          # …then a quarter on top (owner 2026-10-22: "very slightly
                        # quieter" than the chime's 0.5 → 0.42, then step by step
                        # 0.37, 0.33, 0.30, then "set … to 0.25")
MAX_BARS = 6            # the main layer follows a handful of bars, like the drafts
_STRUGGLE_LEVELS = (0.3, 0.45, 0.6)
_keep = []              # the playing sound object must stay alive


def sound_effect_classes():
    """(QSoundEffect, QUrl) from Anki's Qt: PyQt6, or PyQt5 on Anki's Qt5
    builds (2.1.50–2.1.66; same QSoundEffect API). ImportError if neither."""
    try:
        from PyQt6.QtMultimedia import QSoundEffect
        from PyQt6.QtCore import QUrl
    except ImportError:
        from PyQt5.QtMultimedia import QSoundEffect
        from PyQt5.QtCore import QUrl
    return QSoundEffect, QUrl
_noise_cache = {}


def is_struggling(pat) -> bool:
    """theme.flicker_pattern's struggling-tube branch: dim 0.3 / 0.45 / 0.6 buzzes."""
    return sum(1 for _end, level in pat if level in _STRUGGLE_LEVELS) >= 3


# ── building blocks ───────────────────────────────────────────────────────────

def _levels(pat, n):
    """Per-sample level of one bar: held per segment, fully on after the last."""
    out, start = [], 0
    for end, level in pat:
        stop = min(n, int(end * SR))
        if stop > start:
            out.extend([level] * (stop - start))
            start = stop
    out.extend([1.0] * (n - start))
    return out


def _onsets(pat):
    """(time, jump) where the tube jumps up: a spark."""
    out, prev, start = [], 0.0, 0.0
    for end, level in list(pat) + [(None, 1.0)]:
        if level > prev + 0.05:
            out.append((start, level - prev))
        prev = level
        if end is not None:
            start = end
    return out


def _smooth(env, ms):
    a = 1 - math.exp(-1 / (SR * ms / 1000))
    y, out = 0.0, []
    app = out.append
    for x in env:
        y += a * (x - y)
        app(y)
    return out


def _hum(n, f0, drive, harm):
    """A buzzing hum from one exact cycle-table (f0 divides SR·k)."""
    periods = 1
    while (SR * periods) % f0:
        periods += 1
    size = SR * periods // f0
    norm = math.tanh(drive)
    table = []
    for i in range(size):
        ph = 2 * math.pi * f0 * i / SR
        s = sum(a * math.sin(ph * (k + 1)) for k, a in enumerate(harm))
        table.append(math.tanh(drive * s) / norm)
    reps = n // size + 1
    return (table * reps)[:n]


def _noise(n, seed, hp, lp):
    key = (seed, hp, lp)
    got = _noise_cache.get(key)
    if got is not None and len(got) >= n:
        return got[:n]
    rnd = random.Random(seed)
    y = x1 = l = 0.0
    out = []
    for _ in range(n):
        x = rnd.uniform(-1, 1)
        y = hp * (y + x - x1) if hp else x       # one-pole high-pass
        x1 = x
        l += lp * (y - l)                        # one-pole low-pass
        out.append(l)
    _noise_cache[key] = out
    return out


def _click(buf, t, amp, freq, decay_ms, seed):
    rnd = random.Random(seed)
    i0 = int(t * SR)
    tau = SR * decay_ms / 1000
    for i in range(int(tau * 6)):
        if i0 + i >= len(buf):
            break
        buf[i0 + i] += amp * math.exp(-i / tau) * (
            0.6 * math.sin(2 * math.pi * freq * i / SR) + 0.4 * rnd.uniform(-1, 1))


def _tail(n, on_at, hold, fade):
    """1 until on_at + hold, then fades to 0: no endless buzz in a UI."""
    a, b = int((on_at + hold) * SR), int((on_at + hold + fade) * SR)
    span = max(1, b - a)
    head = [1.0] * min(n, a)
    mid = [(1 - i / span) ** 2 for i in range(max(0, min(n, b) - a))]
    return head + mid + [0.0] * (n - len(head) - len(mid))


def _normalise(buf, peak):
    m = max((abs(x) for x in buf), default=0) or 1
    k = peak / m
    return [x * k for x in buf]


def _mean_env(pats, n):
    env = [0.0] * n
    for p in pats:
        env = [a + b for a, b in zip(env, _levels(p, n))]
    k = 1 / len(pats)
    return [x * k for x in env]


# ── the three sounds ──────────────────────────────────────────────────────────

def _soft_hum(pats, end, n):
    """Draft 1: a quiet, warm hum with tiny ticks."""
    env = _smooth(_mean_env(pats, n), 6)
    h = _hum(n, 100, 1.2, (1, .25, .08))
    nz = _noise(n, 7, 0.0, 0.08)
    tl = _tail(n, end, 0.15, 0.5)
    buf = [(a * 0.35 + b * 0.25) * e * t for a, b, e, t in zip(h, nz, env, tl)]
    for j, p in enumerate(pats):
        for t, jump in _onsets(p):
            _click(buf, t, 0.12 * jump, 1200, 3, j + int(t * 997))
    return _normalise(buf, 0.45)


def _crackle(pats, end, n):
    """Draft 3: an electric crackle on every spark over a thin buzz."""
    env = _smooth(_mean_env(pats, n), 1)
    h = _hum(n, 120, 4, (1, .6, .4, .3, .2))
    nz = _noise(n, 11, 0.85, 0.6)
    tl = _tail(n, end, 0.2, 0.5)
    ch = [0.0] * n
    tau = SR * 0.02
    for j, p in enumerate(pats):
        for t, jump in _onsets(p):
            i0 = int(t * SR)
            rnd = random.Random(j * 7 + i0)
            for k in range(int(SR * 0.06)):
                if i0 + k < n and rnd.random() < 0.35:
                    ch[i0 + k] += jump * math.exp(-k / tau)
    buf = [(a * 0.3 * e + b * 1.6 * c) * t for a, e, b, c, t in zip(h, env, nz, ch, tl)]
    return _normalise(buf, 0.7)


def _struggle(pat, end, n, j):
    """Draft 7: one struggling tube's transformer buzz, a tick per spark."""
    env = _smooth(_levels(pat, n), 2)
    h = _hum(n, 100, 3, (1, .5, .3, .2))
    tl = _tail(n, end, 0.35, 0.6)
    buf = [a * e * t * 0.5 for a, e, t in zip(h, env, tl)]
    for t, jump in _onsets(pat):
        _click(buf, t, 0.35 * jump, 1800 + 300 * j, 4, j * 31 + int(t * 1000))
    return _normalise(buf, 0.7)


def render_spark(seed) -> list:
    """A spark off a tube (rain.py, owner 2026-10-22: "can't hear the
    sparks"): a sharp crack, a fast crackle that thins out, a short sizzle."""
    rnd = random.Random(seed)
    n = int(SR * 0.55)
    buf = [0.0] * n
    _click(buf, 0.0, 1.0, rnd.uniform(2200, 3200), 2.2, seed)            # the crack
    nz = _noise(n, 300 + seed % 7, 0.9, 0.75)
    hiss = [nz[i] * math.exp(-i / (SR * 0.09)) * 0.55 for i in range(n)]
    buf = [a + b for a, b in zip(buf, hiss)]
    t = 0.004
    while t < 0.32:                                                       # crackle, thinning out
        _click(buf, t, rnd.uniform(0.25, 0.7) * (1 - t / 0.34), rnd.uniform(1800, 4200),
               rnd.uniform(0.8, 1.8), int(t * 10007) + seed)
        t += rnd.uniform(0.006, 0.02) + t * 0.12
    return _normalise(buf, 0.75)


SPARK_VOLUME = 0.05             # × the Settings level (the intro is 0.25); 0.2 → 0.12 → 0.05 (owner 2026-10-22: "still really loud")
_SPARKS: list = []              # rendered spark files, this session


def prepare_sparks(k: int = 3) -> list:
    """Render k spark variants into user_files (no Qt: worker-thread safe);
    fixed names, rewritten each session."""
    try:
        os.makedirs(_DIR, exist_ok=True)
        out = []
        for i in range(k):
            path = os.path.join(_DIR, f"neon_spark_{i}.wav")
            _write(path, render_spark(random.randrange(1 << 30)))
            out.append(path)
        _SPARKS[:] = out
        return out
    except Exception:
        return []


def play_spark():
    """One of the rendered sparks (nothing if they aren't ready yet)."""
    if _SPARKS:
        play_file(random.choice(_SPARKS), SPARK_VOLUME, window=True)


def stop_window_sounds():
    """The Kotodama window lost the focus: silence its sounds now (the
    flicker buzz, a spark, a stutter); the mini widget's carry on."""
    for fx in list(_keep):
        if getattr(fx, "_kotodama_window", False):
            try:
                fx.stop()
            except Exception:
                pass


def render(patterns, seed) -> list:
    """Float samples (−1…1) for these bars' flicker patterns."""
    pats = [list(p) for p in patterns if p]
    if not pats:
        return []
    rnd = random.Random(seed)
    end = max(p[-1][0] for p in pats)
    n = int(SR * (end + 1.1))
    struggling = [p for p in pats if is_struggling(p)]
    steady = [p for p in pats if not is_struggling(p)] or pats
    if len(steady) > MAX_BARS:
        steady = rnd.sample(steady, MAX_BARS)
    main = (_soft_hum if rnd.random() < 0.5 else _crackle)(steady, end, n)
    for j, p in enumerate(struggling[:2]):
        main = [a + b * 0.6 for a, b in zip(main, _struggle(p, end, n, j))]
    return _normalise(main, MASTER)


def _write(path, samples):
    pcm = array("h", (int(max(-1.0, min(1.0, x)) * 32767) for x in samples))
    import sys
    if sys.byteorder == "big":
        pcm.byteswap()
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def prepare(patterns, run: int):
    """Synthesise the intro's sound for these flicker patterns into a WAV;
    its path, or None. No Qt: safe on a worker thread (it takes ~0.2 s,
    so the intro holds its bars dark until it's ready). run: the intro's
    number — a fresh file and a fresh pick each time."""
    try:
        samples = render(patterns, run)
        if not samples:
            return None
        os.makedirs(_DIR, exist_ok=True)
        name = f"neon_flicker_{os.getpid()}_{run}.wav"
        path = os.path.join(_DIR, name)
        _write(path, samples)
        # Earlier files, once they're surely done with (the mini widget
        # prepares a few at once and plays the one whose page shows).
        import time
        for old in os.listdir(_DIR):
            p = os.path.join(_DIR, old)
            if old.startswith("neon_flicker_") and old != name:
                try:
                    if time.time() - os.path.getmtime(p) > 30:
                        os.remove(p)
                except OSError:
                    pass
        return path
    except Exception:
        return None


# ── the mini widget (owner 2026-10-22: "a lot quieter") ───────────────────────
# Its flicker is CSS on the deck list, drawn 2–4 times on arrival (each draw
# replacing the last before it shows). Every draw queues its sound here; one
# worker thread renders the newest. The page that actually shows tells us
# when its flicker starts (pycmd "jlpt_neon_sound:<run>", mini_widget), and
# play_queued plays that draw's sound, or nothing if it isn't ready in time.
MINI_VOLUME = 0.15          # vs _VOLUME 0.25 for the main window (0.1 → 0.112 → 0.15: owner 2026-10-22)
MINI_LATE = 0.15            # s a page may wait for its sound before going silent
_mini = {"latest": None, "worker": None, "done": {}}


def queue(patterns, run: int):
    """Render this draw's sound in the background (newest draw first)."""
    try:
        from . import effects
        if effects.muted():
            return
        import threading
        _mini["latest"] = (list(patterns), run)
        w = _mini["worker"]
        if w is None or not w.is_alive():
            _mini["worker"] = threading.Thread(target=_work, daemon=True)
            _mini["worker"].start()
    except Exception:
        pass


def _work():
    while True:
        job, _mini["latest"] = _mini["latest"], None
        if job is None:
            return
        pats, run = job
        path = prepare(pats, run)
        done = _mini["done"]
        done[run] = path
        while len(done) > 4:
            done.pop(next(iter(done)))


def play_queued(run: int, waited: float = 0.0):
    """The page of draw `run` started its flicker (main thread)."""
    try:
        done = _mini["done"]
        if run in done:
            play_file(done.pop(run), MINI_VOLUME)
            return
        if waited < MINI_LATE:                # still rendering: a moment more
            from aqt.qt import QTimer
            QTimer.singleShot(20, lambda: play_queued(run, waited + 0.02))
    except Exception:
        pass


def preview(level: float):
    """A sample at this Settings volume (0–1), for the slider."""
    try:
        from .theme import flicker_pattern
        run = random.randrange(1 << 30)
        play_file(prepare([flicker_pattern(run + k) for k in range(6)], run), level=level)
    except Exception:
        pass


def play_file(path, volume: float = _VOLUME, level: float = None, window: bool = False):
    """Play a WAV from prepare() (main thread) at `volume` × the Settings
    level (effects.py; `level` overrides it). Never raises."""
    try:
        if level is None:
            from . import effects
            level = effects.volume()
        volume *= level
        if not path or volume <= 0:
            return
        try:
            QSoundEffect, QUrl = sound_effect_classes()
            fx = QSoundEffect()
            fx.setSource(QUrl.fromLocalFile(path))
            fx.setVolume(volume)
            fx._kotodama_window = window          # stop_window_sounds()
            fx.play()
            # Kept alive while it plays; a few at once, so a batch lit by
            # scrolling doesn't cut the one before it off (2026-10-22).
            _keep.append(fx)
            del _keep[:-4]
            return
        except Exception:
            pass
        import sys
        # Windows' plain player has no volume: only at the main window's
        # full level (a quieter sound, the mini widget's or a lowered
        # Settings volume, would play just as loud).
        if sys.platform == "win32" and volume >= _VOLUME:
            import winsound
            winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
    except Exception:
        pass
