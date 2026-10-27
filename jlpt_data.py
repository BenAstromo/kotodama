"""
jlpt_data.py
Manages JLPT vocabulary lists and word matching.

Matching strategy:
  A user card is considered to "know" a JLPT word when:
    1. Its display (kanji) form matches either the JLPT display or JLPT reading, OR
    2. Its reading (kana) form matches the JLPT reading.

  Deduplication: two JLPT entries with the same reading are treated as DIFFERENT
  words only when their display forms differ (e.g. 家庭 vs 課程 are both かてい
  but are separate entries).  Two entries with the SAME reading AND the same
  display are duplicates and are merged.

  Kana-only words (e.g. 眼鏡 ↔ めがね): if the user's card field contains めがね
  we still match it against the JLPT entry 眼鏡 because reading == めがね.

Unlisted words: any deck card that does not appear in any JLPT level list is
collected under the special key "unlisted".
"""

import os
import re
import unicodedata

LEVELS = ["N5", "N4", "N3", "N2", "N1"]

# Single source of truth for level colours, shared by every UI module.
# LEVEL_COLORS is the bright foreground; LEVEL_BG the dark gradient stop.
LEVEL_COLORS = {
    "N5": "#4caf50",
    "N4": "#8bc34a",
    "N3": "#ff9800",
    "N2": "#f44336",
    "N1": "#9c27b0",
}
LEVEL_BG = {
    "N5": "#1b5e20",
    "N4": "#33691e",
    "N3": "#e65100",
    "N2": "#b71c1c",
    "N1": "#4a148c",
}

# Directory where this file lives — bundled word lists live alongside it
_HERE = os.path.dirname(os.path.abspath(__file__))


# ── Per-word metadata (from optional 3rd/4th list columns) ───────────────────
#
# Keyed by (display, reading). Filled as list files are loaded, so it covers
# the Kotodama JLPT lists.
#   ALT_FORMS: other spellings of the same word, e.g. いちばん → [一番]
#   FLAGS:     loanword flags derived from JMdict — "eng", "wasei", "abbr",
#              or "loan-<lang>" for loanwords from other languages
ALT_FORMS:    dict[tuple[str, str], list[str]] = {}
FLAGS:        dict[tuple[str, str], set[str]]  = {}
ALT_READINGS: dict[tuple[str, str], list[str]] = {}   # other readings (5th column)

# Words whose meaning in Japanese differs from the English source, so an
# English speaker can't simply guess them: the loanword button never marks
# them. JMdict only tags some wasei-eigo explicitly; these are ones it misses.
# Owner-reviewed 2026-10-08 against Wikipedia's "List of gairaigo and
# wasei-eigo terms" (クレーム, マスター, プロレス … were judged guessable and
# moved out).
FALSE_FRIENDS = {
    "ワイシャツ", "マンション", "スマート", "ハンドル", "カンニング", "トランプ", "ミシン", "タレント",
    "パチンコ", "ルーズ", "ボーイ", "テンション", "センス", "リベンジ", "ストーブ", "ワンピース", "シール",
    "パンク", "スタイル", "パンツ", "クラクション", "ニート", "ラムネ", "ヤンキー", "ペイオフ", "スルー",
}

# Katakana words that count as English loanwords for the button even though
# JMdict tags them as abbreviations or wasei-eigo: the owner judged them
# understandable to an English speaker (テレビ, アニメ, エアコン, リモコン,
# ボールペン). Owner-reviewed word by word on 2026-10-08; abbreviations not
# listed here stay skipped (パソコン, コンビニ, ハンカチ, パート, ハンバーグ),
# as do loanwords from other languages (アルバイト).
COUNT_AS_ENGLISH = {
    "アパート", "カレー", "テレビ", "トイレ", "ノート", "フォーク", "ペット", "アメリカ", "ソフト", "タイプ",
    "スーパー", "アウト", "オーバー", "カード", "クラシック", "クリーム", "ゴール", "コピー", "スタンド",
    "デモ", "トップ", "ドラマ", "ビデオ", "プロ", "マイク", "ミルク", "エプロン", "ガム", "ギャング",
    "コース", "スライド", "センチ", "ダブル", "チップ", "ナンバー", "バック", "フリー", "ランニング",
    "アップ", "アプローチ", "アルミ", "インフレ", "オートマチック", "キャッチ", "コンタクト", "スプリング",
    "タイマー", "タイムリー", "ダウン", "ダンプ", "チェンジ", "テレックス", "ネガ", "マーク", "レギュラー",
    "ブル", "メール", "ネット", "イン", "バイク", "ハウス", "オフ", "ミニ", "ボディー", "テロ", "バンク",
    "ブロック", "ケーブル", "セル", "アニメ", "バブル", "リアル", "ショート", "ハード", "メーク", "ピース",
    "キャラ", "イラスト", "スポット", "ログ", "マルチ", "マイクロ", "オート", "シングル", "クレジット",
    "メジャー", "リビング", "ホット", "エコ", "チョコ", "タグ", "ロール", "アメリカン", "デッキ", "コマンド",
    "トーク", "スロー", "コール", "ネーム", "マジック", "コンパクト", "クロース", "ストレッチ", "フェア",
    "マザー", "ハンド", "ラテン", "コーラ", "ワイヤ", "インテリア", "ワゴン", "フォロー", "ポテト",
    "インフラ", "バイオ", "シャープ", "ピッチ", "ダイニング", "リハビリ", "バレー", "バラエティー", "コミック",
    "デフレ", "ミッション", "ブリッジ", "ラッシュ", "ネック", "ループ", "ダート", "ドメイン", "ウォッチ",
    "ドッグ", "ドック", "セルフ", "ナビ", "セールス", "イエロー", "カート", "スナック", "アンダー",
    "スロット", "ホモ", "パッド", "レザー", "バスケット", "ツイン", "オープニング", "ステンレス", "フィギュア",
    "マイナー", "ノブ", "ヘリ", "エコー", "コットン", "リップ", "セッション", "カッター", "ランダム",
    "フロッピー", "パーマ", "アンプ", "ポピュラー", "ハンデ", "スカウト", "キャスター", "ポリ", "エアロ",
    "スナップ", "インナー", "ミドル", "ミント", "ポルノ", "ボー", "ネオン", "デス", "ハードル", "シャトル",
    "クイック", "ネーティブ", "アンカー", "エディター", "エロ", "ファーム", "コスメ", "ハザード", "コースター",
    "ローション", "スパイク", "セレブ", "ファウル", "ディ", "タップ", "パーフェクト", "アロマ", "バーゲン",
    "タイト", "メカ", "シンクロ", "バーガー", "ギブ", "モノクロ", "テク", "コラボ", "スクラップ",
    "エコノミー", "ジェイ", "バスケ", "スワップ", "レポ", "グラデーション", "コールド", "ウインド", "ネービー",
    "リキッド", "ブレーン", "ワイヤレス", "キャブ", "アスパラ", "テクノ", "アナル", "トート", "キウイ",
    "サプリ", "リニア", "アッパー", "ラボ", "アプリ", "パラ", "ハンティング", "ピック", "テレコム",
    "ミリオン", "リムジン", "マヨ", "プロテイン", "ロボ", "サックス", "スペル", "フェラ", "マタニティー",
    "スコッチ", "ドロー", "ボールペン", "デパート", "ビル", "レジ", "ダイヤ", "ビニール", "インテリ",
    "エアコン", "コンビ", "インター", "レス", "ロケ", "ヘルス", "アトピー", "メンテ", "コンペ", "コネ",
    "コピペ", "ファンデ", "フィル", "アマ", "グラ", "ダックス", "オペ", "コンポ", "エレキ", "ラジカセ",
    "ワープロ", "ゼミ", "パトカー", "マスコミ", "カテ", "スト", "デジカメ", "リストラ", "アナ", "レフ",
    "リモコン", "セクハラ", "メルアド", "トレ", "カーナビ", "メルマガ", "スタメン", "ネル", "ファミレス",
    "ギャラ", "フロン", "サス",
    # Owner 2026-10-09: words JMdict tags as French, German, Dutch, Italian …
    # that English shares with the same meaning (コーヒー, レストラン, エネルギー).
    "キロ", "コーヒー", "メートル", "レストラン", "キロメートル", "キログラム", "アルコール", "ガス", "ガラス",
    "サラダ", "ピアノ", "エネルギー", "ビール", "ヨーロッパ", "エチケット", "オルガン", "コック", "ゴム",
    "テーマ", "テンポ", "ビタミン", "ミリ", "リットル", "レンズ", "アルカリ", "イエス", "カテゴリー",
    "コンパス", "シック", "ジャンル", "ソロ", "ニュアンス", "ホース", "ポンプ", "ランプ", "レバー", "ドル",
    "センチメートル", "タバコ", "ミリメートル", "ウイルス", "ラーメン", "イスラム", "ホルモン", "デビュー",
    "イオン", "アイス", "カフェ", "ミリリットル", "ヘクタール", "アレルギー", "ミリグラム", "オペラ", "サロン",
    "リンパ", "ドクター", "オリーブ", "カトリック", "エリート", "プチ", "モチーフ", "ウラン", "パスタ",
    "ポンド", "ギョーザ", "イデオロギー", "ヨーグルト", "ワクチン", "グルメ", "アール", "ピザ", "キムチ",
    "プロフィール", "ベージュ", "スパゲッティ", "マヨネーズ", "ゲリラ", "ヨーガ", "ベクトル", "ペニス",
    "ルネサンス", "シルエット", "マージャン", "シェフ", "ソナタ", "バレエ", "ミクロ", "アトリエ", "エトセトラ",
    "シャンパン", "クーデター", "フラン", "ブルジョア", "マント", "アンティーク", "コロッケ", "カプセル",
    "スペクトル", "ゲノム", "マダム", "シロップ", "ガーゼ", "カリスマ", "マルク", "サウナ", "ウィンナ",
    "グランプリ", "ムスリム", "アクリル", "レイ", "フェスタ", "フラ", "ルー", "ナチ", "ピエロ", "カルテル",
    "ウーロン", "ソーダ", "チタン", "カジノ", "タルト", "ムース", "ウォッカ", "カテーテル", "コラーゲン",
    "クロム", "オブジェ", "ブーケ", "アンサンブル", "エタノール", "カフェイン", "シネマ", "バロック", "グラタン",
    "フェニックス", "ウォン", "コンソメ", "メタン", "エゴ", "プラチナ", "ドン", "エロス", "ショコラ",
    "ハングル", "ソプラノ", "クーポン", "トリオ", "クレープ", "ヌーボー", "ソテー", "カースト", "シフォン",
    "クレヨン", "ゲルマン", "ディスコ", "マドンナ", "カオス", "ビュッフェ", "ヘルニア", "アルト", "バラード",
    "ラメ", "サタン", "コカイン", "メトロ", "リキュール", "チャクラ", "コルク", "ルージュ", "メチル", "ラビ",
    "レアル", "テーゼ", "ゴンドラ", "オンブズマン", "マリネ", "ブルゾン", "アリア", "セロハン", "ヒステリー",
    "スルタン", "マンガン", "ホルン", "ラマ", "キロリットル", "インディオ", "フラメンコ", "コサージュ", "サテン",
    "ハディース", "パフェ", "クーペ", "プロレタリア", "ジュ", "リラ", "シャトー", "ペチカ", "ローブ",
    "スエード", "レジスタンス", "アスベスト", "バカンス", "キャバレー", "コレラ", "バラモン", "オナニー",
    "パプリカ", "レトルト",
    # Owner 2026-10-09: the old dated words (90s tech, old spellings); the
    # Suspend Dated Words button was removed and these count as English instead.
    "テープレコーダー", "タイプライター", "カセット", "ステレオ", "スチュワーデス", "タイピスト", "トランジスター",
    "ビールス", "インキ", "タイア", "レクリェーション", "ドライブイン",
}

# Katakana words that aren't English loanwords at all, though JMdict gives
# them no foreign source (so they'd default to "eng"): native words written in
# katakana (コメ 米, クリ 栗), sound words (ドーン, シャー) and words from other
# languages English doesn't share (サボテン, ゴーヤー). Owner, 2026-10-09.
NOT_ENGLISH = {
    "サボテン", "ゴーヤー", "チャンポン", "アリラン", "キリ", "コメ", "クリ", "イチジク", "ハブ", "ドーン",
    "シャー", "ジャン",
}

def format_pct(known: int, total: int) -> str:
    """Percentage with one decimal. Only a truly complete count shows 100.0% —
    anything short of it is capped at 99.9% so it never rounds up."""
    if total <= 0:
        return "0.0%"
    if known >= total:
        return "100.0%"
    return f"{min(known / total * 100, 99.9):.1f}%"


def format_progress(known: int, total: int) -> str:
    """e.g. "37.3%  (2,906 / 7,794)" — the one format every bar uses."""
    return f"{format_pct(known, total)}  ({known:,} / {total:,})"


def _merge(table: dict, key, values) -> None:
    """Append values to table[key], keeping order and skipping duplicates."""
    lst = table.setdefault(key, [])
    for v in values:
        if v and v not in lst:
            lst.append(v)


def alt_forms(display: str, reading: str) -> list[str]:
    return ALT_FORMS.get((display, reading), [])


def same_kanji_forms(display: str, reading: str) -> list[str]:
    """The alternate spellings that may count as this word on a card: those
    written with the entry's own kanji (owner 2026-10-14). A spelling with
    different kanji is a different word (会う ↛ 遭う, 作る ↛ 造る, 飛ぶ ↛ 跳ぶ),
    as the JLPT N2/N1 kanji sections test exactly that choice."""
    return [a for a in alt_forms(display, reading)
            if counts_as(display, a)]


def counts_as(entry: str, spelling: str) -> bool:
    """True if a card spelled `spelling` can be the list word `entry`."""
    return same_kanji(entry, spelling) or (entry, spelling) in DATED_SPELLINGS


# List entries written in a dated or rare spelling of a word whose modern
# spelling uses other kanji: a card in the modern spelling still counts.
# Not choices the exam tests (庖丁 vs 包丁), unlike 会う / 遭う.
DATED_SPELLINGS = {
    ("中味", "中身"), ("馴れる", "慣れる"), ("馴らす", "慣らす"),
    ("庖丁", "包丁"), ("贋物", "偽物"), ("真に", "誠に"), ("膨脹", "膨張"),
    ("濫用", "乱用"), ("箇箇", "個々"), ("跡切れる", "途切れる"),
    ("悪い", "憎い"),   # N1 悪い にくい
}


# Print-standard glyphs (JIS2004) → the simplified forms most fonts and
# dictionaries use: one kanji drawn two ways, not two kanji.
GLYPH_VARIANTS = {
    "剝": "剥", "𠮟": "叱", "噓": "嘘", "頰": "頬", "搔": "掻", "摑": "掴",
    "瘦": "痩", "繫": "繋", "塡": "填", "蔣": "蒋", "醬": "醤", "俱": "倶",
    "啞": "唖", "嚙": "噛", "吞": "呑", "餠": "餅", "鷗": "鴎", "鹼": "鹸",
    "蠟": "蝋", "禱": "祷", "屛": "屏", "潑": "溌", "囊": "嚢", "焰": "焔",
    "繡": "繍", "蟬": "蝉", "顚": "顛", "瀆": "涜", "蠅": "蝿", "姸": "妍",
}


def _is_kanji(c: str) -> bool:
    o = ord(c)
    return 0x3400 <= o <= 0x9FFF or 0xF900 <= o <= 0xFAFF or 0x20000 <= o <= 0x3FFFF


def _kanji_seq(word: str) -> list[str]:
    """The kanji of a spelling in order: glyph variants unified, 々 spelled
    out (時々 = 時時), the honorific prefix 御 dropped (御飯 = ご飯)."""
    out = []
    for i, c in enumerate(unicodedata.normalize("NFKC", word)):
        c = GLYPH_VARIANTS.get(c, c)
        if c == "々" and out:
            out.append(out[-1])
        elif _is_kanji(c):
            if not (i == 0 and c == "御" and len(word) > 1):
                out.append(c)
    return out


def _subseq(short: list, long: list) -> bool:
    it = iter(long)
    return all(c in it for c in short)


def same_kanji(entry: str, spelling: str) -> bool:
    """True if `spelling` writes the word `entry` with the same kanji.
    Writing some kanji in kana is fine (子ども / 子供, 一しょ / 一緒), and so is
    writing the entry's kana in kanji (子供 for 子ども) — but a kanji the
    entry doesn't have, in place of one it does, makes another word."""
    ek, sk = _kanji_seq(entry), _kanji_seq(spelling)
    if not ek or _subseq(sk, ek):
        return True
    if not _subseq(ek, sk):
        return False
    # The spelling has extra kanji; each must stand for kana of the entry
    # that the spelling no longer has (子ども → 子供: 供 for ども).
    gone = [c for c in entry if not _is_kanji(c) and c not in spelling]
    return len(sk) - len(ek) <= len(gone)


def alt_readings(display: str, reading: str) -> list[str]:
    return ALT_READINGS.get((display, reading), [])


def suru_stem(display: str, reading: str):
    """(stem, reading) of a katakana word + する (チェックする → チェック), else
    None. The same word as its stem (one meaning = one word)."""
    if display.endswith("する") and len(display) > 2 and all(
            "ァ" <= c <= "ヶ" or c == "ー" for c in display[:-2]):
        r = reading[:-2] if reading.endswith(("する", "スル")) else reading
        return display[:-2], r or display[:-2]
    return None


def is_english_loanword(display: str, reading: str) -> bool:
    """True for plain English loanwords an English speaker can guess:
    excludes wasei-eigo, abbreviations (パソコン; but see COUNT_AS_ENGLISH),
    false friends and words that aren't English (NOT_ENGLISH). A katakana
    word + する (チェックする, コピーする) is judged by its katakana part
    (owner 2026-10-21: チェックする was left out — the list's own flags
    don't cover チェック; the frequency list's do)."""
    stem = suru_stem(display, reading)
    if stem is not None:
        if is_english_loanword(*stem):
            return True
        from . import freq_data
        return freq_data.is_english_loanword(*stem)
    flags = FLAGS.get((display, reading), ())
    return (("eng" in flags or display in COUNT_AS_ENGLISH)
            and display not in FALSE_FRIENDS
            and display not in NOT_ENGLISH)


# ── Kotodama JLPT list loading ─────────────────────────────────────────────────

def _load_bundled(level: str) -> list:
    """
    Load the bundled .txt file for the given level.
    Returns [(display, reading), ...].
    Falls back to empty list if the file is missing.
    """
    path = os.path.join(_HERE, f"jlpt_{level.lower()}.txt")
    if os.path.isfile(path):
        return _load_file(path)
    return []


def _load_file(path: str) -> list:
    """
    Parse a vocabulary file.  Accepted formats (may be mixed in one file):
      - word only            →  (word, word)
      - word<TAB>reading     →  (word, reading)
      - word,reading         →  (word, reading)
      - word<TAB>reading<TAB>alt1|alt2<TAB>flag1,flag2<TAB>read1|read2
                             →  (word, reading), extra columns stored in
                                ALT_FORMS / FLAGS / ALT_READINGS
    Comments (#) and blank lines are ignored.
    Entries where the reading contains only non-Japanese ASCII text
    (scraper artefacts) have their reading replaced by the word itself.
    Returns list of (display, reading).
    """
    BAD = re.compile(r'(noun|adjective|participle|taking|particle|adverb)', re.IGNORECASE)
    # A reading that mixes ASCII letters with Japanese characters is a scraper
    # artefact (e.g. 'aっ' for あっ, where the scraper lost the hiragana 'あ'
    # and substituted ASCII 'a'). Such a reading is guaranteed wrong, so we
    # replace it with the display form just as we do for English POS words.
    ASCII_IN_JP = re.compile(r'[a-zA-Z]')
    words = []
    seen  = set()   # (display, reading) dedup within one file
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                line = re.sub(r"<[^>]+>", "", line)
                if "\t" in line:
                    parts = [p.strip() for p in line.split("\t")]
                elif "," in line:
                    parts = [p.strip() for p in line.split(",", 1)]
                else:
                    parts = [line.strip()]
                display = parts[0]
                reading = parts[1] if len(parts) > 1 else parts[0]
                if not display:
                    continue
                # Fix scraper artefacts: English POS words, or ASCII letters
                # mixed with Japanese characters (e.g. 'aっ' → should be 'あっ').
                # In both cases the reading is corrupt — fall back to display.
                has_japanese = any(ord(c) > 0x3000 for c in reading)
                if BAD.search(reading) or (ASCII_IN_JP.search(reading) and has_japanese):
                    reading = display
                key = (display, reading)
                # The same word can be listed at two levels with different
                # extra columns (N5 かかる 掛かる vs N3 かかる 罹る; N4 もっとも
                # 最も vs N3 もっとも 尤も — 17 entries). Merge them instead of
                # letting the later level overwrite the earlier one, which hid
                # 掛かる / 最も cards from the N5 / N4 entries.
                if len(parts) > 2 and parts[2]:
                    _merge(ALT_FORMS, key, parts[2].split("|"))
                if len(parts) > 3 and parts[3]:
                    FLAGS.setdefault(key, set()).update(f for f in parts[3].split(",") if f)
                if len(parts) > 4 and parts[4]:
                    _merge(ALT_READINGS, key, parts[4].split("|"))
                if key not in seen:
                    seen.add(key)
                    words.append((display, reading))
    except Exception:
        pass
    return words


# ── List building ─────────────────────────────────────────────────────────────

def build_lists(lists_cfg: dict = None) -> dict:
    """
    Build {level: [(display, reading), ...]} from the bundled lists.
    Always the bundled ones (owner 2026-10-26): Nakama, History and the Goal
    compare numbers across people and days, so everyone uses the same lists.
    lists_cfg (the old per-level upload settings) is ignored; an old
    {"mode": "files"} entry in someone's config has no effect.
    """
    return {level: _load_bundled(level) for level in LEVELS}
