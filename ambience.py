"""
ambience.py
Amaterasu mode's star sound (owner 2026-10-16), built from the Sun's real
oscillation spectrum sped up ~36,000× (p-modes 91–120 Hz around 110 Hz;
generator: tools/star_ambience.js):
  - media/star_ignition.ogg     — one-shot, played with the ascension intro:
                                  a quickening flutter, then a bell strike at
                                  STRIKE s (when her light blooms);
  - media/star_ringing_sun.ogg  — 60 s loop, starts at the strike;
  - media/star_heartbeat.ogg    — one colossal beat per HEARTBEAT_PERIOD s
                                  (the loop's length, beat at 0 s), first
                                  one a period after the strike.
Settings → Amaterasu → "Play the star's sound" mutes it all (on by default).
Plays while the Kotodama window is in Amaterasu mode (the real 20,000 or
the debug preview); opening the window there fades the Ringing Sun in,
heartbeat a period later. Quiet like the chime: soft files, half volume.
Settings → Amaterasu → "Play the star's sound" mutes all of it (on by
default; owner 2026-10-16).
Qt Multimedia loops the OGGs gaplessly (checked: the decoded stream is
continuous across loops). Never raises.
"""

from __future__ import annotations

import os

from aqt.qt import QObject, QTimer, QUrl, QVariantAnimation

_MEDIA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "media")
STRIKE = 0.55               # s into the ignition: its bell strike
HEARTBEAT_PERIOD = 4.0      # s between heartbeats (15 bpm), = strike → first beat
HEARTBEAT = False           # owner 2026-10-16: heartbeat off for now (file kept)
VOLUME = 0.5
_FILES = {"ignition": "star_ignition.ogg", "sun": "star_ringing_sun.ogg",
          "heart": "star_heartbeat.ogg"}


class _Ambience(QObject):
    def __init__(self):
        super().__init__()
        self._players = {}          # name → (QMediaPlayer, QAudioOutput)
        self._fades = []
        self._gen = 0               # bumped on every start/stop: stale timers do nothing
        self.running = False
        self._away = False          # the Kotodama window lost the focus: silent (set_away)
        self._paused = []           # players paused for that, resumed when it's back

    def _player(self, name: str, loop: bool):
        if name not in self._players:
            from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
            player, out = QMediaPlayer(self), QAudioOutput(self)
            player.setAudioOutput(out)
            player.setSource(QUrl.fromLocalFile(os.path.join(_MEDIA, _FILES[name])))
            player.setLoops(QMediaPlayer.Loops.Infinite if loop else 1)
            self._players[name] = (player, out)
        return self._players[name]

    def _play(self, name: str, loop: bool, fade_ms: int = 0):
        if self._away:                          # starts when the window is back
            if name not in self._paused:
                self._paused.append(name)
            return
        player, out = self._player(name, loop)
        player.stop()
        player.setPosition(0)
        from . import effects                   # Settings → Sound effects
        vol = VOLUME * effects.volume()
        self._fade(out, 0.0 if fade_ms else vol, vol, fade_ms)
        player.play()

    def _fade(self, out, start: float, end: float, ms: int, then=None):
        if ms <= 0:
            out.setVolume(end)
            if then:
                then()
            return
        anim = QVariantAnimation(self)
        anim.setStartValue(float(start))
        anim.setEndValue(float(end))
        anim.setDuration(ms)
        anim.valueChanged.connect(lambda v: out.setVolume(float(v)))

        def finished():
            if anim in self._fades:
                self._fades.remove(anim)
            if then:
                then()
        anim.finished.connect(finished)
        self._fades.append(anim)
        anim.start()

    def _later(self, seconds: float, fn):
        gen = self._gen
        QTimer.singleShot(int(seconds * 1000), lambda: gen == self._gen and fn())

    def _reset(self):
        self._gen += 1
        for anim in self._fades:
            anim.stop()
        self._fades = []
        for player, _out in self._players.values():
            player.stop()

    def ascend(self) -> bool:
        """The ascension: ignition now, the Ringing Sun at its strike, the
        first heartbeat a period after that. False if it can't play (muted
        counts as played: no chime either)."""
        if not enabled():
            return True
        try:
            self._reset()
            self.running = True
            self._play("ignition", loop=False)
            self._later(STRIKE, lambda: self._play("sun", loop=True, fade_ms=800))
            if HEARTBEAT:
                self._later(STRIKE + HEARTBEAT_PERIOD, lambda: self._play("heart", loop=True))
            return True
        except Exception:
            self.running = False
            return False

    def enter(self):
        """Amaterasu mode is on (window opened there): fade the Ringing Sun
        in, heartbeat a period later. Nothing if it's already playing."""
        if self.running or not enabled():
            return
        try:
            self._reset()
            self.running = True
            self._play("sun", loop=True, fade_ms=3000)
            if HEARTBEAT:
                self._later(HEARTBEAT_PERIOD, lambda: self._play("heart", loop=True))
        except Exception:
            self.running = False

    def set_away(self, away: bool):
        """The Kotodama window lost the focus (away) or got it back (owner
        2026-10-22: "make all sound muted if focus of kotodama window is
        lost"): a quick fade and pause, then a fade back in where it was."""
        if away == self._away:
            return
        self._away = away
        try:
            from PyQt6.QtMultimedia import QMediaPlayer
            from . import effects
            if away:
                for name, (player, out) in self._players.items():
                    if player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                        self._paused.append(name)
                        self._fade(out, out.volume(), 0.0, 250, then=player.pause)
            else:
                names, self._paused = self._paused, []
                if not self.running:
                    return
                vol = VOLUME * effects.volume()
                for name in names:
                    player, out = self._player(name, name != "ignition")
                    out.setVolume(0.0)
                    player.play()
                    self._fade(out, 0.0, vol, 600)
        except Exception:
            pass

    def leave(self, fade_ms: int = 1500):
        """Amaterasu mode off or the window closed: fade everything out."""
        self._paused = []
        if not self.running:
            return
        self.running = False
        try:
            self._gen += 1                      # cancel a heartbeat still to come
            for player, out in self._players.values():
                self._fade(out, out.volume(), 0.0, fade_ms, then=player.stop)
        except Exception:
            pass


def enabled() -> bool:
    """Settings → Amaterasu → "Play the star's sound" (on by default)."""
    try:
        from . import _cfg, effects
        return bool(_cfg().get("amaterasu_sound", True)) and not effects.muted()
    except Exception:
        return True


_AMBIENCE = None


def get() -> _Ambience:
    global _AMBIENCE
    if _AMBIENCE is None:
        _AMBIENCE = _Ambience()
    return _AMBIENCE
