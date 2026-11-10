"""The owner's corrections to the JLPT lists (2026-11-10), applied by
build_jlpt.py after OpenJLPT + JMdict, so a rebuild keeps them.

    python -I -X utf8 tools/jlpt_owner_fixes.py <addon_dir>

applies them to the current jlpt_n*.txt files in place (the same step a
rebuild runs; for when OpenJLPT / JMdict aren't downloaded). Idempotent.

Rows are (word, reading, alts, flags, alt_reads), as build_jlpt.py makes them.
"""
import os, sys

# (level, word, reading): left out of the list.
REMOVE = {
    ("N5", "せっけん", "せっけん"),        # thrift (節倹), not soap; soap is N2 石鹸
}

# (level, word, reading) → (word, reading): listed under another form of the
# same JMdict entry. The old form stays as an alternate spelling (if it has
# kanji) or reading, so cards written the old way still count.
RENAME = {
    ("N5", "ゆっくりと", "ゆっくりと"): ("ゆっくり", "ゆっくり"),
    ("N4", "びっくりする", "びっくりする"): ("びっくり", "びっくり"),
    ("N4", "舟", "ふね"): ("船", "ふね"),
}


def _has_kanji(s: str) -> bool:
    return any("一" <= c <= "鿿" or "㐀" <= c <= "䶿" or c == "々" for c in s)


def apply(level: str, rows: list) -> list:
    out = []
    for w, r, alts, flags, alt_reads in rows:
        if (level, w, r) in REMOVE:
            continue
        new = RENAME.get((level, w, r))
        if new:
            nw, nr = new
            alts = ([w] if w != nw and _has_kanji(w) else []) + [a for a in alts if a not in (nw, w)]
            alt_reads = ([r] if r != nr else []) + [a for a in alt_reads if a not in (nr, r)]
            w, r = nw, nr
        out.append((w, r, list(alts), list(flags), list(alt_reads)))
    return out


def _read(path):
    head, rows = [], []
    for line in open(path, encoding="utf-8"):
        line = line.rstrip("\n")
        if line.startswith("#") or not line.strip():
            head.append(line)
            continue
        c = line.split("\t") + [""] * 5
        rows.append((c[0], c[1], [a for a in c[2].split("|") if a],
                     [f for f in c[3].split(",") if f], [a for a in c[4].split("|") if a]))
    return head, rows


def _write(path, level, head, rows):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        for line in head:
            if line.startswith(f"# JLPT {level} vocabulary list"):
                line = f"# JLPT {level} vocabulary list — {len(rows)} words"
            f.write(line + "\n")
        for w, r, alts, flags, alt_reads in rows:
            cols = [w, r, "|".join(alts), ",".join(flags), "|".join(alt_reads)]
            while cols[-1] == "":
                cols.pop()
            f.write("\t".join(cols) + "\n")


if __name__ == "__main__":
    addon = sys.argv[1]
    for n in "54321":
        level = "N" + n
        path = os.path.join(addon, f"jlpt_n{n}.txt")
        head, rows = _read(path)
        fixed = apply(level, rows)
        if fixed != rows:
            _write(path, level, head, fixed)
            print(level, len(rows), "→", len(fixed))
