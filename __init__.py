"""
Kotodama 言霊 — JLPT Progress & Rank Tracker (Anki add-on)  v3.0.1

Matching strategy:
  Step 1. Exact match on display form in card's primary field (or one of
          the list's alternate spellings).
  Step 2. Kana-only card: JLPT reading appears in primary field.
  Step 3. Reading field: JLPT reading appears in card's dedicated kana field —
          BUT only when that reading is UNIQUE across all JLPT lists.
  Step 4. Honorific prefix: JLPT お/ご+kanji entry matches the bare-root card
          (soft match — the nid is not claimed, so the bare entry can match too).

  Additionally:
  - "Marked as found" words (middle-clicked by user) count as known even
    if they are not in the deck.
  - "Suspended" words are removed from all JLPT level lists before analysis.

Counting guarantee: a note is claimed by at most one list entry per reading;
it can also count for the same word listed twice (挨拶 at N4 and N3) or for
one entry per reading (明日 あした / あす) — soft matches, APP_VISION §5. A
note on no list is Off-list unless it duplicates a counted JLPT word.
"""

from __future__ import annotations

import html as _html
import re
import unicodedata
from collections import Counter
from aqt import mw
from aqt.qt import *
from aqt.utils import showWarning

from . import card_state
from . import jlpt_data
from . import freq_data
from . import history
from . import mini_widget
from . import rank_toast
from .config_dialog import ConfigDialog
from .progress_dialog import ProgressDialog
from .jlpt_data import LEVELS
from .overrides import Overrides


# ── config helpers ─────────────────────────────────────────────────────────────

def _cfg() -> dict:
    return mw.addonManager.getConfig(__name__) or {}

def _save(cfg: dict):
    mw.addonManager.writeConfig(__name__, cfg)


# Moving from a shared copy (folder jlpt_progress) to the AnkiWeb version:
# bring its user_files and settings over once, before anything reads them
# (migrate.py, owner 2026-10-20).
def _import_old_copy():
    import os
    from aqt import gui_hooks
    from . import migrate
    try:
        moved = migrate.import_old_copy(os.path.dirname(os.path.abspath(__file__)), mw.addonManager)
    except Exception:
        return
    if not moved:
        return

    def tell(*_args):
        from aqt.utils import showInfo
        showInfo("Kotodama: your data from the earlier copy of the add-on (found words, history, "
                 "settings, Nakama) was moved to this version, and the old copy was turned off. "
                 "Restart Anki to finish.", title="Kotodama")
        gui_hooks.profile_did_open.remove(tell)
    gui_hooks.profile_did_open.append(tell)


_import_old_copy()


# The mini widget (Anki's main-screen web view) plays the animated rank
# pictures from media/, served at /_addons/<folder>/media/… (owner 2026-10-16).
try:
    mw.addonManager.setWebExports(__name__, r"media/.+\.webm")
except Exception:
    pass


# ── text normalisation ─────────────────────────────────────────────────────────

def _norm(s: str) -> str:
    return unicodedata.normalize("NFKC", s).strip()


def _extract_words(raw: str) -> list[str]:
    s = re.sub(r"<[^>]+>", "", raw)
    s = _html.unescape(s)            # 猫&nbsp; (Anki's editor adds them) → 猫
    s = re.sub(r"\[.*?\]", "", s)
    s = re.sub(r"[（(].*?[)）]", "", s)
    parts = re.split(r"[/／、,，・\s]+", s)
    return [_norm(p) for p in parts if p.strip()]


def _extract_reading(raw: str) -> str:
    """Extract a plain-kana reading from a field that may contain furigana markup.

    Handles the three common formats users employ for in-card furigana display:

      1. Plain kana          "ごちそう"          → "ごちそう"
      2. Anki bracket format "ご馳走[ちそう]"    → "ごちそう"
         Each kanji run is optionally followed by [reading]; hiragana/katakana
         prefix/suffix characters are kept as-is.
      3. HTML ruby markup    "ご<ruby>馳走<rt>ちそう</rt></ruby>"
                                                 → "ごちそう"

    Returns a single normalised string, or "" if nothing kana-like is found.
    """
    s = _norm(raw.strip())

    # ── format 3: HTML ruby — pull <rt>…</rt> text, discard the kanji inside
    # <ruby>…</ruby>. We do this before any other stripping so the kanji
    # between <ruby> and <rt> doesn't bleed into the result.
    # e.g. "ご<ruby>馳走<rt>ちそう</rt></ruby>" → "ごちそう"
    def _ruby_to_kana(m):
        # m.group(0) is the full <ruby>…</ruby> block
        # Extract all <rt>…</rt> contents from inside it
        rt_texts = re.findall(r"<rt[^>]*>(.*?)</rt>", m.group(0), re.IGNORECASE)
        return "".join(rt_texts)

    s = re.sub(r"<ruby>.*?</ruby>", _ruby_to_kana, s, flags=re.IGNORECASE | re.DOTALL)

    # Strip any remaining HTML tags (e.g. <b>, <span>, etc.) and entities
    s = re.sub(r"<[^>]+>", "", s)
    s = _norm(_html.unescape(s))

    # ── format 2: Anki bracket furigana "漢字[かんじ]"
    # Strategy: walk through the string, collecting kana characters as-is and
    # replacing each kanji run (followed by optional "[reading]") with its
    # bracketed reading.  If a kanji run has no bracket we drop it (can't
    # recover the reading).
    result = []
    i = 0
    _KANA = re.compile(r"[\u3041-\u309F\u30A0-\u30FF\uFF66-\uFF9F]")  # hira+kata
    _KANJI = re.compile(r"[\u4E00-\u9FFF\u3400-\u4DBF\uF900-\uFAFF]")
    while i < len(s):
        c = s[i]
        if _KANA.match(c):
            # Plain kana — keep directly
            result.append(c)
            i += 1
        elif _KANJI.match(c):
            # Consume the kanji run
            j = i
            while j < len(s) and _KANJI.match(s[j]):
                j += 1
            # Check for a bracket reading immediately after
            m = re.match(r"\[([^\]]+)\]", s[j:])
            if m:
                result.append(m.group(1))
                i = j + len(m.group(0))
            else:
                # No bracket — drop the kanji (we can't infer the reading)
                i = j
        elif c in _READING_SEPS:
            # Separator between alternative readings (よん、し / なな/しち) —
            # keep it as "・" so the readings don't merge into one string.
            if result and result[-1] != "・":
                result.append("・")
            i += 1
        else:
            # Punctuation, spaces, Latin, etc. — skip
            i += 1

    reading = _norm("".join(result)).strip("・")

    # Fall back to the plain-stripped string if the bracket parser produced
    # nothing (e.g. the field was already plain kana to begin with, or used
    # a format we didn't recognise above).
    if not reading:
        plain = re.sub(r"\[.*?\]", "", s)
        plain = re.sub(r"[（(].*?[)）]", "", plain)
        reading = _norm(plain)

    return reading


# Characters that separate alternative readings in a single reading field.
_READING_SEPS = set("・、,，/／;；") | {" ", "　"}
_READING_SPLIT = re.compile(r"[・、,，/／;；\s　]+")


def _accepted_readings(display: str, reading: str) -> set[str]:
    """All readings (hiragana) a card may have to match this list entry: the
    entry's own reading plus the word's other readings from JMdict."""
    readings = [reading] + jlpt_data.alt_readings(display, reading)
    return {_kata_to_hira(_norm(r)) for r in readings if r}


def _reading_parts(reading: str) -> list[str]:
    """Split a reading field into its alternative readings:
    "なな・しち" → ["なな", "しち"]; a single reading → [reading]."""
    return [p for p in _READING_SPLIT.split(_norm(reading)) if p]


# ── kana utilities ─────────────────────────────────────────────────────────────

_K2H = {c: c - 0x60 for c in range(0x30A1, 0x30F7)}     # ァ…ヶ → ぁ…ゖ (str.translate: fast)


def _kata_to_hira(s: str) -> str:
    """Convert katakana to hiragana. Non-katakana characters pass through unchanged."""
    return s.translate(_K2H)


def _readings_match(r1: str, r2: str) -> bool:
    """
    True when two readings are phonetically identical after normalising
    katakana -> hiragana.  Handles the meganE (hira) <-> megane (kata) case.
    """
    if not r1 or not r2:
        return False
    return _kata_to_hira(_norm(r1)) == _kata_to_hira(_norm(r2))


# ── honorific-o stripping ──────────────────────────────────────────────────────

_KANJI_RE = re.compile(r"[\u4E00-\u9FFF\u3400-\u4DBF]")


def _honorific_o_strip(display: str) -> str:
    """
    If `display` starts with a Japanese honorific prefix (お or ご) followed
    IMMEDIATELY by a kanji character, return the bare root without the prefix.
    Examples: お皿→皿, お酒→酒, ご馳走→馳走, ご飯→飯.
    Returns empty string if the pattern does not apply.

    Two honorific prefixes exist in Japanese:
      お (U+304A) — on-reading prefix, e.g. お皿, お酒, お金
      ご (U+3054) — kun-reading prefix, e.g. ご馳走, ご飯, ご存知

    Safety rule: these prefixes are only stripped when followed immediately by
    a kanji character. Phonetic words that begin with お or ご but consist
    entirely of kana (おとこ, おいしい, ごめん) are never stripped because
    position [1] is kana, not kanji.
    """
    nd = _norm(display)
    if len(nd) >= 2 and nd[0] in ("\u304A", "\u3054") and _KANJI_RE.match(nd[1]):
        return nd[1:]
    return ""


# ── build unique-reading set ───────────────────────────────────────────────────

def _build_unique_readings(lists: dict) -> set[str]:
    all_readings: list[str] = []
    for lvl in LEVELS:
        for display, reading in lists.get(lvl, []):
            r = _norm(reading)
            if r:
                all_readings.append(r)
    counts = Counter(all_readings)
    return {r for r, n in counts.items() if n == 1}


# ── deck scanning ──────────────────────────────────────────────────────────────

def collect_words(deck_name: str, field_mappings: list, ignore_suspended: bool = False,
                  seen_only: bool = True, duplicates: dict | None = None):
    """seen_only=False: never-studied notes too (only for new_card_words,
    the grids' "New" tiles; nothing counts them). `duplicates`, if given,
    is filled with {first nid: [nids]} for notes with the very same word and
    reading (sentence-card words don't count: a word card plus a sentence
    using it is no duplicate)."""
    from . import sentence_parser
    col = mw.col
    raw: list[tuple[int, str, str]] = []
    sentence_words: list[tuple[int, int, str, str]] = []   # (nid, index, display, reading)
    notes = card_state.deck_notes(deck_name, seen_only)
    parsed = None                     # sentence-card words, cached on disk
    for nid in col.find_notes(card_state.deck_search(deck_name, ignore_suspended, seen_only)):
        note = notes.get(nid)
        if note is None:
            continue
        model_name = note.type_name
        display = ""
        reading = ""
        for mapping in field_mappings:
            mapped_nt = mapping.get("note_type", "")
            if mapped_nt and mapped_nt != model_name:
                continue
            sentence_field = mapping.get("sentence_field", "")
            if (not mapping.get("field") and sentence_field and sentence_field in note
                    and not display):
                # No word field: every dictionary word in the sentence is
                # this card's vocab (the auto parser).
                if parsed is None:
                    parsed = sentence_parser.SentenceWords()
                for i, (d, r) in enumerate(parsed.get(sentence_parser.clean(note[sentence_field]))):
                    sentence_words.append((nid, i, d, r))
                break
            field_name = mapping.get("field", "")
            if field_name and field_name in note and not display:
                words = _extract_words(note[field_name])
                if words:
                    display = words[0]
            reading_field = mapping.get("reading_field", "")
            if reading_field and reading_field in note and not reading:
                # Use the furigana-aware extractor so formats like
                # "ご馳走[ちそう]" and "ご<ruby>馳走<rt>ちそう</rt></ruby>"
                # are reduced to their plain-kana reading "ごちそう".
                reading = _extract_reading(note[reading_field])
        if display:
            raw.append((nid, display, reading))
    if parsed is not None:
        parsed.save()

    if sentence_words:
        # The same word in many sentences counts once: keep the most mature
        # sentence card's copy (its id is note id × 1000 + word index).
        maturity = card_state.note_maturity(deck_name, ignore_suspended)
        sentence_words.sort(key=lambda w: -maturity.get(w[0], -1))
        raw += [(card_state.pseudo_nid(nid, i), d, r) for nid, i, d, r in sentence_words]

    seen_word_pairs: dict[tuple[str, str], int] = {}   # pair → first nid
    display_index:  dict[str, list[int]] = {}
    reading_index:  dict[str, list[int]] = {}
    nid_to_display: dict[int, str] = {}
    nid_to_reading: dict[int, str] = {}

    for nid, display, reading in raw:
        nd   = _norm(display)
        nr   = _norm(reading)
        pair = (nd, nr)
        if pair in seen_word_pairs:
            first = seen_word_pairs[pair]
            if (duplicates is not None and nid < card_state.PSEUDO_BASE
                    and first < card_state.PSEUDO_BASE):
                duplicates.setdefault(first, [first]).append(nid)
            continue
        seen_word_pairs[pair] = nid
        display_index.setdefault(nd, []).append(nid)
        for part in _reading_parts(nr):   # index each alternative reading
            reading_index.setdefault(part, []).append(nid)
        nid_to_display[nid] = display
        if reading:
            nid_to_reading[nid] = reading

    return display_index, reading_index, nid_to_display, nid_to_reading


# ── matching ───────────────────────────────────────────────────────────────────

def _find_match(jlpt_display: str, jlpt_reading: str,
                display_index: dict, reading_index: dict,
                nid_to_reading: dict, unique_readings: set,
                claimed_nids: set, kana_nids: set = frozenset(),
                nid_to_display: dict = None) -> tuple[int | None, bool]:
    """
    Returns (nid, soft) for the best unclaimed candidate, or (None, False).
    soft=True means the match came from the honorific-o step and the caller
    should NOT claim the nid.

    Script rule (design decision): a card written with kanji may count for a
    kana list entry (出来る card → できる), but a kana-only card never counts
    for a list entry written with kanji (やさしい card ↛ 易しい). Knowing a
    word's kana doesn't show you know its kanji spelling. kana_nids is the set
    of cards whose display is kana-only.

    Matching steps (in priority order):
      1. Exact display form match in primary field.
         1b. Same, using the list's alternate spellings (いちばん ↔ 一番),
             only those with the entry's own kanji (会う ↛ 遭う; see
             jlpt_data.same_kanji).
      2. Kana-only card: JLPT reading appears as the display form
         (kana list entries only, per the script rule).
      3. Reading field match (unique-reading guard).
      4. Honorific-o: JLPT display starts with o+kanji — try the bare root
         (e.g. JLPT has osara, user has sara in their deck).
      4b. Reverse honorific: list has 互い, card is お互い.
      5. Same word listed twice (N4 舟 / N3 船): counted again, soft.

    Kana script mismatches (same display, readings differ only in hiragana vs
    katakana, e.g. JLPT メガネ vs card めがね) are handled inside every step by
    _pick's phonetic comparison rather than as a separate step.

    Within any candidate list, prefer a candidate whose stored reading matches
    the JLPT reading phonetically (hira/kata-normalised), then fall back to any
    unclaimed candidate only when no candidate has a reading at all.
    """
    nd = _norm(jlpt_display)
    nr = _norm(jlpt_reading)
    accepted = _accepted_readings(jlpt_display, jlpt_reading)
    # Script rule: a kanji list entry can't be matched by a kana-only card.
    entry_has_kanji = bool(_KANJI_RE.search(nd))

    def _allowed(nids):
        if not entry_has_kanji:
            return list(nids)
        return [n for n in nids if n not in kana_nids]

    def _pick(nids: list[int]) -> int | None:
        """
        Choose the best unclaimed nid from the candidate list.

        Preference order:
          a) exact reading match (after NFKC norm)
          b) phonetic reading match (katakana->hiragana normalised)
          c) no-reading card (reading field blank) — safe fallback

        If every candidate has a reading and none of the above match,
        the candidate list is not a match for this JLPT entry — return None.
        """
        unclaimed = [n for n in _allowed(nids) if n not in claimed_nids]
        if not unclaimed:
            return None
        if nr:
            # A card's reading field may list several readings (なな・しち);
            # any one of them can match.
            # (a) exact
            for n in unclaimed:
                if nr in _reading_parts(nid_to_reading.get(n, "")):
                    return n
            # (b) phonetic (hiragana/katakana equivalence), or another
            #     reading of the same word (今日 きょう ↔ こんにち)
            for n in unclaimed:
                if any(_kata_to_hira(p) in accepted
                       for p in _reading_parts(nid_to_reading.get(n, ""))):
                    return n
            # (c) card has no reading at all — safe fallback
            no_reading = [n for n in unclaimed if not nid_to_reading.get(n)]
            if no_reading:
                return no_reading[0]
            # Every candidate has a different reading — not a real match
            return None
        return unclaimed[0]

    # ── Step 1: exact display match ───────────────────────────────────────────
    if nd and nd in display_index:
        match = _pick(display_index[nd])
        if match is not None:
            return match, False

    # ── Step 1b: alternate spelling from the list (e.g. いちばん → 一番) ──────
    for alt in jlpt_data.same_kanji_forms(jlpt_display, jlpt_reading):
        na = _norm(alt)
        if na in display_index:
            match = _pick(display_index[na])
            if match is not None:
                return match, False

    # ── Step 2: kana-only card (reading used as display) ─────────────────────
    if nr and nr != nd and nr in display_index:
        match = _pick(display_index[nr])
        if match is not None:
            return match, False

    # ── Step 3: reading-field match (unique-reading guard) ───────────────────
    #    The card must still use the entry's kanji: a 捕らえる card isn't
    #    捉える just because only one of them is on the lists.
    if nr and nr in reading_index and nr in unique_readings:
        cands = reading_index[nr]
        if entry_has_kanji and nid_to_display is not None:
            cands = [n for n in cands
                     if jlpt_data.counts_as(jlpt_display, _norm(nid_to_display.get(n, "")))]
        match = _pick(cands)
        if match is not None:
            return match, False

    # ── Step 4: honorific-o prefix (JLPT has o+kanji, user dropped the o) ───
    #    e.g. JLPT: おさら (N5), deck: 皿/さら. We match the bare card but do NOT
    #    claim the nid (soft=True) so that the bare JLPT entry (e.g. N3's 皿/さら)
    #    can also match the same card — both levels should count as known.
    bare = _honorific_o_strip(nd)
    if bare:
        bare_nr = nr[1:] if nr and nr[0] in ("\u304A", "\u3054") else nr
        bare_nr_hira = _kata_to_hira(bare_nr) if bare_nr else ""

        if bare in display_index:
            unclaimed = [n for n in display_index[bare] if n not in claimed_nids]
            if unclaimed:
                matched = None
                if bare_nr:
                    for n in unclaimed:
                        if bare_nr in _reading_parts(nid_to_reading.get(n, "")):
                            matched = n
                            break
                    if matched is None:
                        for n in unclaimed:
                            if any(_kata_to_hira(p) == bare_nr_hira
                                   for p in _reading_parts(nid_to_reading.get(n, ""))):
                                matched = n
                                break
                    if matched is None:
                        no_reading = [n for n in unclaimed if not nid_to_reading.get(n)]
                        if no_reading:
                            matched = no_reading[0]
                else:
                    matched = unclaimed[0]
                if matched is not None:
                    return matched, True   # soft: don't claim, let bare entry also match

    def _same_word(nids: list[int]) -> int | None:
        """First card among nids (claimed or not) whose reading is one of
        this entry's readings — i.e. the card IS this word."""
        for n in _allowed(nids):
            parts = _reading_parts(nid_to_reading.get(n, ""))
            if not parts or any(_kata_to_hira(p) in accepted for p in parts):
                return n
        return None

    # ── Step 4b: reverse honorific (list has 互い, card is お互い) ───────────
    if nd and not _honorific_o_strip(nd):
        for prefix in ("お", "ご"):   # お, ご
            cands = display_index.get(prefix + nd, [])
            unclaimed = [n for n in cands if n not in claimed_nids]
            match = _same_word(unclaimed) if nr else (unclaimed[0] if unclaimed else None)
            if match is None and nr:
                # Card's reading carries the prefix too (おたがい vs たがい).
                for n in unclaimed:
                    if any(_kata_to_hira(p) == _kata_to_hira(prefix + nr)
                           for p in _reading_parts(nid_to_reading.get(n, ""))):
                        match = n
                        break
            if match is not None:
                return match, False

    # ── Step 5: same word listed twice (N4 舟 ふね and N3 船 ふね) ───────────
    #    The card was already counted for the other entry; count it here too
    #    (soft, like the honorific step) instead of showing a known word as
    #    missing.
    for form in [nd] + [_norm(a) for a in jlpt_data.same_kanji_forms(jlpt_display, jlpt_reading)]:
        if form in display_index:
            match = _same_word(display_index[form])
            if match is not None:
                return match, True

    return None, False


# ── analysis ───────────────────────────────────────────────────────────────────

def analyse(display_index, reading_index, nid_to_display, nid_to_reading,
            lists, unique_readings, overrides: Overrides = None,
            exact_duplicates: dict | None = None) -> dict:
    """
    Each nid counted at most once. First level to claim a nid wins (N5→N1).
    results["duplicates"]: groups of notes that are one word (collect_words'
    exact copies + a second card for a counted JLPT word, かかる / 掛かる).

    Overrides applied before analysis:
      - suspended words are skipped entirely (not counted as known or missing)
      - found words with no deck match are injected as known (nid=None)
    """
    results      = {}
    claimed_nids = set()
    soft_nids    = set()   # matched via honorific-o only; excluded from unlisted
    # Readings already used per card. A card listing several readings
    # (何 "なに・なん") can match one JLPT entry per reading; it's only fully
    # claimed once every reading has been used.
    used_readings: dict[int, set[str]] = {}
    # Cards written without kanji — these may not count for kanji list
    # entries (see the script rule in _find_match).
    kana_nids = {nid for nid, d in nid_to_display.items() if not _KANJI_RE.search(_norm(d))}

    def _claim(nid: int, jlpt_display: str, jlpt_reading: str):
        parts = {_kata_to_hira(p) for p in _reading_parts(nid_to_reading.get(nid, ""))}
        used = used_readings.setdefault(nid, set())
        # Mark the one reading this entry used: its own reading if the card
        # lists it, otherwise the card's reading that matched an alternate.
        # (何 なん must only use なん, leaving なに for 何 なに.)
        own = _kata_to_hira(_norm(jlpt_reading))
        if own in parts:
            used.add(own)
        else:
            used |= set(sorted(parts & _accepted_readings(jlpt_display, jlpt_reading))[:1])
        if len(parts) <= 1 or parts <= used:
            claimed_nids.add(nid)

    # Build a set of suspended (norm_display, norm_reading) pairs for fast lookup
    suspended_keys: set[tuple[str, str]] = set()
    if overrides:
        for d, r in overrides.suspended_pairs():
            suspended_keys.add((_norm(d), _norm(r)))

    # Build found lookup: (norm_display, norm_reading) → (display, reading)
    # for user-marked words. Matched by exact pair, same as the override key,
    # so marking one word found doesn't also promote other JLPT entries that
    # happen to share the same display kanji with a different reading.
    found_virtual: dict[tuple[str, str], tuple[str, str]] = {}
    if overrides:
        for d, r in overrides.found_pairs():
            nd, nr = _norm(d), _norm(r)
            found_virtual[(nd, nr)] = (d, r)

    for lvl in LEVELS:
        word_list = lists.get(lvl, [])

        # Deduplicate list entries.
        # Also drop any お+kanji entry whose bare form already exists as a
        # standalone entry in this level's list (e.g. お風呂 is redundant when
        # 風呂 is already present). Without this, 風呂 claims the nid first and
        # お風呂 can never match, leaving it as a false "missing" word.
        #
        # Key: only count a bare form as "present" when it appears as its own
        # entry — NOT when it's only derivable by stripping お from another word.
        # Build the set from displays that are NOT themselves お+kanji words.
        non_o_displays = {
            _norm(d)
            for d, _ in word_list
            if not _honorific_o_strip(_norm(d))  # "" means not an お/ご+kanji word
        }

        seen_pairs = set()
        deduped    = []
        for display, reading in word_list:
            nd  = _norm(display)
            key = (nd, _norm(reading))
            if key in seen_pairs:
                continue
            # Skip お+kanji entry when the bare root exists as its own entry
            bare = _honorific_o_strip(nd)
            if bare and bare in non_o_displays:
                continue
            seen_pairs.add(key)
            deduped.append((display, reading))

        known   = []
        missing = []

        for display, reading in deduped:
            nd = _norm(display)
            nr = _norm(reading)

            # Skip suspended words from known/missing counts, but still
            # claim their nid so the card doesn't leak into the unlisted bucket.
            if (nd, nr) in suspended_keys:
                nid, soft = _find_match(display, reading, display_index,
                                        reading_index, nid_to_reading,
                                        unique_readings, claimed_nids, kana_nids,
                                        nid_to_display)
                if nid is not None:
                    if soft:
                        soft_nids.add(nid)
                    else:
                        _claim(nid, display, reading)
                continue

            nid, soft = _find_match(display, reading, display_index,
                                    reading_index, nid_to_reading,
                                    unique_readings, claimed_nids, kana_nids,
                                    nid_to_display)

            if nid is not None:
                known.append((display, reading, nid))
                if not soft:
                    _claim(nid, display, reading)
                else:
                    soft_nids.add(nid)
            elif (nd, nr) in found_virtual:
                # User manually marked this as found
                known.append((display, reading, None))
                # Don't add None to claimed_nids — virtual entries don't block real nids
            else:
                missing.append((display, reading))

        results[lvl] = {"known_words": known, "missing_words": missing}

    # A leftover card is still a JLPT word if it's a second card for a list
    # entry (掛かる when かかる already counted): same spelling (or an
    # alternate spelling) with one of the entry's readings. Those aren't
    # "Non-JLPT", so keep them out of the unlisted bucket.
    jlpt_spellings: dict[str, set[str]] = {}
    spelling_entries: dict[str, list] = {}   # spelling → [((display, reading), readings)]
    for lvl in LEVELS:
        for d, r in lists.get(lvl, []):
            acc = _accepted_readings(d, r)
            entry_has_kanji = bool(_KANJI_RE.search(_norm(d)))
            for form in [d] + jlpt_data.same_kanji_forms(d, r):
                # Script rule: a kanji entry's kana spellings don't make a
                # kana card a JLPT word.
                if entry_has_kanji and not _KANJI_RE.search(_norm(form)):
                    continue
                jlpt_spellings.setdefault(_norm(form), set()).update(acc)
                alts = jlpt_data.alt_forms(d, r)
                main = next((_norm(a) for a in alts if _KANJI_RE.search(a)), "")
                spelling_entries.setdefault(_norm(form), []).append(
                    ((_norm(d), _norm(r), frozenset(alts)), acc, main))

    def _is_jlpt_duplicate(nid: int, display: str) -> bool:
        acc = jlpt_spellings.get(_norm(display))
        if acc is None:
            return False
        parts = _reading_parts(nid_to_reading.get(nid, ""))
        return not parts or any(_kata_to_hira(p) in acc for p in parts)

    # Unlisted: deck cards not matched to any JLPT entry
    unlisted      = []
    seen_unlisted = set()
    for nid, display in nid_to_display.items():
        if (nid not in claimed_nids and nid not in soft_nids
                and nid not in used_readings and nid not in seen_unlisted
                and not _is_jlpt_duplicate(nid, display)):
            reading = nid_to_reading.get(nid, "")
            unlisted.append((display, reading, nid))
            seen_unlisted.add(nid)

    results["unlisted"] = {"known_words": unlisted, "missing_words": []}
    results["duplicates"] = _duplicate_groups(
        results, nid_to_display, nid_to_reading, spelling_entries, exact_duplicates or {},
        lambda nid: (nid not in claimed_nids and nid not in soft_nids
                     and nid not in used_readings))

    # Frequency-dictionary comparison for the rank section (independent of
    # the JLPT lists; found/suspended marks apply to it too).
    results["frequency"] = freq_data.coverage(nid_to_display, nid_to_reading, overrides)
    # Marked loanwords that count at once, off the schedule (card_state).
    results["loans_now"] = overrides.counted_pairs() if overrides else []
    return results


def _duplicate_groups(results, nid_to_display, nid_to_reading, spelling_entries,
                      exact: dict, leftover) -> list:
    """Notes that are the same word, as [[nid, …], …] (word order of the
    first note): exact copies, and a leftover card that is a second card for
    a JLPT word another card already counts (掛かる next to かかる, 出来る next
    to できる; same kanji only, kana cards never for kanji words). Better
    than Anki's own check, which only compares the first field as typed.
    Sentence-card words are never part of a group. A list entry is its
    spelling, reading and alternates (いる 居る and いる 要る are two words)."""
    real = lambda n: n is not None and n < card_state.PSEUDO_BASE
    entry_nid = {}   # one word listed at two levels (うるさい N5 + N1) takes two cards
    parent = {}

    def readings(n):
        return {_kata_to_hira(p) for p in _reading_parts(nid_to_reading.get(n, ""))}

    def same_word(a, b) -> bool:
        """Two cards an entry lumps together are still two words if both
        have kanji and the kanji differ (点ける / 付ける, 掛ける / 懸ける), or
        both have readings and none is shared (避ける さける / よける)."""
        da, db = _norm(nid_to_display.get(a, "")), _norm(nid_to_display.get(b, ""))
        if (_KANJI_RE.search(da) and _KANJI_RE.search(db)
                and not (jlpt_data.same_kanji(da, db) or jlpt_data.same_kanji(db, da))):
            return False
        ra, rb = readings(a), readings(b)
        return not (ra and rb) or bool(ra & rb)

    def find(n):
        while parent.setdefault(n, n) != n:
            n = parent[n]
        return n

    def join(a, b):
        parent[find(b)] = find(a)

    for lvl in LEVELS:
        for d, r, nid in results.get(lvl, {}).get("known_words", []):
            if not real(nid):
                continue
            # Same spelling, reading and alternates = the same word; かかる
            # 掛かる (N5) and かかる 罹る (N3) differ, so they stay apart.
            word = (_norm(d), _norm(r), frozenset(jlpt_data.alt_forms(d, r)))
            first = entry_nid.setdefault(word, nid)
            if first != nid and same_word(first, nid):
                join(first, nid)
    for first, nids in exact.items():
        for n in nids:
            join(first, n)
    for nid, display in nid_to_display.items():
        if not real(nid) or not leftover(nid):
            continue
        parts = readings(nid)
        for key, acc, main in spelling_entries.get(_norm(display), ()):
            anchor = entry_nid.get(key)
            # A kana card is the word's main kanji spelling only: いる is
            # listed as 居る and 要る, so a 要る card isn't a second いる.
            if (anchor is not None and anchor != nid and not _KANJI_RE.search(
                    _norm(nid_to_display.get(anchor, ""))) and _KANJI_RE.search(_norm(display))
                    and not (main and jlpt_data.same_kanji(main, _norm(display)))):
                continue
            if (anchor is not None and anchor != nid and (not parts or parts & acc)
                    and same_word(anchor, nid)):
                join(anchor, nid)
                break
    groups = {}
    for n in list(parent):
        groups.setdefault(find(n), []).append(n)
    out = [sorted(g) for g in groups.values() if len(g) > 1]
    return sorted(out, key=lambda g: _norm(nid_to_display.get(g[0], "")))


def new_card_words(results: dict, deck_name: str, lists: dict, analysis_inputs: dict) -> dict:
    """The grids' "New" tiles (owner 2026-10-17): missing words that a
    never-studied card in the deck would match. Display only: every count
    (bars, rank, frequency tiers, history, Text Check) still uses only
    studied cards. Found by re-running the matching over every note of the
    deck and keeping the entries that only a new note matches.
    Returns {"words": {(display, reading): nid}, "ranks": {rank: nid},
    "notes": {nid: word} of the new notes (the kanji scan reads them)}."""
    out = {"words": {}, "ranks": {}, "notes": {}}
    fm = analysis_inputs.get("field_mappings") or []
    if not deck_name or not fm:
        return out
    seen = card_state.deck_notes(deck_name)
    new_nids = set(card_state.deck_notes(deck_name, seen_only=False)) - set(seen)
    if not new_nids:
        return out
    ign = bool(analysis_inputs.get("ignore_suspended", False))
    di, ri, nd, nr = collect_words(deck_name, fm, ign, seen_only=False)
    every = analyse(di, ri, nd, nr, lists, analysis_inputs.get("unique_readings", set()))

    def is_new(nid) -> bool:
        return nid is not None and card_state.real_nid(nid) in new_nids

    out["notes"] = {n: d for n, d in nd.items() if is_new(n)}
    for lvl in LEVELS:
        missing = set(results.get(lvl, {}).get("missing_words", ()))
        for d, r, nid in every.get(lvl, {}).get("known_words", ()):
            if (d, r) in missing and is_new(nid):
                out["words"][(d, r)] = nid
    freq = results.get("frequency") or {}
    missing_ranks = {e[0] for e in freq.get("entries", ()) if e[3] is None}
    for rank, _d, _r, nid in (every.get("frequency") or {}).get("entries", ()):
        if rank in missing_ranks and is_new(nid):
            out["ranks"][rank] = nid
    return out


# ── main flow ──────────────────────────────────────────────────────────────────

def apply_loanword_default(lists: dict):
    """English loanwords marked found by default on a fresh install
    (overrides.apply_loanword_default). Main thread only: it writes the
    config, so the main window's analysis calls it, not the mini widget's
    background count (a new user's first setup opens the main window)."""
    from .overrides import apply_loanword_default as apply
    apply(lists, _cfg, _save)


def _open_progress_dialog(cfg: dict) -> bool:
    """Run the analysis and show ProgressDialog using the given config.
    Returns True on success, False if the config is incomplete (and a
    warning was shown)."""
    deck_name      = cfg.get("deck_name", "")
    field_mappings = cfg.get("field_mappings", [])
    lists_cfg      = cfg.get("lists", {})

    if not deck_name:
        showWarning("Please select a deck.")
        return False
    if not field_mappings:
        showWarning("Please add at least one vocab field in Settings.")
        return False
    if not card_state.deck_exists(deck_name):
        showWarning(f"Kotodama can't find the deck “{deck_name}”. It may have been "
                    "renamed or deleted. Choose your deck again in Kotodama → Settings.")
        return False

    lists = jlpt_data.build_lists(lists_cfg)
    if not any(lists.values()):
        showWarning("No vocabulary lists loaded.")
        return False

    if _opening["busy"]:
        return True                  # already counting (a second click)
    _opening["busy"] = True
    apply_loanword_default(lists)        # once, on a fresh install

    def show(out):
        _opening["busy"] = False
        results, analysis_inputs, extras, overrides = out
        _OpeningNote.show_over(mw)       # until the window is up
        try:
            ProgressDialog(
                mw, results, deck_name, lists, overrides=overrides,
                analysis_inputs=analysis_inputs, extras=extras,
            ).show()
        finally:
            QTimer.singleShot(300, _OpeningNote.close_it)

    # Counted ahead in the background (prepare_dialog) and nothing has
    # changed since: open at once (owner 2026-10-24: the widget click took
    # seconds, every time).
    key = _prep_key(cfg)
    if key is not None and _prep["key"] == key and _prep["out"] is not None:
        out, _prep["out"], _prep["key"] = _prep["out"], None, None   # used once
        _OpeningNote.show_over(mw)
        QTimer.singleShot(0, lambda: show(out))
        return True
    if key is not None and _prep["running"] == key:
        _prep["waiting"] = True          # opens when that count is done
        _OpeningNote.show_over(mw)
        return True

    def work_or_reset():
        try:
            return _dialog_work(cfg, lists)
        except BaseException:
            _opening["busy"] = False
            mw.taskman.run_on_main(_OpeningNote.close_it)
            raise

    # Our own note, not Anki's progress bar: the precount was stale, so
    # this click counts afresh (owner 2026-10-26: the old bar still showed).
    _OpeningNote.show_over(mw)
    card_state.run_in_background(mw, work_or_reset, show)
    return True


def _dialog_work(cfg: dict, lists: dict):
    """Everything the main window needs, counted off the main thread: the
    deck scan, every analysis, kanji, grammar, history. Returns (results,
    analysis inputs, extras, overrides)."""
    deck_name      = cfg.get("deck_name", "")
    field_mappings = cfg.get("field_mappings", [])
    ignore_suspended = bool(cfg.get("ignore_suspended_cards", False))
    overrides        = Overrides()
    unique_readings  = _build_unique_readings(lists)
    exact_dups: dict = {}
    display_index, reading_index, nid_to_display, nid_to_reading =         collect_words(deck_name, field_mappings, ignore_suspended, duplicates=exact_dups)
    results = analyse(
        display_index, reading_index,
        nid_to_display, nid_to_reading,
        lists, unique_readings,
        overrides=overrides, exact_duplicates=exact_dups,
    )
    # nid → new/learning/young/mature, for the tile saturation.
    results["maturity"] = card_state.with_pseudo(
        card_state.note_maturity(deck_name, ignore_suspended), nid_to_display)
    analysis_inputs = {
        "display_index":  display_index,
        "reading_index":  reading_index,
        "nid_to_display": nid_to_display,
        "nid_to_reading": nid_to_reading,
        "exact_duplicates": exact_dups,
        "unique_readings": unique_readings,
        "field_mappings":  field_mappings,   # needed so Refresh re-scans the deck
        "ignore_suspended": ignore_suspended,
    }
    # Kanji, grammar, found-words count, today's history snapshot.
    extras = ProgressDialog.compute_extras(results, deck_name, lists, analysis_inputs)
    return results, analysis_inputs, extras, overrides


# The main window's count, made ahead of time (prepare_dialog) for the
# next click; key = what it depends on, when it was made.
_prep = {"key": None, "out": None, "running": None, "waiting": False}


def _prep_key(cfg: dict):
    """mini_widget's change key (settings, cards, notes, word marks) plus
    the kanji / grammar marks and the day (today's history snapshot)."""
    import os
    from .overrides import KANJI_PATH, GRAMMAR_PATH
    key = mini_widget._change_key(cfg)
    if key is None:
        return None
    marks = []
    for p in (KANJI_PATH, GRAMMAR_PATH):
        try:
            marks.append(os.stat(p).st_mtime_ns)
        except Exception:
            marks.append(0)
    try:
        day = mw.col.sched.day_cutoff
    except Exception:
        return None
    return (key, tuple(marks), day)


def prepare_dialog():
    """Count the main window's numbers now, quietly in the background, so
    the next click on the widget opens it at once. Called after the mini
    widget's own recount (the deck list after reviews, a closed window,
    Anki's start); does nothing if that count is still current."""
    if getattr(mw, "state", "deckBrowser") != "deckBrowser":
        return                       # reviewing: never queue ahead of answers
    cfg = _cfg()
    if not cfg.get("deck_name") or not cfg.get("field_mappings"):
        return
    if not card_state.deck_exists(cfg["deck_name"]):
        return
    # Not while the main window is open (its intro and sounds need the
    # main thread; closing it redraws the deck list, which asks again).
    if any(isinstance(w, ProgressDialog) and w.isVisible() for w in QApplication.topLevelWidgets()):
        return
    key = _prep_key(cfg)
    if key is None or _prep["running"] is not None or _prep["key"] == key:
        return
    lists = jlpt_data.build_lists(cfg.get("lists", {}))
    if not any(lists.values()):
        return
    _prep["running"] = key

    def work():
        return _dialog_work(cfg, lists)

    def done(out):
        _prep["running"] = None
        _prep["key"], _prep["out"] = key, out
        if _prep["waiting"]:             # clicked while this ran
            _prep["waiting"] = False
            _opening["busy"] = False
            _OpeningNote.close_it()
            _open_progress_dialog(_cfg())

    def run():
        try:
            return work()
        except BaseException:
            _prep["running"] = None
            if _prep["waiting"]:
                _prep["waiting"] = False
                _opening["busy"] = False
                _OpeningNote.close_it()
            raise

    card_state.run_in_background(mw, run, done, quiet=True)


class _OpeningNote:
    """"Opening Kotodama…" over Anki's window while the main window is
    counted (when the count was already running) and built (Anki's progress
    window closes when the counting ends); busy.py's note."""
    _one = None

    @classmethod
    def show_over(cls, parent):
        if cls._one is None:
            from .busy import show_note
            cls._one = show_note(parent, "Opening Kotodama…")

    @classmethod
    def close_it(cls):
        from .busy import close_note
        close_note(cls._one)
        cls._one = None


_opening = {"busy": False}


def run_jlpt_check():
    cfg = _cfg()
    dlg = ConfigDialog(mw, cfg)
    if dlg.exec() != QDialog.DialogCode.Accepted:
        return

    new_cfg = dlg.get_config()
    _save(new_cfg)
    mini_widget.invalidate_cache()
    if not new_cfg.get("amaterasu_sound", True):
        from . import ambience
        ambience.get().leave()               # muted: quiet at once

    # Refresh the main screen so the mini widget reflects the new
    # enabled/disabled state and any config changes immediately.
    if mw.state == "deckBrowser":
        mw.deckBrowser.refresh()

    _open_progress_dialog(new_cfg)


def open_progress_dialog_direct():
    """Open the main progress window directly, bypassing the Settings
    dialog — used by the mini overview widget's click handler. Falls back
    to the normal Settings flow if the add-on isn't configured yet."""
    cfg = _cfg()
    if not cfg.get("deck_name") or not cfg.get("field_mappings"):
        run_jlpt_check()
        return
    if not _open_progress_dialog(cfg):   # e.g. the deck is gone: choose it again
        run_jlpt_check()


# ── menu ───────────────────────────────────────────────────────────────────────

# Its own menu on Anki's menu bar, before Help (owner 2026-10-15; was an
# entry under Tools).
_menu = QMenu("Kotodama", mw)
_open_action = QAction("Open Kotodama", mw)
_open_action.triggered.connect(open_progress_dialog_direct)
_menu.addAction(_open_action)
_settings_action = QAction("Settings…", mw)
_settings_action.triggered.connect(run_jlpt_check)
_menu.addAction(_settings_action)
_menu.addSeparator()
# The credits screen (about.py; JMdict's licence asks for one reachable from a menu)
_about_action = QAction("About Kotodama…", mw)
from . import about
_about_action.triggered.connect(lambda: about.show_about(mw))
_menu.addAction(_about_action)
# macOS would move "Settings…" / "About…" into the application menu by their
# text (Qt's TextHeuristicRole); keep all three in the Kotodama menu.
for _a in (_open_action, _settings_action, _about_action):
    try:
        _a.setMenuRole(QAction.MenuRole.NoRole)
    except Exception:
        pass
mw.form.menubar.insertMenu(mw.form.menuHelp.menuAction(), _menu)
# Tools → Add-ons → Config opens Kotodama's own Settings, not raw JSON.
try:
    mw.addonManager.setConfigAction(__name__, run_jlpt_check)
except Exception:
    pass

mini_widget.setup()
rank_toast.setup()
history.setup()
from . import seal
seal.setup()                 # Amaterasu seal on the review screen (Settings, off by default)
from . import nakama
nakama.setup()               # Nakama: your card is sent after Anki syncs (once you've joined)
