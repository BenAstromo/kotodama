"""
migrate.py
Moving to the AnkiWeb version (owner 2026-10-20). A shared .ankiaddon
installs into addons21/jlpt_progress (its manifest's "package"); AnkiWeb
installs into a folder named by the add-on's AnkiWeb number. Anki keeps an
add-on's user_files only within its own folder, so without this a user who
switches would start over: no found words, history, caches, Nakama login or
settings.

At startup, from any folder other than jlpt_progress, once: if a
jlpt_progress folder sits next to this one, copy its user_files here
(never overwriting a file that already exists) and its settings (only if
this copy has none of its own yet), disable the old copy (two copies would
mean two menus and widgets) and say so after the profile opens. A marker
file in user_files makes it run once. The loyalty badge and the Nakama
login also live in the collection, so they come back even without this.
"""

from __future__ import annotations

import json
import os
import shutil

OLD_PACKAGE = "jlpt_progress"
MARKER = ".imported_from_jlpt_progress"


def import_old_copy(addon_dir: str, manager=None) -> dict | None:
    """Do the move if it applies. Returns what was done ({"files": n,
    "config": bool, "disabled": bool}) or None. manager: Anki's
    AddonManager (getConfig / writeConfig / toggleEnabled); None = files only."""
    here = os.path.basename(os.path.normpath(addon_dir))
    if here == OLD_PACKAGE:
        return None
    old_dir = os.path.join(os.path.dirname(os.path.normpath(addon_dir)), OLD_PACKAGE)
    new_user = os.path.join(addon_dir, "user_files")
    if os.path.exists(os.path.join(new_user, MARKER)) or not os.path.isdir(old_dir):
        return None
    old_user = os.path.join(old_dir, "user_files")
    copied = 0
    if os.path.isdir(old_user):
        for root, _dirs, files in os.walk(old_user):
            rel = os.path.relpath(root, old_user)
            dest_root = os.path.normpath(os.path.join(new_user, rel))
            for f in files:
                if f == MARKER:
                    continue
                dest = os.path.join(dest_root, f)
                if os.path.exists(dest):
                    continue                    # never overwrite what this copy already has
                os.makedirs(dest_root, exist_ok=True)
                shutil.copy2(os.path.join(root, f), dest)
                copied += 1
    config = False
    disabled = False
    if manager is not None:
        try:
            old_cfg = _meta_config(old_dir)
            if old_cfg and not _meta_config(addon_dir):
                cur = manager.getConfig(here) or {}
                cur.update(old_cfg)
                manager.writeConfig(here, cur)
                config = True
        except Exception:
            pass
        try:
            manager.toggleEnabled(OLD_PACKAGE, enable=False)
            disabled = True
        except Exception:
            pass
    os.makedirs(new_user, exist_ok=True)
    with open(os.path.join(new_user, MARKER), "w", encoding="utf-8") as f:
        json.dump({"from": old_dir, "files": copied, "config": config}, f)
    return {"files": copied, "config": config, "disabled": disabled}


def _meta_config(addon_dir: str) -> dict:
    """The user's settings Anki saved for an add-on (meta.json "config")."""
    try:
        with open(os.path.join(addon_dir, "meta.json"), encoding="utf-8") as f:
            cfg = json.load(f).get("config")
        return cfg if isinstance(cfg, dict) else {}
    except Exception:
        return {}
