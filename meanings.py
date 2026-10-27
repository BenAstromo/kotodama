"""
meanings.py
English meanings for the hover text, from meanings.json (built from
Jitendex by tools/build_meanings.py; JLPT and top-20,000 frequency words
only). Shows the part of speech and the first 7 meanings, "(+N more)" after.

lookup() takes a list word (display, reading) exactly; a deck card's
display + reading field also works when it matches a list word (several
readings like "なに・なん" are tried one by one). Cards that aren't list
words get no meaning (owner's decision).
"""

from __future__ import annotations

import html
import json
import os
import re

_HERE = os.path.dirname(os.path.abspath(__file__))
_PATH = os.path.join(_HERE, "meanings.json")

_data = None           # {"k": {"display\treading": seq}, "m": {seq: [total, senses]}}
_by_display = None     # display → {seq} for cards without a reading


def _load():
    global _data, _by_display
    if _data is None:
        try:
            with open(_PATH, encoding="utf-8") as f:
                _data = json.load(f)
        except Exception:
            _data = {"k": {}, "m": {}}
        _by_display = {}
        for key, seq in _data["k"].items():
            _by_display.setdefault(key.split("\t", 1)[0], set()).add(seq)
    return _data


_K2H = {c: c - 0x60 for c in range(0x30A1, 0x30F7)}     # ァ…ヶ → ぁ…ゖ (str.translate: fast)


def _kata_to_hira(s: str) -> str:
    return s.translate(_K2H)


def _hira_to_kata(s: str) -> str:
    return "".join(chr(ord(c) + 0x60) if "ぁ" <= c <= "ゖ" else c for c in s)


def lookup(display: str, reading: str = "") -> list | None:
    """[total_senses, [[pos, gloss], …]] or None."""
    data = _load()
    keys, m = data["k"], data["m"]
    display = (display or "").strip()
    reading = (reading or "").strip()
    parts = [p for p in re.split(r"[・/／、,，;；\s]+", reading) if p] or [display]
    from .freq_splits import GLOSSES
    for r in parts:
        for rr in (r, _kata_to_hira(r), _hira_to_kata(r)):
            # Split frequency tiles (聴く apart from 聞く) have their own
            # meaning; JMdict's entry is shared or missing (freq_splits).
            g = GLOSSES.get((display, rr))
            if g:
                return [len(g) - 1, [[g[0] if i == 0 else "", s] for i, s in enumerate(g[1:])]]
            seq = keys.get(f"{display}\t{rr}")
            if seq is not None:
                return m.get(str(seq))
    if not reading:
        seqs = _by_display.get(display, set())
        if len(seqs) == 1:
            return m.get(str(next(iter(seqs))))
    return None


def tooltip_html(display: str, reading: str = "") -> str:
    """The meaning as tooltip HTML (part of speech in grey, numbered
    meanings, "(+N more)"), or "" if there's none."""
    hit = lookup(display, reading)
    if not hit:
        return ""
    total, senses = hit
    rows = []
    for i, (pos, gloss) in enumerate(senses, start=1):
        if pos:
            rows.append(f"<span style='color:#9a9a9a; font-style:italic;'>{html.escape(pos)}</span>")
        num = f"{i}. " if total > 1 else ""
        rows.append(f"{num}{html.escape(gloss)}")
    if total > len(senses):
        rows.append(f"<span style='color:#9a9a9a;'>(+{total - len(senses)} more)</span>")
    return "<br>".join(rows)
