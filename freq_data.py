"""
freq_data.py
Frequency-dictionary comparison for the rank section.

The rank itself counts every studied (learning/young/mature) note in the deck. This module answers the
complementary question: how many of the deck's words are actually COMMON
words? A deck of 13,800 obscure words reaches Amaterasu rank but covers far
less real Japanese than 13,800 high-frequency words.

Data: freq_bccwj.txt — the 20,000 most frequent content words in the BCCWJ
(Balanced Corpus of Contemporary Written Japanese, NINJAL), one per line in
rank order:  display<TAB>reading<TAB>per-million-words<TAB>spellings(|)

Matching: a frequency entry counts as known when any deck note's display
field equals one of the entry's spellings (為る|する, 私 ...) and, if the
note has a reading, that reading is one of the entry's readings — so one
汚れ (よごれ) card doesn't also count as 汚れ (けがれ). A kana-only note
counts as the one entry spelled that way in kana (そう → そう, not 層/沿う/僧);
if none is, it counts as the most common kanji entry with that reading.
"""

from __future__ import annotations

import os
import re
import unicodedata

_HERE = os.path.dirname(os.path.abspath(__file__))
_PATH = os.path.join(_HERE, "freq_bccwj.txt")
# Ranks beyond the top 20,000 (exact) and estimated ranks for compounds the
# short-unit list splits apart (日本語, 可能性 …). Display and sorting only —
# never part of the Frequency Check bars. Built by tools/build_freq_extra.py.
_EXTRA_PATH = os.path.join(_HERE, "freq_extra.txt")
# The CEJC (everyday conversation) list, same format: only for the "of
# everyday speech" percentage, never the bars or ranks (2.4 million words,
# too small to rank 20,000 words reliably). Built by tools/build_freq.py.
_SPEECH_PATH = os.path.join(_HERE, "freq_cejc.txt")

# Tier cut-offs shown as bars. The target is the "Required N1 Vocab (Modern
# Estimate)", ~13,800 words. It's also where the Amaterasu rank begins, but
# the UI never says so in the frequency context (owner wants Amaterasu to be
# a surprise). (The rank's own belt
# threshold is the same 13,800 since 2026-10-20; it was 13,402 / 13,400).
N1_VOCAB_TARGET = 13_800   # was 13,800; 13,800 with Amaterasu (owner 2026-10-20: 3 and 8)
# The tiers' SIZES are the modern vocabulary estimates per JLPT level (the
# same milestones as the rank legend: 800 / 1,500 / 3,900 / 6,000 / 13,800),
# plus 20,000 = near-native. Their WORDS are the most common in written
# Japanese, not the test's words (only 222 of the 682 N5 list words are in
# the top 800; 348 of the top 800 are N3–N1 words), so the bars are named
# by size, "Top 3,900", not "Up to N3" (owner 2026-10-20; was "Required N3
# Vocab (Modern Estimate)"). TIER_LEVEL keeps the level each size follows.
TIERS = [800, 1_500, 3_900, 6_000, N1_VOCAB_TARGET, 20_000]
TIER_LEVEL = {800: "N5", 1_500: "N4", 3_900: "N3", 6_000: "N2", N1_VOCAB_TARGET: "N1"}
TIER_NAMES = {**{n: f"Top {n:,}" for n in TIER_LEVEL}, 20_000: "Near Native"}
# The tiers shown as bars (owner 2026-10-20): the N2 and N1 sizes only, the
# pools of an N2 / N1 goal's step 2. Top 800 / 1,500 / 3,900 are still
# counted (history keeps f800 / f1500 / f3900) but not shown: past the JLPT
# list their fill-in words are N2 / N1 newspaper vocabulary (対策, 資金, 福祉;
# after the N3 list the top 3,900 needs 1,797 more: 447 N2, 683 N1, 667 on
# no list), the wrong next step up to N3, where the lists are the guide.
# N3-useful common words missing from the lists (お客様, 体調) belong in the
# lists themselves (the Word Addition Project), not in a bar.
BAR_TIERS = [6_000, N1_VOCAB_TARGET]


def tier_description(n: int) -> str:
    """'The 3,900 most common words … (about the vocabulary size N3 asks
    for, a modern estimate)' … 'Near-native active vocabulary'.

    20,000 sits inside the published estimates of native ACTIVE (productive)
    vocabulary — from ~8,000 (online writing) to ~30,000 (university
    students) — and well below native RECOGNITION vocabulary (~40,000–
    45,000). It's a target for active vocabulary, not total vocabulary."""
    lvl = TIER_LEVEL.get(n)
    if TIER_NAMES.get(n) == "Near Native":
        return "Near-native active vocabulary (estimate)"
    if lvl is None:
        return f"Top {n:,}"
    return (f"The {n:,} most common words of written Japanese (about the vocabulary size "
            f"{lvl} asks for, a modern estimate; not the test's own words)")

_entries = None   # [(display, reading, pmw, [spellings])], loaded lazily
# (display, reading) → loanword flag ("eng", "wasei", "abbr", "loan-xxx") for
# katakana words; 5th column of freq_bccwj.txt, from JMdict.
FLAGS: dict[tuple[str, str], str] = {}


def _norm(s: str) -> str:
    return unicodedata.normalize("NFKC", s).strip()


_K2H = {c: c - 0x60 for c in range(0x30A1, 0x30F7)}     # ァ…ヶ → ぁ…ゖ (str.translate: fast)


def _kata_to_hira(s: str) -> str:
    return s.translate(_K2H)


def _is_kana(s: str) -> bool:
    return all("぀" <= c <= "ヿ" for c in s)


def load() -> list:
    global _entries
    if _entries is not None:
        return _entries
    entries = []
    try:
        with open(_PATH, encoding="utf-8") as f:
            for line in f:
                if not line.strip() or line.startswith("#"):
                    continue
                parts = line.rstrip("\n").split("\t")
                if len(parts) < 4:
                    continue
                display, reading, pmw, forms = parts[:4]
                # NFKC so full-width digits display normally (１日 → 1日).
                entries.append((_norm(display), reading, float(pmw), forms.split("|")))
                if len(parts) > 4 and parts[4]:
                    FLAGS[(_norm(display), reading)] = parts[4]
    except Exception:
        entries = []
    if entries:
        size = len(entries)
        entries = _add_compounds(entries)
        entries = _merge_reading_splits(entries)
        entries = _split_shared_spellings(entries)
        fitted = _fit_size(entries, size)
        # The sentence parser keeps the corpus words, rows past 20,000
        # included (オーロラ). The added compounds are left out here: なので,
        # ですが, 今や as single words hid the grammar inside them (owner's
        # deck: 38 of 3,000 sentences lost ので / が / や …); the parser adds
        # back only the safe ones (compound_rows, sentence_parser._compound_ok).
        _PARSER_ROWS[:] = [e for e in (entries if len(entries) >= size else fitted)
                           if (e[0], e[1]) not in COMPOUNDS]
        entries = fitted
    _entries = entries
    return entries


_PARSER_ROWS: list = []

_speech = None   # [(display, reading, pmw, [spellings])] from freq_cejc.txt

# Words the corpora count inside another row (owner 2026-10-28): UniDic files
# 何 なん under 何 なに, and splits お母さん into お + 母 (かあ) + さん, so a
# card for the whole word covers that row in the written / speech
# percentages. (spellings, readings in hiragana, corpus row (display, reading)).
# A card matches by spelling (its reading, if any, among these) or as kana.
COVERAGE_PARTS = [
    ({"何"}, {"なん"}, ("何", "なに")),
    ({"お母さん", "母さん", "お母ちゃん", "母ちゃん", "御母さん"},
     {"おかあさん", "かあさん", "おかあちゃん", "かあちゃん"}, ("母", "かあ")),
    ({"お父さん", "父さん", "お父ちゃん", "父ちゃん", "御父さん"},
     {"おとうさん", "とうさん", "おとうちゃん", "とうちゃん"}, ("父", "とう")),
    ({"お兄さん", "兄さん", "お兄ちゃん", "兄ちゃん", "御兄さん"},
     {"おにいさん", "にいさん", "おにいちゃん", "にいちゃん"}, ("兄", "にい")),
    ({"お姉さん", "姉さん", "お姉ちゃん", "姉ちゃん", "御姉さん"},
     {"おねえさん", "ねえさん", "おねえちゃん", "ねえちゃん"}, ("姉", "ねえ")),
    ({"お爺さん", "お祖父さん", "爺さん", "お爺ちゃん", "お祖父ちゃん", "爺ちゃん"},
     {"おじいさん", "じいさん", "おじいちゃん", "じいちゃん"}, ("じい", "じい")),
    ({"お婆さん", "お祖母さん", "婆さん", "お婆ちゃん", "お祖母ちゃん", "婆ちゃん"},
     {"おばあさん", "ばあさん", "おばあちゃん", "ばあちゃん"}, ("ばあ", "ばあ")),
]


def load_speech() -> list:
    global _speech
    if _speech is not None:
        return _speech
    rows = []
    try:
        with open(_SPEECH_PATH, encoding="utf-8") as f:
            for line in f:
                if not line.strip() or line.startswith("#"):
                    continue
                parts = line.rstrip("\n").split("\t")
                if len(parts) >= 4:
                    rows.append((_norm(parts[0]), parts[1], float(parts[2]), parts[3].split("|")))
    except Exception:
        rows = []
    _speech = rows
    return rows


def parser_rows() -> list:
    """The rows the sentence parser's dictionary is built from (load())."""
    load()
    return _PARSER_ROWS


def compound_rows() -> list:
    """The added compound tiles (可能性, 日本語 …) as (display, reading, rank,
    spellings); the sentence parser takes the safe ones (sentence_parser
    _compound_ok)."""
    return [(d, r, i, f) for i, (d, r, _p, f) in enumerate(load()) if (d, r) in COMPOUNDS]


# (display, reading) → the tile it shares its frequency with (聴く → 聞く):
# spellings BCCWJ counts as one word, given their own tiles (freq_splits).
SHARED_WITH: dict[tuple[str, str], str] = {}
# (display, reading) of the compounds added from freq_extra (_add_compounds).
# Neither these nor the shared tiles add to the text-coverage estimate: their
# frequency is already counted (お金 in お + 金, 聴く in 聞く).
COMPOUNDS: set[tuple[str, str]] = set()


def shared_with(display: str, reading: str) -> str:
    """The tile whose (combined) frequency this one shows, or ""."""
    load()
    return SHARED_WITH.get((_norm(display), reading), "")


def _extra_rows():
    """freq_extra.txt rows: (display, reading, rank, kind, other spellings)."""
    try:
        with open(_EXTRA_PATH, encoding="utf-8") as f:
            for line in f:
                parts = line.rstrip("\n").split("\t")
                if line.startswith("#") or len(parts) < 4:
                    continue
                try:
                    rank = int(parts[2])
                except ValueError:
                    continue
                others = [x for x in parts[4].split("|") if x] if len(parts) > 4 else []
                yield _norm(parts[0]), parts[1], rank, parts[3], others
    except Exception:
        return


def _add_compounds(entries: list) -> list:
    """Compounds the short-unit list splits apart (でも = で + も, お金 = お + 金,
    可能性 = 可能 + 性) join the ranking when their estimated rank is above
    COMPOUND_RANK_LIMIT (owner 2026-10-12), at the frequency of the row at
    that rank. Spellings another row already has are left to that row (あたし
    doesn't take 私)."""
    from .freq_splits import COMPOUND_RANK_LIMIT, COMPOUND_DISPLAY, COMPOUND_READING
    COMPOUNDS.clear()
    have = set()
    for d, _r, _p, forms in entries:
        have.add(d)
        have.update(_norm(f) for f in forms)
    out = list(entries)
    for d, rd, rank, kind, others in _extra_rows():
        if kind != "e" or rank > COMPOUND_RANK_LIMIT or d in have:
            continue
        display = COMPOUND_DISPLAY.get(d, d)
        reading = COMPOUND_READING.get(d, rd)
        if display in have:
            continue
        forms = [display]
        for x in (d, *others, rd, reading):
            x = _norm(x)
            if x and x not in have and x not in forms:
                forms.append(x)
        have.update(forms)
        COMPOUNDS.add((display, reading))
        out.append((display, reading, entries[min(rank, len(entries)) - 1][2], forms))
    out.sort(key=lambda e: -e[2])      # stable: ties keep their order
    return out


def _split_shared_spellings(entries: list) -> list:
    """Spellings BCCWJ counts as one word but which differ in use (聞く / 聴く,
    返る / 帰る) get their own tile right after the row they're counted in,
    with its frequency; that row stops matching them (freq_splits)."""
    from .freq_splits import SHARED_SPELLINGS
    SHARED_WITH.clear()
    rows = [[d, r, p, list(f)] for d, r, p, f in entries]
    # Each row's reading in hiragana once, and the rows by it, in order
    # (this was 2 million conversions per load: maintenance pass 2026-10-26).
    by_reading: dict[str, list[int]] = {}
    for i, row in enumerate(rows):
        by_reading.setdefault(_kata_to_hira(row[1]), []).append(i)
    # By reading too: 外 ほか gets its own tile though 外 そと has one.
    displays = {(rows[i][0], h) for h, idx in by_reading.items() for i in idx}
    after: dict[int, list] = {}
    for (spelling, reading), children in SHARED_SPELLINGS:
        same = by_reading.get(reading, ())
        parent = next((i for i in same if spelling in rows[i][3]), None)
        if parent is None:
            continue
        for entry in children:
            spellings = entry.split("|")         # "捕らえる|捕える": tile + other spellings
            child = spellings[0]
            if (child, reading) in displays:     # BCCWJ has it as its own word
                continue
            for i in same:                       # only rows with this reading
                row = rows[i]
                row[3][:] = [f for f in row[3] if f not in spellings]
            after.setdefault(parent, []).append(
                [child, rows[parent][1], rows[parent][2], spellings + [reading]])
            SHARED_WITH[(child, rows[parent][1])] = rows[parent][0]
            displays.add((child, reading))
    out = []
    for i, row in enumerate(rows):
        out.append(row)
        out.extend(after.get(i, ()))
    return [tuple(r) for r in out]


def _fit_size(entries: list, size: int) -> list:
    """Back to exactly `size` rows: drop the rarest, or top up from the exact
    ranks beyond the list in freq_extra.txt."""
    if len(entries) >= size:
        return entries[:size]
    entries = list(entries)
    floor = entries[-1][2]
    have = {(d, r) for d, r, _, _ in entries}
    for display, rd, _rank, kind, others in _extra_rows():
        if len(entries) >= size:
            break
        if kind != "x" or (display, rd) in have:
            continue
        have.add((display, rd))
        # No frequency in freq_extra; just below the last row.
        entries.append((display, rd, floor, list(dict.fromkeys([display, *others, rd]))))
    return entries


# Bumped whenever load() changes the list it returns, so history.signature()
# notices and recomputes old snapshots. (Also bump it when freq_bccwj.txt is
# rebuilt: "pos-1" = kana corpus words matched to dictionary entries by part
# of speech, 2026-10-10.)
LIST_VERSION = "split-3"   # 2026-10-14: + 跳ぶ, 出合う, 永い, 捕らえる tiles (split-2 2026-10-12: じる verbs, split tiles, compounds)

# (display, kept reading) → the other readings merged into that row, in
# frequency order (明日 あす → [あした, みょうにち]). For search and hover.
MERGED_READINGS: dict[tuple[str, str], list[str]] = {}


def merged_readings(display: str, reading: str) -> list[str]:
    """Other readings merged into this frequency row ([] if none)."""
    load()
    return MERGED_READINGS.get((_norm(display), reading), [])


def _merge_reading_splits(entries: list) -> list:
    """BCCWJ splits one word into several rows when the text analyzer assigned
    different readings or kanji (明日 あす #700 / あした #8,117 / みょうにち
    #14,694; 町 vs 街 まち). A written 明日 can't be heard, so most were
    labelled あす. Rows with the same display and the same JMdict spellings are
    one word: merge them (per-million frequencies added, best row's reading
    kept) and re-sort (_fit_size tops the list back up). Homographs that are
    different words (居る/要る いる) have different spellings and stay
    separate, and so do the readings that differ in meaning (今日 きょう /
    こんにち: freq_splits.READING_SPLITS), each keeping only its own kana.
    Done at load time so the bundled BCCWJ file stays as built."""
    from .freq_splits import READING_SPLITS
    merged, index = [], {}
    MERGED_READINGS.clear()
    for display, reading, pmw, forms in entries:
        if display in READING_SPLITS:
            rd = _kata_to_hira(reading)
            forms = [f for f in forms if not _is_kana(_norm(f)) or _kata_to_hira(_norm(f)) == rd]
            key = (display, reading)
        else:
            key = (display, frozenset(_norm(f) for f in forms))
        i = index.get(key)
        if i is None:
            index[key] = len(merged)
            merged.append([display, reading, pmw, forms])
        else:
            merged[i][2] += pmw
            kept = merged[i][1]
            others = MERGED_READINGS.setdefault((display, kept), [])
            if reading != kept and reading not in others:
                others.append(reading)
    merged.sort(key=lambda e: -e[2])   # stable: ties keep BCCWJ order
    return [tuple(e) for e in merged]


_rank_index = None   # spelling → [(rank, {readings})], built lazily


def is_english_loanword(display: str, reading: str) -> bool:
    """Frequency-list counterpart of jlpt_data.is_english_loanword: plain
    English loanwords, not wasei-eigo, abbreviations, loanwords from other
    languages or false friends."""
    from .jlpt_data import FALSE_FRIENDS, COUNT_AS_ENGLISH, NOT_ENGLISH
    load()
    flag = FLAGS.get((display, reading))
    return ((flag == "eng" or display in COUNT_AS_ENGLISH)
            and display not in FALSE_FRIENDS and display not in NOT_ENGLISH)


def _override_key(display: str, reading: str) -> tuple[str, str]:
    """Overrides are keyed by the word as shown; compare loosely so a JLPT
    entry and a frequency entry for the same word share one mark."""
    return _norm(display), _kata_to_hira(_norm(reading))


def mark_ranks(pairs) -> set:
    """0-based frequency rows that marked (found / suspended) words lead to
    through their spellings — the JLPT entry's alternate spellings included —
    and reading. Lets a mark made on a JLPT word reach its frequency row when
    the two lists spell it differently (JLPT おまえ, frequency お前). A
    katakana mark only reaches a katakana row: the list counts ガン as a
    spelling of がん (cancer), タイ of 鯛, ドン of どん, so marking the
    loanwords marked those words too (owner 2026-10-27: "6 words marked
    found" with only the loanword button pressed)."""
    from .jlpt_data import alt_forms
    entries = load()
    out = set()
    for d, r in pairs:
        rk = word_rank(d, r, alt_forms(d, r))
        if rk is None:
            continue
        if _is_katakana(d) and not _is_katakana(entries[rk - 1][0]):
            continue
        out.add(rk - 1)
    return out


def _is_katakana(s: str) -> bool:
    s = _norm(s)
    return bool(s) and all("ァ" <= c <= "ヶ" or c in "ー・" for c in s)


_usual_kana = None   # {(kanji display, hiragana reading)} usually written in kana


def usually_kana(display: str, reading_h: str) -> bool:
    """A kanji word real text usually writes in kana (物 もの, 言う いう,
    諦める あきらめる): the parser's kana_ok.txt + kana_usual.txt. Only these
    let a kana-only spelling reach a kanji row."""
    global _usual_kana
    if _usual_kana is None:
        from .sentence_parser import _kana_ok
        _usual_kana = {(_norm(d), _kata_to_hira(_norm(r))) for d, r in _kana_ok()}
    return (_norm(display), reading_h) in _usual_kana


def word_rank(display: str, reading: str, alts=()) -> int | None:
    """1-based frequency rank of a word (e.g. a JLPT list entry), or None if
    it isn't in the list. Matches on any spelling (display or alts) whose
    entry also has this reading, so 汚れ よごれ and 汚れ けがれ get their own
    ranks. A kana spelling prefers the row spelled that way, then a kana row
    it's a variant of (ずうっと → ずっと), and reaches a kanji row by its
    sound only if that word is usually written in kana (もの → 物): else
    ほうき (broom) was 放棄, やかん (kettle) 夜間, なんか 南下, と 都 (owner
    2026-10-27). The word's own spelling wins over its alts (街 is 街, not
    the commoner 町)."""
    global _rank_index
    if _rank_index is None:
        _rank_index = {}
        for rank, (disp, rd, _, forms) in enumerate(load(), start=1):
            readings = {_kata_to_hira(_norm(f)) for f in forms if _is_kana(_norm(f))}
            readings.add(_kata_to_hira(rd))
            row = (rank, readings, _kata_to_hira(_norm(disp)), _kata_to_hira(_norm(rd)))
            for form in forms:
                _rank_index.setdefault(_norm(form), []).append(row)
    r = _kata_to_hira(_norm(reading)) if reading else ""
    best = None                              # (tier, rank)
    for i, form in enumerate((display, *alts)):
        f = _norm(form)
        kana = _is_kana(f)
        alt = i > 0
        for rank, readings, disp_h, main_h in _rank_index.get(f, ()):
            if r and r not in readings:
                continue
            if _kata_to_hira(f) == disp_h:
                tier = 2 if alt else 0       # the row spelled this way (はし with alt 箸: 箸)
            elif not kana:
                tier = 3 if alt else 1       # one of the row's spellings (解ける in 溶ける)
            elif _is_kana(disp_h) and (_is_katakana(f) or _kata_to_hira(f)[:1] == disp_h[:1]):
                tier = 5 if alt else 4       # a kana variant of a kana row (リポート → レポート, not なんか → カボチャ)
            elif usually_kana(disp_h, _kata_to_hira(f)):
                tier = 7 if alt else 6       # by its sound, a usually-kana word
            else:
                continue
            if best is None or (tier, rank) < best:
                best = (tier, rank)
    return best[1] if best else None


_extra_index = None   # spelling → [(rank, estimated, {readings})], built lazily


def _load_extra() -> dict:
    global _extra_index
    if _extra_index is not None:
        return _extra_index
    index = {}
    try:
        with open(_EXTRA_PATH, encoding="utf-8") as f:
            for line in f:
                if not line.strip() or line.startswith("#"):
                    continue
                parts = line.rstrip("\n").split("\t")
                if len(parts) < 4:
                    continue
                display, rd, rank, kind = parts[:4]
                forms = [display, rd] + ([x for x in parts[4].split("|") if x]
                                         if len(parts) > 4 else [])
                readings = {_kata_to_hira(_norm(x)) for x in forms if _is_kana(_norm(x))}
                entry = (int(rank), kind == "e", readings)
                for form in dict.fromkeys(_norm(x) for x in forms):
                    index.setdefault(form, []).append(entry)
    except Exception:
        index = {}
    _extra_index = index
    return index


def _extra_rank(forms, reading: str, exact_kana: bool = False):
    """(rank, estimated) from freq_extra.txt, or None. `exact_kana`: a
    kana-only card only matches an entry spelled that way, so one kana card
    doesn't borrow the rank of a kanji homophone."""
    r = _kata_to_hira(_norm(reading)) if reading else ""
    best = None
    index = _load_extra()
    for form in forms:
        nf = _norm(form)
        for rank, est, readings in index.get(nf, ()):
            if exact_kana and _kata_to_hira(nf) not in readings:
                continue
            if (not r or r in readings) and (best is None or rank < best[0]):
                best = (rank, est)
    return best


def word_rank_info(display: str, reading: str, alts=()):
    """(rank, estimated) for any word: its real rank in the top 20,000, else
    an exact rank beyond 20,000 or an estimated rank for a compound
    (日本語 ≈ #1,662). None if the word isn't ranked at all."""
    rank = word_rank(display, reading, alts)
    if rank is not None:
        return rank, False
    return _extra_rank((display, *alts), reading)


def rank_text(rank: int, estimated: bool) -> str:
    """'#2,340', or '≈#2,340' for an estimated rank."""
    return f"{'≈' if estimated else ''}#{rank:,}"


def coverage(nid_to_display: dict, nid_to_reading: dict, overrides=None) -> dict:
    """
    Compare the deck's notes against the frequency list.

    Overrides (the same found/suspended marks as the JLPT lists): a word
    marked found with no card counts as known; a suspended word is left out
    of the counts AND the totals (tier_totals), like the JLPT bars.

    Returns:
      available     - False if the frequency file is missing
      list_size     - number of ranked words (20,000)
      tiers         - [(N, known_in_top_N)] for each N in TIERS
      notes_total   - number of scanned deck notes (real notes: the words
                      parsed from one sentence card are one note)
      notes_in_top  - {N: number of deck notes with a word in the top N}
      text_coverage - share (0-1) of running content-word text covered by
                      known words, estimated from per-million frequencies
      missing       - [(rank, display, reading)] most common words the deck
                      doesn't have, first 100
      entries       - [(rank, display, reading, nid or None)] for every ranked
                      word, in rank order — used by the frequency word grid
      nid_rank      - {nid: 0-based rank} for deck notes found in the list —
                      used to sort the Non-JLPT section of the Word Grid
      tier_totals   - {N: words in the top N that aren't suspended}
      found_ranks / suspended_ranks - sets of 0-based ranks of words
                      marked found (with no card) / suspended
    """
    entries = load()
    if not entries:
        return {"available": False}

    found_keys = suspended_keys = set()
    found_alias = suspended_alias = set()
    if overrides is not None:
        found_keys = {_override_key(d, r) for d, r in overrides.found_pairs()}
        suspended_keys = {_override_key(d, r) for d, r in overrides.suspended_pairs()}
        # A mark made on a JLPT word also reaches its frequency row when the
        # JLPT list spells it another way (おまえ there, お前 here): the row
        # its spellings + reading lead to, as for the hover's JLPT level.
        found_alias = mark_ranks(overrides.found_pairs())
        suspended_alias = mark_ranks(overrides.suspended_pairs())
    found_ranks: set[int] = set()
    suspended_ranks: set[int] = set()

    # Index the deck. Cards written with kanji are looked up by spelling;
    # kana-only cards are handled separately, because a kana spelling is
    # shared by many homophones (そう = 層, 沿う, 僧 …) and one card should
    # count as one word, not all of them.
    by_display: dict[str, list[int]] = {}   # kanji cards: spelling → nids
    kana_cards: dict[str, list[int]] = {}   # kana cards: exact kana → nids
    kana_hira:  dict[str, list[int]] = {}   # kana cards: hiragana → nids
    for nid, display in nid_to_display.items():
        d = _norm(display)
        if _is_kana(d):
            kana_cards.setdefault(d, []).append(nid)
            kana_hira.setdefault(_kata_to_hira(d), []).append(nid)
        else:
            by_display.setdefault(d, []).append(nid)

    # A kana card is the frequency word spelled exactly that way (そう → そう).
    # Only if no frequency word is spelled in that kana does it fall back to
    # the most common kanji word with that reading that is usually written
    # in kana (もの → 物, あきらめる → 諦める); never to any homophone (と was
    # 都, なんか 南下, かぎ 鍵: owner 2026-10-27, as the JLPT bars do).
    kana_spelled = {_kata_to_hira(_norm(d)) for d, _, _, _ in entries if _is_kana(_norm(d))}
    kana_fallback_used: set[str] = set()

    nid_best_rank: dict[int, int] = {}
    known_nids: dict[int, list[int]] = {}   # 0-based rank → every matching nid
    known_flags = []
    pmw_known = pmw_total = 0.0
    missing = []
    grid_entries = []

    # Note readings in hiragana, for telling homographs apart
    # (汚れ よごれ "dirt" vs 汚れ けがれ "impurity").
    # A reading field may hold several readings (何 "なに・なん"), so keep each.
    note_reading = {
        nid: {_kata_to_hira(p) for p in re.split(r"[・/／、,，;；\s]+", _norm(r)) if p}
        for nid, r in nid_to_reading.items() if r
    }

    # Corpus rows the deck covers through COVERAGE_PARTS (お母さん → 母 かあ):
    # the two percentages only, never a tile or a bar.
    credited: set[tuple[str, str]] = set()
    for spellings, part_readings, target in COVERAGE_PARTS:
        for nid, display in nid_to_display.items():
            d = _norm(display)
            r = note_reading.get(nid)
            if ((d in spellings and (not r or r & part_readings))
                    or (_is_kana(d) and _kata_to_hira(d) in part_readings)):
                credited.add(target)
                break

    written_rank: dict[tuple[str, str], int] = {}   # (display, reading) → 0-based rank
    for rank, (display, reading, pmw, forms) in enumerate(entries):
        readings = {_kata_to_hira(_norm(f)) for f in forms if _is_kana(_norm(f))}
        readings.add(_kata_to_hira(reading))
        nids = []
        for form in forms:
            for nid in by_display.get(_norm(form), ()):
                # Spelling matches; the reading must too when the note has one.
                r = note_reading.get(nid)
                if not r or r & readings:
                    nids.append(nid)
        nd_ = _norm(display)
        if _is_kana(nd_):
            nids.extend(kana_cards.get(nd_, ()))
        else:
            for rh in readings:
                if (rh in kana_hira and rh not in kana_spelled and rh not in kana_fallback_used
                        and usually_kana(nd_, rh)):
                    nids.extend(kana_hira[rh])
                    kana_fallback_used.add(rh)

        written_rank.setdefault((nd_, _kata_to_hira(reading)), rank)
        okey = _override_key(display, reading)
        if okey in suspended_keys or rank in suspended_alias:
            # Suspended: out of the counts and the totals.
            suspended_ranks.add(rank)
            known_flags.append(None)
            grid_entries.append((rank + 1, display, reading, nids[0] if nids else None))
            continue
        if not nids and (okey in found_keys or rank in found_alias):
            found_ranks.add(rank)
        known = bool(nids) or rank in found_ranks
        known_flags.append(known)
        grid_entries.append((rank + 1, display, reading, nids[0] if nids else None))
        # Text coverage counts each corpus word once (not the shared or
        # compound tiles, whose frequency is in other rows already).
        weight = 0.0 if ((display, reading) in SHARED_WITH or (display, reading) in COMPOUNDS) else pmw
        pmw_total += weight
        if known or (nd_, _kata_to_hira(reading)) in credited:
            pmw_known += weight
        if known:
            if nids:
                known_nids[rank] = nids
            for nid in nids:
                if nid not in nid_best_rank:
                    nid_best_rank[nid] = rank
        else:
            missing.append((rank + 1, display, reading))

    # Everyday speech (CEJC): the same estimate over real conversation. A
    # word in the written list keeps its known / suspended state from there
    # (marks included); a speech-only word (うわ, めっちゃ) is matched to the
    # deck the same way as above.
    def _deck_has(display, reading, forms):
        readings = {_kata_to_hira(_norm(f)) for f in forms if _is_kana(_norm(f))}
        readings.add(_kata_to_hira(reading))
        for form in forms:
            for nid in by_display.get(_norm(form), ()):
                r = note_reading.get(nid)
                if not r or r & readings:
                    return True
        if _is_kana(display):
            return display in kana_cards
        return any(rh in kana_hira and rh not in kana_spelled and usually_kana(display, rh)
                   for rh in readings)

    speech_known = speech_total = 0.0
    speech_by_rank: dict[int, float] = {}   # written rank → speech pmw, for hold_found
    for display, reading, pmw, forms in load_speech():
        r = written_rank.get((display, _kata_to_hira(reading)))
        if r is not None:
            if known_flags[r] is None:          # suspended
                continue
            known = known_flags[r] or _deck_has(display, reading, forms)
            if known_flags[r]:
                speech_by_rank[r] = speech_by_rank.get(r, 0.0) + pmw
        else:
            okey = _override_key(display, reading)
            if okey in suspended_keys:
                continue
            known = okey in found_keys or _deck_has(display, reading, forms)
        speech_total += pmw
        if known or (display, _kata_to_hira(reading)) in credited:
            speech_known += pmw

    tiers = []
    tier_totals = {}
    running = counted = 0
    tier_iter = iter(TIERS)
    next_tier = next(tier_iter)
    for i, k in enumerate(known_flags, start=1):
        if k is not None:          # None = suspended
            running += k
            counted += 1
        while next_tier is not None and i == next_tier:
            tiers.append((next_tier, running))
            tier_totals[next_tier] = counted
            next_tier = next(tier_iter, None)

    # Real notes: a sentence card's parsed words have ids of their own
    # (card_state.pseudo_nid) but are one card (2026-10-20: each word was
    # counted as a card, inflating "of your N cards" for sentence decks).
    from .card_state import real_nid
    # The Frequency Check's missing words: the first 100, and the first 100
    # without other spellings / readings of a known word (its "Hide …"
    # checkbox, owner 2026-10-20): the same spelling as a known row (私
    # わたくし, 月 がつ) or a split tile whose parent is known (聴く, 在る, 診る).
    known_disp = {_norm(entries[i][0]) for i, k in enumerate(known_flags) if k}
    missing_lean = [m for m in missing
                    if _norm(m[1]) not in known_disp
                    and _norm(SHARED_WITH.get((m[1], m[2]), "")) not in known_disp][:100]
    missing = missing[:100]

    notes_in_top = {
        n: len({real_nid(nid) for nid, r in nid_best_rank.items() if r < n}) for n in TIERS
    }

    # Notes outside the top 20,000: exact ranks beyond it or estimated
    # compound ranks (display and sorting only; not part of any count above).
    nid_rank_extra: dict[int, tuple[int, bool]] = {}
    for nid, display in nid_to_display.items():
        if nid in nid_best_rank:
            continue
        d = _norm(display)
        reads = note_reading.get(nid) or {""}
        best = None
        for r in reads:
            hit = _extra_rank((d,), r, exact_kana=_is_kana(d))
            if hit and (best is None or hit[0] < best[0]):
                best = hit
        if best:
            nid_rank_extra[nid] = best

    return {
        "available":     True,
        "list_size":     len(entries),
        "tiers":         tiers,
        "notes_total":   len({real_nid(nid) for nid in nid_to_display}),
        "notes_in_top":  notes_in_top,
        "text_coverage": (pmw_known / pmw_total) if pmw_total else 0.0,
        "pmw_total":     pmw_total,       # for hold_found
        # Share (0-1) of everyday conversation (CEJC) covered by known words;
        # None when freq_cejc.txt is missing.
        "speech_coverage": (speech_known / speech_total) if speech_total else None,
        "speech_total":  speech_total,    # for hold_found
        "speech_by_rank": speech_by_rank,
        "missing":       missing,
        "missing_lean":  missing_lean,
        "entries":       grid_entries,
        "nid_rank":      nid_best_rank,   # nid → best 0-based rank (ranked notes only)
        # 0-based rank → every deck nid matching that word (known words only);
        # history.py dates each word by its earliest note
        "known_nids":    known_nids,
        "tier_totals":   tier_totals,
        "found_ranks":   found_ranks,
        "suspended_ranks": suspended_ranks,
        # nid → (1-based rank, estimated) for notes outside the top 20,000
        "nid_rank_extra": nid_rank_extra,
    }


def hold_found(freq: dict, ranks: set):
    """Take these marked-found rows (0-based ranks) off coverage()'s counts:
    the tiers and the text coverage (card_state.hold_back_loans). They stay
    marked, and stay out of the missing lists."""
    ranks = set(ranks) & set(freq.get("found_ranks") or ())
    if not ranks:
        return
    freq["found_ranks"] = set(freq["found_ranks"]) - ranks
    freq["tiers"] = [(n, k - sum(1 for r in ranks if r < n)) for n, k in freq.get("tiers", [])]
    entries, total = load(), freq.get("pmw_total") or 0.0
    if entries and total:
        held = sum(entries[r][2] for r in ranks
                   if (entries[r][0], entries[r][1]) not in SHARED_WITH
                   and (entries[r][0], entries[r][1]) not in COMPOUNDS)
        freq["text_coverage"] = max(0.0, freq.get("text_coverage", 0.0) - held / total)
    s_total, s_by_rank = freq.get("speech_total") or 0.0, freq.get("speech_by_rank") or {}
    if freq.get("speech_coverage") is not None and s_total:
        held = sum(s_by_rank.get(r, 0.0) for r in ranks)
        freq["speech_coverage"] = max(0.0, freq["speech_coverage"] - held / s_total)
