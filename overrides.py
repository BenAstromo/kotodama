"""
overrides.py
Persistent storage for user-managed word overrides.

Two sets are stored in <addon_dir>/user_files/overrides.json (Anki keeps
user_files/ when it updates an add-on; everything else in the add-on folder
is replaced). An overrides.json left in the add-on folder by older versions
is copied there once, plus a backup copy, and the original is left alone.
  "found"     : words the user marked as known via middle-click
                (treated identically to deck-matched words in the analysis)
  "suspended" : words the user wants excluded from all JLPT lists
                (removed from both known and missing counts)

Keys are "display\treading" strings so the file is human-readable.

Kanji marks use the same class with their own file (KANJI_PATH), so they
stay out of the words' Marked & Suspended tab.
"""

import json
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
USER_DIR = os.path.join(_HERE, "user_files")
_PATH = os.path.join(USER_DIR, "overrides.json")
_OLD_PATH = os.path.join(_HERE, "overrides.json")
_BACKUP_PATH = os.path.join(USER_DIR, "overrides_backup_before_move.json")
KANJI_PATH = os.path.join(USER_DIR, "kanji_overrides.json")
GRAMMAR_PATH = os.path.join(USER_DIR, "grammar_overrides.json")   # keyed by grammar id


def _migrate():
    """One-time move of the pre-user_files overrides.json."""
    try:
        os.makedirs(USER_DIR, exist_ok=True)
        if not os.path.exists(_PATH) and os.path.isfile(_OLD_PATH):
            import shutil
            shutil.copy2(_OLD_PATH, _BACKUP_PATH)
            shutil.copy2(_OLD_PATH, _PATH)
    except Exception:
        pass


_migrate()


def keep_unreadable(path: str):
    """A user file exists but can't be read (cut off by a crash mid-save,
    edited by hand …) and is about to be replaced: keep a copy beside it,
    <name>.unreadable-<its time>, once per broken version, so nothing is
    lost silently (maintenance pass 2026-10-26)."""
    try:
        st = os.stat(path)
        if st.st_size == 0:
            return
        import shutil
        import time
        stamp = time.strftime("%Y%m%d-%H%M%S", time.localtime(st.st_mtime))
        dest = f"{path}.unreadable-{stamp}"
        if not os.path.exists(dest):
            shutil.copy2(path, dest)
    except Exception:
        pass


def _load(path: str = _PATH) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        def _normalise(entries) -> set:
            """Accept both storage formats:
              - "word\treading"          (internal format written by _save)
              - ["word", "reading"]      (list format, e.g. externally generated)
            """
            out = set()
            for e in entries:
                if isinstance(e, str):
                    out.add(e)
                elif isinstance(e, (list, tuple)) and len(e) >= 2:
                    out.add(f"{e[0]}\t{e[1]}")
                elif isinstance(e, (list, tuple)) and len(e) == 1:
                    out.add(e[0])
            return out

        return {
            "found":     _normalise(data.get("found", [])),
            "suspended": _normalise(data.get("suspended", [])),
        }
    except FileNotFoundError:
        pass
    except Exception:
        keep_unreadable(path)
    return {"found": set(), "suspended": set()}


def _save(data: dict, path: str = _PATH):
    # Written to a temp file, then swapped in: a crash mid-save keeps the
    # old marks instead of a cut-off file (which would load as empty).
    tmp = path + ".tmp"
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "found":     sorted(data["found"]),
                    "suspended": sorted(data["suspended"]),
                },
                f,
                ensure_ascii=False,
                indent=2,
            )
        os.replace(tmp, path)
    except Exception:
        try:
            os.remove(tmp)
        except Exception:
            pass


def key(display: str, reading: str) -> str:
    return f"{display}\t{reading}"


def parse_key(k: str) -> tuple:
    parts = k.split("\t", 1)
    return (parts[0], parts[1]) if len(parts) == 2 else (parts[0], parts[0])


# ── public API ────────────────────────────────────────────────────────────────

class Overrides:
    """
    Thin wrapper around the two persistent sets.
    A single instance is shared across the session and reloaded on demand.
    """

    #: Expose path so the UI can show the user where to put overrides.json
    path: str = _PATH

    def __init__(self, path: str = _PATH):
        self.path = path
        d = _load(path)
        self.found:     set = d["found"]
        self.suspended: set = d["suspended"]

    def _save(self):
        _save({"found": self.found, "suspended": self.suspended}, self.path)

    def reload(self):
        """Re-read overrides.json from disk. Called on Refresh so that a file
        dropped into the addon folder is picked up without restarting Anki."""
        d = _load(self.path)
        self.found     = d["found"]
        self.suspended = d["suspended"]

    # ── queries ───────────────────────────────────────────────────────────────

    def is_found(self, display: str, reading: str) -> bool:
        return key(display, reading) in self.found

    def is_suspended(self, display: str, reading: str) -> bool:
        return key(display, reading) in self.suspended

    # ── mutations (each one saves immediately) ────────────────────────────────
    # Copy-on-write: each change puts a NEW set in place instead of changing
    # the old one, so an analysis reading the marks in the background (the
    # window's Refresh) keeps a stable set while you mark tiles meanwhile
    # ("Set changed size during iteration": maintenance pass 2026-10-26).

    def _set(self, found=None, suspended=None):
        if found is not None:
            self.found = found
        if suspended is not None:
            self.suspended = suspended
        self._save()

    def toggle_found(self, display: str, reading: str) -> bool:
        """Returns True if now marked-found, False if unmarked."""
        k = key(display, reading)
        now = k not in self.found
        self._set(found=(self.found | {k}) if now else (self.found - {k}),
                  suspended=self.suspended - {k})          # can't be both
        return now

    def toggle_suspended(self, display: str, reading: str) -> bool:
        """Returns True if now suspended, False if unsuspended."""
        k = key(display, reading)
        now = k not in self.suspended
        self._set(suspended=(self.suspended | {k}) if now else (self.suspended - {k}),
                  found=self.found - {k})                  # can't be both
        return now

    def remove_found(self, display: str, reading: str):
        self._set(found=self.found - {key(display, reading)})

    def remove_suspended(self, display: str, reading: str):
        self._set(suspended=self.suspended - {key(display, reading)})

    # Bulk variants save once instead of once per word.

    def add_found_many(self, pairs):
        keys = {key(d, r) for d, r in pairs}
        self._set(found=self.found | keys, suspended=self.suspended - keys)   # can't be both

    def remove_found_many(self, pairs):
        self._set(found=self.found - {key(d, r) for d, r in pairs})

    def add_suspended_many(self, pairs):
        keys = {key(d, r) for d, r in pairs}
        self._set(suspended=self.suspended | keys, found=self.found - keys)   # can't be both

    def remove_suspended_many(self, pairs):
        self._set(suspended=self.suspended - {key(d, r) for d, r in pairs})

    def clear_found(self):
        """Remove all 'marked as found' overrides."""
        self._set(found=set())

    def clear_suspended(self):
        """Remove all 'suspended' overrides."""
        self._set(suspended=set())

    # ── bulk access for analysis ──────────────────────────────────────────────

    def found_pairs(self) -> list:
        return [parse_key(k) for k in self.found]

    def suspended_pairs(self) -> list:
        return [parse_key(k) for k in self.suspended]


def apply_loanword_default(lists: dict, get_cfg, save_cfg, overrides=None) -> int:
    """English loanwords are marked found by default (owner 2026-10-21):
    once, on a fresh install (no word marked yet), every English loanword on
    the JLPT lists and the frequency list is marked, as the "Mark English
    Loanwords as Found" button does. A one-time flag (config
    loanwords_default_done): unmarking them later sticks, and installs that
    already have marks aren't touched. The rank counts them on its gradual
    schedule (card_state). Returns how many were marked."""
    from . import freq_data, jlpt_data
    try:
        cfg = get_cfg()
        if cfg.get("loanwords_default_done"):
            return 0
        cfg["loanwords_default_done"] = True
        save_cfg(cfg)
        ov = overrides or Overrides()
        if ov.found:
            return 0                     # not a fresh install: the user's own choice stands
        pairs, seen = [], set()
        for lvl in jlpt_data.LEVELS:
            for d, r in lists.get(lvl, ()):
                if jlpt_data.is_english_loanword(d, r):
                    seen.add((d, freq_data._kata_to_hira(r)))
                    pairs.append((d, r))
        for d, r, _pmw, _forms in freq_data.load():
            key = (d, freq_data._kata_to_hira(r))
            if key not in seen and freq_data.is_english_loanword(d, r):
                seen.add(key)
                pairs.append((d, r))
        if pairs:
            ov.add_found_many(pairs)
        return len(pairs)
    except Exception:
        import traceback
        traceback.print_exc()
        return 0
