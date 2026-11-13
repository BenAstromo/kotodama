# Kotodama 3.0.0: pre-launch review and implementation guide

Written 2026-11-12 by Claude Fable 5.2 for Claude Opus 5.5. Nothing in the add-on was changed. Each item is for the owner to approve first; do them one at a time.

**How to read an item.** *Confirmed* = shown by a script or traced end to end in the code. *Plausible* = follows from the code or from Qt / Anki behaviour, but not shown on this PC. Size: S = under an hour, M = a few hours, L = a day or more.

**Standing rules for every fix** (APP_VISION §8–9): Python 3.9 syntax (`parse39.py`, `compat39.py`); any new or changed English UI text needs its Japanese in `divine_text.py` and `tools/check_gold_text.py` must print OK (Settings and tooltips stay English); run `tools/grammar_eval.py` and `tools/vocab_eval.py` (0 differences) after any change, UI included; new Qt classes or `gui_hooks` names go into the tools' stub lists; no new settings unless the item says so.

---

## 1. Summary

- The add-on is in good shape for launch. All eight new-user scenario tests pass (fresh, empty deck, missing field, odd deck names, missing deck, corrupt files, non-ASCII paths, old config), as do the mark, duplicate, migration, offline-Nakama, gold-text and Python 3.9 checks. Both evals show 0 differences.
- No crash or data loss was found on the normal path. What's left is mostly **silent wrong numbers during setup**, which a new user reads as "it's broken".
- The three most important items: **1** (a mistyped field name gives a window of plausible but wrong numbers and no warning), **2** (Nakama's network calls sit in Anki's collection queue and can freeze reviewing for up to 12 seconds), **4** (on macOS the Settings and About menu items probably move out of the Kotodama menu).
- Not tested here and worth one real run each before the soft launch: macOS, Anki's light theme, and an Anki Qt5 build (the PyQt5 test venv is gone).

---

## 2. Must fix before launch

### 1. A wrong field name gives wrong numbers and no warning — Confirmed

**What a user sees.** They type `expression` instead of `Expression` in Settings (or pick the wrong field). The window opens normally and the bars show numbers, but those numbers are only the English loanwords marked by default. Nothing says their cards weren't read.

**Evidence.**
- `config_dialog.py:43-50`: the three field boxes are free-text `QLineEdit`s. Nothing checks the name against the note type.
- `__init__.py:299`: `if field_name and field_name in note` is an exact, case-sensitive match, so a wrong name is skipped silently.
- Shown with a script (8 studied notes, field typed as `expression`): words read from the deck **0**; bars N5 56/676, N4 37/632, N3 97/1676, N2 119/1780, N1 183/3081 (all loanword marks); rank count 8; warnings shown: none. With the right field, N5 is 63/676.
- The same happens with a deck that has no studied cards yet, and with a note type the mapping rows don't cover.

**Fix.**
1. `config_dialog.FieldMappingRow` and `SimpleFieldRow`: replace each field `QLineEdit` with an **editable `QComboBox`** listing the field names of the chosen note type (for "(all note types)": every field name in the collection, sorted, each once). Refill when the note-type combo changes; keep whatever is typed. Read with `currentText().strip()` so `get_mapping()` returns the same dict as now (the history signature in `history.signature` hashes `field_mappings`, so the stored shape must not change). First entry empty, so "no reading field" stays possible.
2. `ConfigDialog.accept` (override it): for each row, if a typed name isn't a field of that note type (or of any note type, for "(all note types)"), show one `showWarning` naming the row and the bad name and keep the dialog open. Compare exactly; if a name matches except for case, say so and offer the right spelling.
3. An honest empty state in the main window. In `OverviewTab._build` (`progress_dialog.py:7013`), after `real_total = count_deck_notes(...)`: if the analysis read no words from cards (no `known_words` entry with a real nid in any level and `results["unlisted"]["known_words"]` is empty), add one hint line at the top of the JLPT Vocabulary card:
   - `real_total > 0` (studied notes exist): "Kotodama read no words from your N studied notes. Check the field names in Kotodama → Settings."
   - `real_total == 0`: "No studied cards in this deck yet. Words count once you've studied their card."
   Style it like the existing notes (`HINT_CSS`, colour `#e0a050`). `real_total` includes hand marks, so use the note count from `card_state.deck_search` if you need the pure card number.
4. Rename the placeholder and column header "Kanji spelling field" to "Word field" (the README already says "the field with the Japanese word"). The hint above the rows explains kanji / kana.

**Must not change:** how `collect_words` matches; the config keys; a row with only a sentence field is still a sentence card.

**Tests.** `t_scenarios.py nofield` (extend it to assert the hint text is present), `t_scenarios.py empty`, `fresh`, `normal`; `check_gold_text.py` (the two hint lines are window text: add them to `divine_text.py`); both evals; a new small test that `get_config()` returns the same mapping dicts as before for an existing config.

**Size / risk.** M. Risk: the Settings layout (combo boxes are wider than line edits; keep the 2/2/2/2 stretch) and the history signature if the mapping dict changes shape.

**Owner decision needed?** Yes: OK to rename "Kanji spelling field" to "Word field"?

---

### 2. Nakama's network calls can freeze reviewing — Confirmed (the mechanism), Plausible (the freeze)

**What a user sees.** With Nakama joined and a slow or broken connection, answering a card right after a sync does nothing for up to 12 seconds.

**Evidence.**
- `nakama.py:399`: `tm.run_in_background(work, finished)`, with no `uses_collection` argument.
- Anki 26.9.4's `aqt/taskman` (the owner's install) says: "Tasks that access the collection are serialized. If you're doing things that don't require the collection (e.g. network requests), you can pass uses_collection=False". The default is True, so the request holds the single collection thread. The reviewer answers cards through that same queue (`answer_card` … `run_in_background` in `aqt/reviewer`).
- `nakama.py:51`: `TIMEOUT = 12`. `_on_sync_did_finish` (`nakama.py:573`) uploads after every sync, which is exactly when people start reviewing.

**Fix.** In `nakama._in_background`, replace the last line with:
```python
try:
    tm.run_in_background(work, finished, uses_collection=False)
except TypeError:            # older Anki: no such argument
    tm.run_in_background(work, finished)
```
`work` only calls `_request`, so it never touches the collection. Nothing else changes.

**Tests.** `t_nakama_offline.py refused` and `timeout` (the stub's `run_in_background` already takes `**k`); `t_scenarios.py normal`.

**Size / risk.** S. Very low risk.

**Owner decision needed?** No.

---

### 3. The background count can hold up the first answers of a review session — Plausible

**What a user sees.** They open Anki, go straight into a deck, and the first answer hangs for a few seconds (on a large deck's first count, much longer), sometimes with Anki's "Processing…" box.

**Evidence.**
- Every count runs as a `QueryOp` (`card_state.py:187`), which Anki puts on the same single collection thread as card answers (see item 2; `aqt/operations`: "Operations that access the collection are serialized").
- `mini_widget.py:1094-1117`: the main window's full count (`prepare_dialog`: words, kanji, grammar, history) starts on a timer 4 seconds after the deck list is drawn. `_prepare_now` doesn't check where the user is by then, so it can start while they're already reviewing.
- Measured times (APP_VISION §0, `card_state.py:165`): a Refresh is 2.9 s on the owner's deck; a 30k-note deck took about 35 s the first time.
- Not shown: this needs real Anki. **Check first**: in Anki, with the mini widget on, open a big deck within 4–5 seconds of the deck list appearing and answer at once.

**Fix (small, safe part).**
1. `mini_widget._prepare_now`: return unless `mw.state == "deckBrowser"`. The next deck-list draw re-arms the timer (`cached_results` → `_prepare_dialog`), so nothing is lost.
2. `__init__.prepare_dialog`: same guard at the top, for callers other than the timer.

Don't move the counts to `QueryOp.without_collection()` without the owner's say: they do read the collection, and running beside a sync or a profile switch could fail mid-count.

**Tests.** `t_scenarios.py normal` (the stub `mw.state` is "deckBrowser"); add a case with `mw.state = "review"` asserting `prepare_dialog` starts nothing; `t_perf_all.ps1` unchanged.

**Size / risk.** S. Risk: the window opens a little slower when clicked right after reviewing (it counts on the click instead, as it already does when the precount is stale).

**Owner decision needed?** Yes: run the check above and say whether the stall is real on your PC; if the widget's own recount also stalls answers, that's a separate, bigger decision.

---

### 4. macOS: "Settings…" and "About Kotodama…" probably leave the Kotodama menu — Plausible

**What a user sees.** On a Mac, the Kotodama menu shows only "Open Kotodama". Settings isn't where the README says it is; it may appear as, or replace, Anki's own Preferences / About entries in the application menu.

**Evidence.**
- `__init__.py:1068-1081`: plain `QAction("Settings…")` and `QAction("About Kotodama…")`. No `setMenuRole` anywhere in the add-on (grep: none).
- Qt's documented macOS behaviour (`QAction::menuRole`, default `TextHeuristicRole`): actions whose text starts with "about", "settings", "preferences", "options", "config" or "setup" are moved into the application menu. Not shown here (Windows PC).

**Fix.** After creating each of the three actions:
```python
for a in (_open_action, _settings_action, _about_action):
    a.setMenuRole(QAction.MenuRole.NoRole)
```
`QAction.MenuRole.NoRole` exists in PyQt5 5.15 and PyQt6.

**Tests.** Both evals and `t_scenarios.py fresh` (they import `__init__`; the stubs fake `QAction`, so check `setMenuRole` exists on the fake or add it to the stub lists in APP_VISION §9). Then one look on a real Mac.

**Size / risk.** S. No risk on Windows / Linux.

**Owner decision needed?** No. Do find one Mac user to confirm before the Reddit posts.

---

### 5. Tools → Add-ons → Config opens raw JSON — Confirmed

**What a user sees.** Many users open an add-on's settings from Anki's Add-ons window. For Kotodama that shows a JSON text editor with `"field_mappings": []` and no explanation.

**Evidence.** No `setConfigAction` call in the add-on (grep: none); no `config.md`. Anki's `AddonManager.setConfigAction` exists in 2.1.50 and 26.9.4.

**Fix.** In `__init__.py`, after `run_jlpt_check` is defined: `mw.addonManager.setConfigAction(__name__, run_jlpt_check)`. The Config button then opens Kotodama's own Settings.

**Tests.** `t_scenarios.py fresh` (add `setConfigAction=lambda *a: None` to the stub `addonManager` in `stubenv.py` and the other stub lists); both evals.

**Size / risk.** S. None.

**Owner decision needed?** No.

---

### 6. A new install shows nothing until the user finds the menu — Confirmed

**What a user sees.** After installing and restarting, Anki looks exactly as before. The only sign of Kotodama is a new word in the menu bar.

**Evidence.** `mini_widget.py:1002-1003`: not configured → `_compute_results` returns None; `mini_widget.py:1144-1146`: with no results and nothing shown before, the hook returns without adding anything to the deck list.

**Fix.** In `_on_deck_browser_will_render_content`, when `mini_widget_enabled` is on and the config has no `deck_name` or no `field_mappings`: add a small card in the same corner and style as the widget (reuse `#jlpt-mini-widget`'s CSS and the `pycmd('jlpt_open_progress')` click, which already opens Settings when unconfigured, `__init__.py:1058`). Text: "Kotodama 言霊" and under it "Click to set up". No bars, no neon, no sound. It disappears by itself once a deck and a field are saved (the normal widget takes over).

**Must not change:** nothing shows when the user has turned the widget off; no popup at start-up.

**Tests.** `t_scenarios.py fresh` (assert the card's HTML is returned and holds the click message), `normal`; `mini_neon*.py` in tools/dev if the CSS is touched.

**Size / risk.** S. Risk: none for configured users (the branch is only reached when unconfigured).

**Owner decision needed?** Yes: is a "Click to set up" card on the deck list OK, and is that the wording? (The widget is never gold before setup, so no Japanese is needed, but add the text to `divine_text.py`'s skip list if `check_gold_text.py` scans `mini_widget.py`.)

---

### 7. The chosen deck was renamed, deleted, or belongs to another Anki profile: everything shows zero — Confirmed

**What a user sees.** After renaming their deck in Anki (or opening a second Anki profile), the widget and window show loanwords only, with no hint why. For that day the History chart gets a zero point, and a joined Nakama card can upload zeros.

**Evidence.**
- Settings are per add-on, not per profile, and store the deck by name (`config_dialog.py:547`).
- `__init__.py:845-855` and `mini_widget.py:1002`: only "is a name set" is checked, never "does the deck exist".
- Shown with a script (config deck "Japanese", collection without it): `history.json` got a snapshot for "Japanese" with `rank 0, jlpt 492, N5 56, mature 0`. `nakama.store_partial` runs on the same path (`mini_widget.py:1038`).

**Fix.**
1. Add `card_state.deck_exists(deck_name) -> bool`: `mw.col.decks.id_for_name(deck_name) is not None`, wrapped in try (True on any error, so a failure never hides the widget).
2. `mini_widget._compute_results`: after the "not configured" check, `if not card_state.deck_exists(deck_name): return None` (before `history.record_auto` and `nakama.store_partial`, so nothing is recorded or stored).
3. `history._on_deck_browser_will_render_content` and `__init__.prepare_dialog`: same guard.
4. `__init__._open_progress_dialog`: if the deck doesn't exist, `showWarning("Kotodama can't find the deck “X”. It may have been renamed or deleted. Choose your deck again in Kotodama → Settings.")`, return False, and make `open_progress_dialog_direct` fall through to `run_jlpt_check()` in that case, as it does when unconfigured.
5. `rank_toast._set_baseline` / `_on_did_answer`: no change needed (a missing deck counts 0 and never toasts).

**Must not change:** sub-deck handling; the stored config key.

**Tests.** `t_scenarios.py nodeck` (extend: no snapshot written to `history.json`, the warning is logged in `E.LOG["warnings"]`); add `id_for_name` to `mkcol.py`'s `_Decks` and to the other tools' fake collections (`tools/harness.py`, `grammar_review.py`, `speed_test.py`), or every eval crashes; both evals.

**Size / risk.** S–M. Risk: the stub lists (above). A deck name that differs only by case or Unicode form from Anki's would be "missing": use Anki's own lookup, not a string compare.

**Owner decision needed?** No. (Following a rename automatically by deck id is in "Ideas for later".)

---

### 8. Two "(all note types)" rows: the second row's sentences are never read — Confirmed

**What a user sees.** A user with two note types leaves both rows on "(all note types)" (the default for a new row) and fills in different field names. Vocabulary counts for both note types, but grammar and sentence kanji come only from the first row's sentence field.

**Evidence.**
- `sentence_parser.py:66-74`: the loop `break`s after the first row whose note type fits, even when that row's sentence field isn't in the note. `grammar_data.py:3256-3267` (`word_card_ids`) and `review.py:69-79` do the same.
- `__init__.py:284-308` (`collect_words`) tries every fitting row, so words are found.
- Shown with a script (rows: `Word`/`Sentence` and `Expression`/`SentenceJP`, both all note types): words read 学校, 水; sentences read only 水を飲みたいです。 With the note types chosen per row, both sentences are read.

**Fix.** In all three loops, only stop at a row that actually applied:
- `sentence_texts`: move the `break` inside `if sf and sf in note and not (...)`. A row that names a specific note type still ends the search for that note (`if m.get("note_type"): break` after the `if`), so a deliberate "this note type has no sentence field" row keeps working.
- `word_card_ids`: `break` only when `f and f in note`, or the row names the note type.
- `review.py`: the same as `sentence_texts`.

**Must not change:** results for configs where every row names its note type (the owner's): the evals and the owner's counts must be identical.

**Tests.** Both evals (0 differences); a new case in `t_scenarios.py` built like the script above, asserting two sentences; `t_scenarios.py normal`.

**Size / risk.** S. Risk: a user whose first all-types row deliberately has no sentence field and whose second has one would start getting sentences read (that is the intended reading of their settings).

**Owner decision needed?** No.

---

### 9. One odd friend card breaks the whole Nakama tab — Confirmed

**What a user sees.** After adding a friend code whose card holds something unexpected (made by hand against the public server, or by a future version), an add-on error appears every time the Nakama tab opens, and the friend can't be removed because the list is never drawn.

**Evidence.**
- `nakama_view.py:59` `int(data.get("rank") or 0)`, `:35`, `:88`: no guard. Script: `{"rank": "lots"}` → ValueError; `{"week": "x"}` → ValueError.
- `share_card.py:567-574`: `{"jlpt": "x"}` → AttributeError; `:606` `{"week": "x"}` → ValueError.
- `server/worker.js:86-90` (`cleanData`) accepts any JSON object up to 6,000 characters, so the server won't stop it.

**Fix.** Clean every profile once, where it arrives: add `nakama.clean_profile(p) -> dict` and apply it in `fetch_friends` before caching (`nakama.py:480-485`), in `demo_members`, and when reading the cache in `nakama_view._members`.
- `name`: `str`, at most 32 characters.
- `data`: a dict, else `{}`. Inside it: `rank`, `found`, `found_loan`, `loan_marked`, `jlpt_loans`, `loyal` → non-negative ints (else 0), `rank` capped at 20,000; `week`, `month` → ints or None; `jlpt` → dict of level → `[int, int]` pairs, others dropped; `freq` → a pair or None; `kanji`, `grammar` → dicts of pairs; `goal` → str or None; `sun` → bool. Unknown keys are kept as they are (a newer version's fields), so nothing is lost when re-saved.
- Also wrap the body of the per-member loop in `nakama_view._fill_list` so one bad row is shown as "Can't show this card" instead of stopping the list.

**Must not change:** `_signature(own.get("name"), own.get("data"))` in `fetch_friends` must be computed on the raw server data, before cleaning, or the "resend once a day" check misfires.

**Tests.** `t_nakama_offline.py`; a new test feeding the bad profiles above through `clean_profile`, `_Row` and `render_profile`; `tools/dev/nakama_demo.py` still shows its friends; `check_gold_text.py` if the fallback text is new.

**Size / risk.** S. Low.

**Owner decision needed?** No.

---

### 10. The debug row still ships — Confirmed

**What a user sees.** One click on an invisible 28 × 22 px spot under the rank title (and the same spot on the Nakama tab) shows a row of debug buttons: "☀ Force Amaterasu" (names and shows the secret top rank), "★ Mark All JLPT Found" (writes about 10,000 marks into the user's files), "Count all notes", test toasts.

**Evidence.** `progress_dialog.py:7201-7290`, `nakama_view.py:275-313`. APP_VISION §7 says "Debug buttons: visible; the owner removes them before release", and `tools/build_package.py --list` still prints "decide on the debug row" as open. It isn't on the §0 launch list, so it could be forgotten. (A guard for it is on the closed list; this item is only the removal the decision log already promises.)

**Fix, if the owner says remove.** Delete the secret button and the debug box in both places, and the handlers nothing else uses: `_nudge_rank`, `_cycle_loyalty`, `_mark_all_jlpt_found`, `_set_count_all`, `_set_force_amaterasu`, `_test_rank_toast` in `OverviewTab`; `_debug_row`, `_debug_step`, `_debug_set`, `_belt_starts`, `_shown_count` and `_preview` in `NakamaTab`. Keep `_DEBUG_FULL`, `_DEBUG_ROW`, `debug_count_all` and `_rank_debug_offset` as constants that stay off (many places read them; `tools/dev` scripts and `t_sun_debug.py` set them directly), and keep the "DEBUG: the rank is counting every note" warning label. Check `git grep -n "_DEBUG_ROW\|_rank_debug_offset\|_preview"` afterwards.

**Tests.** `t_scenarios.py normal`, `t_sun_debug.py`, `t_tiles_look.py` / `t_buttons_look.py` compare (ALL SAME), `check_gold_text.py`, both evals.

**Size / risk.** S–M. Risk: the dev tools that click these buttons (`tools/dev/qt_*.py`); update them to set the flags directly.

**Owner decision needed?** Yes: remove the debug row now, or ship it hidden as it is?

---

### 11. Anki Qt5 builds: clicking in the Progress Review raises an error — Confirmed (by reading)

**What a user sees.** On Anki 2.1.50–2.1.66 Qt5 builds, every click on a word, heading or day in the Progress Review shows an add-on error.

**Evidence.** `review_view.py:77`: `ev.position().toPoint()`. Qt5's `QMouseEvent` has no `position()`. Every other mouse handler has a fallback (`progress_dialog.py:4234` `_mouse_pos`, `history_view.py:432`). The Qt5 test pass was on 2026-10-26; the Progress Review (10-27), the widget's corner drag (11-07) and the painted grid canvas (11-10) came later, and the PyQt5 venv (`%TEMP%\qt5v`) no longer exists, so none of them has run on Qt5. The README promises Qt5 builds work.

**Fix.** In `review_view._Hover.eventFilter`, use `(ev.position().toPoint() if hasattr(ev, "position") else ev.pos())`, or import `_mouse_pos` from `progress_dialog`. Then rebuild the PyQt5 venv (`python -m venv %TEMP%\qt5v`, `pip install PyQt5`) and run `t_scenarios.py normal`, `t_tiles_use.py` and `tools/dev/qt_neon.py` with `KT_QT=5`; fix whatever else they show.

**Tests.** As above, plus the usual PyQt6 runs.

**Size / risk.** S for the line; unknown for what the Qt5 run turns up.

**Owner decision needed?** Yes: installing PyQt5 downloads a package; OK to do that? If Qt5 isn't worth it, change the README line to "Anki 2.1.50+ (Qt6 builds)" instead.

---

### 12. The public guide describes Settings that no longer exist, and prints accuracy numbers — Confirmed

**What a user sees.** `docs/GUIDE.md` (linked from the README as "the full guide") sends them to tabs and a file format that were removed, and contradicts the window on loanwords.

**Evidence.**
- `GUIDE.md:7`, `:17-21`, `:31`, `:42`: "Deck & Fields tab", "Vocabulary Lists tab", "Kanji & Grammar tab", "(same tab)". Settings has been one scrolling page since 2026-10-26 (`config_dialog.py:1-7`).
- `GUIDE.md:34-40`: a "File format" for uploading word lists. Custom lists were removed on 2026-10-26.
- `GUIDE.md:64`: marked loanwords join "everywhere: the rank, the JLPT and frequency bars". Since 2026-11-09 the JLPT bars count them at once (`card_state.py:389-398`).
- `GUIDE.md:124`: "finds about 9 in 10 points, and about 99% of what it finds is right". The owner's decision (release_drafts.md, 2026-10-20; advertising plan) is no accuracy numbers on public pages.
- `GUIDE.md:57`, `:27`: "Overview tab". The tab is called "Vocabulary" (`progress_dialog.py:8102`).
- `README.md:111` and the Join text (`nakama_view.py:142-145`) say only "your name and the numbers on your bars" are sent. Also sent: months with Kotodama, how many words are marked found, and, unless unticked, the JLPT goal's level and test date (`nakama.py:287-293`; `share_show_goal` defaults to on, `goal.py:654`). And "everything else stays on your computer" skips that the friend code, key, name and friends list are kept in the Anki collection and sync through AnkiWeb (`nakama.py:160-170`).

**Fix.** Text only.
- GUIDE: rewrite "Setup" as one Settings page in its real order (deck, field rows, kanji source, grammar source, suspended cards, main screen widget, sound, animations, Night look); delete the "File format" block; correct the loanword sentence (JLPT bars at once; rank and frequency bars gradually); rename "Overview" to "Vocabulary"; replace the accuracy sentence with a plain one ("It finds most points; the ones it misses are those only the meaning of the sentence can tell apart …").
- README privacy paragraph and the Join text: "your name and the numbers on your card (rank, bars, words marked found, time with Kotodama and, if you choose, your JLPT goal)". Add one sentence: "Your friend code and friends list are also saved in your Anki collection, so they follow your AnkiWeb sync." Mirror the README change into `release_drafts.md` §6.

**Tests.** `check_gold_text.py` (the Join text is window text: update its Japanese in `divine_text.py`).

**Size / risk.** S. None.

**Owner decision needed?** Yes: confirm the accuracy sentence should go from the guide (it's your earlier decision; the guide predates it).

---

## 3. Fix in 3.0.x (first weeks after launch)

### 13. `&nbsp;` or `&amp;` in a word field stops the word from matching — Confirmed
**What a user sees.** A card whose word field has a stray non-breaking space (Anki's editor adds them) is listed under Off-list as `猫&nbsp;` and its JLPT word shows as missing.
**Evidence.** `__init__.py:94-99` (`_extract_words`) strips tags but not entities. Script: `"猫&nbsp;"` → `['猫&nbsp;']`, `"R&amp;D"` → `['R&amp;D']`. Sentence fields are fine (`kanji_data.py:83`).
**Fix.** In `_extract_words`, after the tag strip: `s = html.unescape(s)` (import `html`); the existing split on `\s` and `_norm`'s NFKC then drop the space. Do the same at the top of `_extract_reading` after its tag strip.
**Tests.** `vocab_eval.py`, `grammar_eval.py`, `tools/anomaly_scan.py` on the harness copy, `t_dups.py`, `t_marks.py`. Expect the owner's baseline numbers to stay the same or rise by a handful; look at any that change.
**Size / risk.** S. Low: a word field that really contains `&lt;` text is unheard of.
**Owner decision needed?** No.

### 14. Light theme: parts of the deck-list widget and Settings are hard to read — Confirmed (by calculation), not seen
**What a user sees.** In Anki's light theme the widget is a grey box: the "Today: 9 / 14 words" line and, with the rank picture off, the rank line and count are pale grey on mid grey.
**Evidence.** `mini_widget.py:370`: `background: rgba(20,20,20,0.55)`, which over a white page is about `#7e7e7e`. On that, `#cfcfcf` (goal text, `:138`) is about 2.5:1, `#ddd` (`:581`) about 3:1, `#999` (`:589`) about 1.4:1. `config_dialog.py:184`: column headers `#aaa` on a light dialog, about 2.3:1.
**Fix.** In `_widget_html`, pick the box background by theme: `from aqt.theme import theme_manager`; dark → as now; light → `rgba(20,20,20,0.88)` (hover `rgba(35,35,35,0.94)`), inside try/except with today's value as the fallback. In `config_dialog.py:184` use `color: gray`, like the hints.
**Tests.** `tools/dev/mini_neon*.py` renders; a look in real Anki in both themes.
**Size / risk.** S. It's a visual change: per the owner's rule, show the light-theme before/after first.
**Owner decision needed?** Yes: approve the look from a screenshot.

### 15. A non-ASCII character in the add-on's path breaks the tab arrows' style rule — Confirmed
**What a user sees.** With a Windows user name like `José` or `ゆき`, the tab bar's scroll arrows fall back to Qt's grey ones (only visible when the tabs don't fit), and Qt logs "Could not parse stylesheet".
**Evidence.** `theme.py:309`: `image: url({img})`, unquoted. Script (PyQt6, offscreen): a path with `ü環境` → "Could not parse stylesheet of object QDialog", and every rule after the bad one is dropped; with `url("…")` it parses. The arrow rules are last in the sheet, so only they are lost. Spaces alone are fine.
**Fix.** `image: url("{img}")`.
**Tests.** `t_scenarios.py unicode` (add a Qt message handler that fails on "Could not parse stylesheet"); `t_tiles_look.py` compare.
**Size / risk.** S. None.
**Owner decision needed?** No.

### 16. When a count fails, the user gets a bare error and nothing to report — Plausible
**What a user sees.** If an unusual note makes the count fail, a small box shows only the error's text (for example "list index out of range") and the window never opens.
**Evidence.** `__init__.py:888-899`: `work_or_reset` re-raises into `QueryOp` with no `.failure()` handler, so Anki's default shows `str(exception)` only. Same for the window's Refresh (`progress_dialog.py:8353-8373`). No such failure was found; this is for the ones nobody has seen yet.
**Fix.** Give `card_state.run_in_background` a default `failure` for the non-quiet case: `showWarning` with "Kotodama couldn't count your deck. Please report this at github.com/BenAstromo/kotodama/issues with the text below." plus the traceback (`traceback.format_exception`), which Anki's warning box lets the user copy. Keep the quiet path as it is.
**Tests.** A scenario that makes `collect_words` raise and asserts the warning text holds "Traceback"; `t_scenarios.py normal`.
**Size / risk.** S. None.
**Owner decision needed?** No.

### 17. The Nakama server has no limit on reads and updates per address — Plausible
**What a user sees.** If someone hammers the public address, the free plan's daily allowance (100,000 requests) runs out and Nakama shows "Couldn't reach the Nakama server" for everyone until the next day. Nothing is billed and nothing leaks.
**Evidence.** `server/worker.js:113-118`: only `create` uses the rate-limit binding. `list`, `update`, `leave`, `remove` have none. Normal use is far below the allowance (a handful of requests per member per day).
**Fix.** Add a second binding in `wrangler.toml` (for example `READ_LIMIT`, 60 per minute) and call it at the top of `list`; reuse it or a third for `update` / `leave` / `remove`, keyed by `cf-connecting-ip`. Reply 429 "Too many requests. Try again in a minute." The add-on already shows server messages (`nakama.py:369-374`). Redeploy per HISTORY's notes (`npx wrangler@4 deploy` in `server/`, by the owner).
**Tests.** `t_kofi.mjs`; a local `wrangler dev` run on a port other than 8765.
**Size / risk.** S. Risk: a limit set too low blocks a school or shared network; 60 a minute per address is generous.
**Owner decision needed?** Yes: it needs a redeploy from your account.

### 18. Two Anki profiles created on the same day can share one Nakama membership — Plausible
**What a user sees.** Rare: a second profile (or a friend given a copy of the folder) whose collection was created on the same day uploads over the first one's card.
**Evidence.** `nakama.py:96-101` identifies the collection by `col.crt`. Anki sets `crt` to the start of the day the collection was created (4 a.m. local), not the exact second, so it isn't unique. Not verified against the owner's collection.
**Fix.** Make the stamp more specific without breaking existing ones: keep accepting a stored `col` equal to `str(col.crt)`, and for new stamps use `f"{col.crt}:{mw.pm.name}"`… only if the owner wants it: a profile name isn't synced, so a second computer with a different profile name would stop adopting the membership. Simpler and safe: leave it, and document the limit in the handbook.
**Size / risk.** S, but the "fix" can do more harm than the bug. **Recommendation: leave as is.**
**Owner decision needed?** No, unless a real case turns up.

---

## 4. Ideas for later (optional)

1. **Follow a renamed deck by itself.** Save the deck's id beside its name in Settings; when the name is gone but the id exists, switch to the new name and move the History entries (`history.json` is keyed by deck name). Builds on item 7.
2. **Pre-fill the field rows.** When a deck is chosen in a fresh Settings, add one row per note type found in that deck, with the note type's first field as the word field and any field named like "Sentence" as the sentence field. The user only confirms. Builds on item 1; no new setting.
3. **A footer on the share image that people can act on.** It now says "Kotodama 言霊 · JLPT progress for Anki" in 10 pt dark grey (`share_card.py:482-486`). Since shared images are the planned word of mouth, a slightly larger line with "free Anki add-on" would let a viewer find it. A visual change: mock-ups first.

---

## 5. Checked and fine

Nobody needs to re-check these unless the code around them changes.

**Ran and passed (2026-11-12, PyQt6 offscreen):**
- `t_scenarios.py` fresh, empty, nofield, baddeck, nodeck, corrupt, unicode, oldcfg: ALL PASS (no tracebacks; the widget, window, every tab, grids, Refresh, close).
- `t_marks.py`, `t_dups.py`, `t_nakama_offline.py` (refused, timeout), `t_userfile_safety.py`, `t_override_race.py`, `t_deck_query.py`, `t_decode.py`, `t_rank_math.py`, `t_migrate.py`: all pass.
- `parse39.py`, `compat39.py`: OK. `data_check.py`: no duplicate or malformed rows. `check_gold_text.py`: OK. `vocab_eval.py` and `grammar_eval.py`: 0 differences.
- `build_package.py --list`: `user_files/`, `meta.json`, `server/`, `tools/`, `docs/` are left out; about 19 MB before zipping.

**Read and found sound:**
- **Hooks while reviewing** (`rank_toast.py`, `seal.py`, `mini_widget.py`, `history.py`, `nakama.py`): every one is wrapped (`card_state.hook_guard` or try/except) and filter hooks return Anki's value on error. New-card answers cost one deck search; other answers cost nothing.
- **User files**: every save writes a temp file and swaps it in; an unreadable file is copied aside before being replaced (`overrides.py`, `history.py`, `goal.py`, `nakama.py`). Marks are copy-on-write, so a background count never sees a half-changed set.
- **Deck names** with `_ * \ "` and `::` (`card_state.deck_query`).
- **Migration** from the shared `jlpt_progress` folder to an AnkiWeb folder (`migrate.py`): never overwrites, runs once, failures are swallowed.
- **Nakama privacy**: nothing is sent before Join; the snapshot holds numbers, a name and (optionally) the goal, never cards, words or deck names; Leave blanks the name and data on the server; the key is stored hashed (SHA-256) server-side; bodies are capped at 8 KB; names are stripped of control characters; friend names are HTML-escaped in the list (`nakama_view.py:71`); codes are 8 characters from 31, too many to guess.
- **Nakama offline**: a refused or timed-out server shows one line in the tab and nothing else breaks.
- **Free-plan limits under normal use**: a few requests per member per day against 100,000; one small row per member.
- **Platform code**: `winsound` and the Windows title-bar colour are behind `sys.platform` checks; sounds and videos fall back silently when Qt Multimedia is missing; fonts fall back through Windows, macOS and Linux families.
- **Paths with spaces** (macOS's "Application Support", Windows names like "John Smith") parse fine in the style sheet; only non-ASCII is affected (item 15).
- **Old Anki API use**: `QueryOp`, `taskman`, `gui_hooks` names, `Browser.search_for`, `col.get_config` all exist in 2.1.50; newer-only calls are behind try/except or `getattr`.
- **Goal near the test date**: a goal set inside the last 14 days shows the "review" phase rather than a wrong per-day number (`goal.py:569-576`).
- **Memory**: not re-measured (the short `t_leaks.py 3` run I tried is too few rounds for its own maths and stops with an error in the test, not the add-on); APP_VISION §0's 2026-11-10 result stands.

**Not checked, and why:**
- Real Anki, macOS, Linux, Anki's light theme on screen, and Qt5: this review only read code and ran the offline tests.
- Parser and grammar accuracy: tuning is finished by the owner's decision; only crashes were looked for, and none was found.
- `progress_dialog.py` was read in its risky parts (window lifecycle, Overview, Refresh, grid windows, Browser calls, share), not line by line; its painting and neon code is covered by `t_scenarios`, `t_tiles_*` and `t_buttons_look`.
