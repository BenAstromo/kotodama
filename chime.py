"""
chime.py
The ascension chime (owner 2026-10-09): a soft bell when the Amaterasu flash
plays. It must never be loud, even with the volume turned up — too quiet is
fine — so it's quiet twice over:
  - the sound itself is synthesised at a low level (peak ≈ −26 dBFS);
  - it's played at half volume where Qt Multimedia is available (≈ −32 dBFS);
    without it (Windows' plain player, no volume control) the baked-in level
    still keeps it soft.
Settings: "Play a quiet chime on ascension" (on by default).

The WAV is generated once into user_files/ (no bundled audio file).
"""

import math
import os
import struct
import wave

_HERE = os.path.dirname(os.path.abspath(__file__))
_PATH = os.path.join(_HERE, "user_files", "ascension_chime.wav")
_PEAK = 0.05          # ≈ −26 dBFS
_VOLUME = 0.5         # Qt Multimedia playback volume on top
_keep = []            # the playing sound object must stay alive


def _make_wav():
    """A small bell: inharmonic partials with their own decays, a 6 ms
    attack, 3 s long, 44.1 kHz mono."""
    rate, secs, f0 = 44_100, 3.0, 660.0
    partials = ((1.0, 1.0, 1.6), (2.76, 0.45, 2.6), (5.40, 0.25, 4.0), (8.93, 0.12, 6.0))
    n = int(rate * secs)
    frames = bytearray()
    for i in range(n):
        t = i / rate
        attack = min(1.0, t / 0.006)
        s = sum(a * math.exp(-d * t) * math.sin(2 * math.pi * f0 * m * t)
                for m, a, d in partials)
        v = int(max(-1.0, min(1.0, s / 1.8 * attack)) * _PEAK * 32767)
        frames += struct.pack("<h", v)
    os.makedirs(os.path.dirname(_PATH), exist_ok=True)
    with wave.open(_PATH, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(bytes(frames))


def play():
    """Play the chime (not its own setting since 2026-10-10; Settings →
    Sound effects sets its volume, effects.py). Never raises."""
    try:
        from . import effects
        level = effects.volume()
        if level <= 0:
            return
        if not os.path.exists(_PATH):
            _make_wav()
        try:
            from .neon_sound import sound_effect_classes
            QSoundEffect, QUrl = sound_effect_classes()
            fx = QSoundEffect()
            fx.setSource(QUrl.fromLocalFile(_PATH))
            fx.setVolume(_VOLUME * level)
            fx.play()
            _keep[:] = [fx]
            return
        except Exception:
            pass
        import sys
        if sys.platform == "win32" and level >= 1:     # no volume control there
            import winsound
            winsound.PlaySound(_PATH, winsound.SND_FILENAME | winsound.SND_ASYNC)
    except Exception:
        pass
