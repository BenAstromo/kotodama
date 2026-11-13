"""
sentence_parser.py
The auto parser (backlog #5, phase 3): finds vocab, kanji and grammar in
sentence fields, for users who mine sentence cards instead of (or as well as)
word cards. Pure Python, bundled, no install: Anki's Python can't load
MeCab-type analysers.

Vocab works like Yomitan: at each position take the longest stretch of text
that is a dictionary word, directly or after undoing its conjugation
(食べなかった → 食べる), then move past it. The dictionary is our own word
lists: the JLPT lists and the 20,000-word frequency list, with their
alternate spellings. Only those words count anywhere in the add-on, so a
bigger dictionary wouldn't change any count.

Rules that keep the counts honest (owner: detect the right words, don't
inflate):
  - Script rule, as for cards: kana in a sentence only matches words that
    are themselves written in kana (はし is never 橋). Kanji spellings always
    match.
  - A conjugated form only matches a word whose part of speech fits the
    rule (食べた → 食べる needs an Ichidan verb; 高かった → 高い an
    i-adjective). Parts of speech come from meanings.json (JMdict via
    Jitendex). Words without one only match unconjugated.
  - Single kana never count as words (particles, fragments).
  - When one spelling is several words (汚れ よごれ / けがれ), the more
    common one is taken.

Kanji come straight from the text (kanji_data.kanji_in); grammar from
grammar_data.sentence_ids.
"""

from __future__ import annotations

import math
import re

from . import freq_data
from . import jlpt_data
from . import meanings
from .jlpt_data import LEVELS
from .kanji_data import field_text, is_kanji

MAX_LEN = 12          # longest surface form tried at one position
_INVISIBLE = {0x200E, 0x200F, 0x200B, 0xFEFF}   # LRM, RLM, zero-width space, BOM


def clean(raw: str) -> str:
    """A sentence field as plain text: line breaks become spaces, HTML,
    bracket furigana and invisible marks are dropped."""
    s = re.sub(r"<br\s*/?>|</div>|</p>", " ", raw or "", flags=re.I)
    s = field_text(s)
    return "".join(c for c in s if ord(c) not in _INVISIBLE)


def sentence_texts(deck_name: str, field_mappings: list, sentence_only: bool = False,
                   seen_only: bool = True) -> dict:
    """nid → cleaned sentence of every note in the deck whose note-type
    mapping has a sentence field (sentence_only: only mappings without a
    word field, i.e. sentence cards whose vocab is parsed)."""
    from . import card_state
    out = {}
    if not deck_name:
        return out
    for nid, note in card_state.deck_notes(deck_name, seen_only).items():
        model = note.type_name
        for m in field_mappings:
            if m.get("note_type") and m["note_type"] != model:
                continue
            sf = m.get("sentence_field", "")
            if sf and sf in note:
                if not (sentence_only and m.get("field")):
                    text = clean(note[sf])
                    if text:
                        out[nid] = text
                break
            # An "(all note types)" row whose sentence field this note lacks
            # doesn't apply: try the next row. A row naming this note type
            # ends the search (a deliberate "no sentence field").
            if m.get("note_type"):
                break
    return out


def _has_kanji(s: str) -> bool:
    return any(is_kanji(c) for c in s)


# ── dictionary ────────────────────────────────────────────────────────────────

_LEX = None   # surface → [(priority, display, reading, kinds)]


_FREQ_FORMS = None


def _other_spellings(display: str, reading: str) -> list:
    """The word's kanji spellings (なる → 成る), from its list entries."""
    global _FREQ_FORMS
    if _FREQ_FORMS is None:
        _FREQ_FORMS = {}
        for d, r, _pmw, fs in freq_data.parser_rows():
            _FREQ_FORMS.setdefault((d, r), []).extend(fs)
    return [f for f in jlpt_data.alt_forms(display, reading) + _FREQ_FORMS.get((display, reading), [])
            if _has_kanji(f)]


def _kinds(display: str, reading: str) -> frozenset:
    """Conjugation classes from the word's parts of speech. A word listed in
    kana with no part of speech of its own (なる) borrows its kanji
    spelling's (成る): without it 先生になった was に+な+っ+た (MeCab
    comparison, 2026-10-14)."""
    fix = _kinds_fix().get((display, reading))
    if fix:
        return frozenset({fix})
    hit = meanings.lookup(display, reading)
    if (not hit or not _pos_kinds(hit)) and not _has_kanji(display):
        for alt in _other_spellings(display, reading):
            h = meanings.lookup(alt, reading)
            if h and _pos_kinds(h):
                hit = h
                break
    if not hit:
        return frozenset()
    return _pos_kinds(hit)


def _pos_kinds(hit) -> frozenset:
    pos = " ".join(p for p, _ in hit[1])
    out = set()
    if "Ichidan" in pos:
        out.add("v1")
    if "Godan" in pos:
        out.add("v5")
    if "Kuru" in pos:
        out.add("vk")
    if "i-adjective" in pos:
        out.add("adj-i")
    if "する verb" in pos:
        out.add("vsn")
    return frozenset(out)


# Same spelling, same JLPT level, several readings: the everyday one. (The
# frequency list's readings are UniDic's formal ones, e.g. 私 わたくし.)
PREFERRED_READING = {"私": "わたし", "一日": "いちにち"}


def _hira(s: str) -> str:
    return "".join(chr(ord(c) - 0x60) if 0x30A1 <= ord(c) <= 0x30F6 else c for c in s)


_KINDS_FIX = None


def _kinds_fix() -> dict:
    """(display, reading) → conjugation class for words whose meanings entry
    has none (kinds_fix.txt, built with MeCab by tools/build_kinds_fix.py)."""
    global _KINDS_FIX
    if _KINDS_FIX is None:
        import os
        _KINDS_FIX = {}
        try:
            with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "kinds_fix.txt"),
                      encoding="utf-8") as f:
                for line in f:
                    if line.strip() and not line.startswith("#"):
                        d, r, k = line.rstrip("\n").split("\t")[:3]
                        _KINDS_FIX[(d, r)] = k
        except OSError:
            pass
    return _KINDS_FIX


_KANA_OK = None


def _kana_ok() -> set:
    """(display, reading) of words listed with kanji that are usually written
    in kana (kana_ok.txt, built by tools/build_kana_ok.py from JMdict)."""
    global _KANA_OK
    if _KANA_OK is None:
        import os
        _KANA_OK = set()
        # + kana_usual.txt: words real text usually writes in kana (あきらめる,
        # ふもと), measured with MeCab over Tatoeba by tools/build_kana_usual.py
        for name in ("kana_ok.txt", "kana_usual.txt"):
            try:
                with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), name),
                          encoding="utf-8") as f:
                    for line in f:
                        if line.strip() and not line.startswith("#"):
                            d, r = line.rstrip("\n").split("\t")[:2]
                            _KANA_OK.add((d, r))
            except OSError:
                pass
    return _KANA_OK


# 〜す verbs that are just a godan verb's short causative: their passive is
# the short causative-passive (待たされた "was made to wait", 飲まされた,
# 泣かされた, 驚かされた). Real verbs of their own stay plain passives
# (飛ばされた, 減らされた, 生かされる, 任された). grammar_data uses it too.
SHORT_CAUSATIVE = {"待たす", "飲ます", "泣かす", "笑わす", "驚かす", "聞かす", "読ます", "食わす",
                   "黙らす", "立たす", "言わす", "歩かす", "働かす", "書かす", "行かす", "買わす",
                   "払わす", "作らす"}
_SU_READINGS = None


def _su_verb_readings() -> set:
    """Readings of the lexicon's 〜す verbs of their own (まかす, すます,
    めぐらす; not the SHORT_CAUSATIVE ones), so kana text of their passive
    isn't read as a short causative-passive."""
    global _SU_READINGS
    if _SU_READINGS is None:
        entries = [e for es in lexicon().values() for e in es]
        short = {r for _p, d, r in entries if d in SHORT_CAUSATIVE}
        _SU_READINGS = {r for _p, d, r in entries
                        if d.endswith("す") and r.endswith("す") and "v5" in kinds_of(d, r)} - short
    return _SU_READINGS


def lexicon() -> dict:
    """surface → [(priority, display, reading)], best first.

    Which word a spelling is when several share it (時 とき / じ, 方 かた /
    ほう): the lowest JLPT level first (the reading learners meet first),
    then the most frequent; PREFERRED_READING settles same-level ties."""
    global _LEX
    if _LEX is not None:
        return _LEX
    level: dict[tuple, int] = {}
    rank: dict[tuple, int] = {}
    forms: dict[tuple, set] = {}
    for r, (display, reading, _pmw, fs) in enumerate(freq_data.parser_rows()):
        rank.setdefault((display, reading), r)
        forms.setdefault((display, reading), set()).update([display] + fs)
    lists = jlpt_data.build_lists({})
    for li, lvl in enumerate(LEVELS):
        for display, reading in lists.get(lvl, []):
            level.setdefault((display, reading), li)
            forms.setdefault((display, reading), set()).update(
                [display] + jlpt_data.same_kanji_forms(display, reading))

    kana_ok = _kana_ok()
    _RARE_KANA.clear()
    _RANK.clear()
    lex: dict[str, list] = {}
    for (display, reading), fs in forms.items():
        # words usually written in kana (物 もの, 言う いう …) may match their
        # kana spelling although they're listed with kanji (kana_ok.txt)
        kanji_word = _has_kanji(display) and (display, reading) not in kana_ok
        # Our own list additions count as frequency-list words here: listing
        # たこ / いか / だし made したこと read し + たこ + と (2026-10-28).
        # ない stays a real word although Waller doesn't list it (it came
        # with the community words, removed 2026-11-03): as a rare kana word,
        # なくて lost its くて (じゃなくて, 何もすることがなくて).
        if ((display, reading) not in level or "ours" in jlpt_data.FLAGS.get((display, reading), ())) \
                and (display, reading) != ("ない", "ない") \
                and all(0x3041 <= ord(c) <= 0x309F for c in display):
            _RARE_KANA.add((display, reading))
        prio = (level.get((display, reading), 9),
                0 if PREFERRED_READING.get(display) == reading else 1,
                rank.get((display, reading), 99_999))
        for f in fs:
            if not f or (len(f) == 1 and not _has_kanji(f)):
                continue
            if f in ("彼の", "本の") and display in ("あの", "かの", "ほんの"):
                continue                  # 彼の is かれの, 本の is ほん + の (MeCab comparison)
            if not _has_kanji(f):
                # Script rule: a kanji word's kana spellings don't make kana
                # text that word; and kana only spells a word with that
                # reading (なんか isn't カボチャ).
                if kanji_word or _hira(f) != _hira(reading):
                    continue
            lex.setdefault(f, []).append((prio, display, reading))
        # Wider kana rule (owner 2026-10-17: "yes widen the kana rule"): a
        # kanji word may also match its hiragana reading (だれ, なに, はる,
        # つきあう, ことば), costed above real words in tokens() so particles
        # and words listed in kana keep winning. Two kana at least.
        if kanji_word and len(reading) >= 2 and all(0x3041 <= ord(c) <= 0x309F for c in reading) \
                and (display, reading) not in _KANA_NEVER \
                and (prio[0] <= 2 or prio[2] <= 5000):      # common words only (not 萌芽 ほうが, 操舵 そうだ)
            lex.setdefault(reading, []).append((prio, display, reading))
        # How common the word is, for tie-breaks in tokens(): its frequency
        # rank, or for a list word without one (日本 is listed にっぽん) the
        # rank its JLPT level stands for.
        _RANK[(display, reading)] = min(rank.get((display, reading), 99_999),
                                        _LEVEL_RANK.get(level.get((display, reading)), 99_999))
    _LEX = {s: sorted(v) for s, v in lex.items()}

    # Compound tiles (可能性, 日本語, 考え方, お客様, 私たち): read as one word
    # instead of 可能 + 性, but only the safe ones (_compound_ok), and only
    # spellings no list word has.
    extra: dict[str, list] = {}
    for display, reading, r, fs in freq_data.compound_rows():
        for f in [display] + list(fs):
            if f and f not in _LEX and _compound_ok(f, display, reading):
                extra.setdefault(f, []).append(((9, 1, r), display, reading))
    _CACHE.clear()
    _TOK_CACHE.clear()
    _COMPOUND_KEYS.clear()
    for f, v in extra.items():
        _LEX[f] = sorted(v)
        _COMPOUND_KEYS.update((d, r) for _p, d, r in v if d == f)
        for p, d, r in v:
            _RANK.setdefault((d, r), p[2])
    # Spellings the script rule drops but real text uses in one spot only:
    # the auxiliary みる after て (してみた; tokens() checks the て) and
    # 通り voiced after a noun (時間どおり, 予定どおり). Vocab test 2026-10-17.
    for spelling, (d, r) in _CONTEXT_SPELLINGS.items():
        hit = [e for e in _LEX.get(d, ()) if e[1:] == (d, r)]
        if hit:
            _LEX[spelling] = sorted(set(_LEX.get(spelling, [])) | {hit[0]})
    return _LEX


_NUMERALS = set("一二三四五六七八九十百千万億何")
_COUNTER_READING = {"年": "ねん", "日": "にち", "人": "にん", "時": "じ", "分": "ふん", "円": "えん", "回": "かい",
                    "度": "ど", "歳": "さい", "本": "ほん", "枚": "まい", "個": "こ", "台": "だい", "階": "かい"}
_COUNTERS = set("年月日時分秒人円割回度歳本枚個台冊階週匹頭杯件軒点番倍万千百十億")
_CONTEXT_SPELLINGS = {"みる": ("見る", "みる"), "どおり": ("通り", "とおり")}
_RANK: dict = {}
_LEVEL_RANK = {0: 800, 1: 1500, 2: 3900, 3: 6000, 4: 13400}   # N5 … N1 → frequency band (a parser tie-break; kept at 13400 when the N1 estimate moved to 13,800)


# (display, reading) of the compounds the parser reads whole. In the split
# they may not touch another kanji (tokens): 住人たち is 住人 + たち, not
# 住 + 人たち; 大学生活 is 大学 + 生活, not 大学生 + 活.
_COMPOUND_KEYS: set = set()

# Hiragana-only words from the frequency list alone or our own list
# additions (たこ, とが, たが, かに, はむ): they cost more per character, so したことがある is した + こと + が,
# not し + たこ + とが, and 妹はもう is は + もう (accuracy test 3, 2026-10-14).
_RARE_KANA: set = set()
# kanji words whose kana reading must never stand for them (filled from the evals)
_KANA_NEVER: set = {("指摘", "してき"), ("入る", "はいる"), ("足る", "たる"), ("理想", "りそう"), ("申す", "もうす")}
_COST_RARE_KANA = 1.2            # per character, words of up to 3 kana


_PARTICLE_END = set("やともはにでがをのへか")


def _compound_ok(surface: str, display: str, reading: str) -> bool:
    """Whether a compound tile's spelling may join the parser's dictionary
    (2026-10-13). The first try with every compound lost grammar: kana ones
    (なので, ですが, それら) and ones ending in a particle (今や, 二人とも)
    swallowed it, and potential verbs (行ける, 思える) hid the verb the
    grammar rules look for (学校に行ける → に + 行く = destination). Those
    stay split; kanji compounds, katakana words, お〜 nouns, 〜方, plurals
    (私たち) and さ-nouns (高さ) are read whole."""
    hira = [0x3041 <= ord(c) <= 0x309F for c in surface]
    if not _has_kanji(surface):
        # Katakana words (ホームページ) are fine; hiragana ones are the
        # function-word compounds.
        return not any(hira) and _hira(surface) == _hira(reading)
    if _has_kanji(display) and not _has_kanji(surface):
        return False                       # script rule, as above
    if surface[-1] in _PARTICLE_END:
        return False
    if hira[-1]:
        w = lookup_full(surface)           # (only the list words are in _LEX yet)
        if w and w[2] not in (None, "adj-i"):
            return False                   # 言える = 言う, potential
    return True


_KIND_CACHE: dict = {}
_POS_CACHE: dict = {}


def pos_text(display: str, reading: str) -> str:
    """The word's parts of speech as one string ("noun, する verb …"), or ""."""
    k = (display, reading)
    if k not in _POS_CACHE:
        hit = meanings.lookup(display, reading)
        _POS_CACHE[k] = " ".join(p for p, _ in hit[1]) if hit else ""
    return _POS_CACHE[k]


def kinds_of(display: str, reading: str) -> frozenset:
    k = (display, reading)
    if k not in _KIND_CACHE:
        _KIND_CACHE[k] = _kinds(display, reading)
    return _KIND_CACHE[k]


# ── conjugation rules ─────────────────────────────────────────────────────────
# (inflected ending, dictionary ending, types the inflected form may have,
#  type of the result). None among the "in" types = plain sentence text.

_RULES: list[tuple[str, str, frozenset, str]] = []


def _r(infl, base, ins, out):
    _RULES.append((infl, base, frozenset(ins), out))


SURF = None
_GODAN = {  # dictionary ending: a, i, e, o, te, ta
    "う": ("わ", "い", "え", "お", "って", "った"),
    "く": ("か", "き", "け", "こ", "いて", "いた"),
    "ぐ": ("が", "ぎ", "げ", "ご", "いで", "いだ"),
    "す": ("さ", "し", "せ", "そ", "して", "した"),
    "つ": ("た", "ち", "て", "と", "って", "った"),
    "ぬ": ("な", "に", "ね", "の", "んで", "んだ"),
    "ぶ": ("ば", "び", "べ", "ぼ", "んで", "んだ"),
    "む": ("ま", "み", "め", "も", "んで", "んだ"),
    "る": ("ら", "り", "れ", "ろ", "って", "った"),
}
for u, (a, i, e, o, te, ta) in _GODAN.items():
    _r(te, u, {SURF, "te"}, "v5")
    _r(ta, u, {SURF}, "v5")
    _r(i + "ます", u, {SURF, "masu"}, "v5")
    _r(a + "ない", u, {SURF, "adj-i"}, "v5")
    _r(i + "たい", u, {SURF, "adj-i"}, "v5")
    _r(o + "う", u, {SURF}, "v5")
    _r(e + "ば", u, {SURF}, "v5")
    _r(e, u, {SURF}, "v5")                     # imperative 書け
    _r(e + "る", u, {SURF, "v1"}, "v5")        # potential 書ける
    _r(a + "れる", u, {SURF, "v1"}, "v5")      # passive 書かれる
    _r(a + "せる", u, {SURF, "v1"}, "v5")      # causative 書かせる
    if u not in ("す", "ぬ"):                   # (す verbs only take させられる; 死なされる
                                                #  is rare, なされる honorific common)
        _r(a + "される", u, {SURF, "v1"}, "v5")  # short causative-passive 歌わされる (last resort: lookup_full)
    _r(a + "ず", u, {SURF}, "v5")
    _r(i, u, {SURF}, "v5")                     # stem 書き(ながら)
# honorific -aru verbs take い before ます: いらっしゃいます, おっしゃいます,
# くださいます, なさいます, ございます (recall test 3)
for end in ("ゃ", "さ", "ざ"):
    _r(end + "います", end + "る", {SURF, "masu"}, "v5")
# 行く: 行って / 行った (checked in _valid)
_r("って", "く", {SURF, "te"}, "v5-iku")
_r("った", "く", {SURF}, "v5-iku")

for infl in ("た", "ます", "ない", "たい", "よう", "れば", "ろ", "られる", "させる",
             "ず", ""):
    ins = {SURF}
    if infl == "ます":
        ins.add("masu")
    elif infl in ("ない", "たい"):
        ins.add("adj-i")
    elif infl in ("られる", "させる"):
        ins.add("v1")
    _r(infl, "る", ins, "v1")
_r("て", "る", {SURF, "te"}, "v1")

for infl in ("した", "します", "しない", "したい", "しよう", "すれば", "しろ", "せよ", "し",
             "される", "させる", "せず", "さない"):
    ins = {SURF}
    if infl == "します":
        ins.add("masu")
    elif infl in ("しない", "したい", "さない"):
        ins.add("adj-i")
    elif infl in ("される", "させる"):
        ins.add("v1")
    _r(infl, "する", ins, "vs")
_r("して", "する", {SURF, "te"}, "vs")
_r("する", "", {SURF, "vs"}, "vsn")           # 勉強する → 勉強

for k in ("く", "来"):
    stem_i, stem_o = ("き", "こ") if k == "く" else ("来", "来")
    for infl, ins in ((stem_i + "た", {SURF}), (stem_i + "て", {SURF, "te"}),
                      (stem_i + "ます", {SURF, "masu"}), (stem_o + "ない", {SURF, "adj-i"}),
                      (stem_o + "よう", {SURF}), ("来れば" if k == "来" else "くれば", {SURF}),
                      (stem_o + "い", {SURF}), (stem_i + "たい", {SURF, "adj-i"})):
        _r(infl, "来る" if k == "来" else "くる", ins, "vk")

# 〜たら conditional: 行ったら, 読んだら, 食べたら, したら, 来たら, 高かったら
for u, (_a, _i, _e, _o, _te, ta) in _GODAN.items():
    _r(ta + "ら", u, {SURF}, "v5")
_r("ったら", "く", {SURF}, "v5-iku")
_r("たら", "る", {SURF}, "v1")
_r("したら", "する", {SURF}, "vs")
_r("きたら", "くる", {SURF}, "vk")
_r("来たら", "来る", {SURF}, "vk")
_r("かったら", "い", {SURF}, "adj-i")

for infl, ins in (("かった", {SURF}), ("くて", {SURF, "te"}), ("くない", {SURF, "adj-i"}),
                  ("く", {SURF}), ("ければ", {SURF}), ("さ", {SURF}), ("そう", {SURF}),
                  ("すぎる", {SURF, "v1"}), ("かろう", {SURF}), ("き", {SURF}),
                  ("がる", {SURF, "v5"}),     # 欲しがる, 怖がって (was 欲 + し + がる; grammar recall test 10)
                  # 行かなくちゃ, 行かなくっちゃ, 行かなきゃ (vocab test 2026-10-17)
                  ("くちゃ", {SURF}), ("くっちゃ", {SURF}), ("きゃ", {SURF})):
    _r(infl, "い", ins, "adj-i")

# Verb stem + すぎる / がたい / にくい / やすい / づらい is one verb (しすぎる
# was しい, 耐えがたき 耐える + たい; vocab test 2026-10-17)
for aux, out_ins in (("すぎる", {SURF, "v1"}), ("がたい", {SURF, "adj-i"}), ("にくい", {SURF, "adj-i"}),
                     ("やすい", {SURF, "adj-i"}), ("づらい", {SURF, "adj-i"})):
    for u, (_a, i, _e, _o, _te, _ta) in _GODAN.items():
        _r(i + aux, u, out_ins, "v5")
    _r(aux, "る", out_ins, "v1")
    _r("し" + aux, "する", out_ins, "vs")
# 罰せられる, 罰せず: a する verb written whole (罰する, 愛する); _valid
_r("せられる", "する", {SURF, "v1"}, "vs")

# 〜なさい (寝なさい, 読みなさい, しなさい): MeCab comparison 2026-10-14
for u, (_a, i, _e, _o, _te, _ta) in _GODAN.items():
    _r(i + "なさい", u, {SURF}, "v5")
_r("なさい", "る", {SURF}, "v1")
_r("しなさい", "する", {SURF}, "vs")
_r("きなさい", "くる", {SURF}, "vk")
_r("来なさい", "来る", {SURF}, "vk")

# auxiliaries that keep the verb's own form
_r("ました", "ます", {SURF}, "masu")
_r("ません", "ます", {SURF}, "masu")
_r("ませんでした", "ます", {SURF}, "masu")
_r("まして", "ます", {SURF, "te"}, "masu")
_r("ましょう", "ます", {SURF}, "masu")
_r("ましたら", "ます", {SURF}, "masu")           # 出版されましたら (vocab test 2)
_r("ている", "て", {SURF, "v1"}, "te")
_r("でいる", "で", {SURF, "v1"}, "te")
_r("てる", "て", {SURF, "v1"}, "te")
_r("でる", "で", {SURF, "v1"}, "te")
_r("ちゃう", "て", {SURF, "v5"}, "te")
_r("じゃう", "で", {SURF, "v5"}, "te")
_r("ておく", "て", {SURF, "v5"}, "te")
_r("とく", "て", {SURF, "v5"}, "te")

_BY_END: dict[str, list] = {}
for rule in _RULES:
    _BY_END.setdefault(rule[0][-1:] if rule[0] else "", []).append(rule)

_FITS = {"v1": "v1", "v5": "v5", "v5-iku": "v5", "vk": "vk", "adj-i": "adj-i", "vsn": "vsn"}


def _deinflect(text: str) -> list[tuple[str, str, tuple]]:
    """(dictionary form, its type, the endings undone in order from the
    surface) candidates for text, plain text first."""
    out = [(text, None, ())]
    seen = {(text, None)}
    queue = [(text, None, 0, ())]
    while queue:
        form, typ, depth, path = queue.pop()
        if depth >= 5:
            continue
        for end in {form[-1:], ""}:
            for infl, base, ins, out_t in _BY_END.get(end, ()):
                if not form.endswith(infl) or (typ not in ins):
                    continue
                stem = form[:len(form) - len(infl)] if infl else form
                if not stem and out_t not in ("vs", "vk"):   # 来た / きた are all ending
                    continue
                new = stem + base
                if not new or (new, out_t) in seen:
                    continue
                seen.add((new, out_t))
                out.append((new, out_t, path + (infl,)))
                queue.append((new, out_t, depth + 1, path + (infl,)))
    return out


def _valid(base: str, typ, display: str, reading: str) -> bool:
    if typ is None:
        return True
    if typ in ("te", "masu"):
        return False   # an unfinished chain
    if typ == "vs":
        # する itself, or a word that ends in it (罰する, 関する: 罰せられる, 関して)
        # (not 決する / 欲する: 決して is the adverb, 欲しい the adjective)
        return display in ("する", "為る") or (base == display and len(display) > 2
                                                and display.endswith("する") and _has_kanji(display[:-2])
                                                and display not in ("決する", "欲する"))
    if typ == "v5-iku":
        return base.endswith(("行く", "いく", "逝く"))
    need = _FITS.get(typ)
    return bool(need) and need in kinds_of(display, reading)


def _bad_chain(display: str, path: tuple) -> bool:
    """Ending chains that look valid but aren't (grammar recall test 10):
    行く's て / た forms are 行って / 行った only (the plain godan く rule of
    書いて made いいとき into 行く + とく), and とき after a word is "when"."""
    if path[:2] == ("き", "とく") or path[:2] == ("ぎ", "どく"):
        return True     # a bare stem of the casual とく (いとき = いておき) is とき "when": 悪いとき, いいとき
    return display in ("行く", "いく", "逝く", "往く") and any(p in ("いて", "いた", "いたら", "いたり") for p in path)


_CACHE: dict[str, tuple] = {}


def lookup_full(text: str):
    """(display, reading, type, endings undone) of the word this text is,
    or None. type is None for an unconjugated word."""
    if text in _CACHE:
        return _CACHE[text]
    lex = lexicon()
    best = None
    for base, typ, path in _deinflect(text):
        for prio, display, reading in lex.get(base, ()):
            if _valid(base, typ, display, reading) and not _bad_chain(display, path):
                # The word actually spelled this way beats one that merely
                # lists it as an alternate spelling (家 is いえ, not 内 うち;
                # 始めて is 始める, not 初めて); then plain over conjugated,
                # then fewer endings undone: 立てて is 立てる, not the potential
                # of 立つ; 整えて 整える, not 整う (vocab test 2026-10-17).
                # A godan potential (付けた as 付く + ける) is the last resort:
                # any real word wins, even one listed in kana (つける).
                pot = typ in ("v5", "v5-iku") and bool(path) and len(path[-1]) == 2                     and path[-1][1] == "る" and path[-1][0] in "えけげせてねべめれ"
                # (not against an adjective that merely lists the spelling:
                # 行けなかった is 行く, not いけない spelled 行けない)
                pot = pot or (typ == "adj-i" and display != base)
                # The short causative-passive (歌わされた → 歌う) likewise: a real
                # 〜す verb's passive wins (飛ばされた is 飛ばす, 減らされた 減らす)
                short_cp = typ == "v5" and bool(path) and len(path[-1]) == 4 and path[-1].endswith("される")
                if short_cp and base[:-1] + path[-1][0] + "す" in _su_verb_readings():
                    continue    # kana まかされた is 任す (まかす), すまされない 済ます, not まく / 住む
                if display in ("なさる", "為さる", "いらっしゃる", "おっしゃる", "仰る", "くださる", "下さる"):
                    pot = False   # なされた is honorific なさる, not なす + される
                # A kanji word read from kana (wider kana rule) only when nothing
                # else fits: なれなかった is なる's potential, not 慣れる
                wide = _has_kanji(display) and not _has_kanji(text) and (display, reading) not in _kana_ok() \
                    and base not in _CONTEXT_SPELLINGS
                if short_cp:    # below even a kana-spelled kanji verb: まかされた is 任す
                    wide = pot = True
                cand = (wide, pot, display != base, typ is not None, len(path), prio, display, reading, typ, path)
                if best is None or cand[:8] < best[:8]:
                    best = cand
    res = best[6:] if best else None
    _CACHE[text] = res
    return res


def _latin(s: str) -> bool:
    """Only Latin letters, ASCII or full-width (DJ, ＤＪ)."""
    return bool(s) and all("a" <= c.lower() <= "z" or "ａ" <= c <= "ｚ" or "Ａ" <= c <= "Ｚ" for c in s)


_CLAUSE_START = set("、。，,．.！？!?…―「『（( 　")


def _phrase_only(display: str, reading: str) -> bool:
    """An interjection / set expression, not a noun or verb (しまった, いただきます)."""
    pos = pos_text(display, reading)
    return ("interjection" in pos or "expression" in pos) and "noun" not in pos and "verb" not in pos


def _as_verb(text: str):
    """lookup_full, but only readings as a conjugated verb (しまった → しまう)."""
    lex = lexicon()
    best = None
    for base, typ, path in _deinflect(text):
        if typ is None or typ == "adj-i":
            continue
        for prio, display, reading in lex.get(base, ()):
            if _valid(base, typ, display, reading) and not _bad_chain(display, path):
                cand = (display != base, prio, display, reading, typ, path)
                if best is None or cand[:2] < best[:2]:
                    best = cand
    return best[2:] if best else None


def lookup(text: str):
    """(display, reading) of the word this text is (conjugated or not), or
    None."""
    w = lookup_full(text)
    return w[:2] if w else None


# Particles and grammatical endings: consumed by the segmenter so they can't
# be misread as words (ですか → "すか", だったんだ → "たん"); not counted as
# vocab. One that is also a list word (から, まで, でも) counts as that word.
# Particle pairs (には, では) aren't listed, so they split into their single
# particles for the grammar detection.
FUNCTION_TOKENS = set("""
は が を に で と も へ や の か ね よ な わ ぞ さ ば て し ず
って から まで より だけ しか ほど など けど けれど けれども のに ので ばかり
でも ても とか なら たら たり だら ながら つつ こそ さえ すら ずつ ごろ
だ です でした だった だろう でしょう でしょ だって じゃ じゃない ではない じゃん
んだ んです のだ のです ます ました ません ましょう ない なかった た たい ん
れる られる せる させる ちゃ ちゃった てる てた ている ていた いる
みたい
ように ような
もんだ もんです
べき すべき っぱなし どころ らしい らしく らしかった くらい ぐらい がてら
""".split())

_COST_KANJI_WORD = 1.0
_COST_KANA_WORD = {2: 1.6}       # longer kana words: 1.2
_COST_KANA_SPELLING = {2: 1.8}   # a kanji word written in kana (wider kana rule); longer: 1.3
_COST_FUNCTION = 1.1
_COST_UNKNOWN = 2.5              # per character no word covers

# A token of a split sentence:
#   (surface, kind, display, reading, type, endings undone)
# kind: "word" (a dictionary word), "func" (a particle / ending that isn't a
# list word), "lone" (a single kanji stuck to other kanji: not counted),
# "punct" (space / punctuation), "unk" (a character nothing covers).
_TOK_CACHE: dict[str, list] = {}


def tokens(text: str) -> list[tuple]:
    """The sentence split into tokens (see above).

    The whole sentence is split at once, picking the cheapest split: words
    and function tokens cost about one each (short kana words a bit more,
    since they're the likeliest misreadings), and every character nothing
    covers costs extra. So the split that explains the most text with the
    fewest, most solid pieces wins."""
    if text in _TOK_CACHE:
        return _TOK_CACHE[text]
    n = len(text)
    # (cost, pieces, tie-break, back): see the tie-break below
    best = [(0.0, 0, 0.0, None)] + [(float("inf"), 0, 0.0, None)] * n
    for i in range(n):
        cost_i, pieces_i, tie_i, _ = best[i]
        if cost_i == float("inf"):
            continue
        c = text[i]
        # Skip one character: free for spaces/punctuation/digits (and the
        # katakana middle dot ・), else costly.
        skip = 0.0 if not (is_kanji(c) or 0x3040 <= ord(c) <= 0x30FF or c == "々") or c == "・" else _COST_UNKNOWN
        if (round(cost_i + skip, 6), pieces_i, tie_i) < best[i + 1][:3]:
            best[i + 1] = (round(cost_i + skip, 6), pieces_i, tie_i, (i, None))
        for L in range(1, min(MAX_LEN, n - i) + 1):
            s = text[i:i + L]
            w = lookup_full(s) if (L > 1 or is_kanji(s)) else None
            # ... but only when that kanji really belongs to a word with the
            # compound's edge (住人, 生活); 以上僕らと is 以上 + 僕ら
            # (vocab test 2026-10-17)
            if w and (w[0], w[1]) in _COMPOUND_KEYS and (
                    (i > 0 and is_kanji(text[i - 1]) and lookup_full(text[i - 1:i + 1]))
                    or (i + L < n and is_kanji(text[i + L]) and lookup_full(text[i + L - 1:i + L + 1]))):
                w = None
            # において / における: に + おいて (におい "smell" + て is never right)
            if w and s == "におい" and text.startswith(("て", "た"), i + L):
                w = None
            # そこでの, それでの, ではの: そこ + で + の
            if w and s in ("そこで", "それで", "では") and text.startswith("の", i + L):
                w = None
            # 夢みたい is 夢 + みたい ("like a dream"), not 夢見る written
            # with a kana み + たい (Gemini pass 1, 2026-10-14).
            # 今日は is the greeting こんにちは only on its own (今日は出かけない is
            # 今日 + は; recall test 2026-10-14)
            if w and w[0] == "こんにちは" and s == "今日は" and i + L < n \
                    and (is_kanji(text[i + L]) or 0x3040 <= ord(text[i + L]) <= 0x30FF):
                w = None
            # A set phrase that is also a conjugated verb (しまった "oh no",
            # いただきます) is the verb inside a sentence: ケーキをしまった,
            # 紅茶を頂きます (recall test 3, 2026-10-14)
            if w and s in ("もんだ", "もんです"):
                w = None                  # ものだ, not もむ + んだ
            if w and w[2] is None and i > 0 and text[i - 1] not in _CLAUSE_START \
                    and _phrase_only(w[0], w[1]):
                w = _as_verb(s) or w
            if w and "見" in w[0] and "見" not in s and "み" in s and \
                    text.startswith("みたい", i + s.rfind("み")) and not (s[0] == "み" and i > 0 and text[i - 1] in "てで"):
                w = None
            # A set phrase with a particle inside (気をつける, 間に合う) can't
            # start inside a kanji compound: 電気をつけない is 電気 + を + つけない,
            # 谷間にあった is 谷間 + に + あった (recall test 5, 2026-10-16)
            # (の too: 彼女のこと was 彼 + 女の子 + と; vocab test 2026-10-17)
            if w and L >= 3 and i > 0 and is_kanji(s[0]) and is_kanji(text[i - 1]) \
                    and any(p in w[0][1:-1] for p in "をにがでの"):
                w = None
            # Wider kana rule: a kanji word's kana spelling can't start with a
            # particle's kana right after a word (彼氏はいる is は + いる, not
            # 入る; 病気になった に + なった; 戻るのかどうか か + どう). After
            # punctuation or another particle it can (切手をはる, 彼をしって).
            # And it only starts where a word can: after punctuation, a
            # particle, a て-form or an adverb's く (not なりそう → 理想).
            if w and _has_kanji(w[0]) and (w[0], w[1]) not in _kana_ok() and not _has_kanji(s) \
                    and s not in _CONTEXT_SPELLINGS and (w[0], w[1]) != ("見る", "みる"):
                nxt_c = text[i + L] if i + L < n else "。"
                if i > 0 and text[i - 1] not in _CLAUSE_START and (
                        text[i - 1] not in "をがにはもでとへのやてくら"
                        or s[0] in "はにがをでともかへやのし" and text[i - 1] not in "をがにはもでとへ"):
                    w = None
                elif s[0] == "た" and i > 0 and text[i - 1] == "く":
                    w = None                  # 高くたって: an adjective's くたって, not 立つ
                elif s.startswith("して"):
                    w = None                  # する's て-form (気がしてきた), not 指摘 / 私的
                elif any(s[:m] in FUNCTION_TOKENS for m in range(2, min(L, 4) + 1)) \
                        or any(text[i - 1:i + m] in FUNCTION_TOKENS for m in range(2, min(L, 4) + 1) if i > 0):
                    w = None                  # しかない is しか + ない (not 敷く); のでしょうか で + しょう
                elif s[0] in "はがをもへ" and i > 0 and text[i - 1] not in _CLAUSE_START and text[i - 1] not in "をが":
                    w = None                  # にはなれなかった: に + は + なれ (not 離れる)
                elif w[2] is None and not kinds_of(w[0], w[1]) & {"v1", "v5", "vk", "adj-i"} and not (
                        nxt_c in _CLAUSE_START or nxt_c in "はがをにでともへのやよねだ"):
                    w = None                  # 紙 + つかれた, 歌 + たね, 動詞 + たの, 人 + かどの:
                                              # a noun in kana ends at a particle
                elif w[2] is None and i > 0 and text[i - 1] == "を":
                    verb = next(((d, r) for _p, d, r in lexicon().get(s, ())
                                 if kinds_of(d, r) & {"v1", "v5"}), None)
                    if verb:
                        w = verb + (None, ())  # 切手をはる: 貼る, not 春
            # The context-only spellings (lexicon): みる only right after て/で
            # (してみた, 読んでみる), どおり only after a word (時間どおり)
            if w and s.startswith("み") and (w[0], w[1]) == ("見る", "みる") \
                    and not (i > 0 and text[i - 1] in "てで"):
                w = None
            if w and s == "どおり" and not (i > 0 and (is_kanji(text[i - 1]) or _is_kata(text[i - 1]))):
                w = None
            # この間違い is この + 間違い, not この間 + 違い; その後悔 その + 後悔
            if w and L >= 2 and not is_kanji(s[0]) and is_kanji(s[-1]) and i + L < n                     and any(lookup_full(text[i + L - 1:i + L - 1 + k]) for k in (2, 3)
                            if i + L - 1 + k <= n and is_kanji(text[i + L])
                            or (k == 3 and i + L + 1 < n and 0x3041 <= ord(text[i + L]) <= 0x309F)):
                w = None
            # ですかね / ますかね: か + ね, not かねる
            if w and s == "かね" and text[max(0, i - 2):i] in ("です", "ます", "でし", "まし"):
                w = None
            # １００万人 is 万 + 人, not 万人 ばんじん "all people"
            if w and L >= 2 and s[0] in "十百千万億" and i > 0 and text[i - 1].isdigit():
                w = None
            # A noun that is also a verb's stem, before a comma after a
            # particle, is the verb: 家から離れ、 / 学校へ行き、 / と感じ、
            # (owner 2026-10-14: 行き、 read as the noun; vocab test 2026-10-17)
            if w and w[2] is None and i > 0 and text[i - 1] in "をがにへとでらもは" \
                    and i + L < n and text[i + L] in "、，," and _has_kanji(s):
                v = _as_verb(s)
                if v and len(v[3]) == 1 and v[3][0] in ("", "い", "き", "ぎ", "し", "ち", "に", "び", "み", "り"):
                    w = v
            # Noun + 的 (個性的, 内向的): one word, the noun's (not 個 + 性的)
            if not w and L >= 3 and s[-1] == "的" and all(is_kanji(c) for c in s):
                base = lookup_full(s[:-1])
                if base and base[2] is None and "noun" in pos_text(base[0], base[1]):
                    w = base
            tie = 0.0
            if w:
                cost = (_COST_KANJI_WORD if _has_kanji(s)
                        else _COST_KANJI_WORD if (w[0], w[1]) in _kana_ok()   # もの, いう: real words
                        else _COST_KANA_SPELLING.get(L, 1.3) if _has_kanji(w[0])   # wider kana rule
                        else _COST_KANA_WORD.get(L, 1.2))
                if L <= 3 and (w[0], w[1]) in _RARE_KANA:
                    cost = max(cost, _COST_RARE_KANA * L)
                if s in FUNCTION_TOKENS:
                    cost = min(cost, _COST_FUNCTION)
                # An adverb ending in a particle (単に, 別に) doesn't start
                # inside a compound: 簡単に is 簡単 + に, 無分別に 無 + 分別 + に
                if L >= 2 and s[-1] in "にと" and is_kanji(s[0]) and i > 0 and is_kanji(text[i - 1])                         and lookup_full(text[i - 1:i + 1]):
                    cost += 0.2
                # A single kanji cut off from its okurigana is unlikely: 開いたそう
                # is 開いた + そう, not 開 + いたそう (vocab test 2026-10-17)
                if L == 1 and i + 2 <= n and 0x3041 <= ord(text[i + 1]) <= 0x309F:
                    for k in (2, 3):
                        ok = lookup_full(text[i:i + k]) if i + k <= n else None
                        if ok and ok[2] is not None:
                            cost += 0.7
                            break
                # Exact ties between equally solid splits go to the more
                # common kanji words: 外国語 is 外国 + 語, not 外 + 国語; 西日本
                # 西 + 日本, not 西日 + 本; 歩行者 歩行 + 者 (vocab test
                # 2026-10-17). Kept apart from the cost so it can't move any
                # other decision (kana ties keep their old order).
                # (a kana word counts as rare, so 開いた + そう beats 開 + いたそう)
                tie = math.log10(_RANK.get((w[0], w[1]), 99_999) + 10) if _has_kanji(s) else 5.0
            elif s in FUNCTION_TOKENS:
                cost = _COST_FUNCTION
                w = "func"
            else:
                continue
            cand = (round(cost_i + cost, 6), pieces_i + 1, tie_i + tie)   # rounded: equal costs must tie exactly
            if cand < best[i + L][:3]:
                best[i + L] = cand + ((i, w),)
    out = []
    j = n
    while j > 0:
        i, w = best[j][3]
        s = text[i:j]
        if w == "func":
            out.append((s, "func", s, s, None, ()))
        elif w:
            # A single kanji stuck to other kanji (家 in 建築家, 期 in 死期,
            # 露 in the name 露伴) is part of a compound or name we don't
            # know: it's consumed but not counted, so it can't credit the
            # wrong word.
            lone = (j - i == 1 and ((i > 0 and is_kanji(text[i - 1]))
                                    or (j < n and is_kanji(text[j]))))
            if lone and s == "何" and not (i > 0 and is_kanji(text[i - 1])):
                lone = False              # 何日, 何人, 何回: 何 + a counter
            if lone and s in "十百千万億" and i > 0 and text[i - 1].isdigit():
                lone = False              # １００万人: 万 + 人
            if lone and ((s in _NUMERALS and j < n and text[j] in _COUNTERS)
                         or (s in _COUNTERS and i > 0 and (text[i - 1] in _NUMERALS or text[i - 1].isdigit()))):
                lone = False              # 三年前, 六万円, 六割: a numeral and its counter (not 万端)
            if s in _COUNTER_READING and i > 0 and (text[i - 1] in _NUMERALS or text[i - 1].isdigit()):
                r = _COUNTER_READING[s]
                if any(e[1:] == (s, r) for e in lexicon().get(s, ())):
                    w = (s, r) + tuple(w[2:])   # １９９１年 ねん, 三人 にん, 何日 にち
            if s == "月" and w[1] != "つき" and not (i > 0 and (text[i - 1].isdigit() or text[i - 1] in _NUMERALS
                                                                or text[i - 1] in "毎先今来")):
                w = ("つき", "つき") + tuple(w[2:])   # 月に六万円 (not 三月 / 毎月)
            if w[:2] == ("方", "かた") and _hoagain(text, i, j):
                w = ("方", "ほう") + tuple(w[2:])
            if s == "他" and not lone:
                w = ("ほか", "ほか") + tuple(w[2:])   # 他に, 他の: ほか (た only in compounds)
            out.append((s, "lone" if lone else "word") + tuple(w))
        else:
            kana_or_kanji = is_kanji(s) or s == "々" or (0x3040 <= ord(s) <= 0x30FF and s != "・")
            out.append((s, "unk" if kana_or_kanji or _latin(s) else "punct", "", "", None, ()))
        j = i
    out.reverse()
    # A run of katakana nothing covers is one unknown piece (a name: トム),
    # not one token per character (recall test 2026-10-14)
    # Latin letters are one piece too (ＤＪ, CD: a name-like word, so 彼はＤＪです
    # still has a word before です; recall test 3)
    merged = []
    for t in out:
        if t[1] == "unk" and merged and merged[-1][1] == "unk" and (all(
                0x30A1 <= ord(c) <= 0x30FA or c == "ー" for c in merged[-1][0] + t[0])
                or _latin(merged[-1][0] + t[0])):
            merged[-1] = (merged[-1][0] + t[0],) + merged[-1][1:]
        else:
            merged.append(t)
    out = _merge_katakana_names(merged)
    _TOK_CACHE[text] = out
    return out


def _hoagain(text: str, i: int, j: int) -> bool:
    """Whether a lone 方 is ほう "side / rather" (話さない方がいい, 早い方, 私の
    方), not かた "person / way" (あの方, 読み方). Vocab test 2026-10-17."""
    if i > 0 and text[i - 1] in "たるいのな" and not text[max(0, i - 2):i] in ("この", "その", "あの", "どの"):
        return True
    return bool(re.match(r"[がは](?:いい|よい|良い|まし|楽)", text[j:]))


def _is_kata(s: str) -> bool:
    return bool(s) and all(0x30A1 <= ord(c) <= 0x30FA or c == "ー" for c in s)


def _merge_katakana_names(toks: list) -> list:
    """A katakana run split into pieces, one of them unknown or only one or
    two letters long, is one unknown name: スティーブ was ス + ティー + ブ,
    メアリー メ + アリ + ー, ベルリン ベル + リン (recall test 5, 2026-10-16).
    Runs that split into longer words (テニス + コート) stay split."""
    out = []
    i = 0
    while i < len(toks):
        j = i
        while j < len(toks) and toks[j][1] in ("word", "unk", "lone") and _is_kata(toks[j][0]):
            j += 1
        run = toks[i:j]
        if len(run) >= 2 and any(t[1] == "unk" or len(t[0].replace("ー", "")) <= 2 for t in run):
            out.append(("".join(t[0] for t in run), "unk", "", "", None, ()))
            i = j
        elif run:
            out.extend(run)
            i = j
        else:
            out.append(toks[i])
            i += 1
    return out


def words_in(text: str) -> list[tuple[str, str, str]]:
    """[(surface, display, reading)] of the dictionary words in a sentence."""
    return [(t[0], t[2], t[3]) for t in tokens(text) if t[1] == "word"]


# ── sentence-card word cache ──────────────────────────────────────────────────
# A sentence card's vocab is every word the parser finds in it. Parsing a
# 30k deck's sentence cards takes ~12 s the first time in an Anki session
# (speed report 2026-10-17), so the words per sentence text are kept on disk
# like the grammar parse cache: same signature (the add-on's code + bundled
# data files), so a parser fix or an add-on update throws it away. Only the
# sentences of the last scan are kept, so edited or deleted ones drop out.

def _words_cache_path() -> str:
    import os
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "user_files", "words_cache.json")


_wcache: dict | None = None   # {"sig": str, "words": {text: [[display, reading], …]}}


class SentenceWords:
    """One deck scan's words per sentence: .get(text) parses only what the
    cache doesn't have; .save() writes the cache if anything changed."""

    def __init__(self):
        global _wcache
        from .grammar_data import _parse_sig
        self._sig = _parse_sig()
        if _wcache is None or _wcache.get("sig") != self._sig:
            try:
                import json
                with open(_words_cache_path(), encoding="utf-8") as f:
                    _wcache = json.load(f)
            except Exception:
                _wcache = {}
            if not isinstance(_wcache, dict) or _wcache.get("sig") != self._sig:
                _wcache = {"sig": self._sig, "words": {}}
        self._cached = _wcache["words"]
        self._fresh: dict = {}

    def get(self, text: str) -> list:
        w = self._fresh.get(text)
        if w is None:
            w = self._cached.get(text)
            if w is None:
                w = [[d, r] for _s, d, r in words_in(text)]
            self._fresh[text] = w
        return w

    def save(self):
        global _wcache
        if self._fresh == self._cached:
            return
        _wcache = {"sig": self._sig, "words": self._fresh}
        try:
            import json, os
            path = _words_cache_path()
            os.makedirs(os.path.dirname(path), exist_ok=True)
            tmp = path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(_wcache, f, ensure_ascii=False, separators=(",", ":"))
            os.replace(tmp, path)
        except Exception:
            pass   # a cache that can't be written just means a slower scan
