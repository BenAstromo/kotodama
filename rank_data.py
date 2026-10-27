"""
rank_data.py
Anki Vocabulary Rank System — pure data/logic layer.

Independent of JLPT levels: this tracks total note count in the configured
deck against a 20,000-word "native-like fluency" target, regardless of
whether those notes are JLPT-listed or not.

Structure
  10 main ranks x 8 belt subdivisions = 80 levels.
  A higher main rank always outranks every belt of a lower main rank
  (e.g. White Belt Shogun > Black Belt Samurai).

Progression curve
  Belt sizes grow exponentially (ratio ≈ 1.05 per belt) so early ranks
  fly by and later ranks become a serious grind — just like a real martial-
  arts belt system.

    Gaijin  rank total ≈    198 cards  (belts  21–29 cards each)
    Tourist rank total ≈    291 cards
    ...
    Amaterasu rank total ≈ 6598 cards

  The 81-entry BELT_THRESHOLDS list encodes every belt boundary directly,
  so get_rank_info() is a simple binary search — no floating-point curve
  math at runtime.

Amaterasu Black Belt — 10 degrees, half the rank
  Per spec, Amaterasu's White through Brown belts (7 belts) are compressed
  to take up exactly the FIRST HALF of the Amaterasu rank's card span, and
  Black Belt — split into 10 equal degrees — takes up the SECOND HALF.
  This makes Amaterasu's early belts (e.g. White Belt Amaterasu) noticeably
  EASIER than the equivalent belt in the previous rank (e.g. White Belt
  Emperor), while the back half (the 10 black degrees) becomes a much
  longer grind than a normal belt would be — degrees are ~330 cards each
  vs. a normal belt's ~700-900 cards at this point in the curve.

  Concretely, out of Amaterasu's 6,598-card span:
    White..Brown (7 belts):      3,299 cards total (~405-543 cards each)
    Black, 10 degrees:           3,299 cards total (~330 cards each)

  No other rank's Black Belt is split into degrees or rebalanced — this
  reshaping is exclusive to Amaterasu, the final rank.

Special case
  Black Belt Amaterasu is reached at exactly 20,000 cards and is treated
  as the unique "max level" rather than a normal 80th belt.
"""

import bisect

MAX_CARDS      = 20_000
BELTS_PER_RANK = 8
N_RANKS        = 10
N_BELTS        = N_RANKS * BELTS_PER_RANK   # 80

# Belt order, lowest → highest
BELTS = [
    "White",
    "Yellow",
    "Orange",
    "Green",
    "Blue",
    "Purple",
    "Brown",
    "Black",
]

# Belt colors — used for badge text
BELT_COLORS = {
    "White":  "#f5f5f5",
    "Yellow": "#fdd835",
    "Orange": "#fb8c00",
    "Green":  "#43a047",
    "Blue":   "#1e88e5",
    "Purple": "#8e24aa",
    "Brown":  "#795548",
    "Black":  "#212121",
}

# Bar fill colors — slightly adjusted so pure black/white glow well on dark UI
BELT_BAR_COLORS = {
    "White":  "#cfd8dc",
    "Yellow": "#fdd835",
    "Orange": "#fb8c00",
    "Green":  "#43a047",
    "Blue":   "#1e88e5",
    "Purple": "#8e24aa",
    "Brown":  "#8d6e63",
    "Black":  "#616161",
}

# Per-rank gradient colors: (dominant, accent)
RANK_COLORS = {
    "Gaijin":           ("#1565c0", "#42a5f5"),   # Blue
    "Tourist":          ("#2e7d32", "#66bb6a"),   # Green
    "Weeb":             ("#ff9800", "#ffe0b2"),   # Light orange (warm, bright)
    "Exchange Student": ("#bf360c", "#ff5722"),   # Deep orange
    "Naijin":           ("#b71c1c", "#ef5350"),   # Red
    "Nihonjin":         ("#1a1a1a", "#f5f5f5"),   # Black and white
    "Samurai":          ("#7f0000", "#0d2966"),   # Dark red and dark blue
    "Shogun":           ("#111111", "#d4af37"),   # Black and gold
    "Emperor":          ("#8b0000", "#ff6a00"),   # Fire: deep crimson → bright flame orange
    "Amaterasu":        ("#f5c518", "#fff8c5"),   # Bright light gold
}

MAIN_RANKS_EN = [
    "Gaijin",
    "Tourist",
    "Weeb",
    "Exchange Student",
    "Naijin",
    "Nihonjin",
    "Samurai",
    "Shogun",
    "Emperor",
    "Amaterasu",
]

MAIN_RANKS_JP = [
    "外人",
    "観光客",
    "ウィーブー",
    "留学生",
    "内人",
    "日本人",
    "侍",
    "将軍",
    "天皇",
    "天照",
]

MAIN_RANKS = [f"{en} ({jp})" for en, jp in zip(MAIN_RANKS_EN, MAIN_RANKS_JP)]

# The single, ultimate max-level state: exactly 20,000 cards (Black Belt
# Amaterasu). Every progress bar across the whole add-on EXCEPT the belt
# bar itself (which legitimately shows Black Belt's own dark color) —
# every JLPT level bar, the "All Levels Combined" bar, and the mini
# overview widget — switches to this fill when is_max_amaterasu is True.
# Matches RANK_COLORS["Amaterasu"][0] exactly so every bar shows the
# SAME bright gold as the rank bar itself, rather than a similar-looking
# second gold.
MAX_RANK_FILL_COLOR = RANK_COLORS["Amaterasu"][0]   # "#f5c518"

# ── Curved threshold table ────────────────────────────────────────────────────
#
# 81 values: BELT_THRESHOLDS[i] is the card count at which belt i begins.
# BELT_THRESHOLDS[80] == MAX_CARDS == 20,000 (sentinel / Tenth-Degree Black
# Belt Amaterasu).
#
# Generated with r=1.05 exponential growth over 80 belts, originally scaled
# to sum=20,000. The final 8 entries (Amaterasu's belts, global indices
# 72-79) were then RESHAPED per spec so that White..Brown (7 belts) and
# Black (10 degrees, handled separately below) each take up exactly HALF
# of Amaterasu's total card span — see module docstring for details.
# Belt sizes elsewhere range from 21 cards (belt 0, White Gaijin) up to
# ~717 cards for Emperor's Black belt.
#
# 2026-10-20 (owner): Amaterasu moved from 13,402 to 13,800 (3: she is one
# of the three noble children, 三貴子; 8: 八百万の神 and the 八咫鏡 mirror),
# with the N1 estimate (freq_data.N1_VOCAB_TARGET). Only Emperor's 8 belts
# were stretched (8,937 → 13,800, same proportions) and Amaterasu's
# reshaped as before (White..Brown 13,800 → 16,900, Black 16,900 → 20,000):
# every belt below Emperor is unchanged, so no one is demoted.
#
BELT_THRESHOLDS = [
         0,     21,     43,     66,     90,    115,    141,    169,
       198,    228,    260,    294,    329,    366,    405,    446,
       489,    534,    581,    631,    683,    738,    795,    855,
       918,    984,   1054,   1127,   1204,   1285,   1370,   1459,
      1552,   1650,   1753,   1861,   1975,   2094,   2219,   2350,
      2488,   2633,   2785,   2945,   3113,   3289,   3474,   3668,
      3872,   4086,   4311,   4547,   4795,   5055,   5328,   5615,
      5916,   6232,   6564,   6913,   7279,   7664,   8068,   8492,
      8937,   9447,   9981,  10542,  11132,  11750,  12400,  13083,
     13800,  14181,  14580,  15000,  15441,  15904,  16390,  16900,
     20000,
]

assert len(BELT_THRESHOLDS) == N_BELTS + 1
assert BELT_THRESHOLDS[-1] == MAX_CARDS

# ── Amaterasu Black Belt degrees ─────────────────────────────────────────────
#
# Only the FINAL belt (global index 79 — Black Belt Amaterasu) is split into
# degrees. Per spec, this belt's span covers exactly the SECOND HALF of
# Amaterasu's total card range — 3,100 cards (16,900 → 20,000) — and is
# divided as:
#
#   First .. Ninth Degree   9 equal ~344-card segments (16,900 → 19,656)
#   Tenth Degree            a single CAPPED value at exactly 20,000 cards,
#                           mirroring how the original (pre-degree) Black
#                           Belt Amaterasu worked: you are not considered
#                           Tenth-Degree until you have truly hit the
#                           20,000-card "native-like fluency" target, not
#                           merely while progressing through the final
#                           degree segment.
#
# No other rank's Black Belt gets degrees — this is purely an Amaterasu-only
# refinement of belt 79.
#
N_DEGREES = 10
_AMATERASU_BLACK_START = BELT_THRESHOLDS[N_BELTS - 1]   # 16,900
_AMATERASU_BLACK_END   = BELT_THRESHOLDS[N_BELTS]       # 20,000
_AMATERASU_BLACK_SPAN  = _AMATERASU_BLACK_END - _AMATERASU_BLACK_START  # 3,100

N_REGULAR_DEGREES = N_DEGREES - 1   # 9 — First..Ninth (Tenth is the capped point)

# 10 boundary values splitting the span into 9 equal degree segments
# (First..Ninth). DEGREE_THRESHOLDS[9] == _AMATERASU_BLACK_END and doubles
# as both "where Ninth-Degree ends" and "the single point where you become
# Tenth-Degree."
DEGREE_THRESHOLDS = [
    _AMATERASU_BLACK_START + round(_AMATERASU_BLACK_SPAN * i / N_REGULAR_DEGREES)
    for i in range(N_REGULAR_DEGREES + 1)
]
DEGREE_THRESHOLDS[-1] = _AMATERASU_BLACK_END   # exact, avoid rounding drift

DEGREE_ORDINALS = [
    "First", "Second", "Third", "Fourth", "Fifth",
    "Sixth", "Seventh", "Eighth", "Ninth", "Tenth",
]


def _degree_index_for_count(count: int) -> int:
    """Return the 0-based degree index (0–9) within Amaterasu Black Belt
    for a count already known to be >= _AMATERASU_BLACK_START.

    0-8 (First..Ninth) come from the 9 equal DEGREE_THRESHOLDS segments.
    9 (Tenth) is returned ONLY when count has truly reached the 20,000-card
    cap — never while merely progressing through the final regular segment.
    """
    if count >= _AMATERASU_BLACK_END:
        return N_DEGREES - 1   # 9 — Tenth-Degree, the true 20,000-card max
    clamped = max(_AMATERASU_BLACK_START, count)
    idx = bisect.bisect_right(DEGREE_THRESHOLDS, clamped) - 1
    return max(0, min(idx, N_REGULAR_DEGREES - 1))   # clamp to 0-8 (Ninth max)


def _belt_index_for_count(count: int) -> int:
    """Return the 0-based belt index (0–79) for a given card count.

    Uses bisect_right so that a count exactly at a threshold boundary
    is placed in the NEW belt (just reached it), except at MAX_CARDS
    which is clamped to belt 79 (Black Belt Amaterasu).
    """
    clamped = max(0, min(count, MAX_CARDS))
    if clamped >= MAX_CARDS:
        return N_BELTS - 1   # 79 — Black Belt Amaterasu
    # bisect_right: BELT_THRESHOLDS[idx-1] <= clamped < BELT_THRESHOLDS[idx]
    idx = bisect.bisect_right(BELT_THRESHOLDS, clamped) - 1
    return max(0, min(idx, N_BELTS - 1))


def get_rank_info(count: int) -> dict:
    """
    Compute full rank/belt info for a given total card count.

    Returns a dict:
      count            - clamped input count
      raw_count        - original unclamped count
      max_cards        - MAX_CARDS (20000)
      overall_pct      - 0.0–1.0 progress toward MAX_CARDS
      rank_index       - 0–9
      rank_name        - combined form e.g. "Samurai (侍)"
      rank_name_en     - English only e.g. "Samurai"
      rank_name_jp     - Japanese only e.g. "侍"
      rank_color_a     - dominant rank hex color
      rank_color_b     - accent/glow rank hex color
      belt_index       - 0–7 within the current rank
      belt_name        - raw belt name, e.g. "Blue" or "Black" (no degree)
      belt_display_name - what the UI should show: same as belt_name except
                         for Amaterasu Black Belt, where it becomes
                         "First-Degree Black" .. "Tenth-Degree Black"
      is_amaterasu_black - True only for the 10 Amaterasu Black Belt degrees
      degree_index     - 0–9 within Amaterasu Black Belt, else None
      degree_ordinal   - "First".."Tenth", else None
      belt_color       - hex for badge text
      belt_bar_color   - hex for progress bar fill
      belt_start       - card count where this belt (or degree) begins
      belt_end         - card count where this belt (or degree) ends
                         (exclusive, or MAX_CARDS if the final one)
      belt_pct         - 0.0–1.0 progress through CURRENT belt/degree only
      is_max           - True if count >= MAX_CARDS
      next_belt_name   - belt/degree name at belt_end, or None if is_max
      next_rank_name   - main rank name if next belt enters a new rank,
                         else None
      cards_to_next    - cards until the next belt/degree threshold, 0 if is_max
    """
    raw_count = count
    clamped   = max(0, min(count, MAX_CARDS))
    is_max    = clamped >= MAX_CARDS

    global_belt = _belt_index_for_count(clamped)
    rank_idx    = global_belt // BELTS_PER_RANK
    belt_idx    = global_belt  % BELTS_PER_RANK

    belt_start = BELT_THRESHOLDS[global_belt]
    belt_end   = BELT_THRESHOLDS[global_belt + 1]

    # Amaterasu Black Belt (global belt 79) only: subdivide into 10 degrees.
    # Every other Black Belt (Gaijin..Emperor) is left as a normal single
    # belt with no degree subdivision.
    is_amaterasu_black = (global_belt == N_BELTS - 1)
    degree_index = None
    degree_ordinal = None
    if is_amaterasu_black:
        degree_index   = _degree_index_for_count(clamped)
        degree_ordinal = DEGREE_ORDINALS[degree_index]
        if degree_index == N_DEGREES - 1:
            # Tenth-Degree: a single capped value at exactly 20,000, exactly
            # like the original (pre-degree) Black Belt Amaterasu cap.
            belt_start = MAX_CARDS
            belt_end   = MAX_CARDS
        else:
            # First..Ninth: override belt_start/belt_end to the DEGREE's own
            # span so belt_pct (and therefore the belt progress bar) reflects
            # progress through just this degree, not the whole Black Belt range.
            belt_start = DEGREE_THRESHOLDS[degree_index]
            belt_end   = DEGREE_THRESHOLDS[degree_index + 1]

    belt_span = belt_end - belt_start
    belt_pct  = (clamped - belt_start) / belt_span if belt_span > 0 else 1.0
    belt_pct  = max(0.0, min(1.0, belt_pct))

    # What comes next?
    next_belt_name = None
    next_rank_name = None
    cards_to_next  = 0
    if not is_max:
        cards_to_next = belt_end - clamped
        if is_amaterasu_black:
            # Next degree within the same Black Belt (or MAX at degree 10)
            if degree_index + 1 < N_DEGREES:
                next_belt_name = f"{DEGREE_ORDINALS[degree_index + 1]}-Degree Black"
            else:
                next_belt_name = None   # already at Tenth-Degree == is_max
        else:
            next_global_belt   = global_belt + 1
            next_belt_idx      = next_global_belt % BELTS_PER_RANK
            next_rank_idx      = next_global_belt // BELTS_PER_RANK
            next_belt_name     = BELTS[next_belt_idx]
            # Entering Amaterasu Black Belt for the first time means landing
            # on First-Degree, not a plain "Black" belt.
            if next_global_belt == N_BELTS - 1:
                next_belt_name = "First-Degree Black"
            if next_rank_idx != rank_idx and next_rank_idx < N_RANKS:
                next_rank_name = MAIN_RANKS[next_rank_idx]

    belt_name   = BELTS[belt_idx]
    rank_en     = MAIN_RANKS_EN[rank_idx]
    rank_colors = RANK_COLORS[rank_en]

    # Display name for the belt label: plain "Black" everywhere except
    # Amaterasu, where it becomes "First-Degree Black" .. "Tenth-Degree Black".
    if is_amaterasu_black:
        belt_display_name = f"{degree_ordinal}-Degree Black"
    else:
        belt_display_name = belt_name

    return {
        "count":          clamped,
        "raw_count":      raw_count,
        "max_cards":      MAX_CARDS,
        "overall_pct":    clamped / MAX_CARDS,
        "rank_index":     rank_idx,
        "rank_name":      MAIN_RANKS[rank_idx],
        "rank_name_en":   rank_en,
        "rank_name_jp":   MAIN_RANKS_JP[rank_idx],
        "rank_color_a":   rank_colors[0],
        "rank_color_b":   rank_colors[1],
        "belt_index":     belt_idx,
        "belt_name":      belt_name,            # raw belt name, e.g. "Black"
        "belt_display_name": belt_display_name, # what the UI should show
        "is_amaterasu_black": is_amaterasu_black,
        "degree_index":   degree_index,         # 0-9, or None
        "degree_ordinal": degree_ordinal,        # "First".."Tenth", or None
        "belt_color":     BELT_COLORS[belt_name],
        "belt_bar_color": BELT_BAR_COLORS[belt_name],
        "belt_start":     belt_start,
        "belt_end":       belt_end,
        "belt_pct":       belt_pct,
        "is_max":         is_max,
        # Alias of is_max with an explicit name — the global "every bar
        # except the belt bar turns gold" trigger used throughout the UI.
        "is_max_amaterasu": is_max,
        "next_belt_name": next_belt_name,
        "next_rank_name": next_rank_name,
        "cards_to_next":  cards_to_next,
    }
