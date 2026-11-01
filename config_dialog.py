"""
config_dialog.py
Settings dialog: one scrolling page (owner 2026-10-26) — deck and fields,
kanji and grammar sources, then the look and sound. The JLPT word lists are
always the bundled ones (owner 2026-10-26: Nakama compares everyone's bars,
so everyone uses the same lists; the per-level upload was removed).
"""

from aqt.qt import *
from aqt import mw


def _remove_button() -> QPushButton:
    """A row's ✕. No padding: Anki's button padding (2px 6px) squeezed the
    glyph out of the narrow button, and #c00 vanished on the dark theme
    (owner 2026-10-26: the buttons looked empty)."""
    btn = QPushButton("✕")
    btn.setFixedSize(28, 26)
    btn.setToolTip("Remove this row")
    btn.setStyleSheet("QPushButton { color: #e05555; padding: 0px; "
                      "font-size: 13px; font-weight: bold; }")
    return btn


# ── Field mapping row ─────────────────────────────────────────────────────────

class FieldMappingRow(QWidget):
    removed = pyqtSignal(object)

    def __init__(self, note_types, note_type="", field="", reading_field="",
                 sentence_field="", parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)

        self.note_combo = QComboBox()
        self.note_combo.addItem("(all note types)")
        for nt in note_types:
            self.note_combo.addItem(nt)
        if note_type and note_type in note_types:
            self.note_combo.setCurrentText(note_type)

        self.field_edit = QLineEdit(field)
        self.field_edit.setPlaceholderText("Kanji spelling field  e.g. Expression")

        self.reading_edit = QLineEdit(reading_field)
        self.reading_edit.setPlaceholderText("Reading field  e.g. Reading")

        self.sentence_edit = QLineEdit(sentence_field)
        self.sentence_edit.setPlaceholderText("Sentence field  e.g. Sentence")
        self.sentence_edit.setToolTip(
            "The card's example sentence. Used by the auto parser for kanji and grammar "
            "(Kanji and Grammar below). With no word field, the vocab is parsed from it too.")

        btn = _remove_button()
        btn.clicked.connect(lambda: self.removed.emit(self))

        layout.addWidget(self.note_combo, 2)
        layout.addWidget(self.field_edit, 2)
        layout.addWidget(self.reading_edit, 2)
        layout.addWidget(self.sentence_edit, 2)
        layout.addWidget(btn, 0)

    def get_mapping(self):
        nt = self.note_combo.currentText()
        m = {
            "note_type":     "" if nt == "(all note types)" else nt,
            "field":         self.field_edit.text().strip(),
            "reading_field": self.reading_edit.text().strip(),
        }
        # Only stored when set, so existing mappings (and the history
        # signature built from them) don't change.
        if self.sentence_edit.text().strip():
            m["sentence_field"] = self.sentence_edit.text().strip()
        return m


class SimpleFieldRow(QWidget):
    """Note type + one field (kanji source, later grammar)."""
    removed = pyqtSignal(object)

    def __init__(self, note_types, note_type="", field="", placeholder="", parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        self.note_combo = QComboBox()
        self.note_combo.addItem("(all note types)")
        for nt in note_types:
            self.note_combo.addItem(nt)
        if note_type and note_type in note_types:
            self.note_combo.setCurrentText(note_type)
        self.field_edit = QLineEdit(field)
        self.field_edit.setPlaceholderText(placeholder)
        btn = _remove_button()
        btn.clicked.connect(lambda: self.removed.emit(self))
        layout.addWidget(self.note_combo, 2)
        layout.addWidget(self.field_edit, 2)
        layout.addWidget(btn, 0)

    def get_mapping(self):
        nt = self.note_combo.currentText()
        return {"note_type": "" if nt == "(all note types)" else nt,
                "field": self.field_edit.text().strip()}


# ── Main config dialog ────────────────────────────────────────────────────────

def _scrolled(page: QWidget) -> QScrollArea:
    """The settings page, scrolling when the window is shorter than it
    (owner 2026-10-26: Settings ran off the bottom of the screen)."""
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setWidget(page)
    return scroll


class ConfigDialog(QDialog):
    def __init__(self, parent, cfg):
        super().__init__(parent)
        self.setWindowTitle("Kotodama — Settings")
        self.setMinimumWidth(860)
        self.setMinimumHeight(500)
        self._cfg          = cfg
        self._rows         = []
        self._note_types   = sorted(m["name"] for m in mw.col.models.all())
        self._build_ui()
        # as tall as its content (the page scrolls, so ask for it), then
        # fit_on_screen keeps it above the taskbar once shown
        self.resize(max(self.width(), 900), self._page.sizeHint().height() + 80)

    def showEvent(self, event):
        super().showEvent(event)
        if not getattr(self, "_fitted", False):
            self._fitted = True
            from .theme import fit_on_screen
            QTimer.singleShot(0, lambda: fit_on_screen(self))

    def _build_ui(self):
        outer = QVBoxLayout(self)
        page  = QWidget()
        self._page = page
        dt = QVBoxLayout(page)
        dt.setSpacing(10)
        outer.addWidget(_scrolled(page))

        # ── Deck & fields ─────────────────────────────────────────────────

        deck_grp = QGroupBox("Deck to analyse (includes sub-decks)")
        dl = QHBoxLayout(deck_grp)
        self.deck_combo = QComboBox()
        self.deck_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        deck_names = sorted(d["name"] for d in mw.col.decks.all())
        for n in deck_names:
            self.deck_combo.addItem(n)
        saved = self._cfg.get("deck_name", "")
        if saved in deck_names:
            self.deck_combo.setCurrentText(saved)
        dl.addWidget(self.deck_combo)
        dt.addWidget(deck_grp)

        map_grp = QGroupBox("Vocab — which fields hold your words?")
        ml = QVBoxLayout(map_grp)
        hint = QLabel(
            "Add one row per note type.  "
            "<b>Kanji spelling field</b>: the field with kanji or kana (e.g. Expression).  "
            "<b>Reading field</b>: a separate kana-only field (e.g. Reading).  "
            "Adding the reading field helps match words like めがね ↔ 眼鏡 and avoids "
            "false positives from homophones (家庭 vs 課程 are both かてい but stay separate "
            "because their display forms differ).  "
            "<b>Sentence field</b>: the card's example sentence, read by the auto "
            "parser for kanji and grammar. A row with a sentence field but no word field is a "
            "sentence card: every word in its sentence counts as its vocab."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: gray; font-size: 11px;")
        ml.addWidget(hint)

        # Column headers
        hdr = QHBoxLayout()
        for txt, stretch in [("Note type", 2), ("Kanji spelling field", 2), ("Reading field", 2), ("Sentence field", 2), ("", 0)]:
            lbl = QLabel(f"<b>{txt}</b>")
            lbl.setStyleSheet("font-size: 10px; color: #aaa;")
            hdr.addWidget(lbl, stretch)
        ml.addLayout(hdr)

        self._rows_widget = QWidget()
        self._rows_vbox   = QVBoxLayout(self._rows_widget)
        self._rows_vbox.setContentsMargins(0, 0, 0, 0)
        self._rows_vbox.setSpacing(2)
        ml.addWidget(self._rows_widget)

        add_btn = QPushButton("＋ Add vocab field")
        add_btn.clicked.connect(lambda: self._add_row())
        ml.addWidget(add_btn)
        dt.addWidget(map_grp)

        # ── Kanji and grammar sources ──────────────────────────────────────
        self._add_kanji_grammar(dt, deck_names)

        # ── Anki-suspended cards ───────────────────────────────────────────
        susp_grp = QGroupBox("Suspended cards")
        sg = QVBoxLayout(susp_grp)
        self.ignore_susp_chk = QCheckBox("Ignore cards suspended in Anki")
        self.ignore_susp_chk.setChecked(bool(self._cfg.get("ignore_suspended_cards", False)))
        sg.addWidget(self.ignore_susp_chk)
        susp_hint = QLabel(
            "Notes whose cards are all suspended in Anki won't count toward "
            "the JLPT bars, the Frequency Check or the rank."
        )
        susp_hint.setWordWrap(True)
        susp_hint.setStyleSheet("color: gray; font-size: 11px;")
        sg.addWidget(susp_hint)
        dt.addWidget(susp_grp)

        # ── Mini overview widget toggle ────────────────────────────────────
        mini_grp = QGroupBox("Main screen widget")
        mg = QVBoxLayout(mini_grp)
        self.mini_widget_chk = QCheckBox(
            "Show a mini progress overview on the main Anki screen"
        )
        self.mini_widget_chk.setChecked(bool(self._cfg.get("mini_widget_enabled", True)))
        self.mini_rank_chk = QCheckBox("Include rank")
        self.mini_rank_chk.setToolTip(
            "Show your Kotodama Japanese Rank, belt and their progress bars "
            "under the N5–N1 bars")
        self.mini_rank_chk.setChecked(bool(self._cfg.get("mini_widget_show_rank", True)))
        self.mini_rank_chk.setEnabled(self.mini_widget_chk.isChecked())
        self.mini_widget_chk.toggled.connect(self.mini_rank_chk.setEnabled)
        self.mini_art_chk = QCheckBox("Rank picture")
        self.mini_art_chk.setToolTip(
            "Show a mini version of your rank's picture and badge background "
            "(as on the Overview tab) in the widget's rank section")
        self.mini_art_chk.setChecked(bool(self._cfg.get("mini_widget_show_rank_art", True)))

        def _art_enabled(*_):
            self.mini_art_chk.setEnabled(self.mini_widget_chk.isChecked()
                                         and self.mini_rank_chk.isChecked())
        _art_enabled()
        self.mini_widget_chk.toggled.connect(_art_enabled)
        self.mini_rank_chk.toggled.connect(_art_enabled)
        mini_row = QHBoxLayout()
        mini_row.addWidget(self.mini_widget_chk)
        mini_row.addSpacing(16)
        mini_row.addWidget(self.mini_rank_chk)
        mini_row.addSpacing(16)
        mini_row.addWidget(self.mini_art_chk)
        mini_row.addStretch()
        mg.addLayout(mini_row)
        mini_hint = QLabel(
            "Adds a small always-visible set of N5–N1 progress bars "
            "next to your deck list on the main screen."
        )
        mini_hint.setWordWrap(True)
        mini_hint.setStyleSheet("color: gray; font-size: 11px;")
        mg.addWidget(mini_hint)
        dt.addWidget(mini_grp)

        # ── Amaterasu: only shown once it's unlocked, so it stays a surprise
        # (owner 2026-10-10; the chime is no longer a setting) ──
        self.seal_chk = None
        self.sound_chk = None
        try:
            from .seal import _in_amaterasu_mode
            unlocked = _in_amaterasu_mode()
        except Exception:
            unlocked = False
        if unlocked:
            top_grp = QGroupBox("Amaterasu")
            tg = QVBoxLayout(top_grp)
            self.seal_chk = QCheckBox("Show the 天照大神 seal on the review screen")
            self.seal_chk.setToolTip("A small gold seal in the corner while you review")
            self.seal_chk.setChecked(bool(self._cfg.get("review_seal", False)))
            tg.addWidget(self.seal_chk)
            # The star's sound (ambience.py) is continuous, so it can be
            # muted (owner 2026-10-16); on by default.
            self.sound_chk = QCheckBox("Play the star's sound")
            self.sound_chk.setToolTip("The ascension and the soft ambience while the window "
                                      "is in Amaterasu mode")
            self.sound_chk.setChecked(bool(self._cfg.get("amaterasu_sound", True)))
            tg.addWidget(self.sound_chk)
            dt.addWidget(top_grp)

        # ── Sound effects: one volume for every sound (owner 2026-10-22;
        # effects.py). Moving it plays a sample at the new level. ──
        from . import effects
        snd_grp = QGroupBox("Sound effects")
        sv = QVBoxLayout(snd_grp)
        snd_row = QHBoxLayout()
        snd_row.addWidget(QLabel("Volume"))
        self.effects_slider = QSlider(Qt.Orientation.Horizontal)
        self.effects_slider.setRange(0, 100)
        self.effects_slider.setSingleStep(5)
        self.effects_slider.setPageStep(10)
        self.effects_slider.setValue(int(self._cfg.get(effects.KEY, effects.DEFAULT)))
        snd_val = QLabel()
        snd_val.setMinimumWidth(36)

        def _show_volume(v):
            snd_val.setText("Off" if v == 0 else f"{v}%")
        _show_volume(self.effects_slider.value())
        self.effects_slider.valueChanged.connect(_show_volume)
        # A sample once the slider settles (drag, click or keys).
        self._snd_timer = QTimer(self)
        self._snd_timer.setSingleShot(True)
        self._snd_timer.setInterval(350)

        def _sample():
            from . import neon_sound
            neon_sound.preview(self.effects_slider.value() / 100)
        self._snd_timer.timeout.connect(_sample)
        self.effects_slider.valueChanged.connect(lambda _v: self._snd_timer.start())
        snd_row.addWidget(self.effects_slider, 1)
        snd_row.addWidget(snd_val)
        sv.addLayout(snd_row)
        self.mini_sound_chk = QCheckBox("Mini widget sounds")
        self.mini_sound_chk.setToolTip(
            "The mini widget's bars flickering on, on the deck list. "
            "Off: the widget stays silent; the Kotodama window keeps its sounds.")
        self.mini_sound_chk.setChecked(bool(self._cfg.get(effects.MINI_SOUND_KEY, True)))
        self.mini_sound_chk.setEnabled(self.effects_slider.value() > 0)
        self.effects_slider.valueChanged.connect(lambda v: self.mini_sound_chk.setEnabled(v > 0))
        sv.addWidget(self.mini_sound_chk)
        snd_hint = QLabel(
            "The add-on's sounds, like the bars flickering on. "
            "Move the slider to hear a sample; 0% turns them off. "
            "Untick Mini widget sounds to keep the deck list's widget silent "
            "while the Kotodama window still plays its sounds."
        )
        snd_hint.setWordWrap(True)
        snd_hint.setStyleSheet("color: gray; font-size: 11px;")
        sv.addWidget(snd_hint)
        dt.addWidget(snd_grp)

        # ── Animations: the neon flicker-on and the rain (owner 2026-10-22;
        # effects.py). Both on by default. ──
        anim_grp = QGroupBox("Animations")
        av = QVBoxLayout(anim_grp)
        anim_row = QHBoxLayout()
        self.flicker_chk = QCheckBox("Neon flicker")
        self.flicker_chk.setChecked(bool(self._cfg.get(effects.ANIM_KEY, True)))
        self.rain_chk = QCheckBox("Rain")
        self.rain_chk.setChecked(bool(self._cfg.get(effects.RAIN_KEY, True)))
        anim_row.addWidget(self.flicker_chk)
        anim_row.addSpacing(16)
        anim_row.addWidget(self.rain_chk)
        anim_row.addStretch()
        av.addLayout(anim_row)
        anim_hint = QLabel(
            "Neon flicker: the bars and grids flicker on when you first see them "
            "(off: lit at once). Rain: drops on the window's glass, with the odd spark."
        )
        anim_hint.setWordWrap(True)
        anim_hint.setStyleSheet("color: gray; font-size: 11px;")
        av.addWidget(anim_hint)
        dt.addWidget(anim_grp)

        # ── Night look: moon mode's effects, each its own switch (owner
        # 2026-10-25; effects.FX). All on by default; a change shows within
        # a second, no reopening. ──
        fx_grp = QGroupBox("Night look")
        fv = QVBoxLayout(fx_grp)
        fx_grid = QGridLayout()
        self.fx_chks = {}
        for i, (key, label) in enumerate(effects.FX.items()):
            chk = QCheckBox(label)
            chk.setChecked(bool(self._cfg.get(key, True)))
            self.fx_chks[key] = chk
            fx_grid.addWidget(chk, i // 4, i % 4)
        fv.addLayout(fx_grid)
        fx_hint = QLabel(
            "The window's night: the tubes' light spilling onto the wall and reflected below them, "
            "out-of-focus city lights, darker corners, and mist on the glass that running drops wipe clear."
        )
        fx_hint.setWordWrap(True)
        fx_hint.setStyleSheet("color: gray; font-size: 11px;")
        fv.addWidget(fx_hint)
        dt.addWidget(fx_grp)

        dt.addStretch()

        for m in self._cfg.get("field_mappings", []):
            self._add_row(m.get("note_type", ""), m.get("field", ""), m.get("reading_field", ""),
                          m.get("sentence_field", ""))
        if not self._rows:
            self._add_row()

        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        outer.addWidget(btn_box)

    def _add_kanji_grammar(self, v, deck_names):
        """The Kanji and Grammar source groups, added to layout v."""
        src = self._cfg.get("kanji_source") or {}
        grp = QGroupBox("Kanji — where do your kanji come from?")
        g = QVBoxLayout(grp)
        self.kanji_vocab_rb = QRadioButton(
            "From my vocab words (the deck and fields above)")
        self.kanji_sentence_rb = QRadioButton(
            "From my sentence fields (every kanji in the sentence fields above)")
        self.kanji_fields_rb = QRadioButton("From a field in another deck (e.g. a kanji deck)")
        g.addWidget(self.kanji_vocab_rb)
        g.addWidget(self.kanji_sentence_rb)
        g.addWidget(self.kanji_fields_rb)

        self._kanji_fields_box = QWidget()
        fb = QVBoxLayout(self._kanji_fields_box)
        fb.setContentsMargins(22, 0, 0, 0)
        deck_row = QHBoxLayout()
        deck_row.addWidget(QLabel("Deck:"))
        self.kanji_deck_combo = QComboBox()
        self.kanji_deck_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        for n in deck_names:
            self.kanji_deck_combo.addItem(n)
        if src.get("deck") in deck_names:
            self.kanji_deck_combo.setCurrentText(src["deck"])
        deck_row.addWidget(self.kanji_deck_combo)
        fb.addLayout(deck_row)
        self._kanji_rows = []
        self._kanji_rows_vbox = QVBoxLayout()
        self._kanji_rows_vbox.setSpacing(2)
        fb.addLayout(self._kanji_rows_vbox)
        add = QPushButton("＋ Add kanji field")
        add.clicked.connect(lambda: self._add_kanji_row())
        fb.addWidget(add)
        g.addWidget(self._kanji_fields_box)
        for m in src.get("mappings", []):
            self._add_kanji_row(m.get("note_type", ""), m.get("field", ""))
        if not self._kanji_rows:
            self._add_kanji_row()

        fields_mode = src.get("mode") == "fields"
        self.kanji_fields_rb.setChecked(fields_mode)
        self.kanji_sentence_rb.setChecked(src.get("mode") == "sentence")
        self.kanji_vocab_rb.setChecked(src.get("mode") not in ("fields", "sentence"))
        self._kanji_fields_box.setEnabled(fields_mode)
        self.kanji_fields_rb.toggled.connect(self._kanji_fields_box.setEnabled)

        hint = QLabel(
            "Every kanji in the chosen text counts. A kanji is <b>known</b> once a card you've "
            "studied contains it; its colour shows <b>how well</b> you know it: the average "
            "strength of those cards (FSRS stability, difficulty and lapses). Suspended cards "
            "don't count. Kanji don't affect your rank or the word counts.")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: gray; font-size: 11px;")
        g.addWidget(hint)
        v.addWidget(grp)

        from . import grammar_data
        gsrc = grammar_data.source_config(self._cfg)
        ggrp = QGroupBox("Grammar — where does your grammar come from?")
        gg = QVBoxLayout(ggrp)
        self.grammar_sentence_rb = QRadioButton(
            "Parse my sentence fields (auto parser: the sentence fields above)")
        self.grammar_fields_rb = QRadioButton("From a grammar deck's field")
        gg.addWidget(self.grammar_sentence_rb)
        gg.addWidget(self.grammar_fields_rb)
        self._grammar_fields_box = QWidget()
        gb = QVBoxLayout(self._grammar_fields_box)
        gb.setContentsMargins(22, 0, 0, 0)
        gdeck_row = QHBoxLayout()
        gdeck_row.addWidget(QLabel("Deck:"))
        self.grammar_deck_combo = QComboBox()
        self.grammar_deck_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        for n in deck_names:
            self.grammar_deck_combo.addItem(n)
        if gsrc.get("deck") in deck_names:
            self.grammar_deck_combo.setCurrentText(gsrc["deck"])
        gdeck_row.addWidget(self.grammar_deck_combo)
        gb.addLayout(gdeck_row)
        self._grammar_rows = []
        self._grammar_rows_vbox = QVBoxLayout()
        self._grammar_rows_vbox.setSpacing(2)
        gb.addLayout(self._grammar_rows_vbox)
        gadd = QPushButton("＋ Add grammar field")
        gadd.clicked.connect(lambda: self._add_grammar_row())
        gb.addWidget(gadd)
        gg.addWidget(self._grammar_fields_box)
        for m in gsrc.get("mappings", []):
            self._add_grammar_row(m.get("note_type", ""), m.get("field", ""))
        if not self._grammar_rows:
            self._add_grammar_row()
        g_fields = gsrc.get("mode") == "fields"
        self.grammar_fields_rb.setChecked(g_fields)
        self.grammar_sentence_rb.setChecked(not g_fields)
        self._grammar_fields_box.setEnabled(g_fields)
        self.grammar_fields_rb.toggled.connect(self._grammar_fields_box.setEnabled)
        ghint = QLabel(
            "The field should hold the grammar pattern, e.g. <b>〜がてら</b>, <b>がてら</b> or "
            "<b>〜がてら (while)</b>; it's matched to OpenJLPT's 526 grammar points. A few patterns "
            "share a form (で: place of action / means): add the English meaning to tell them "
            "apart, e.g. <b>で (means)</b>, or the card won't count.")
        ghint.setWordWrap(True)
        ghint.setStyleSheet("color: gray; font-size: 11px;")
        gg.addWidget(ghint)
        v.addWidget(ggrp)

    def _add_kanji_row(self, note_type="", field=""):
        row = SimpleFieldRow(self._note_types, note_type, field,
                             "Field with the kanji  e.g. kanji")
        row.removed.connect(self._remove_kanji_row)
        self._kanji_rows_vbox.addWidget(row)
        self._kanji_rows.append(row)

    def _remove_kanji_row(self, row):
        self._kanji_rows_vbox.removeWidget(row)
        self._kanji_rows.remove(row)
        row.deleteLater()

    def _add_grammar_row(self, note_type="", field=""):
        row = SimpleFieldRow(self._note_types, note_type, field,
                             "Field with the grammar pattern  e.g. Grammar")
        row.removed.connect(self._remove_grammar_row)
        self._grammar_rows_vbox.addWidget(row)
        self._grammar_rows.append(row)

    def _remove_grammar_row(self, row):
        self._grammar_rows_vbox.removeWidget(row)
        self._grammar_rows.remove(row)
        row.deleteLater()

    def _add_row(self, note_type="", field="", reading_field="", sentence_field=""):
        row = FieldMappingRow(self._note_types, note_type, field, reading_field,
                              sentence_field, self._rows_widget)
        row.removed.connect(self._remove_row)
        self._rows_vbox.addWidget(row)
        self._rows.append(row)

    def _remove_row(self, row):
        self._rows_vbox.removeWidget(row)
        self._rows.remove(row)
        row.deleteLater()

    def get_config(self) -> dict:
        mappings = [m for m in (r.get_mapping() for r in self._rows)
                    if m["field"] or m.get("sentence_field")]
        # Start from the existing config so keys this dialog doesn't edit
        # (e.g. rank_last_real_count) survive a save. "lists" is dropped:
        # the bundled lists are always used.
        cfg = {k: v for k, v in self._cfg.items() if k != "lists"}
        return {
            **cfg,
            "deck_name":           self.deck_combo.currentText(),
            "field_mappings":      mappings,
            "mini_widget_enabled": self.mini_widget_chk.isChecked(),
            "mini_widget_show_rank": self.mini_rank_chk.isChecked(),
            "mini_widget_show_rank_art": self.mini_art_chk.isChecked(),
            "review_seal": (self.seal_chk.isChecked() if self.seal_chk is not None
                            else self._cfg.get("review_seal", False)),
            "amaterasu_sound": (self.sound_chk.isChecked() if self.sound_chk is not None
                                else self._cfg.get("amaterasu_sound", True)),
            "ignore_suspended_cards": self.ignore_susp_chk.isChecked(),
            "effects_volume":     self.effects_slider.value(),
            "mini_widget_sound":  self.mini_sound_chk.isChecked(),
            "neon_flicker":       self.flicker_chk.isChecked(),
            "rain":               self.rain_chk.isChecked(),
            **{key: chk.isChecked() for key, chk in self.fx_chks.items()},
            "kanji_source": {
                "mode":     ("fields" if self.kanji_fields_rb.isChecked() else
                             "sentence" if self.kanji_sentence_rb.isChecked() else "vocab"),
                "deck":     self.kanji_deck_combo.currentText(),
                "mappings": [m for m in (r.get_mapping() for r in self._kanji_rows)
                             if m["field"]],
            },
            "grammar_source": {
                "mode":     "fields" if self.grammar_fields_rb.isChecked() else "sentence",
                "deck":     self.grammar_deck_combo.currentText(),
                "mappings": [m for m in (r.get_mapping() for r in self._grammar_rows)
                             if m["field"]],
            },
        }
