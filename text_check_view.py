"""
text_check_view.py
The Text Check tab (owner 2026-10-14): paste Japanese text or open a .txt /
subtitle file, see how much of it your known words cover, and list the
unknown words in it (click to copy, Shift+click for Jisho). Logic lives in
text_check.py. A Vocab / Kanji / Grammar switch (owner 2026-10-20) lists
the text's kanji and grammar points the same way.
"""

from __future__ import annotations

from aqt.qt import *

from . import freq_data
from .theme import HINT_CSS
from . import text_check
from .progress_dialog import (
    FREQ_FG, LEVEL_FG, _fill_table, _copy_or_jisho, _copy_to_clipboard,
    _meaning_tip, _shown_reading, _kanji_form, _regold,
)

KNOWN_FG = "#7bc67b"
_LEVEL_ORDER = {"N5": 0, "N4": 1, "N3": 2, "N2": 3, "N1": 4}


class TextCheckTab(QWidget):
    def __init__(self, get_results, parent=None):
        """get_results: returns the dialog's current analysis results (they
        change on Refresh)."""
        super().__init__(parent)
        self._get_results = get_results
        self._result = None
        self._kanji = None
        self._grammar = None
        self._rows = []
        self._build()

    def _build(self):
        v = QVBoxLayout(self)
        intro = QLabel("Paste Japanese text (an article, a chapter, a subtitle file) to see how "
                       "much of it you already know, and which new words in it are worth learning.")
        intro.setWordWrap(True)
        intro.setStyleSheet("color: #aaa;")
        v.addWidget(intro)

        self._edit = QPlainTextEdit()
        self._edit.setPlaceholderText("Paste Japanese text here…")
        self._edit.setMaximumHeight(130)
        v.addWidget(self._edit)

        row = QHBoxLayout()
        open_btn = QPushButton("Open file…")
        open_btn.clicked.connect(self._open_file)
        row.addWidget(open_btn)
        row.addStretch()
        check_btn = QPushButton("Check text")
        check_btn.setDefault(True)
        check_btn.clicked.connect(self._check)
        row.addWidget(check_btn)
        v.addLayout(row)

        self._headline = QLabel("")
        self._headline.setStyleSheet("font-size: 17px; padding-top: 6px;")
        self._verdict = QLabel("")
        self._verdict.setWordWrap(True)
        self._detail = QLabel("")
        self._detail.setStyleSheet("color: #aaa;")
        self._detail.setWordWrap(True)
        # Kanji and grammar in the text (owner 2026-10-20)
        self._kg = QLabel("")
        self._kg.setStyleSheet("color: #aaa;")
        self._kg.setWordWrap(True)
        for w in (self._headline, self._verdict, self._detail, self._kg):
            v.addWidget(w)

        ctrl = QHBoxLayout()
        ctrl.addWidget(QLabel("Show:"))
        self._kind = QComboBox()
        self._kind.addItem("Vocab", "vocab")
        self._kind.addItem("Kanji", "kanji")
        self._kind.addItem("Grammar", "grammar")
        ctrl.addWidget(self._kind)
        self._show = QComboBox()
        self._show.addItem("Unknown words", "unknown")
        self._show.addItem("All words", "all")
        ctrl.addWidget(self._show)
        ctrl.addSpacing(16)
        ctrl.addWidget(QLabel("Sort:"))
        self._sort = QComboBox()
        self._sort.addItem("Most frequent in this text", "text")
        self._sort.addItem("Most common in Japanese", "freq")
        ctrl.addWidget(self._sort)
        ctrl.addStretch()
        for combo in (self._kind, self._show, self._sort):      # widths follow the kind's texts
            combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self._copy_btn = QPushButton("Copy unknown words")
        self._copy_btn.clicked.connect(self._copy_unknown)
        ctrl.addWidget(self._copy_btn)
        v.addLayout(ctrl)

        self._table = QTableWidget()
        self._table.setColumnCount(5)
        self._table.setHorizontalHeaderLabels(["In text", "Rank", "Level", "Word", "Reading"])
        from .progress_dialog import set_empty_hint
        set_empty_hint(self._table, "Paste Japanese text above (or open a file) and press Check text: "
                       "the words you don't know yet, most useful first, appear here.")
        hh = self._table.horizontalHeader()
        for c in (0, 1, 2):
            hh.setSectionResizeMode(c, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        hh.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self._table.horizontalHeaderItem(0).setToolTip("How many times the word appears in the text")
        self._table.horizontalHeaderItem(1).setToolTip(
            "Frequency rank in written Japanese (BCCWJ) — lower is more common. "
            "— means not in the top 20,000.")
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.verticalHeader().setVisible(False)
        self._table.setAlternatingRowColors(True)
        self._table.itemClicked.connect(self._on_click)
        v.addWidget(self._table, 1)

        self._unrec = QLabel("")
        self._unrec.setWordWrap(True)
        self._unrec.setStyleSheet("color: #aaa;")
        v.addWidget(self._unrec)

        self._hint = QLabel("Click a row to copy the word · Shift+Click to open it on Jisho.org.")
        self._hint.setWordWrap(True)
        self._hint.setStyleSheet(HINT_CSS)
        v.addWidget(self._hint)

        self._show.currentIndexChanged.connect(self._fill)
        self._sort.currentIndexChanged.connect(self._fill)
        self._kind.currentIndexChanged.connect(self._on_kind)

    # ── input ────────────────────────────────────────────────────────────────

    def _open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open text or subtitles", "",
            "Text and subtitles (*.txt *.srt *.vtt *.ass *.ssa);;All files (*)")
        if not path:
            return
        try:
            with open(path, "rb") as f:
                raw = text_check.decode_text(f.read())
        except OSError:
            raw = None
        if raw is None:
            from aqt.utils import showWarning
            showWarning("Couldn't read that file as text.", parent=self)
            return
        self._edit.setPlainText(text_check.text_from_file(raw, path))
        self._check()

    def _check(self):
        text = self._edit.toPlainText()
        if not text.strip():
            self._headline.setText("Paste some Japanese text first.")
            _regold(self._headline)
            return
        from .busy import busy
        with busy(self, "Checking the text…"):
            results = self._get_results()
            know = text_check.Knowledge(results)
            self._result = text_check.check_text(text, know)
            self._kanji = text_check.check_kanji(text, results, self._result["words"])
            self._grammar = text_check.check_grammar(text, results)
            self._show_result()

    # ── output ───────────────────────────────────────────────────────────────

    def _show_result(self):
        r = self._result
        if not r["total"]:
            self._headline.setText("No Japanese words found in this text.")
            for w in (self._verdict, self._detail, self._unrec, self._kg):
                w.setText("")
            self._fill()
            _regold(self._headline, self._verdict, self._detail, self._unrec)
            return
        pct = r["coverage"] * 100
        self._headline.setText(f"<b>{pct:.1f}%</b> of the words in this text are known")
        self._verdict.setText(text_check.verdict(r["coverage"]))
        self._detail.setText(
            f"{r['total']:,} words: {r['known']:,} known · {r['unknown']:,} unknown · "
            f"{r['unrecognised']:,} not on our lists (names, rare words) · "
            f"different words: {r['unique_known']:,} of {r['unique_total']:,} known")
        if r["unrec"]:
            shown = ", ".join(f"{s} ×{n}" if n > 1 else s for s, n in r["unrec"][:30])
            more = f" (+{len(r['unrec']) - 30:,} more)" if len(r["unrec"]) > 30 else ""
            self._unrec.setText("<b>Not on our lists</b> (names, rare words, or text the "
                                "parser can't read): " + shown + more)
        else:
            self._unrec.setText("")
        self._kg.setText(self._kg_line())
        self._fill()
        _regold(self._headline, self._verdict, self._detail, self._unrec, self._kg)

    def _kg_line(self) -> str:
        """"Kanji: 92% known (8 of 104 not known yet) · Grammar: 14 points,
        3 not learned yet"."""
        parts = []
        k = self._kanji
        if k and k["unique"]:
            if k["tracked"]:
                pct = round(k["known"] / k["unique"] * 100)
                parts.append(f"Kanji: <b>{pct}%</b> known ({k['unique'] - k['known']:,} of "
                             f"{k['unique']:,} not known yet)")
            else:
                parts.append(f"Kanji: {k['unique']:,} different")
        g = self._grammar
        if g and g["rows"]:
            n = len(g["rows"])
            if g["tracked"]:
                parts.append(f"Grammar: {n:,} points, <b>{n - g['known']:,}</b> not learned yet")
            else:
                parts.append(f"Grammar: {n:,} points found")
        return " &nbsp;·&nbsp; ".join(parts)

    # ── kind switch: vocab / kanji / grammar ─────────────────────────────────

    _KIND_TEXT = {
        "vocab": (("Unknown words", "All words"), "Most common in Japanese", "Copy unknown words",
                  ["In text", "Rank", "Level", "Word", "Reading"],
                  "Click a row to copy the word · Shift+Click to open it on Jisho.org."),
        "kanji": (("Unknown kanji", "All kanji"), "By JLPT level", "Copy unknown kanji",
                  ["In text", "Level", "Kanji", "Meaning", "Words in this text"],
                  "Click a row to copy the kanji · Shift+Click to open it on Jisho.org."),
        "grammar": (("Grammar not learned yet", "All grammar points"), "By JLPT level",
                    "Copy grammar not learned yet",
                    ["In text", "Level", "Pattern", "Meaning", "In this text"],
                    "Click a row to copy the pattern · Hover a row for the sentences it's in. "
                    "Basic particles (は, が, を…) aren't listed. Grammar detection can miss "
                    "some points (about 1 in 10)."),
    }

    def _on_kind(self, *_):
        kind = self._kind.currentData()
        (unk, allx), sort2, copy, headers, hint = self._KIND_TEXT[kind]
        from .progress_dialog import _GOLD_MODE
        gold = _GOLD_MODE["on"]
        if gold:
            # the gold pass remembers each header's / item's English: undo it
            # first, so the new English texts are translated afresh
            from . import divine_text
            divine_text.apply(self, False)
        for combo in (self._show, self._sort):
            combo.blockSignals(True)
        self._show.setItemText(0, unk)
        self._show.setItemText(1, allx)
        self._sort.setItemText(1, sort2)
        for combo in (self._show, self._sort):
            combo.blockSignals(False)
        self._copy_btn.setText(copy)
        self._table.setHorizontalHeaderLabels(headers)
        self._hint.setText(hint)
        hh = self._table.horizontalHeader()
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents if kind == "vocab"
                                else QHeaderView.ResizeMode.Stretch)
        self._fill()
        if gold:
            divine_text.apply(self, True)

    def _fill(self):
        kind = self._kind.currentData()
        if kind == "kanji":
            return self._fill_kanji()
        if kind == "grammar":
            return self._fill_grammar()
        r = self._result
        rows = list(r["words"]) if r else []
        if self._show.currentData() == "unknown":
            rows = [w for w in rows if not w["known"]]
        if self._sort.currentData() == "text":
            rows.sort(key=lambda w: (-w["count"], w["rank"] or 10 ** 9))
        else:
            rows.sort(key=lambda w: (w["rank"] is None, w["rank"] or 0, -w["count"]))
        self._rows = rows
        _fill_table(self._table, [
            (
                (f"{w['count']:,}", None),
                (freq_data.rank_text(w["rank"], False) if w["rank"] else "—",
                 FREQ_FG if w["rank"] else "#777777"),
                (w["level"] or "—", LEVEL_FG.get(w["level"], "#777777")),
                (w["display"], KNOWN_FG if w["known"] else None),
                (_shown_reading(w["display"], w["reading"])
                 or (f"〔{k}〕" if (k := _kanji_form(w["display"], w["reading"])) else ""), None),
            )
            for w in rows
        ], tooltips=[_meaning_tip(w["display"], w["reading"]) for w in rows])

    def _fill_kanji(self):
        from .kanji_data import data as kanji_info
        k = self._kanji
        rows = list(k["rows"]) if k else []
        if self._show.currentData() == "unknown":
            rows = [x for x in rows if x["known"] is False]
        if self._sort.currentData() == "text":
            rows.sort(key=lambda x: -x["count"])
        else:
            rows.sort(key=lambda x: (_LEVEL_ORDER.get(x["level"], 9), -x["count"]))
        self._rows = rows
        tips = []
        for x in rows:
            info = kanji_info().get(x["char"]) or {}
            tip = f"<b style='font-size:20px;'>{x['char']}</b>  {', '.join(info.get('meanings', [])[:6])}"
            if info.get("on") or info.get("kun"):
                tip += f"<br>{'、'.join(info.get('on', []))}  ·  {'、'.join(info.get('kun', []))}"
            tips.append(tip)
        _fill_table(self._table, [
            (
                (f"{x['count']:,}", None),
                (x["level"] or "—", LEVEL_FG.get(x["level"], "#777777")),
                (x["char"], KNOWN_FG if x["known"] else None),
                (", ".join(x["meanings"][:3]), None),
                ("、".join(x["words"][:6]), None),
            )
            for x in rows
        ], tooltips=tips)

    def _fill_grammar(self):
        import html
        from . import grammar_data
        g = self._grammar
        rows = list(g["rows"]) if g else []
        if self._show.currentData() == "unknown":
            rows = [x for x in rows if x["known"] is False or (x["known"] is None)]
        if self._sort.currentData() == "text":
            rows.sort(key=lambda x: (-x["count"], _LEVEL_ORDER.get(x["level"], 9)))
        else:
            rows.sort(key=lambda x: (_LEVEL_ORDER.get(x["level"], 9), -x["count"]))
        self._rows = rows
        data = grammar_data.data()

        def marked(sentence, spans):
            out, last = [], 0
            for a, b in sorted(spans):
                if a < last:
                    continue
                out.append(html.escape(sentence[last:a]) + "<b style='color:#ffe066;'>"
                           + html.escape(sentence[a:b]) + "</b>")
                last = b
            return "".join(out) + html.escape(sentence[last:])

        tips = []
        for x in rows:
            p = data[x["gid"]]
            tip = f"<b>{html.escape(p['pattern'])}</b> ({p['level']}): {html.escape(p.get('meaning', ''))}"
            if p.get("formation"):
                tip += f"<br><span style='color:#aaa;'>{html.escape(p['formation'])}</span>"
            tip += "<br><br>" + "<br>".join(marked(s_, sp) for s_, sp in x["examples"])
            tips.append(tip)
        _fill_table(self._table, [
            (
                (f"{x['count']:,}", None),
                (x["level"] or "—", LEVEL_FG.get(x["level"], "#777777")),
                (data[x["gid"]]["pattern"], KNOWN_FG if x["known"] else None),
                (data[x["gid"]].get("meaning", ""), None),
                (x["examples"][0][0] if x["examples"] else "", None),
            )
            for x in rows
        ], tooltips=tips)

    def _on_click(self, item):
        if not 0 <= item.row() < len(self._rows):
            return
        kind = self._kind.currentData()
        x = self._rows[item.row()]
        if kind == "kanji":
            _copy_or_jisho(x["char"], self.window(), "")
        elif kind == "grammar":
            from . import grammar_data
            _copy_or_jisho(grammar_data.data()[x["gid"]]["pattern"].lstrip("〜～"), self.window(), "")
        else:
            _copy_or_jisho(x["display"], self.window(), x["reading"])

    def _copy_unknown(self):
        kind = self._kind.currentData()
        from aqt.utils import tooltip
        if kind in ("kanji", "grammar"):
            res = self._kanji if kind == "kanji" else self._grammar
            if not res:
                return
            rows = [x for x in res["rows"] if not x["known"]]
            rows.sort(key=lambda x: -x["count"])
            if kind == "kanji":
                text = "".join(x["char"] for x in rows)
            else:
                from . import grammar_data
                d = grammar_data.data()
                text = "\n".join(f"{d[x['gid']]['pattern']}\t{d[x['gid']].get('meaning', '')}" for x in rows)
            _copy_to_clipboard(text)
            tooltip(f"Copied {len(rows):,}", parent=self.window())
            return
        r = self._result
        if not r:
            return
        words = sorted((w for w in r["words"] if not w["known"]),
                       key=lambda w: (-w["count"], w["rank"] or 10 ** 9))
        _copy_to_clipboard("\n".join(f"{w['display']}\t{w['reading']}" for w in words))
        from aqt.utils import tooltip
        tooltip(f"Copied {len(words):,} words", parent=self.window())
