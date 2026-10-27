"""
Rain on the glass (owner 2026-10-22: "atmospheric faint reflections and
rainy aesthetic … the light of the lit up tube can sometimes catch the rain
reflections … occasionally sparks … very rarely a random tube flicker with a
very very quiet sound").

RainGlass is a mouse-transparent pane over a whole window (the main window
and the grid windows), as if you looked at the neon street through a wet
window: drops sit on the glass, now and then one runs down leaving a faint
trail, faint rain falls beyond it, and drops / rain near a lit tube catch
its colour (and its flicker: the lights come from the window's neon
elements, progress_dialog.neon_lights). Rare events: sparks off a tube's
lit end in the tube's own colour, and (very rarely) one tube stuttering with a very quiet buzz
(stutter_fn).

Cheap by design: nothing is redrawn wholesale. Each frame repaints only the
small patches where something moved or faded (a drop is a few pixels, a
streak a thin strip), so the widgets underneath redraw only there; the
drops are repainted all together only when the light under them changes
(scrolling, a tab switch, a flicker). It stops while its window is in the
background or minimised, and in Amaterasu mode (no neon there).
"""

from __future__ import annotations

import math
import random
import time

from aqt.qt import *

FRAME_MS = 16                 # 60 fps while running: low frame rates looked bad (owner)
DROP_AREA = 7500              # px² of window per drop on the glass
LIGHT_REACH = 60              # px: how far a tube's light reaches a drop
SPARK_EVERY = (25.0, 70.0)    # s between sparks (random in this range)
STUTTER_EVERY = (150.0, 360.0)  # s between tube stutters (very rare)
SLIDE_EVERY = (1.5, 4.5)      # s between drops starting to run
RAIN_PER_S = 5.0              # falling streaks per second beyond the glass
LENS_FRAME_MS = 100           # frame interval with the rain off (only the lens effects)
# Lens effects on the glass (owner 2026-10-25, Settings → Night look):
VIGNETTE_ALPHA = 120          # the corners' darkness (0–255)
MIST_ALPHA = (1, 2)           # condensation: each blotch's alpha (owner 2026-10-25: (5, 12) was far too much)
MIST_REFOG_S = 1.5            # how often wiped glass mists over again a little
MIST_REFOG = 0.05             # … by this much of the original mist each time


class _Drop:
    __slots__ = ("x", "y", "r", "born", "life", "col", "k")

    def __init__(self, x, y, r, born, life):
        self.x, self.y, self.r, self.born, self.life = x, y, r, born, life
        self.col, self.k = None, 0.0           # the light it catches (RainGlass._relight)

    def rect(self) -> QRect:
        m = self.r * 1.5 + 2
        return QRect(int(self.x - m), int(self.y - m), int(2 * m) + 1, int(2 * m) + 2)

    def alpha(self, t) -> float:
        age = t - self.born
        return max(0.0, min(1.0, age / 0.6, (self.life - age) / 1.2))


def page_scroll_areas(win) -> list:
    """The window's page scrollers: scroll areas not inside another scroll
    area, and not lists / tables (owner 2026-10-25: rain moved when the
    recommended-words list inside the page scrolled), nor ones in a pop-up
    window the window owns (2026-10-26: the stars moved while scrolling the
    rank "?" window)."""
    out = []
    for area in win.findChildren(QScrollArea):
        if area.window() is not win:
            continue
        a = area.parentWidget()
        while a is not None and a is not win and not isinstance(a, QAbstractScrollArea):
            a = a.parentWidget()
        if a is None or a is win:
            out.append(area)
    return out


def _is_tube(w) -> bool:
    """A bar or level sign (sparks and stutters come off those), and still alive."""
    try:
        return bool(getattr(w, "_neon_tube", False)) and w.isVisible()
    except RuntimeError:
        return False


class RainGlass(QWidget):
    """The glass: its own see-through, click-through window laid exactly over
    `window`'s inside, owned by it (so it stays with it, above it). Windows
    composites it on top, so a moving drop repaints only the glass — never
    the widgets underneath (as a child widget, every drop made the whole
    stack under it repaint: ~30 % of a core)."""

    def __init__(self, window: QWidget, lights_fn, stutter_fn=None, off_fn=None, spark_fn=None,
                 rain_fn=None, fx_fn=None):
        super().__init__(window, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint
                         | Qt.WindowType.WindowTransparentForInput
                         | Qt.WindowType.WindowDoesNotAcceptFocus
                         | Qt.WindowType.NoDropShadowWindowHint)
        self._win = window
        self._lights_fn = lights_fn            # () → [(QRect, QColor, strength, widget)] in window coords
        self._stutter_fn = stutter_fn          # (widget) → None: one tube flickers, very quietly
        self._off_fn = off_fn or (lambda: False)   # True: no rain now (Amaterasu mode)
        self._spark_fn = spark_fn              # () → None: the spark's crackle
        self._rain_fn = rain_fn or (lambda: True)  # Settings → Rain
        self._fx_fn = fx_fn or (lambda key: True)  # Settings → Night look (effects.FX)
        self._vignette = None                  # (size, pixmap)
        self._mist = self._mist_orig = None    # condensation (QImage), wiped by running drops
        self._mist_wiped = QRect()             # where it was wiped, mists over again
        self._mist_at = 0.0
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._rnd = random.Random()
        self._t = 0.0                          # running time (paused time doesn't count)
        self._last = None
        self._frame = 0
        self._drops: list[_Drop] = []
        self._sliders: list[dict] = []
        self._streaks: list[list] = []         # [x, y, length, speed, alpha]
        self._sparks: list[dict] = []
        self._lights: list = []
        self._sig = None
        self._scroll_last: dict = {}           # id(scroll bar) → its last value (_follow_scroll)
        self._check_at = 0.0                   # next self-check (_self_check)
        r = self._rnd
        self._next = {"spark": r.uniform(6, 20),
                      "stutter": r.uniform(*STUTTER_EVERY), "slide": r.uniform(*SLIDE_EVERY)}
        self._rain_debt = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(FRAME_MS)
        self._timer.timeout.connect(self._tick)
        # While paused, a look once a second: an activation that came before
        # this pane existed (or Amaterasu mode turned off) sends no event.
        self._poll = QTimer(self)
        self._poll.setSingleShot(True)
        self._poll.setInterval(1000)
        self._poll.timeout.connect(self._resume)
        window.installEventFilter(self)
        self._place()
        self._fill_drops(initial=True)
        self._sync_shown()
        self._timer.start()

    def _place(self):
        """Exactly over the window's inside (its frame and title bar excluded)."""
        self.setGeometry(QRect(self._win.mapToGlobal(QPoint(0, 0)), self._win.size()))

    def _wanted(self) -> bool:
        """Not in Amaterasu mode, and the rain or a lens effect is on."""
        if self._off_fn():
            return False
        return self._rain_fn() or any(self._fx_fn(k) for k in ("fx_vignette", "fx_condensation"))

    def _sync_shown(self):
        """Shown with its window (not minimised, not in Amaterasu mode)."""
        w = self._win
        want = w.isVisible() and not w.isMinimized() and self._wanted()
        if want != self.isVisible():
            if want:
                self._place()
            self.setVisible(want)

    # ── window events: follow its size, pause in the background ──────────────
    def eventFilter(self, obj, event):
        # Never raise out of a Qt handler (PyQt6 would abort Anki).
        try:
            self._on_window_event(obj, event)
        except Exception:
            pass
        return False

    def _on_window_event(self, obj, event):
        if obj is self._win:
            et = event.type()
            if et == QEvent.Type.Resize:
                self._place()
                self._vignette = None
                self._mist = self._mist_orig = None
                self._mist_wiped = QRect()
                self._drops = [d for d in self._drops if d.x < self.width() and d.y < self.height()]
                del self._drops[self._target() * 3 // 2:]
                self._fill_drops()
            elif et == QEvent.Type.Move:
                self._place()
            elif et in (QEvent.Type.WindowActivate, QEvent.Type.Show, QEvent.Type.WindowStateChange):
                self._sync_shown()
                QTimer.singleShot(0, self._resume)
            elif et == QEvent.Type.Hide:
                self._pause()
                self.hide()
            elif et == QEvent.Type.WindowDeactivate:
                self._pause()
                self._poll.start()             # a missed WindowActivate can't strand it

    def _running(self) -> bool:
        w = self._win
        return w.isVisible() and not w.isMinimized() and w.isActiveWindow() and self._wanted()

    def _resume(self):
        try:
            if self._timer.isActive():
                return
            self._sync_shown()
            if self._running():
                self._last = None
                # Back from the background: work out every drop's light again
                # and draw the whole glass (only changed patches are drawn
                # per frame, and the glass may have lost its picture
                # meanwhile: the rain was gone, or drops caught no light
                # until something changed; owner 2026-10-25).
                self._lights, self._sig = [], None
                self._place()
                self.update()
                self._timer.start()
            else:
                self._poll.start()
        except RuntimeError:
            pass

    def _self_check(self):
        """Once a second while running: shown, in place, and following the
        window's scroll areas (new ones appear as tabs are built)."""
        want = self._win.isVisible() and not self._win.isMinimized() and self._wanted()
        if want and not self.isVisible():
            self._place()
            self.show()
            self.update()
        elif want and self.geometry() != QRect(self._win.mapToGlobal(QPoint(0, 0)), self._win.size()):
            self._place()
        for area in page_scroll_areas(self._win):
            bar = area.verticalScrollBar()
            if id(bar) in self._scroll_last:
                continue
            self._scroll_last[id(bar)] = bar.value()
            bar.valueChanged.connect(lambda v, a=area, b=bar: self._follow_scroll(a, b, v))

    def _follow_scroll(self, area, bar, value):
        """The page scrolled: every drop on the glass moves with it, as if the
        water were on the page (owner 2026-10-25; the whole glass since
        2026-10-26); the ones carried out of view dry up, new ones form."""
        try:
            last = self._scroll_last.get(id(bar), value)
            self._scroll_last[id(bar)] = value
            dy = value - last
            if not dy or not self.isVisible() or not area.isVisible():
                return
            # the whole glass, the header too (owner 2026-10-26: drops moving
            # only over the page split the window in two)
            box = QRect(0, 0, self.width(), self.height())
            inside = lambda x, y: box.contains(int(x), int(y))
            keep = []
            for d in self._drops:
                if inside(d.x, d.y):
                    d.y -= dy
                    if not inside(d.x, d.y):
                        continue
                keep.append(d)
            self._drops = keep
            live = []
            for sl in self._sliders:
                d = sl["drop"]
                if inside(d.x, d.y):
                    d.y -= dy
                    sl["stop"] -= dy
                    sl["trail"] = [(x, y - dy, t) for x, y, t in sl["trail"]]
                    if not inside(d.x, d.y):
                        continue
                live.append(sl)
            self._sliders = live
            for sp in self._sparks:
                if inside(sp["x0"], sp["y0"]):
                    sp["y0"] -= dy
                    for part in sp["parts"]:
                        part[1] -= dy
                    self._move_spark(sp, 0.0)
            self._lights, self._sig = [], None      # the tubes moved too: relight next frame
            self.update(box)
        except RuntimeError:
            pass

    def _pause(self):
        self._timer.stop()
        self._last = None

    # ── simulation ────────────────────────────────────────────────────────────
    def _target(self) -> int:
        return max(20, int(self.width() * self.height() / DROP_AREA))

    def _new_drop(self, born) -> _Drop:
        r = self._rnd
        return _Drop(r.uniform(0, self.width()), r.uniform(0, self.height()),
                     r.uniform(1.3, 3.4), born, r.uniform(20, 60))

    def _fill_drops(self, initial=False):
        while len(self._drops) < self._target():
            d = self._new_drop(self._t - (self._rnd.uniform(0.6, 8) if initial else 0))
            self._drops.append(d)

    def _tick(self):
        try:
            if not self._running():
                self._pause()
                self._sync_shown()               # hidden in Amaterasu mode / minimised
                self._poll.start()
                return
            now = time.monotonic()
            dt = 0.0 if self._last is None else min(now - self._last, 0.05)
            self._last = now
            self._t += dt
            self._frame += 1
            t, r = self._t, self._rnd
            dirty = QRegion()
            if t >= self._check_at:
                self._check_at = t + 1.0
                self._self_check()
                dirty += self._lens_check()
            raining = self._rain_fn()
            self._timer.setInterval(FRAME_MS if raining else LENS_FRAME_MS)
            if not raining and (self._drops or self._sliders or self._streaks or self._sparks):
                for d in self._drops + [sl["drop"] for sl in self._sliders]:
                    dirty += d.rect()
                for st in self._streaks:
                    dirty += self._streak_rect(st)
                for sp in self._sparks:
                    dirty += sp["box"]
                self._drops, self._sliders, self._streaks, self._sparks = [], [], [], []
            if self._mist is not None and not self._mist_wiped.isEmpty() and t >= self._mist_at:
                self._mist_at = t + MIST_REFOG_S
                dirty += self._refog()

            # the light under the glass: drops repaint when it changes
            if self._frame % 8 == 1 or not self._lights:
                lights = self._lights_fn()
                sig = tuple((q.x() // 3, q.y() // 3, q.width() // 6, round(k, 1), c.rgb())
                            for q, c, k, _w in lights)
                # Always the fresh list (a refresh rebuilds the bars in the
                # same places: same signature, new widgets); the drops only
                # repaint when the light itself changed.
                self._lights = lights
                if sig != self._sig:
                    self._sig = sig
                    for d in self._drops:
                        if self._relight(d):
                            dirty += d.rect()
                    for s in self._sliders:
                        self._relight(s["drop"])
                        dirty += s["drop"].rect()

            if not raining:
                if not dirty.isEmpty():
                    self.update(dirty)
                return

            # drops on the glass come and go
            keep = []
            for d in self._drops:
                age = t - d.born
                if age >= d.life:
                    dirty += d.rect()
                    continue
                if (age < 0.6 or d.life - age < 1.2) and self._frame % 6 == 0:
                    dirty += d.rect()          # fading in / out (10 steps a second is plenty)
                keep.append(d)
            self._drops = keep
            while len(self._drops) < self._target():
                d = self._new_drop(t)
                self._relight(d)
                self._drops.append(d)
                dirty += d.rect()

            # now and then a drop runs down the glass
            if t >= self._next["slide"] and len(self._sliders) < 3 and self._drops:
                self._next["slide"] = t + r.uniform(*SLIDE_EVERY)
                d = max(r.sample(self._drops, min(6, len(self._drops))), key=lambda q: q.r)
                self._drops.remove(d)
                d.r = max(d.r, 2.4)
                d.life, d.born = 1e9, t - 1.0
                self._sliders.append({"drop": d, "v": 0.0, "vmax": r.uniform(30, 80),
                                      "stop": d.y + r.uniform(70, 320), "trail": [], "dx": r.uniform(-0.3, 0.3)})
            live = []
            for s in self._sliders:
                d = s["drop"]
                dirty += d.rect()
                s["v"] = min(s["vmax"], s["v"] + 60 * dt)
                d.y += s["v"] * dt
                d.x += s["dx"] * math.sin(t * 7 + d.r) * 0.4
                self._relight(d)
                dirty += self._wipe(d)
                s["trail"].append((d.x, d.y, t))
                s["trail"] = [p for p in s["trail"] if t - p[2] < 1.8]
                dirty += d.rect()
                if self._frame % 12 == 0 and s["trail"]:        # the faint trail fades at 5 fps
                    xs = [p[0] for p in s["trail"]]
                    ys = [p[1] for p in s["trail"]]
                    dirty += QRect(int(min(xs) - 3), int(min(ys) - 3), int(max(xs) - min(xs)) + 7,
                                   int(max(ys) - min(ys)) + 7)
                # it swallows the small drops it runs into
                for q in [q for q in self._drops if abs(q.x - d.x) < d.r + q.r and abs(q.y - d.y) < d.r + q.r]:
                    self._drops.remove(q)
                    dirty += q.rect()
                    d.r = min(4.2, d.r + 0.15)
                if d.y < s["stop"] and d.y < self.height() + 10:
                    live.append(s)
                else:                          # it stops and stays a while
                    d.life, d.born = r.uniform(6, 20), t - 0.6
                    self._drops.append(d)
                    if s["trail"]:
                        xs = [p[0] for p in s["trail"]]
                        ys = [p[1] for p in s["trail"]]
                        dirty += QRect(int(min(xs) - 3), int(min(ys) - 3), int(max(xs) - min(xs)) + 7,
                                       int(max(ys) - min(ys)) + 7)
            self._sliders = live

            # faint rain falling beyond the glass
            self._rain_debt += RAIN_PER_S * dt
            while self._rain_debt >= 1:
                self._rain_debt -= 1
                self._streaks.append([r.uniform(0, self.width() + 40), r.uniform(-60, -10),
                                      r.uniform(18, 40), r.uniform(700, 1100), r.uniform(0.5, 1.0)])
            live = []
            for s in self._streaks:
                dirty += self._streak_rect(s)
                s[1] += s[3] * dt
                s[0] -= s[3] * dt * 0.16
                if s[1] < self.height() + 10:
                    dirty += self._streak_rect(s)
                    live.append(s)
            self._streaks = live

            # rare events
            tubes = [lt for lt in self._lights if _is_tube(lt[3])]
            if t >= self._next["spark"]:
                self._next["spark"] = t + r.uniform(*SPARK_EVERY)
                if tubes:
                    self._spark(r.choice(tubes), t)
            if t >= self._next["stutter"]:
                self._next["stutter"] = t + r.uniform(*STUTTER_EVERY)
                if tubes and self._stutter_fn is not None:
                    try:
                        self._stutter_fn(r.choice(tubes)[3])
                    except RuntimeError:          # that tube was just rebuilt
                        pass
            live = []
            for sp in self._sparks:
                dirty += sp["box"]
                age = t - sp["t0"]
                if age < 0.9:
                    self._move_spark(sp, dt)
                    dirty += sp["box"]
                    live.append(sp)
            self._sparks = live

            if not dirty.isEmpty():
                self.update(dirty)
        except RuntimeError:
            # A widget deleted underneath (a refresh): drop the stale lights
            # and carry on; stop only if the window itself is gone.
            if not getattr(self, "_err_shown", False):
                self._err_shown = True             # once, for the debug log
                import traceback
                traceback.print_exc()
            self._lights, self._sig = [], None
            try:
                self._win.isVisible()
            except RuntimeError:
                self._timer.stop()

    @staticmethod
    def _streak_rect(s) -> QRect:
        x, y, length = s[0], s[1], s[2]
        return QRect(int(x - length * 0.16 - 2), int(y - 2), int(length * 0.16) + 5, int(length) + 5)

    def _spark(self, light, t):
        """A burst off the tube's lit end, in the tube's own colour."""
        rect, color, _k, _w = light
        r = self._rnd
        x0, y0 = rect.right() - 1, rect.center().y() + r.uniform(-rect.height() * 0.3, rect.height() * 0.3)
        # Twice the first size (owner 2026-10-22: "increase the spark by double"):
        # twice the pieces, flying twice as far, thicker, a bigger flash.
        parts = []
        for _ in range(r.randint(18, 32)):
            a = r.uniform(-math.pi * 0.95, math.pi * 0.25)
            v = r.uniform(140, 460)
            parts.append([x0, y0, math.cos(a) * v, math.sin(a) * v, r.uniform(0.35, 0.85)])
        sp = {"t0": t, "x0": x0, "y0": y0, "color": QColor(color), "parts": parts, "box": QRect()}
        self._move_spark(sp, 0.0)
        self._sparks.append(sp)
        if self._spark_fn is not None:
            try:
                self._spark_fn()
            except Exception:
                pass

    def spark_from(self, widget):
        """A spark off this tube now (it just came on), if the rain is running
        and the tube is lit on screen."""
        try:
            if not self._timer.isActive():
                return
            for light in self._lights_fn():
                if light[3] is widget:
                    self._spark(light, self._t)
                    return
        except Exception:
            pass

    def _move_spark(self, sp, dt):
        xs, ys = [sp["x0"]], [sp["y0"]]
        for p in sp["parts"]:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[3] += 700 * dt                   # gravity
            p[2] *= 0.985
            xs += [p[0], p[0] - p[2] * 0.04]
            ys += [p[1], p[1] - p[3] * 0.04]
        sp["box"] = QRect(int(min(xs) - 24), int(min(ys) - 24), int(max(xs) - min(xs)) + 49,
                          int(max(ys) - min(ys)) + 49)

    # ── lens effects (Settings → Night look) ──────────────────────────────────
    def _lens_check(self) -> QRegion:
        """Once a second: an effect switched on / off in Settings → redraw."""
        on = (self._fx_fn("fx_vignette"), self._fx_fn("fx_condensation"))
        if on != getattr(self, "_lens_on", on):
            self._lens_on = on
            return QRegion(self.rect())
        self._lens_on = on
        return QRegion()

    def _vignette_pm(self):
        if self._vignette is None or self._vignette[0] != self.size():
            w, h = max(self.width(), 1), max(self.height(), 1)
            pm = QPixmap(w, h)
            pm.fill(Qt.GlobalColor.transparent)
            p = QPainter(pm)
            g = QRadialGradient(QPointF(w / 2, h / 2), math.hypot(w, h) / 2)
            for at, a in ((0.0, 0), (0.55, 0), (0.8, VIGNETTE_ALPHA * 0.45), (1.0, VIGNETTE_ALPHA)):
                g.setColorAt(at, QColor(0, 0, 0, int(a)))
            p.fillRect(pm.rect(), QBrush(g))
            p.end()
            self._vignette = (self.size(), pm)
        return self._vignette[1]

    def _mist_img(self):
        if self._mist is None or self._mist.size() != self.size():
            w, h = max(self.width(), 1), max(self.height(), 1)
            img = QImage(w, h, QImage.Format.Format_ARGB32_Premultiplied)
            img.fill(Qt.GlobalColor.transparent)
            p = QPainter(img)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.setPen(Qt.PenStyle.NoPen)
            rnd = random.Random(5)
            for _ in range(int(w * h / 5200)):
                x, y, r = rnd.uniform(0, w), rnd.uniform(0, h), rnd.uniform(18, 70)
                g = QRadialGradient(QPointF(x, y), r)
                g.setColorAt(0, QColor(220, 228, 240, rnd.randint(*MIST_ALPHA)))
                g.setColorAt(1, QColor(220, 228, 240, 0))
                p.setBrush(QBrush(g))
                p.drawEllipse(QPointF(x, y), r, r)
            p.end()
            self._mist, self._mist_orig = img, img.copy()
            self._mist_wiped = QRect()
        return self._mist

    def _wipe(self, d) -> QRegion:
        """A running drop wipes the mist off the glass where it passes."""
        if not self._fx_fn("fx_condensation") or self._mist is None:
            return QRegion()
        r = d.r * 2.4
        p = QPainter(self._mist)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationOut)
        g = QRadialGradient(QPointF(d.x, d.y), r)
        g.setColorAt(0, QColor(0, 0, 0, 230))
        g.setColorAt(1, QColor(0, 0, 0, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(g))
        p.drawEllipse(QPointF(d.x, d.y), r, r)
        p.end()
        box = QRect(int(d.x - r - 1), int(d.y - r - 1), int(2 * r) + 3, int(2 * r) + 3)
        self._mist_wiped = self._mist_wiped.united(box)
        return QRegion(box)

    def _refog(self) -> QRegion:
        """Wiped glass slowly mists over again (a little of the original
        mist laid back on, which settles at the original)."""
        box = self._mist_wiped
        p = QPainter(self._mist)
        p.setOpacity(MIST_REFOG)
        p.drawImage(box, self._mist_orig, box)
        p.end()
        self._mist_refogs = getattr(self, "_mist_refogs", 0) + 1
        if self._mist_refogs > 80:                 # back to the original by now
            self._mist = self._mist_orig.copy()
            self._mist_wiped = QRect()
            self._mist_refogs = 0
        return QRegion(box)

    # ── drawing ───────────────────────────────────────────────────────────────
    def _relight(self, d) -> bool:
        """Work out the light a drop catches; True if it changed."""
        col, k = self._light_at(d.x, d.y)
        k = round(k, 2) if col is not None and k > 0.3 else 0.0
        col = col if k else None
        changed = k != d.k or (col is not None and (d.col is None or col.rgb() != d.col.rgb()))
        d.col, d.k = col, k
        return changed

    def _light_at(self, x, y):
        best, col = 0.0, None
        for rect, color, k, _w in self._lights:
            dx = max(rect.left() - x, 0, x - rect.right())
            dy = max(rect.top() - y, 0, y - rect.bottom())
            d = math.hypot(dx, dy)
            if d < LIGHT_REACH:
                v = k * (1 - d / LIGHT_REACH)
                if v > best:
                    best, col = v, color
        return col, best

    def paintEvent(self, event):
        p = QPainter(self)
        try:
            self._paint(p, event.region())
        except Exception:                      # never raise out of a paint (PyQt6 aborts)
            pass
        p.end()

    def _paint(self, p, er):
        """er: the dirty region; only what's in it is drawn."""
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        t = self._t
        br = er.boundingRect()
        if self._fx_fn("fx_vignette"):
            p.drawPixmap(br, self._vignette_pm(), br)
        if self._fx_fn("fx_condensation"):
            p.drawImage(br, self._mist_img(), br)
        # rain beyond the glass
        for s in self._streaks:
            if not er.intersects(self._streak_rect(s)):
                continue
            col, k = self._light_at(s[0], s[1] + s[2] / 2)
            if col is not None and k > 0.25:
                c = QColor(col).lighter(140)
                c.setAlpha(int(70 * k * s[4]))
                p.setPen(QPen(c, 1.3))
            else:
                p.setPen(QPen(QColor(220, 230, 255, int(16 * s[4])), 1))
            p.drawLine(QPointF(s[0], s[1]), QPointF(s[0] - s[2] * 0.16, s[1] + s[2]))
        # trails of running drops
        for s in self._sliders:
            tr = s["trail"]
            for a, b in zip(tr, tr[1:]):
                fade = max(0.0, 1 - (t - b[2]) / 1.8)
                p.setPen(QPen(QColor(255, 255, 255, int(20 * fade)), 1.2))
                p.drawLine(QPointF(a[0], a[1]), QPointF(b[0], b[1]))
        # drops
        for d in self._drops + [s["drop"] for s in self._sliders]:
            if not er.intersects(d.rect()):
                continue
            a = d.alpha(t)
            if a <= 0:
                continue
            col, k = d.col, d.k
            if col is not None:
                g = QRadialGradient(QPointF(d.x + d.r * 0.3, d.y + d.r * 0.3), d.r * 1.2)
                c0 = QColor(col).lighter(160)
                c0.setAlpha(int((80 + 140 * k) * a))
                c1 = QColor(col)
                c1.setAlpha(int(40 * k * a))
                g.setColorAt(0, c0)
                g.setColorAt(1, c1)
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QBrush(g))
                p.drawEllipse(QPointF(d.x, d.y), d.r, d.r * 1.15)
                p.setBrush(QColor(255, 255, 255, int(150 * k * a)))
                p.drawEllipse(QPointF(d.x - d.r * 0.35, d.y - d.r * 0.4), d.r * 0.3, d.r * 0.3)
            else:
                p.setBrush(QColor(0, 0, 0, int(38 * a)))
                p.setPen(QPen(QColor(255, 255, 255, int(24 * a)), 0.7))
                p.drawEllipse(QPointF(d.x, d.y), d.r, d.r * 1.15)
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor(255, 255, 255, int(38 * a)))
                p.drawEllipse(QPointF(d.x - d.r * 0.35, d.y - d.r * 0.4), d.r * 0.25, d.r * 0.25)
        # sparks, in the tube's colour
        for sp in self._sparks:
            if not er.intersects(sp["box"]):
                continue
            age = t - sp["t0"]
            base = sp["color"]
            if age < 0.12:                     # the flash where it broke off
                g = QRadialGradient(QPointF(sp["x0"], sp["y0"]), 22)
                c0 = QColor(base).lighter(170)
                c0.setAlpha(int(220 * (1 - age / 0.12)))
                c1 = QColor(base)
                c1.setAlpha(0)
                g.setColorAt(0, c0)
                g.setColorAt(1, c1)
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QBrush(g))
                p.drawEllipse(QPointF(sp["x0"], sp["y0"]), 22, 22)
            for x, y, vx, vy, life in sp["parts"]:
                f = 1 - age / life
                if f <= 0:
                    continue
                c = QColor(base).lighter(150)
                c.setAlpha(int(230 * f))
                p.setPen(QPen(c, 1.8))
                p.drawLine(QPointF(x, y), QPointF(x - vx * 0.04, y - vy * 0.04))
                p.setPen(Qt.PenStyle.NoPen)
                core = QColor(base).lighter(190)
                core.setAlpha(int(255 * f))
                p.setBrush(core)
                p.drawEllipse(QPointF(x, y), 2.0, 2.0)
