"""
rank_video.py
Animated rank pictures (owner 2026-10-15). The owner's Wallpaper Engine
scenes, recorded and cut into a play-once intro and a seamless loop:
media/<rank>_intro.webm and media/<rank>_loop.webm (720×480, 30 fps, VP9;
the loop's end is crossfaded into its start, and the intro ends on the frame
before the loop's first, so intro → loop doesn't jump).

Played with Qt Multimedia (Anki's Qt ships its FFmpeg backend) into a
QVideoSink, so the badge shows the frames in its own picture label and the
divine overlay still draws on top. Without Qt Multimedia, or if a file won't
play, the badge just keeps its still picture.

Only Amaterasu has clips so far; the other ranks are being remade.
"""

from __future__ import annotations

import os

from aqt.qt import QObject, QImage, QUrl, pyqtSignal

_MEDIA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "media")

# Seconds into the intro where the light behind her blooms: it starts to
# show at 0.12 s and is fully up at 0.55 s (measured on the recording).
# The ascension flash peaks with it, and the divine light fades in with it.
INTRO_BLOOM = {"Amaterasu": (0.12, 0.55)}


def clip(rank_en: str, kind: str) -> str | None:
    """Path of a rank's 'intro' or 'loop' clip, or None if it has none."""
    path = os.path.join(_MEDIA, f"{rank_en.lower()}_{kind}.webm")
    return path if os.path.exists(path) else None


class RankVideo(QObject):
    """Plays a rank's loop forever, or its intro once and then the loop.
    Emits every decoded frame as a QImage. Never raises; `ok` is False if
    Qt Multimedia isn't there (the caller keeps its still picture)."""

    frame = pyqtSignal(QImage)

    def __init__(self, rank_en: str, parent=None):
        super().__init__(parent)
        self.rank = rank_en
        self.ok = False
        self._intro = None          # (player, sink) while the intro plays
        self._intro_t = None        # seconds into the intro on screen
        self._intro_shown = False   # its first frame has arrived
        try:
            from PyQt6.QtMultimedia import QMediaPlayer, QVideoSink
            self._QMediaPlayer, self._QVideoSink = QMediaPlayer, QVideoSink
            self._loop = self._player(clip(rank_en, "loop"))
            self._loop[0].setLoops(QMediaPlayer.Loops.Infinite)
            self._loop[1].videoFrameChanged.connect(lambda vf: self._emit(vf, False))
            self.ok = True
        except Exception:
            self._loop = None

    def _player(self, path):
        player = self._QMediaPlayer(self)
        sink = self._QVideoSink(self)
        player.setVideoSink(sink)
        player.setSource(QUrl.fromLocalFile(path))
        return player, sink

    def _emit(self, vf, intro: bool):
        if not intro and self._intro is not None:
            return                          # the loop pre-rolling under the intro
        try:
            if intro:
                self._intro_t = max(0.0, vf.startTime() / 1e6)
                self._intro_shown = True
            img = vf.toImage()
            if not img.isNull():
                self.frame.emit(img)
        except Exception:
            pass

    def has_intro(self) -> bool:
        return self.ok and clip(self.rank, "intro") is not None

    def play_loop(self):
        if self.ok and self._intro is None:
            self._loop[0].play()

    def play_intro(self) -> bool:
        """The intro from the start, then the loop. False if there's none."""
        if not self.has_intro():
            return False
        try:
            self._loop[0].stop()
            if self._intro is not None:
                self._intro[0].stop()
                self._intro[0].deleteLater()
            player, sink = self._player(clip(self.rank, "intro"))
            sink.videoFrameChanged.connect(lambda vf: self._emit(vf, True))
            player.mediaStatusChanged.connect(self._intro_status)
            self._intro, self._intro_t = (player, sink), 0.0
            self._intro_shown = False
            player.play()
            # Pre-roll the loop, paused on its first frame, so it starts
            # without a hitch when the intro ends.
            self._loop[0].pause()
            return True
        except Exception:
            self._intro = None
            return False

    def _intro_status(self, status):
        if status in (self._QMediaPlayer.MediaStatus.EndOfMedia,
                      self._QMediaPlayer.MediaStatus.InvalidMedia):
            self._end_intro()

    def _end_intro(self):
        """Hand over to the loop (its first frame follows the intro's last;
        the last intro frame stays up until the loop's first arrives)."""
        if self._intro is not None:
            player = self._intro[0]
            self._intro, self._intro_t = None, None
            player.stop()
            player.deleteLater()
        self.play_loop()

    def intro_shown(self) -> bool:
        """The intro is playing and its first frame is on screen."""
        return self._intro is not None and self._intro_shown

    def intro_time(self) -> float | None:
        """Seconds into the intro on screen, or None when it isn't playing."""
        return self._intro_t if self._intro is not None else None

    def pause(self):
        if not self.ok:
            return
        if self._intro is not None:
            self._end_intro()              # a hidden intro isn't worth resuming
        self._loop[0].pause()

    def resume(self):
        if self.ok and self._intro is None:
            self.play_loop()

    def stop(self):
        if not self.ok:
            return
        if self._intro is not None:
            self._intro[0].stop()
            self._intro = None
        self._loop[0].stop()
