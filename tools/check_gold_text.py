"""
check_gold_text.py — the English ↔ Amaterasu-mode text protocol.

Every English UI text has to have a gold-mode Japanese version in
divine_text.py (owner 2026-10-09). This script finds the user-visible English
strings in the UI source and reports any that divine_text can't translate,
so a new or changed English text can't silently stay English in gold mode.

Run after any UI text change (from anywhere):
    python -I -X utf8 tools/check_gold_text.py
Exit code 0 = everything covered; 1 = untranslated strings listed.

What counts as UI text: the first string argument of QLabel / QPushButton /
QCheckBox / QRadioButton / QGroupBox(...), .setText / .setPlaceholderText /
.addItem / .setTabText(…, text) / .addTab(…, text) / setWindowTitle, and the
labels in setHorizontalHeaderLabels([...]). Tooltips (setToolTip) and the
Settings dialog (config_dialog.py) stay English by design and aren't checked.

f-strings: each {…} is replaced by a sample value (a number, or N5 for level
placeholders) before translating, the way it would look at run time.

A string that legitimately stays English (debug-only UI, symbols, names)
goes in STAYS_ENGLISH below, with a reason.
"""

import ast
import os
import re
import sys
import types
import importlib.util

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UI_FILES = ["progress_dialog.py", "kanji_view.py", "history_view.py", "share_card.py", "nakama_view.py",
            "text_check_view.py", "goal_view.py", "busy.py", "__init__.py"]

CALLS = {"QLabel", "QPushButton", "QCheckBox", "QRadioButton", "QGroupBox"}
# "please wait" notes (busy.py): the text is the second argument
WAIT_CALLS = {"busy", "show_note", "_LazyTab"}
METHODS = {"setText": 0, "setPlaceholderText": 0, "addItem": 0, "setWindowTitle": 0,
           "setTabText": 1, "addTab": 1}

# Stays English in gold mode, on purpose (exact text as the checker sees it).
STAYS_ENGLISH = {
    # debug row (the owner removes it before release)
    "◀ -250", "+250 ▶", "★ Mark All JLPT Found", "Count all notes", "Debug preview:",
    "Test belt-up toast", "Test rank-up toast", "☀ Force Amaterasu", "Loyalty ▶",
    "Reset", "1,234 · 1,234 belt (1,234)",      # Nakama tab debug row
    "DEBUG: the rank is counting every note in the deck, learned or not "
    "(Count all notes is on). Progress history still uses the real count.",
    # symbols / icons
    "?", "🔍", "★", "✕", "",
    # the Amaterasu message is shown in Japanese only
    "天照大神",
    # set directly in code for gold mode (ProgressDialog._apply_gold_now /
    # the rank info window), not through divine_text
    "Kotodama 言霊 — Deck",
    "About the Kotodama 言霊 Japanese Rank",   # window title (label is in EXACT)
    "About the Frequency Check",              # window title, set to 頻度チェックについて in code
    "English loanwords",                      # window title, set to 英語の外来語 in code
    # f"{belt.upper()} BELT": in gold mode it can only be TENTH-DEGREE BLACK
    # BELT, which is in EXACT
    "1,234 BELT",
}

LEVEL_NAMES = {"lvl", "level", "key", "l"}
# Realistic values for placeholders whose shape matters to the patterns.
SAMPLES = {"kind": "automatic", "when": "Oct 9, 19:05", "deck_name": "Deck",
           "_deck_name": "Deck", "coverage": "85.0", "noun": "grammar points",
           "target": "20,000", "name": "N5", "color": "#7ec8f0", "c": "#7ec8f0",
           "range_txt": "13,800 – 20,000 cards"}


def _sample(node) -> str:
    """Run-time-like text for an f-string placeholder."""
    expr = node.value
    name = expr.id if isinstance(expr, ast.Name) else getattr(expr, "attr", "")
    if name in SAMPLES:
        return SAMPLES[name]
    if name in LEVEL_NAMES:
        return "N5"
    return "1,234"


def _text(node):
    """The string a node evaluates to (approximately), or None."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        out = []
        for v in node.values:
            if isinstance(v, ast.Constant):
                out.append(str(v.value))
            elif isinstance(v, ast.FormattedValue):
                out.append(_sample(v))
        return "".join(out)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        a, b = _text(node.left), _text(node.right)
        if a is not None and b is not None:
            al = a if isinstance(a, list) else [a]
            bl = b if isinstance(b, list) else [b]
            out = [x + y for x in al for y in bl]
            return out if len(out) > 1 else out[0]
    if isinstance(node, ast.IfExp):          # "A" if x else "B" → check both
        out = []
        for t in (_text(node.body), _text(node.orelse)):   # nested ifs give lists: flatten
            out.extend(t if isinstance(t, list) else [t] if t is not None else [])
        return out or None
    return None


def ui_strings(path):
    tree = ast.parse(open(path, encoding="utf-8").read())
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        f = node.func
        arg = None
        if isinstance(f, ast.Name) and f.id in CALLS and node.args:
            arg = node.args[0]
        elif isinstance(f, ast.Name) and f.id in WAIT_CALLS and len(node.args) > 1:
            arg = node.args[1]                  # busy(widget, "Building…") etc.
        elif isinstance(f, ast.Attribute) and f.attr in METHODS:
            i = METHODS[f.attr]
            if len(node.args) > i:
                arg = node.args[i]
        elif isinstance(f, ast.Attribute) and f.attr == "setHorizontalHeaderLabels" and node.args:
            if isinstance(node.args[0], ast.List):
                for el in node.args[0].elts:
                    t = _text(el)
                    if t:
                        yield node.lineno, t, "header"
            continue
        if arg is None:
            continue
        t = _text(arg)
        for s in (t if isinstance(t, list) else [t]):
            if s is not None:
                yield node.lineno, s, "text"


def load_divine():
    qt = types.ModuleType("aqt.qt")
    for n in ("QWidget", "QLabel", "QAbstractButton", "QComboBox", "QLineEdit",
              "QPlainTextEdit", "QTextEdit", "QTabWidget", "QTableWidget", "QColor"):
        setattr(qt, n, type(n, (), {}))
    qt.Qt = types.SimpleNamespace(ItemDataRole=types.SimpleNamespace(UserRole=256),
                                  BrushStyle=types.SimpleNamespace(NoBrush=0))
    sys.modules.update({"aqt": types.ModuleType("aqt"), "aqt.qt": qt})
    spec = importlib.util.spec_from_file_location("divine_text", os.path.join(HERE, "divine_text.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


NAMES_OK = {"JLPT", "Jisho", "Anki", "Shift", "Ctrl", "BCCWJ", "NINJAL", "OpenJLPT", "FSRS", "PNG",
            "Kaishi", "Lapis", "Word", "Expression", "json", "overrides", "org", "Deck"}


def leftover(dt, s: str, kind: str):
    """English words still left in gold mode ([] = covered)."""
    plain = re.sub(r"<[^>]+>|&nbsp;", " ", s)
    if not re.search(r"[A-Za-z]{2,}", plain):
        return []                    # no English words (numbers, symbols, Japanese)
    if " ".join(s.split()) in STAYS_ENGLISH or s in STAYS_ENGLISH:
        return []
    if kind == "header":
        return [] if s in dt.HEADERS else [s]
    if s in dt.PLACEHOLDERS:
        return []
    ja = dt.translate(s)
    left = re.sub(r"<[^>]+>|&nbsp;", " ", ja)
    # no English words left over (names like Jisho / JLPT are fine)
    rest = [w for w in re.findall(r"[A-Za-z]{3,}", left) if w not in NAMES_OK]
    return rest if (rest or ja == s) else []


def main():
    dt = load_divine()
    missing = []
    for name in UI_FILES:
        for line, s, kind in ui_strings(os.path.join(HERE, name)):
            rest = leftover(dt, s, kind)
            if rest:
                missing.append((name, line, s, rest))
    if not missing:
        print("OK: every UI text has a gold-mode (Japanese) version.")
        return 0
    print(f"{len(missing)} UI text(s) without a gold-mode version "
          "(add to divine_text.py, or to STAYS_ENGLISH with a reason):")
    for name, line, s, rest in missing:
        print(f"  {name}:{line}: {s[:100]!r}\n      still English: {' '.join(rest[:12])}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
