# Kotodama 言霊 (JLPT Progress Tracker) — Handbook

> **Read this first after a context reset.** It holds the current state, the rules the add-on follows (and why), the code map and how to work on it safely. It is kept short on purpose: **the full history** (every session log, measurement round and decision story up to 2026-10-26) **is in `docs/HISTORY.md` — grep it, never read it whole.** When a session ends, *replace* §0 instead of stacking new entries on top, and put lasting rules in the section they belong to.
>
> Version 3.0.0 (`__init__.py`, `README.md`, `manifest.json`), author BenAstromo, licence AGPL-3.0-or-later (LICENSE).

---

## 0. Current state (updated 2026-10-31, eighth session)

**Everything is committed and pushed** (https://github.com/BenAstromo/kotodama, private, branch `main`; `git log` for detail). Earlier sessions are logged in `docs/HISTORY.md` (grep the date).

**This session (2026-10-30/31; owner checked in Anki: all clear):** new Nihonjin, Tourist and Samurai pictures; Shogun cropped to 480×320; Shogun and Naijin pictures kept (accepted risk); no rank-picture credit line anywhere. **Nihonjin and up are animated** (`media/<rank>_loop.webm`) in the Overview badge, the mini widget, the All Ranks window and the Nakama tab; Amaterasu still only in Amaterasu mode. Fixed the owner's goal showing 0 kanji / grammar a day: the hidden debug button "★ Mark All JLPT Found" had marked everything found (their marks were cleared by hand). Loop recipe and details: HISTORY, "eighth session".

**Tests to run after related changes:** `t_marks.py`, `t_dups.py`, `t_kofi.mjs`, `tools/dev/qt_goal.py` and `tools/dev/test_gain.py` (PyQt6 venv `%TEMP%\qtv`), `tools/dev/maint/t_scenarios.py normal` (delete its `env/` after), `tools/grammar_eval.py` + `tools/vocab_eval.py` (0 differences from baseline 2026-10-28, rechecked 2026-10-29 after the speech round), `tools/check_gold_text.py` after any UI text, `parse39.py` / `compat39.py` before a commit.

**Git:** commit / push only when the owner asks (they usually just say "commit"). `.gitignore` keeps out `user_files/`, `meta.json`, `.wrangler/`, `server/.wrangler/` and caches. Before making the repo public: the release checklist (§11). `server/wrangler.toml`'s D1 `database_id` stays public (owner 2026-10-27: it's a label, not a secret).

**Accuracy state:** grammar fresh recall 91 % (tuning stopped); precision A 99 % / N3 94 % / N2 98 % / N1 97 %; `tools/grammar_cases.json` 4,859 rulings, 0 failures; vocab recall 99.4 % / precision 99.3 %.

**Open (development only; owner's call unless noted):**
- **Owner checks:** one real Ko-fi tip ("♥ Supported Kotodama"; test `node tools/dev/maint/t_kofi.mjs`; refunds: clear `supporter` by hand; wrangler from the add-on root needs `--config server/wrangler.toml`).
- **Word Addition Project: done** (written #1–6,000 + speech #1–6,000). Speech round notes, rows keyed `r<srank>`, Artifact page via `speech_round.py <out.html>`.
- **Word Addition Project follow-up:** rebuild `freq_extra.txt` (§6; display/sorting only). `tools/build_freq_extra.py` already follows build_freq.py's newer mapping (DROP_LEMMAS, ずる→じる, POS fit, KIND1_SPLITS; untested); waits on the owner downloading both NINJAL zips (records 3228 + 3234): the NINJAL repository is down for maintenance since 2026-10-28 15:00 (no end date given); the script download (curl with referer, §6) should work again once it is back. No further batches past #6,000 (owner 2026-10-28). Review pages: https://claude.ai/artifact/NHt9rMw2icW5aSLuNxSLuq (db docs `review/choices`, `round2`, `round3`), fit check https://claude.ai/artifact/Niz5EFogy6r2itUmLuNyc1. Grep HISTORY for "Word Addition Project".
- **Licence (release_drafts.md §7):** Owner 2026-10-28: no NINJAL email (free add-on, credited, tip-only Ko-fi; accepted risk), no Grok credit. Done: BCCWJ + CEJC paper citations in README and About ("Corpus references"). No credit line for the rank pictures anywhere (owner 2026-10-31: removed "made for Kotodama" from About, README, release drafts).
- **Rank pictures: done** (owner 2026-10-31). Any rank with `media/<rank>_loop.webm` plays it wherever its picture shows; new loops: owner records the Wallpaper Engine scene in OBS (aim for ~1248×832, 60 fps, ~30 s), cut with the recipe in HISTORY ("eighth session"). The Shogun redo prompt stays in release_drafts.md.
- **Public README + AnkiWeb text: written 2026-11-01** (README = landing page with screenshots in `docs/screenshots/`; the old detailed manual moved to `docs/GUIDE.md`; AnkiWeb HTML in release_drafts.md §6, images from raw.githubusercontent, so they only load once the repo is public). Still to do: **owner reads through the README and the AnkiWeb text (release_drafts.md §6) by hand** before release; replace `history.png` (its graph shows a drop and bump from the owner clicking the loanword button off and on); owner swaps `rank.png`, `nakama.png`, `main-screen.png` (and `mini-widget.png`) for GIFs, retaken **without the debug row**; fake Nakama friends for the screenshot (Claude, next session); maybe retake `text-check.png` (pasted Aozora text carried ruby readings, 吾輩わがはい, which look messy and lower the score; a modern text would show a friendlier verdict than "63.3 % · Hard", and Show: Grammar is worth a shot); fill `[ANKIWEB CODE]` after upload.
- **Repo scan before going public (2026-11-02, all 50 commits):** clean of secrets: no user_files / meta.json / overrides / nakama.json / backups / collection files ever committed; no keys, tokens or e-mail addresses in any file. **Owner decisions:** (a) every commit's author name is **"Bennett Hannemann"** (e-mail is GitHub's noreply), so the real name shows on the public repo: **owner 2026-11-02: keep it** (no history rewrite); (b) the Windows user path `C:\Users\benne` is in ~26 dev files (tools/, docs/HISTORY.md, APP_VISION.md, `.claude/launch.json`): harmless, **owner: leave it**; (c) `tools/grammar_cases.json` (4,859) and `tools/grammar_eval_baseline.json` hold short sentences from the owner's own deck (mined cards), besides Tatoeba samples (credited): **owner: keep**. Turn on GitHub Issues when public.
- **Release prep (§11):** launch as soon as possible, no date (owner 2026-10-30: someone could build a similar add-on with AI). Testing on other PCs (the ESAN friend's copy counts), public GitHub page + screenshots, demo video (owner narrates), AnkiWeb upload, version bump (3.0.0 now). Launch posts: Anki Forums → r/Anki → r/LearnJapanese (check self-promo rules) → r/JLPT / r/LearnJapaneseNovice; TheMoeWay Discord (owner joined 2026-10-29) after taking part a few weeks. Organic only, no accuracy numbers.
- Known small issues: renaming a mapped field keeps a stale field index until a note changes or Anki restarts (`tools/dev/maintenance_log.md`); the mini widget can't see the past 7 days (only matters for weekly kinds, which it never shows).
- Backlog: **parser words past #20,000** (owner 2026-11-01, wants ~60,000): the parser's lexicon is only the JLPT lists + `freq_data.parser_rows()` (top 20,000 + safe compounds), so rarer words are "unknown pieces" in Text Check and sentence cards; check whether a learned off-list card past #20,000 counts as known in Text Check (likely not). Do it with the `freq_extra` rebuild (same NINJAL download; extend past 40,000), let rare words only fill gaps (never beat a common word), re-run grammar_eval + vocab_eval (0 differences expected on the eval sets).
- **Goal / review / widget fixes: done 2026-11-02, uncommitted, owner to check in Anki.** (1) **N2 goal = just the lists** (`goal.FREQ_GOALS` is N1 only): step 2 had stayed alive for the lists' last 4 words, and `today_parts` counted *every* top-6,000 word not on the N5–N2 lists (N1-list words too: 優先, 鍛える, 採取, 化する) in "Today" with no cap, so "Today" said 13 while the Progress Review listed 10. (2) **Progress Review "outside your goal" = list words above the goal only**; off-list words (性癖) show only without a goal (`review.build`). (3) **Mini widget stale after reviewing: same root cause.** The window saves the day's start for the widget as known − today's gains; the uncapped step-2 gains made that start too low by the step-2 words seen so far, so words studied after the window's last opening were missing on the widget (owner's 7 vs 11) until the window reopened. Tests: qt_goal (N2 tests rewritten: no steps, lists only, loanwords 1,000; N1 step-2 loanwords; N1 without frequency data), test_gain, t_scenarios normal, t_marks, py3.9: all pass. Left as is: an N1 goal's "Today" still counts step-2 words past step 2's need once it's full (need ≈ 4,000, so only near the end).
- **"No such card" error (owner 2026-11-02): not Kotodama.** Checked every hook: no editor hooks; the reviewer hooks (rank_toast, seal) only read the rank count and add the seal HTML; nothing loads, changes or deletes cards or notes. Likely another add-on (AJT Japanese, Auto-refresh browser, Multiple Browser Windows). Owner: run Tools → Check Database.
- **Review our JLPT additions (`ours`, 1,742 words): review page live 2026-11-02, owner to go through it** — https://claude.ai/artifact/7jpfpe28AMxkxZh7oDAery (db doc `review/choices`: {"choices": {"<level>|<word>|<reading>": "keep"|"drop"}}). Claude's confidence that each word really appears on the JLPT: 5 very likely 592 · 4 likely 174 · 3 possible 543 · 2 unlikely 392 · 1 very unlikely 41 (by hand: taboo/slang/history-drama/food katakana down, core register up; default 3). After the owner's pass: read the doc, drop the "drop" words from `OUR_ADDITIONS` in build_jlpt.py, rebuild the lists, rerun vocab_eval / grammar_eval. Also recheck the README's example words (メール, 私たち, 可能性, 動画 / スマホ, 終電, 部活, 飲み会). (性癖 was never ours: an off-list card in the Progress Review, fixed.)
- **Done 2026-11-02, uncommitted, owner to check in Anki:** (a) **loanword marks on the History chart**: snapshots keep their loanword share (`loans`), `history.loans_on_chart` swaps it for the current marks' share from `loans_since` (set the day the button is pressed; "start" for marks made before this; cleared on unmark), so unmarking leaves no drop or bump and marking jumps on its day; old snapshots without `loans` are matched to the nearer of with/without; gains unchanged. (b) **Bokeh stays off the UI**: `_NightSky._bokeh_clip` leaves out section cards (`kcard`), the History chart, tables, text boxes and controls (only their on-screen part). (c) **Spark sound variations**: five kinds (crackle, snap, double, fizzle, zap), 10 files a session (every kind), never the same file twice in a row, each up to 30 % quieter at random; volume unchanged (0.05); preview `user_files/spark_preview.wav` (delete after listening). (d) **Fake Nakama friends for the screenshot**: `tools/dev/nakama_demo.py` writes `user_files/nakama_demo.json` (7 friends, numbers on a curve fitted to the owner's own), listed after real friends by `nakama.demo_members()`, never sent or synced; `--clear` (or deleting the file) removes them after the screenshot. NINJAL still down 2026-11-02 (503 maintenance), so the freq_extra rebuild waits.
- **Closed, don't propose again:** gamification ideas beyond the Progress Review; Susanoo/Tsukuyomi ranks; History chart marking-day step (stays); #12 BCCWJ + Jiten blend; a spoken-corpus toggle for the bars; a stricter step 2 (only the most common non-list words: owner kept "any of the top N"); fractional per-day numbers (weekly instead); word batches past #6,000; the NINJAL email; a Grok credit; ideas declined 2026-10-31: a debug-row guard, a fresh-profile run-through, re-recording the loops bigger, a rank-up fade into the video, an animated share card, a "what's new" note; a Duolingo-style weekly league board in Nakama (owner 2026-10-31: launch first).

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
2. **Word Grid** — JLPT words: known level by level (Mature → Young → New, ★ marked found last, most common first), then missing. Hover = meaning (Jitendex); click known → Browser, missing → copy; Shift+click → Jisho; middle-click found; Ctrl+middle suspend. **⧉ duplicates** (owner 2026-10-27, minimal): `analyse` → `results["duplicates"]` (`_duplicate_groups`: exact copies from `collect_words(duplicates=)`, leftover same-kanji second cards, one word listed at two levels with matching alternates; never sentence-card words, kana cards for kanji words, different kanji/readings); `WordCell` draws a faint ⧉ top-left (`DUP_MARK_ALPHA`) in every grid and opens all the notes; every `WordGridPanel` (Word Grid tab, JLPT and frequency pop-ups) and the Off-list tab show "⧉ Words with more than one card: N — see the list" (grids: beside the search box, out of the scroll fade) only when their tiles include some → `_show_duplicates` list (click = that word's notes, "Open all in browser"); test `tools/dev/maint/t_dups.py`.
3. **Missing** — Vocab / Kanji / Grammar switch; sortable, filterable, Copy all.
4. **Marked & Suspended** — found and suspended lists (each in its own card with its Reset button), loanword button, Show / Sort.
5. **Off-list** — deck cards on no list (still count for rank + frequency); tile grid | table splitter; the same "⧉ … see the list" line only when an off-list word has a duplicate.
6. **Kanji & Grammar** — compact bars; heatmap grids (strength = mean card score; red → cyan); grammar from the sentence parser or a grammar deck; "find it in your deck" search.
7. **Text Check** — paste text / open subtitles → coverage, verdict, unknown words (`text_check.py`).
8. **History** — chart of rank, JLPT, frequency over time (`history.py`, `history_view.py`); daily auto snapshot + "Take snapshot now".
9. **Nakama 仲間** — friends board (`nakama.py`, `nakama_view.py`; server `server/worker.js`, Cloudflare Worker + D1, not shipped).

**Grid pop-ups**: word / frequency / kanji / grammar grids, 900×890, glowing tile shape, neon flicker-on as rows come into view, search box with complementary-colour highlight.

**Progress Review** (`review.py`, `review_view.py`, owner 2026-10-27, mock-up A): today on the left (Words / Kanji / Grammar, each grammar point with its own sentence and the matched part underlined), the past 7 days on the right (totals, needed pace, a bar per day dimmed under the target, words by day, kanji, grammar). With a goal its items come first and the rest is one "+N outside your N2 goal" link (opens them all; no word list, owner 2026-10-27); without one, off-list words are the extra. Every heading opens everything under it in the Browser, every item just its card, a day line / bar that day's (no buttons, owner). Opened only by the goal card's "Today" (owner 2026-10-28: the "+N today / this week / this month" links open those cards in the Browser). Pops up by itself the first time the main window opens after the day's word target is reached (`REVIEW_POP_MS` after the intro; config `review_popped` = the day). Rebuilt on every open. Not on the mini widget (owner: the widget only opens the main window). No streaks (owner 2026-10-27: Review Heatmap already shows one; not even a weekly one).

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
| `README.md`, `docs/GUIDE.md` | README: public landing page (screenshots, install, privacy, credits; also the AnkiWeb text's source). GUIDE: every tab and click in detail. Keep both in sync with features. |

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
Kanji cards: display = an entry spelling and (if it has a reading) a matching reading. Kana cards: the entry spelled in that kana, else the most common kanji entry with that reading **only if that word is usually written in kana** (`freq_data.usually_kana` = `kana_ok.txt` + `kana_usual.txt`: もの → 物, きょう → 今日); otherwise nothing (と ↛ 都, ねこ ↛ 猫; owner 2026-10-27, same as the JLPT script rule). `word_rank` follows the same rule for kana JLPT words, and a kana side form only reaches a kana row starting with the same kana (なんか ↛ カボチャ; katakana variants are fine: リポート → レポート). `nid_rank` / `nid_rank_extra` sort Off-list views.
- **`word_rank`** (a JLPT word's frequency row: marks, hover ranks, the JLPT level on frequency tiles, Missing tab, goal pool, Text Check; not card counting) picks by tier, then commonest: the row spelled like the word → a row listing its spelling → the same for the list's alternate spellings → a kana word by its sound (the row's main reading) → a kana variant of a kana row. A kana word never takes a kanji row that only lists it as a side form (BCCWJ lists わた under 海, じゃ under 蛇). 2026-10-27.
- **Marks across lists** (`mark_ranks`, `card_state.found_key`): a JLPT mark reaches its frequency row through `word_rank`; a **katakana mark only reaches a katakana row** (BCCWJ lists ガン as a spelling of がん, タイ of 鯛). `tools/dev/maint/t_marks.py` checks both.

### 5c. Sentence parser and grammar
- **Config:** a mapping row with `sentence_field` but no `field` is a **sentence card**. `kanji_source.mode` vocab / sentence / fields; `grammar_source.mode` sentence / fields; hand marks always count. Parsed words get pseudo nids (`nid × 1000 + i`, `card_state.pseudo_nid` / `real_nid`).
- **Parser (`sentence_parser.py`):** dictionary = frequency list + JLPT lists (+ compounds); Yomitan-style deinflection typed by POS (`meanings.json`, `kinds_fix.txt`); lowest-cost whole-sentence split (`words_in`; kanji 1.0, kana 1.2, rare short kana costlier, function tokens); `kana_ok.txt` lets usually-kana words match in kana; katakana names are one unk token. Also feeds Text Check, so vocab accuracy matters.
- **Grammar (`grammar_data.py`):** regex detectors per distinctive written form (`_tail` conjugation, gap rules) + `_NOT_AFTER` / `_NOT_BEFORE` guards + `_CONTEXT` checks (id → fn(text, match)) + token rules from the parser's split (particles, endings path, passive, keigo). `EXTRA_FORMS` adds variants; `SENTENCE_SKIP` = hand-mark only. Every rule was checked against real sentences; rulings live in `tools/grammar_cases.json`.
- **Accuracy method:** fresh Tatoeba samples (`tools/accuracy/`, new seed each time), precision set A (as they occur) + B (50 per level), recall by annotating every point in 100 sentences; quote 95 % CIs. **Stop when fresh samples stop moving** (memory `stop-when-diminishing`); what's left needs meaning, which the add-on won't model.
- Owner decisions: no "label your sentences" review; grammar hand marking always on.

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
| Ranks 11–12 (Susanoo, Tsukuyomi) | Dropped (owner 2026-10-27): not part of Kotodama | — |
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
1. (closed 2026-10-27: rank/belt colour legibility was already done.)
2. (closed 2026-10-27: chart stays; duplicate finder built.)

## 11. Backlog and release plan
- Open backlog: none. #11 became the everyday speech percentage (CEJC, §0); #12 blend: closed 2026-10-27 (§0). Everything else in the original backlog is built.
- **Release:** release-ready first (parser vocab accuracy measured like grammar), then roadmap + licence audit (JMdict, Tatoeba, OpenJLPT, BCCWJ, AnkiWeb rules on donation links). Launch with only the Ko-fi one-time donation ("♥ Support", bottom-left, never a popup). "Supported Kotodama" line: built and deployed 2026-10-28 (see §0). Rank-up ribbons on the share image and supporter cosmetics: ideas, not part of the first release; earned things (rank, glow, belts) never change with money.
- **Positioning:** grammar coverage of your own sentences and any text is the strongest unique claim (measured precision/recall above).

## 12. Credits that must stay in README / list headers
- OpenJLPT (CC BY-SA 4.0); Jonathan Waller's JLPT lists (CC BY)
- JMdict, EDRDG (CC BY-SA 4.0); KANJIDIC2 via OpenJLPT kanji
- BCCWJ short- and long-unit frequency lists, NINJAL (CC BY-NC-ND 3.0; trimmed files are derivatives, accepted by the owner)
- CEJC short-unit vocabulary table ver202209, NINJAL (CC BY-NC-ND 3.0, same terms): the everyday speech percentage
- Jitendex, Stephen Kraus (CC BY-SA 4.0): hover meanings
- Tatoeba (CC BY 2.0 FR): evaluation only
- stephenmk/yomitan-jlpt-vocab, jamsinclair/open-anki-jlpt-decks, elzup/jlpt-word-list (community additions)
