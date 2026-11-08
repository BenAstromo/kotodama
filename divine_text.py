"""
divine_text.py
Amaterasu gold mode, text (owner 2026-10-09): every visible English text in
the add-on's windows turns into gold Japanese — except Settings and hover
tooltips, which stay English. At 20,000 words everything reads "max", so the
mode is about feel; the numbers stay as they are.

Rather than touching every place a label is built, apply() walks a window's
widgets (labels, buttons, check boxes, tabs, drop-downs, search
placeholders), translates what it recognises and remembers the original, so
turning gold mode off (the debug −250) restores the English. Text it doesn't
recognise (the debug row, deck and word names) is left alone.

Translation, in order: an exact match of the whole text; then the regex
PATTERNS (texts with numbers in them); then PHRASES, replaced inside the text
(longest first) for anything built from pieces.
"""

import re

from aqt.qt import (QWidget, QLabel, QAbstractButton, QComboBox, QLineEdit,
                    QPlainTextEdit, QTextEdit, QTabWidget, QTableWidget, QColor, Qt)

GOLD = "#f5c518"
_MONTHS = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}

EXACT = {
    # JLPT goal (goal_view.py, history_view.py, share_card.py; owner 2026-10-20)
    "JLPT Goal": "JLPT目標", "<b>JLPT Goal</b>": "<b>JLPT目標</b>", "JLPT goal": "JLPT目標",
    "Set a JLPT goal…": "JLPT目標を設定…", "Set your next goal…": "次の目標を設定…",
    "Change…": "変更…", "Other date…": "別の日付…", "Save": "保存", "Cancel": "キャンセル",
    # Progress Review (review_view.py, owner 2026-10-27)
    "Progress Review": "振り返り", "Goal reached": "目標達成",
    "Click any heading or item to see its cards in the Browser.":
        "見出しや項目をクリックすると、そのカードをブラウザで開きます。",
    "Nothing new yet today.": "今日はまだ新しいものはありません。",
    "Nothing new in these days.": "この期間に新しいものはありません。",
    "No history yet: the review fills in as you study.": "まだ履歴がありません。学習するにつれて振り返りが埋まります。",
    "Test date:": "試験日：", "Remove goal": "目標を削除",
    "Show time with Kotodama": "言霊と過ごした時間を表示", "Show JLPT goal": "JLPT目標を表示",
    "Which words count: first every word on the JLPT lists up to your level. The lists fall a little short of what each level needs, so a top-up adds the most common words from the harder levels, up to your level's size (N5 800, N4 1,500, N3 3,900, N2 6,000 words). Real tests use some of these words too. Kanji and grammar use the JLPT lists.":
        "数える単語：まず、あなたのレベルまでのJLPTリストのすべての単語。リストは各レベルに必要な語数より少し少ないので、上のレベルの頻出語で補い、レベルの語数（N5 800、N4 1,500、N3 3,900、N2 6,000語）まで増やします。実際の試験にもこうした単語が出ます。漢字と文法はJLPTリストを使います。",
    "Which words count: first every word on the JLPT lists up to N1. N1 has no harder level, so the top-up adds the most common words of written Japanese that aren't on the lists, up to 13,800 words in all (about three-quarters of the high estimate of 18,000 words for N1).":
        "数える単語：まず、N1までのJLPTリストのすべての単語。N1より上のレベルはないので、リストにない書き言葉の頻出語で補い、合計13,800語まで増やします（N1の推定の上限18,000語の約4分の3）。",
    "Taking the JLPT? Pick your level and test date, and Kotodama works out how much to learn each day.":
        "JLPTを受けますか？レベルと試験日を選ぶと、言霊が1日に覚える量を計算します。",
    "Which JLPT are you taking, and when? The test covers every level up to yours, so N3 means N5, N4 and N3.":
        "どのJLPTを、いつ受けますか？試験はそのレベルまでの全範囲なので、N3ならN5・N4・N3です。",
    "Review time: the last two weeks before the test are for review and practice tests.":
        "復習期間：試験前の最後の2週間は、復習と模擬試験のための期間です。",
    "The finish line is 14 days before the test: the last two weeks are for review and practice "
    "tests. Per day is what's left at the start of today, divided by the days to the finish line: "
    "fall behind and the daily number goes up; get ahead and it goes down.":
        "ゴールは試験の14日前：最後の2週間は復習と模擬試験のためです。1日の量は、今日の始まりに"
        "残っていた量をゴールまでの日数で割ったもの。遅れると1日の量が増え、先に進むと減ります。",
    # the goal card's "?" (goal_view._show_info, owner 2026-10-28)
    "<b>How many words each level needs</b>": "<b>各レベルに必要な語数</b>",
    "Cumulative: each level includes the vocabulary below it. The sizes follow modern estimates "
    "for each JLPT level, the same milestones as the rank.":
        "累計です。各レベルはそれ以下の語彙をすべて含みます。語数は各JLPTレベルの現代の推定に"
        "合わせた、ランクと同じ節目です。",
    "<b>Which words count</b>": "<b>数える単語</b>",
    "<b>The daily number</b>": "<b>1日の量</b>",
    "English loanwords you mark as found join your known words gradually, as your card count "
    "grows. Until one joins, the goal leaves it out of what's still to learn, so the daily number "
    "doesn't ask you to study a word you already know.":
        "見つけた印を付けた英語の外来語は、カードが増えるにつれて少しずつ既知語に加わります。"
        "加わるまでは目標の「残り」から外すので、もう知っている語を1日の量で求めることはありません。",
    "When kanji or grammar need 6 or fewer a week, they show a number for the week instead, counted over "
    "the past 7 days. It turns green when you learn one today, or when the past 7 days already "
    "reach the week's number.":
        "漢字や文法が週6つ以下でよいときは、代わりに週の数を表示します（過去7日間で数えます）。今日1つ覚えるか、"
        "過去7日間ですでに週の数に届いていれば緑になります。",
    "Click a Today number for the Progress Review: what you learned today and this week, each "
    "card a click away.":
        "「今日」の数字をクリックすると振り返りが開きます：今日と今週に覚えたもの、"
        "どのカードもクリックひとつで。",
    "Time with Kotodama": "言霊と過ごした時間",     # rank "?" window (loyalty.py)
    # tabs and window
    "Overview": "概要",
    "Word Grid": "単語グリッド",
    # "please wait" notes (busy.py, owner 2026-10-25)
    "Please wait…": "少々お待ちください…",
    "Opening Kotodama…": "言霊を開いています…",
    "Building the Word Grid…": "単語グリッドを作成中…",
    "Building the Missing list…": "未習得リストを作成中…",
    "Building Marked & Suspended…": "発見済み・保留を作成中…",
    "Building the Off-list tab…": "リスト外を作成中…",
    "Building the grid…": "グリッドを作成中…",
    "Updating the window…": "画面を更新中…",
    "Counting your deck…": "デッキを数えています…",
    "Updating the list…": "リストを更新中…",
    "Checking the text…": "テキストをチェック中…",
    "Missing": "未習得",
    "Kanji && Grammar": "漢字 && 文法",
    "History": "履歴",
    "Close": "閉じる",
    # Duplicate cards list (progress_dialog._show_duplicates, owner 2026-10-27)
    # ♥ Support note (progress_dialog._show_support_note, owner 2026-10-27)
    "Support Kotodama": "言霊を応援", "Go to Ko-fi": "Ko-fiへ",
    "Kotodama is free. If it helps you, you can leave a tip on Ko-fi. Nothing is unlocked by it: thank you!":
        "言霊は無料です。役に立っていたら、Ko-fiでチップを送れます。それで何かが解放されることはありません。ありがとうございます！",
    "Put your friend code in the Ko-fi message, and your Nakama card and share image will say "
    "“♥ Supported Kotodama”, the same for any amount. It shows once your Nakama tab next updates.":
        "Ko-fiのメッセージに仲間コードを書くと、仲間カードと共有画像に「♥ 言霊サポーター」と表示されます"
        "（金額に関係なく同じです）。次に仲間タブが更新されると表示されます。",
    "Join Nakama first (the Nakama tab) and put your friend code in the Ko-fi message, and your card "
    "and share image will say “♥ Supported Kotodama”.":
        "まず仲間に参加し（仲間タブ）、Ko-fiのメッセージに仲間コードを書くと、カードと共有画像に"
        "「♥ 言霊サポーター」と表示されます。",
    "Only the date of your first tip is kept with your code: no name, email or amount.":
        "コードと一緒に保存されるのは最初のチップの日付だけです。名前、メール、金額は保存されません。",
    "Open all in browser": "すべてブラウザで開く", "Duplicate cards": "重複カード",
    "The same word in more than one note. Click a word to open its cards in the browser.":
        "同じ単語が複数のノートにあります。単語をクリックするとそのカードをブラウザで開きます。",
    "♥ Support": "♥ 応援する",
    # Overview
    "Click any bar to open that level's word grid.":
        "バーをクリックすると、そのレベルの単語グリッドが開きます。",
    "⟳ Refresh": "⟳ 更新",
    "⟳ Refresh Progress": "⟳ 進捗を更新",
    "<b>All N Levels Combined</b>": "<b>全Nレベル合計</b>",
    "<b>Kotodama 言霊 Japanese Rank</b>": "<b>言霊 日本語ランク</b>",
    "<span style='font-size:22px; font-weight:600; letter-spacing:1px;'>Kotodama</span>"
    "&nbsp;&nbsp;<span style='font-size:22px; color:#d4a017;'>言霊</span>"
    "&nbsp;&nbsp;<span style='font-size:18px; color:#555555;'>|</span>&nbsp;&nbsp;"
    "<span style='font-size:18px; color:#bbbbbb;'>JLPT Tracker</span>":
        "<span style='font-size:22px; font-weight:600;'>言霊</span>"
        "&nbsp;&nbsp;<span style='font-size:22px;'>ことだま</span>"
        "&nbsp;&nbsp;<span style='font-size:18px;'>|</span>&nbsp;&nbsp;"
        "<span style='font-size:18px;'>JLPT 進捗</span>",
    "Vocabulary": "語彙",
    "<b>JLPT Vocabulary</b>": "<b>JLPT 語彙</b>",
    "Counts every card you've studied in the selected deck, plus every word you've "
    "marked as found, toward 20,000 — the vocabulary size associated with native-like "
    "fluency. New cards count once you study them, like the JLPT bars and goal.":
        "選択したデッキで学習したすべてのカードと、発見済みにしたすべての単語を、"
        "ネイティブ並みの語彙量とされる20,000語に向けて数えます。"
        "新しいカードは、JLPTバーや目標と同じく、一度学習すると数えられます。",
    "TENTH-DEGREE BLACK BELT": "十段 黒帯",
    "Amaterasu": "天照大神",
    "<b>Frequency Check</b>": "<b>頻度チェック</b>",
    # Frequency Check redesign (owner 2026-10-20)
    "The most common words in written Japanese, and how many you know.":
        "書き言葉で最もよく使われる語と、そのうちいくつを知っているか。",
    "of everyday written text": "日常の書き言葉をカバー",
    # the loanword "?" (owner 2026-10-21)
    "English loanwords (カメラ, テーブル, データ…) are words most English speakers understand after "
    "seeing them once or twice in context, so they're marked as found from the start and you don't "
    "need cards for them. It's your choice: if you'd rather learn them like any other word and "
    "create Anki cards for them, or English isn't your first language, press the button to unmark them.":
        "英語の外来語（カメラ・テーブル・データ…）は、英語を話す人なら文脈で一、二度見れば分かる語なので、"
        "最初から発見済みになっていて、カードは要りません。使うかどうかは自由です："
        "ほかの語と同じようにAnkiのカードを作って覚えたい人や、英語が母語でない人は、ボタンで解除してください。",
    "<b>They count gradually, as your vocabulary reaches them.</b> Sorted from most to least "
    "common, each marked loanword joins once your rank reaches its frequency rank. Very common ones like テレビ count almost at once; one ranked "
    "8,000 counts once your rank reaches about 8,000. A loanword on a JLPT list but not in the "
    "20,000-word frequency list takes its level's place in that order: N5 800, N4 1,500, "
    "N3 3,900, N2 6,000, N1 13,800.":
        "<b>語彙がそこに届くにつれて、少しずつ数えます。</b>よく使われる順に、発見済みの各外来語は、"
        "ランクがその語の頻度順位に達したときに加わります。"
        "テレビのようにとてもよく使われる語はほぼすぐに、順位8,000の語はランクが約8,000に達したときに数えられます。"
        "JLPTのリストにあって頻度リスト（20,000語）にない外来語は、レベルごとの位置に並びます："
        "N5は800、N4は1,500、N3は3,900、N2は6,000、N1は13,800。",
    "<b>One order, everywhere.</b> A loanword either counts or doesn't yet, the same for your "
    "rank, the JLPT bars, the frequency bars, your goal, your history and your Nakama card. Each "
    "counts only the counted loanwords that belong to it, so the numbers differ: the rank counts "
    "all of them, the frequency bars the ones in the top 20,000, the JLPT bars the ones on a JLPT "
    "list (many everyday loanwords aren't on one). A word on both, like テレビ, counts on both. "
    "Your marks stay: a loanword that doesn't count yet keeps its ★. Middle-click a faint ★ "
    "to count that word now, like any word you mark; middle-click again to unmark it.":
        "<b>順番はどこでも一つです。</b>外来語は「数えられている」か「まだ」のどちらかで、"
        "ランク・JLPTバー・頻度バー・目標・履歴・仲間カードのどこでも同じです。"
        "それぞれは数えられた外来語のうち自分に当てはまるものだけを数えるので、数字は違います："
        "ランクはすべて、頻度バーは上位20,000語に入るもの、JLPTバーはJLPTのリストにあるもの"
        "（日常の外来語の多くはリストにありません）。テレビのように両方にある語は両方で数えられます。"
        "印はそのままで、まだ数えられていない外来語も★のままです。"
        "薄い★を中クリックすると、ほかの発見済みの語と同じようにすぐ数えます。もう一度中クリックで印を外します。",
    "Why: marking about 2,500 loanwords at once would skip the early ranks, but you shouldn't need "
    "thousands of cards for words you already understand to reach 20,000. With every loanword "
    "marked, the last one joins at about 17,500 learned cards, exactly where marking them all at "
    "once would have reached 20,000. It also keeps ranks fair to compare: the share image and your "
    "Nakama card say how many loanwords are counted.":
        "理由：約2,500語を一度に数えると序盤のランクを飛ばしてしまいますが、分かっている語のために何千枚もの"
        "カードを作らなくても20,000に届くべきです。すべて発見済みにした場合、最後の外来語は覚えたカード約17,500枚で"
        "加わり、一度に数えたときに20,000に届くのとちょうど同じ地点です。ランクを公平に比べられるよう、"
        "共有画像と仲間カードには数えている外来語の数が表示されます。",
    "Left out: wasei-eigo (サラリーマン), false friends (マンション), Japanese-made shortenings "
    "(パソコン) and loanwords from other languages (パン, アルバイト).":
        "対象外：和製英語（サラリーマン）、意味の違う語（マンション）、日本で作られた略語（パソコン）、"
        "英語以外からの外来語（パン・アルバイト）。",
    "Hide other spellings and readings of words you know": "知っている語の別表記・別の読みを隠す",
    "The percentage at the top is how much of everyday written text your known words cover, "
    "weighted by how often each word is used.":
        "上の割合は、知っている語が日常の書き言葉のどれだけをカバーしているかです（語の使用頻度で重み付け）。",
    "Bars and word lists: BCCWJ (Balanced Corpus of Contemporary Written Japanese, "
    "NINJAL) — top 20,000 content words; particles, numerals and proper nouns excluded.":
        "バーと単語一覧：BCCWJ（現代日本語書き言葉均衡コーパス、国立国語研究所）— "
        "上位20,000の内容語（助詞・数詞・固有名詞を除く）",
    # everyday speech percentage (owner 2026-10-27)
    "of everyday speech": "日常の話し言葉をカバー",
    "Everyday speech percentage: CEJC (Corpus of Everyday Japanese Conversation, "
    "NINJAL) — top 20,000 content words; particles, numerals and proper nouns excluded.":
        "話し言葉の割合：CEJC（日本語日常会話コーパス、国立国語研究所）— "
        "上位20,000の内容語（助詞・数詞・固有名詞を除く）",
    "The smaller percentage under it is the same for everyday speech: real "
    "conversations recorded at home, at work, in shops and with friends. "
    "Conversation uses a small set of words over and over, so it's higher: "
    "that's real, not a flattering estimate.":
        "その下の小さい割合は、日常の話し言葉について同じものです。家庭・職場・お店・友人との"
        "実際の会話を録音したものです。会話は少ない語を何度も使うので割合が高くなります。"
        "甘い見積もりではなく、実際にそうなのです。",
    # Kanji & Grammar tab
    "Kanji and grammar are tracked separately from your words: they don't affect your "
    "rank or the word counts. Click a bar to open its grid.":
        "漢字と文法は単語とは別に記録されます。ランクや単語数には影響しません。"
        "バーをクリックするとグリッドが開きます。",
    # History tab
    "<b>Progress History</b>": "<b>進捗の履歴</b>",
    "Take snapshot now": "今すぐ記録",
    "No snapshot saved yet": "まだ記録がありません",
    "One snapshot per day is saved automatically. Days before the first snapshot are "
    "rebuilt from your review history: rank and mature from your reviews, JLPT, kanji, "
    "grammar and frequency from when the first card with them was first reviewed (or "
    "added, if never reviewed), always using the current lists. Words marked found count "
    "from the first day. Deleted cards and past found/suspended marks can't be rebuilt.":
        "記録は1日1回自動で保存されます。最初の記録より前の日は復習履歴から再現します："
        "ランクと成熟は復習から、JLPT・漢字・文法・頻度はそれを含むカードを初めて復習した日"
        "（未復習なら追加日）から、常に現在のリストで計算します。発見済みの単語は初日から数えます。"
        "削除したカードや過去の発見済み・保留の印は再現できません。",
    # History summary table (2026-10-15)
    "Now": "現在", "Today": "今日", "This week": "今週", "This month": "今月", "This year": "今年",
    "Since start": "開始から", "Best week": "最高の週",
    "7 days": "7日", "30 days": "30日", "90 days": "90日", "All time": "全期間",
    "Rank": "ランク", "JLPT levels": "JLPTレベル", "Frequency": "頻度",
    # Missing / Marked & Suspended / Off-list
    "Show:": "表示：", "<b>Show:</b>": "<b>表示：</b>", "Sort:": "並び：", "Level:": "レベル：",
    "Vocab": "単語", "Kanji": "漢字", "Grammar": "文法",
    "All levels": "全レベル",
    "Most common first": "よく使われる順",
    "By level": "レベル順",
    "A–Z": "五十音順",
    "Copy all": "すべてコピー",
    "Copy all to clipboard": "すべてクリップボードにコピー",
    "Reset All Found": "発見済みをすべて解除",
    "Reset All Suspended": "保留をすべて解除",
    "Revert": "元に戻す",
    "★ Found": "★ 発見済み",
    "Click a row to copy the word to clipboard.": "行をクリックすると単語をコピーします。",
    "Click a row to copy the word · Shift+Click to open it on Jisho.org.":
        "行をクリックで単語をコピー · Shift+クリックでJisho.orgを開く",
    "Click a row to copy the kanji · Shift+Click to open it on Jisho.":
        "行をクリックで漢字をコピー · Shift+クリックでJishoを開く",
    "Click a row to find every form of it in your deck · Shift+Click to search the web for it · Right-click to copy the example sentence.":
        "行をクリックでデッキ内のあらゆる形を検索 · Shift+クリックでウェブ検索 · 右クリックで例文をコピー",
    # grids
    "Hover: meaning  ·  Shift+Click: Jisho  ·  Middle-click: mark as found  ·  "
    "Ctrl+Middle-click: suspend (exclude from list)":
        "ホバー：意味 · Shift+クリック：Jisho · 中クリック：発見済みにする · "
        "Ctrl+中クリック：保留（リストから除外）",
    "No matches found.": "見つかりません。",
    "Frequency list only": "頻度リストのみ",
    "About the Kotodama 言霊 Japanese Rank": "言霊 日本語ランクについて",
    "Share image…": "画像で共有…",
    "Share your progress": "進捗を共有",
    "Name:": "名前：",
    "Message (shown on the image and engraved on the Overview):":
        "メッセージ（画像に表示され、概要に刻まれます）：",
    "Save PNG…": "PNGで保存…",
    "Copy image": "画像をコピー",
    "Save image": "画像を保存",
    "All Ranks": "全ランク",
    "<b>Middle-click</b> any tile to mark a word as found (★ yellow border) — it will count "
    "toward your progress without being in your Anki deck.<br><b>Ctrl+Middle-click</b> to "
    "suspend a word (✕ dim tile) — it will be hidden from the JLPT lists entirely.<br>Use the "
    "<b>Revert</b> buttons below to undo an override.":
        "<b>中クリック</b>でタイルを発見済みにします（★ 黄色の枠）— Ankiのデッキになくても"
        "進捗に数えられます。<br><b>Ctrl+中クリック</b>で単語を保留にします（✕ 暗いタイル）"
        "— JLPTリストから完全に外れます。<br>下の<b>元に戻す</b>ボタンで取り消せます。",
    # Text Check tab (2026-10-14)
    "Text Check": "テキストチェック",
    "Paste Japanese text (an article, a chapter, a subtitle file) to see how much of it you "
    "already know, and which new words in it are worth learning.":
        "日本語のテキスト（記事、小説の一章、字幕ファイル）を貼り付けると、"
        "どれだけ知っているか、どの新しい語を覚える価値があるかが分かります。",
    "Open file…": "ファイルを開く…",
    "Check text": "チェック",
    "Unknown words": "知らない語",
    "All words": "すべての語",
    "Most frequent in this text": "このテキストで多い順",
    "Most common in Japanese": "日本語でよく使われる順",
    "Copy unknown words": "知らない語をコピー",
    # Text Check: kanji and grammar (owner 2026-10-20)
    "Unknown kanji": "知らない漢字", "All kanji": "すべての漢字",
    "Grammar not learned yet": "未習得の文法", "All grammar points": "すべての文法",
    "By JLPT level": "JLPTレベル順",
    "Copy unknown kanji": "知らない漢字をコピー", "Copy grammar not learned yet": "未習得の文法をコピー",
    "Click a row to copy the kanji · Shift+Click to open it on Jisho.org.":
        "行をクリックで漢字をコピー · Shift+クリックでJisho.orgを開く。",
    "Click a row to copy the pattern · Hover a row for the sentences it's in. Basic particles "
    "(は, が, を…) aren't listed. Grammar detection can miss some points (about 1 in 10).":
        "行をクリックで文型をコピー · 行にカーソルを合わせると、その文型がある文を表示。"
        "基本の助詞（は・が・を…）は表示しません。文法の検出は一部を見落とすことがあります（約10分の1）。",
    "Paste some Japanese text first.": "まず日本語のテキストを貼り付けてください。",
    "No Japanese words found in this text.": "このテキストに日本語の語が見つかりません。",
    "Comfortable: you can read this and pick up the few new words from context.":
        "快適：読めます。わずかな新しい語は文脈から覚えられます。",
    "Good for immersion: some new words, but the story should carry you.":
        "多読に最適：新しい語はありますが、話の流れで読み進められます。",
    "Challenging: expect to look words up often.": "難しい：辞書を引く回数が多くなります。",
    "Hard: too many unknown words to follow without a dictionary.":
        "とても難しい：知らない語が多く、辞書なしでは追えません。",
    # Kanji → words window (2026-10-14)
    "<b>Words to learn with this kanji</b> — most common first":
        "<b>この漢字を使う、覚えるべき語</b> — よく使われる順",
    "Click a word to copy it · Shift+Click to open it on Jisho.org. "
    "Your cards: click to open the card in the Browser.":
        "語をクリックでコピー · Shift+クリックでJisho.orgを開く。"
        "あなたのカード：クリックでブラウザに表示。",
    "Search cards in Browser": "ブラウザでカードを検索",
    "Copy kanji": "漢字をコピー",
    "None yet.": "まだありません。",
    "None: you know every common word with this kanji.":
        "なし：この漢字を使うよく使われる語はすべて知っています。",
    # Nakama tab
    "Nakama 仲間": "仲間",
    "<span style='font-size:20px;'><b>Nakama 仲間</b></span>&nbsp;&nbsp;"
    "<span style='color:#9a9a9a;'>your friends' Kotodama bars, next to yours</span>":
        "<span style='font-size:20px;'><b>仲間</b></span>&nbsp;&nbsp;"
        "<span style='color:#9a9a9a;'>友達の言霊バーを、あなたのバーと並べて</span>",
    "<span style='font-size:18px;'><b>Nakama 仲間</b></span>":
        "<span style='font-size:18px;'><b>仲間</b></span>",
    "Join to get a friend code. Anyone you give it to can add you and see your card: "
    "your name and the numbers on your bars (rank, JLPT words, top 20k words, kanji and "
    "grammar). No cards, words or deck names are sent. Your card updates after Anki "
    "syncs. You can leave at any time: your card is removed, and your code is kept for you.":
        "参加するとフレンドコードがもらえます。コードを渡した人はあなたを追加して、"
        "あなたのカード（名前とバーの数字：ランク・JLPT語彙・上位2万語・漢字・文法）を見られます。"
        "カード・単語・デッキ名は送られません。カードはAnkiの同期後に更新されます。"
        "いつでも退会でき、カードは削除されますが、コードはあなたのために残ります。",
    "Join Nakama": "仲間に参加",
    "Leave Nakama": "仲間を退会",
    "Copy code": "コードをコピー",
    "Add friend": "友達を追加",
    "Sort by:": "並び順：",
    "Kotodama rank": "言霊ランク",
    "This week": "今週",
    "JLPT kanji": "JLPT漢字",
    "JLPT grammar": "JLPT文法",
    "Joining…": "参加中…",
    "Updating…": "更新中…",
    "Name saved.": "名前を保存しました。",
    "Saving your name…": "名前を保存中…",
    "<span style='color:#9a9a9a;'>Nobody uses this code (any more).</span>":
        "<span style='color:#9a9a9a;'>このコードは（もう）使われていません。</span>",
    "<span style='color:#9a9a9a;'>No card yet: press ⟳ Refresh.</span>":
        "<span style='color:#9a9a9a;'>カードはまだありません：⟳ 更新を押してください。</span>",
    "Type the name your friends will see first.": "まず友達に表示される名前を入力してください。",
    "Your bars aren't counted yet: wait for the count to finish.":
        "バーがまだ数えられていません：集計が終わるまでお待ちください。",
    "Give your code to a friend, and add theirs above to see their card here.":
        "コードを友達に渡し、友達のコードを上に追加すると、ここにカードが表示されます。",
    "A code is 8 letters and numbers, like ABCD-EFGH.": "コードは英数字8文字です（例：ABCD-EFGH）。",
    "That's your own code.": "それはあなた自身のコードです。",
    "Already in your Nakama.": "すでに仲間にいます。",
    "Your card, as your friends will see it:": "友達に表示されるあなたのカード：",
    # empty tables (owner 2026-10-18)
    "No words marked as found yet. Middle-click a tile in a word grid to count a word you "
    "know without a card.":
        "発見済みの単語はまだありません。単語グリッドのタイルを中クリックすると、"
        "カードがなくても知っている単語として数えられます。",
    "Nothing suspended. Ctrl+Middle-click a tile in a word grid to leave a word out of the lists.":
        "保留はありません。単語グリッドのタイルをCtrl+中クリックすると、その単語をリストから外せます。",
    "No missing words to show: they're all in your deck or marked found (or none match the filter).":
        "表示する未習得の単語はありません：すべてデッキにあるか発見済みです（または絞り込みに一致しません）。",
    "No kanji marked as found yet. Middle-click a tile in the grids to count one you know "
    "without a card.":
        "発見済みの漢字はまだありません。グリッドのタイルを中クリックすると、カードがなくても数えられます。",
    "No grammar points marked as found yet. Middle-click a tile in the grids to count one you "
    "know without a card.":
        "発見済みの文型はまだありません。グリッドのタイルを中クリックすると、カードがなくても数えられます。",
    "Nothing suspended. Ctrl+Middle-click a tile in the grids to leave one out of the counts.":
        "保留はありません。グリッドのタイルをCtrl+中クリックすると、数えないようにできます。",
    "Nothing missing to show (or nothing matches the filter).":
        "表示する未習得はありません（または絞り込みに一致しません）。",
    "Paste Japanese text above (or open a file) and press Check text: the words you don't know "
    "yet, most useful first, appear here.":
        "上に日本語のテキストを貼り付け（またはファイルを開き）、テキストチェックを押すと、"
        "まだ知らない単語が役立つ順にここに表示されます。",
    "Add a friend's code above to see their card here.":
        "上に友達のコードを追加すると、ここにカードが表示されます。",
    "<span style='color:#9a9a9a;'>Your card appears here once your bars are counted.</span>":
        "<span style='color:#9a9a9a;'>バーが数えられると、ここにあなたのカードが表示されます。</span>",
}

# Table column headers (separate: "Rank" is 順位 here, ランク elsewhere)
HEADERS = {
    "Level": "レベル", "Word": "単語", "Reading": "読み", "Rank": "順位",
    "Kanji": "漢字", "Pattern": "文型", "Meaning": "意味", "Formation": "接続",
    "On": "音読み", "Kun": "訓読み",
    "In text": "出現数", "Card": "カード",
    "Words in this text": "このテキストの語", "In this text": "このテキストでは",
}

# Placeholders (search boxes)
PLACEHOLDERS = {
    "Your name (shown on the image)": "名前（画像に表示）",
    "A message of your own…": "あなた自身のメッセージ…",
    "Filter words…": "単語を絞り込む…",
    "Filter…": "絞り込む…",
    "Search marked as found…": "発見済みを検索…",
    "Search suspended…": "保留を検索…",
    "Filter kanji, readings, meanings…": "漢字・読み・意味で絞り込む…",
    "Filter patterns, meanings…": "文型・意味で絞り込む…",
    "Find a word in this grid (kanji or kana)…": "このグリッドで単語を探す（漢字・かな）…",
    "Find a kanji, reading, meaning or word…": "漢字・読み・意味・単語を探す…",
    "Find a pattern, romaji or meaning…": "文型・ローマ字・意味を探す…",
    "Paste Japanese text here…": "ここに日本語のテキストを貼り付け…",
    "The name your friends see": "友達に表示される名前",
    "A friend's code (ABCD-EFGH)": "友達のコード（ABCD-EFGH）",
}

def _loyalty_ja(m) -> str:
    """"Jade · 6 months with Kotodama" → "翡翠 · 言霊と6か月" (loyalty.py)."""
    try:
        from . import loyalty
        names = {t[1]: t[2] for t in loyalty.TIERS}
    except Exception:
        names = {}
    num, unit = m.group(2), m.group(3)
    if unit.startswith("month"):
        dur = f"{num}か月"
    else:
        dur = f"{num[:-2]}年半" if num.endswith(".5") else f"{num}年"
    return f"{names.get(m.group(1), m.group(1))} · 言霊と{dur}"


_EN_MONTH_NUM = {m: i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July", "August", "September",
     "October", "November", "December"], 1)}
_DATE_RX = r"(?:January|February|March|April|May|June|July|August|September|October|November|December) \d+, \d{4}"


def _date_ja(text: str) -> str:
    """"December 6, 2026" → "2026年12月6日" (goal.fmt_date's English)."""
    m = re.fullmatch(r"(\w+) (\d+), (\d{4})", text.strip())
    if not m or m.group(1) not in _EN_MONTH_NUM:
        return text
    return f"{m.group(3)}年{_EN_MONTH_NUM[m.group(1)]}月{int(m.group(2))}日"


_GOAL_UNITS = {"word": "語", "words": "語", "kanji": "字", "grammar point": "文法", "grammar points": "文法"}
_GOAL_HEADS = {"Per day": "1日あたり", "Today": "今日", "Still to learn": "残り",
               "This week": "今週", "Learned": "習得済み", "Pace": "ペース", "Progress": "進み具合"}


def _goal_counts_ja(m) -> str:
    """"Per day: <b>14</b> words · <b>3</b> kanji" → "1日あたり：<b>14</b> 語 · <b>3</b> 字"."""
    body = re.sub(r"(</b>(?: / [\d,]+)?) (grammar points?|words?|kanji)\b",
                  lambda u: f"{u.group(1)} {_GOAL_UNITS[u.group(2)]}", m.group(2))
    # a weekly kind (under 1 a day, goal_view); daily ones say so when mixed ("Pace" / "Progress")
    body = body.replace(" a week", "（週あたり）").replace(" this week", "（今週）")
    body = body.replace(" a day", "（1日あたり）").replace(" today", "（今日）")
    return f"{_GOAL_HEADS[m.group(1)]}：{body}"


_PACE_NAMES = {"A gentle pace": "ゆったりペース", "A steady pace": "着実なペース",
               "An intense pace": "ハードなペース", "A sprint": "短距離走",
               "Not realistic for most people": "ほとんどの人には現実的ではありません"}
_PACE_NOTES = {
    "It fits around work or school.": "仕事や学校と両立できます。",
    "A common pace for serious learners.": "本気で学ぶ人によくあるペースです。",
    "Learners who keep this up for months usually call it their ceiling.":
        "何か月も続ける人の多くが、これを限界と言います。",
    "Most learners who try more than 40 new words a day burn out within weeks or months.":
        "1日40語を超えると、多くの人は数週間から数か月で燃え尽きます。",
    "Few learners keep this up even for a few weeks.": "数週間でも続けられる人はわずかです。",
}
_PACE_NAMES_LOWER = {k[0].lower() + k[1:]: v for k, v in _PACE_NAMES.items()}


def _pace_ja(m) -> str:
    """goal.pace's sentence: "A sprint: by November 22, 2026, about 430
    reviews and 85 new cards a day, 2–2.5 hours (10–12 seconds a review,
    30–45 seconds a new card). …"."""
    span = m.group(5) + (f"–{m.group(6)}" if m.group(6) else "")
    unit = "分" if m.group(7) == "minutes" else "時間"
    return (f"{_PACE_NAMES[m.group(1)]}：{_date_ja(m.group(2))}には1日に復習約 {m.group(3)} 回と"
            f"新しいカード {m.group(4)} 枚、{span}{unit}（復習1回10–12秒、新しいカード1枚30–45秒）。"
            f"{_PACE_NOTES[m.group(8)]}")


_REVIEW_KINDS = {"Words": "単語", "Kanji": "漢字", "Grammar": "文法", "word": "単語", "words": "単語",
                 "kanji": "漢字", "grammar point": "文法", "grammar points": "文法"}
_JA_WEEKDAYS = dict(zip(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], "月火水木金土日"))

PATTERNS = [
    # JLPT goal (goal_view.py)
    (re.compile(r"^(<b style='color:#\w+;'>JLPT N\d</b>) · (" + _DATE_RX + r") · <b>([\d,]+)</b> days? left to learn$"),
     lambda m: f"{m.group(1)} · {_date_ja(m.group(2))} · 学習期間 あと <b>{m.group(3)}</b> 日"),
    (re.compile(r"^(<b style='color:#\w+;'>JLPT N\d</b>) · (" + _DATE_RX + r") · <b>([\d,]+)</b> days? to the test$"),
     lambda m: f"{m.group(1)} · {_date_ja(m.group(2))} · 試験まで <b>{m.group(3)}</b> 日"),
    (re.compile(r"^Your JLPT (N\d) test was on (" + _DATE_RX + r")\. How did it go\?$"),
     lambda m: f"JLPT {m.group(1)} の試験（{_date_ja(m.group(2))}）はいかがでしたか？"),
    (re.compile(r"^Everything up to (N\d) is learned\. The rest is review\.$"),
     r"\1 までをすべて習得しました。あとは復習です。"),
    (re.compile(r"^(Per day|Today|Still to learn|This week|Learned|Pace|Progress): (.*)$", re.S), _goal_counts_ja),
    (re.compile(r"^Not included: ([\d,]+) English loanwords you marked found\. "
                r"They join on their own as your card count grows\.$"),
     r"含まれていないもの：発見済みにした英語の外来語 \1 語。カードが増えるにつれて自然に加わります。"),
    (re.compile(r"^You already know every word up to (N\d)\.$"), r"\1 までの単語はすべて知っています。"),
    (re.compile(r"^([\d,]+) words still to learn, and the test is less than (\d+) days away: "
                r"there's no time left before the finish line\.$"),
     r"残り \1 語。試験まで \2 日を切っていて、ゴールまでの時間がありません。"),
    (re.compile(r"^([\d,]+) words still to learn: about <b>([\d,]+)</b> a day until (" + _DATE_RX +
                r"), 14 days before the test\.(.*)$", re.S),
     lambda m: f"残り {m.group(1)} 語：{_date_ja(m.group(3))}（試験の14日前）まで1日約 <b>{m.group(2)}</b> 語。"
               + m.group(4)),
    (re.compile(r"(" + "|".join(_PACE_NAMES) + r"): by (" + _DATE_RX + r"), about ([\d,]+) reviews and "
                r"([\d,]+) new cards? a day, ([\d.]+)(?:–([\d.]+))? (minutes|hours) \(10–12 seconds a "
                r"review, 30–45 seconds a new card\)\. "
                r"(" + "|".join(re.escape(n) for n in _PACE_NOTES) + r")"),
     _pace_ja),
    (re.compile(r" ?For the (" + _DATE_RX + r") test instead: about ([\d,]+) a day \(("
                + "|".join(_PACE_NAMES_LOWER) + r")\)\."),
     lambda m: f"{_date_ja(m.group(1))}の試験にすれば：1日約 {m.group(2)} 語（{_PACE_NAMES_LOWER[m.group(3)]}）。"),
    (re.compile(r"^" + _DATE_RX + r"$"), lambda m: _date_ja(m.group(0))),          # the date list
    (re.compile(r"^Lists up to (N\d): (.+) / ([\d,]+)$"),
     r"\1 までのリスト：\2 / \3"),
    (re.compile(r"^Top-up to ([\d,]+) \(the modern estimate for (N\d)\): (.+) / ([\d,]+)$"),
     r"\1 語まで補う（\2の現代の推定）：\3 / \4"),
    (re.compile(r"^Top-up: the most common words from the harder levels\.$"), "補う語：上のレベルの頻出語。"),
    (re.compile(r"^Top-up: the most common words of written Japanese that aren't on the lists\.$"), "補う語：リストにない書き言葉の頻出語。"),
    (re.compile(r"<br>Lists: ([\d,]+) to go · top-up: ([\d,]+) to go\."),
     r"<br>リスト：残り \1 · 補う語：残り \2。"),
    (re.compile(r"Goal words \((N\d)\)"), r"目標の単語（\1）"),                      # History legend (N2 / N1 goal)
    # Progress Review (review_view.py, owner 2026-10-27)
    (re.compile(r"^(Words|Kanji|Grammar) · ([\d,]+)$"),
     lambda m: f"{_REVIEW_KINDS[m.group(1)]} · {m.group(2)}"),
    (re.compile(r"^Past ([\d,]+) days$"), r"過去\1日間"),
    (re.compile(r"^\+([\d,]+) (words?|kanji|grammar points?) outside your (N\d) goal$"),
     lambda m: f"{m.group(3)}目標外の{_REVIEW_KINDS[m.group(2)]} +{m.group(1)}"),
    (re.compile(r"^\+([\d,]+) (words?|kanji|grammar points?) on no JLPT list$"),
     lambda m: f"JLPTリスト外の{_REVIEW_KINDS[m.group(2)]} +{m.group(1)}"),
    (re.compile(r"^\+([\d,]+) words? today$"), r"今日 +\1 語"),
    (re.compile(r"^([\d,]+) words?$"), r"\1 語"),
    (re.compile(r"^([\d,]+) kanji$"), r"\1 字"),
    (re.compile(r"^([\d,]+) grammar$"), r"文法 \1"),
    (re.compile(r"^Needed in ([\d,]+) days: (.+)$"),
     lambda m: f"{m.group(1)}日で必要な量：" + " · ".join(
         re.sub(r"^([\d,]+) (words|kanji|grammar)$",
                lambda p: f"{p.group(1)} {'語' if p.group(2) == 'words' else '字'}"
                if p.group(2) != "grammar" else f"文法 {p.group(1)}", part)
         for part in m.group(2).split(" · "))),
    (re.compile(r"^(Mon|Tue|Wed|Thu|Fri|Sat|Sun) (\d+)$"),
     lambda m: f"{m.group(2)}日（{_JA_WEEKDAYS[m.group(1)]}）"),
    (re.compile(r"^(Mon|Tue|Wed|Thu|Fri|Sat|Sun)$"), lambda m: _JA_WEEKDAYS[m.group(1)]),
    (re.compile(r"Top ([\d,]+) words"), r"上位 \1 語"),
    (re.compile(r"Most Common Words — Top ([\d,]+)$"), r"最頻出語 — 上位 \1"),
    (re.compile(r"\bTop ([\d,]+)\b"), r"上位 \1"),                                 # "Top 3,900" (History legend, grid headers)
    (re.compile(r"Words up to (N\d)"), r"\1 までの単語"),                          # History legend
    (re.compile(r"On track"), "予定ライン"),
    (re.compile(r"^(\w+(?: \w+)?) · ([\d.]+) (months?|years?) with Kotodama$"), _loyalty_ja),
    (re.compile(r"^Your code: (<b[^>]*>[^<]*</b>)$"), r"あなたのコード：\1"),
    (re.compile(r"^Welcome back: you'll keep your code (\S+)\.$"), r"おかえりなさい：コード \1 はそのまま使えます。"),
    (re.compile(r"^Decks?: "), "デッキ："),
    (re.compile(r"<b>([\d.,]+)%</b> of the words in this text are known"),
     r"このテキストの語の <b>\1%</b> を知っています"),
    (re.compile(r"([\d,]+) words: ([\d,]+) known · ([\d,]+) unknown · ([\d,]+) not on our lists "
                r"\(names, rare words\) · different words: ([\d,]+) of ([\d,]+) known"),
     r"\1 語：既知 \2 · 未知 \3 · リスト外 \4（人名・まれな語） · 異なり語数：\6 語中 \5 語が既知"),
    (re.compile(r"<b>Not on our lists</b> \(names, rare words, or text the parser can't read\): "),
     "<b>リスト外</b>（人名・まれな語・解析できない部分）："),
    (re.compile(r"<b>Your cards with this kanji</b> \(([\d,]+)\)"),
     r"<b>この漢字を使うあなたのカード</b> (\1)"),
    (re.compile(r"^Words with (\S+)$"), r"「\1」を使う語"),
    (re.compile(r"\(\+([\d,]+) more\)$"), r"（ほか \1）"),
    (re.compile(r"JLPT Vocabulary Coverage"), "JLPT語彙カバー率"),
    (re.compile(r"Marked && Suspended"), "発見済み && 保留"),
    (re.compile(r"Off-list \(([\d,]+)\)"), r"リスト外 (\1)"),
    (re.compile(r"<b>([+−][\d,]+)</b> learned this week"), r"今週 <b>\1</b> 語を習得"),
    (re.compile(r"learned this week"), "今週の習得"),
    (re.compile(r"</span> today</a>"), "</span> 今日</a>"),       # delta_html's "+N today"
    (re.compile(r"this month"), "今月"),
    (re.compile(r"this week"), "今週"),
    (re.compile(r"^History starts (\S+) \(([\d,]+) days\)\. This year = since January 1\.$"),
     r"履歴の開始：\1（\2 日間）。今年＝1月1日から。"),
    (re.compile(r"^How many of the 20,000 most common words.*", re.S),
     "書き言葉で最もよく使われる20,000語のうち、あなたのデッキがどれだけをカバーしているか"
     "（ネイティブに近い読み手の語彙量）。下のバーは上位6,000・13,800語："
     "その語数はN2・N1に必要な語彙量の現代の推定に合わせていますが、"
     "語そのものは書き言葉の最頻出語で、試験の語ではありません。試験の語は上のJLPT語彙バーで。"
     "N3まではそれが目安です。書き言葉はN2から重要になり、N2・N1の読解は新聞のような記事や評論です："
     "N1のJLPT目標は、2段階目をこれらのバーから埋めます。上位13,800は上位6,000を含みます。"
     "ランクは覚えた語数を、ここではそれが大切な語かどうかを示します。"),
    (re.compile(r"<b>([\d,]+)</b> known = ([\d,]+) from your cards \+ ([\d,]+) marked found"
                r" &nbsp;·&nbsp; <b>([\d,]+)</b> of your ([\d,]+) cards match a top-([\d,]+) "
                r"word &nbsp;·&nbsp; known words cover <b>≈([\d.]+)%</b> of everyday "
                r"written text"),
     r"既知 <b>\1</b> 語 = カードから \2 + 発見済み \3 &nbsp;·&nbsp; カード \5 枚のうち "
     r"<b>\4</b> 枚が上位 \6 語に該当 &nbsp;·&nbsp; 日常の書き言葉の <b>≈\7%</b> をカバー"),
    # split_html: the JLPT, frequency and rank "made of" lines (one form, 2026-10-22)
    (re.compile(r"<b>([\d,]+)</b> counted = ([\d,]+) from your cards \+ ([\d,]+) English loanwords"
                r" \+ ([\d,]+) marked found"),
     r"ランク <b>\1</b> 語 = カードから \2 + 英語の外来語 \3 + 発見済み \4"),
    (re.compile(r"<b>([\d,]+)</b> counted = ([\d,]+) from your cards \+ ([\d,]+) marked found"),
     r"ランク <b>\1</b> 語 = カードから \2 + 発見済み \3"),
    (re.compile(r"<b>([\d,]+)</b> known = ([\d,]+) from your cards \+ ([\d,]+) English loanwords"
                r" \+ ([\d,]+) marked found"),
     r"既知 <b>\1</b> 語 = カードから \2 + 英語の外来語 \3 + 発見済み \4"),
    (re.compile(r"<b>([\d,]+)</b> known = ([\d,]+) from your cards \+ ([\d,]+) marked found"),
     r"既知 <b>\1</b> 語 = カードから \2 + 発見済み \3"),
    (re.compile(r"^Near Native<br>"), "ネイティブ級<br>"),
    (re.compile(r"^Top<br>"), "上位<br>"),             # frequency bar labels (named by size, 2026-10-20)
    (re.compile(r"\b(N\d) size\b"), r"\1 相当"),
    (re.compile(r"Kanji: <b>(\d+)%</b> known \(([\d,]+) of ([\d,]+) not known yet\)"),
     r"漢字：<b>\1%</b> を知っています（\3 字中 \2 字は未知）"),
    (re.compile(r"Kanji: ([\d,]+) different"), r"漢字：\1 種類"),
    (re.compile(r"Grammar: ([\d,]+) points, <b>([\d,]+)</b> not learned yet"),
     r"文法：\1 項目、未習得 <b>\2</b>"),
    (re.compile(r"Grammar: ([\d,]+) points found"), r"文法：\1 項目"),
    (re.compile(r"^(<b style='[^']*'>[\d,]+%</b>) of your learned words are among the 20,000 most common in "
                r"written Japanese &nbsp;·&nbsp; ([\d,]+) are outside it \(names, slang, words newer than "
                r"the corpus like スマホ, genre words, other spellings\)$"),
     r"覚えた語の \1 が書き言葉の最頻出20,000語に入っています &nbsp;·&nbsp; 入らないのは \2 語"
     r"（人名・俗語・スマホのようにコーパスより新しい語・ジャンルの語・別表記）"),
    (re.compile(r"common words you know &nbsp;&nbsp; (<span[^>]*>■</span>) your rank: ([\d,]+) words learned"),
     r"知っている最頻出語 &nbsp;&nbsp; \1 ランク：覚えた語 \2"),     # frequency bar captions ("Top 6,000" itself: the Top pattern)
    (re.compile(r"<b>Most common words not in your deck</b>"), "<b>デッキにないよく使われる語</b>"),
    (re.compile(r"— click to copy · Shift\+Click to look up on Jisho"),
     "— クリックでコピー · Shift+クリックでJisho"),
    (re.compile(r"([\d,]+) more kanji in your cards aren't on any JLPT level; they're at "
                r"the end of the All Kanji grid\."),
     r"カードにはJLPTのどのレベルにもない漢字があと \1 字あります（全漢字グリッドの最後）。"),
    (re.compile(r"(N\d|All levels)\s+\(([\d,]+) missing\)"),
     lambda m: f"{'全レベル' if m.group(1) == 'All levels' else m.group(1)}（未習得 {m.group(2)}）"),
    (re.compile(r"([\d,]+) / ([\d,]+) known across all levels"), r"全レベルで \1 / \2 語が既知"),
    (re.compile(r"([\d,]+) / ([\d,]+) known"), r"\1 / \2 既知"),
    (re.compile(r"([\d,]+) missing"), r"未習得 \1"),
    (re.compile(r"★ Mark English Loanwords as Found \(([\d,]+)\)"),
     r"★ 英語の外来語を発見済みにする (\1)"),
    (re.compile(r"✓ Unmark English Loanwords \(([\d,]+)\)"), r"✓ 英語の外来語を元に戻す (\1)"),
    # rank info ("?") window
    (re.compile(r"Starts at <b>([\d,]+) cards</b>  ·  ([\d,]+) – ([\d,]+) cards"),
     r"開始 <b>\1 枚</b>  ·  \2 – \3 枚"),
    # kanji / grammar grids
    (re.compile(r"^Kanji source: (.+?)\. Colour = how well you know it: .*", re.S),
     lambda m: f"漢字の出典：{m.group(1)}。色＝覚えている度合い（その漢字を含む学習済み"
               "カードの平均の強さ。FSRSの安定度・難易度・忘却回数から）。既知の漢字が先"
               "（強い順、★ 発見済みは最後）、次にまだ習得していないカードにだけある漢字"
               "（点線の枠）、未学習の漢字がその後。ホバー：意味・読み・"
               "あなたのカード · Shift+クリック：Jisho · 中クリック：発見済みにする · "
               "Ctrl+中クリック：保留。"),
    (re.compile(r"^Grammar source: (.+?)\. Colour = how well you know it .*", re.S),
     lambda m: f"文法の出典：{m.group(1)}。色＝覚えている度合い（習得したカードの平均の強さ）。"
               "習得した文型が先（強い順、★ 発見済みは最後）、残りはOpenJLPTの順。"
               "ホバー：意味・接続・例文 · クリック：デッキ内を検索 · Shift+クリック：ウェブ検索 · "
               "中クリック：発見済みにする"
               " · Ctrl+中クリック：保留。"),
    (re.compile(r">(N\d) Kanji<"), r">\1 漢字<"),
    (re.compile(r">(N\d) Grammar<"), r">\1 文法<"),
    (re.compile(r">Off-list Kanji<"), ">リスト外の漢字<"),
    (re.compile(r"([\d,]+) kanji in your cards that aren't on any JLPT level "
                r"\(not counted in the bars\)"),
     r"カードにあるJLPT外の漢字 \1 字（バーには数えない）"),
    (re.compile(r"([\d,]+) unseen"), r"未学習 \1"),
    (re.compile(r"([\d,]+) not learned"), r"未習得 \1"),
    (re.compile(r"([\d,]+) suspended"), r"保留 \1"),
    (re.compile(r"^<b>Why are some obvious points here\?</b>.*", re.S),
     "<b>当たり前の文型がここにあるのはなぜ？</b> に・で・が のような短い形には意味がいくつもあり、"
     "OpenJLPTでは別々の項目です（に：時間・目的地・場所・相手・頻度）。文からはどれか判別"
     "できないことがあるので、はっきりした場合だけ検出します（3時に → 時間、学校に行く → "
     "目的地）。知っているものは ★ 発見済み で登録できます。"),
    (re.compile(r"^Mark (kanji|grammar points) found or suspended with middle-click / "
                r"Ctrl\+middle-click in the grids \(Kanji & Grammar tab\)\. Press Refresh to "
                r"update the bars\."),
     lambda m: f"{'漢字' if m.group(1) == 'kanji' else '文法'}はグリッド（漢字 & 文法タブ）で"
               "中クリック／Ctrl+中クリックすると発見済み・保留にできます。更新でバーに反映されます。"),
    # Off-list tab
    (re.compile(r"^<b>Off-list words</b> — ([\d,]+) cards in your deck aren't on the Kotodama "
                r"JLPT lists\..*?([\d,]+) of them are among the ([\d,]+) most common words.*", re.S),
     r"<b>リスト外の単語</b> — デッキの \1 枚のカードは言霊のJLPTリストにありません。"
     r"リストには試験に最も出やすい語が入っていますが、上のレベルではどのリストよりも多くの語が"
     r"求められるので、これらの多くも試験に出ることがあります。そのうち \2 枚は最頻出 \3 語に"
     r"入り、すべてランクと頻度チェックに数えられます。<br><span style='color:#aaa; font-size:11px;'>"
     r"タイルは 成熟 → 若い の順、各グループ内はよく使われる順。リストはよく使われる"
     r"順です（≈ は頻度リストで分割される複合語の推定順位、例：日本語）。仕切りをドラッグして"
     r"大きさを変えられます。タイルをクリック（または行をダブルクリック）するとブラウザで開きます。"
     r"これらは発見済み・保留にはできません。</span>"),
    (re.compile(r"^(<span[^>]*>)⧉ Words with more than one card: ([\d,]+) — "
                r"<a href='dups'>see the list</a></span>$"),
     r"\1⧉ 複数のカードがある単語：\2 — <a href='dups'>一覧を見る</a></span>"),
    # History: dates in Japanese
    (re.compile(r"Last snapshot: (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) (\d+), "
                r"(\d+:\d+) \((manual|automatic)\)"),
     lambda m: f"最終記録：{_MONTHS[m.group(1)]}月{m.group(2)}日 {m.group(3)}"
               f"（{'手動' if m.group(4) == 'manual' else '自動'}）"),
    (re.compile(r"^Match (\d+) / (\d+): "), r"一致 \1 / \2：　"),
    (re.compile(r"^([\d,]+) matches — first: "), r"\1 件一致 — 最初：　"),
    (re.compile(r"  —  rank (≈?#[\d,]+)  —  "), r"  —  順位 \1  —  "),
    (re.compile(r"  —  Off-list  —  "), "  —  リスト外  —  "),
    (re.compile(r"✓ Known — in your deck$"), "✓ 既知 — デッキにあり"),
    (re.compile(r"★ Marked as found$"), "★ 発見済み"),
    (re.compile(r"★ Marked as found, counted now"), "★ 発見済み（もう数えています）"),
    (re.compile(r"★ Marked as found, not counted yet$"), "★ 発見済み（まだ数えていません）"),
    (re.compile(r"★ Marked as found, not counted yet: English loanwords count once your "
                r"rank reaches their frequency rank"),
     "★ 発見済み（まだ数えていません）：英語の外来語は、ランクがその頻度順位に達すると数えられます"),
    (re.compile(r"  —  Missing$"), "  —  未習得"),
    (re.compile(r"overrides\.json location: "), "overrides.json の場所："),
    (re.compile(r"Showing ([\d,]+) of ([\d,]+) found words"), r"発見済み \2 語中 \1 語を表示"),
    (re.compile(r"([\d,]+) found words"), r"発見済み \1 語"),
    (re.compile(r"Known \(([\d,]+)\) — click to open in browser"),
     r"既知（\1）— クリックでブラウザを開く"),
    (re.compile(r"Missing \(([\d,]+)\) — click to copy"), r"未習得（\1）— クリックでコピー"),
]

# Pieces, replaced inside longer texts (longest first).
PHRASES = sorted([
    ("Known words are shown level by level; within each level they're grouped",
     "既知の単語はレベルごとに表示し、各レベル内で"),
    ("Known words first, grouped", "既知の単語を先に、"),
    ("Known words are grouped", "既知の単語は"),
    ("(★ marked found last), most common first in each group. ",
     "の順（★ 発見済みは最後）、各グループ内はよく使われる順。"),
    ("(★ marked found last), most common first in each group; ",
     "の順（★ 発見済みは最後）、各グループ内はよく使われる順。"),
    ("(★ marked found last), ", "の順（★ 発見済みは最後）、"),
    ("(★ marked found last)", "の順（★ 発見済みは最後）"),
    ("most common first in each group", "各グループ内はよく使われる順"),
    ("then missing words in frequency order", "その後に未習得の単語を頻度順"),
    ("Missing words follow.", "その後に未習得の単語。"),
    ("In your deck — click to open in browser", "デッキにあり — クリックでブラウザを開く"),
    ("Missing — click to copy", "未習得 — クリックでコピー"),
    ("Hover: meaning and rank", "ホバー：意味と順位"),
    ("Hover: meaning", "ホバー：意味"),
    ("Shift+Click: Jisho", "Shift+クリック：Jisho"),
    ("Ctrl+Middle-click: suspend (left out of the counts).", "Ctrl+中クリック：保留（数えない）。"),
    ("Ctrl+Middle-click: suspend (exclude from list)", "Ctrl+中クリック：保留（リストから除外）"),
    ("Middle-click: mark as found", "中クリック：発見済みにする"),
    ("Marks are shared with the JLPT lists; Refresh updates the bars.",
     "マークはJLPTリストと共有されます。更新でバーに反映されます。"),
    ("then missing words in frequency order.", "その後に未習得の単語を頻度順に。"),
    ("Marked as Found", "発見済み"),
    ("(excluded from lists)", "（リストから除外）"),
    ("Known tiles get more vivid as cards mature:", "既知のタイルはカードが成熟するほど濃くなります："),
    ("Known tiles by card maturity:", "成熟度別の既知タイル："),
    ("Off-list tiles by card maturity:", "成熟度別のリスト外タイル："),
    ("Mature → Young", "成熟 → 若い"),
    ("New words (dashed: in your deck, not studied yet), then marked English loanwords not counted yet (faint ★), then missing words, follow.",
     "次に新規の単語（点線：デッキにあり・未学習）、まだ数えていない発見済みの英語外来語（薄い★）、その後に未習得の単語。"),
    ("then new words (dashed), marked English loanwords not counted yet (faint ★) and missing words in frequency order.",
     "その後に新規（点線）、まだ数えていない発見済みの英語外来語（薄い★）、未習得の単語を頻度順に。"),
    ("New (in your deck, not studied yet)", "新規（デッキにあり・未学習）"),
    ("Learning", "学習中"),
    ("Young", "若い"),
    ("Mature", "成熟"),
    ("Learned (rank)", "習得（ランク）"),
    ("JLPT Words", "JLPT語彙"),
    ("JLPT Kanji", "JLPT漢字"),
    ("JLPT Grammar", "JLPT文法"),
    ("Near Native (20,000)", "ネイティブ級 (20,000)"),
    ("All JLPT levels", "全JLPTレベル"),
    ("Near Native", "ネイティブ級"),
    ("Missing JLPT", "未習得のJLPT語"),
    ("Marked found", "発見済み"),
    ("★ Marked found", "★ 発見済み"),
    ("✕ Suspended", "✕ 保留"),
    ("Suspended", "保留"),
    ("All Kanji", "全漢字"),
    ("All Grammar", "全文法"),
    ("<b>Kanji</b>", "<b>漢字</b>"),
    ("<b>Grammar</b>", "<b>文法</b>"),
    ("<b>JLPT Kanji</b>", "<b>JLPT 漢字</b>"),
    ("<b>JLPT Grammar</b>", "<b>JLPT 文法</b>"),
    ("from your vocab words:", "単語から："),
    ("from your sentence fields:", "例文フィールドから："),
    ("from a field:", "フィールドから："),
    ("parser · sentence fields:", "解析 · 例文フィールド："),
    ("sentence cards:", "例文カード："),
    ("none set", "未設定"),
    ("Unseen (no learned card)", "未学習（習得済みカードなし）"),
    ("Unseen", "未学習"),
    ("Not learned", "未習得"),
    ("In your deck, not learned yet", "デッキにあり・まだ未習得"),   # grammar tile (search status)
    ("In your deck, not learned", "デッキにあり・未習得"),          # grammar legend
    ("Weak", "弱"),
    ("Strong", "強"),
    ("Up to ", ""),     # "Up to N3 (3,900)" → "N3 (3,900)" (history legend)
], key=lambda kv: -len(kv[0]))

_GRAYS = re.compile(r"color:\s*(gray|grey|#aaa|#aaaaaa|#888|#888888|#999|#999999|#777|#777777|"
                    r"#ccc|#cccccc|#9a9a9a)\b", re.I)


def translate(text: str) -> str:
    """Japanese for a UI text, or the text unchanged if it isn't known."""
    if not text:
        return text
    key = " ".join(text.split())
    if key in EXACT:
        return EXACT[key]
    out = text
    for rx, rep in PATTERNS:
        out = rx.sub(rep, out)
    for en, ja in PHRASES:
        if en in out:
            out = out.replace(en, ja)
    return out


def _gold_ss(ss: str, cls: str) -> str:
    """Add gold text (and, for buttons, a gold focus border instead of blue)
    to a widget's style sheet — once, however often it's re-applied."""
    if GOLD in (ss or ""):
        return ss
    focus = (f" {cls}:focus, {cls}:default {{ border-color: {GOLD}; }}"
             if cls in ("QPushButton", "QToolButton") else "")
    if "{" in (ss or ""):
        return ss + f" {cls} {{ color: {GOLD}; }}" + focus
    if focus:
        # plain declarations → wrap them, so a :focus rule can sit beside
        decl = (ss or "").strip()
        if decl and not decl.endswith(";"):
            decl += ";"
        return f"{cls} {{ {decl} color: {GOLD}; }}" + focus
    return (ss + ";" if ss and not ss.rstrip().endswith(";") else ss) + f" color: {GOLD};"


# Inline colours left as they are in gold mode: the ✕ red, the ★ yellow and
# the dark "missing" square. Everything else (level colours, the frequency
# blue, grays) turns gold.
_KEEP_COLORS = {"#e05a5a", "#ffe066", "#555", "#555555", "#8b2020"}
_HEX = re.compile(r"color:\s*(#[0-9a-fA-F]{3,6})\b")


def _recolor(html: str) -> str:
    html = _GRAYS.sub(f"color:{GOLD}", html)
    return _HEX.sub(lambda m: m.group(0) if m.group(1).lower() in _KEEP_COLORS
                    else f"color:{GOLD}", html)


def _set(w: QWidget, on: bool, get, put, cls: str, transform=translate):
    """Swap one widget's text: remember the English (and stylesheet) the
    first time, restore it when gold mode ends — unless the text was
    changed since (then the new English is already there)."""
    cur = get()
    if on:
        if w.property("jlpt_ja") == cur:
            return                                  # already done
        ja = transform(cur)
        if ja == cur:
            return
        w.setProperty("jlpt_en", cur)
        w.setProperty("jlpt_ss", w.styleSheet())
        put(ja)
        w.setProperty("jlpt_ja", get())            # as shown (grays turned gold)
        if not w.property("jlpt_keep_color"):      # (the badge's own dark gold)
            w.setStyleSheet(_gold_ss(w.styleSheet(), cls))
    else:
        en = w.property("jlpt_en")
        if en is None:
            return
        if w.property("jlpt_ja") == cur:
            put(en)
        w.setStyleSheet(w.property("jlpt_ss") or "")
        for k in ("jlpt_en", "jlpt_ja", "jlpt_ss"):
            w.setProperty(k, None)


def apply(root: QWidget, on: bool):
    """Gold Japanese on (or English back) for every widget under root."""
    for w in [root] + root.findChildren(QWidget):
        try:
            if w.property("jlpt_gold_skip"):        # e.g. the invisible debug switch
                continue
            if isinstance(w, QLabel):
                keep = bool(w.property("jlpt_keep_color"))
                heat = w.property("jlpt_heat_legend")
                matur = w.property("jlpt_maturity_legend")
                if heat is not None:
                    # Kanji/grammar strength legend: the ramp for the mode
                    # (heat_color follows gold mode), translated.
                    from .kanji_view import _heat_legend_html
                    tf = lambda t, h=heat: _GRAYS.sub(f"color:{GOLD}", translate(_heat_legend_html(h)))
                elif matur is not None:
                    # Word maturity legend: the gold tiles' three depths.
                    from .progress_dialog import _maturity_legend_html
                    tf = lambda t, m=matur: _GRAYS.sub(
                        f"color:{GOLD}", translate(_maturity_legend_html(m or None, gold=True)))
                elif keep:
                    tf = translate
                else:
                    tf = lambda t: _recolor(translate(t))
                _set(w, on, w.text, w.setText, "QLabel", tf)
                if not on and heat is not None:
                    from .kanji_view import _heat_legend_html
                    w.setText(_heat_legend_html(heat))      # back to the heat ramp
            elif isinstance(w, QAbstractButton):
                _set(w, on, w.text, w.setText, type(w).__name__)
            elif w.property("jlpt_gold_list"):
                # The frequency "missing words" chips: gold, like the tiles.
                if on and w.property("jlpt_list_ss") is None:
                    w.setProperty("jlpt_list_ss", w.styleSheet())
                    w.setStyleSheet(LIST_SS)
                elif not on and w.property("jlpt_list_ss") is not None:
                    w.setStyleSheet(w.property("jlpt_list_ss"))
                    w.setProperty("jlpt_list_ss", None)
            elif isinstance(w, QComboBox):
                _gold_combo(w, on)            # gold text and drop-down list
                orig = w.property("jlpt_items")
                if on and orig is None:
                    items = [w.itemText(i) for i in range(w.count())]
                    ja = [translate(t) for t in items]
                    if ja != items:
                        w.setProperty("jlpt_items", items)
                        for i, t in enumerate(ja):
                            w.setItemText(i, t)
                elif not on and orig is not None:
                    if len(orig) == w.count():
                        for i, t in enumerate(orig):
                            w.setItemText(i, t)
                    w.setProperty("jlpt_items", None)
            elif isinstance(w, (QLineEdit, QPlainTextEdit, QTextEdit)):
                # gold text and a gold focus border instead of blue
                if on and w.property("jlpt_edit_ss") is None:
                    from aqt.qt import QPalette
                    w.setProperty("jlpt_edit_ss", w.styleSheet())
                    w._jlpt_pal = QPalette(w.palette())
                    w.setStyleSheet((w.styleSheet() or "") + " " + EDIT_SS)
                    w.setPalette(_gold_pal(w._jlpt_pal))
                elif not on and w.property("jlpt_edit_ss") is not None:
                    w.setStyleSheet(w.property("jlpt_edit_ss"))
                    if getattr(w, "_jlpt_pal", None) is not None:
                        w.setPalette(w._jlpt_pal)
                    w.setProperty("jlpt_edit_ss", None)
                ph = w.placeholderText()
                if on and ph in PLACEHOLDERS:
                    w.setProperty("jlpt_ph", ph)
                    w.setPlaceholderText(PLACEHOLDERS[ph])
                elif not on and w.property("jlpt_ph") is not None:
                    w.setPlaceholderText(w.property("jlpt_ph"))
                    w.setProperty("jlpt_ph", None)
            elif isinstance(w, QTableWidget):
                _apply_table(w, on)
            if isinstance(w, QTabWidget):
                apply_tabs(w, on)
        except RuntimeError:
            continue          # a widget deleted mid-walk


_ORIG_ROLE = Qt.ItemDataRole.UserRole + 50     # a table item's colour before gold
TABLE_SS = (f"QTableWidget {{ color: {GOLD}; }}"
            f" QHeaderView::section {{ color: {GOLD}; }}")


def tint_item(item, on: bool):
    """A table cell's own colour (level, rank …) → gold, or back. The
    original is kept on the item, so it survives until the table refills."""
    if item is None:
        return
    if on:
        if item.data(_ORIG_ROLE) is not None:
            return
        fg = item.foreground()
        if fg.style() == Qt.BrushStyle.NoBrush:
            return
        name = fg.color().name()
        if name.lower() in _KEEP_COLORS:
            return
        item.setData(_ORIG_ROLE, name)
        item.setForeground(QColor(GOLD))
    else:
        orig = item.data(_ORIG_ROLE)
        if orig is not None:
            item.setForeground(QColor(orig))
            item.setData(_ORIG_ROLE, None)


def _apply_table(t: QTableWidget, on: bool):
    # gold text and headers
    if on and t.property("jlpt_tbl_ss") is None:
        t.setProperty("jlpt_tbl_ss", t.styleSheet())
        t.setStyleSheet((t.styleSheet() or "") + " " + TABLE_SS)
    elif not on and t.property("jlpt_tbl_ss") is not None:
        t.setStyleSheet(t.property("jlpt_tbl_ss"))
        t.setProperty("jlpt_tbl_ss", None)
    # header labels
    for c in range(t.columnCount()):
        h = t.horizontalHeaderItem(c)
        if h is None:
            continue
        if on and h.data(_ORIG_ROLE) is None and h.text() in HEADERS:
            h.setData(_ORIG_ROLE, h.text())
            h.setText(HEADERS[h.text()])
        elif not on and h.data(_ORIG_ROLE) is not None:
            h.setText(h.data(_ORIG_ROLE))
            h.setData(_ORIG_ROLE, None)
    # cells with their own colour
    for r in range(t.rowCount()):
        for c in range(t.columnCount()):
            tint_item(t.item(r, c), on)


def gold_tooltip(w: QWidget, on: bool):
    """Tile tooltips in gold mode: gold text on near-black, colours turned
    gold (level name, part of speech, hints). Called on hover, so it always
    reflects the current tooltip and mode."""
    cur = w.toolTip()
    if on:
        if w.property("jlpt_tip_gold") == cur:
            return
        w.setProperty("jlpt_tip_src", cur)
        gold = _recolor(cur)
        w.setToolTip(gold)
        w.setProperty("jlpt_tip_gold", gold)
        if w.property("jlpt_tip_ss") is None:
            w.setProperty("jlpt_tip_ss", w.styleSheet())
            w.setStyleSheet((w.styleSheet() or "") +
                            f" QToolTip {{ color: {GOLD}; background-color: #14110a;"
                            f" border: 1px solid {GOLD}; }}")
    elif w.property("jlpt_tip_gold") is not None:
        if w.property("jlpt_tip_gold") == cur:
            w.setToolTip(w.property("jlpt_tip_src") or "")
        w.setStyleSheet(w.property("jlpt_tip_ss") or "")
        for k in ("jlpt_tip_src", "jlpt_tip_gold", "jlpt_tip_ss"):
            w.setProperty(k, None)


def gold_titlebar(window: QWidget, on: bool, _tries: int = 0):
    """Windows 11: gold title bar with dark text and a gold border (DWM
    caption / text / border colour attributes), or the system default
    back. Silently does nothing elsewhere or on older Windows.

    Windows only takes the colour once the window is on screen (set any
    earlier, it was ignored — the "?" window stayed red), so until then this
    retries every 50 ms (up to 2 s)."""
    import sys
    if sys.platform != "win32":
        return
    try:
        if not window.isVisible():
            if _tries < 40:
                from aqt.qt import QTimer
                QTimer.singleShot(50, lambda: gold_titlebar(window, on, _tries + 1))
            return
    except RuntimeError:
        return                                   # window closed meanwhile
    try:
        import ctypes
        from ctypes import wintypes
        hwnd = wintypes.HWND(int(window.winId()))
        DEFAULT = 0xFFFFFFFF
        def colorref(h):                     # "#rrggbb" → 0x00BBGGRR
            r, g, b = int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)
            return (b << 16) | (g << 8) | r
        for attr, value in ((34, colorref("#f5c518")),      # DWMWA_BORDER_COLOR
                            (35, colorref("#f5c518")),      # DWMWA_CAPTION_COLOR
                            (36, colorref("#14110a"))):     # DWMWA_TEXT_COLOR
            v = ctypes.c_uint(value if on else DEFAULT)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(v),
                                                      ctypes.sizeof(v))
    except Exception:
        pass


def gold_palette(window: QWidget, on: bool):
    """Selection highlights and focus rings (blue by default) → gold, or
    back. The original palette is kept on the window."""
    from aqt.qt import QPalette
    if on:
        if getattr(window, "_jlpt_palette", None) is None:
            window._jlpt_palette = QPalette(window.palette())
        pal = QPalette(window._jlpt_palette)
        pal.setColor(QPalette.ColorRole.Highlight, QColor(GOLD))
        pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#14110a"))
        window.setPalette(pal)
    elif getattr(window, "_jlpt_palette", None) is not None:
        window.setPalette(window._jlpt_palette)
        window._jlpt_palette = None


COMBO_SS = (f"QComboBox {{ color: {GOLD}; border-color: #6b5a1a; }}"
            f" QComboBox:focus, QComboBox:on {{ border-color: {GOLD}; }}"
            f" QComboBox QAbstractItemView {{ color: {GOLD}; background-color: #14110a;"
            f" selection-background-color: {GOLD}; selection-color: #14110a; }}")
VIEW_SS = (f"QAbstractItemView {{ color: {GOLD}; background-color: #14110a;"
           f" selection-background-color: {GOLD}; selection-color: #14110a;"
           f" border: 1px solid #6b5a1a; }}"
           f" QAbstractItemView::item:hover {{ background-color: #3a3114; color: {GOLD}; }}"
           f" QAbstractItemView::item:selected {{ background-color: {GOLD}; color: #14110a; }}")
EDIT_SS = (f"QLineEdit, QPlainTextEdit, QTextEdit {{ color: {GOLD}; border-color: #6b5a1a; }}"
           f" QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus {{ border-color: {GOLD}; }}")


def _gold_pal(base):
    """A copy of a palette with gold text and gold selection."""
    from aqt.qt import QPalette
    pal = QPalette(base)
    for role in (QPalette.ColorRole.Text, QPalette.ColorRole.ButtonText,
                 QPalette.ColorRole.WindowText):
        pal.setColor(role, QColor(GOLD))
    pal.setColor(QPalette.ColorRole.Highlight, QColor(GOLD))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#14110a"))
    return pal


def _gold_combo(w: QComboBox, on: bool):
    """Gold closed box and drop-down list. Anki's theme styles combo boxes
    and their pop-ups, so the gold goes on three ways at once: a style sheet
    on the box, one directly on its list view, and palettes on the box, the
    view and the pop-up window."""
    from aqt.qt import QPalette
    view = w.view()
    popup = view.window() if view is not None else None
    if on and w.property("jlpt_combo_ss") is None:
        w.setProperty("jlpt_combo_ss", w.styleSheet())
        w._jlpt_pals = [(x, QPalette(x.palette()), x.styleSheet())
                        for x in (w, view, popup) if x is not None]
        w.setStyleSheet((w.styleSheet() or "") + " " + COMBO_SS)
        for x, pal, _ss in w._jlpt_pals:
            x.setPalette(_gold_pal(pal))
        if view is not None:
            view.setStyleSheet((view.styleSheet() or "") + " " + VIEW_SS)
    elif not on and w.property("jlpt_combo_ss") is not None:
        w.setStyleSheet(w.property("jlpt_combo_ss"))
        for x, pal, ss in getattr(w, "_jlpt_pals", []):
            x.setPalette(pal)
            if x is not w:
                x.setStyleSheet(ss)
        w._jlpt_pals = []
        w.setProperty("jlpt_combo_ss", None)


def apply_tabs(tabs: QTabWidget, on: bool):
    """Tab titles only — cheap, for titles rewritten later (the Marked &
    Suspended counts)."""
    for i in range(tabs.count()):
        en_k, ja_k = f"jlpt_tab{i}", f"jlpt_tabja{i}"
        cur = tabs.tabText(i)
        if on:
            if tabs.property(ja_k) == cur:
                continue
            ja = translate(cur)
            if ja != cur:
                tabs.setProperty(en_k, cur)
                tabs.setProperty(ja_k, ja)
                tabs.setTabText(i, ja)
        elif tabs.property(en_k) is not None:
            if tabs.property(ja_k) == cur:
                tabs.setTabText(i, tabs.property(en_k))
            tabs.setProperty(en_k, None)
            tabs.setProperty(ja_k, None)


# Gold word chips (the Overview's most-common-missing list), like the tiles:
# gold gradient, dark bronze text.
LIST_SS = (
    "QListWidget { background: transparent; border: none; }"
    "QListWidget::item { color: #3b2600; border: 1px solid #fff2b8; border-radius: 4px;"
    " padding: 2px 6px;"
    " background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffe98f, stop:1 #e0b225); }"
    "QListWidget::item:hover { background: #fff3c2; }"
    "QListWidget::item:selected { color: #3b2600; background: #fff7d6; }"
)

# The gold tab frame (dialog tab bar), applied with the text.
TAB_SS = (
    "QTabWidget::pane { border: 1px solid rgba(245,197,24,0.55); }"
    "QTabBar::tab { color: #ffe066; background: #2a2410; border: 1px solid #6b5a1a;"
    " padding: 4px 10px; margin-right: 1px; }"
    "QTabBar::tab:hover { background: #3a3114; }"
    "QTabBar::tab:selected { color: #14110a; font-weight: bold;"
    " background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #fff3b0, stop:1 #f5c518); }"
)
