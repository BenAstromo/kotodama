# Kotodama 言霊 — JLPT Progress & Rank Tracker (Anki add-on) v3.0.0

Visualize how much of each JLPT level (N5 → N1) your Anki deck covers.

## Installation

1. Locate your Anki add-ons folder:
   - **Windows**: `%APPDATA%\Anki2\addons21\`
   - **macOS**: `~/Library/Application Support/Anki2/addons21/`
   - **Linux**: `~/.local/share/Anki2/addons21/`
2. Copy the entire `jlpt_progress` folder into `addons21/`
3. Restart Anki
4. Open via the **Kotodama** menu on Anki's menu bar (**Open Kotodama**, or **Settings…** to change the deck and fields first), or click the widget on the main screen

---

## Setup

### 1. Deck & Fields tab
Select the deck you want to analyse (sub-decks are included) and map your note types to the field that contains the Japanese target word (e.g. `Expression`, `Word`). Optionally add a **reading field** (e.g. `Reading`) — it helps match kana-only cards and tells homophones apart. Add one row per note type.

**Sentence field** (optional, e.g. `Sentence`): the card's example sentence. The **auto parser** reads it to find kanji and grammar (see the Kanji & Grammar tab). A row with a sentence field but **no word field** is a sentence card: every dictionary word in its sentence counts as its vocab, so people who mine plain sentence cards get JLPT, frequency, kanji and grammar progress too.

How the auto parser reads a sentence (pure Python, nothing to install):
- **Words**: the sentence is split into the words of our JLPT and frequency lists, undoing conjugations (食べなかった → 食べる, 使えます → 使う), with the split that explains the most text winning. Particles and endings (です, だった, んだ) are skipped. Kana only matches words written in kana (はし is never 橋); a conjugated form only matches a word of the right kind (食べた needs an Ichidan verb); a single kanji stuck to other kanji (家 in 建築家) isn't counted; when one spelling is several words, the lowest JLPT level wins (時 → とき). Common compounds on the frequency list are read whole (可能性, 日本語, 考え方, お客様, 私たち), except kana-only ones like なので and ですが, which would hide the grammar inside them. The same word in many sentences counts once.
- **Kanji**: every kanji in the sentence.
- **Grammar**: OpenJLPT's patterns, letting their endings conjugate (ことにする finds ことにした); when one pattern sits inside a longer one (〜ことに in 〜ことになる), only the longer one counts. Short particles and endings (は, を, です, ます, た, たい …) are found from the parser's split of the sentence, so は inside はし or こんにちは doesn't count. Forms with several meanings (に: time / destination / place / target / frequency; で; が; か; と; から …) only count where the sentence makes the meaning clear (3時に → time, 学校に行く → destination, 電話で → means, 硬いですが、 → but); the rest can be marked found by hand.

This tab also has the **Main screen widget** toggle (on by default) with an **Include rank** option (on by default) and a **Rank picture** option (on by default: a mini version of your rank's picture on its badge background, as on the Overview tab), which shows a small set of N5–N1 bars, your rank and belt, and two thin bars (overall rank progress and current-belt progress) next to your deck list. Clicking it opens the main window.

**Sound effects** (same tab): one **Volume** slider for every sound the add-on makes — the quiet neon buzz as the bars flicker on (the main screen widget's is quieter still) and the rest. Moving it plays a sample; it starts at 50%, and 0% turns them all off. Untick **Mini widget sounds** to keep the main screen widget silent while the Kotodama window keeps its sounds.

**Animations** (same tab): **Neon flicker** — the bars and grids flicker on when you first see them (off: lit at once); **Rain** — drops on the window's glass that catch the neon light, with the odd spark. Both on by default. **Night look** (same tab): each of the window's night effects on its own switch — light spill, stars and moon, bokeh, vignette, condensation, puddle reflection; all on by default, none in Amaterasu mode.

**Neon street look:** the bars, grids and the N5–N1 signs flicker on like neon signs as they come into view, and you see them through a rainy window: drops on the glass catch the colour of the nearest lit tube, now and then a drop runs down, a spark comes off a bar, or one tube stutters with a very quiet buzz. It only runs while the window is in front (it stops in the background and when minimised).

**Top rank extras:** a soft sound when you reach the top rank, which stays as a quiet ambience while the window is open (deliberately soft), and a seal on the review screen, which you can switch on in Settings once you've reached it (off by default).

**Share image…** (Overview, next to the rank's "?"): makes a picture of your progress to save as PNG or copy — your name, your rank picture, rank and belt, one bar per JLPT level combining vocab, kanji and grammar, and the 20,000-word frequency bar.

**Ignore cards suspended in Anki**: when ticked, notes whose cards are all suspended in Anki don't count toward the JLPT bars, the Frequency Check or the rank.

### 2. Vocabulary Lists tab
The **Kotodama JLPT lists** cover every level (OpenJLPT plus a few hundred additions, 8,070 words total). They follow Jonathan Waller's community JLPT lists — the basis of every JLPT list since official lists stopped in 2010 — with modern spellings (ありがとう rather than 有難う) and alternate spellings kept for matching. Everyone uses the same Kotodama JLPT lists, so your bars, History and Nakama numbers compare fairly. To check your coverage of some other list (a textbook's, say), paste it into **Text Check**.

**File format** (may be mixed within one file):
- One word per line: `食べる`
- Word + reading (TSV): `食べる\tたべる`
- Word + reading (CSV): `食べる,たべる`
- Optional extra TSV columns: alternate spellings (`|`-separated) and flags, e.g. `いちばん	いちばん	一番`

Lines starting with `#` are treated as comments. The JLPT does not publish an official vocabulary list, so no list is authoritative.

### 3. Kanji & Grammar tab
Where your kanji come from:
- **From my vocab words** (default): every kanji in the words found through the Deck & Fields tab. Sentence cards (no word field) give the kanji of their whole sentence.
- **From my sentence fields**: every kanji in the sentence fields set on the Deck & Fields tab.
- **From a field in another deck**: e.g. a kanji deck's `kanji` field (choose the deck, then one row per note type + field). Every kanji in that field counts.

Where your grammar comes from:
- **Parse my sentence fields** (default): the auto parser finds grammar in the sentence fields set on the Deck & Fields tab.
- **From a grammar deck's field**: the field holds the pattern, e.g. `〜がてら`, `がてら` or `〜がてら (while)`; ～, spaces and romaji don't matter. A few points share a form (で: place of action / means): add the English meaning (`で (means)`) to tell them apart, or the card won't count. Cards that don't match are listed under the grammar grid.


---

## Features

### Overview tab
- Progress bar for **each JLPT level** showing known / total words, plus an **All N Levels Combined** bar
- Click any bar → opens that level's word grid in a separate window
- **⟳ Refresh** re-scans the deck and re-applies your found/suspended overrides
- **JLPT Goal** — pick the level you're taking and the test date (the next ones are listed: the first Sunday of July and December, or any other date), and the card under the bars works out how many **words, kanji and grammar points to learn per day**. The test covers every level up to yours (N3 = N5 + N4 + N3). The finish line is **14 days before the test**, leaving the last two weeks for review and practice tests. It's worked out fresh every day: fall behind and the number goes up, get ahead and it goes down; there are no streaks and nothing is lost for a missed day. Words, kanji and grammar marked found count as known and lower what's left at once (marked English loanwords as they join), but never count as "today's" study.
  - **Which words count:** for N5–N3, the JLPT word lists (the JLPT bars). For **N2 and N1**, the goal is the modern vocabulary size (about 6,000 / 13,800 words) in **two steps**: first every word on the JLPT lists up to that level (the words most likely on the test), then the rest from the most common words of written Japanese that aren't on the lists. The JLPT hasn't published word lists since 2010, and the old lists ours build on stop well short of N2 and N1; written Japanese also matters more there. Kanji and grammar always use the JLPT lists.
  - Also shown: **"Today: 9 / 14 words"** on the main-screen widget, an **On track** line on the History chart (running on to the test day), and optionally **"Aiming for JLPT N3 · December 2026"** on the share image and your Nakama card (a checkbox in the share window, next to "Show time with Kotodama")
- **Kotodama 言霊 Japanese Rank** — counts every note in the selected deck with a **card you've studied** (learning, young or mature) (JLPT-listed or not, any note type) toward a 20,000-note "native-like fluency" target, plus every word you've **marked as found** (words you know without a card; counted once even if they're on both the JLPT and frequency lists). **English loanwords marked found join gradually**, as your vocabulary reaches them: a loanword at frequency rank 8,000 counts once your rank reaches 8,000. This holds everywhere: the rank, the JLPT and frequency bars, your goal, the History tab and your Nakama card. So marking them doesn't jump you past the early ranks, and with all of them marked you still reach 20,000 at the same point. The share image and Nakama card say how many are counted; a marked loanword that doesn't count yet shows a faint ★ in the grids. New cards count once you study them; relearning cards still count. Marks made in the grids reach the rank after a Refresh.
  - While reviewing, a small **rank-up message** appears at the bottom-left of Anki's window when a newly studied card moves you to a new belt or rank. It's repeated as a banner at the top of the main-screen widget when you go back to the deck list, in case you missed it; the banner stays until you click its ✕, open the add-on, or start reviewing again.
  - 10 main ranks (Gaijin → Amaterasu) × 8 karate-style belts (White → Black). A higher main rank always outranks every belt of a lower rank.
  - Belt sizes grow by about 5% per belt: the first belt takes 21 notes, later belts several hundred.
  - Amaterasu's Black Belt is split into 10 degrees; Tenth-Degree is reached at exactly 20,000 notes, which turns every bar gold and shows a reward message.
  - Two bars: overall 0–20,000 progress (coloured by rank) and current-belt progress (coloured by belt). Hover for notes remaining. The **?** button explains the system.
  - **+N this week · +N this month** under each main bar: All N Levels Combined, the rank, Near Native (frequency), and on the Kanji & Grammar tab All Kanji and All Grammar (from the progress history). Click a number to open those cards in the Anki Browser; the JLPT goal's "Today" numbers work the same way
- **Frequency Check** — compares your deck against the 20,000 most common words in written Japanese (BCCWJ corpus). The rank counts every card; this shows whether they're the words that matter:
  - a summary bar: how many of the 20,000 most common words (near-native vocabulary) are in your deck
  - how many of your words are common, and roughly what share of everyday written text your vocabulary covers, with a smaller second number for everyday speech (real conversation, CEJC corpus; the bars stay written Japanese)
  - **One tile per word**: words that differ in meaning get their own tiles even where the corpus lumps them together (聞く / 聴く, 返る / 帰る, 町 / 街, 今日 きょう / こんにち); a tile the corpus can't count separately sits next to the one it's counted with, at the same frequency ("frequency shared with …" on hover). The same word with another reading or kanji spelling stays one tile (明日 あした / あす). Common compounds the corpus splits (でも, お金, 可能性) are included, with their meanings on hover, and 感ずる-style verbs count as 感じる
  - **Size bars** (always shown): the top 6,000 and 13,800 words. Their sizes follow modern estimates of the vocabulary N2 and N1 ask for, but the words are the most common in written Japanese, not the test's words (use the JLPT bars for those; up to N3 they're the guide). Written Japanese matters more from N2 on, and an N2 or N1 JLPT goal fills its second step from these bars; written Japanese matters more at N2 and N1, whose reading sections are newspaper-style articles and essays. Unlike the JLPT bars, each one includes the ranges before it; hover a bar for its own band (e.g. words #1,501–3,900). Also shows the most common words you're missing (click → copy the word, Shift+Click → Jisho)
- **Debug preview** buttons: ±250 notes (display only), **★ Mark All JLPT Found** (writes to `overrides.json`), and **Test belt-up / rank-up toast** (shows the review-time rank-up message for the next belt or rank above the previewed count)

### Word Grid
- Every word in the JLPT lists as a coloured tile, with a search bar: known words first, then missing
- In every grid, known words are **grouped Mature → Young → Learning** (words marked found by hand last), most common first within each group (the JLPT grid shows level by level, grouped by maturity inside each level)
- Clicking a Frequency Check bar opens the same grid for the top-N most common words, known first then missing, each in rank order. **Middle-click** marks a frequency word found (counts as known) and **Ctrl+Middle-click** suspends it (left out of the counts and the totals). Found/suspended marks are shared with the JLPT lists: a word marked on either counts on both; press Refresh to update the bars
- **Known words** in the level's colour — click to open the note in the Anki Browser. The colour gets more vivid as the card matures: new / learning (faded), young, mature (full colour). A note with several cards uses its most mature card.
- **⧉ Duplicate cards:** a faint ⧉ in a tile's corner means you have more than one note for that word: exact copies, a kana and a kanji card for the same word (できる / 出来る), or one card for each level the word is listed on. Click the tile to see them all in the Browser. It goes further than Anki's own duplicate check, which only compares the first field as typed. Different kanji (会う / 遭う), different readings and a kana card for a kanji word (ねこ / 猫) are not counted as duplicates. Every grid that shows some also gets a line beside its search box, "⧉ Words with more than one card: N — see the list": the list names each one (できる · 出来る ×2), click a word to open its cards, or open them all. Shown only when there are duplicates.
- **Missing words** in dark grey — click to copy the word, then paste it into your browser and add it with Yomitan
- **Hover** any tile → the word's English meaning (part of speech + the first 7 meanings, from Jitendex), plus its status. Missing Words rows, Off-list rows and the Frequency Check's missing-word chips show the meaning too. Only words on the JLPT or frequency lists have meanings
- **Shift+Click** any tile (known words too) → look the word up on Jisho, for the full entry
- **Ctrl+Click** any tile → search the whole collection for that word's text
- **Middle-click** a missing word → toggle *marked as found* (counts as known)
- **Ctrl+Middle-click** a missing word → toggle *suspended* (removed from all counts)

### Missing tab
- A **Show: Vocab / Kanji / Grammar** dropdown at the top. Kanji: every JLPT kanji with no learned card (level, kanji, meaning, on, kun; most common first or by level); grammar: every point not learned (level, pattern, meaning, formation). Click a kanji row to copy it, or a grammar row to find every form of the point in your deck (see below); Shift+Click → Jisho (kanji) or a web search (grammar)
- Grammar also has a note on why some obvious points are listed, a **★ Found** button on every row (kanji too), and **★ Mark basic particles as found** (toggle): は, が (subject), を, に (destination / time / target), で (place / means), の, も, と (and / with), へ, か (question), ね, よ
- Vocab: a filterable table of missing words, by level or all levels
- Click a row to copy the word; Shift+Click to look it up on Jisho
- **Copy all to clipboard** exports the list as TSV (word TAB reading)

### Marked & Suspended tab
- A **Show: Vocab / Kanji / Grammar** dropdown at the top. The kanji and grammar pages list what you marked found or suspended in their grids, with Revert and Reset All buttons. The tab label counts all three
- Lists every override with per-word **Revert** buttons
- The found table has **Show** (All levels, N5–N1, Frequency list only) and **Sort** (Most common first, By level, A–Z) dropdowns and a Rank column
- Readings are left blank for words written without kanji (also in Missing Words and Off-list)
- **Reset All Found** and **Reset All Suspended**
- **Mark English Loanwords as Found** — on by default (a fresh install marks them once; unmarking sticks); marks English loanwords (カメラ, テーブル, テレビ, コーヒー …) as known, including dated ones (ワープロ, テープレコーダー). Excludes wasei-eigo and false friends whose Japanese meaning is something else (サラリーマン, マンション, ストーブ), Japanese-made shortenings (パソコン, コンビニ) and words that don't sound like English (アルバイト, パン). Covers the JLPT lists **and the 20,000-word frequency list**.
- The loanword button is a toggle — click again to undo
- Overrides are stored in `user_files/overrides.json` inside the add-on folder (Anki keeps `user_files` when the add-on updates); a file placed there is picked up on Refresh. An `overrides.json` from an older version in the add-on folder is copied there automatically, with a backup copy (`overrides_backup_before_move.json`)

### Off-list tab
- Your deck cards that aren't on the Kotodama JLPT lists (the lists are old and incomplete, so many can still appear on the test). They still count toward your rank and the Frequency Check.
- Tile grid on the left (grouped Mature → Young → Learning, most common first) and a filterable word list on the right; drag the divider to resize.
- Click a tile or double-click a row to open the note in the Browser.

### Kanji & Grammar tab
- Kept apart from your words on purpose: kanji and grammar **don't affect your rank or the word counts**, so their bars are small
- **Kanji**: an All Kanji bar and N5–N1 bars for OpenJLPT's 2,383 kanji. A kanji is **known** once a card you've studied contains it (learning counts; suspended cards never count). Click a bar to open its kanji grid
- **Kanji grid**: tiles coloured by **how well you know each kanji**, a weak → strong heatmap (red → orange → yellow → green → teal → cyan) from the average strength of the learned cards that contain it, nudged by how many there are (a kanji or grammar point in several cards reads a little stronger than one in a single card; the deck's overall average stays the same). Strength comes from each card's FSRS stability (1 day → weakest, about a month → middle, 2 years → strongest), lowered a little for high difficulty and for each lapse; without FSRS the interval and ease are used. Learned kanji are sorted strongest → weakest; unseen kanji are dark grey and follow
- Hover a kanji → meanings, on/kun readings, strength, best card maturity, the cards that contain it and the most common words with it you don't know yet. **Click** a kanji → a window with your cards that use it (click one to open it in the Browser) and the most common words with it you don't know yet, most common first (click to copy, Shift+Click → Jisho), plus Search cards in Browser / Copy kanji / Jisho buttons. **Shift+Click** → Jisho's kanji page. **Middle-click** marks an unseen kanji found, **Ctrl+Middle-click** suspends it (kept in `user_files/kanji_overrides.json`, separate from word marks)
- The All Kanji grid ends with **Off-list kanji**: kanji in your cards that aren't on any JLPT level (not counted)
- **Grammar**: an All Grammar bar and N5–N1 bars for OpenJLPT's 526 grammar points. A point is known once a card you've studied names it: from your grammar deck, or found by the auto parser in your sentences, or by marking it found by hand (middle-click in the grid). A vocab card whose word *is* a grammar form (でも, ながら, つつ) counts for every point written that way (でも → "even if" and "…or something", as a suggestion), since a good dictionary on the card explains all its uses; only the word field is read, never the dictionary or example fields. Kanji-only forms (方, 中, 以上) and forms that are everyday words (出す, 切る, 始める) don't count this way. A point that's in one of your cards but not learned yet (the card is new, not studied yet) gets a **dashed outline** in the grid, right after your known points: it counts once you study the card. Spaces inside a sentence (common in subtitle-mined cards: 社長か 副社長に 確認して ください) don't stop a point from being found. Click a bar to open the **grammar grid**: tiles as wide as their pattern, the same weak → strong colours, learned points strongest first, then the rest in OpenJLPT's order
- Hover a grammar point → meaning, formation, an example sentence, strength and your cards. Click a learned point → its cards in the Browser; click any other (or **Ctrl+Click** a learned one) → **find it in your deck**: the Browser lists every note in the deck containing any written form of the point (〜 dropped, all variants, conjugated endings: 〜ことがある also finds ことがあります, 〜てはいけない finds てはいけません). It finds more than the auto detection does, so you can read the sentences and mark the point found if you know it. If no note matches, the Browser still opens with the search typed in, so you can loosen or change it. **Shift+Click** → web search. **Middle-click** marks it found, **Ctrl+Middle-click** suspends it (kept in `user_files/grammar_overrides.json`)

### Text Check tab
- Paste Japanese text (an article, a chapter, a web page) or **Open file…** (.txt, or .srt / .vtt / .ass subtitles; timestamps and styling are dropped) and **Check text**
- **Coverage**: the share of the text's words you know, counted every time a word appears, the same way the bars count words (a learned card or a found mark for its JLPT entry or frequency tile). Particles and endings aren't counted; a stretch no list word covers (names, rare words) counts as one unknown piece. Plus a verdict: 98%+ comfortable, 95–98% good for immersion, 90–95% challenging, below that hard
- **Kanji and grammar** (Show: Vocab / Kanji / Grammar): every kanji in the text (how often, JLPT level, known or not, the text's words that use it) and every grammar point found in it (level, known or not, how often; hover a row for the sentences it's in, the trigger highlighted). Basic particles (は, が, を…) aren't listed. A summary line gives the share of the text's kanji you know and how many of its grammar points you haven't learned yet. Grammar detection is precise (≈99%) but can miss about 1 in 10 points.
- The text is split by the same parser as sentence fields, so its limits apply (an occasional misread split)
- **Word list**: the unknown words (or all words, known ones in green), sorted by how often they appear in the text or by how common they are in Japanese, with rank, JLPT level and meaning on hover. Click → copy, Shift+Click → Jisho; **Copy unknown words** copies them all (word TAB reading). Below it, the pieces not on our lists

### History tab
- A chart of your progress over time: learned notes (the rank count), mature notes, JLPT words per level and in total, known kanji, known grammar points, and the Frequency Check tiers
- Show the last **7 / 30 / 90 days** or **all time**; turn **Rank**, **JLPT levels**, **Kanji**, **Grammar** and **Frequency** lines on or off; hover the chart for each day's numbers
- A **summary table** for learned (rank), mature, JLPT words, kanji, grammar and Near Native: the number now, the gain this week, this month, this year (since January 1) and since the history starts, and your best 7 days
- A snapshot is saved automatically once a day (whenever the deck list or this window runs an analysis); **Take snapshot now** rescans and saves today's numbers right away. Snapshots are kept in `user_files/history.json`
- Days before your first snapshot are **rebuilt from your review history**: rank and mature from your reviews; JLPT, kanji, grammar and frequency from when the first card with them was first reviewed (or added, if never reviewed). Rebuilt days always use the current word lists. Words marked found count from the first day; deleted cards and past found/suspended marks can't be rebuilt
- No projected dates — just what you've done

---

## Matching logic
Each JLPT entry is matched to at most one note, trying in order:
1. Exact match on the display (kanji) form, or one of the list's alternate spellings (いちばん ↔ 一番)
2. Kana-only card whose display field equals the JLPT reading
3. Reading-field match — only when that reading is unique across all JLPT lists
4. Honorific prefix — JLPT お/ご+kanji (e.g. お皿) matches a bare-root card (皿)

A card written with kanji can count for a list word written in kana (出来る → できる), but a kana-only card never counts for a list word written with kanji. Words usually written in kana (うるさい, さすが, めがね…) are listed in kana, so both kinds of card count for them.

Different kanji make different words, even with the same reading: a 会う card doesn't count for N2 遭う, nor 作る for 造る, 飛ぶ for 跳ぶ, 長い for 永い. Choosing the right kanji is exactly what the N2/N1 kanji questions test. Writing a kanji in kana (子ども / 子供), the honorific 御 (御飯 / ご飯) and print-variant glyphs (剝 / 剥) still count as the same spelling.

When several notes are candidates, one whose reading matches (hiragana/katakana treated as equal) is preferred. HTML, furigana brackets and ruby markup are stripped before matching. Levels are processed N5 → N1, and each note counts toward at most one level.

## Browser search
Clicking a known word tile searches the Browser with `nid:<note_id>`, which always finds the exact note regardless of its field content.

## Data sources & credits
The same credits are in Anki under **Kotodama → About Kotodama…**.

- **JLPT lists:** [OpenJLPT](https://github.com/evanclan/OpenJLPT) (CC BY-SA 4.0), levels from [Jonathan Waller's JLPT lists](https://web.archive.org/web/20260406082505/http://www.tanos.co.uk/jlpt/) (CC BY; archived copy, the site is offline)
- **Loanword flags and spelling mapping:** [JMdict](https://www.edrdg.org/jmdict/j_jmdict.html), Electronic Dictionary Research and Development Group (CC BY-SA 4.0)
- **Frequency list:** BCCWJ short-unit-word frequency list v1.0, National Institute for Japanese Language and Linguistics (NINJAL) (CC BY-NC-ND 3.0)
- **Everyday speech percentage:** CEJC (Corpus of Everyday Japanese Conversation) short-unit-word vocabulary table ver202209, NINJAL (CC BY-NC-ND 3.0)
- **Estimated ranks for compounds (≈):** BCCWJ long-unit-word frequency list v1.0, NINJAL (CC BY-NC-ND 3.0). Words the short-unit list splits apart (日本語, 可能性) get the rank their frequency would have in it, shown as ≈#N. Those estimated above #6,000 also join the 20,000-word list.
- **Grammar points** (patterns, meanings, formation, examples): [OpenJLPT](https://github.com/evanclan/OpenJLPT) contributors (CC BY-SA 4.0)
- **Kanji levels, readings and meanings:** [OpenJLPT](https://github.com/evanclan/OpenJLPT) (CC BY-SA 4.0): Jonathan Waller's kanji levels (CC BY) and [KANJIDIC2](https://www.edrdg.org/wiki/KANJIDIC_Project.html), EDRDG (CC BY-SA 4.0)
- **Meanings on hover:** [Jitendex](https://jitendex.org) by Stephen Kraus (CC BY-SA 4.0), based on JMdict
- **Extra JLPT words:** a few words on Jonathan Waller's lists that OpenJLPT omits (via [stephenmk/yomitan-jlpt-vocab](https://github.com/stephenmk/yomitan-jlpt-vocab), which keeps Waller's levels; CC BY-SA 4.0)
- **Community additions:** 211 words on community JLPT lists ([jamsinclair/open-anki-jlpt-decks](https://github.com/jamsinclair/open-anki-jlpt-decks), [elzup/jlpt-word-list](https://github.com/elzup/jlpt-word-list)) that Waller's current lists don't have, e.g. 顔, 母, 頑張る, 当然, 仕方がない. They use those lists' levels and are flagged `community` in the list files. Both lists are MIT-licensed; their notices are in `THIRD_PARTY_NOTICES.txt`.

## Supporting Kotodama
Kotodama is free, and nothing is unlocked by money. **♥ Support** (bottom left of the window) explains how to leave a tip on [Ko-fi](https://ko-fi.com/benastromo). If you're in Nakama and put your friend code in the Ko-fi message, your Nakama card and share image say **♥ Supported Kotodama**: one plain line, the same for any amount. The Nakama server keeps only the date of your first tip with your code (no name, email or amount).

## Compatibility
- Anki 2.1.50+, Qt6 or Qt5 builds. On the older Qt5 builds (2.1.50–2.1.66) everything works except the top rank's animated picture (shown still) and its star ambience (silent), which need Qt6
- Desktop only — AnkiDroid/AnkiMobile do not support add-ons

## Licence
Copyright (C) 2026 BenAstromo.

Kotodama's code is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version. It is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License (the LICENSE file) for more details.

The bundled data keeps its own licences (see Data sources & credits): the derived word, kanji, grammar and meaning files are shared under CC BY-SA 4.0, and the frequency files (freq_bccwj.txt, freq_extra.txt, freq_cejc.txt, freq_splits.py) remain under NINJAL's CC BY-NC-ND 3.0 terms. The rank pictures are by the author; the animated Amaterasu was made in Wallpaper Engine.
