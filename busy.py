"""A "please wait" note over a Kotodama window while something is built on
the main thread (a tab, a grid window, a refreshed window) — owner
2026-10-25: "it should be indicated that they need to wait and that their
Anki's not crashing". The work can't run anywhere else (Qt widgets live on
the main thread), so the note is drawn first, then the work runs, then it
goes.

    with busy(self, "Building the Word Grid…"):
        build()
"""

from contextlib import contextmanager

from aqt.qt import QApplication, QFrame, QLabel, QVBoxLayout, Qt

SUBTITLE = "Please wait…"           # owner 2026-10-26

_depth = {"n": 0}         # nested busy(): only the outermost shows a note


def _gold() -> bool:
    try:
        from .progress_dialog import _GOLD_MODE
        return bool(_GOLD_MODE["on"])
    except Exception:
        return False


class BusyNote(QFrame):
    """The note itself: a title and a quiet line under it, centred over
    `parent`. Gold mode: gold border and Japanese text (divine_text)."""

    def __init__(self, parent, title: str):
        super().__init__(parent)
        gold = _gold()
        sub = SUBTITLE
        if gold:
            from . import divine_text
            title, sub = divine_text.translate(title), divine_text.translate(sub)
        edge, fg = ("#c9a227", "#f5c518") if gold else ("#555555", "#e8e8e8")
        self.setObjectName("kbusy")
        self.setStyleSheet(f"#kbusy {{ background: rgba(20, 20, 24, 240); border: 1px solid {edge};"
                           " border-radius: 10px; }")
        v = QVBoxLayout(self)
        v.setContentsMargins(28, 14, 28, 14)
        v.setSpacing(4)
        t = QLabel(title)
        t.setStyleSheet(f"color: {fg}; font-size: 15px; font-weight: bold; background: transparent;")
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        s = QLabel(sub)
        s.setStyleSheet("color: #9a9a9a; font-size: 12px; background: transparent;")
        s.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(t)
        v.addWidget(s)
        self.adjustSize()
        self.move(max(0, (parent.width() - self.width()) // 2),
                  max(0, (parent.height() - self.height()) // 2))


def show_note(parent, title: str):
    """A note that stays until close_note() (for waits that span the event
    loop, e.g. a count running in the background)."""
    note = BusyNote(parent, title)
    note.show()
    note.raise_()
    note.repaint()                       # drawn before the main thread gets busy
    return note


def close_note(note):
    if note is None:
        return
    try:
        note.hide()
        note.deleteLater()
    except RuntimeError:
        pass                             # its window closed meanwhile


@contextmanager
def busy(widget, title: str):
    """Note + wait cursor over widget's window while the block runs."""
    win = None
    try:
        win = widget.window() if widget is not None else None
    except RuntimeError:
        pass
    if win is None or not win.isVisible() or _depth["n"]:
        yield
        return
    _depth["n"] += 1
    note = BusyNote(win, title)
    note.show()
    note.raise_()
    QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
    try:
        win.repaint()                    # the whole frame now (a tab switch too)
        yield
    finally:
        QApplication.restoreOverrideCursor()
        close_note(note)
        _depth["n"] -= 1
