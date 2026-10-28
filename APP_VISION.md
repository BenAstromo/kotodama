# Kotodama 言霊 (JLPT Progress Tracker) — Handbook

> **Read this first after a context reset.** It holds the current state, the rules the add-on follows (and why), the code map and how to work on it safely. It is kept short on purpose: **the full history** (every session log, measurement round and decision story up to 2026-10-26) **is in `docs/HISTORY.md` — grep it, never read it whole.** When a session ends, *replace* §0 instead of stacking new entries on top, and put lasting rules in the section they belong to.
>
> Version 3.0.0 (`__init__.py`, `README.md`, `manifest.json`), author BenAstromo, licence AGPL-3.0-or-later (LICENSE).

---

## 0. Current state (updated 2026-10-27, second session, end)

**Everything is committed and pushed** (https://github.com/BenAstromo/kotodama, private, branch `main`; `git log` for detail). The working folder matches GitHub. The first 2026-10-27 session (Nakama membership per collection, Progress Review, cloth belt label) is logged in `docs/HISTORY.md` → "2026-10-27".

**This session (owner saw the first half in Anki; the bug-round fixes at the end are tested headless, not yet seen):**
- **Marked English loanwords join every count gradually**, not just the rank (§2.4): `card_state.hold_back_loans` runs after each analysis (window + mini widget) and moves loanwords the rank doesn't count yet out of the JLPT known words and the frequency tiers; `results["loans_waiting"]` keeps them. `found_parts` is cached in results (always the full marked list). Word Grid: waiting ones sit in list order among the missing, drawn as missing with a faint ★ (`WordCell(waiting=…)`, `#7a6a3a`); the Missing tab leaves them out. History dates each loanword to the day the cards reached it. Cause: WIGGLE's Nakama card showed 344 words beside 850 JLPT words (2,586 marked, 4 counted).
- **A word is an English loanword if either list's test says so** (`card_state.is_loan`), everywhere marks are split into "loanwords" / "marked found".
- **Marks reach only their own word** (§5b): katakana marks only reach katakana frequency rows (the loanword button had also marked がん via ガン, 鯛 via タイ …: the owner's "6 words marked found"); `word_rank` tiers (own spelling first; kana never lands on a kanji row that only lists it as a side form). 91 JLPT words moved to their right row (ほうき was 放棄, 街 was 町).
- **Nakama ⟳ Refresh recounts first** (the window's full refresh), so your card carries your latest marks. Nakama card / share image: "N English loanwords", "N words marked found" (`share_card._loans_line`, one line for both).
- **Kanji & Grammar:** a Refresh left the old intro + ⟳ drawn over the page; `update_results` now deletes every child but the gold overlay. Other tabs checked: fine.
- **Progress Review:** "+N outside your goal" is a link only (no word list). Days with 0 words draw no bar.
- **Loanword "?" pop-up** rewritten: gradual everywhere, one order (rank counts all counted ones; frequency bars those in the top 20,000; JLPT bars those on a list), JLPT-only loanwords take their level's place (N5 800 … N1 13,800).
- **Regression test** `tools/dev/maint/t_marks.py` (plain Python, 17 checks): run it after any change to marks, `word_rank`, loanwords or history.

**Git:** commit / push only when the owner asks (he usually just says "commit"). `.gitignore` keeps out `user_files/`, `meta.json`, `server/.wrangler/` and caches. Before making the repo public: the release checklist (§11), and decide whether `server/wrangler.toml`'s D1 `database_id` stays.

**Accuracy state:** grammar fresh recall 91 % (tuning stopped); precision A 99 % / N3 94 % / N2 98 % / N1 97 %; `tools/grammar_cases.json` 4,859 rulings, 0 failures. **Not re-run after this session's `word_rank` change:** run `tools/grammar_eval.py` and `tools/vocab_eval.py` once (Text Check uses `word_rank`).

**Open (owner's call unless noted):**
- **WIGGLE needs this version** (folder copy without `user_files/`): his card only changes once his add-on has it.
- Kana words with no frequency row of their own still land on a homophone (と → 都, なんか → 南下, すり → 刷り): needs meaning; left alone.
- **Word Addition Project** (suggested next): 589 candidates in the frequency top 3,900 with no JLPT entry → rules in `tools/missing_words/confidence_rules.py` add 453 (N5 5, N4 40, N3 119, N2 190, N1 99), skip 136. Phone review Artifact https://claude.ai/artifact/NHt9rMw2icW5aSLuNxSLuq: round 1 = ArtifactData `review/choices` (52 owner decisions); `review/round2` saved 2026-10-26 with no changes (= accepted as is; confirm with the owner). Next: add the words in `tools/build_jlpt.py` with flag `ours`, rebuild, run the evals; then the #3,901–6,000 batch (`wa_candidates.json`, db doc `review/round3`); afterwards rebuild `freq_extra.txt` (needs the LUW zip, §6). Details: grep HISTORY for "Word Addition Project".
- **Gamification:** Progress Review built; no streaks. Unpicked ideas (2026-10-26): milestone seals (判子) on bars, level clears (完), rare-word finds, kanji families, grammar "seen in the wild", weekly ink on the History chart, hidden titles on the share image, Nakama nudges. Recommended first: seals + "seen in the wild". Mock-ups before building (§8).
- Rank pictures (only Amaterasu is animated); testing on other PCs; release prep (GitHub page, screenshots, version bump, "Supported Kotodama" line, §11).
- Owner decisions pending: History chart marking-day step; #6 duplicate-card finder.
- Known small issue: renaming a mapped field keeps a stale field index until a note changes or Anki restarts (`tools/dev/maintenance_log.md`).

---

## 1. What this is

An Anki desktop add-on (`addons21/jlpt_progress`, menu **Kotodama**: Open Kotodama / Settings…) that shows a Japanese learner how their deck measures up:

1. **JLPT coverage** — words, kanji and grammar of each N5–N1 level known from the deck.
2. **Kotodama 言霊 Japanese Rank** — Gaijin → Amaterasu from the number of *studied* notes, toward 20,000.
3. **Frequency Check** — coverage of the most common words in written Japanese, so the rank can't be gamed with obscure words.

**The owner** (Ben) is a Japanese learner and the author; plans a free release with voluntary donations. Works by screenshots and short instructions; expects concrete, verified changes. Deck `Japanese::ベンの辞書`; note types Kaishi 1.5k (`Word` / `WordReading`) and Lapis (`Expression` / `ExpressionReading`); live config in `meta.json`.

---

## 2. Philosophy (the "why")

### 2.1 There is no official modern JLPT vocabulary list — be honest about it
- Official lists stopped in 2010. **Every** list out there is based on **Jonathan Waller's** adaptation of the pre-2010 lists (tanos.co.uk). Problems: N3 invented by splitting levels, 1990s vocabulary (ワープロ), no modern words (スマホ), ~8,000 words (too few for N1), archaic kanji in scrapes (有難う).
- **Decision:** the best-cleaned Waller-based list (**OpenJLPT**) + Waller words OpenJLPT dropped + 211 community-list words + our own additions (`ours`), modern spellings only (§6). Other problems are handled by other features: Frequency Check (modern words, size), the loanword button (dated katakana), the Rank (size). Never pretend a list is official.
- Other AIs have made false claims about these lists ("tracks post-2010 data", made-up words). Check claims against the data.

### 2.2 Three lenses
| Lens | Question | Counts |
|---|---|---|
| JLPT bars | How much of each level's list do I cover? | list entries matched to cards (+ marked found) |
| Rank | How big is my vocabulary? | every note in the deck with a studied card (learning, young or mature; `-is:new`), any note type |
| Frequency Check | Are my cards the words that matter? | deck words among the top 20,000 BCCWJ words; bars named by size (Top 800 … Top 13,400, Near Native 20,000), cumulative |

- **13,400 words ≈ comfortably passing N1** (owner's research; where Amaterasu begins; UI says 13,400). 20,000 = "Near Native" (inside published native *active* vocabulary estimates; an estimate, not a standard).
- **"Known" means recognised** (Anki = recognition; immersion → acquisition → production). See memory `learning-philosophy`.

### 2.3 Accuracy over inflation, and over strictness
- **One card = one word.** No credit for homographs/homophones (汚れ よごれ ≠ けがれ; a kana card そう ≠ 層/沿う).
- **The same word counts wherever it's listed**: alternate spellings (できる↔出来る), readings, お-forms, する-verbs, duplicates across levels.
- **Script rule:** a kanji card may count for a kana entry; a **kana-only card never counts for a kanji entry**.
- **Usually-kana words are listed in kana** (JMdict first sense; 275 words: うるさい, さすが, めがね), so both kana and kanji cards count.
- **Different kanji = different word** (2026-10-14): 会う ↛ 遭う, 作る ↛ 造る (N2/N1 test that choice). Only `jlpt_data.same_kanji_forms()` spellings match.
- **One tile per meaning** in the frequency list (`freq_splits.py`): 聞く / 聴く, 帰る / 返る are separate; 年配 / 年輩 stay one.
- Prefer verifiable data rules (JMdict, readings) over hand lists; keep hand lists small and documented.

### 2.4 Owner's learner-centric choices
- **English loanwords** are understandable, so carding them is bloat → **Mark English Loanwords as Found** button. Marked loanwords join **every count (rank, bars, history, goal, Nakama) gradually**, most common first, as your vocabulary reaches them (`card_state.loans_counted` / `hold_back_loans`, owner 2026-10-27); the marks stay. Test: *would an English speaker hearing it in context land on the right thing?* `COUNT_AS_ENGLISH` (always), `FALSE_FRIENDS` and `NOT_ENGLISH` (never) in `jlpt_data.py`; wasei / non-English / unguessable abbreviations excluded.
- **Licensing:** the owner optimises for JLPT relevance and knowingly ships trimmed BCCWJ derivatives (CC BY-NC-ND; accepted risk; plan B = ship NINJAL's original file and trim at load time). Always credit every source (§12).
- **Fewer settings**: fixed sensible behaviour over checkboxes; unlockables stay hidden until earned.

### 2.5 Gamification
- 10 ranks × 8 belts (exponential, ~1.05 per belt); Amaterasu's Black Belt has 10 degrees, the Tenth at exactly 20,000. Amaterasu is a surprise: never named in frequency text; its art is blurred behind "?" until reached.
- **Amaterasu gold mode (20,000):** bars turn gold and the UI turns gold Japanese (`divine_text.py`). Any new bar/label must respect it (§8).
- **Never show 100 % unless complete** (`jlpt_data.format_pct` / `format_progress`).
- Time with Kotodama (loyalty badge) is earned by time, never money.

---

## 3. Features (current)

**Main window** (`ProgressDialog`): header (Kotodama 言霊 | JLPT Tracker, moon), tabs:
1. **Vocabulary** — All N Levels Combined + N5–N1 bars (click → word grid pop-up), "+N today / week / month", rank badge / rank bar / belt bar, **JLPT Goal** card (`goal.py`, `goal_view.py`: level + test date → words / kanji / grammar per day), Frequency Check bars, share image button.
2. **Word Grid** — JLPT words: known level by level (Mature → Young → New, ★ marked found last, most common first), then missing. Hover = meaning (Jitendex); click known → Browser, missing → copy; Shift+click → Jisho; middle-click found; Ctrl+middle suspend.
3. **Missing** — Vocab / Kanji / Grammar switch; sortable, filterable, Copy all.
4. **Marked & Suspended** — found and suspended lists (each in its own card with its Reset button), loanword button, Show / Sort.
5. **Off-list** — deck cards on no list (still count for rank + frequency); tile grid | table splitter.
6. **Kanji & Grammar** — compact bars; heatmap grids (strength = mean card score; red → cyan); grammar from the sentence parser or a grammar deck; "find it in your deck" search.
7. **Text Check** — paste text / open subtitles → coverage, verdict, unknown words (`text_check.py`).
8. **History** — chart of rank, JLPT, frequency over time (`history.py`, `history_view.py`); daily auto snapshot + "Take snapshot now".
9. **Nakama 仲間** — friends board (`nakama.py`, `nakama_view.py`; server `server/worker.js`, Cloudflare Worker + D1, not shipped).

**Grid pop-ups**: word / frequency / kanji / grammar grids, 900×890, glowing tile shape, neon flicker-on as rows come into view, search box with complementary-colour highlight.

**Progress Review** (`review.py`, `review_view.py`, owner 2026-10-27, mock-up A): today on the left (Words / Kanji / Grammar, each grammar point with its own sentence and the matched part underlined), the past 7 days on the right (totals, needed pace, a bar per day dimmed under the target, words by day, kanji, grammar). With a goal its items come first and the rest is one "+N outside your N2 goal" link (opens them all; no word list, owner 2026-10-27); without one, off-list words are the extra. Every heading opens everything under it in the Browser, every item just its card, a day line / bar that day's (no buttons, owner). Opened by every "+N today / this week / this month" link (this month → past 30 days) and the goal card's "Today"; outside the main window those still open the Browser. Pops up by itself the first time the main window opens after the day's word target is reached (`REVIEW_POP_MS` after the intro; config `review_popped` = the day). Rebuilt on every open. Not on the mini widget (owner: the widget only opens the main window). No streaks (owner 2026-10-27: Review Heatmap already shows one; not even a weekly one).

**Elsewhere:** mini widget on the deck list (`mini_widget.py`: N5–N1 bars, rank + belt bars, optional rank picture, rank-up banner; click → main window, precounted in the background); rank-up toast while reviewing (`rank_toast.py`); Settings (`config_dialog.py`: deck, field mappings incl. sentence fields, sources, mini widget, ignore suspended, Night look, sound volume); "♥ Support" bottom-left; review seal (`seal.py`, Amaterasu only).

**Atmosphere** (each its own Settings switch, faint by default): night sky + moon + stars (`attach_sky`), rain on the glass (`rain.py`), light spill / reflections, bokeh, vignette, condensation (`effects.py`); neon flicker sound (`neon_sound.py`), Amaterasu star ambience (`ambience.py`), chime (`chime.py`). Sounds start quiet and mute when the window is unfocused.

**Busy notes** (`busy.py`): any wait > a moment shows a "… / Please wait…" note over the window; never Anki's progress bar.

---

## 4. Code map

| File | Role |
|---|---|
| `__init__.py` | Entry point, menu, config helpers; **matching engine** (`collect_words`, `_find_match`, `analyse`, reading helpers); `_open_progress_dialog` / `prepare_dialog` (background precount for the widget click). |
| `jlpt_data.py` | `LEVELS`, `LEVEL_COLORS` / `LEVEL_BG`; list loading (5 columns), alt forms/readings (`_merge`), `same_kanji_forms`, loanword sets, `format_pct` / `format_progress`. |
| `freq_data.py`, `freq_splits.py` | Frequency list load (+ `_merge_reading_splits` at load time), tiers, `coverage()`, `word_rank(_info)`, `rank_text`; tile-split decisions. |
| `progress_dialog.py` (~7,700 lines) | All main UI: `LevelBar`, `RankBadge`, `RankBar`, `BeltBar`, `WordCell`, `_TileCanvas` + `_NeonZone`, `WordGridPanel`, `_fill_table`, panels, `OverviewTab`, `ProgressDialog`, night sky, neon intro, grid window helpers. |
| `kanji_view.py` | Kanji & Grammar tab, `KanjiCell` / `GrammarCell` (heatmap), grid panels, kanji → words window, Missing / M&S kanji-grammar panels. |
| `kanji_data.py`, `grammar_data.py`, `sentence_parser.py` | Kanji analysis + `card_score` (FSRS); grammar detectors / context checks / token rules (§5c); the pure-Python parser. |
| `text_check.py`, `text_check_view.py` | Text Check logic (no Qt) and tab. |
| `card_state.py` | Scheduling state, `deck_query` (escapes deck names), `note_maturity`, `rank_count`, pseudo nids for parsed words, `run_in_background` (QueryOp + `ANALYSIS_LOCK`). |
| `history.py`, `history_view.py` | Snapshots in `user_files/history.json`, revlog backfill, `build_series`; chart. |
| `goal.py`, `goal_view.py` | JLPT goal. |
| `review.py`, `review_view.py` | Progress Review: today + last 7 / 30 days of learned words, kanji, grammar (from the history series' gains); once-a-day pop-up. |
| `rank_data.py`, `rank_images.py`, `rank_video.py`, `media/` | Rank/belt math and colours; rank art; animated rank pictures. |
| `mini_widget.py`, `rank_toast.py` | Deck-list widget (HTML), rank-up toast/banner. |
| `overrides.py` | Found / suspended marks (`user_files/*overrides.json`), atomic saves, copy-on-write, `keep_unreadable`. |
| `theme.py`, `busy.py`, `effects.py`, `rain.py`, `neon_sound.py`, `ambience.py`, `chime.py`, `seal.py` | Window theme (`fit_on_screen`), wait notes, atmosphere and sound. |
| `divine_text.py` | Gold-mode Japanese for every English UI text. |
| `share_card.py`, `loyalty.py`, `nakama*.py` | Share image, Time with Kotodama badge, friends board. |
| `config_dialog.py`, `migrate.py` | Settings; moving `user_files` to the AnkiWeb folder. |
| `meanings.py` + `meanings.json` | Hover meanings (Jitendex). |
| Data (generated, never hand-edit) | `jlpt_n1..5.txt`, `freq_bccwj.txt`, `freq_extra.txt`, `kanji_jlpt.txt`, `grammar_jlpt.json`, `meanings.json`, `kana_ok.txt`, `kana_usual.txt`, `kinds_fix.txt`. |
| `user_files/` | Survives updates: overrides, history, goal, nakama, parse caches. `overrides1.json` at the root: old backup, leave it alone. |
| `tools/` | Builds (§6), evals (§9), `harness.py`, `build_package.py`, `check_gold_text.py`, `accuracy/`, `missing_words/`, `dev/` (Qt test harnesses, `maintenance_log.md`). Not shipped. |
| `README.md` | User docs + credits; keep in sync with features. |

---

## 5. Matching algorithm (JLPT lists ↔ deck)

**`collect_words`** scans the deck (and sub-decks) via the field mappings: display from `_extract_words` (strips HTML, furigana, brackets; first word), reading from `_extract_reading` (kana, `漢字[かな]`, `<ruby>`; alternative readings kept as ・). Duplicate (display, reading) pairs are skipped (they still count for rank).

**`_find_match`** → `(nid, soft)`; kana-only cards are filtered out for kanji entries at every step:
1. Exact display (prefers exact reading → alternate reading → no reading). 1b. Alternate spellings (same-kanji only).
2. Kana card whose display = the entry's reading. 3. Reading-field match if the reading is unique across lists.
4. お/ご + kanji entry ← bare card (**soft**). 4b. Bare entry ← お/ご card.
5. Same word listed twice (spelling + accepted reading), even if claimed (**soft**).

**`analyse`** (N5 → N1): drops お-duplicates within a level; suspended words skip counts but claim their card; marked-found with no card = known with `nid=None`; `_claim` uses one reading per entry (何 なに・なん serves two). **Off-list** = cards not claimed, soft-matched, partly used, or duplicates of a JLPT word.

### 5b. Frequency matching (`freq_data.coverage`)
Kanji cards: display = an entry spelling and (if it has a reading) a matching reading. Kana cards: the entry spelled in that kana, else only the single most common kanji entry with that reading. `nid_rank` / `nid_rank_extra` sort Off-list views.
- **`word_rank`** (a JLPT word's frequency row: marks, hover ranks, the JLPT level on frequency tiles, Missing tab, goal pool, Text Check; not card counting) picks by tier, then commonest: the row spelled like the word → a row listing its spelling → the same for the list's alternate spellings → a kana word by its sound (the row's main reading) → a kana variant of a kana row. A kana word never takes a kanji row that only lists it as a side form (BCCWJ lists わた under 海, じゃ under 蛇). 2026-10-27.
- **Marks across lists** (`mark_ranks`, `card_state.found_key`): a JLPT mark reaches its frequency row through `word_rank`; a **katakana mark only reaches a katakana row** (BCCWJ lists ガン as a spelling of がん, タイ of 鯛). `tools/dev/maint/t_marks.py` checks both.

### 5c. Sentence parser and grammar
- **Config:** a mapping row with `sentence_field` but no `field` is a **sentence card**. `kanji_source.mode` vocab / sentence / fields; `grammar_source.mode` sentence / fields; hand marks always count. Parsed words get pseudo nids (`nid × 1000 + i`, `card_state.pseudo_nid` / `real_nid`).
- **Parser (`sentence_parser.py`):** dictionary = frequency list + JLPT lists (+ compounds); Yomitan-style deinflection typed by POS (`meanings.json`, `kinds_fix.txt`); lowest-cost whole-sentence split (`words_in`; kanji 1.0, kana 1.2, rare short kana costlier, function tokens); `kana_ok.txt` lets usually-kana words match in kana; katakana names are one unk token. Also feeds Text Check, so vocab accuracy matters.
- **Grammar (`grammar_data.py`):** regex detectors per distinctive written form (`_tail` conjugation, gap rules) + `_NOT_AFTER` / `_NOT_BEFORE` guards + `_CONTEXT` checks (id → fn(text, match)) + token rules from the parser's split (particles, endings path, passive, keigo). `EXTRA_FORMS` adds variants; `SENTENCE_SKIP` = hand-mark only. Every rule was checked against real sentences; rulings live in `tools/grammar_cases.json`.
- **Accuracy method:** fresh Tatoeba samples (`tools/accuracy/`, new seed each time), precision set A (as they occur) + B (50 per level), recall by annotating every point in 100 sentences; quote 95 % CIs. **Stop when fresh samples stop moving** (memory `stop-when-diminishing`); what's left needs meaning, which the add-on won't model.
- Owner decisions: no "label your sentences" review; basic particles have a ★ Mark-as-found toggle; grammar hand marking always on.

---

## 6. Data pipeline

All bundled data files are **generated**: fix the build script and rebuild, never hand-edit. Scripts in `tools/` run **from a working folder containing `data/` and `ojlpt/`** (currently `%TEMP%`: `data/jmdict.pkl`, `data/JMdict_e.gz`, `data/bccwj_suw.zip`, `ojlpt/…`; `%TEMP%` gets cleaned, re-download if missing). Run `py -I -X utf8 tools/<script>.py <addon_dir> …`; build to a scratch folder and diff against the current files before replacing.

| Data | Source | Notes |
|---|---|---|
| JLPT lists | OpenJLPT `data/json/vocab/n*.json` (CC BY-SA 4.0) | `build_jlpt.py`: + all JMdict spellings/readings, usually-kana relisting, `ADDITIONS` (Waller words OpenJLPT dropped), `COMMUNITY_ADDITIONS` (211, flag `community`), `OUR_ADDITIONS` (flag `ours`). Format `word	reading	alts	flags	alt readings`. |
| Dictionary | JMdict_e.gz (EDRDG, CC BY-SA 4.0) | `jmdict_parse.py` → `data/jmdict.pkl`. |
| Frequency | BCCWJ SUW v1.0, NINJAL record 3234 (CC BY-NC-ND 3.0) | `build_freq.py`: content POS only, **laws register excluded**, one JMdict entry per lemma, `DROP_LEMMAS` (ウ, ア). Download needs a referer: `curl -e https://repository.ninjal.ac.jp/records/3234 -A Mozilla/5.0 https://repository.ninjal.ac.jp/record/3234/files/<file>`. |
| Extra ranks | BCCWJ LUW v1.0, record 3228 (57 MB zip) | `build_freq_extra.py`: exact ranks 20,001–40,000 + ≈ estimates for compounds; display/sorting only. **Stale**: rebuild after the Word Addition Project. |
| Meanings | Jitendex for Yomitan (CC BY-SA 4.0) | `build_meanings.py <addon_dir> <zip>`. |
| Kanji / grammar | OpenJLPT kanji + grammar JSON (KANJIDIC2 data) | `build_kanji.py` (2,383 kanji; `supp` = needed by vocab), `build_grammar.py` (526 points). |
| Parser aids | JMdict; MeCab/UniDic (dev only) | `build_kana_ok.py`, `build_kana_usual.py`, `build_kinds_fix.py`. MeCab (fugashi + unidic-lite) lives in `%LOCALAPPDATA%\jlpt_devtools\pylib`, never shipped. |
| Corpus | Tatoeba jpn sentences (CC BY 2.0 FR) | `%TEMP%\data\tatoeba\jpn_sentences.tsv`; evaluation only. |

Deliberately not done: dropping white papers / Diet minutes (they hold N2/N1 vocabulary); filtering compound fragments (会, 県); dropping counters.

---

## 7. Decision log (short; the stories are in HISTORY)

| Topic | Decision | Rejected / why |
|---|---|---|
| JLPT source | OpenJLPT + JMdict + additions (above) | japandict scrape, stephenmk lists (archaic forms); all Waller-based anyway. List-source toggle not built (same data). |
| Kana vs kanji | Script rule + usually-kana relisting | Stricter relisting by jōyō kanji: owner kept current behaviour. |
| Homophones | Kana cards never count for other words that sound the same | — |
| Frequency source | BCCWJ (written, balanced); LUW only for ≈ ranks | Jiten (fiction-heavy), JPDB (no licence); BCCWJ + Jiten blend on hold (#12; licence conflict). |
| Frequency tiers | Top 800 / 1,500 / 3,900 / 6,000 / 13,400 + Near Native 20,000, named by size | Arbitrary 1k/5k/10k; a 30,000 "Native" target. |
| Different kanji | Different word | Old behaviour counted them together. |
| Tile order | Every grid: Mature → Young → New, ★ found last; JLPT grid level first; most common first inside | — |
| Kanji strength | Heatmap of mean card score (FSRS stability, light difficulty, lapses); maturity only on hover | Ease (meaningless under FSRS); heavy difficulty weight. |
| Kanji & grammar placement | One tab, compact bars, grids via the bars | They don't affect rank or word counts. |
| Add missing words to Anki | Dropped: click copies, owner uses Yomitan | — |
| Loanwords / dated words | One button marks found; dated katakana in `COUNT_AS_ENGLISH`; Suspend Dated Words removed | "Suspend all katakana" too blunt. |
| Off-list name | "Off-list" | "Non-JLPT" (implies not on the test). |
| Belt bar | Centred, grows outwards; rank bars left-aligned | — |
| Colours | Level colours §8; N4 stays #8bc34a; frequency sky blue; Off-list dark blues; All Levels white with red glow | Yellower N4; shared blue for frequency/Off-list. |
| History | Backfill from revlog + note first review; daily auto snapshot; `user_files/` | Dating by nid (shared decks keep the author's nid). |
| Grid glow | The tiles' shape glows, not each tile; kanji/grammar glow follows the heatmap | Per-tile glow (small words unreadable). |
| Debug buttons | Visible; the owner removes them before release | — |
| Ranks 11–12 (Susanoo, Tsukuyomi) | Parked (#14); plan in HISTORY | — |
| Custom word lists | Removed 2026-10-26: always the Kotodama JLPT lists (`build_lists` ignores the old `lists` config) | Per-level upload: Nakama / History / Goal numbers stop being comparable; uploads lack JMdict ids. Text Check covers "how much of list X do I know". |
| Settings layout | One scrolling page: deck, field mappings, kanji, grammar, suspended, then widget / Amaterasu / sound / animations / Night look | Three tabs (Deck & Fields, Vocabulary Lists, Kanji & Grammar). |

---

## 8. UI conventions & constants

- **Level colours** (`jlpt_data`): N5 #4caf50/#1b5e20, N4 #8bc34a/#33691e, N3 #ff9800/#e65100, N2 #f44336/#b71c1c, N1 #9c27b0/#4a148c. Gold #f5c518; found border #ffe066; suspended ✕ #e05a5a; `MISSING_GLOW` #6a6a6a.
- Numbers: thousands separators; one decimal; never 100.0 % unless complete.
- Tables left-aligned; big tables via `_fill_table`.
- Pop-ups and the main window get min/max buttons. Grid pop-ups: `size_grid_window` + `place_grid_window`.
- **Font sizes** for labels under a Kotodama window go in the label's own style sheet (theme.py's `QDialog#kotodama QWidget` font-size beats `setFont`, also in owned pop-ups).
- **Waits:** busy.py notes, never Anki's progress bar (`card_state.run_in_background` without a label).
- **Gold mode:** new bars `LevelBar(..., force_max_gold=..., colors=..., clickable=...)` added to `_freq_bars` / `_level_bars`; new labels in `_set_level_label_gold`; text set after build → `_regold(widget)`; only gold, black #0d0b08 and white in gold mode.
- **Gold text protocol** (memory `gold-text-protocol`): every English UI text gets its Japanese in `divine_text.py` (`EXACT`, `PATTERNS`, `PHRASES`, `HEADERS`, `PLACEHOLDERS`) in the same change; `tools/check_gold_text.py` must print OK. Settings and tooltips stay English. Never remove English the owner wrote (`_AMATERASU_MESSAGE_EN`).
- **Naming the word lists:** user-facing text says **"the Kotodama JLPT lists"** (gold: 言霊のJLPTリスト), never "bundled lists" (owner 2026-10-26: confusing once custom lists were gone). "Bundled data" stays fine for licences and shipped files.
- **New visuals:** offscreen mock-ups of 2–3 variants first, owner picks; new effects start very faint, one tunable constant each, each its own switch; new sounds start low.

---

## 9. Developer workflow & gotchas

- **Git repo** (`main`, GitHub `BenAstromo/kotodama`, private). Scratch files go in the session scratchpad, never the add-on folder; delete your own leftovers (memory `clean-up-own-files`).
- **Python:** `%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe` (no PyQt). `python` / `py` on PATH are Microsoft Store stubs. Anki bundles Python 3.13 + PyQt6; keep code Python 3.9-compatible (checked in each round).
- **After grammar / parser changes:** `py -I -X utf8 tools/grammar_eval.py` (0 failures; read the diff; `--update` to accept) and `tools/vocab_eval.py` (0 diffs). For corpus effects: `tools/dev/dump_ids.py` + `diff_sample.py` (full dump ≈ 5 min), judge a sample of gained/lost credits.
- **After UI text changes:** `tools/check_gold_text.py`.
- **Real Qt offscreen:** venv `%TEMP%\qtv` (PyQt6; `py -m venv --upgrade qtv` if python.exe vanished); PyQt5 venv `%TEMP%\qt5v` with `KT_QT=5`. `tools/dev/qt_neon.py` builds the real add-on over a synthetic 8k-note collection; reuse its first ~192 lines as a harness. Its scratch dir must be **outside** the add-on folder, and it swallows `print`: write results to a file. New Qt classes / gui_hooks → add them to the tools' stub lists (`tools/dev/maint/stubenv.py`).
- **Stub lists:** the headless tools fake Qt with a fixed name list (grammar_eval.py, grammar_review.py, harness.py, missing_words/stubs.py, speed_test.py) and a fake `mw.form` / `gui_hooks`: a new Qt class used at import time, `mw.form` attribute or `gui_hooks.<name>` must be added to all of them, or every eval crashes. Always run the evals after UI work too.
- **Offscreen regression suite:** `tools/dev/maint/` (README there; `t_scenarios.py`, `t_leaks.py`, `t_nakama_offline.py`, invariants; `t_marks.py` needs no Qt). Re-run after risky changes. It missed two kinds of bug found 2026-10-27: a mark landing on another word (only a data-level check finds it) and widgets left over after a tab's Refresh (only looking after a Refresh finds it).
- **Parser tie-break:** frequency is a separate DP key in `sentence_parser.tokens`; never fold tiny costs into the main cost (old splits once flipped on float rounding).
- **Headless matching:** `tools/harness.py <scratch>` on a **copy** of `collection.anki2` (`C:\Users\benne\AppData\Roaming\Anki2\Ben\`; never touch the original; delete the copy after); `tools/anomaly_scan.py` after any matching change. The owner's collection may be blocked: use `user_files/parse_cache.json` texts for sentence audits.
- **Shell:** the owner's terminal is PowerShell 5.1 (`;` not `&&`). Long patches as `.py` files rather than inline Python. Edit tool for code edits (heredocs mangle `\n` / `\uXXXX`).
- **Mini widget HTML:** Anki's deck list sits in `<center>`; the widget sets `text-align: left`, centre things with `margin: auto`.
- **Review pages for the owner:** private Artifacts with the db capability, split by confidence (memory `review-on-phone`). Never use port **8765** (AnkiConnect); stop preview servers after use.
- **Anki crash diagnosis:** ask the owner to run `anki-console.bat` from the Anki install folder.
- **Packaging:** `tools/build_package.py` (skips APP_VISION.md, docs/, tools/, server/, user_files/).
- After anything user-visible, update `README.md`.

### Baseline numbers (owner's deck, 2026-10-26, loanword button pressed; from 2026-10-27 the bars count only the loanwords the rank counts, so these are higher than now)
All levels 3,006 / 8,064 (2,504 from cards + 501 loanwords + 1 marked); N5 661/682, N4 570/640, N3 843/1,703, N2 412/1,827, N1 520/3,212; Off-list 735; marked found 2,594. Large unexplained swings after a change mean something broke. Script-rule check: JLPT known words whose list display has kanji but whose card has none must be 0.

---

## 10. Open questions (ask the owner before acting)
1. Rank/belt colour legibility — waiting for the owner's screenshots.
2. History chart marking-day step; #6 duplicate-card finder — explained, undecided.

## 11. Backlog and release plan
- Open backlog: #6 duplicate finder (undecided), #11 listening frequency bar (maybe), #12 BCCWJ + Jiten blend (on hold), #14 Susanoo + Tsukuyomi ranks (parked). Everything else in the original backlog is built.
- **Release:** release-ready first (parser vocab accuracy measured like grammar), then roadmap + licence audit (JMdict, Tatoeba, OpenJLPT, BCCWJ, AnkiWeb rules on donation links). Launch with only the Ko-fi one-time donation ("♥ Support", bottom-left, never a popup). "Supported Kotodama" line: verified via Ko-fi webhook → Nakama Worker (plan in HISTORY, not built). Rank-up ribbons on the share image and supporter cosmetics: ideas, not part of the first release; earned things (rank, glow, belts) never change with money.
- **Positioning:** grammar coverage of your own sentences and any text is the strongest unique claim (measured precision/recall above).

## 12. Credits that must stay in README / list headers
- OpenJLPT (CC BY-SA 4.0); Jonathan Waller's JLPT lists (CC BY)
- JMdict, EDRDG (CC BY-SA 4.0); KANJIDIC2 via OpenJLPT kanji
- BCCWJ short- and long-unit frequency lists, NINJAL (CC BY-NC-ND 3.0; trimmed files are derivatives, accepted by the owner)
- Jitendex, Stephen Kraus (CC BY-SA 4.0): hover meanings
- Tatoeba (CC BY 2.0 FR): evaluation only
- stephenmk/yomitan-jlpt-vocab, jamsinclair/open-anki-jlpt-decks, elzup/jlpt-word-list (community additions)
