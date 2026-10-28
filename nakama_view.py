"""
nakama_view.py
The Nakama 仲間 tab (nakama.py has the data and the server calls).

Not joined: what Nakama is, what gets sent, a name box and Join.
Joined: your friend code (Copy), a box for a friend's code (Add), a short
list of members (you included) sorted by rank / this week / kanji /
grammar, and the selected member's card (share_card.render_profile) with
your own position ticked on every bar. Right-click a member: Copy code,
Remove (friends only). Two friends with the same name show the end of
their code.
"""

from __future__ import annotations

import html
import time

from aqt.qt import *

from . import nakama, rank_data
from .theme import HINT_CSS

SORTS = [("Kotodama rank", "rank"), ("This week", "week"),
         ("JLPT kanji", "kanji"), ("JLPT grammar", "grammar")]
REFETCH_AFTER = 60          # seconds between automatic fetches


def _metric(data: dict, key: str) -> int:
    if key in ("kanji", "grammar"):
        try:
            return int(((data.get(key) or {}).get("All") or [0])[0])
        except Exception:
            return 0
    return int(data.get(key) or 0)


def _thumb(count: int) -> QPixmap | None:
    try:
        from . import rank_images
        raw = rank_images.get_rank_art(rank_data.get_rank_info(count)["rank_name_en"])
    except Exception:
        raw = None
    if not raw:
        return None
    pm = QPixmap()
    pm.loadFromData(raw)
    return None if pm.isNull() else pm.scaled(
        54, 36, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)


class _Row(QWidget):
    """One member in the list: rank picture, name and belt, the sort
    metric, and this week's gain."""

    def __init__(self, profile: dict, me: bool, key: str, parent=None, show_code: bool = False):
        super().__init__(parent)
        data = profile.get("data") or {}
        count = int(data.get("rank") or 0)
        info = rank_data.get_rank_info(count)
        h = QHBoxLayout(self)
        h.setContentsMargins(6, 4, 8, 4)
        h.setSpacing(10)
        art = QLabel()
        art.setFixedSize(54, 36)
        pm = _thumb(count)
        if pm is not None:
            art.setPixmap(pm)
        h.addWidget(art)
        name = html.escape(profile.get("name") or "?")
        if profile.get("missing"):
            sub = "Code not found (left Nakama?)"
        else:
            sub = f"{info['rank_name_en']} · {info['belt_display_name']} belt"
        you = " <span style='color:#9a9a9a;'>(you)</span>" if me else ""
        if show_code and profile.get("id"):
            # two friends with the same name: the end of the code tells them apart
            you += f" <span style='color:#777777;'>…{html.escape(str(profile['id'])[-4:])}</span>"
        txt = QLabel(f"<b>{name}</b>{you}"
                     f"<br><span style='color:#888; font-size:12px;'>{html.escape(sub)}</span>")
        h.addWidget(txt, 1)
        val = _metric(data, key)
        v = QLabel(f"<b>{val:+,}</b>" if key == "week" else f"<b>{val:,}</b>")   # -1, not +-1
        v.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        h.addWidget(v)
        if key != "week" and data.get("week") is not None:
            w = int(data["week"])
            colour = "#7bd88f" if w > 0 else "#ff8a80" if w < 0 else "#9a9a9a"   # a loss isn't green
            wk = QLabel(f"<span style='color:{colour}; font-size:12px;'>{w:+,} wk</span>")
            wk.setFixedWidth(64)
            wk.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            h.addWidget(wk)


class NakamaTab(QWidget):

    def __init__(self, parent=None, recount=None):
        super().__init__(parent)
        # recount(then): the window's full recount (its Refresh), then `then`;
        # the ⟳ button runs it first so your card has today's marks and
        # cards (owner 2026-10-27: it sent the card from the last count).
        self._recount = recount
        self._last_fetch = 0.0
        self._selected = None      # code
        self._preview = None       # DEBUG: rank count the shown card is previewed at
        self._busy = False
        self._img = None
        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(10, 10, 10, 10)
        self._body = None
        self._build()

    # ── layout ───────────────────────────────────────────────────────────────

    def _build(self):
        if self._body is not None:
            self._root.removeWidget(self._body)
            self._body.hide()
            self._body.deleteLater()
        self._body = QWidget()
        self._root.addWidget(self._body)
        if nakama.joined():
            self._build_member(self._body)
        else:
            self._build_join(self._body)

    def _build_join(self, body):
        v = QVBoxLayout(body)
        v.setContentsMargins(0, 0, 0, 0)
        title = QLabel("<span style='font-size:20px;'><b>Nakama 仲間</b></span>"
                       "&nbsp;&nbsp;<span style='color:#9a9a9a;'>your friends' Kotodama bars, next to yours</span>")
        v.addWidget(title)
        about = QLabel(
            "Join to get a friend code. Anyone you give it to can add you and see your card: "
            "your name and the numbers on your bars (rank, JLPT words, top 20k words, kanji and "
            "grammar). No cards, words or deck names are sent. Your card updates after Anki "
            "syncs. You can leave at any time: your card is removed, and your code is kept for you.")
        about.setWordWrap(True)
        about.setStyleSheet("color: #bbbbbb; padding: 6px 0;")
        v.addWidget(about)
        row = QHBoxLayout()
        row.addWidget(QLabel("Name:"))
        from . import share_card
        self._name = QLineEdit(nakama.state().get("name") or share_card.saved_name())
        self._name.setPlaceholderText("The name your friends see")
        self._name.setMaxLength(32)
        self._name.setFixedWidth(260)
        row.addWidget(self._name)
        self._join_btn = QPushButton("Join Nakama")
        self._join_btn.clicked.connect(self._join)
        row.addWidget(self._join_btn)
        row.addStretch()
        v.addLayout(row)
        parked = nakama.parked_code()
        if parked:
            # left before: joining again gives the same code back (owner 2026-10-20)
            back = QLabel(f"Welcome back: you'll keep your code {nakama.show_code(parked)}.")
            back.setStyleSheet("color: #7bd88f;")
            v.addWidget(back)
        self._status = QLabel("")
        self._status.setStyleSheet("color: #e0a050;")
        self._status.setWordWrap(True)
        v.addWidget(self._status)
        v.addLayout(self._debug_row())
        # Your own card before joining: what friends will see.
        prev = QLabel("Your card, as your friends will see it:")
        prev.setStyleSheet(HINT_CSS)
        v.addWidget(prev)
        self._card = QLabel()
        self._card.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        self._card.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        v.addWidget(self._card, 1)
        self._name.textChanged.connect(lambda _t: self._render_own())
        self._render_own()

    def _render_own(self):
        """Join view: your card from your last count (with the debug
        preview's rank, if any)."""
        if nakama.joined() or not hasattr(self, "_card"):
            return
        mine = nakama.state().get("mine")
        if not mine:
            self._img = None
            self._card.setText("<span style='color:#9a9a9a;'>Your card appears here once your "
                               "bars are counted.</span>")
            return
        data = dict(mine, rank=self._preview) if self._preview is not None else mine
        from . import share_card
        self._img = share_card.render_profile(
            {"name": self._name.text().strip() or "Nakama", "data": data}, None, "", framed=False)
        self._show_img()

    def _build_member(self, body):
        s = nakama.state()
        v = QVBoxLayout(body)
        v.setContentsMargins(0, 0, 0, 0)
        top = QHBoxLayout()
        top.addWidget(QLabel("<span style='font-size:18px;'><b>Nakama 仲間</b></span>"))
        top.addSpacing(16)
        code = QLabel(f"Your code: <b style='font-size:15px; letter-spacing:1px;'>"
                      f"{nakama.show_code(s['id'])}</b>")
        code.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        top.addWidget(code)
        copy = QPushButton("Copy code")
        copy.clicked.connect(self._copy_code)
        top.addWidget(copy)
        top.addStretch()
        top.addWidget(QLabel("Name:"))
        self._name = QLineEdit(s.get("name") or "")
        self._name.setMaxLength(32)
        self._name.setFixedWidth(180)
        self._name.editingFinished.connect(self._rename)
        top.addWidget(self._name)
        leave = QPushButton("Leave Nakama")
        leave.clicked.connect(self._leave)
        top.addWidget(leave)
        v.addLayout(top)

        row = QHBoxLayout()
        self._code_edit = QLineEdit()
        self._code_edit.setPlaceholderText("A friend's code (ABCD-EFGH)")
        self._code_edit.setFixedWidth(220)
        self._code_edit.returnPressed.connect(self._add)
        row.addWidget(self._code_edit)
        add = QPushButton("Add friend")
        add.clicked.connect(self._add)
        row.addWidget(add)
        row.addStretch()
        row.addWidget(QLabel("Sort by:"))
        self._sort = QComboBox()
        for label, _k in SORTS:
            self._sort.addItem(label)
        self._sort.currentIndexChanged.connect(lambda _i: self._fill_list())
        row.addWidget(self._sort)
        ref = QPushButton("⟳ Refresh")
        ref.clicked.connect(self._refresh_clicked)
        row.addWidget(ref)
        v.addLayout(row)

        self._status = QLabel("")
        self._status.setStyleSheet(HINT_CSS)
        v.addWidget(self._status)
        v.addLayout(self._debug_row())

        split = QSplitter(Qt.Orientation.Horizontal)
        self._list = QListWidget()
        self._list.setMinimumWidth(300)        # room for "Shogun · Brown belt" at 12 px
        self._list.setWordWrap(True)          # the in-list hint wraps
        self._list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._list.customContextMenuRequested.connect(self._row_menu)
        self._list.currentItemChanged.connect(self._on_select)
        split.addWidget(self._list)
        self._card = QLabel()
        self._card.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        self._card.setMinimumWidth(300)
        self._card.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        split.addWidget(self._card)
        split.setStretchFactor(0, 0)
        split.setStretchFactor(1, 1)
        split.setSizes([340, 660])
        v.addWidget(split, 1)
        self._fill_list()

    # ── DEBUG: preview the shown card at any rank ────────────────────────────
    # Hidden like the Overview's debug row (same invisible switch at the
    # row's left, same shown/hidden state). Only the picture changes: nothing
    # is uploaded, no count changes (owner 2026-10-18).

    def _debug_row(self) -> QHBoxLayout:
        from .progress_dialog import _DEBUG_ROW
        line = QHBoxLayout()
        line.setSpacing(0)
        secret = QPushButton()
        secret.setFixedSize(28, 22)
        secret.setFlat(True)
        secret.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        secret.setStyleSheet("QPushButton, QPushButton:hover, QPushButton:pressed "
                             "{ background: transparent; border: none; }")
        secret.setProperty("jlpt_gold_skip", True)
        line.addWidget(secret)
        box = QWidget()
        box.setVisible(_DEBUG_ROW["shown"])
        line.addWidget(box, 1)
        self._debug_box = box          # follows the Overview's switch on every show

        def toggle():
            _DEBUG_ROW["shown"] = not _DEBUG_ROW["shown"]
            box.setVisible(_DEBUG_ROW["shown"])
        secret.clicked.connect(toggle)
        row = QHBoxLayout(box)
        row.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel("Debug preview:")
        lbl.setStyleSheet(HINT_CSS)
        row.addWidget(lbl)
        for text, kind, step in (("◀◀ Rank", "rank", -1), ("◀ Belt", "belt", -1),
                                 ("Belt ▶", "belt", 1), ("Rank ▶▶", "rank", 1)):
            b = QPushButton(text)
            b.clicked.connect(lambda _c=False, k=kind, s=step: self._debug_step(k, s))
            row.addWidget(b)
        reset = QPushButton("Reset")
        reset.clicked.connect(lambda: self._debug_set(None))
        row.addWidget(reset)
        self._debug_lbl = QLabel("")
        self._debug_lbl.setStyleSheet(HINT_CSS)
        row.addWidget(self._debug_lbl)
        row.addStretch()
        return line

    @staticmethod
    def _belt_starts() -> list[int]:
        """Every count where a belt or Amaterasu degree starts, plus 20,000."""
        return sorted(set(rank_data.BELT_THRESHOLDS[:-1]) | set(rank_data.DEGREE_THRESHOLDS)
                      | {rank_data.MAX_CARDS})

    def _shown_count(self) -> int:
        if self._preview is not None:
            return self._preview
        if not nakama.joined():
            return int((nakama.state().get("mine") or {}).get("rank") or 0)
        prof = next((m for c, m, _me in self._members() if c == self._selected), None)
        return int(((prof or {}).get("data") or {}).get("rank") or 0)

    def _debug_step(self, kind: str, step: int):
        starts = self._belt_starts()
        cur = self._shown_count()
        if kind == "rank":
            idx = rank_data.get_rank_info(cur)["rank_index"]
            ranks = {}
            for s in starts:               # the first count of every rank
                ranks.setdefault(rank_data.get_rank_info(s)["rank_index"], s)
            target = ranks.get(max(0, min(max(ranks), idx + step)))
            if step < 0 and cur > ranks.get(idx, 0):
                target = ranks[idx]        # back to the start of this rank first
            elif step > 0 and target <= cur:
                target = rank_data.MAX_CARDS   # past the last rank's start: 20,000 (gold card)
        else:
            later = [s for s in starts if s > cur]
            earlier = [s for s in starts if s < cur]
            target = (later[0] if later else cur) if step > 0 else (earlier[-1] if earlier else 0)
        self._debug_set(target)

    def _debug_set(self, count):
        self._preview = count
        if count is None:
            self._debug_lbl.setText("")
        else:
            info = rank_data.get_rank_info(count)
            self._debug_lbl.setText(f"{info['rank_name_en']} · {info['belt_display_name']} belt "
                                    f"({count:,})")
        if nakama.joined():
            self._on_select(self._list.currentItem(), None)
        else:
            self._render_own()

    # ── list and card ────────────────────────────────────────────────────────

    def _members(self) -> list[tuple[str, dict, bool]]:
        s = nakama.state()
        me = s.get("id")
        out = [(me, {"id": me, "name": s.get("name"), "data": s.get("mine") or {},
                     "updated": (s["cache"].get(me) or {}).get("updated")}, True)]
        for c in s["friends"]:
            out.append((c, s["cache"].get(c) or {"id": c, "name": nakama.show_code(c)}, False))
        return out

    def _fill_list(self):
        if not nakama.joined() or not hasattr(self, "_list"):
            return
        key = SORTS[self._sort.currentIndex()][1]
        members = sorted(self._members(),
                         key=lambda m: (bool(m[1].get("missing")), -_metric(m[1].get("data") or {}, key)))
        self._list.blockSignals(True)
        self._list.clear()
        sel_row = 0
        names = [(m[1].get("name") or "").strip().lower() for m in members]
        for i, (code, prof, me) in enumerate(members):
            it = QListWidgetItem()
            it.setData(Qt.ItemDataRole.UserRole, code)
            w = _Row(dict(prof, id=prof.get("id") or code), me, key,
                     show_code=names.count(names[i]) > 1 and bool(names[i]))
            it.setSizeHint(QSize(0, 48))
            self._list.addItem(it)
            self._list.setItemWidget(it, w)
            if code == self._selected:
                sel_row = i
        self._list.blockSignals(False)
        self._list.setCurrentRow(sel_row)
        self._on_select(self._list.currentItem(), None)
        if len(members) == 1:
            # The hint inside the list itself (owner 2026-10-18).
            it = QListWidgetItem("Add a friend's code above to see their card here.")
            it.setFlags(Qt.ItemFlag.NoItemFlags)
            it.setForeground(QColor("#7a7a7a"))
            it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it.setSizeHint(QSize(0, 60))
            self._list.addItem(it)

    def _on_select(self, item, _prev):
        if item is None:
            return
        self._selected = item.data(Qt.ItemDataRole.UserRole)
        prof = next((m for c, m, _me in self._members() if c == self._selected), None)
        if not prof:
            return
        me = self._selected == nakama.state().get("id")
        if prof.get("missing") or not prof.get("data"):
            self._img = None
            self._card.setText("<span style='color:#9a9a9a;'>"
                               + ("Nobody uses this code (any more)." if prof.get("missing")
                                  else "No card yet: press ⟳ Refresh.") + "</span>")
            return
        if self._preview is not None:      # DEBUG preview: this card at that rank
            prof = dict(prof, data=dict(prof["data"], rank=self._preview))
        from . import share_card
        self._img = share_card.render_profile(
            prof, None if me else nakama.state().get("mine"),
            nakama.synced_text(prof.get("updated")) if not me or prof.get("updated") else "",
            framed=False)
        self._show_img()

    def _show_img(self):
        if self._img is None:
            return
        w = min(max(300, self._card.width() - 8), self._img.width())
        h = max(200, self._card.height() - 8)
        self._card.setPixmap(QPixmap.fromImage(self._img).scaled(
            w, h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self._img is not None and hasattr(self, "_card"):
            self._show_img()

    def showEvent(self, e):
        super().showEvent(e)
        if nakama.adopt_collection():                 # membership arrived with a sync
            self._build()
        from .progress_dialog import _DEBUG_ROW
        box = getattr(self, "_debug_box", None)
        if box is not None:
            try:
                box.setVisible(_DEBUG_ROW["shown"])   # opened on the Overview → shown here too
            except RuntimeError:                       # its view was rebuilt
                pass
        self._render_own()
        self.refresh()

    # ── actions ──────────────────────────────────────────────────────────────

    def _set_status(self, text: str, error: bool = False):
        if hasattr(self, "_status"):
            self._status.setText(text)
            self._status.setStyleSheet(f"color: {'#e0a050' if error else '#9a9a9a'}; font-size: 12px;")

    def _refresh_clicked(self):
        if self._recount is not None and not self._busy:
            self._recount(lambda: self.refresh(force=True))
        else:
            self.refresh(force=True)

    def refresh(self, force: bool = False):
        """Send your card if it changed, then fetch everyone's."""
        if not nakama.joined() or self._busy:
            return
        if not force and time.time() - self._last_fetch < REFETCH_AFTER:
            return
        self._busy = True
        self._set_status("Updating…")

        def fetched(error):
            self._busy = False
            self._last_fetch = time.time()
            if error:
                self._set_status(error, error=True)
            else:
                self._set_status("")
            self._fill_list()

        def sent(_sent, error):
            if error:
                self._set_status(error, error=True)
            nakama.fetch_friends(fetched)
        nakama.upload_if_changed(sent)

    def _join(self):
        name = self._name.text().strip()
        if not name:
            self._status.setText("Type the name your friends will see first.")
            return
        if not nakama.state().get("mine"):
            self._status.setText("Your bars aren't counted yet: wait for the count to finish.")
            return
        self._join_btn.setEnabled(False)
        self._status.setText("Joining…")

        def done(ok, error):
            if not ok:
                self._join_btn.setEnabled(True)
                self._status.setText(error or "Couldn't join.")
                return
            self._last_fetch = 0
            self._build()
            self.refresh(force=True)
        nakama.join(name, done)

    def _copy_code(self):
        QApplication.clipboard().setText(nakama.show_code(nakama.state()["id"]))
        from aqt.utils import tooltip
        tooltip("Code copied", parent=self)

    def _rename(self):
        name = self._name.text().strip()
        if not name or name == nakama.state().get("name"):
            return
        # kept here at once; sent now, or with the next upload if the server
        # was updated less than a minute ago
        nakama.state()["name"] = name
        nakama.save()
        self._set_status("Saving your name…")

        def done(_sent, error):
            self._set_status(error or "Name saved.", error=bool(error))
            self._fill_list()
        nakama.upload_if_changed(done)

    def _add(self):
        code = nakama.clean_code(self._code_edit.text())
        if not code:
            self._set_status("A code is 8 letters and numbers, like ABCD-EFGH.", error=True)
            return
        if code == nakama.state().get("id"):
            self._set_status("That's your own code.", error=True)
            return
        if not nakama.add_friend(code):
            self._set_status("Already in your Nakama.", error=True)
            return
        self._code_edit.clear()
        self._selected = code
        self.refresh(force=True)

    def _row_menu(self, pos):
        item = self._list.itemAt(pos)
        if item is None:
            return
        code = item.data(Qt.ItemDataRole.UserRole)
        if not code:
            return
        m = QMenu(self)
        copy = m.addAction("Copy code")             # owner 2026-10-20: share a friend's code on
        act = None
        if code != nakama.state().get("id"):
            act = m.addAction("Remove from Nakama")
        chosen = m.exec(self._list.mapToGlobal(pos))
        if chosen == copy:
            QApplication.clipboard().setText(nakama.show_code(code))
            from aqt.utils import tooltip
            tooltip("Code copied", parent=self)
        elif act is not None and chosen == act:
            nakama.remove_friend(code)
            self._selected = None
            self._fill_list()

    def _leave(self):
        from aqt.utils import askUser
        if not askUser("Leave Nakama? Your name and card are removed from the server, and "
                       "friends who added you will no longer see you. Your code is kept for you, "
                       "so if you join again you get the same code back. Your friends list stays "
                       "here.", parent=self):
            return

        def done(ok, error):
            if not ok:
                self._set_status(error or "Couldn't leave.", error=True)
                return
            self._build()
        nakama.leave(done)
