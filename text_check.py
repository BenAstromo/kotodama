"""
text_check.py
Two views on "which words do I know", built on the analysis results (no Qt
here, so it can be tested headless):

  Text check (owner 2026-10-14): paste a text or open a subtitle file, and
  see how much of it your known words cover, and which unknown words in it
  are worth learning. The sentence parser splits the text into the words of
  our lists (the same reading the sentence cards get). Material at about
  95–98% coverage is the sweet spot for immersion.

  Kanji → words (owner 2026-10-14): for one kanji, the common words that use
  it which you don't know yet, most common first.

  Kanji and grammar in a text (owner 2026-10-20): every kanji in the text
  (level, known, the text's words that use it) and every grammar point the
  detector finds (level, known, the sentences it's in), basic particles
  left out. Known = as on the Kanji & Grammar tab. Grammar detection
  measured ≈99% precision / ≈90% recall: a listed point is almost always
  there, about 1 in 10 may be missed.

A word counts as known exactly as on the bars: a learned card (or a mark as
found) for its JLPT entry or its frequency tile.
"""

from __future__ import annotations

import re
from collections import Counter

from . import freq_data
from . import jlpt_data
from .jlpt_data import LEVELS
from .kanji_data import is_kanji

# Coverage verdicts, by share of the text's words you know.
VERDICTS = [
    (0.98, "Comfortable: you can read this and pick up the few new words from context."),
    (0.95, "Good for immersion: some new words, but the story should carry you."),
    (0.90, "Challenging: expect to look words up often."),
    (0.00, "Hard: too many unknown words to follow without a dictionary."),
]


def verdict(coverage: float) -> str:
    for limit, text in VERDICTS:
        if coverage >= limit:
            return text
    return VERDICTS[-1][1]


# ── what you know ─────────────────────────────────────────────────────────────

class Knowledge:
    """Known / level / rank lookups for list words, from analyse() results."""

    def __init__(self, results: dict):
        self.level: dict[tuple, str] = {}
        self.jlpt_known: set[tuple] = set()
        for lvl in LEVELS:
            res = results.get(lvl) or {}
            for d, r, _nid in res.get("known_words", ()):
                self.jlpt_known.add((d, r))
                self.level.setdefault((d, r), lvl)
            for d, r in res.get("missing_words", ()):
                self.level.setdefault((d, r), lvl)
        freq = results.get("frequency") or {}
        self.entries = freq.get("entries") or []          # [(rank, d, r, nid)]
        found = freq.get("found_ranks") or set()          # 0-based
        self.suspended = {i + 1 for i in (freq.get("suspended_ranks") or ())}
        self.freq_known = {rank for rank, _d, _r, nid in self.entries
                           if nid is not None or (rank - 1) in found}
        self._rank_cache: dict[tuple, int | None] = {}

    def rank(self, d: str, r: str):
        key = (d, r)
        if key not in self._rank_cache:
            self._rank_cache[key] = freq_data.word_rank(d, r, jlpt_data.same_kanji_forms(d, r))
        return self._rank_cache[key]

    def is_known(self, d: str, r: str) -> bool:
        if (d, r) in self.jlpt_known:
            return True
        rank = self.rank(d, r)
        return rank is not None and rank in self.freq_known


# ── text check ────────────────────────────────────────────────────────────────

_SRT_TIME = re.compile(r"^\s*\d+:\d+(:\d+)?[.,]\d+\s*-->")


def _text_score(t: str) -> int:
    """How much a decoding looks like Japanese text: kana, kanji and plain
    ASCII count; half-width katakana and control characters (what EUC-JP
    read as Shift-JIS, or the reverse, turns into) count against it."""
    s = 0
    for c in t:
        o = ord(c)
        if 0x3040 <= o <= 0x30FF or 0x4E00 <= o <= 0x9FFF or 0x20 <= o < 0x7F or c in "\n\t\r　、。":
            s += 1
        elif 0xFF61 <= o <= 0xFF9F:
            s -= 2
        elif o < 0x20 or 0xE000 <= o <= 0xF8FF:
            s -= 5
    return s


def decode_text(raw: bytes) -> str | None:
    """A text / subtitle file's bytes as text, or None if it isn't text.
    A BOM decides; else UTF-8; else UTF-16 without a BOM (many NUL bytes);
    else Shift-JIS or EUC-JP, whichever reads more like Japanese. (Trying
    UTF-16 before Shift-JIS read every even-length Shift-JIS file as
    garbage: maintenance pass 2026-10-26.)"""
    if raw.startswith(b"\xef\xbb\xbf"):
        cands = ["utf-8-sig"]
    elif raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        cands = ["utf-16"]
    else:
        try:
            return raw.decode("utf-8")
        except UnicodeError:
            pass
        if raw and raw.count(0) >= len(raw) // 5:
            even0 = raw[0::2].count(0)
            cands = ["utf-16-be", "utf-16-le"] if even0 > raw[1::2].count(0) else ["utf-16-le", "utf-16-be"]
        else:
            cands = ["cp932", "euc_jp"]
    best = None
    for enc in cands:
        try:
            t = raw.decode(enc)
        except UnicodeError:
            continue
        if best is None or _text_score(t) > _text_score(best):
            best = t
    if best is None:
        return None
    bad = sum(1 for c in best if (ord(c) < 0x20 and c not in "\n\t\r") or 0xE000 <= ord(c) <= 0xF8FF)
    return None if bad > max(2, len(best) // 100) else best


def text_from_file(raw: str, name: str = "") -> str:
    """Plain text from a .txt / .srt / .vtt / .ass file's contents: cue
    numbers, timestamps and styling tags dropped."""
    name = name.lower()
    lines = raw.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    out = []
    if name.endswith((".ass", ".ssa")):
        for line in lines:
            if line.startswith("Dialogue:"):
                text = line.split(",", 9)[-1]
                text = re.sub(r"\{[^}]*\}", "", text).replace("\\N", "\n").replace("\\n", "\n")
                out.append(text)
        return "\n".join(out)
    if name.endswith((".srt", ".vtt")):
        for line in lines:
            s = line.strip()
            if not s or s.isdigit() or _SRT_TIME.match(s) or s == "WEBVTT":
                continue
            out.append(re.sub(r"<[^>]+>|\{[^}]*\}", "", s))
        return "\n".join(out)
    return "\n".join(lines)


def _clean(text: str) -> str:
    # Aozora-style ruby: ｜漢字《かんじ》 → 漢字
    text = re.sub(r"《[^》]*》", "", text).replace("｜", "")
    return text


def _pieces(text: str):
    """The text in parser-sized pieces (sentences, at most ~120 characters)."""
    for line in re.split(r"(?<=[。！？!?\n])", _clean(text)):
        line = line.strip()
        while len(line) > 120:
            cut = max(line.rfind(c, 0, 120) for c in "、，, 　")
            cut = cut + 1 if cut > 20 else 120
            yield line[:cut]
            line = line[cut:]
        if line:
            yield line


def _jp(s: str) -> bool:
    return any(is_kanji(c) or 0x3040 <= ord(c) <= 0x30FF for c in s)


# Conjunctions that, inside a sentence, are only particles: 外では = 外 + で + は,
# 腕白だが = だ + が (vocab test 2026-10-17).
_MID_CONJ = {"では", "だが", "そこで", "それで", "だから"}
# Suffix kanji that aren't list words themselves (定食屋, 日本製)
_SUFFIX_KANJI = set("屋製産型派系費率側式歴帳界際感観論説党省庁署局課科")


def piece_items(toks: list) -> list:
    """What one parsed piece adds to the count: ("word", display, reading)
    for each counted word, ("unrec", text) for each run of characters no list
    word covers. Shared with tools/vocab_eval.py, which measures it.

    Not unknown words (vocab test 2026-10-17): a single kanji stuck to a
    counted word is its prefix or suffix (定食屋, 交通量, 無関心, 長距離走:
    the word counts, the affix is neither known nor unknown); お / ご / 御
    before a word and ら after one likewise. Two or more such characters
    together (心棒, 付箋, 東京) are an unknown word."""
    from . import sentence_parser
    out = []
    n = len(toks)
    i = 0
    while i < n:
        surface, kind, d, r = toks[i][:4]
        if kind in ("unk", "lone"):
            j = i
            while j < n and toks[j][1] in ("unk", "lone"):
                j += 1
            run = "".join(t[0] for t in toks[i:j])
            prev_word = i > 0 and toks[i - 1][1] == "word"
            next_word = j < n and toks[j][1] == "word"
            affix = len(run) == 1 and (
                (kind == "lone" and (prev_word or next_word))
                or (run in _SUFFIX_KANJI and prev_word)
                or (run in ("お", "ご", "御") and next_word)
                or (run == "ら" and prev_word))
            if _jp(run) and not affix:
                out.append(("unrec", run))
            i = j
            continue
        # Particles that are also list words (だけ, から, より) are
        # grammar here, like the parser's other function tokens.
        # 入るなり (as soon as): grammar after a plain verb, not なる
        if kind == "word" and surface not in sentence_parser.FUNCTION_TOKENS \
                and not (surface in _MID_CONJ and i > 0 and toks[i - 1][1] != "punct") \
                and not (surface == "なり" and i > 0 and toks[i - 1][1] == "word"
                         and toks[i - 1][4] is None and toks[i - 1][0][-1:] in "うくぐすつぬぶむる"):
            out.append(("word", d, r))
        i += 1
    return out


def check_text(text: str, know: Knowledge) -> dict:
    """Coverage of a text by known words.

    Every word the parser finds counts each time it appears; particles and
    endings aren't counted; a run of characters no list word covers (names,
    rare words) counts as one unknown piece. coverage = known words /
    (words + unknown pieces)."""
    from . import sentence_parser
    known_n = unknown_n = 0
    words: Counter = Counter()
    unrec: Counter = Counter()
    cache = sentence_parser._TOK_CACHE
    for piece in _pieces(text):
        fresh = piece not in cache
        toks = sentence_parser.tokens(piece)
        if fresh:
            cache.pop(piece, None)          # don't keep a whole novel cached
        for item in piece_items(toks):
            if item[0] == "word":
                words[(item[1], item[2])] += 1
            else:
                unrec[item[1]] += 1
    rows = []
    for (d, r), n in words.items():
        k = know.is_known(d, r)
        if k:
            known_n += n
        else:
            unknown_n += n
        rows.append({"display": d, "reading": r, "count": n, "known": k,
                     "rank": know.rank(d, r), "level": know.level.get((d, r))})
    unrec_n = sum(unrec.values())
    total = known_n + unknown_n + unrec_n
    return {
        "total": total,
        "known": known_n,
        "unknown": unknown_n,
        "unrecognised": unrec_n,
        "coverage": known_n / total if total else 0.0,
        "unique_known": sum(1 for row in rows if row["known"]),
        "unique_total": len(rows),
        "words": rows,
        "unrec": unrec.most_common(),
    }


# ── kanji and grammar in a text ─────────────────────────────────────────────

def check_kanji(text: str, results: dict, word_rows: list) -> dict:
    """Every kanji in the text: {"char", "count", "level", "known" (None when
    kanji aren't tracked), "words": the text's words that use it}."""
    from . import kanji_data
    info = kanji_data.data()
    kres = results.get("kanji")
    known = set(kres.get("known", ())) if kres else None
    counts = Counter(c for c in _clean(text) if is_kanji(c))
    words: dict[str, list] = {}
    for w in sorted(word_rows, key=lambda w: -w["count"]):
        for c in dict.fromkeys(w["display"]):
            if c in counts:
                words.setdefault(c, []).append(w["display"])
    rows = [{"char": c, "count": n, "level": (info.get(c) or {}).get("level") or None,
             "known": (c in known) if known is not None else None,
             "meanings": (info.get(c) or {}).get("meanings", []), "words": words.get(c, [])}
            for c, n in counts.items()]
    return {"rows": rows, "unique": len(rows),
            "known": sum(1 for r in rows if r["known"]),
            "tracked": known is not None}


def check_grammar(text: str, results: dict, examples: int = 3) -> dict:
    """Grammar points found in the text (basic particles left out):
    {"gid", "count" (sentences it's in), "level", "known" (None without a
    grammar source), "examples": [(sentence, [(start, end)])]}."""
    from . import grammar_data
    data = grammar_data.data()
    gres = results.get("grammar")
    known = set(gres.get("known", ())) if gres and gres.get("known") else None
    basic = set(grammar_data.BASIC_PARTICLES)
    found: dict[str, dict] = {}
    for piece in _pieces(text):
        spans: dict = {}
        try:
            ids = grammar_data.sentence_ids(piece, spans)
        except Exception:
            continue
        for gid in ids:
            if gid in basic or gid not in data:
                continue
            row = found.setdefault(gid, {"gid": gid, "count": 0, "level": data[gid].get("level"),
                                         "known": (gid in known) if known is not None else None,
                                         "examples": []})
            row["count"] += 1
            if len(row["examples"]) < examples:
                row["examples"].append((piece, spans.get(gid, [])))
    rows = list(found.values())
    return {"rows": rows, "known": sum(1 for r in rows if r["known"]),
            "tracked": known is not None}


# ── kanji → words ─────────────────────────────────────────────────────────────

def kanji_learn_index(results: dict, per_kanji: int = 30) -> dict:
    """kanji → [(rank, display, reading, level)] of the most common words
    containing it that you don't know yet (frequency list, then JLPT words
    off it), at most per_kanji each. Built in one pass."""
    know = Knowledge(results)
    out: dict[str, list] = {}
    seen: set[tuple] = set()

    def add(item, display):
        for c in dict.fromkeys(display):
            if is_kanji(c):
                lst = out.setdefault(c, [])
                if len(lst) < per_kanji:
                    lst.append(item)

    for rank, d, r, _nid in know.entries:
        if rank in know.freq_known or rank in know.suspended:
            continue
        if (d, r) in know.jlpt_known:
            continue
        seen.add((d, r))
        add((rank, d, r, know.level.get((d, r))), d)
    for lvl in LEVELS:
        for d, r in (results.get(lvl) or {}).get("missing_words", ()):
            if (d, r) in seen or know.rank(d, r) is not None:
                continue   # already in, under its frequency tile
            add((None, d, r, lvl), d)
    return out
