"""
kanji_data.py
Kanji tracker (backlog #5): which JLPT kanji are in the user's learned cards,
and how well they're known.

Owner's rules (2026-10-09):
  - A kanji is KNOWN when at least one studied card (learning, young or
    mature) contains it (owner 2026-10-21, like words; was young / mature
    only). Suspended cards never count, new (unstudied) cards don't yet.
  - How WELL it's known is a 0–1 score shown as a heatmap colour, the mean
    of the scores of every studied card containing it (a card still in
    learning scores 0: it has just started). Maturity is only
    listed on the hover.
  - Kanji don't affect the rank or the word counts.

Where the kanji come from (config "kanji_source"):
  mode "vocab"    : every kanji in the vocab words (deck + display fields set
                    for the word lists); the cards are those words' cards.
                    Sentence cards (a mapping with only a sentence field)
                    give the kanji of their whole sentence.
  mode "sentence" : every kanji in the sentence fields of the vocab deck's
                    mappings (the auto parser, phase 3).
  mode "fields"   : every kanji in the given note-type fields of another
                    deck, e.g. a kanji deck's "kanji" field.

Card score (FSRS, which the owner uses, and SM-2 as a fallback):
  strength   = log(stability) / log(STRENGTH_FULL_DAYS), clamped to 0..1:
               1 day → 0, ~1 month → 0.5, 2 years → 1. Stability is the
               number of days until recall probability drops to 90%; under
               SM-2 the interval stands in for it.
  difficulty = FSRS difficulty 1–10 (SM-2: from the ease factor, 130% → 10,
               300% → 1); it lowers the score by up to DIFFICULTY_WEIGHT.
               Kept light: FSRS difficulty clusters near 10 for most cards
               (owner's median 8.9), so a heavy weight would make every
               kanji look weak.
  lapses     = each lapse multiplies the score by LAPSE_FACTOR (up to
               MAX_LAPSES).
Review counts and Good/Easy answers are already built into stability.
"""

import json
import math
import os
import re
import unicodedata

from . import card_state
from .jlpt_data import LEVELS

_HERE = os.path.dirname(os.path.abspath(__file__))
_PATH = os.path.join(_HERE, "kanji_jlpt.txt")

STRENGTH_FULL_DAYS = 730
DIFFICULTY_WEIGHT  = 0.15
LAPSE_FACTOR       = 0.96
MAX_LAPSES         = 8


def is_kanji(c: str) -> bool:
    """CJK ideograph (not 々 or kana). Code points, not escapes: the editing
    tools turn \\u escapes into literal characters."""
    o = ord(c)
    return (0x4E00 <= o <= 0x9FFF or 0x3400 <= o <= 0x4DBF
            or 0xF900 <= o <= 0xFAFF or 0x20000 <= o <= 0x2FFFF)


def kanji_in(text: str) -> list[str]:
    """The distinct kanji in a text, in order of appearance."""
    seen = []
    for c in unicodedata.normalize("NFKC", text or ""):
        if is_kanji(c) and c not in seen:
            seen.append(c)
    return seen


def field_text(raw: str) -> str:
    """A field's text without HTML or furigana. Furigana is ignored, never
    read (owner 2026-10-14): ruby readings (<rt>) are dropped with their
    tags, and Anki's bracket form loses the space before each piece too,
    as Anki does, so 証[しょう] 拠[こ] is 証拠 again, not 証 拠."""
    s = re.sub(r"<rt[^>]*>.*?</rt>|<rp[^>]*>.*?</rp>", "", raw or "", flags=re.I | re.S)
    s = re.sub(r"<[^>]+>", "", s)
    s = s.replace("&nbsp;", " ")
    s = re.sub(r" ?([^ >\[\]]+?)\[[^\]]*\]", r"\1", s)
    s = re.sub(r"\[[^\]]*\]", "", s)
    return s.strip()


# ── bundled list ──────────────────────────────────────────────────────────────

_DATA = None


def data() -> dict:
    """char → {level, freq, strokes, meanings, on, kun, supp}, in file order
    (N5 → N1, most common first)."""
    global _DATA
    if _DATA is None:
        out = {}
        try:
            with open(_PATH, encoding="utf-8") as f:
                for line in f:
                    if not line.strip() or line.startswith("#"):
                        continue
                    p = line.rstrip("\n").split("\t")
                    p += [""] * (8 - len(p))
                    out[p[0]] = {
                        "level":    p[1],
                        "freq":     int(p[2]) if p[2] else None,
                        "strokes":  int(p[3]) if p[3] else None,
                        "meanings": [m for m in p[4].split("; ") if m],
                        "on":       [r for r in p[5].split("、") if r],
                        "kun":      [r for r in p[6].split("、") if r],
                        "supp":     p[7] == "supp",
                    }
        except OSError:
            pass
        _DATA = out
    return _DATA


def level_chars() -> dict[str, list[str]]:
    out = {lvl: [] for lvl in LEVELS}
    for c, info in data().items():
        out.setdefault(info["level"], []).append(c)
    return out


# ── scoring ───────────────────────────────────────────────────────────────────

def card_score(ivl: int, factor: int, lapses: int, card_data: str) -> float:
    """0–1 strength of one learned card (see the module docstring)."""
    stability = difficulty = None
    if card_data:
        try:
            j = json.loads(card_data)
            stability, difficulty = j.get("s"), j.get("d")
        except (ValueError, TypeError):
            pass
    if stability is None:
        stability = ivl
    if difficulty is None:
        difficulty = 1 + 9 * min(max((3000 - (factor or 2500)) / 1700, 0), 1)
    strength = min(max(math.log(max(stability, 1)) / math.log(STRENGTH_FULL_DAYS), 0), 1)
    dn = min(max((difficulty - 1) / 9, 0), 1)
    return strength * (1 - DIFFICULTY_WEIGHT * dn) * LAPSE_FACTOR ** min(lapses or 0, MAX_LAPSES)


# Contexts (owner 2026-10-18, to-do 2f): a kanji's readings and a grammar
# point's uses need several cards to settle, so one strong card shouldn't
# read as strong as many. A balance shift, not a boost: each item's mean is
# weighted by f(n) = 1 − W + W·(1 − e^(−n/K)) for its n learned cards, then
# everything is divided by the deck's own average weight, so the deck-wide
# average score stays where it was (no inflation): few-card items move down,
# many-card items up. n = 1 → 0.82, 2 → 0.89, 3 → 0.93, 5 → 0.98, 8+ → ≈1.
CONTEXT_WEIGHT = 0.3
CONTEXT_K      = 2.0


def context_weight(n: int) -> float:
    return 1 - CONTEXT_WEIGHT + CONTEXT_WEIGHT * (1 - math.exp(-n / CONTEXT_K))


def weigh_contexts(stats: dict) -> None:
    """Rescale stats[x]["score"] (a mean card score) for the number of
    learned cards, keeping the average over all items unchanged. The plain
    mean stays in "card_mean"."""
    items = [s for s in stats.values() if s.get("score") is not None]
    total = sum(s["score"] for s in items)
    if not total:
        return
    norm = sum(s["score"] * context_weight(s["cards"]) for s in items) / total
    for s in items:
        s["card_mean"] = s["score"]
        s["score"] = min(s["score"] * context_weight(s["cards"]) / norm, 1.0)


# ── analysis ──────────────────────────────────────────────────────────────────

def field_labels(mappings: list, key: str) -> list[str]:
    """["Kaishi 1.5k → Word", …] for the mappings that set this field."""
    return [f"{m.get('note_type') or 'all note types'} → {m[key]}"
            for m in mappings if m.get(key)]


def source_config(cfg: dict) -> dict:
    src = dict(cfg.get("kanji_source") or {})
    src.setdefault("mode", "vocab")
    src.setdefault("deck", "")
    src.setdefault("mappings", [])
    return src


def _field_texts(deck_name: str, mappings: list, seen_only: bool = True) -> dict[int, str]:
    """nid → text of the mapped fields (fields mode)."""
    out = {}
    for nid, note in card_state.deck_notes(deck_name, seen_only).items():
        model = note.type_name
        parts = []
        for m in mappings:
            if m.get("note_type") and m["note_type"] != model:
                continue
            f = m.get("field", "")
            if f and f in note:
                t = field_text(note[f])
                if t:
                    parts.append(t)
        if parts:
            out[nid] = " ".join(parts)
    return out


def analyse(cfg: dict, deck_name: str, nid_to_display: dict, overrides=None,
            new_notes: dict = None) -> dict:
    """Kanji results for the Kanji & Grammar tab.

    Returns {
      "source": the kanji_source config used, "deck": the deck it scanned,
      "stats":  char → {"score": mean card score or None, "cards": learned
                card count, "best": most mature state, "words": [(text,
                state, nid)] best first, "pending": a new card
                (not suspended) has it},
      "levels": level → [chars] (N5 → N1, most common first),
      "offlist": [chars] in the source but on no level list, most used first,
      "known":  set of known chars (a learned card, or marked found),
    }
    Never-studied cards are scanned too (new_notes: nid → word of the deck's
    new notes, vocab mode), for the "in your deck, not learned yet" tiles
    (owner 2026-10-17); like learning cards they never make a kanji known.
    """
    from aqt import mw
    from anki.utils import ids2str

    from . import sentence_parser
    src = source_config(cfg)
    mappings = cfg.get("field_mappings", [])
    if src["mode"] == "fields" and src["deck"] and src["mappings"]:
        texts, deck = _field_texts(src["deck"], src["mappings"], seen_only=False), src["deck"]
    elif src["mode"] == "sentence":
        texts, deck = sentence_parser.sentence_texts(deck_name, mappings, seen_only=False), deck_name
    else:
        src["mode"] = "vocab"
        deck = deck_name
        # Word cards: their word. Sentence cards: their whole sentence.
        every = dict(nid_to_display)
        every.update(new_notes or {})
        texts = {n: d for n, d in every.items() if n < card_state.PSEUDO_BASE}
        if any(n >= card_state.PSEUDO_BASE for n in every):
            texts.update(sentence_parser.sentence_texts(deck_name, mappings, sentence_only=True,
                                                        seen_only=False))

    note_kanji = {nid: kanji_in(t) for nid, t in texts.items()}
    note_kanji = {nid: ks for nid, ks in note_kanji.items() if ks}

    scores: dict[str, list[float]] = {}
    best:   dict[str, int] = {}
    words:  dict[str, dict[int, int]] = {}   # char → nid → best state
    pending: set[str] = set()                # a new (unstudied) card has it
    studied: set[str] = set()                # a studied (not new) card has it
    cids = mw.col.find_cards(card_state.deck_search(deck, seen_only=False)) if deck else []
    if cids and note_kanji:
        rows = mw.col.db.all(
            "select nid, type, queue, ivl, factor, lapses, data from cards "
            f"where id in {ids2str(cids)}")
        for nid, ctype, queue, ivl, factor, lapses, cdata in rows:
            ks = note_kanji.get(nid)
            if not ks:
                continue
            # Suspended cards never count; their kanji stay unseen.
            state = card_state.NEW if queue == -1 else card_state.card_state(ctype, ivl)
            learned = state >= card_state.LEARNING          # studied (owner 2026-10-21)
            sc = card_score(ivl, factor, lapses, cdata) if learned else None
            for k in ks:
                w = words.setdefault(k, {})
                if state > w.get(nid, -1):
                    w[nid] = state
                if learned:
                    scores.setdefault(k, []).append(sc)
                elif queue != -1:
                    pending.add(k)
                if ctype != 0:
                    studied.add(k)
                if state > best.get(k, -1):
                    best[k] = state

    stats = {}
    for k in set(words) | set(scores):
        sc = scores.get(k, [])
        stats[k] = {
            "score": sum(sc) / len(sc) if sc else None,
            "cards": len(sc),
            "best":  best.get(k, card_state.NEW),
            "words": sorted(((texts[n], st, n) for n, st in words.get(k, {}).items()),
                            key=lambda w: -w[1]),
            "pending": k in pending,
        }
    weigh_contexts(stats)

    found = {k.split("\t", 1)[0] for k in overrides.found} if overrides else set()
    known = {k for k, s in stats.items() if s["cards"]} | found
    lvl = level_chars()
    listed = data()
    # Off-list kanji: only those in a studied card, as before new cards
    # were scanned (a deck of unstudied cards shouldn't fill it).
    offlist = sorted((k for k in stats if k not in listed and k in studied),
                     key=lambda k: (-stats[k]["cards"], -len(stats[k]["words"]), k))
    return {"source": src, "deck": deck, "stats": stats, "levels": lvl,
            "offlist": offlist, "known": known,
            "word_fields": field_labels(mappings, "field"),
            "sentence_fields": field_labels(mappings, "sentence_field"),
            "sentence_only_fields": field_labels(
                [m for m in mappings if not m.get("field")], "sentence_field")}


def level_counts(kres: dict, suspended: set = frozenset()) -> dict:
    """level → (known, total), leaving out kanji the user suspended; plus
    "All"."""
    out = {}
    tk = tt = 0
    for lvl in LEVELS:
        chars = [c for c in kres["levels"].get(lvl, []) if c not in suspended]
        k = sum(1 for c in chars if c in kres["known"])
        out[lvl] = (k, len(chars))
        tk += k; tt += len(chars)
    out["All"] = (tk, tt)
    return out
