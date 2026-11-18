"""
build_package.py — build the release .ankiaddon (to-do (4), 2026-10-17).

An .ankiaddon is a zip of the add-on folder's contents (no top folder, no
__pycache__). This script decides by an allow-list, so a new file is never
shipped by accident: anything it doesn't know is left out and reported.

    python -I -X utf8 tools/build_package.py              # build into %TEMP%/kotodama_dist/
    python -I -X utf8 tools/build_package.py --out DIR    # build into DIR (not inside the add-on)
    python -I -X utf8 tools/build_package.py --list       # dry run: list and check, write nothing

Shipped: the root .py / .txt / .json files (minus personal and dev ones),
README.md, and media/ (videos + star sounds). Left out: user_files/ (the
owner's history, overrides, parse cache, found count and the generated chime;
the code makes all of it at run time), meta.json (Anki's copy of the owner's
config), the root overrides.json / overrides1.json, any .ankiaddon,
APP_VISION.md, docs/ (its history archive), tools/, server/ (the Nakama Worker),
.claude/, __pycache__/.

It never deletes, moves or edits anything in the add-on folder: the release
items it can't settle (version, author, stale files …) are printed as
warnings. Exit code 0 = built (or listed) with no warnings; 1 = warnings.
"""
import argparse, ast, os, re, sys, tempfile, zipfile

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
ADDON = os.path.dirname(HERE)

ROOT_EXT = (".py", ".txt", ".json")
ROOT_EXTRA = {"README.md", "LICENSE"}          # LICENSE: AGPL-3.0-or-later (owner 2026-10-20)
MEDIA_EXT = (".webm", ".ogg", ".png", ".wav")
SKIP_FILES = {"meta.json", "overrides.json", "overrides1.json", "APP_VISION.md", "release_drafts.md"}
SKIP_DIRS = {"user_files", "tools", ".claude", "__pycache__", ".git", "server", "docs"}
# release items in to-do (4) that no file check can answer
MANUAL = [
    "rebuild freq_extra.txt from the BCCWJ LUW zip (ranks past #7,421 are 1–2 too high)",
    "rebuild the friend packages",
    "'unofficial lists, not affiliated with the Japan Foundation / JEES' line",
    "decide on the rank name 'gaijin'",
    "Grok credit in README / §12",
    "check AnkiWeb's upload size limit",
]


def collect():
    """[(path relative to the add-on, size)] to ship, and [(path, why)] left out."""
    ship, skipped = [], []
    for name in sorted(os.listdir(ADDON)):
        full = os.path.join(ADDON, name)
        if os.path.isdir(full):
            if name == "media":
                for f in sorted(os.listdir(full)):
                    p = os.path.join(full, f)
                    if os.path.isfile(p) and f.lower().endswith(MEDIA_EXT):
                        ship.append(("media/" + f, os.path.getsize(p)))
                    else:
                        skipped.append(("media/" + f, "UNKNOWN media file"))
            elif name in SKIP_DIRS:
                skipped.append((name + "/", "dev / personal folder"))
            else:
                skipped.append((name + "/", "UNKNOWN folder"))
        elif name in SKIP_FILES:
            skipped.append((name, "personal / dev file"))
        elif name.endswith(".ankiaddon"):
            skipped.append((name, "old package"))
        elif name.endswith(ROOT_EXT) or name in ROOT_EXTRA:
            ship.append((name, os.path.getsize(full)))
        else:
            skipped.append((name, "UNKNOWN file"))
    return ship, skipped


def checks(ship, skipped):
    """Warnings for release items still open."""
    warn = []
    names = {p for p, _ in ship}
    for p, why in skipped:
        if why.startswith("UNKNOWN"):
            warn.append(f"{p}: not on the allow-list, left out — add it to build_package.py if it's needed")
    for p in ("overrides.json", "overrides1.json", "jlpt_progress.ankiaddon"):
        if os.path.exists(os.path.join(ADDON, p)):
            warn.append(f"{p} is still in the add-on folder (left out of the package; delete it before release)")
    try:
        import json
        man = json.load(open(os.path.join(ADDON, "manifest.json"), encoding="utf-8"))
    except (OSError, ValueError) as e:
        warn.append(f"manifest.json unreadable: {e}")
        man = {}
    if not man.get("author"):
        warn.append("manifest.json: author is empty")
    if man.get("version") == "2.3.0":
        warn.append("manifest.json: version is still 2.3.0 (bump before release)")
    if not any(n.upper().startswith("LICENSE") for n in os.listdir(ADDON)):
        warn.append("no LICENSE file (to-do (0c))")
    # every file the code opens by name must be shipped
    for p in sorted(n for n in names if n.endswith(".py")):
        src = open(os.path.join(ADDON, p), encoding="utf-8").read()
        try:
            ast.parse(src, feature_version=(3, 9))
        except SyntaxError as e:
            warn.append(f"{p}: doesn't parse as Python 3.9 ({e})")
        for ref in set(re.findall(r'"([A-Za-z0-9_]+\.(?:txt|json|webm|ogg))"', src)):
            if ref in names or "media/" + ref in names or ref in SKIP_FILES or re.search(
                    r'"user_files"[^\n]*"' + re.escape(ref) + '"', src):
                continue
            if ref not in ("manifest.json", "config.json") and not os.path.exists(os.path.join(ADDON, "user_files", ref)):
                warn.append(f"{p} names {ref}, which isn't in the package")
    # personal paths / addresses in shipped text
    leak = re.compile(r"[A-Za-z]:\\\\?Users\\\\?[A-Za-z]|@gmail\.com|AppData")
    for p in sorted(names):
        if p.endswith((".py", ".txt", ".json", ".md")):
            text = open(os.path.join(ADDON, p), encoding="utf-8", errors="replace").read()
            m = leak.search(text)
            if m:
                line = text.count("\n", 0, m.start()) + 1
                warn.append(f"{p}:{line}: looks like a personal path or address ({m.group()!r}…)")
    return warn, man


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(tempfile.gettempdir(), "kotodama_dist"))
    ap.add_argument("--list", action="store_true", help="dry run: write nothing")
    a = ap.parse_args()
    out_dir = os.path.abspath(a.out)
    if os.path.commonpath([out_dir, ADDON]) == ADDON:
        sys.exit("--out must be outside the add-on folder (Anki would load the package's files)")

    ship, skipped = collect()
    warn, man = checks(ship, skipped)
    total = sum(s for _, s in ship)
    print(f"{man.get('name', '?')}  v{man.get('version', '?')}")
    print(f"\nShipped ({len(ship)} files, {total / 1e6:.2f} MB unpacked):")
    for p, s in ship:
        print(f"  {s:>10,}  {p}")
    print("\nLeft out:")
    for p, why in skipped:
        print(f"  {p}  ({why})")

    if not a.list:
        os.makedirs(out_dir, exist_ok=True)
        dest = os.path.join(out_dir, man.get("package", "jlpt_progress") + ".ankiaddon")
        with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
            for p, _ in ship:
                z.write(os.path.join(ADDON, p), p)
        with zipfile.ZipFile(dest) as z:
            bad = z.testzip()
            if bad:
                warn.append(f"zip check failed at {bad}")
        print(f"\nWrote {dest} ({os.path.getsize(dest) / 1e6:.2f} MB)")

    print(f"\nWarnings ({len(warn)}):" if warn else "\nWarnings: none")
    for w in warn:
        print("  !", w)
    print("\nStill to decide by hand (to-do (4)):")
    for m in MANUAL:
        print("  -", m)
    return 1 if warn else 0


if __name__ == "__main__":
    sys.exit(main())
