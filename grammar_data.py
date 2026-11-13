"""
grammar_data.py
Grammar tracker (backlog #5, phase 2): OpenJLPT's 526 grammar points, known
from a grammar deck's field or marked by hand. Like kanji, grammar doesn't
affect the rank or the word counts.

A grammar point is KNOWN when a studied card (learning, young or mature;
owner 2026-10-21, like words) in the grammar deck matches it, or the user marked it found (middle-click). How WELL is the
same heatmap score as kanji (kanji_data.card_score, mean over its cards).

Matching a card's field to a point:
  - Each pattern gives one or more keys: its " / " alternatives, with
    English hints in brackets dropped (〜で（means）→ で) and Japanese ones
    optional (〜場合（は）→ 場合は, 場合); only kana/kanji are kept, so
    〜, ～, spaces and romaji don't matter.
  - The field is cleaned the same way, also split on / ／ 、 , ; and line
    breaks, so "〜がてら (while)", "がてら", "〜がてら／〜かたがた" all work.
  - 25 keys are shared by several points (で: place of action, means, the
    で of 〜くて / 〜で). A card whose key is shared counts only when English
    words on the card pick out one point (its bracket hint or meaning, e.g.
    "で (means)"). Otherwise it counts for none and is listed as unmatched:
    the owner wants the right points detected, not inflated counts.
  - Sentence parsing (phase 3) will add a "sentence" source.
"""

from __future__ import annotations

import json
import os
import re
import unicodedata

from . import card_state
from .jlpt_data import LEVELS
from .kanji_data import card_score, field_text, field_labels, weigh_contexts

_HERE = os.path.dirname(os.path.abspath(__file__))
_PATH = os.path.join(_HERE, "grammar_jlpt.json")


def _is_jp(c: str) -> bool:
    o = ord(c)
    return (0x3040 <= o <= 0x30FF or 0x4E00 <= o <= 0x9FFF
            or 0x3400 <= o <= 0x4DBF or o == 0x3005)


def _jp_only(s: str, tilde: bool = False) -> str:
    """Only the kana/kanji of s; with tilde=True also 〜 (～ and ~ become 〜),
    for the exact written form."""
    s = unicodedata.normalize("NFKC", s).replace("~", "〜")
    return "".join(c for c in s if _is_jp(c) or (tilde and c == "〜"))


def _hint(alt: str) -> str:
    """The English hint of one alternative: 〜で（means）→ "means"."""
    m = re.search(r"[（(]([^）)]*)[）)]", alt)
    return m.group(1) if m and not _jp_only(m.group(1)) else ""


# OpenJLPT separates alternatives with " / "; a bare "/" can be inside an
# English hint (〜らしい（hearsay/conjecture）).
_ALT = re.compile(r"\s+/\s+|\s*／\s*")


def _forms(pattern: str, tilde: bool, full_only: bool = False) -> set[str]:
    """Every written form of a pattern: its " / " alternatives, English
    hints dropped, Japanese bracket parts optional (full_only: always
    included, i.e. the form as written)."""
    out = set()
    for alt in _ALT.split(pattern):
        def opt(m):
            inner = m.group(1)
            return "\0" + inner + "\0" if inner and inner == _jp_only(inner) else ""
        parts = re.sub(r"[（(]([^）)]*)[）)]", opt, alt).split("\0")
        variants = [""]
        for i, part in enumerate(parts):
            optional = i % 2 and not full_only
            variants = ([v + part for v in variants] + variants) if optional else [v + part for v in variants]
        for v in variants:
            k = _jp_only(v, tilde)
            if _jp_only(k):
                out.add(k)
    return out


def pattern_keys(pattern: str) -> set[str]:
    return _forms(pattern, tilde=False)


_SPLIT = re.compile(r"[/／、,，;；\n]+")


def field_parts(raw: str) -> tuple[list[tuple[str, str]], str]:
    """([(key, exact form)] for each part of a grammar card's field, its
    lower-case English text)."""
    text = re.sub(r"<br\s*/?>|</div>|</p>", "\n", raw or "", flags=re.I)
    text = field_text(text)
    parts = [(_jp_only(p), _jp_only(p, tilde=True)) for p in _SPLIT.split(text)]
    english = " ".join(re.findall(r"[A-Za-z]+(?:[ '-][A-Za-z]+)*", text)).lower()
    return [(k, e) for k, e in parts if k], english


# ── bundled list ──────────────────────────────────────────────────────────────

_DATA = None
_INDEX = None

# The basic particles (owner's list, 2026-10-09): left out of the Text
# Check's grammar list. (Their "★ Mark basic particles as found" button went
# 2026-10-28: the parser finds every one in any deck with sentences.)
BASIC_PARTICLES = ["wa", "ga-subject", "o", "ni-destination", "ni-time",
                   "ni-indirect-object", "de-place", "de-means", "no", "mo", "to-and",
                   "to-with", "e", "ka-question", "ne", "yo"]


def data() -> dict:
    """id → point dict (id, level, pattern, romaji, meaning, formation,
    ex_ja, ex_en, notes), N5 → N1 in OpenJLPT's order."""
    global _DATA
    if _DATA is None:
        try:
            with open(_PATH, encoding="utf-8") as f:
                _DATA = {p["id"]: p for p in json.load(f)["points"]}
        except (OSError, ValueError, KeyError):
            _DATA = {}
    return _DATA


def key_index() -> dict[str, list[str]]:
    global _INDEX
    if _INDEX is None:
        _INDEX = {}
        for gid, p in data().items():
            for k in pattern_keys(full_pattern(gid)):
                _INDEX.setdefault(k, []).append(gid)
    return _INDEX


def level_ids() -> dict[str, list[str]]:
    out = {lvl: [] for lvl in LEVELS}
    for gid, p in data().items():
        out.setdefault(p["level"], []).append(gid)
    return out


def _hint_of(gid: str) -> str:
    return " ".join(h for h in (_hint(a) for a in _ALT.split(data()[gid]["pattern"])) if h)


def _pick(ids: list[str], exact: str, english: str) -> list[str]:
    """Choose among points that share a key (see the module docstring)."""
    # 1. The card writes one point's pattern exactly (〜しか〜ない vs 〜しかない).
    #    The form as written first (〜上 is 〜上, not 〜上（に）), then with
    #    optional parts left out.
    for full_only in (True, False):
        hit = [g for g in ids if exact in _forms(data()[g]["pattern"], True, full_only)]
        if len(hit) == 1:
            return hit
    # 2. The card contains one point's whole English hint ("で (means)").
    letters = lambda s: " ".join(re.findall(r"[a-z]+", s.lower()))
    hit = [g for g in ids if _hint_of(g) and letters(_hint_of(g)) in letters(english)]
    if len(hit) == 1:
        return hit
    # 3. English words on the card overlap one point's hint + meaning most.
    words = set(re.findall(r"[a-z]{2,}", english))
    if words:
        def overlap(g):
            ref = _hint_of(g) + " " + data()[g]["meaning"]
            return len(words & set(re.findall(r"[a-z]{2,}", ref.lower())))
        scored = sorted(((overlap(g), g) for g in ids), reverse=True)
        if scored[0][0] and scored[0][0] > scored[1][0]:
            return [scored[0][1]]
    # 4. No English to go on: a bare 〜て card means the single-form point
    #    written without a hint (〜て, not 〜て（reason）); never a multi-form
    #    one (a bare で isn't 〜くて / 〜で).
    plain = [g for g in ids if not _hint_of(g) and "/" not in data()[g]["pattern"]]
    return plain if len(plain) == 1 else []


def match_field(raw: str) -> list[str]:
    """Grammar point ids a card's field names (see the module docstring)."""
    parts, english = field_parts(raw)
    idx = key_index()
    out = []
    for key, exact in parts:
        ids = idx.get(key, [])
        if len(ids) > 1:
            ids = _pick(ids, exact, english)
        for gid in ids:
            if gid not in out:
                out.append(gid)
    return out


# ── grammar in sentences (phase 3) ────────────────────────────────────────────
# Each pattern's written forms become search rules: the literal parts in
# order (〜 = a gap of up to 25 characters), the last part allowed to
# conjugate (ことにする also finds ことにした / ことにします). Only DISTINCTIVE
# forms are searched (owner: detect the right ones, don't inflate): at least
# 3 characters of pattern text, or 2 with a kanji, and not shared with
# another point (で, が, そうだ appearance / hearsay can't be told apart in a
# sentence). Short ones (〜て, 〜が, 〜も) come only from a grammar deck or
# hand marks.

SENTENCE_SKIP: set[str] = set()   # extra point ids never searched in sentences

# Spellings OpenJLPT's pattern leaves out, per point id (it lists the pairs
# なければならない / なくてはいけない, but the mixed ones are as common).
EXTRA_FORMS = {
    "nakereba-naranai-nakute-wa-ikenai": ["〜なければいけない", "〜なくてはならない",
                                          "〜なきゃいけない", "〜なきゃならない", "〜ねばならない"],
    "ni-kagiru": ["〜にかぎる"],
    "hou-ga-ii": ["〜方がいい", "〜方が良い", "〜方がよい", "〜ほうが良い", "〜ほうがよい"],
    "te-iru": ["〜ておる", "〜でおる"],
    "ga-hoshii": ["〜が欲しい"],
    # recall test 5 (2026-10-16):
    "te-kudasai": ["〜て下さい"],
    "ga-suki-ga-kirai": ["〜が大好き", "〜が大嫌い"],
    "ta-koto-ga-aru": ["〜たことがない", "〜たことはない", "〜たことない"],   # 習ったことないよ (recall test 13)
    # point coverage (2026-10-17): forms the examples use but the pattern lacked
    "ni-tomonatte": ["〜に伴い", "〜に伴う", "〜にともない", "〜にともなう"],
    "o-fumaete": ["〜を踏まえ", "〜をふまえ"],
    "te-wa-ikenai": ["〜ちゃいけない", "〜ちゃだめ", "〜ちゃダメ", "〜ちゃ駄目", "〜じゃいけない", "〜ではだめ", "〜てはだめ", "〜てはダメ"],
    "o-kudasai": ["〜を下さい"],
    # recall test 8 (2026-10-17): kanji spellings and plain negatives
    "te-hoshii": ["〜て欲しい"],
    "te-hajimete": ["〜て初めて"],
    "ni-mo-kakawarazu": ["〜にも関わらず", "〜にも拘らず", "〜にも拘わらず"],
    "de-wa-arimasen-ja-nai": ["〜ではない", "〜じゃなく"],
    "dake-de-naku": ["〜だけではなく", "〜だけじゃなく"],
    "bakari-de-naku": ["〜ばかりではなく", "〜ばかりじゃなく"],
    "koto-ga-dekiru": ["〜ことが出来る"],     # recall test 9
    "te-mo-ii": ["〜ても良い", "〜てもよい", "〜ても宜しい", "〜てもよろしい"],   # recall test 10
    "nakute-mo-ii": ["〜なくても良い", "〜なくてもよい"],
    "to-omou": ["〜とは思う", "〜とも思う"],  # 奇妙だとは思いません (recall test 10)
    # the formation's ご + noun + する, the notes' お〜いたす, and the humble
    # potential (お借りできますか, ご案内できます; owner's misses 2026-10-17)
    # sentence-final なきゃ (the notes: "なきゃ is also very common"), and the
    # formation's かけの + noun (読みかけの本) (2026-10-20)
    "nai-to-ikenai-nakucha": ["〜なきゃ"],
    "kakeru": ["〜かけの"],
    # compound particles: the noun-modifying (に基づく / に基づいた + noun) and
    # written (に基づき、) forms their formations list (OpenJLPT examples 2026-10-20)
    "ni-taishite": ["〜に対する", "〜に対し"],
    "ni-oujite": ["〜に応じ"],
    "ni-hanshite": ["〜に反する", "〜に反し"],
    "ni-motozuite": ["〜に基づく", "〜にもとづく"],
    "ni-watatte": ["〜にわたる", "〜にわたり", "〜に渡り"],   # not 〜に渡る: アメリカに渡った (crossed)
    "ni-sotte": ["〜に沿う"],
    "o-megutte": ["〜をめぐる", "〜をめぐり", "〜を巡り"],   # not 〜を巡る: お城を巡る (touring)
    "o-nozoite": ["〜を除く"],   # not kana: 本屋をのぞいて (peek)
    "ni-kotaete": ["〜に応える", "〜に応え"],   # not kana: 胃にこたえる (take a toll)
    "ni-sakidatte": ["〜に先立つ"],
    "ni-atatte": ["〜にあたり"],
    "ni-mukete": ["〜に向け"],
    "ni-sokushite": ["〜に即する", "〜に即し"],
    "ni-nottotte": ["〜に則る", "〜にのっとる"],
    "o-chuushin-ni": ["〜を中心として", "〜を中心とした", "〜を中心とする"],
    # polite / casual / kanji spellings the patterns lacked (OpenJLPT examples 2026-10-20)
    "masu-you-ni": ["〜ませんように"],                       # its formation lists it
    "mono-de-wa-nai": ["〜ものじゃない", "〜もんじゃない"],
    "ni-kimatte-iru": ["〜に決まってる", "〜にきまってる", "〜にきまっている"],
    "mono-ka": ["〜もんか"],
    "te-mo-sashitsukae-nai": ["〜てもさしつかえありません", "〜ても差し支えない", "〜ても差し支えありません",
                              "〜でもさしつかえない", "〜でもさしつかえありません", "〜でも差し支えない",
                              "〜でも差し支えありません"],     # na-adjective / noun + でも (formation)
    "te-shou-ga-nai-te-shikata-ga-nai": ["〜てしかたない", "〜て仕方がない", "〜て仕方ない",
                                         "〜でしょうがない", "〜でしかたがない", "〜でしかたない",
                                         "〜で仕方がない", "〜で仕方ない"],   # na-adjective + で (formation)
    "te-naranai": ["〜でならない"],                          # na-adjective + で (formation)
    "toori-ni-doori-ni": ["〜たとおり", "〜のとおり", "〜どおり", "〜た通り", "〜の通りだ", "〜の通りです",
                          "〜の通りである"],   # 言ったとおり、 / 以下のとおり / 予定どおり; 思った通りだった (recall test 13)
    "kiru-kirenai": ["〜きれない"],   # 隠しきれなかった (recall test 13)
    "gatai": ["〜難い"],               # 言い難い (recall test 13)
    "te-ageru": ["〜てやる"],          # 与えてやった (recall test 13)
    "to-wa-ie": ["とはいえ"],                                # sentence-first とはいえ、
    # N5: kana 誰 / 何 (notes: "誰 is often written in hiragana"), 来る / 帰る
    # ("work the same way: 遊びに来る"), and the other order (notes)
    "nani-mo-nai-dare-mo-nai": ["だれも〜ない", "なにも〜ない"],
    "nani-ka-dare-ka-doko-ka": ["だれか", "なにか"],
    "ni-iku": ["〜に来る", "〜に帰る"],
    "no-hou-ga-yori": ["〜より〜の方が", "〜より〜のほうが"],
    "hazu-da": ["〜はずなのに", "〜はずなので"],             # 置いたはずなのに
    "te-kudasaru-te-itadaku": ["〜てくださいます"],           # 直してくださいました (くださる's い)
    "te-mo-kamawanai": ["〜てもかまわない", "〜でも構わない", "〜でもかまわない"],   # na-adj / noun + でも (formation)
    "o-suru": ["ご〜する", "お〜いたす", "ご〜いたす", "お〜致す", "ご〜致す", "お〜できる", "ご〜できる"],
}


def full_pattern(gid: str) -> str:
    """The point's pattern plus its EXTRA_FORMS, as one " / " pattern."""
    pattern = data()[gid]["pattern"]
    extra = EXTRA_FORMS.get(gid)
    return pattern + " / " + " / ".join(extra) if extra else pattern

_KANJI = chr(0x4E00) + "-" + chr(0x9FFF)
# Characters a gap (〜) may not cross, and that don't count as "something
# before the pattern": spaces and punctuation.
_PUNCT = r"\s、。，,．.！？!?「」『』（）()…―〜~・：:；;" + "\"'“”"
_GAP = "[^" + _PUNCT + "]{1,25}?"
# たり〜たり often has a comma between its two halves (読んだり、聞いたりする)
_COMMA_GAP = "[^" + _PUNCT.replace("、", "") + "]{1,25}?"
_COMMA_GAP_IDS = {"tari-tari-suru"}
_SHORT_GAP = "[^" + _PUNCT + "]{1,6}?"       # お〜する: just a verb stem
# Last characters of a masu stem (書き, 食べ); に left out (it's nearly always
# the particle). Kanji-only stems (見, 寝) aren't accepted: missing a few is
# better than counting 大切 as 〜切る.
_STEM_END = "いきぎしじちぢひびぴみりえけげせぜてでねへべぺめれ"
# The polite endings (ます / ました / ません / ましょう …) and なさい can't
# follow a noun or a particle, so for them the one-kanji ichidan stems
# (見ました, 出ません, 寝なさい) and 来 (来ましょう) are verb stems too, and
# に (死にました) (owner's deck audit 2026-10-17: 見ました / 出ました /
# 死にました were only 〜た). Not any kanji: 覚ました is 覚ます + た.
_POLITE_STEM_END = _STEM_END + "に見出寝着居似煮来得経干射"
# お〜する / お〜になる: what fills the 〜 is one verb stem (お持ち, お知らせ)
# or a kanji noun (ご案内, お電話), nothing else (owner's review 2026-10-14:
# お腹が空きました, おかしい, お父さん were all counted).
_O_GAP = ("(?:[" + _KANJI + "]{1,2}[ぁ-ゖ]?[" + _STEM_END + "]|[" + _KANJI + "]{2,3})")

_GODAN_TAILS = {"う": "(?:[わいうえお]|っ)", "く": "(?:[かきくけこ]|い[てた])",
                "ぐ": "(?:[がぎぐげご]|い[でだ])", "す": "[さしすせそ]",
                "つ": "(?:[たちつてと]|っ)", "ぬ": "(?:[なにぬねの]|ん[でだ])",
                "ぶ": "(?:[ばびぶべぼ]|ん[でだ])", "む": "(?:[まみむめも]|ん[でだ])"}

# Hand-tuned on the owner's 3,373 sentences (2026-10-09). Keyed by the
# pattern text without 〜 (the "core").
_NOT_AFTER = {          # lookbehind: what may not come right before the core
    "として": ("う", "落", "がん", "頑", "閑散", "堂々", "平然", "呆然", "毅然", "悠然", "漠然", "断固", "依然", "[っッ]"),   # + 依然として (still; fresh sample 8)
    # ようとしている (〜ようとする), 落として (drop), がんとして / 閑散として (adverbs; Gemini final);
    # っとして: すらっとして / ぬめっとしてる (mimetic + とする; recall test 5); グッとして (katakana ッ, 2026-11-10)
    "ばかりだ": "[ただ]",           # 〜たばかり
    "ところに": "の", "ところへ": "の", "ところを": "の", "ところだ": "の",   # 友達のところ (a place)
    "わりに": "[終代変替かまお]", "わりには": "[終代変替かまお]",   # + (か)わりに, (ま)わりに (Gemini batch 8)                     # 終わりに
    "がたい": "り",                # ありがたい
    "難い": "り",                  # 有り難い
    "ものだ": "の", "ものだから": "の", "もので": "の",   # そのもの (itself)
    "あまり": "[はもがをにでと]", "あまりに": "[はもがをにでと]",   # the adverb あまり
    "以上": "れ",                  # これ以上 (any more)
    "て初めて": "のっ",             # 書くのって初めて (topic って; recall test 8)
    "てもよい": "と", "ても良い": "と",   # とてもよかった (recall test 10)
    # older precision samples (2026-10-17, round 8):
    "ばほど": "[^えけげせぜてでねへべぺめれ]",   # いちばん…それほど (ば must be a conditional's)
    "たって": "う",                 # うたって (歌って)
    "もうた": "っと",               # ちっともうまくならなかった
    "ものの": "う",                # 〜というもの の …
    "と言う": ("度", "こ"),        # 二度と言わない; そんなこと言った (the と of こと)
    "と思う": "こ",                # そんなこと思ってない / 長いこと思い出せなかった (こと + 思う; recall test 10)
    "とは思う": "こ", "とも思う": "こ",
    "のです": ("も", "誰", "私", "僕", "俺", "君", "彼", "彼女"),   # そのものです; 誰のですか (whose)
    "んです": "[さゃ]",            # 田中さんです, ちゃんです (name suffix + です; Gemini pass 1)
    "までに": ("ここ|そこ|どこ", "今"),   # ここまでにしましょう (let's stop here), 今までに (so far)
    # Gemini review batches 1–3 (2026-10-14), each checked against its sentences:
    "が早いか": ("[方手]", "ほう"),   # 方が早いかも, 手が早いから (not "no sooner than")
    "たりとも": "[ふっ]",           # ふたりとも, ゆったりと
    "とあって": "[んっ]",           # うんとあって, もっとあって
    "とあれば": "っ",               # もっとあれば
    "ときたら": "ピン",             # ピンときたら (not パソコンときたら)
    "なりに": ("[とかく]", "曲がり", "まがり", "弓", "鈴", "いき", "言い", "いい", "道"), "なりの": ("[とかく]", "いき", "弓", "鈴", "言い", "いい"),   # + 言いなり (at someone's beck and call; precision test 6)   # となり(に), かなりの, 人となり, 亡くなりに, 曲がりなりにも (idiom)
    "ともあろう": "こ",             # こともあろうに
    "じみた": "な", "じみる": "な",   # 幼なじみ, なじむ
    "ぐるみ": "[い着]",             # ぬいぐるみ, 着ぐるみ
    "あっての": "が",               # 悪気があってのこと (plain ある + て)
    # Gemini review batches 4–9 (2026-10-14):
    "くらいなら": ("少し", "ちょっと"), "ぐらいなら": ("少し", "ちょっと"),   # 少しくらいなら (a little)
    "ないことには": "の",           # 関わりのないことには (matters that don't concern you)
    "ことから": "ふとした",         # ふとしたことから (by chance)
    "にかけては": "気",             # 気にかけてはいない
    "にあたって": "火",             # 火にあたって (warm oneself by the fire)
    "において": ("たい", "大体", "概"),   # だいたいにおいて / 大体において (generally)
    "ごとに": "大",                 # 大ごとになる
    "っぽい": "ち",                 # ちっぽけ
    "気味": "い",                   # いい気味だ (serves them right)
    "てしょうがない": "[ただ]っ", "てしかたがない": "[ただ]っ",   # 行ったって / したって + しょうがない
    "としたら": ("[っッこ]", "落"), "とすれば": ("[っッこ]", "落"),   # ひょっとしたら, こんなこと + したら; 落としたら (drop; precision test 6); グッとすれば (mimetic + する, owner 2026-11-10)
    "としても": "[何ん]",           # 何としても / なんとしても (by all means)
    "ていく": "なく",               # 書かなくて(は)いけない
    "うと思う": "だろ",             # だろうと思った (conjecture, not a plan)
    "といえば": "か",               # どちらかといえば (if anything)
    "というと": "ざ",               # いざというとき
    "うちに": "その",               # そのうちに (sooner or later)
    "により": "[な何]", "による": "[な何]",   # なにより / 何より
    "次第": "当たり",               # 手当たり次第 (Gemini final)
    # fresh accuracy test (2026-10-14):
    "ごとく": "こと", "ごとき": "こと",   # ことごとく (entirely)
    "ません": "すみ",               # すみません (a greeting, not the negative)
    "から見ると": ("遠く", "横", "上", "下", "前", "後ろ", "外", "窓", "近く", "空"),
    "から見れば": ("遠く", "横", "上", "下", "前", "後ろ", "外", "窓", "近く", "空"),   # 横から見ると (literally)
    "次第だ": "いう",               # こういう次第だ (that's how it is)
    # Gemini review batches 10–13 (2026-10-14):
    "ほうがいい": "の", "方がいい": "の", "方が良い": "の", "方がよい": "の",   # 夏休みのほうがいい (comparison)
    "とかとか": "ひ",               # ひとかどの人物だとか
    "おきに": "お",                 # おおきに (thanks)
    "でした": "せん",               # 見ませんでした (〜ませんでした)
    # accuracy test 3 (2026-10-14):
    "について": ("[^自中]身", "席", "床", "眠り", "家路", "帰途", "職", "位置", "岐路", "食卓"),
    # 身について (身に付く), 席について (sit down); 自身について / 中身について stay
    "にとって": ("手", "自由", "勝手", "大事", "ため"),   # 手にとって / 自由にとって / ためにとって (取る: pick up, keep)
    "までもない": "[^うくぐすつぬぶむる]",   # a plain verb before it (言うまでもない), not のろま+でもない
    # recall test 5 (2026-10-16):
    "たらた": "[もはあわ]",          # もたらした, はたらいた, あたらしい, わたらない
    "につき": ("職", "任", "席", "床", "帰路", "家路", "眠り", "位置"),   # 新しい職につき (就く; precision test 5)
    "続ける": "[てで]", "始める": "[てで]", "終わる": "[てで]",   # 思って続けてる: the verb on its own
    "くなる": "亡",                  # 亡くなる (die)
}
_NOT_BEFORE = {         # lookahead: what may not come right after the match
    "てある": "がと|(?<=れ)(?!ば)",   # ありがとう; これってあれか (あれ only as てあれば)
    "なきゃ": "[^。、！？!?…」』）)ーねなっだ～〜\\s]",   # やらなきゃ。 / なきゃだめ; not 行かなきゃ分からない (unless), 言わなきゃよかった
    "をめぐる": "(?<=[らっれ])|の",   # 思いをめぐらす (ponder); 地球をめぐっている (orbit); 〜をめぐるのが (touring)
    "をめぐり": "[^、]", "を巡り": "[^、]",   # 〜をめぐり、 (温泉を巡り歩く: touring)
    "に向け": "ら|る|れ|な|ま|た(?:[。、！？!?」』）)]|$)|[。！？!?]|$",   # only に向け、 / に向けた + noun:
                                    # アリスに向けられた, 銃を警官に向けた。 (pointing at)
    "に応じ": "(?!、|た[^。、！？!?」』）)のんがとかもでよねわ])",   # only に応じ、 / に応じた + noun:
                                    # 招待に応じた。 / 応じられない (the verb "accept")
    "にあたり": "[まな]",           # 祖母にあたります (is, corresponds to), 火にあたりながら
    "に先立つ": "(?<=た)",          # 息子に先立たれた (predeceased)
    "もんか": "[なね]",             # 使い道ないもんかな (a wish, not "as if I would")
    "といっても": "いい|良い|よい",   # テレビ狂といってもいい (one could say; fresh sample 8); 過言ではない stays (ruling)
    "てくださいます": "(?<=せ)",    # 教えてくださいませんか is a request (〜てください)
    "を除く": "(?<=[いかてた])",    # 苦痛を除いてやった, 除かれた (the verb "remove")
    "と言う": "(?<=わ)んばかり", "という": "(?<=わ)んばかり|(?<=っ)ても",   # + といっても isn't "named"   # 〜と言わんばかりに (〜んばかり)
    "ことなく": "て",              # 〜たことなくて (colloquial こと(が)ない)
    "て初めて": "の",               # 私にとって初めての上京 (first; recall test 8)
    "もうた": "[いくかけ]",          # もう…食べたい (〜たい, not past)
    # Gemini review batches 1–3 (2026-10-14):
    "かたわら": "[にで]",           # 王のかたわらに (beside: a place, not "while also")
    "が早いか": "ら",               # 手が早いから
    "こととて": "も",               # 僕のこと + とても
    "であれ": "ば|[がをはもにのでと]",   # であれば (if it is); マジで + あれが (that); 快活であれと (a command)
    "とあって": "い",               # 靴と合っている
    "はおろか": "[にな]|です|だ",     # あなたは愚かなんだ / 愚かにも / 愚かです
    "とはいえ": "[なま]",           # とはいえない / とはいえません (can't be called)
    "に加えて": "くれ|もら|いただ|あげ|ほし|くださ",   # リストに加えてくれて (the verb "add")
    "をめぐって": "い",             # 地球をめぐっている (orbit)
    "を除いて": "や|くれ|あげ|おく|もら",   # 苦痛を除いてやった (the verb "remove")
    "を通して": "[おい]",           # 水を通しておく, 通している (the verb "pass through")
    # Gemini review batches 4–9 (2026-10-14):
    "ことから": "始|はじ|逃|離",     # 作ることから始めよう, いやなことから逃れる
    "からして": "[も貰く]|お[かきくけこ]|いる",   # 人からしてもらいたい, 常日頃からしておく (not おいしそう)
    "からいって": "[きいたまお]",   # 初めからいってきた (the verb 言う)
    "がたい": "さん",               # 友だちがたくさん
    "ようでは": "な|あり",           # 私たちのようではない, 疲れているようではありません
    "にこたえて": "[きいくる]",     # 胃にこたえてきた (take a toll)
    "につき": "なさ|ます|まと|ました|あ|合|た[いくかけ]",   # 定職につきなさい, 側につきます, つきまとう, 墓参りにつきあわせ; 業務につきたい (sample 9)
    "をはじめ": "[たなまてよれ]",   # 話をはじめた (the verb 始める)
    "というと": "て|き|ころ",       # 号室というとても, いざというときの, 間一髪というところで (precision test 7)
    "ところに": "よ",               # 聞いたところによれば (according to; precision test 7)
    "せいか": "[もとな]",           # 気のせいかもしれない / かと / かな
    "にしては": "いけ|なら|だめ|駄目|いられ|おれ|居られ",   # 無駄にしてはいけない; 気にしてはいられない (2026-10-26)
    "にしても": "ら",               # 静かにしてもらえますか
    "につれて": "[いきこっ]",       # 森の中につれていって (take along)
    "だらけ": "[るてた]",           # だらける (laze about)
    "あまり": "の",                 # あまりの豪華さ
    "のもとで": "あ", "のもとに": "な[るっりら]",   # 経済のもとである (base), 事故のもとになる (cause)
    "による": "しく",               # ご家族によろしく
    "かぎり": "ま|ぎ", "限り": "ま",   # 若いうちにかぎります, とはかぎりません, かぎりぎり
    # Gemini review batches 10–13 (2026-10-14):
    "と思う": "ば|出|込|知|付|つ[きくけ]|切|直|浮|起",   # 何かと思えば (I wondered what …); と思い出す /
    # 思い込む / 思い知る / 思いつく … are other verbs (recall test 10)
    "たらどう": "[すし]",           # 失ったらどうする / どうしよう (what to do if)
    "てください": "まし",           # 認めてくださいました (honorific, not a request)
    "てもいい": "よう",             # 何が起こってもいいように
    "ませんか": "ら",               # なりませんから (〜ませんか needs the question か)
    "次第": "に",                   # 次第に (gradually; Gemini final)
    "として": "い[るたまてな]|おり|おる|おい|る",   # 必要としている / 常としておる: とする (consider, make it), not "as"
    "ばかりか": "け",               # 迷惑ばかりかけて
    "半面": "型", "反面": "に",       # 半面型 (half-face mask), 憂いの反面には (the other side)
    # recall test 3 (honorific verbs now read as words):
    "がいる": "っしゃ|っぱ|ぱ",          # 先生がいらっしゃった (sonkeigo); 雲がいっぱい
    "をください": "ま",              # 本をくださいました (honorific くださる, not a request)
    "になる": "い",                  # 何になさいますか (honorific にする)
    # recall test 5 (2026-10-16):
    "て下さい": "まし",
    # older precision samples (2026-10-17, round 8):
    "なりに": "く[いかくけ]",          # 冷静になりにくい (なる + にくい)
    "くなる": "(?<=ら)(?![なずれせ])",   # 行くなら (if you go); 高くならない stays
}
# 自分に / 十二分に end in 分 but aren't times (Gemini batch 11)
_NOT_TIME_BUN = ("自分", "十二分", "随分", "気分", "半分", "部分", "十分", "多分", "大分", "身分", "親分",
                 "存分", "充分", "幾分", "応分", "職分", "本分", "当分")
# と after these is "with / from", not "and" (事件と関係がある, あなたと意見が違う)
_TO_RELATION = {"関係", "意見", "違い", "同じ", "一緒", "結婚", "喧嘩", "話", "約束", "連絡", "競争",
                "比較", "交際", "付き合い", "相談", "別れ", "協力"}
# verbs that make a て-form part of another point (ている, てくる, てしまう …)
_TE_AUX = {"いる", "ある", "くる", "来る", "いく", "行く", "しまう", "おく", "置く", "みる", "見る",
           "くれる", "もらう", "あげる", "やる", "ください", "下さい", "いただく", "くださる", "ほしい",
           "欲しい", "おる", "いい", "よい", "良い", "かまわない", "構わない", "たまらない", "ならない",
           "しょうがない", "仕方がない", "いけない", "はじめて", "初めて"}
# て-forms used as adverbs / conjunctions, not "and then"
_TE_ADVERBS = {"はたして", "果たして", "たいして", "大して", "従って", "したがって", "決して", "初めて", "はじめて",
               "改めて", "あらためて", "思い切って", "思いきって", "せめて", "極めて", "きわめて", "まして", "全て", "すべて", "かつて", "あえて", "敢えて"}
_TE_AUX_SURF = ("い", "あ", "く", "き", "し", "お", "み", "も", "や", "ほ", "は")
# て-forms that are part of a compound particle (について, に基づいて, を通して …)
_PARTICLE_VERBS = {"する", "つく", "付く", "基づく", "限る", "沿う", "通す", "通じる", "関する", "対する",
                   "よる", "因る", "とる", "取る", "わたる", "渡る", "向ける", "つれる", "連れる", "従う",
                   "比べる", "応じる", "際する", "伴う", "反する", "加える", "めぐる", "巡る", "除く", "おく",
                   "置く", "こめる", "込める", "先立つ", "即する", "当たる", "あたる", "かける", "掛ける",
                   "代わる", "替わる", "向かう", "言う", "いう", "かかわる", "関わる"}
# ones whose を + て-form is a plain verb (ネクタイを取って, 電話をかけて; recall test 8)
_WO_TE_REAL = {"取る", "とる", "かける", "掛ける", "向ける", "加える"}
# particle + verb pairs whose て-form is a compound particle (について、, を通して、),
# never "and then" even before a comma (する and を + つく stay: こんな風にして、
# / うそをつかれて、 are real て-forms; 2026-10-16)
_COMPOUND_TE = {
    "に": {"つく", "付く", "とる", "取る", "おく", "置く", "対する", "関する", "よる", "因る", "基づく", "沿う", "向ける",
          "従う", "比べる", "応じる", "際する", "伴う", "反する", "加える", "先立つ", "即する", "わたる",
          "渡る", "かける", "掛ける", "当たる", "あたる", "限る", "代わる", "替わる"},
    "を": {"通す", "通じる", "除く", "めぐる", "巡る", "こめる", "込める"},
}
_PERMISSION = {"いい", "よい", "良い", "よろしい", "かまわない", "構わない", "かまいません", "構いません"}
_SKIP_FORMS = {"かった"}   # わかった / よかった: can't tell the i-adjective past apart
# Points never searched in sentences: rare, and every hit in the owner's
# sentences was something else (みっともない, 無くして, 上に (on), 手前 (in front)).
_SKIP_PATTERNS = {"〜なくして(は)", "〜なしに(は)", "〜ともなく / 〜ともなしに", "〜ものを",
                  "〜をもって", "〜上（に）", "〜手前", "〜にして", "〜を〜として", "〜上で"}
_NO_VOICE = {"てある"}     # である is the copula, not 〜てある
# Kanji suffixes that do follow kanji nouns (子供向け), unlike 実際 / 週末.
_NOUN_SUFFIX = {"muki-muke", "kiwamaru-kiwamari-nai"}   # + 迷惑極まりない (0 Tatoeba hits before)


# a る after an あ / う / お-row kana is always a godan verb's (ある, なる, かかる)
_GODAN_RU = set("あかがさざただなはばぱまやらわうくぐすずつづぬふぶぷむゆるおこごそぞとどのほぼぽもよろを")


def _tail(lit: str) -> str:
    """Regex for a pattern's last literal part, letting it conjugate."""
    e = re.escape
    if lit.endswith("する"):
        # し / さ / せ only with a real する ending after them (します, して,
        # した, しない, しよう, しろ, される, させる, せず): a bare し / さ / せ
        # was しっぽ, おがさわら, くさい, くせに (owner's review 2026-10-14).
        return e(lit[:-2]) + "(?:する|すれ|し(?=[まてたなよろちつ])|さ(?=[せれな])|せ(?=[ずよん]))"
    if lit.endswith(("くる", "来る")):
        return e(lit[:-2]) + "(?:くる|来る|き[たてま]|来|こ[なよい]|くれ(?=ば))"
    if lit.endswith(("行く", "いく")):
        return e(lit[:-1]) + "(?:[かきくけこ]|っ)"
    if lit.endswith("ます"):
        return e(lit[:-2]) + "ま(?:す|し|せ)"
    if lit.endswith("です"):
        return e(lit[:-2]) + "(?:です|でし(?!ま))"     # not 読んでしまう (deck audit 2026-10-17)
    if lit.endswith("ようだ") and len(lit) > 3:
        # かのような / かのように are the usual forms (the point had 0 Tatoeba hits)
        return e(lit[:-1]) + "(?:だ|じゃ|です|でし|だろ|な|に)"
    if lit.endswith("だ") and len(lit) > 1:
        # not で: ことで / ところで / までで are other grammar
        return e(lit[:-1]) + "(?:だ|じゃ|です|でし|だろ)"
    if lit.endswith("ない") and len(lit) >= 4 and (lit[-3] in "はがも" or lit.endswith("じゃない")):
        # a particle + ない: polite is + ありません (わけがありません, ことはありません,
        # ものではありません, わけじゃありません; 2026-10-20: built as わけがぎません)
        return e(lit[:-2]) + "(?:な(?:い|く|か|け|さ)|ありませ)"
    if lit.endswith("ない") and len(lit) >= 4:
        # polite: ichidan stem + ません (いけない → いけません), godan a → i
        # (ならない → なりません); recall test 2026-10-14. The shared start
        # stays outside the group (a leading て gets voiced elsewhere).
        c = lit[-3]
        a_to_i = dict(zip("あかがさざただなはばぱまやらわ", "いきぎしじちぢにひびぴみいりい"))
        return e(lit[:-3]) + "(?:" + e(c) + "な(?:い|く|か|け|さ)|" + (a_to_i.get(c) or e(c)) + "ませ)"
    if lit == "ない":
        # 全然〜ない, しか〜ない, なかなか〜ない …: the polite negative too
        # (全然分かりません, 時間がありません; owner's deck audit 2026-10-17)
        return "(?:な(?:い|く|か|け|さ)|ませ(?=ん))"
    last = lit[-1]
    if last in _GODAN_TAILS:
        return e(lit[:-1]) + _GODAN_TAILS[last]
    if last == "る" and len(lit) >= 2 and lit[-2] in _GODAN_RU:
        # ある / なる / かかる are godan: あな / なよ aren't their forms
        # (私があなたに → がある, 行くなよ → くなる; recall test 5)
        return e(lit[:-1]) + "(?:る|り|ら|れ|ろ|っ)"
    if last == "る":
        # + ちゃう / ちまう (すぎちゃった, 見ていちゃだめ)
        return e(lit[:-1]) + "(?:る|り|ら|れ|ろ|っ|ま|た|て|な|よ|ず|さ|ち(?=[ゃま]))"
    if last == "い":
        return e(lit[:-1]) + "(?:い|く|か|け|さ)"
    if last == "で":
        return e(lit) + "(?![すし])"      # ないです / ものです aren't 〜ないで / 〜もので
    return e(lit)


def _stem_only(p: dict) -> bool:
    """Formation is purely "Verb-stem + …" (出す, 合う, 切る, ながら)."""
    alts = [a.strip() for a in p.get("formation", "").split(" / ") if a.strip()]
    return bool(alts) and all(a.startswith("Verb-stem") for a in alts)


_DETECTORS = None


def detectors() -> list[tuple[str, str, int, object]]:
    """[(id, a literal every match contains, core length, compiled regex)]."""
    global _DETECTORS
    if _DETECTORS is not None:
        return _DETECTORS
    idx = key_index()
    out = []
    for gid, p in data().items():
        if gid in SENTENCE_SKIP or p["pattern"] in _SKIP_PATTERNS:
            continue
        stem_only = _stem_only(p)
        for form in _forms(full_pattern(gid), True):
            lits = [x for x in form.split("〜") if x]
            core = "".join(lits)
            if core in _SKIP_FORMS or len(idx.get(core, ())) > 1:
                continue
            if not (len(core) >= 3 or (len(core) == 2 and any(0x4E00 <= ord(c) <= 0x9FFF for c in core))):
                continue
            parts = []
            for i, lit in enumerate(lits):
                rx = _tail(lit) if i == len(lits) - 1 else re.escape(lit)
                if ((i == 0 and form.startswith("〜") or i > 0 and len(lit) >= 2) and lit[:1] in ("て", "た")
                        and core not in _NO_VOICE):
                    # て / た also come voiced after a verb (読んで, 泳いだ), but
                    # only after ん / い: elsewhere で is できる (できました
                    # isn't で + 来る) or the particle (何で来ない).
                    # Later parts too when they are more than a lone た / て
                    # (食べたり飲んだりした; not もう〜た in もう来ないんだ; 2026-10-20).
                    rx = "(?:" + lit[0] + "|(?<=[んい])" + {"て": "で", "た": "だ"}[lit[0]] + ")" + rx[1:]
                parts.append("(" + rx + ")")    # a group per written part (sentence_ids)
            gap = _O_GAP if form[:1] in ("お", "ご") else _COMMA_GAP if gid in _COMMA_GAP_IDS else _GAP
            rx = gap.join(parts)
            if form.startswith("〜"):
                # Something must fill the 〜 …
                pre = "(?<=[^" + _PUNCT + "])"
                if core.startswith(("と", "って")):
                    # a closing quote fills it too: 「さくら」という店, 「いただきます」と言う,
                    # 「ふろしき」って何 (OpenJLPT examples 2026-10-20)
                    pre = "(?<=[^" + _PUNCT.replace("」", "").replace("』", "") + "])"
                if stem_only:
                    polite = core.startswith("ま") or core == "なさい"
                    ends = _POLITE_STEM_END if polite else _STEM_END
                    if core == "なさい":
                        ends = ends.replace("に", "")      # 何になさいますか is なさる (honorific)
                    pre = "(?<=[" + ends + "])"           # … a verb stem,
                elif 0x4E00 <= ord(lits[0][0]) <= 0x9FFF and gid not in _NOUN_SUFFIX:
                    pre += "(?<![" + _KANJI + "])"        # … not the start of a compound (実際, 週末)
                if core in _NOT_AFTER:
                    na = _NOT_AFTER[core]
                    for x in (na if isinstance(na, tuple) else (na,)):
                        pre += "(?<!" + x + ")"     # a tuple: lookbehinds of other widths
                rx = pre + rx
            if core in _NOT_BEFORE:
                rx += "(?!" + _NOT_BEFORE[core] + ")"
            # Quick pre-check: the longest literal, unconjugated (minus its
            # last character, which may change).
            # The length test sees the part as _tail does, before a voiced て / た
            # is dropped (ていない's anchor was いな, never in ていません;
            # 2026-10-20: まだ来ていません was missed).
            longest = max(lits, key=len)
            anchor = longest
            if anchor.endswith(("する", "くる", "来る", "行く", "いく", "ます", "です")):
                anchor = anchor[:-2]
            elif anchor.endswith("ない") and len(anchor) >= 4:
                anchor = anchor[:-3]          # polite ません changes the stem (いけ / なり)
            elif len(anchor) > 1:
                anchor = anchor[:-1]
            anchor = anchor[1:] if longest[:1] in ("て", "た") else anchor
            out.append((gid, anchor, len(core), re.compile(rx)))
    _DETECTORS = out
    return out


def _search_part(lit: str, last: bool) -> str:
    """One literal of a pattern as a loose regex for Anki's search: て/た
    may be voiced, and the last part's ending may conjugate."""
    voiced = lit[:1] in ("て", "た") and lit not in _NO_VOICE
    head, lit = (lit[0], lit[1:]) if voiced else ("", lit)
    rx = re.escape(lit)
    if last and len(head + lit) >= 2:
        if lit.endswith("ない"):
            # and the polite negatives: いけない / いけません, 構わない /
            # 構いません, ならない / なりません, ことはない / ことはありません
            base = lit[:-2]
            a2i = dict(zip("わかがさたなばまらあ", "いきぎしちにびみりい"))
            alts = [base + "な", base + "ませ", base + "ありませ"]
            if base and base[-1] in a2i:
                alts.append(base[:-1] + a2i[base[-1]] + "ませ")
            rx = "(?:" + "|".join(re.escape(a) for a in alts) + ")"
        elif lit.endswith("だ") and len(lit) > 2:
            rx = re.escape(lit[:-1])          # はずだ → はず (also はずです, はずの)
        elif lit.endswith("だ"):
            rx = re.escape(lit[:-1]) + "(?:だ|で|じゃ)"
        else:
            for end, alt in (("する", "(?:す|し|さ|せ)"), ("くる", "(?:く|き|こ)"), ("来る", "来"),
                             ("ます", "ま[すしせ]"), ("です", "で[すし]")):
                if lit.endswith(end):
                    rx = re.escape(lit[:-len(end)]) + alt
                    break
            else:
                if lit[-1:] in tuple("うくぐすつぬぶむるい") and len(lit) > 1:
                    rx = re.escape(lit[:-1])
    if voiced:
        rx = "[" + head + {"て": "で", "た": "だ"}[head] + "]" + rx
    return rx


def search_regex(gid: str) -> str:
    """Every written form of a grammar point as one regex for Anki's
    Browser (re: search; Rust syntax, so no lookarounds): 〜 dropped, the
    variants (〜ことがある / 〜ことがない) OR-ed, conjugating endings left
    open. Finds more than the detection does, which is what hand marking
    needs: the user reads the sentences and decides."""
    alts = []
    for form in sorted(_forms(full_pattern(gid), True), key=len, reverse=True):
        lits = [x for x in form.split("〜") if x]
        if not lits:
            continue
        rx = ".{0,25}?".join(_search_part(x, i == len(lits) - 1) for i, x in enumerate(lits))
        if rx not in alts:
            alts.append(rx)
    return "|".join(alts)


_QUESTION_WORDS = ("何", "なに", "なん", "どんな", "いくら", "誰", "だれ", "どこ", "どう", "いつ",
                   "どれ", "どちら", "たとえ", "例え")


def _you_ga_you_to(text: str, m) -> str | None:
    """〜(よ)うが / 〜(よ)うと is concessive ("no matter what", N1) only with
    a comma or も after it (言われようが、 / あろうとも) or a question word
    earlier in the clause (何と言われようと). Otherwise ようと leads straight
    into the next action (握手をしようと手を差し出した, "about to / trying
    to") — 〜ようとする without the する — and ようが isn't the point at all."""
    after = text[m.end():m.end() + 1]
    clause = re.split(r"[、。！？!?,，]", text[:m.start()])[-1]
    # 何か / なんとか are "something / somehow", not questions (Gemini batch 1:
    # 何かを伝えようと, なんとかしようという気持ち)
    clause = re.sub("何か|なにか|なんとか|何とか|どうにか|どうか|誰か|だれか|どこか|いつか", "", clause)
    rest = text[m.end():]
    if re.match("[もは](?:しな|しま|せず|せぬ)", rest):
        return "you-to-suru"              # 助けようともしなかった (didn't even try)
    if after == "も":
        t, _start, _prev = _token_at(text, m.end())
        if t is not None and t[0] != "も":
            after = "x"                   # 出ようともみ合った: も of もみ合う
    # a question word already answered by its own ても (どんな犠牲を払っても…しようと
    # 決心した, sample 6) doesn't make this ようと concessive
    clause = re.sub("(?:" + "|".join(_QUESTION_WORDS) + ")[^、。]*?[てで]も", "", clause)
    # … or by an embedded question (誰が話してるのかを見ようと、: purpose; precision test 7)
    clause = re.sub("(?:" + "|".join(_QUESTION_WORDS) + ")[^、。]*?の?か[をがはもと]", "", clause)
    concessive_word = any(q in clause for q in _QUESTION_WORDS + ("いくら", "どんなに", "どれほど", "たとえ"))
    # straight into a quote / intention verb: どうしようと言うつもり, 何をしようと
    # いうんだ (quoted "let's"), どうしようとなさる (〜ようとする) (sample 6)
    # (+ は / も before a quote verb: しようとは思わなかった, 変えようとも考えた)
    if m.group().endswith("と") and (re.match("(?:言|いう|いっ|い[わえ]|思|考え|決|なさ|為さ|する|して|した)", rest)
                                     or re.match("[はも](?:言|いう|いっ|い[わえ]|思|考え)", rest)):
        return "you-to-suru" if re.match("(?:なさ|為さ|する|して|した)", rest) else None
    if m.group().endswith("と") and after in ("、", ",", "，") and not concessive_word:
        return "you-to-suru"              # 阻止しようと、…: purpose (recall/precision test)
    if after in ("", "、", ",", "，", "。", "！", "？", "!", "?", "も") or concessive_word:
        return "you-ga-you-to"
    if m.group().endswith("と") and re.search("^[^、。！？!?]*?(?:言|いっ|い[わうえ]|思|誘|提案|決|約束|叫|答|話|書|考)",
                                             rest) and not re.match("[しする]", rest):
        return None                       # 食事をしようと彼は私に言った: a quoted "let's" (recall test 5)
    return "you-to-suru" if m.group().endswith("と") else None


def _aida_ni(text: str, m) -> str | None:
    """〜間に "during" (その間に, 留守の間に), not (owner's review 2026-10-14):
    the verb 間に合う, the set phrases いつの間にか / 瞬く間に / あっという間に
    / 束の間, or the space between two things (AとBの間には)."""
    if text[m.end():m.end() + 1] in ("合", "あ"):
        return None
    before = text[:m.start()]
    if before.endswith(("いつの", "瞬く", "またたく", "あっという", "あっと言う", "束の", "つかの")):
        return None
    if re.search("と[^" + _PUNCT + "]{1,15}の$", before):
        return None
    # during: after a clause or a time noun (寝てる間に, 30分の間に, その間に), not
    # "between / among" (彼らの間に, 若者の間に; Gemini final)
    if before.endswith(("る", "た", "い", "その", "この", "あの")) or re.search(
            "(?:分|時|日|年|週|月|休み|夏|冬|春|秋|留守|食事|授業|旅行)の$", before):
        return "aida-aida-ni"
    return None


def _token_at(text: str, pos: int):
    """(token, its start, the token before it) of the parser's split at pos."""
    from .sentence_parser import tokens
    start, prev = 0, None
    for t in tokens(text):
        if start <= pos < start + len(t[0]):
            return t, start, prev
        prev = t
        start += len(t[0])
    return None, pos, prev


# Verb + 出す where 出す means "out" or the compound is its own word, not "start
# to …" (owner's review 2026-10-14). 走り出す, 言い出す, 飛び出す, 泣き出す stay.
_DASU_LEXICAL = ("つくり", "作り", "創り", "ほうり", "放り", "思い", "取り", "呼び", "差し", "引き", "生み", "抜け", "追い", "持ち", "貸し",
                 "押し", "見", "作り", "書き", "探し", "聞き", "導き", "編み", "打ち", "割り",
                 "映し", "吐き", "救い", "繰り", "突き", "張り", "搾り", "絞り", "選び", "送り",
                 "連れ", "誘い", "切り", "乗り", "見つけ", "掘り", "投げ", "締め", "放り",
                 "醸し", "炙り", "弾き", "洗い", "釣り", "這い", "せり", "はみ")


def _dasu(text: str, m) -> str | None:
    """〜出す "start to …": a verb stem + 出す, not 出す alone (それ出しといて)
    or a compound that is its own word (思い出す, 取り出す, 引き出し)."""
    t, start, prev = _token_at(text, m.start())
    if t is None:
        return None
    if start < m.start():                       # one word: 思い出した, 走り出す
        stem = t[0][:m.start() - start]
    elif prev is not None and prev[1] == "word" and (
            prev[4] is not None or (any(0x4E00 <= ord(c) <= 0x9FFF for c in prev[0])
                                    and prev[0][-1] in _STEM_END)):
        stem = prev[0]                          # 走り + 出した (走り may read as a noun)
    else:
        return None                             # それ出しといて
    if stem.endswith(_DASU_LEXICAL) or t[2] in ("引き出し", "出し"):
        return None
    return "dasu"


def _koto_ga_aru(text: str, m) -> str | None:
    """〜ことがある "sometimes" after a dictionary-form verb or ない
    (遅刻することがある), not こと as "a matter" (相談したいことがあります)."""
    before = text[:m.start()]
    if before.endswith(("いけない", "ならない", "られない", "れない")) or "もっと" in re.split("[、。！？]", before)[-1]:
        return None                       # しなくてはいけないこと, 忘れられないこと (Gemini final)
    if before and (before.endswith("ない") or (before[-1] in "うくぐすつぬぶむる" and not before.endswith("たる"))):
        return "koto-ga-aru"
    return None


def _o_suru(text: str, m) -> str | None:
    """お〜する humble, not お願いする (learnt as "please": お願いします)."""
    if m.group()[1:2] in ("願", "ね", "前") and not (m.group().startswith("お願") and re.search("(?:いた|致)[さしすせそ]$", m.group())) \
            or m.group().startswith("お辞儀"):   # お前料理できる (you); お願いいたします is humble (recall test 13)
        return None
    if m.group().endswith("さ") and text[m.end():m.end() + 1] == "れ":
        return None                     # ご出席される / お待ちされる: respectful, not humble
    return "o-suru"


def _ku_suru(text: str, m) -> str | None:
    """〜くする only on an i-adjective's く (明るくする, 早くして): the parser
    must read the word before する as that adjective, not なくす (なくして),
    尽くす, たくさん."""
    if m.group().startswith("に"):
        return "ku-suru-ni-suru"
    from .sentence_parser import lookup, kinds_of
    t, start, _prev = _token_at(text, m.start())
    if t is None or t[1] != "word" or start + len(t[0]) != m.start() + 1:
        return None
    if t[4] == "adj-i" and t[5] and t[5][0] == "く":
        return "ku-suru-ni-suru"
    # 早く / 仲良く are list words of their own (adverbs): fine when the
    # い-form is an i-adjective (早くしろ, 仲良くしなよ).
    w = lookup(t[0][:-1] + "い") if any(0x4E00 <= ord(c) <= 0x9FFF for c in t[0]) else None
    return "ku-suru-ni-suru" if w and "adj-i" in kinds_of(*w) else None


# 〜がする: a sound, smell, taste or feeling (音がする, 気がする).
_SENSES = ("音", "声", "匂い", "におい", "臭い", "香り", "味", "予感", "気", "寒気", "感じ",
           "気配", "動悸", "吐き気", "頭痛", "めまい", "目眩", "痛み", "心地", "感触", "悪寒",
           "気分", "響き", "風味", "臭", "匂")


def _ga_suru(text: str, m) -> str | None:
    return "ga-suru" if text[:m.start()].endswith(_SENSES) else None


def _naide(text: str, m) -> str | None:
    """〜ないで "without doing" linking to a next verb (傘を持たないで出かけた),
    not ではないであろう, nor a sentence-final request (言わないで。/ 言わない
    でくれ: the request itself, 〜ないでください's casual form)."""
    if text[:m.start()].endswith(("では", "じゃ", "つ")):
        return None                       # つないで (connect)
    after = text[m.end():].lstrip(" 　")
    if not after or after[0] in "。！？!?…―」』)）" or after.startswith(
            ("くれ", "ください", "下さい", "ちょうだい", "ほしい", "欲しい", "もらえ", "ね", "よ", "な")):
        return None
    return "naide"


# ── owner's review round 3 (N3–N1, 2026-10-14) ────────────────────────────────
_SENT_END = "。！？!?"


def _after(text: str, m) -> str:
    return text[m.end():]


def _before(text: str, m) -> str:
    return text[:m.start()]


def _clause_after(text: str, m) -> str:
    """Text after the match up to the end of its clause (punctuation or a
    space: the owner's subtitle sentences use spaces between lines)."""
    return re.split("[" + _PUNCT + "]", _after(text, m), maxsplit=1)[0]


def _ends_clause(rest: str) -> bool:
    """Nothing but sentence-final particles before the clause ends."""
    return bool(re.match("(?:よ|ね|な|わ|ぞ|さ|か|の|ん)*(?:[" + _PUNCT + "]|$)", rest))


def _mono_dakara(text: str, m) -> str | None:
    """Not もの "thing" + だから in "not A but B" (与えられるものではなく
    獲得するものだから)."""
    if m.group().endswith("で") and _after(text, m)[:1] in ("は", "も", "あ"):
        return None                       # ものではない / ものでもない / ものである (Gemini batch 7)
    return None if re.search("もの(?:では|じゃ)なく", _before(text, m)) else "mono-dakara-mono-de"


def _mono_de_wa_nai(text: str, m) -> str | None:
    """"One shouldn't", not the contrast ものではなく、〜 (not A but B)."""
    if m.group().endswith("く"):
        return None
    # 満足のいくものではない / 大したものではない: もの "a thing" (Gemini batch 7)
    if _before(text, m).endswith(("満足のいく", "満足いく", "満足行く", "大した")):
        return None
    if _before(text, m)[-1:] not in "うくぐすつぬぶむるただ":
        return None                       # そんなものじゃない (a thing): a verb (dict / た) before もの
    return "mono-de-wa-nai"


def _koto_da(text: str, m) -> str | None:
    """Advice: Verb-dict / ない + ことだ ending the sentence (毎日練習する
    ことだ). Not なこと / のこと (自然なことです, とのことです, 頃のこと)
    nor "X は … ことです" (私の夢は先生になることです)."""
    before = _before(text, m)
    if not before or not (before.endswith("ない") or (before[-1] in "うくぐすつぬぶむる" and not before.endswith("たる"))):
        return None
    # よくあることだ, 起こりうることだ, ということだ, 関係ないことだ (a matter,
    # not advice; Gemini final)
    if before.endswith(("ある", "うる", "いう", "言う", "関係ない", "関係のない", "できない")):
        return None
    if not _ends_clause(_after(text, m)):
        return None
    sentence = re.split("[" + _SENT_END + "]", before)[-1]
    from .sentence_parser import tokens
    if any(t[0] == "は" and t[1] == "func" for t in tokens(sentence)):
        return None
    return "koto-da"


def _koto_wa_nai(text: str, m) -> str | None:
    """No need to (心配することはない), not the past fact ことはなかった."""
    if text[m.end() - 1:m.end() + 1] == "かっ":
        return None
    before = _before(text, m)
    if before.endswith(("大した", "たいした")):
        return None                       # 大したことはない (no big deal)
    if "ほど" in re.split("[。！？]", before)[-1]:
        return "hodo-wa-nai"              # 〜ほどうれしいことはない (Gemini final)
    if before.endswith(("過ぎる", "すぎる", "される", "られる", "なる")):
        return None                       # してもし過ぎることはない, 解雇されることはない
    # "No need to" talks to the listener; a third-person topic with no よ / ね /
    # です after it is "never" (彼は…気を落とすことはない).
    sentence = re.split("[。！？]", before)[-1]
    if re.search("(?:彼|彼女|彼ら)は", sentence) and not _after(text, m).startswith(("よ", "ね", "です", "さ", "わ", "って")):
        return None
    return "koto-wa-nai"


def _ni_tsuite(text: str, m) -> str | None:
    """About X, not ついていく / ついてる (keep up, be attached) or the race
    call 位置について."""
    if _before(text, m).endswith(("位置", "あと", "後")):
        return None                       # 私のあとについて読みなさい (follow)
    if _after(text, m).startswith(("読", "来", "き", "こ", "行", "ゆ", "歩", "走")):
        return None                       # 私について読みなさい / ついて来て (follow)
    if _after(text, m).startswith(("いけ", "いく", "いき", "いっ", "いか", "いこ", "いる", "いた",
                                   "いて", "いま", "いな", "る", "た", "ない", "ます", "ました")):
        return None
    return "ni-tsuite"


def _you_na(text: str, m) -> str | None:
    """Like X (鬼のような人), not the conjecture ようなんだ / ようなのだ."""
    if _before(text, m).endswith(("どの", "その", "この", "あの", "さ")):
        return None                       # どのような, そのように, さようなら (Gemini final)
    if _after(text, m).startswith("ら"):
        return "you-da"                   # 咳が出るようなら (if it seems so; precision test 6)
    return None if _after(text, m).startswith(("ん", "の")) else "you-na-you-ni-like"


def _to_shite(text: str, m) -> str | None:
    before = _before(text, m)
    if before.endswith(("ひょっ", "ヒョッ")):
        return None
    if re.search("(?:^|[" + _PUNCT + "])時$", before) and _after(text, m)[:1] in ("、", ",", "，", "は"):
        return None                       # 時として、 (sometimes; precision test 6); 当時として stays
    return "to-shite"


def _tara_ta(text: str, m) -> str | None:
    """〜たら … past: the clause's last predicate must be past (窓を開けたら
    雪が降っていた), not the future/hypothetical (言われたら … 湧くかな)."""
    start = m.start() + text[m.start():].find("ら") + 1
    if text[start:].startswith(("いい", "よい", "良い", "よかろ", "どう")):
        return None                       # どうしたらよいか困った (Gemini final)
    # to the end of the sentence (spaces in subtitles don't end it: 店に入った
    # ら全裸祭りだったから 驚いて逃げたんです)
    sentence = re.split("[" + _SENT_END + "]", text[start:], maxsplit=1)[0]
    sentence = sentence.rstrip(" 　…―」』)）⸺~〜ー")
    if re.search("(?:た|だ)(?:んだ|のだ|のよ|んです|のです|よ|ね|わ|な|ぞ|さ|の|っけ)*$", sentence):
        return "tara-ta"
    return None


_QUOTE_AFTER = ("聞", "言", "いう", "いっ", "思", "顔", "こと", "話", "噂", "有名", "感じ", "知",
                "書", "教", "わけ", "マジ", "まじ", "本当", "ほんと")


def _tatte_datte(text: str, m) -> str | None:
    """Even if (泣いたって始まらない, 子供だって分かる), not hearsay
    (来るんだって, 男なんだって) or a quote (地獄だって聞いてた, ホッとした
    って顔)."""
    before, after = _before(text, m), _after(text, m)
    if before.endswith(("ん", "の")):
        # …but a verb's own past form (読んだって, 泳いだって) is "even if":
        # only a separate explanatory ん (来るんだって) is hearsay.
        t, _s, _p = _token_at(text, m.start())
        own_past = (t is not None and t[1] == "word" and t[0].endswith(("んだ", "いだ"))
                    and t[2] not in (None, t[0]))
        if not own_past:
            return None
    if _ends_clause(after) or after.startswith(_QUOTE_AFTER):
        return None
    if re.match("[^、。]{0,8}?(?:聞|言っ|いっ)", after):
        return None                       # 離れたってトムから聞いた (Gemini final)
    return "tatte-datte"


def _ba_ii(text: str, m) -> str | None:
    """ばいい, not なければいけない (ば + いけ)."""
    return "ba-ii" if m.group().endswith("いい") else None


_MUKI_LEXICAL = ("暮らし", "暮し", "前", "後ろ", "上", "下", "横", "外", "内", "表", "裏", "真", "東", "西", "南", "北",
                 "風", "振り", "仰", "方", "下", "左", "右")


def _muki_muke(text: str, m) -> str | None:
    """Noun + 向け / 向き "aimed at, suited to" (子供向け), not the verb
    向ける (目を向けた) nor a direction (前向き, 風向き)."""
    before = _before(text, m)
    if not before or before[-1] in "をにがはもへのと" or before.endswith(_MUKI_LEXICAL):
        return None
    if m.group().endswith("け") and _after(text, m)[:1] in ("た", "て", "る", "ら", "ま", "ず", "よ", "な", "れ", "ろ"):
        return None
    return "muki-muke"


_KIRU_LEXICAL = ("擦り", "すり", "締め", "しめ", "張り", "はり", "区", "仕", "踏み", "貸し", "打ち", "割り", "思い",
                 "押し", "振り", "裏", "句", "見")


def _kiru(text: str, m) -> str | None:
    """Verb-stem + 切る "completely" (売り切る), not 締め切り, 張り切る,
    思い切り …, nor 切り at the front of a compound (切り落とす)."""
    before = _before(text, m)
    if before.endswith(_KIRU_LEXICAL) or not before or before.endswith(("だけ", "を", "が", "は", "も", "て", "で")):
        return None                       # 切れやしない, 少しだけ切って: the verb 切る alone
    after = text[m.start() + 1:]
    if after.startswith("り") and after[1:2] and 0x4E00 <= ord(after[1]) <= 0x9FFF:
        return None
    return "kiru-kirenai"


_KAKERU_LEXICAL = ("話し", "はなし", "呼び", "問い", "見", "出", "で", "押し", "追い", "働き",
                   "振り", "投げ", "詰め", "引っ", "持ち", "誘い", "笑い", "語り", "吹き", "見せ",
                   "腰", "差し", "仕", "畳み", "攻め", "取り", "手掛", "手が",
                   "こし", "もたせ", "けし", "掛け", "をし", "立て", "たて")   # + Gemini batch 8; 立てかける (lean against; recall test 10)


def _kakeru(text: str, m) -> str | None:
    """Half-done / about to (読みかけ, 死にかける), not 話しかける, 呼び
    かける, 追いかける …"""
    return None if _before(text, m).endswith(_KAKERU_LEXICAL) else "kakeru"


_AU_LEXICAL = ("知り", "付き", "つき", "待ち", "組み", "落ち", "釣り", "問い", "申し", "詰め",
               "盛り", "折り", "隣り", "巡り", "めぐり", "似", "見", "割り", "触れ", "居", "請け",
               "持ち", "埋め", "掛け", "乗り")   # 持ち合わせる, 埋め合わせ (accuracy test 3)


def _au(text: str, m) -> str | None:
    """Doing to each other (話し合う, 向き合う), not 知り合い, 付き合う,
    待ち合わせ, 組み合わせ …"""
    before = _before(text, m)
    if before.endswith(_AU_LEXICAL) or not before or before[-1] not in _STEM_END or re.search("っ.り$", before):
        return None                       # ぴったり合う: the verb 合う alone (Gemini final)
    return "au"


def _wo_tooshite(text: str, m) -> str | None:
    """Through / via (友人を通して), not threading (針に糸を通して)."""
    before = _before(text, m)
    if before.endswith(("糸", "袖", "腕", "紐", "ひも", "針", "穴", "鼻", "耳", "主義", "意地", "我", "目")):   # 目を通す (sample 9)
        return None
    return "o-tsuujite-o-tooshite"


def _ni_kagiru(text: str, m) -> str | None:
    """"Nothing beats X" (夏はビールに限る), not the polite limit (週末に
    限ります) nor a time limit."""
    if not m.group().endswith("る"):          # 限らず, 限り …
        # … but polite 限ります is "nothing beats" too (旅は若いうちにかぎります),
        # unless a person / group is being limited (応募は女性に限ります).
        if not _after(text, m).startswith("ます"):
            return None
        if _limits_group(text, m):
            return None
    if _before(text, m).endswith(_TIME_END) or _before(text, m).endswith(("末", "期間", "本日", "今日")):
        return None
    if _after(text, m).startswith(("と規定", "とする", "とされ")):
        return None                       # 女性に限ると規定されている (a rule, Gemini batch 5)
    return "ni-kagiru"


def _limits_group(text: str, m) -> bool:
    """に限る / に限ります limiting who qualifies (応募は女性に限ります,
    参加者は会員に限ります): a person or group before に."""
    _t, _s, prev = _token_at(text, m.start())
    return bool(_person(prev) or _before(text, m).endswith(
        _GROUP_END + ("女性", "男性", "会員", "大人", "以上", "以下", "名様")))


def _ni_kagiri(text: str, m) -> str | None:
    """Limited to (本日に限り、女性に限り), and the polite 限ります when it
    limits who qualifies (参加者は会員に限ります: "limited to members";
    owner's recall audit 2026-10-17); otherwise 限ります is に限る's
    "nothing beats" (旅は若いうちにかぎります)."""
    if _after(text, m).startswith("ま"):
        return "ni-kagiri" if _after(text, m).startswith("ます") and _limits_group(text, m) else None
    return "ni-kagiri"


_GROUP_END = ("者", "側", "達", "たち", "ら", "親", "人", "家族", "会社", "政府", "国", "店", "客",
              "社員", "生徒", "学生", "子供", "子ども", "方")


def _ni_sureba(text: str, m) -> str | None:
    """From X's standpoint (親にしたら): a person or group before it, not
    the plain conditional of にする (野放しにしたら, 大切にしたら)."""
    _t, _s, prev = _token_at(text, m.start())
    if _after(text, m).startswith(("いい", "良い", "よい")):
        return None                       # 誰にしたらいいかしら (which to choose, Gemini batch 5)
    if _person(prev) or _before(text, m).endswith(_GROUP_END):
        return "ni-sureba-ni-shitara"
    return None


_PHYSICAL_AIM = ("的", "東", "西", "南", "北", "方", "方向", "空", "天", "地面", "海", "山", "前", "後ろ",
                 "外", "窓", "ドア", "扉", "壁", "顔", "胸", "頭", "口", "上", "下", "こちら", "こっち",
                 "そっち", "あっち", "敵", "標的", "犯人", "背中")


def _ni_mukete(text: str, m) -> str | None:
    """Toward a goal / event / audience (体育祭に向けて), not aiming at a
    thing or direction (的に向けて矢を放った)."""
    return None if _before(text, m).endswith(_PHYSICAL_AIM) else "ni-mukete"


_NAGARA_NOUNS = ("涙", "居", "い", "昔", "生まれ", "生れ", "うまれ", "いつも", "今更", "今さら")
# noun + ながら that isn't "although": 陰ながら (secretly), さながら (just like)
_NAGARA_NOT_CONCESSIVE = ("陰", "かげ", "さ", "然")


def _nagara_ni(text: str, m) -> str | None:
    """The fixed set (涙ながらに, 居ながらにして, 昔ながらの, 生まれながらの),
    not concessive ながら (僅かながら)."""
    return "nagara-ni-nagara-no" if _before(text, m).endswith(_NAGARA_NOUNS) else None


def _mitai(text: str, m) -> str | None:
    """〜みたい "like / seems" after a noun or plain form (悪魔みたい,
    降ったみたい), not たい on a verb (owner's review 2026-10-14): 住みたい,
    楽しみたい (み is the verb's own stem: the parser reads one token) and
    〜てみたい (会ってみたい: みる after a て-form)."""
    from .sentence_parser import tokens
    pos = 0
    prev = None
    for t in tokens(text):
        end = pos + len(t[0])
        if pos <= m.start() < end:
            if pos < m.start():
                return None                       # み inside a word: 住みたい
            if prev is not None and prev[1] == "word" and prev[0].endswith(("て", "で")) \
                    and prev[4] is not None:
                return None                       # 会ってみたい
            return "mitai"
        prev = t
        pos = end
    return "mitai"


# Points whose regex match needs a look at the context: id → fn(text, match)
# returning the id to credit (maybe another point's) or None.
# ── Gemini review, batches 1–3 (2026-10-14; each verdict checked against the
# sentences first, see docs/HISTORY.md) ───────────────────────────────────────

def _tara_saigo(text: str, m) -> str | None:
    """たら最後 / たが最後 ("once you…, that's it"), not が subject + 最後
    (彼が最後に勝利を得た, これが最後だ)."""
    if m.group().startswith("が") and not _before(text, m).endswith(("た", "だ")):
        return None
    return "tara-saigo-ga-saigo"


def _tomo_naru(text: str, m) -> str | None:
    """Not 「AともなればBともなる」 (becomes A or B: 地獄ともなれば天国ともなる)."""
    return None if "ともなる" in _after(text, m) else "tomo-naru-to-tomo-nareba"


def _you_ni_mo_nai(text: str, m) -> str | None:
    """動こうにも動けない, not どうにもならない nor ように + もっと."""
    if _before(text, m).endswith("ど") or "にもっ" in m.group():
        return None
    return "you-ni-mo-nai"


def _nari_nari(text: str, m) -> str | None:
    """煮るなり焼くなり (either … or), not お亡くなりになり nor the classical
    copula ending a sentence (彼も人なり我も人なり)."""
    rest = _after(text, m)
    if m.group().startswith("なりに") or rest == "" or rest[0] in _SENT_END:
        return None
    t, _s, _p = _token_at(text, m.start() - 1)
    if _before(text, m).endswith("に") or t is not None and t[4] == "adj-i" and t[5] == ("く",):
        return None                       # 長くなり…短くなり / 医者になり: the verb なる (sample 11)
    return "nari-nari"


def _ni_atte(text: str, m) -> str | None:
    """In a position / time (時代にあって、, 死にあっても), not 会う / 遭う / ある
    (彼にあっていない, 雨にあって, 近くにあって良かった)."""
    if _before(text, m).endswith(("中", "上", "下", "近く", "そば", "前", "後ろ", "奥", "所", "ところ", "外", "内")):
        return None                       # 森の中にあって (is in the forest)
    return "ni-atte" if _after(text, m)[:1] in ("、", ",", "，", "も", "は") else None


def _made_da(text: str, m) -> str | None:
    """した(までだ) "I only did …", not a time limit (５時までです)."""
    if _before(text, m).endswith(tuple("たるうくすつぬむぶぐだ")):
        return "made-da-made-no-koto-da"
    return None


def _o_oite(text: str, m) -> str | None:
    """彼をおいて他にいない / この町をおいてふさわしい場所はない ("no one /
    nowhere but"): 他 next, or a negative later in the sentence. Not the verb
    置く (ペンをおいて椅子にもたれた, 車をおいておきたい)."""
    rest = _after(text, m)
    if rest.startswith(("他", "ほか")):
        return "o-oite"
    if rest[:1] not in ("い", "お") and re.search("な[いか]|ありません|ありませ", rest):
        return "o-oite"
    return None


def _tada_nomi(text: str, m) -> str | None:
    """Not ただ inside いただく (ご同意いただいたお客様のみ)."""
    return None if _before(text, m).endswith("い") else "tada-nomi"


def _kare_kare(text: str, m) -> str | None:
    """遅かれ早かれ, not a verb's かれる (はじかれるように聞かれた)."""
    return None if text[m.start() + 2:m.start() + 3] in tuple("るてたまずよ") else "kare-kare"


def _kaneru(text: str, m) -> str | None:
    """かねません is polite かねない ("might well"), its own point."""
    if m.group().endswith(("ない", "なか")) or _after(text, m).startswith(("せん", "ません")):
        return "kanenai"
    return "kaneru"


def _te_wa_irarenai(text: str, m) -> str | None:
    """〜ないではいられない is 〜ずにはいられない's other form ("can't help")."""
    return "zu-ni-wa-irarenai" if _before(text, m).endswith("ない") else "te-wa-irarenai"


def _mono_ka(text: str, m) -> str | None:
    """The "no way!" ものか (知るものか), not a question about a thing:
    ものかどうか, どうしたものか, どんなものか, いかがなものか."""
    if _after(text, m).startswith("どうか") or _before(text, m).endswith(("な", "どうした")):
        return None
    # a question word in the clause + more of the sentence after it is an
    # embedded "how / what …" (どうしたらそんなミスを犯したものか考えもつかない;
    # precision test 6), not "no way"
    clause = re.split("[、。！？!?]", _before(text, m))[-1]
    if re.search("どう|なぜ|何故|何|なに|いかに|どこ|誰|だれ", clause) and _after(text, m)[:1] not in ("", "。", "！", "？", "!", "?", "」", "、"):
        return None
    return "mono-ka"


def _mono_no(text: str, m) -> str | None:
    """"Although" ものの needs a clause break after it (いるものの、); without
    one it's もの "thing" + の (深いものの一つ, あらゆるものの値段)."""
    return "mono-no" if _after(text, m)[:1] in ("、", ",", "，") else None


# ── Gemini review, batches 4–9 (2026-10-14; each verdict checked first) ──────

_E_RU = tuple(c + "る" for c in "えけげせぜてでねべめれ")
_VERB_END = tuple("るうくすつぬむぶぐ")


def _mono_nara(text: str, m) -> str | None:
    """"If (you) could" after a potential verb (解けるものなら), not もの
    "thing" + なら (甘いものなら何でも)."""
    return "mono-nara" if _before(text, m).endswith(_E_RU + ("できる", "られる")) else None


def _mono_ga_aru(text: str, m) -> str | None:
    """"There's something … about it" after a plain verb or adjective
    (光るものがあった, つらいものがある), not a thing one wants or a question
    (欲しいものがある, 買いたいものがある, 何か新しいものがある, どんなものが)."""
    before = _before(text, m)
    if not before.endswith(_VERB_END + ("い",)) or before.endswith(("たい", "欲しい", "ほしい")):
        return None
    clause = re.split("[、。！？]", before)[-1]
    return None if re.search("何か|なにか|どんな|どれ|何の", clause) else "mono-ga-aru"


def _koto_ka(text: str, m) -> str | None:
    """Exclamation (何と早いことか): needs 何と / どれほど … earlier, not
    a question about a matter (何のことか, ってことか)."""
    if re.search("何と|なんと|どれほど|どれだけ|どんなに|いかに|何度|何回", _before(text, m)):
        return "koto-ka"
    return None


def _koto_ni_wa(text: str, m) -> str | None:
    """驚いたことに、/ 残念なことには、 (emotion, then a comma), not こと +
    に (気が付く, 慣れる, 決める …)."""
    if _before(text, m).endswith("ま"):
        return None                       # まことに、 (誠に: truly; sample 10)
    rest = _after(text, m)
    if m.group().endswith("に") and rest.startswith("は"):
        rest = rest[1:]
    return "koto-ni-wa" if rest[:1] in ("、", ",", "，") else None


def _koto_dakara(text: str, m) -> str | None:
    """Knowing X (トムのことだから): a person before の, not a matter
    (急を要することだから, 2018年のことだから)."""
    before = _before(text, m)
    if not before.endswith("の"):
        return None
    _t, _s, prev = _token_at(text, m.start() - 1)
    who = before[:-1]                     # 彼の is one token (かの): look at the text
    if _person(prev) or who.endswith(tuple(_PERSON) + _GROUP_END + (
            "さん", "くん", "君", "ちゃん", "様", "先生", "子", "奴", "やつ", "あいつ", "こいつ")) \
            or re.search("[ァ-ヶー]{2,}の$", before):
        return "koto-dakara"
    return None


def _koto_naku(text: str, m) -> str | None:
    """Without doing, not 〜たことなかった nor どことなく."""
    if m.group().endswith("なか") or _before(text, m).endswith("ど"):
        return None
    return "koto-naku"


def _koto_wa_ga(text: str, m) -> str | None:
    """Echo concession (行くことは行くが): the word after ことは repeats the
    one before it; otherwise こと + は + something else."""
    after = text[m.start() + 3:]          # what follows ことは
    return "koto-wa-ga" if after[:1] and after[0] in _before(text, m)[-4:] else None


def _ijou_wa(text: str, m) -> str | None:
    """Since / now that after a plain form (約束した以上は), not a number
    (３００エーカー以上, 一つ以上), これ以上 nor 以上です (that's all)."""
    before = _before(text, m)
    if _after(text, m).startswith(("です", "の", "に")) or not before.endswith(tuple("たるうくすつぬむぶぐいだ")):
        return None                       # + 欲しがる以上のもの (more than; recall test 10)
    if re.search("[0-9０-９" + _NUM + "]つ$", before) or before.endswith(("これ", "それ", "あれ")):
        return None
    return "ijou-wa"


_NUKU_LEXICAL = ("通り", "引き", "切り", "ぶち", "追い", "すり", "出し", "見", "書き", "選り", "こそぎ",   # 根こそぎ抜け (sample 9)
                 "まで", "でも", "では")   # 彼まで抜けると (the verb 抜ける; precision test 7)


def _nuku(text: str, m) -> str | None:
    """Through to the end (やり抜く, 生き抜く), not lexical compounds
    (通り抜ける, 引き抜く, 抜け出す)."""
    if _before(text, m).endswith(_NUKU_LEXICAL):
        return None
    if m.group().startswith("抜け") and _after(text, m).startswith("出"):
        return None
    if m.group().startswith("抜か") and _after(text, m).startswith(("さ", "し", "す", "せ", "そ")):
        return None                       # 抜かす (overtake): 抜かされそう
    return "nuku"


def _uru_enai(text: str, m) -> str | None:
    """A verb stem + 得る (あり得ない), not the verb 得る "obtain"
    (只で得られる, 賃金として得た)."""
    before = _before(text, m)
    if not before or before.endswith(("て", "で", "により")) or before[-1] not in _STEM_END:
        return None                       # + 実施により得た成果 (sample 9)
    return None if m.group().startswith("得ら") else "uru-enai"


def _te_naranai(text: str, m) -> str | None:
    """Can't help feeling (気がしてならない), not 聞き捨てならない nor
    忘れて(は)ならない (must not)."""
    return None if _before(text, m).endswith(("捨", "忘れ")) else "te-naranai"


def _ni_shiro(text: str, m) -> str | None:
    """Whether / even if (いずれにせよ、), not a command ending the sentence
    (親切にせよ。自由にしろ！) nor the adverb なにしろ."""
    rest = _after(text, m)
    if rest == "" or rest[0] in _SENT_END + "！!" or rest.startswith("と") or _before(text, m).endswith("な"):
        return None                       # 明確にせよと (a quoted command)
    return "ni-shiro-ni-seyo"


def _ni_atatte(text: str, m) -> str | None:
    """On the occasion of (決定にあたって), not 当たる (任務にあたっている,
    光が当たっていた, ガイドにあたってください, 任にあたって貰う)."""
    return None if _after(text, m).startswith(("い", "く", "貰", "もら", "お")) else "ni-atatte"


def _naosu(text: str, m) -> str | None:
    """Re-do after a verb stem (考え直す), not the verb 直す alone (これ直して)."""
    before = _before(text, m)
    if not before or before.endswith(("これ", "それ", "あれ", "を", "が", "は", "も")):
        return None
    return "naosu"


def _hodo_wa_nai(text: str, m) -> str | None:
    """"Nothing is as … as" (これほど心地よいことはない), not "not as … as"
    (それほど難しくはない, 大家族ではない)."""
    g = m.group()
    i = g.rfind("は")
    return None if i > 0 and g[i - 1] in ("で", "く") else "hodo-wa-nai"


def _tokoro_datta(text: str, m) -> str | None:
    """Almost (溺死するところだった), not "was in the middle of" (お茶を入れて
    いるところだった)."""
    return None if _before(text, m).endswith(("ている", "でいる", "ていた", "でいた")) else "tokoro-datta"


def _nanka(text: str, m) -> str | None:
    """X なんか / なんて (車なんかいらない), not the exclamation なんて速く
    at the start of a clause."""
    before = _before(text, m)
    if before.endswith(("たら", "だら", "けど", "けれど")):
        return None                       # 食べたらなんかお腹痛くなる: filler "somehow"
    return None if not before or before[-1] in "はがも、, 　" else "nanka-nante"


_RAISE_NOUNS = ("声", "ぼこり", "埃", "煙", "悲鳴", "手", "顔", "腰", "スピード", "速度", "成果",
                "利益", "効果", "名", "歓声", "叫び", "炎", "火", "湯気", "しぶき", "水しぶき")


def _ageru(text: str, m) -> str | None:
    """Giving (手紙をあげた), not 上げる "raise" (大声をあげた, 砂ぼこりをあげて)."""
    before = _before(text, m)
    if m.group().startswith("くれ") and before.endswith(("途方に", "日が", "暮", "ひね", "明け", "あけ")):
        return None                       # 途方にくれる (be at a loss), 日がくれる
    if m.group().startswith("あげ") and re.search(
            "(?:" + "|".join(_RAISE_NOUNS) + ")を[^、。！？]{0,8}$", before):
        return None                       # 砂ぼこりをもうもうとあげて
    return "ageru-kureru-morau"


def _te_aru(text: str, m) -> str | None:
    """Not a て-form + あたり / あなた (消えてあたりは, すべてあなたに)."""
    return None if m.group().endswith(("あた", "あな")) else "te-aru"


def _mono_da(text: str, m) -> str | None:
    """General truth / past habit / exclamation, not もの "a thing" after a
    な-adjective or ていた (一時的なものでしかない, 求めていたものです)."""
    before = _before(text, m)
    if before.endswith("な") and not before.endswith("ような"):
        return None
    if re.search("[0-9０-９" + _NUM + "](?:年|日|月|週|時間)$", before):
        return None                       # 2年ものだ (a two-year-old one)
    if before.endswith(("ていた", "でいた")):
        return None
    # "used to" (外出したものです) comes with a time clue; without one, た + もの
    # is "a … thing" (筋の通ったものだ)
    if before.endswith(("た", "だ")) and not re.search(
            "よく|昔|以前|頃|ころ|時代|子供の時|子どもの時|若い時|小さい時|しばしば|いつも|毎日|毎晩|毎週",
            re.split("[。！？]", before)[-1]):
        return None
    return "mono-da"


def _koto_ni_natte_iru(text: str, m) -> str | None:
    """An arrangement after a plain verb (会うことになっている), not 困った
    ことになっている (has got into trouble)."""
    return None if _before(text, m).endswith("た") else "koto-ni-natte-iru"


def _ippou_de(text: str, m) -> str | None:
    """一方で(ある) at the end is 〜一方だ (keeps increasing)."""
    return "ippou-da" if _after(text, m).startswith("あ") else "ippou-de"


def _mo_ba_mo(text: str, m) -> str | None:
    """AもあればBも: the first も is a particle, ば follows れ / け, and the
    last も isn't part of もの / かも (おもしろければ, 言うものだ, できるかも)."""
    g = m.group()
    t, _s, _prev = _token_at(text, m.start())
    if t is None or t[0] not in ("も", "でも"):
        return None
    i = g.find("ば")
    if i < 1 or g[i - 1] not in ("れ", "け"):
        return None
    if _after(text, m).startswith("の") or g[-2:-1] == "か":
        return None
    return "mo-ba-mo"


def _ki_ga_suru(text: str, m) -> str | None:
    """A feeling / hunch, not "don't feel like doing" (勉強する気がしない)."""
    if _after(text, m).startswith("な") and _before(text, m).endswith("る"):
        return None
    return "ki-ga-suru"


def _uchi_ni(text: str, m) -> str | None:
    """While (若いうちに), not そのうちに (sooner or later) nor a span of time
    (一ヶ月のうちに)."""
    before = _before(text, m)
    if not before or before[-1] in "はもがをに、,。 　" or before.endswith(("私の", "僕の", "俺の", "君の", "彼の", "家の")):
        return None                       # 一度はうちに泊まりに (home), 私のうちに
    if before.endswith("その") or re.search("[0-9０-９" + _NUM + "]+(?:ヶ月|か月|カ月|年|日|週間|時間|分)の$", before):
        return None
    return "uchi-ni"


def _tokoro_ni(text: str, m) -> str | None:
    """Just as / in the middle of (盗んでいるところを捕まった), not a place
    or a point (住むところを探す, そんなところへ, 遠いところに)."""
    if not _before(text, m).endswith(("ている", "でいる", "た", "だ")):
        return None
    if re.match("[^、。]{0,6}?(?:聞|探|知|教|尋|訪)", _after(text, m)):
        return None                       # 住んでいるところを聞いた (where he lives)
    if m.group().endswith("に") and re.match("[^、。]{0,4}?(?:立|ある|あり|あっ|いる|い|住|座|置)", _after(text, m)):
        return None                       # 離れたところに立っている (a place)
    return "tokoro-ni-tokoro-e-tokoro-o"


def _wake_da(text: str, m) -> str | None:
    """わけじゃない / わけではない is its own point (not necessarily)."""
    if m.group().endswith("じゃ") or _after(text, m).startswith(("じゃ", "では")):
        return "wake-de-wa-nai"
    return "wake-da"


def _dake_ni(text: str, m) -> str | None:
    """だけに "all the more because" comes before a comma (再開だけに、);
    otherwise it's だけ "only" + に (子供たちだけにしておく)."""
    if m.group().endswith("だけに") and _after(text, m)[:1] not in ("、", ",", "，"):
        return None
    return "dake-atte-dake-ni"


def _ka_to_omottara(text: str, m) -> str | None:
    """No sooner than, after a past verb (光ったかと思うと), not "I thought it
    was X" (無料バスかと思ったら) nor "when I think" (アラサーかと思うと)."""
    return "ka-to-omottara-ka-to-omou-to" if _before(text, m).endswith(("た", "だ")) else None


def _serareru(text: str, m) -> str | None:
    """Made to (させられた / 書かせられた), not the passive of a する-verb
    (処せられた, 課せられた, 魅せられた) nor 見せられない (can't show)."""
    if _after(text, m).startswith("な") or m.group().endswith(("な", "ない", "なか")):
        return None                       # 終わらせられない (can't make it finish)
    if m.group().startswith("させ"):
        return "serareru-saserareru"
    before = _before(text, m)
    return "serareru-saserareru" if before and before[-1] in "かさたなまらわがばぱ" else None


def _tagaru(text: str, m) -> str | None:
    """Wants to (会いたがっている), not したがって (therefore) nor した + が."""
    before, after = _before(text, m), _after(text, m)
    if m.group().endswith("ま") and after.startswith("っ"):
        return None                       # したがまったく
    if re.search("(?:^|[、。！？ 　])し$", before) and m.group().endswith("っ") and after.startswith("て"):
        return None                       # したがって、 (therefore)
    return "tagaru"


# ── Gemini review, batches 10–13 (2026-10-14; each verdict checked first) ────

def _bakari(text: str, m) -> str | None:
    """Only / nothing but (ことばかり言う), not 〜とばかり(に) "as if to say"."""
    before = _before(text, m)
    return None if before.endswith("と") and not before.endswith("こと") else "bakari"


def _o_ni_naru(text: str, m) -> str | None:
    """Honorific お〜になる, not お世話になる (be in someone's care)."""
    return None if m.group().startswith("お世話") else "o-ni-naru"


def _mae_ni(text: str, m) -> str | None:
    """Before doing / before N (出かける前に, 晩ご飯の前に), not "ago"
    (ずっと前に, ３年前に)."""
    before = _before(text, m)
    if before.endswith(("ずっと", "もっと", "少し", "ちょっと", "すこし", "直")) or \
            re.search("[0-9０-９" + _NUM + "](?:年|日|週間|か月|ヶ月|カ月|時間|分|秒)$", before):
        return None
    return "mae-ni"


def _ato_de(text: str, m) -> str | None:
    """After doing / after N (終えた後で, 散歩の後で), not the adverb 後で
    "later" (じゃあ、また後で)."""
    before = _before(text, m)
    return "ato-de" if before.endswith(("た", "だ", "の")) and not before.endswith("また") else None


_VERB_TYPES = ("v1", "v5", "v5-iku", "vk", "vs", "vsn")


def _ku_nai(text: str, m) -> str | None:
    """An i-adjective's くない / かった, not たい's (行きたくない, した
    くなかった): たい has its own point."""
    t, _s, _p = _token_at(text, m.start())
    return None if t is not None and t[4] in _VERB_TYPES else "ku-nai-katta-ku-nakatta"


def _mou_ta(text: str, m) -> str | None:
    """Already (もう寝てしまった), not "another / once more / no more"
    (もう一台, もう一度, もうこれ以上) nor もうもう."""
    from .sentence_parser import is_kanji
    t, start, _p = _token_at(text, m.start())
    if t is not None and start < m.start() and is_kanji(text[m.start() - 1]):
        return None                       # inside a verb: 盗もう (volitional)
    return "mou-ta" if _mou_already(text[m.start() + 2:]) else None


def _mou_already(rest: str) -> bool:
    """もう + rest can mean "already" (not もう一度, もう少し …)."""
    if rest.startswith(("もう", "片方", "片", "少し", "すこし", "ちょっと", "これ以上", "二度", "ひと")) or \
            re.match("一[度台つ回杯人個本枚匹冊着軒点品言]", rest):
        return False                      # もう一週間 (already a week) stays
    return True


def _amari_nai(text: str, m) -> str | None:
    """Not very (あまり好きじゃない), not 〜のあまり (ショックのあまり)."""
    return None if _before(text, m).endswith("の") else "amari-nai"


def _to_iu_named(text: str, m) -> str | None:
    """A noun called / such as (トムという人, ベートーヴェンといった), not
    といい (I hope), ということ / という気持ち after a clause, nor ずっといい."""
    if m.group().endswith("いい") or _after(text, m).startswith(("こと", "もの", "気持ち", "わけ", "の")):
        return None
    if text.startswith(("といっしょ", "といえ"), m.start()):
        return None                       # 犬といっしょに (with), 企業法といえる (can be called)
    if text[m.start() - 1:m.start()] in ("」", "』"):
        return "to-iu-named"              # 「さくら」という店 (a quoted name)
    t, _s, _p = _token_at(text, m.start() - 1)
    if t is None or t[1] not in ("word", "unk", "lone") or t[4] is not None:
        return None                       # a verb / adjective form before と: a clause
    if t[1] == "lone" and (m.group().endswith(("いわ", "いえ")) or text.startswith(("といって", "といったら"), m.start())
                           or _after(text, m).startswith(("から", "じゃ", "なら", "ので", "のに", "けど", "よ", "ね"))):
        return None                       # 洞察力という利益, not 一期一会というじゃない / 腱炎といわれた (corpus check 2026-10-26)
    return "to-iu-named"


_ACTIVITY = ("買い物", "散歩", "映画", "食事", "遊び", "旅行", "ボウリング", "スキー", "釣り", "見物",
             "見学", "花見", "留学", "勉強", "仕事", "泳ぎ", "スケート", "キャンプ", "ドライブ",
             "ハイキング", "登山", "観光", "見舞い", "迎え", "ランチ", "飲み", "カラオケ", "ピクニック")


def _no_hou_ga(text: str, m) -> str | None:
    """夏より冬の方が (the other order), not より多くの方が (more people: 方 = かた)."""
    if re.match("より(?:多|大勢|たくさん|沢山|一層|いっそう)", m.group()):
        return None
    return "no-hou-ga-yori"


def _ni_iku(text: str, m) -> str | None:
    """Go to do (飲みに行く, 買い物に行く): a verb stem or an activity, not a
    place or event (喫茶店に行き, オーストラリアに行った, パーティーに行く)."""
    t, _s, _p = _token_at(text, m.start() - 1)
    before = _before(text, m)
    if before.endswith(("早め", "多め", "少なめ", "大きめ", "小さめ", "長め", "短め", "遅め", "軽め", "初め", "始め",
                        "通り", "どおり", "とおり")):
        return None                       # 早めに帰ります (early), 初めに来た (first), 時間通りにくる
    if t is not None and t[4] in _VERB_TYPES:
        return "ni-iku"
    # 買いに行く: the parser may read the stem as a noun (買い "purchase")
    if re.search("[" + _KANJI + "][いきしちにひみりぎじびえけせてねべめれ]$", before):
        return "ni-iku"
    return "ni-iku" if before.endswith(_ACTIVITY) else None


# ── Gemini review, final pass (2026-10-14) ───────────────────────────────────

def _te_kuru(text: str, m) -> str | None:
    """Comes / gets (降りてきた, 泳いできた), not でき after a noun's い
    (お願いできますか: お願い + できる)."""
    if m.group().startswith("で"):
        t, _s, _p = _token_at(text, m.start() - 1)
        if t is not None and t[1] == "word" and t[4] is None:
            return None                   # a noun before it (お願い + できる)
    return "te-kuru"


def _de_are(text: str, m) -> str | None:
    """Whether / whatever (誰であれ、), not the command 正直であれ。"""
    rest = _after(text, m)
    return None if rest == "" or rest[0] in _SENT_END + "！!" else "de-are-de-are-de-are"


def _made_ni(text: str, m) -> str | None:
    """By (a deadline), not "to the extent of" (盗みをするまでに落ちぶれた,
    ６割を占めるまでになった)."""
    return None if _after(text, m).startswith(("なっ", "なる", "なり", "至", "落ち")) else "made-ni"


def _sue_ni(text: str, m) -> str | None:
    """After a long process (熟考した末に), not the end of a month / year."""
    return None if re.search("(?:月|年|週|学期|年度)の$", _before(text, m)) else "sue-ni"


def _ta_tokoro_de(text: str, m) -> str | None:
    """Even if (言ったところで、駄目だろ): a negative outcome follows, not
    見たところでは (from what I saw), 読み終えたところで (at that point), a place."""
    after = _after(text, m)
    if after.startswith("は"):
        return None
    return "ta-tokoro-de" if re.search("ない|ません|駄目|だめ|無駄|無理", after) else None


def _ta_tokoro(text: str, m) -> str | None:
    """When I did X (行ってみたところ、…): たところです is 〜ところだ
    (just did), and a place (窪んだところに) is neither."""
    after = _after(text, m)
    if after.startswith(("だ", "です", "でし", "でござ")):
        return "tokoro-da"
    return "ta-tokoro" if after[:1] in ("、", ",", "，") else None


def _bakari_ni(text: str, m) -> str | None:
    """〜んばかりに (as if about to) is its own N1 point."""
    before = _before(text, m)
    if before.endswith("ん"):
        return "n-bakari"
    # because of (〜たばかりに / 〜いばかりに / 〜なばかりに), not noun + ばかり + に
    # (この事ばかりに時間をかける: only on; accuracy test 3)
    return "bakari-ni" if before[-1:] in ("た", "だ", "い", "な") else None


def _bakari_da(text: str, m) -> str | None:
    """Keeps getting (悪くなるばかりだ, 泣くばかりだった) after a plain verb, not
    N + ばかり "nothing but" (砂ばかりだった) nor 泣いてばかり."""
    return "bakari-da" if _before(text, m).endswith(_VERB_END) else None


# ── context clues for the last residual cases (2026-10-14) ───────────────────

def _ja_nai(text: str, m) -> str | None:
    """Negative copula (本当じゃない), not a tag question after an i-adjective:
    an i-adjective's negative is くない, so 高すぎじゃない？/ すごいじゃない is
    "isn't it …?"."""
    before = _before(text, m)
    if m.group().startswith("じゃ"):
        if before.endswith(("すぎ", "過ぎ", "よう", "だろう", "ろう")):
            return None                   # 休憩しようじゃないか (let's …), tag questions
        from .sentence_parser import kinds_of
        t, _s, _p = _token_at(text, m.start() - 1)
        if t is not None and t[1] == "word" and "adj-i" in kinds_of(t[2], t[3]) and t[0].endswith("い"):
            return None
    return "de-wa-arimasen-ja-nai"


def _wa_mochiron(text: str, m) -> str | None:
    """"Not to mention A, (also) B": a comma right after, or B's も / まで /
    さえ later in the sentence (週末はもちろん平日も). Without one, もちろん is
    just the adverb "of course" after a topic (彼女はもちろん英語が話せます;
    precision test 6)."""
    rest = _after(text, m)
    if rest[:1] in ("、", ",", "，"):
        return "wa-mochiron-wa-motoyori"
    sentence = re.split("[。！？!?]", rest)[0]
    if re.search("も|まで|さえ", sentence):
        return "wa-mochiron-wa-motoyori"
    # without one, only a person as the topic reads as "of course" (洗顔は
    # もちろん身だしなみを整えて is still "not to mention")
    t, _s, _p = _token_at(text, m.start() - 1)
    return None if t is not None and (_person(t) or _is_name(t)) else "wa-mochiron-wa-motoyori"


def _nani_mo_nai(text: str, m) -> str | None:
    """Nothing / nobody: not 誰もが "everyone" or 何もかも "everything"
    (誰もが詩人になれるとは限らない; precision test 6)."""
    if re.match("(?:誰|何|だれ|なに)も(?:が|かも)|なにもの|何もの|何物", text[m.start():]) \
            or text[m.start() - 1:m.start()] == "ん" and text[m.start():m.start() + 1] == "な":
        return None                       # + こんなにも嬉しい (こんな + にも), なにものでもない
    return "nani-mo-nai-dare-mo-nai"


def _ni_taru(text: str, m) -> str | None:
    """〜に足る "worthy of" (信頼に足る, 取るに足りない), not 足りる
    "be enough" after a noun (生活費に足りない; precision test 6)."""
    if m.group().endswith("り") and not _before(text, m).endswith(_VERB_END):
        return None
    return "ni-taru"


_TYPICAL_ADVERBS = "いかにも|とても|本当に|実に|すごく|なかなか|まさに|さすが"


def _baai_wa(text: str, m) -> str | None:
    """〜場合（は） "in case of", not the plain noun "case": どの場合にも,
    多くの / ほとんどの場合 (in most cases), 場合によっては, 場合に応じて, この
    場合に当てはまる, 〜ている場合じゃない (no time for) (owner's deck audit
    2026-10-17: どの場合にも was credited)."""
    if re.search("(?:どの|多くの|ほとんどの|殆どの|大抵の|たいていの|全ての|すべての|あらゆる|大部分の|一部の|時と)$",
                 text[:m.start()]):
        return None
    if re.match("(?:じゃな|じゃあり|ではな|ではあり|によ|に応|に当|に適|を除|当て)", text[m.start() + 2:]):
        return None
    return "baai-wa"


def _te_ageru(text: str, m) -> str | None:
    """てあげる / てやる; てやる only after a verb's て-form (not 全てやれば)
    and not やり遂げる / やり直す (a compound), nor 〜てやまない (N1)."""
    if text[m.start() + 1:m.start() + 2] != "や":
        return "te-ageru"
    after = text[m.start() + 2:]
    if after.startswith(("ま", "っと", "っぱ", "りくり", "られ")) or re.match("[りっ][一-鿿]", after) \
            or re.match("って(?:来|き[たてまし]|くる|こ)", after):
        return None                       # 出てやっと (finally), 走ってやって来た, やりくり, してやられた
    if re.search("(?:頑張|がんば|思い切|思いき|従|急|黙|協力し|手分けし|分担し|集中し|工夫し)[っいんし]?[てで]$",
                 text[:m.start() + 1]):
        return None                       # がんばってやった, 思い切ってやる: やる is "do" (corpus check 2026-10-26)
    t, _s, _p = _token_at(text, m.start())
    if t is None or t[4] is None or not (t[5] and t[5][0].endswith(("て", "で"))) \
            or t[5][0].endswith("くて"):
        return None                       # 感じたくてやっている (やる "do")
    return "te-ageru"


def _ta_koto(text: str, m) -> str | None:
    """〜たことがない, not 大したことない (no big deal)."""
    return None if _before(text, m).endswith(("大し", "たいし")) else "ta-koto-ga-aru"


def _toori(text: str, m) -> str | None:
    """As (言われた通りに), not the street (混雑した通りで)."""
    if m.group().endswith("通り") and re.match("[をがは]|で(?![すしあは])", _after(text, m)):
        return None
    return "toori-ni-doori-ni"


_GATAI_KANJI_VERBS = ("信じ", "耐え", "言い", "許し", "忘れ", "避け", "理解し", "理解され", "説明し", "考え",
                      "尽くし", "代え", "抑え", "捨て",
                      "救い", "名状し", "想像し", "認め", "動かし", "近寄り", "得", "否み", "度し", "堪え", "抗し")


def _gatai(text: str, m) -> str | None:
    """〜がたい; written 難い only after verbs that take がたい (信じ難い),
    not 答え難い / 読み難い (often にくい; corpus check 2026-10-26)."""
    if m.group().startswith("難") and not _before(text, m).endswith(_GATAI_KANJI_VERBS):
        return None
    return "gatai"


def _shidai(text: str, m) -> str | None:
    """As soon as (分かり次第、連絡します), not "depends on" at the end
    (日にち次第よ / 天気次第だ: shidai-da; sample 9)."""
    return None if re.match("(?:だ|で|よ|です|[。！？!?]|$)", _after(text, m)) else "shidai"


def _ku_naru(text: str, m) -> str | None:
    """長くなる / 行きたくなる / 医者になる (become), not a verb's dictionary
    form + the particle なり (煮るなり焼くなり, 行くなり: either / as soon as)."""
    if m.group().startswith("く"):
        from .sentence_parser import kinds_of
        t, start, _p = _token_at(text, m.start())
        if t is not None and t[1] == "word" and t[4] is None and start + len(t[0]) == m.start() + 1                 and kinds_of(t[2], t[3]) & {"v1", "v5", "vk"}                 and (re.search("[一-鿿]", t[0]) or re.match("なり(?!ま)", text[m.start() + 1:])):
            return None                   # the verb ends at this く (焼く|なり); not 見えなくなる (one word)
            # nor a kana adjective the parser split (ねむく = ね|むく, あったかく = あった|かく)
    return "ku-naru-ni-naru"


_CONTEXT = {"ku-naru-ni-naru": _ku_naru, "shidai": _shidai, "te-ageru": _te_ageru, "ta-koto-ga-aru": _ta_koto, "toori-ni-doori-ni": _toori, "gatai": _gatai, "you-ga-you-to": _you_ga_you_to, "aida-aida-ni": _aida_ni, "mitai": _mitai,
            "dasu": _dasu, "koto-ga-aru": _koto_ga_aru, "o-suru": _o_suru, "baai-wa": _baai_wa,
            "ku-suru-ni-suru": _ku_suru, "ga-suru": _ga_suru, "naide": _naide,
            "mono-dakara-mono-de": _mono_dakara, "mono-de-wa-nai": _mono_de_wa_nai,
            "koto-da": _koto_da, "koto-wa-nai": _koto_wa_nai, "ni-tsuite": _ni_tsuite,
            "you-na-you-ni-like": _you_na, "to-shite": _to_shite, "tara-ta": _tara_ta,
            "tatte-datte": _tatte_datte, "ba-ii": _ba_ii, "muki-muke": _muki_muke,
            "kiru-kirenai": _kiru, "kakeru": _kakeru, "au": _au,
            "o-tsuujite-o-tooshite": _wo_tooshite, "ni-kagiru": _ni_kagiru,
            "ni-kagiri": _ni_kagiri, "ni-sureba-ni-shitara": _ni_sureba,
            "ni-mukete": _ni_mukete, "nagara-ni-nagara-no": _nagara_ni,
            "tara-saigo-ga-saigo": _tara_saigo, "tomo-naru-to-tomo-nareba": _tomo_naru,
            "you-ni-mo-nai": _you_ni_mo_nai, "nari-nari": _nari_nari, "ni-atte": _ni_atte,
            "made-da-made-no-koto-da": _made_da, "o-oite": _o_oite, "tada-nomi": _tada_nomi,
            "kare-kare": _kare_kare, "kaneru": _kaneru, "te-wa-irarenai": _te_wa_irarenai,
            "mono-ka": _mono_ka, "mono-no": _mono_no,
            "mono-nara": _mono_nara, "mono-ga-aru": _mono_ga_aru, "koto-ka": _koto_ka,
            "koto-ni-wa": _koto_ni_wa, "koto-dakara": _koto_dakara, "koto-naku": _koto_naku,
            "koto-wa-ga": _koto_wa_ga, "ijou-wa": _ijou_wa, "nuku": _nuku, "uru-enai": _uru_enai,
            "te-naranai": _te_naranai, "ni-shiro-ni-seyo": _ni_shiro, "ni-atatte": _ni_atatte,
            "naosu": _naosu, "hodo-wa-nai": _hodo_wa_nai, "tokoro-datta": _tokoro_datta,
            "nanka-nante": _nanka, "ageru-kureru-morau": _ageru, "te-aru": _te_aru,
            "mono-da": _mono_da, "koto-ni-natte-iru": _koto_ni_natte_iru, "ippou-de": _ippou_de,
            "mo-ba-mo": _mo_ba_mo, "ki-ga-suru": _ki_ga_suru, "uchi-ni": _uchi_ni,
            "tokoro-ni-tokoro-e-tokoro-o": _tokoro_ni, "wake-da": _wake_da,
            "dake-atte-dake-ni": _dake_ni, "ka-to-omottara-ka-to-omou-to": _ka_to_omottara,
            "serareru-saserareru": _serareru, "tagaru": _tagaru,
            "o-ni-naru": _o_ni_naru, "mae-ni": _mae_ni, "ato-de": _ato_de,
            "ku-nai-katta-ku-nakatta": _ku_nai, "mou-ta": _mou_ta, "amari-nai": _amari_nai,
            "to-iu-named": _to_iu_named, "ni-iku": _ni_iku, "no-hou-ga-yori": _no_hou_ga, "bakari": _bakari,
            "made-ni": _made_ni, "sue-ni": _sue_ni, "ta-tokoro-de": _ta_tokoro_de,
            "ta-tokoro": _ta_tokoro, "bakari-ni": _bakari_ni, "bakari-da": _bakari_da,
            "de-wa-arimasen-ja-nai": _ja_nai, "de-are-de-are-de-are": _de_are, "te-kuru": _te_kuru,
            "wa-mochiron-wa-motoyori": _wa_mochiron, "ni-taru": _ni_taru,
            "nani-mo-nai-dare-mo-nai": _nani_mo_nai}


def _part_spans(m) -> list[tuple[int, int]]:
    """Where a detector match's written parts are (one group each); the
    whole match if the groups aren't there."""
    out = [m.span(k) for k in range(1, (m.re.groups or 0) + 1) if m.span(k)[0] >= 0]
    return out or [m.span()]


# Subtitle spaces (社長か 副社長に 確認して ください): Japanese has none, so a
# space between two Japanese characters is dropped before the grammar is
# read, unless it follows a sentence-ending particle, where it's usually a
# sentence break (マジか 行くぞ, 来るんだよ 早く). Owner 2026-10-17: most
# people mine their cards from subtitle files.
_SPACE_KEEP_AFTER = set("よねぞぜわさなかのろだ")   # + 勉強中だろ 店員の, よく見ろ あれの


def _join_spaces(text: str) -> tuple[str, list[int]]:
    """(text without in-sentence spaces, original index of each kept char)."""
    out, pos = [], []
    n = len(text)
    for i, c in enumerate(text):
        if c in (" ", "　") and 0 < i < n - 1 and _is_jp(text[i - 1]) and _is_jp(text[i + 1]) \
                and (text[i - 1] not in _SPACE_KEEP_AFTER or text[max(0, i - 2):i] == "まだ"):
            continue
        out.append(c)
        pos.append(i)
    return "".join(out), pos


def sentence_ids(text: str, spans: dict | None = None) -> list[str]:
    """Grammar point ids found in a (cleaned) sentence. With subtitle spaces
    inside it, both readings count: spaces joined (社長か 副社長に 確認して
    ください → 〜か "or", 〜てください) and spaces as written, since a space
    can also be a clause break (潜るのに 泳げない, 捜せ 本体を, どうしよう
    学生章). Only "question か" is dropped where the joined reading shows
    〜か "or" there. spans: if given, gid → [(start, end)] in the original
    text."""
    joined, pos = _join_spaces(text)
    if len(joined) == len(text):
        return _sentence_ids_raw(text, spans)
    inner = {} if spans is not None else None
    found = _sentence_ids_raw(joined, inner)
    as_written = _sentence_ids_raw(text, spans)
    for gid in as_written:
        if gid not in found and not (gid == "ka-question" and "ka-or" in found):
            found.append(gid)
    if spans is not None:
        if "ka-question" not in found:
            spans.pop("ka-question", None)
        for gid, ss in inner.items():
            spans.setdefault(gid, []).extend(
                (pos[s], pos[e - 1] + 1) if e > s else (pos[s], pos[s]) for s, e in ss)
    return found


def _sentence_ids_raw(text: str, spans: dict | None = None) -> list[str]:
    """Grammar point ids found in a (cleaned) sentence. When one match lies
    inside a longer point's match (〜ことに inside 〜ことになる, 〜ばかり inside
    〜たばかり), only the longer, more specific point counts. spans: if
    given, gid → [(start, end)] of the text that triggered it.

    "Inside" means starting in one of the longer point's written parts, not
    in its gap (しようとしまいと's ようとし starts in ようと: inside). In
    全然勉強していない (全然〜ない) the 〜ている between 全然 and ない still
    counts, as does 〜になる in なかなか上手にならない (owner's deck audit
    2026-10-17: a gapped point swallowed every point in its gap)."""
    hits = []   # (start, end, core length, id, [(start, end) of each written part])
    for gid, anchor, n, rx in detectors():
        if anchor in text:
            if gid in _CONTEXT:
                # the first match the context accepts (間に合う … その間に)
                for m in rx.finditer(text):
                    g = _CONTEXT[gid](text, m)
                    if g is not None:
                        hits.append((m.start(), m.end(), n, g, _part_spans(m)))
                        break
                continue
            m = rx.search(text)
            if m:
                hits.append((m.start(), m.end(), n, gid, _part_spans(m)))
    found = []
    for s, e, n, gid, _p in hits:
        inside = any(s2 <= s and e <= e2 and n2 > n and g2 != gid
                     and any(a <= s < b for a, b in parts2)   # starts in a written part (住んでいません's
                                                               # ていま starts in 誰も〜ない's gap)
                     for s2, e2, n2, g2, parts2 in hits)
        if not inside:
            if gid not in found:
                found.append(gid)
            if spans is not None:
                spans.setdefault(gid, []).append((s, e))
    # Short forms from the parser's split of the sentence.
    for gid in token_ids(text, spans):
        if gid not in found:
            found.append(gid)
    return found


# ── short grammar from the sentence's tokens (phase 3b, 2026-10-09) ───────────
# Particles and endings too short to search as text (は, を, です, ます, た …)
# are found from the parser's split of the sentence: a particle only counts
# when the split leaves it as a piece of its own (はし / はい / こんにちは are
# words, so they give no は). Points that share a form (に: time /
# destination / place / indirect object / frequency …) only count where
# context makes the meaning clear (3時に → time; 学校に行く → destination);
# anything unclear is skipped and left to hand marks. Tuned on the owner's
# sentences, like the regex detectors.

_NUM = "0123456789０１２３４５６７８９一二三四五六七八九十百千万何数"
_TIME_END = ("時", "分", "秒", "日", "月", "年", "曜日", "週", "朝", "晩", "夜", "夕方", "昼",
             "午前", "午後", "今度", "週末", "夏", "冬", "春", "秋", "休み", "時代")
_QUOTE_VERBS = {"言う", "いう", "云う", "思う", "おもう", "考える", "呼ぶ", "叫ぶ", "答える", "書く", "聞く",
                "決める", "約束", "話す", "信じる", "感じる", "述べる", "伝える", "命じる", "頼む", "誓う",
                "願う", "祈る", "主張", "発表", "説明", "返事", "判断", "怒鳴る", "つぶやく", "見なす", "する", "なる",
                "思い", "分かる", "わかる", "知る", "望む", "規定", "期待", "心配", "確信", "疑う", "認める"}
_PLACE_WORDS = {"ここ", "そこ", "あそこ", "どこ", "外", "そと", "屋外", "野外", "海外", "国外", "郊外"}
_PLACE_END = ("館", "店", "室", "場", "校", "園", "院", "所", "屋", "駅", "社", "局", "港",
              "国", "町", "市", "村", "海", "山", "川", "庭", "家", "部屋", "台所", "空港",
              "会場", "外国", "日本", "東京", "ここ", "そこ", "あそこ", "どこ", "うち", "家",
              # + recall test 10 (2026-10-17)
              "ベッド", "トイレ", "風呂", "プール", "ホテル", "レストラン", "キッチン", "オフィス", "ベランダ",
              "ロビー", "スーパー", "デパート", "コンビニ", "島", "森", "浜", "砂浜", "田舎", "都会", "教会",
              "畑", "舞台", "ステージ", "カフェ", "ビル", "キャンプ", "人前", "面前")
# position nouns after の that name a place: 駅の前で, 俺の前で, 家の近くで (not
# の中で "among", の上で "after", の下で "under someone"; recall test 10)
_PLACE_REL = {"前", "後ろ", "横", "隣", "そば", "近く", "裏", "奥", "向こう", "周り", "まわり", "外", "側", "脇", "前方", "後方"}
_PERSON = {"私", "僕", "俺", "彼", "彼女", "あなた", "君", "友達", "先生", "母", "父", "兄",
           "姉", "弟", "妹", "子供", "家族", "皆", "みんな", "社長", "先輩", "後輩", "店員",
           "客", "誰", "人", "男", "女", "両親", "奥さん", "主人", "医者", "彼氏", "相手",
           # + recall test 7 (2026-10-17)
           "息子", "娘", "夫", "妻", "祖父", "祖母", "子", "赤ちゃん", "生徒", "学生", "部下", "上司",
           "同僚", "患者", "友人", "恋人", "仲間", "警察", "政府", "皆さん", "みなさん", "誰か", "少年",
           "少女", "老人", "女性", "男性", "子ども", "彼ら", "彼女ら", "私たち", "僕たち", "我々", "あいつ",
           "おじさん", "おばさん", "お母さん", "お父さん", "母親", "父親", "家内", "大人"}
_PERSON_END = ("さん", "くん", "ちゃん", "様", "君")
_MOVE = {"行く", "来る", "くる", "帰る", "着く", "向かう", "戻る", "入る", "出かける", "上る",
         "登る", "引っ越す", "通う", "届く", "いく", "参る", "伺う", "寄る",
         "進学", "入学", "到着", "移る", "飛び出す", "飛び込む",   # recall test 8
         "近づく", "近寄る"}   # recall test 10
_BENEFACTIVE = {"あげる", "上げる", "くれる", "呉れる", "やる", "差し上げる", "さしあげる", "下さる", "くださる"}
_EXIST = {"ある", "いる", "居る", "在る", "有る", "住む"}
# where something stays / is put (accuracy test 3): 家に泊まる, 郊外に定住する;
# 冷蔵庫にしまう, 机の上に置く
_STAY = {"泊まる", "定住", "滞在", "残る", "積もる", "座る", "勤める", "暮らす", "並ぶ", "隠れる",
         "住む", "生まれる", "咲く", "浮かぶ", "止まる", "停まる",
         "建つ", "立ち並ぶ", "広がる", "眠る", "かかる", "掛かる", "散らばる", "潜む", "住み着く"}
_HAVE_ABSTRACT = {"興味", "関心", "自信", "責任", "影響", "効果", "意味", "関係", "才能", "経験",
                  "価値", "必要", "理由", "原因", "裏", "気", "権利", "余裕", "用", "時間", "暇"}
_NOT_PLACE = {"ごと", "毎", "おき", "彼ら", "彼女ら", "私たち", "僕ら", "僕たち", "我々", "あなたたち", "君たち", "大人",
              "子供", "子ども", "人々", "ばかり", "あまり", "何", "なに"}
_PUT = {"置く", "しまう", "仕舞う", "入れる", "貼る", "乗せる", "載せる",
        "並べる", "隠す", "戻す", "飾る", "植える", "干す", "書く", "停める", "止める"}
_GIVE = {"あげる", "くれる", "もらう", "払う", "話す", "聞く", "教える", "見せる", "渡す", "送る",
         "言う", "貸す", "借りる", "頼む", "返す", "習う", "伝える", "謝る", "答える",
         "電話", "質問", "連絡", "相談", "説明", "紹介", "お願い",
         # + to a person (recall test 2026-10-14)
         "会う", "尋ねる", "たずねる", "告げる", "命じる", "命令", "知らせる", "報告", "手紙",
         "挨拶", "注意", "感謝", "約束", "譲る", "任せる", "頼る",
         # + recall test 7 (2026-10-17)
         "下さる", "くださる", "名付ける", "勧める", "薦める", "求める", "願う", "提案", "申し込む", "預ける",
         "届ける", "示す", "打ち明ける", "訴える", "呼びかける", "話しかける", "手渡す", "売る", "贈る",
         "依頼", "要求", "申し出る", "返事", "送信", "メール", "教わる", "あずける", "さしあげる", "差し上げる",
         "やる", "知らせる",
         "与える", "明け渡す", "譲り渡す"}   # + recall test 9
_MEANS = {"バス", "電車", "車", "自転車", "飛行機", "船", "タクシー", "地下鉄", "新幹線",
          "自動車", "バイク", "箸", "ペン", "鉛筆", "ボールペン", "手", "電話", "メール",
          "携帯", "スマホ", "ナイフ", "フォーク", "スプーン", "声", "言葉", "インターネット",
          "ネット", "テレビ", "ラジオ", "パソコン", "カード", "現金", "漢字", "写真", "紙",
          "歩き", "徒歩", "機械", "道具", "力", "魔法",
          # + recall test 10 (2026-10-17)
          "船便", "航空便", "郵便", "速達", "書留", "宅配便", "スカイプ", "ズーム", "ファックス", "チャット",
          "手紙", "大声", "小声", "素手", "両手", "片手", "指", "包丁", "はさみ", "ハサミ", "筆", "辞書",
          "電卓", "地図", "電子レンジ", "レンジ", "オーブン", "フライパン", "鍋", "弱火", "強火", "中火",
          "お湯", "石鹸", "せっけん", "ボート", "ヘリコプター", "モノレール", "ロープウェイ", "エレベーター",
          "エスカレーター", "ビデオ", "動画", "ラジオ", "マイク", "スマートフォン", "コンピューター", "コンピュータ"}
_WITH = {"会う", "話す", "遊ぶ", "結婚", "住む", "喧嘩", "別れる", "付き合う", "踊る", "戦う",
         "相談", "旅行", "行く", "出かける", "勉強", "仕事", "食事", "約束", "話し合う"}
_KNOW = {"分かる", "わかる", "知る", "覚える", "教える", "聞く", "調べる", "決める",
         "考える", "確かめる", "確認", "忘れる", "見る"}
_COUNTER = "回時間人個冊度年日月円枚本杯匹台歳分週階番キロメートル"
_PUNCT_END = set("、。，,．.！？!?…―」』)） ") | {"　"}


def _is_name(t) -> bool:
    """A run of katakana no list word covers: a name (トム, ジム, ヤニー), or
    of Latin letters (ＤＪ, CD)."""
    from .sentence_parser import _latin
    return t is not None and t[1] == "unk" and (len(t[0]) >= 2 and all(
        0x30A1 <= ord(c) <= 0x30FA or c == "ー" for c in t[0]) or _latin(t[0]))


_HUMBLE = {"参る", "まいる", "申す", "もうす", "申し上げる", "伺う", "うかがう", "拝見", "拝借",
           "拝読", "おる", "致す", "いたす", "存じる", "存ずる", "差し上げる", "さしあげる",
           "頂く", "いただく", "戴く", "頂戴", "承る", "うけたまわる"}
_HONORIFIC = {"いらっしゃる", "おっしゃる", "仰る", "召し上がる", "めしあがる", "なさる", "為さる",
              "ご覧", "御覧", "下さる", "くださる", "ご存じ", "ご存知", "御存知", "おいで"}
_A_ROW = set("あかがさざただなはばぱまやらわ")




def _short_causative_passive(t) -> bool:
    """歌わされた (歌う + the short causative-passive, sentence_parser's
    a-row + される rule) or 待たされた (待たす + される)."""
    path, typ = t[5], t[4]
    if typ not in ("v5", "v5-iku") or not path:
        return False
    p = path[-1]
    from .sentence_parser import SHORT_CAUSATIVE     # 〜す verbs that are just a short causative
    return (len(p) == 4 and p.endswith("される") and p[0] in _A_ROW) or (t[2] in SHORT_CAUSATIVE and p == "される")


def _passive(t, toks, i) -> bool:
    """A passive verb (造られた, 言われる, リストラされた). Godan / する verbs:
    the あ-row + れる ending can only be passive (or honorific); ichidan
    られる is also the potential, so it needs an agent に / によって before
    it in the clause, or a following しまう (食べられてしまった)."""
    path, typ = t[5], t[4]
    if typ is None or not path or any(p.endswith(("させられる", "せられる")) for p in path):
        return False                    # causative-passive is its own point
    if t[2] in _NOT_PASSIVE or typ == "vk":
        return False                    # いられない (can stay), 来られる, なられる, 悔やまれる
    # (a short causative-passive, 待たされた / 働かされた / 歌わされた, stays a
    # passive too: it ends in the passive される (owner's ruling from sample 6))
    from .sentence_parser import pos_text
    if typ in ("vs", "vsn") and "される" in path[-2:]:
        return True                     # リストラされた (される + the noun's する)
    p = path[-1]                        # the ending on the verb's own stem (innermost):
    if not p.endswith("れる"):          # 立っていられない is いる's, 終わらせられない せる's
        return False
    if typ in ("v5", "v5-iku") and len(p) >= 3 and p[-3] in _A_ROW:
        return True                     # + 歌わされる (short causative-passive: also serareru-saserareru)
    if typ in ("vs", "vsn") and p == "される":
        return True
    if typ in ("v1", "vk") and p == "られる":
        nxt = toks[i + 1] if i + 1 < len(toks) else None
        if nxt is not None and nxt[2] in ("しまう", "仕舞う"):
            return True
        for j in range(i - 1, -1, -1):
            if toks[j][1] == "punct":
                break
            if toks[j][0] == "に" and j > 0 and (_nounish(toks[j - 1]) or _person(toks[j - 1])) \
                    and "na-adjective" not in pos_text(toks[j - 1][2], toks[j - 1][3]) \
                    and toks[j - 1][2] not in _NOT_AGENT and toks[j + 1][0] != "は":
                return True                 # 先生に褒められた; not 母には見せられない
            if toks[j][0] in ("によって", "より") or (toks[j][2] in ("よる", "因る") and toks[j - 1][0] == "に"):
                return True
    return False


_E_ROW = set("えけげせてねべめれ")


def _potential(t, toks, i) -> bool:
    """A potential verb (話せる, 行ける, 生きられない, 勉強できる; recall test
    7, 2026-10-17: the point was never searched). Godan: the e-row + る
    ending on the verb's own stem (real ichidan verbs like 立てる / 切れる are
    words of their own, so the parser doesn't read them as potentials);
    ichidan られる when it isn't the passive; a する noun + できる."""
    from .sentence_parser import kinds_of
    path, typ = t[5], t[4]
    if t[1] != "word":
        return False
    if t[2] in ("できる", "出来る"):
        prev = toks[i - 1] if i > 0 else None
        if prev is not None and prev[1] == "word" and prev[4] is None and "vsn" in kinds_of(prev[2], prev[3]):
            return True
        # 処理が出来なかった, 払い戻しはできません (recall test 8): negative only,
        # since 準備ができた is "is ready"
        pp = toks[i - 2] if i > 1 else None
        return (prev is not None and prev[0] in ("が", "は", "も") and pp is not None and pp[1] == "word"
                and pp[4] is None and "vsn" in kinds_of(pp[2], pp[3])
                and any(q.endswith(("ない", "なかった", "ません")) for q in path or ()))
    if typ is None:
        return False
    if not path or t[2] in ("ある", "有る", "在る") or t[2] in _HONORIFIC:
        return False
    prev = toks[i - 1] if i > 0 else None
    after_te = prev is not None and prev[0].endswith(("て", "で"))
    # kana-only text is too easily a misread (かまけて, のがれたい): only the
    # auxiliaries (〜てもらえる, 〜ていただける, 〜ていける) and 言える
    # + もらえる on its own (no ichidan もらえる exists) and に + なれる (気に
    # なれない, 大人になれる; recall test 10)
    if not any(is_kanji_char(c) for c in t[0]) and not (
            (after_te and t[2] in ("もらう", "貰う", "いただく", "頂く", "いく", "行く")) or t[2] in ("言う", "いう")
            or t[2] in ("もらう", "貰う") and t[0].startswith("もらえ")
            or t[2] in ("なる", "成る") and t[0].startswith("なれ") and _surf(prev) == "に"):
        return False
    if t[2] in ("行く", "いく") and t[0].startswith("いけ") and not after_te:
        return False                    # てはいけない, ないといけない
    p = path[-1]
    if typ in ("v5", "v5-iku") and len(p) == 2 and p[1] == "る" and p[0] in _E_ROW:
        return True
    # ichidan られる is the passive too (与えられた, 信じられている): only when
    # negative (食べられない) or with a を object (手術を任せられる)
    if typ == "v1" and p == "られる" and t[2] not in ("いる", "居る") and not _passive(t, toks, i):
        if any(q.endswith(("ない", "なかった", "ません", "ず")) for q in path):
            return True
        for j in range(i - 1, -1, -1):
            if toks[j][1] == "punct" or _verbish(toks[j]):
                break                   # (それをしたために責められた: that を is した's)
            if toks[j][0] == "を":
                return True
    return False


def is_kanji_char(c: str) -> bool:
    return 0x4E00 <= ord(c) <= 0x9FFF or c == "々"


_NOT_PASSIVE = {"いる", "居る", "なる", "成る", "思う", "感じる", "悔やむ", "偲ぶ", "案じる",
                "思い出す", "考える", "見る", "出来る", "できる", "来る", "くる", "得る"}   # can / spontaneous / honorific
_NOT_AGENT = {"一緒", "いっしょ", "本当", "ほんとう", "すぐ", "急", "特", "非常", "実", "簡単", "上手",
              "きれい", "綺麗", "静か", "大切", "大事", "十分", "自由", "楽", "無理", "確か", "主"}


def _verb_stem(t) -> bool:
    """A verb's stem used as a noun of purpose (遊び, 見送り, 買い物 is not)."""
    if not _is_word(t) or t[4] is not None:
        return False
    from .sentence_parser import _as_verb
    v = _as_verb(t[0])
    return bool(v) and len(v[3]) == 1 and len(v[3][0]) <= 1


def _verb_te_split(t) -> bool:
    """The token before って plus って is really a verb's て-form the parser
    split (にわた + って, い + って, な + って)."""
    if t is None or not t[0]:
        return False
    # a one- or two-character hiragana piece (わた, な, い) is a verb stem cut
    # off; names are katakana, nouns mostly kanji
    if len(t[0]) <= 2 and all(0x3041 <= ord(c) <= 0x3096 for c in t[0]):
        return True
    from .sentence_parser import lookup_full
    w = lookup_full(t[0] + "って")
    return bool(w) and w[2] in ("v5", "v5-iku", "v1", "vk", "vs", "vsn")


def _is_word(t) -> bool:
    return t is not None and (t[1] in ("word", "lone") or _is_name(t))


_NOUN_PATHS = (("さ",), ("み",))     # 優しさ, 楽しみ: nouns made from adjectives (recall test 13)


def _verbish(t) -> bool:
    """A verb or i-adjective (conjugated or not)."""
    if not _is_word(t) or t[4] == "adj-i" and t[5] in _NOUN_PATHS:
        return False
    from .sentence_parser import kinds_of
    return t[4] is not None or bool(kinds_of(t[2], t[3]) & {"v1", "v5", "vk", "adj-i"}) \
        or t[2] in ("する", "為る", "ある", "いる", "いい")     # いい is adj-ix (でいいから; recall test 10)


def _nounish(t) -> bool:
    if _is_name(t) or _is_word(t) and t[4] == "adj-i" and t[5] in _NOUN_PATHS:
        return True
    if not _is_word(t) or t[4] is not None:
        return False
    from .sentence_parser import pos_text
    pos = pos_text(t[2], t[3])
    # (counters / suffixes too: 八時の予定, now that 八 + 時 are words; vocab test 2)
    return ("noun" in pos or "pronoun" in pos or "counter" in pos or "suffix" in pos) and not _verbish(t)


def _person(t) -> bool:
    return _is_word(t) and (t[2] in _PERSON or t[0] in _PERSON or t[0].endswith(_PERSON_END))


def _ends(t, ends) -> bool:
    return t is not None and t[1] in ("word", "lone", "unk") and t[0].endswith(ends)


def _is_num(t) -> bool:
    """A number (the parser leaves digits as punct)."""
    return t is not None and t[1] == "punct" and re.fullmatch("[0-9０-９][0-9０-９.,．，]*", t[0]) is not None


def _clause_end(t) -> bool:
    return t is None or t[1] == "punct"


def _sentence_end(t) -> bool:
    """The end of the sentence (not a comma; a subtitle's … or space ends it)."""
    return t is None or t[1] == "punct" and t[0] not in ("、", "，", ",")


def _surf(t):
    return t[0] if t is not None else ""


def _num_counter_before(text: str, pos: int) -> bool:
    """Text before pos ends with a number + counter (3回, 十人, 2時間)."""
    m = re.search("[" + _NUM + "]+[" + _COUNTER + "]{1,3}$", text[:pos])
    return bool(m)


def token_ids(text: str, spans: dict | None = None) -> list[str]:
    """spans: if given, gid → [(start, end)] of what triggered each point
    (for tools/grammar_review.py)."""
    from .sentence_parser import tokens, pos_text, kinds_of
    toks = tokens(text)
    found: set[str] = set()
    pos = 0
    starts = []
    for t in toks:
        starts.append(pos)
        pos += len(t[0])

    def hit(gid, i):
        found.add(gid)
        if spans is not None:
            spans.setdefault(gid, []).append((starts[i], starts[i] + len(toks[i][0])))

    def hit_rx(gid, m):
        if m:
            found.add(gid)
            if spans is not None:
                spans.setdefault(gid, []).append(m.span())
        return bool(m)

    def at(i, step):
        """The neighbouring token, skipping nothing (punctuation counts)."""
        j = i + step
        return toks[j] if 0 <= j < len(toks) else None

    def after_space(i, n=1):
        """The n-th token after i, skipping spaces (subtitles: 現実か 幻想か)."""
        j = i
        for _ in range(n):
            j += 1
            while j < len(toks) and toks[j][1] == "punct" and not toks[j][0].strip():
                j += 1
        return toks[j] if j < len(toks) else None

    def next_word(i, limit=6):
        """The next word in the same clause (skipping particles; numbers,
        which the parser leaves as punct, don't end it: あなたに１ドル払う)."""
        for j in range(i + 1, min(len(toks), i + 1 + limit)):
            if toks[j][1] == "punct" and not _is_num(toks[j]):
                return None
            if _is_word(toks[j]):
                return toks[j]
        return None

    def clause_words(i):
        """The tokens after i up to the end of its clause."""
        out = []
        for j in range(i + 1, len(toks)):
            if toks[j][1] == "punct" and not _is_num(toks[j]):
                break
            out.append(toks[j])
        return out

    for i, t in enumerate(toks):
        s, kind, disp, read, typ, path = t
        prev, nxt = at(i, -1), at(i, 1)

        # ── single-meaning particles / words ─────────────────────────────
        if kind == "func" or kind == "word":
            if s == "は" and not (_surf(prev).endswith(("て", "で")) and _surf(nxt)[:2] in ("なら", "いけ", "だめ", "駄目", "いか")) \
                    and (_is_word(prev) or _is_num(prev) or _surf(prev) in ("に", "で", "と", "から", "まで", "へ", "ばかり", "だけ", "ほど", "など")
                             or _surf(prev) == "の" and _verbish(at(i, -2))):
                hit("wa", i)            # + には / では / とは … (recall test 2026-10-14); 〜のは (recall test 5)
            elif s == "を" and (_is_word(prev) or _surf(prev) in ("の", "こと") and _verbish(at(i, -2))):   # 話すのをやめた
                hit("o", i)
            elif s == "へ" and _is_word(prev):
                hit("e", i)
            elif s == "や" and _nounish(prev) and _nounish(nxt) and _surf(prev) not in ("今", "いま"):
                hit("ya", i)
            elif s == "ね" and prev is not None and _clause_end(nxt):
                hit("ne", i)
            elif s == "よ" and prev is not None and prev[1] != "punct" \
                    and (_clause_end(nxt) or _surf(nxt) in ("ね", "な") and _clause_end(at(i, 2))) \
                    and not (prev[4] in ("v1", "vk") and prev[5] == ("",)):   # 与えよ (classical imperative)
                hit("yo", i)
            elif s == "より" and _is_word(prev):
                hit("yori", i)
            elif s == "だけ" and prev is not None and prev[1] != "punct" and not (
                    _surf(nxt).startswith("でなく") or _surf(nxt) == "で" and _surf(at(i, 2)).startswith("な")):
                hit("dake", i)
            elif s == "みたい" and prev is not None and prev[0].endswith(("て", "で")) \
                    and prev[4] is not None:
                hit("tai", i)       # 会ってみたい: みる + たい (みたい is a function token)
            elif s in ("ごろ", "頃") and (_ends(prev, _TIME_END) or _num_counter_before(text, starts[i])):
                hit("goro", i)
            elif s in ("これ", "それ", "あれ", "どれ", "これら", "それら", "あれら") and not (
                    s == "あれ" and _clause_end(prev) and _surf(nxt) in ("、", "？", "?", "！", "!", "っ")):
                hit("kore-sore-are-dore", i)    # not the interjection あれ、 (precision sample 4)
            elif s in ("この", "その", "あの", "どの") and (_is_word(nxt) or _surf(nxt) in ("ような", "ように")) \
                    and not any(x is not None and x[1] == "unk" and re.fullmatch("[ぁ-ゖ]+", x[0])
                                for x in ((at(i, -2),) if _surf(prev) == "とか" else ())):
                # ひ|とか|どの: ひとかど (an unknown word), not a demonstrative
                hit("kono-sono-ano-dono", i)
            elif kind == "word" and s[:2] in ("この", "その", "あの", "どの") \
                    and s[2:] in ("方", "かた", "ころ", "頃", "辺", "へん", "時", "とき", "人", "日", "年", "世"):
                hit("kono-sono-ano-dono", i)    # この方, そのころ (one word; recall test 13); not その上 / そのうち
            elif s == "た" and kind == "func" and prev is not None and prev[1] == "word" \
                    and prev[4] == "v1" and prev[5] == ("",):
                hit("ta", i)            # 落ち|ぶれ|た: an ichidan stem the parser split off
            elif s == "です" and prev is not None and prev[1] != "punct":
                hit("desu", i)
            elif s == "だ" and (_is_word(prev) or _surf(prev) in ("みたい", "ばかり", "だけ", "ほど", "など")) and (
                    _clause_end(nxt) or _surf(nxt) in ("よ", "ね", "から", "けど", "と")):
                hit("da", i)            # + だと (recall test 5)
            elif s == "だ" and _surf(nxt) == "ろ" and nxt[1] == "unk" and _clause_end(at(i, 2)):
                hit("darou", i)         # 〜だろ (casual; the parser leaves ろ unknown; recall test 8)
            elif s == "だった" and (_is_word(prev) or _surf(prev) in ("みたい", "ばかり", "だけ", "ほど", "など", "っぱなし")) \
                    and _surf(nxt) != "ら":
                hit("ta", i)            # 手紙だった, 真っ暗だった (missed in recall tests 2–8)
            elif s == "って" and kind == "func" and prev is not None and prev[1] != "punct" \
                    and (_surf(prev) in ("んだ", "のだ") or not _verb_te_split(prev)) and (
                    _nounish(prev) or _surf(prev) in ("んだ", "のだ")
                    or re.match("[^。！？]{0,3}?(?:言|いう|いっ|思|聞|書|話|こと|顔|有名)", text[starts[i] + 2:])):
                hit("tte", i)           # トムって、/ …って言ってた (recall test); 来るんだって (hearsay),
                                        # 怖いって有名 (owner's deck audit 2026-10-17)
            elif s in ("んだ", "のだ") and (_is_word(prev) or _surf(prev) in ("だった", "なかった", "た")
                                          or _surf(prev) == "な" and _is_word(at(i, -2))):
                hit("n-desu-no-desu", i)    # 嬉しいんだ, 行くのだ (plain form; recall test); 外国語なんだ (test 5)
            elif s == "ん" and kind == "func" and _surf(nxt) in ("だろう", "でしょう", "だろ", "です", "でした", "じゃない", "じゃ") \
                    and (_verbish(prev) or _surf(prev) == "な" and _is_word(at(i, -2))):
                hit("n-desu-no-desu", i)    # 美しいんだろう (recall test 8)
            elif s == "ので" and prev is not None and not _surf(nxt).startswith(("あ", "し", "は")) \
                    and not _surf(prev).endswith("も"):
                hit("node", i)          # not のである / のでしか / ものである (Gemini batch 9)
            elif s == "など" and _is_word(prev):
                hit("nado", i)
            elif s == "ずつ" and (_num_counter_before(text, starts[i]) or _is_word(prev)):
                # + 二つずつ, 少しずつ, 半分ずつ: ずつ has no other meaning (2026-10-20)
                hit("zutsu", i)
            elif s == "なら" and (_is_word(prev) or _surf(prev) in ("の", "ん") and _verbish(at(i, -2))) \
                    and not _surf(prev).endswith(("ければ", "ねば")):   # + あるのなら (recall test 5)
                hit("nara", i)          # not なければならない (Gemini batch 9)
            elif s in ("とき", "時") and kind == "word" and (_verbish(prev) or _surf(prev) in ("の", "た", "だ", "な")):
                hit("toki", i)
            elif s == "目" and _num_counter_before(text, starts[i]) or (
                    s == "目" and re.search("[" + _NUM + "][つ回番人度]$", text[:starts[i]])):
                hit("me", i)

        if kind == "lone" and s == "頃" and (_ends(prev, _TIME_END) or _num_counter_before(text, starts[i])):
            hit("goro", i)              # ３時頃 (recall test 8)

        # ── more whole tokens (recall test 5, 2026-10-16) ────────────────
        if kind in ("func", "word") and prev is not None and prev[1] != "punct":
            if s in ("けど", "けれど", "けれども", "だけど") and (s != "だけど" or _is_word(prev)):
                hit("kedo-keredomo", i)     # 怖いけど (けど is too short for the text search)
            elif s == "だから" and _is_word(prev) and _surf(prev) not in ("もの", "物", "こと", "事"):   # ものだから
                hit("kara-reason", i)       # 嫌いだから (sentence-first だから is "so")
            elif s == "だが" and _is_word(prev):
                hit("ga-but", i)            # 便利だが、 / 雨のようだが (sentence-first だが is "however"; recall test 10)
                if _surf(prev) not in ("よう", "そう", "みたい"):
                    hit("da", i)
            elif s == "ます" and kind == "word" and prev[1] == "word":
                hit("masu", i)              # a stem the parser read apart (たち|ます)
            elif s in ("ませ", "まし") and _surf(prev) in ("ください", "下さい", "いらっしゃい", "なさい"):
                hit("masu", i)              # ご覧くださいませ
            elif s == "ても" and kind == "func" and _is_word(prev) and _surf(nxt) not in _PERMISSION \
                    and not (_surf(at(i, -2))[-1:] in ("に", "を") and prev[2] in _PARTICLE_VERBS) \
                    and not _surf(nxt).startswith(("よ", "良", "かま", "構", "さしつかえ", "差し支え")):
                hit("te-mo-de-mo", i)       # 直面し|ても, 考え|ても
            elif s == "では" and kind == "word" and _is_word(prev):
                hit("wa", i)                # スタジオでは: で + は mid-sentence
            elif s == "つつ" and kind == "func" and not _surf(nxt).startswith("あ") and (
                    prev[4] in _VERB_TYPES and len(prev[5]) == 1 and len(prev[5][0]) <= 1 or _verb_stem(prev)):
                hit("tsutsu-tsutsu-mo", i)  # 思いつつ, 知りつつ (つつ is too short for the text search;
                                            # つつある is its own point; owner's card 2026-10-16)
        if kind == "word" and s in ("ここ", "そこ", "あそこ", "どこ"):
            hit("koko-soko-asoko-doko", i)
        # Owner's deck audit 2026-10-17 (points in the owner's sentences that
        # nothing credited):
        if s == "だって" and _is_word(prev) and (
                _sentence_end(nxt) or _surf(nxt) in ("さ", "よ", "ね") and _sentence_end(at(i, 2))
                or _surf(nxt).startswith(_QUOTE_AFTER)):
            hit("tte", i)               # 神様だって (hearsay), 地獄だって聞いてた (a quote); not "even"
                                        # (_tatte_datte): いくら便利だって、 / 制服だって、
        if s == "ついで" and _surf(nxt) == "に" and _clause_end(prev):
            hit("tsuide-ni", i)         # ついでに…寄ってきて (sentence-first: "while you're at it")
        if _potential(t, toks, i):
            hit("eru-rareru-potential", i)  # 話せる, 生きられない, 勉強できる (recall test 7)
        _never_searched(t, i, prev, nxt, toks, text, starts, hit)
        if s == "上" and kind == "word" and prev is not None and (
                (_verbish(prev) and _surf(prev)[-1:] in "うくぐすつぬぶむるただい")
                or (_surf(prev) == "な" and "na-adjective" in pos_text(*at(i, -2)[2:4]))):
            # (a plain / た form: 通って上に昇った, つけ上に are "upward / on top")
            # 上で / 上に after a verb / adjective form (確認した上で, 学ぶ上で, おいしい上に,
            # 便利な上に, 速い上、); the physical 上 comes after の (机の上で) (2026-10-20)
            is_adj = _surf(prev) == "な" or prev[4] == "adj-i" or (
                prev[4] is None and "adj-i" in kinds_of(prev[2], prev[3]))
            if _surf(nxt) == "で" and not is_adj:
                hit("ue-de", i)
            elif _surf(nxt) in ("に", "、"):
                hit("ue-ni", i)
        if s == "目" and kind == "lone" and re.search("[" + _NUM + "][" + _COUNTER + "つ]{1,3}$", text[:starts[i]]):
            hit("me", i)                    # 二回目 (目 can come out as a lone token; 2026-10-20)
        if s == "そう" and kind == "word" and prev is not None and prev[1] == "word" and prev[4] is None \
                and "na-adjective" in pos_text(prev[2], prev[3]) and prev[2] not in ("多分", "たぶん") \
                and _surf(nxt)[:1] in ("だ", "で", "な", "に"):   # not 多分そうだ (probably so)
            hit("sou-da-appearance", i)     # 元気そうだった, 静かそうな (na-adjective + そう; 2026-10-20)
        if kind == "word" and len(s) >= 2 and s.endswith("的") and s not in ("目的", "標的", "射的", "金的"):
            hit("teki", i)                  # 個性的, 具体的 (〜的 is one token since recall test 5)
        if kind == "word" and disp in ("ない", "無い") \
                and not (s in ("なく", "無く") and re.search("(?:だけ|ばかり|のみ)で$", text[:starts[i]])):
            hit("nai", i)                   # お金が無い, 協力がなかった, 過程などない (not だけでなく)
        if kind == "word" and disp in ("過ぎる", "すぎる") and prev is not None and prev[1] == "word" \
                and prev[5] == ("",):
            hit("sugiru", i)                # 食べ|過ぎています (stem + 過ぎる)
        if s in ("こと", "事") and kind == "word" and _is_word(prev) and (
                prev[4] in _VERB_TYPES or kinds_of(prev[2], prev[3]) & {"v1", "v5", "vk"} or prev[2] in ("ない", "する")) \
                and _surf(nxt) in ("を", "が", "は", "で", "に", "も") and prev[2] not in ("いう", "言う") \
                and not (_surf(nxt) == "に" and _clause_end(at(i, 2))) \
                and not (_surf(nxt) == "で" and _surf(at(i, 2)).startswith("あ")) \
                and not (_surf(nxt) in ("が", "は") and at(i, 2) is not None and at(i, 2)[2] in ("ある", "ない", "できる", "出来る")) \
                and not (_surf(nxt) == "に" and at(i, 2) is not None and at(i, 2)[2] in ("する", "なる", "為る", "成る")):
            hit("no-koto-nominalizer", i)   # ついたことで, そうでないことを (not ことがある / ことにする)

        # ── endings undone by the parser (食べました, 行きたい …) ─────────
        if kind == "word" and typ is not None and path:
            last = path[0]          # the outermost ending, as written
            if typ == "adj-i" and "がる" in path and last != "がる":
                typ = "v5"          # 欲しがった / 怖がらない / 怖がってる conjugate as a verb (recall test 10)
            if s.endswith("ます"):
                hit("masu", i)
            if typ in ("v1", "v5", "v5-iku", "vk", "vs", "vsn"):
                if any(p.endswith(("ない", "なかった")) for p in path):
                    hit("nai", i)
                if any(p.endswith("たい") and not p.endswith("がたい") for p in path) and "がる" not in path:
                    hit("tai", i)       # not 知りたがる (〜たがる; recall test 10)
                if last.endswith(("た", "だ")) and not last.endswith(("たい",)) and _surf(nxt) != "ら" \
                        and not (s == "した" and _surf(prev) == "ちょっと" and _nounish(nxt)):
                    hit("ta", i)        # not ありました|ら (precision test 5), ちょっとした痛み (slight; test 7)
                    if _surf(nxt) == "か":
                        j = i - 1
                        while j >= 0 and toks[j][1] != "punct":
                            if toks[j][0] == "もう" and _mou_already(text[starts[j] + 2:]):
                                hit("mou-ta", i)    # もう落ち着かれましたか (たか: recall test 13)
                                break
                            j -= 1
                elif last.endswith("た") and _surf(nxt) == "ら":
                    hit("tara", i)
                if last.endswith(("たら", "だら")) and not text.startswith("しい", starts[i] + len(s)) \
                        and not (disp in ("くる", "来る") and text[:starts[i]].endswith("と")):   # 〜ときたら (as for)
                    hit("tara", i)      # not ついたらしい (た + らしい)
                if (last.endswith("ば") and not last.endswith("れば") or last in ("れば", "すれば", "来れば", "くれば")) \
                        and not (disp in ("よる", "因る", "依る") and _surf(prev) == "に"):
                    hit("ba", i)        # によれば is "according to" (Gemini batch 9)
                # であろう is written だろう (conjecture), not "let's be" (Gemini pass 1).
                de_arou = disp == "ある" and last == "ろう" and _surf(prev).endswith("で")
                if last.endswith(("おう", "こう", "ごう", "そう", "とう", "のう", "ぼう", "もう", "ろう",
                                  "よう")) and typ != "adj-i" and _clause_end(nxt) and not de_arou or (
                        last in ("よう", "しよう", "こよう") and _surf(nxt) in ("か", "と", "", "よ")) or (
                        typ in ("v5", "v5-iku") and last.endswith(("おう", "こう", "ごう", "とう", "のう", "ぼう",
                                                                   "もう", "ろう"))
                        and _surf(nxt) in ("よ", "ね") and _clause_end(at(i, 2))):
                    hit("ou-you", i)    # + 行こうよ (recall test 14; not そう: 降りそうよ)
                elif typ in ("v5", "v5-iku") and last.endswith(("おう", "こう", "ごう", "そう", "とう", "のう",
                                                                "ぼう", "もう", "ろう")) \
                        and _surf(nxt) == "と" and at(i, 2) is not None and at(i, 2)[2] in ("する", "為る"):
                    hit("ou-you", i)    # 盗もうとしている: godan volitional + とする (accuracy test 3)
                    hit("you-to-suru", i)
                # + godan imperatives (黙れ！, 行けと言った) and a quoted command
                # (寝ろと言われた; recall test 10)
                # (not 込め「 = 込める's stem, 安く買え、 (can buy, and …), とはいえ
                # (言う), 良かれ悪しかれ, 筒|抜けよ (a noun right before it: a
                # compound the parser split))
                godan_imp = typ in ("v5", "v5-iku") and len(last) == 1 and last in _E_ROW and len(path) == 1 \
                    and disp not in ("くれる", "呉れる") and not s.endswith("かれ") \
                    and not (disp in ("言う", "いう") and text[:starts[i]].endswith(("と", "とは")) or s == "とはいえ") \
                    and _surf(nxt) != "「" and not (_surf(nxt) in ("、", ",", "，") and (
                        _ichidan_word(s + "る") or prev is not None and prev[4] == "adj-i"
                        # before a comma a stem (目を伏せ、) looks the same: only a
                        # clause-first command (急げ、) or one with さもないと after it
                        or not (_clause_end(prev) or re.match("[、,，](?:さもないと|さもなければ|すると|そうすれば)",
                                                              text[starts[i] + len(s):])))) \
                    and not (prev is not None and prev[1] == "lone")
                if (last in ("ろ", "しろ", "こい") or godan_imp) and (
                        _clause_end(nxt) or _surf(nxt) == "よ" and _clause_end(at(i, 2))
                        or _surf(nxt) == "と" and at(i, 2) is not None and at(i, 2)[2] in _QUOTE_VERBS | {"命じる", "命令", "怒鳴る", "頼む"}):
                    hit("e-ro", i)
                if any(p in ("とく", "どく", "といて", "どいて", "といた", "どいた", "とけ", "どけ") for p in path):
                    hit("te-oku", i)    # casual ておく: 止めとき, 読んどいて (recall test 10)
                if any(p in ("てる", "でる", "てた", "でた", "てます", "でます", "てない", "でない",
                             "てて", "でて", "てん", "でん") for p in path):
                    hit("te-iru", i)    # casual ている: 住んでる, 言ってた (recall test)
                if last in ("て", "で", "って", "いて", "いで", "んで", "して") and _surf(nxt) in ("は", "も") \
                        and _is_word(at(i, 2)) and at(i, 2)[2] in ("いる", "居る") \
                        and not _surf(at(i, 2)).startswith("いられ"):   # 〜てはいられない is its own point
                    hit("te-iru", i)    # 住んではいない (recall test 13)
                if last in ("て", "で", "って", "いて", "いで", "んで", "して", "きて", "来て") \
                        and _surf(nxt) == "、" and not (s == "して" and _surf(prev).endswith(("と", "から"))) \
                        and disp not in _COMPOUND_TE.get(_surf(prev)[-1:], ()):   # について、 / をめぐって、 / のに対して、
                    hit("te", i)        # not として、 (Gemini batch 12)
                elif last in ("て", "で", "って", "いて", "いで", "んで", "して") and _verbish(nxt) \
                        and nxt[2] not in _TE_AUX and not _surf(nxt).startswith(_TE_AUX_SURF) \
                        and not (_surf(prev)[-1:] in ("に", "を", "と") and disp in _PARTICLE_VERBS) \
                        and not (s == "して" and text[:starts[i]].endswith(("と", "べく", "に", "から"))):
                    hit("te", i)        # sequential て before another verb: 聞いて驚いた (recall test)
                elif last in ("て", "で", "って", "いて", "いで", "んで", "して") and _nounish(nxt) \
                        and not (_surf(prev)[-1:] in ("に", "を", "と") and disp in _PARTICLE_VERBS | {"因む", "ちなむ", "則る", "のっとる", "代表"}
                                 and not (_surf(prev) == "を" and disp in _WO_TE_REAL)) \
                        and s not in _TE_ADVERBS and not (s == "ついて" and _surf(prev) == "に") and not (s in ("やって", "して") and _surf(prev) in ("どう", "なんとか", "何とか", "どうにか")) \
                        and not (s == "して" and text[:starts[i]].endswith(("と", "べく", "に", "から"))) \
                        and any(_verbish(w) and w[2] not in _TE_AUX for w in clause_words(i)[1:]):
                    hit("te", i)        # 思ってそれをした, 発生して森林を焼いた (recall test 5)
                if last in ("て", "で", "って", "いて", "いで", "んで", "して") and _surf(nxt) == "も" \
                        and _surf(at(i, 2)) not in _PERMISSION \
                        and not (_is_word(at(i, 2)) and at(i, 2)[2] in ("いる", "居る")):
                    hit("te-mo-de-mo", i)   # not 〜てもいい (permission, Gemini batch 9)
            if typ == "adj-i" and any(p == "くて" for p in path):
                if last == "くて" and _surf(nxt) == "も" and _surf(at(i, 2)) not in _PERMISSION:
                    hit("te-mo-de-mo", i)   # 遠くても行く (the parser may split 遠くて|も)
                else:
                    hit("kute-de", i)
            if last == "ければ" and (typ == "adj-i" or typ in ("v1", "v5", "v5-iku", "vk", "vs")):
                hit("ba", i)            # + やすまなければ (a kana verb read whole since the wider kana rule)
            if typ == "adj-i" and last == "かったら":
                hit("tara", i)
            if typ == "adj-i" and last == "そう" and disp != "たい":
                hit("sou-da-appearance", i)     # not あっ+たそう (hearsay after た, Gemini batch 9)
            if typ == "adj-i" and last == "かった":
                hit("ta", i)        # 欲しかった, 楽しかった (recall test 3)
                if disp not in ("ない", "無い", "たい", "いけない") and not _surf(prev).endswith(("ば", "ら")):   # 〜ばよかった
                    hit("ku-nai-katta-ku-nakatta", i)   # 若かった (the text search skips かった; recall test 8)
            if _passive(t, toks, i):
                hit("reru-rareru-passive", i)
            if _short_causative_passive(t):
                hit("serareru-saserareru", i)   # 歌わされた, 待たされた (2026-10-20)
            if typ in ("v5", "v5-iku") and len(path[-1]) >= 3 and path[-1].endswith("せる") \
                    and path[-1][-3] in _A_ROW and not any(p.endswith(("せられる", "される")) for p in path) \
                    and any(is_kanji_char(c) for c in s):   # not もたせかける (凭せ掛ける)
                hit("seru-saseru", i)   # 驚かせた, 付き合わせて (せる is too short for the text search; recall test 9)

        # ── humble / honorific verbs (keigo; the patterns are just labels) ──
        if kind == "word" and (disp in _HUMBLE or disp in _HONORIFIC):
            if disp in _HONORIFIC:
                if not (disp in ("なさる", "為さる") and s.endswith("なさい")) \
                        and not (disp in ("下さる", "くださる") and (path and path[0] in ("い",) or s in ("ください", "下さい"))):
                    hit("sonkeigo", i)  # not しなさい (a command) / てください
            elif disp in ("おる", "居る") and not (s.startswith("おりま") or _surf(prev).endswith(("て", "で"))):
                pass                    # とおり / どおり / 檻 (おり): not humble おる
            elif not (disp in ("参る", "まいる") and s.startswith(("参った", "まいった")) and (
                    _clause_end(nxt) or _surf(nxt) in ("よ", "な", "ね", "わ") and _clause_end(at(i, 2)))):
                hit("kenjougo", i)      # 参った！ is "I give up"

        # ── shared forms: only where context makes the meaning clear ──────
        if kind != "func" and s not in ("から", "まで", "でも", "のに", "ながら", "しか", "では"):
            continue
        nw = next_word(i)
        if s == "に":
            after = text[starts[i] + 1:]
            cw = clause_words(i)
            if [w[0] for w in cw] in (["は"], ["も"]) and _surf(at(i, 2)) in ("、", ",", "，"):
                cw = cw + clause_words(i + 2)   # 公園には、男の子が数人いる (recall test 10)
            vj = next((j for j, w in enumerate(cw) if _verbish(w) and not (
                w[4] == "adj-i" or w[4] is None and kinds_of(w[2], w[3]) == {"adj-i"})), None)
            verb = cw[vj] if vj is not None else None          # the clause's first verb (not 黒い; recall test 6)
            if verb is not None and verb[2] in ("かかる", "掛かる") and any(
                    w[0] in ("時間", "お金", "金", "費用", "手間", "日数", "時", "年月", "コスト") for w in cw[:vj]):
                verb = None                 # 充電には、時間がかかる (takes time, not a place; round 8)
            if verb is not None and verb[2] in _EXIST and vj > 0 and (
                    _verbish(cw[vj - 1]) or cw[vj - 1][0].endswith(("て", "で", "っ", "ず"))
                    or cw[vj - 1][1] == "unk" or any(w[2] in _HAVE_ABSTRACT for w in cw[:vj])):
                verb = None                 # あたって|いる: ている; 祭りに興味がある: "have"
            # ない after が / は / も is ある's negative: 島には一軒しか店がない (recall test 7)
            # (a verb that only describes a noun doesn't count: ここには勉強する空間がない)
            # — only verb + noun + が/は/も + ない right after it, so 自転車に乗る時は…
            # ことはない stays out (Tatoeba check, round 8)
            attributive = vj is not None and vj + 3 < len(cw) and _nounish(cw[vj + 1]) \
                and cw[vj + 2][0] in ("が", "は", "も") and cw[vj + 3][0] in ("ない", "無い", "なかった", "無かった")
            exist_neg = (verb is None or attributive) and any(
                w[0] in ("ない", "なかった", "無い", "無かった") and k > 1 and cw[k - 1][0] in ("が", "は", "も")
                and cw[k - 2][0] != "と" for k, w in enumerate(cw))                 and not any(w[2] in _HAVE_ABSTRACT for w in cw)                 and not (cw and _is_word(cw[0]) and cw[0][2] in _PARTICLE_VERBS)   # 〜に関する規則はない
            place = _nounish(prev) and not _person(prev) and not _ends(prev, _TIME_END) \
                and _surf(prev) not in _NOT_PLACE and not _surf(prev).endswith(("以外", "ため", "為")) \
                and not (len(_surf(prev)) > 1 and _surf(prev).endswith("中")) \
                and "adverb" not in pos_text(prev[2], prev[3]) \
                and not re.match("(?:もほど|かけて|であ)", after)   # 失礼にもほどがある, 〜にかけては
            # + a て-form carried along: 家に持って帰る, 駅に走って行く (recall test 10)
            te_move = False
            if nw is not None and nw[0].endswith(("て", "で")) and nw[2] in ("持つ", "連れる", "走る", "歩く", "急ぐ", "飛ぶ"):
                k = next((k for k, w in enumerate(cw) if w is nw), None)
                te_move = k is not None and k + 1 < len(cw) and cw[k + 1][2] in _MOVE
            if _ends(prev, ("日", "週", "月", "年", "時間")) and re.match(
                    "[" + _NUM + "]+[回度]", after):
                hit("ni-frequency", i)
            elif _ends(prev, _TIME_END) and (not re.match("[" + _NUM + "]", after) or re.match("[" + _NUM + "]+歳", after)) \
                    and not _surf(prev).endswith(_NOT_TIME_BUN) \
                    and not re.match("(?:し(?:よう|ます|ましょう|た)|かこつけ|ちな|な[るりっら])", after):   # 冬になると (recall test 5)
                hit("ni-time", i)       # not 何時にしましょうか (にする)
            elif (nw is not None and nw[2] in _MOVE or te_move or place and verb is not None and verb[2] in _PUT) \
                    and _is_word(prev) and not _verbish(prev) \
                    and _surf(prev) not in ("見", "寝", "着", "出", "来", "居", "一緒", "いっしょ", "すぐ", "急", "先", "次", "わけ", "訳",
                                            "通り", "どおり", "とおり", "後", "あと", "以前", "以内", "うち") \
                    and not (_surf(prev) == "前" and _surf(at(i, -2)) != "の") \
                    and not ("na-adjective" in pos_text(prev[2], prev[3]) and "noun" not in pos_text(prev[2], prev[3])) \
                    and not re.match("(?:おい|おけ|おき)", after) \
                    and not (text[:starts[i]].endswith(("をもと", "を元", "を基"))
                             and not (verb is not None and verb[2] in ("戻す", "もどす", "返す", "かえす"))) \
                    and not re.match("[^、。]{0,6}と(?:呼|言|い|叫|命|頼)", after) and not _verb_stem(prev):
                hit("ni-destination", i)    # not 私に帰れと呼んでいる (Gemini batch 11)
            elif (_is_word(nxt) and nxt[2] in _EXIST or place and verb is not None and verb[2] in _EXIST | _STAY
                  or place and exist_neg) \
                    and _is_word(prev) and not _verbish(prev) \
                    and _surf(prev) not in ("本当", "ほんとう", "ほんと", "実", "特", "非常", "一緒", "いっしょ"):
                # the verb can come later: 公園に雪がたくさん積もっている (accuracy test 3)
                hit("ni-location", i)       # not 本当にいる (Gemini batch 11)
            elif (_person(prev) or _is_name(prev) and prev[0][0] >= "ァ") and _give_verb(i, toks) \
                    and not re.search("て(?:もら|いただ|貰)", after[:15]):
                hit("ni-indirect-object", i)    # not 医者にみてもらう (Gemini batch 11)
            elif _surf(nxt) in ("する", "します", "しよう", "しました") and _clause_end(at(i, 2)) \
                    and _is_word(prev):
                if "na-adjective" in pos_text(prev[2], prev[3]):
                    hit("ku-suru-ni-suru", i)
                elif _nounish(prev) and prev[2] not in ("気", "大事", "大切", "馬鹿", "無駄", "邪魔", "耳", "目"):   # 気にする, 耳にする etc. are idioms
                    hit("ni-suru", i)
        elif s == "で" or s == "では" and _is_word(prev):
            if _is_word(prev) and (prev[2] in _MEANS or prev[0] in _MEANS or prev[0].endswith("語")) \
                    and not _surf(nxt).startswith("あ") \
                    and not re.match("(?:いい|よい|良い|よろし[いく]|宜し[いく]|結構|大丈夫|構わ[なね]|かまわ[なね])"
                                     "(?:です|でしょ|ん|の|か|よ|ね|[。？！?!]|$)", text[starts[i] + len(s):]):
                # not この辞書でよろしいですか (で + "is fine"; round 8)
                hit("de-means", i)          # not 言葉である (Gemini batch 11)
            elif (_ends(prev, _PLACE_END) or _surf(prev) in _PLACE_WORDS or _is_name(prev) and prev[0][0] >= "ァ"
                  or _surf(prev) in _PLACE_REL and _surf(at(i, -2)) == "の"
                  or _ends(prev, ("内",)) and not _surf(prev).endswith(("以内", "案内", "身内"))) \
                    and not text.startswith(("すら", "さえ"), starts[i] + len(s)) and any(
                    _verbish(w) and w[2] not in _EXIST and w[2] != "ない" for w in clause_words(i)):
                hit("de-place", i)      # the verb can come later (駅で偶然…会った; recall test)
        elif s == "が":
            if _surf(prev) in ("です", "ます", "でした", "ました", "だ", "た", "んです", "のです", "んだ") \
                    and _clause_end(nxt):
                hit("ga-but", i)        # + 注文したいんですが (recall test)
            elif _verbish(prev) and prev[1] == "word" and _surf(nxt) == "、" and not (prev[5] and prev[5][0].endswith(
                    ("おう", "こう", "ごう", "そう", "とう", "のう", "ぼう", "もう", "ろう", "よう"))):
                hit("ga-but", i)        # 試合があるが、/ 失ったが、 (not ようが; recall test 8)
            elif (_nounish(prev) or _surf(prev) in ("こと", "事", "もの", "物")
                  and not (_is_word(nxt) and nxt[2] in ("ある", "できる", "出来る", "ない"))
                  or _surf(prev) == "の" and _verbish(at(i, -2))
                  or _surf(prev) == "と" and _nounish(at(i, -2)) and _surf(at(i, -3)) == "と") and _is_word(nxt):
                hit("ga-subject", i)    # + そんなことが, 吠えているのが (recall test 5); 幸福とお金とが (13)
                if re.fullmatch("[" + _NUM + "]+[" + _COUNTER + "つ]{1,2}", _surf(nxt)) and at(i, 2) is not None \
                        and at(i, 2)[2] in ("ある", "有る", "在る", "いる", "居る") and _surf(prev) not in ("こと", "事"):
                    hit("ga-aru-ga-iru", i)     # 男の子が数人いる (one token; recall test 10)
            elif _nounish(prev) and _is_num(nxt):
                # 質問が２つあります, 兄弟が３人いる (recall test 9): skip the number + counter
                j = i + 1
                while j < len(toks) and (_is_num(toks[j]) or len(toks[j][0]) <= 2 and all(c in _COUNTER + "つ" for c in toks[j][0])):
                    j += 1
                if j < len(toks) and _is_word(toks[j]):
                    hit("ga-subject", i)
                    if toks[j][2] in ("ある", "有る", "在る", "いる", "居る") and _surf(prev) not in ("こと", "事"):
                        hit("ga-aru-ga-iru", i)     # not 〜たことが一度ある (its own point)
        elif s == "か":
            sn = after_space(i)             # the next token, past a subtitle's spaces
            after_comma = at(i, 2)
            # The token after the noun that follows か (副 + 社長: a one-kanji
            # prefix the parser doesn't know joins the noun), or False.
            if _nounish(sn):
                after_noun = after_space(i, 2)
            elif sn is not None and sn[1] in ("unk", "lone") and len(sn[0]) == 1 \
                    and 0x4E00 <= ord(sn[0]) <= 0x9FFF and _nounish(after_space(i, 2)):
                after_noun = after_space(i, 3)
            else:
                after_noun = False
            if _surf(nxt) in ("、", ",", "，") and _is_word(after_comma) and after_comma[2] in _KNOW \
                    and not text[:starts[i]].endswith("とこと"):   # わかりづらいとことか、 (= とこ + とか)
                hit("ka-embedded-question", i)  # どこに住んでいるのか、わからない (accuracy test 3)
            elif _surf(nxt).strip() == "" and nxt is not None and _nounish(prev) and after_noun is not False \
                    and _surf(after_noun) in ("を", "が", "は", "に", "で", "か", "の") \
                    and not re.search("(?:何|いくら|いち|どちら|どっち|誰|どこ)[^、。！？ 　]{0,3}$", text[:starts[i]]):
                hit("ka-or", i)                 # subtitle spaces: 現実か 幻想か, 社長か 副社長に (owner's cards 2026-10-17)
            elif _surf(nxt).strip() == "" and nxt is not None and _is_word(sn) and sn[2] in _KNOW:
                hit("ka-embedded-question", i)  # 幻想か 分かりません
            elif _clause_end(nxt) and (_surf(prev) in ("です", "ます", "でした", "ました", "ません", "の", "ん",
                                                       "でしょう", "だろう", "のです", "んです", "のでした", "んでした")
                                    or _verbish(prev)
                                    or _nounish(prev) and _clause_end(at(i, -2)) and _surf(nxt) != "、"
                                    and not _is_num(nxt) and not _is_num(at(i, -2))   # １日か２日 (or)
                                    or _surf(prev) in ("本当", "ほんと", "ほんとう", "マジ", "まじ", "そう", "嘘", "うそ")
                                    and _clause_end(at(i, -2))):
                hit("ka-question", i)   # + でしょうか (recall test 5); 本当か、/ 雨か？ (recall test 10)
            elif _surf(nxt) in ("な", "なあ", "なぁ") and _clause_end(at(i, 2)) and (
                    _verbish(prev) or _surf(prev) in ("の", "ん", "じゃない", "ない", "だろう", "でしょう")):   # + んじゃないかな (recall test 10)
                hit("kana-kashira", i)  # 遅れてくるのかな (かな is too short for the text search)
            elif _surf(nxt) == "よ" and _clause_end(at(i, 2)) and (_nounish(prev) or _verbish(prev)):
                hit("ka-question", i)   # 8連敗かよ？
            elif _surf(nxt) == "い" and _clause_end(at(i, 2)) and (_surf(prev) in ("の", "ん") or _verbish(prev)):
                hit("ka-question", i)   # 気があるのかい？ (recall test 13)
            elif _is_word(sn) and sn[2] in _KNOW or (_surf(sn) in ("は", "も", "に") and _is_word(after_space(i, 2))
                                                    and after_space(i, 2)[2] in _KNOW):
                hit("ka-embedded-question", i)  # + across a space: 幻想か 分かりません (owner's card 2026-10-17)
            elif _nounish(prev) and after_noun is not False and _surf(after_noun) in ("を", "が", "は", "に", "で", "か", "の") \
                    and not re.search("(?:何|いくら|いち|どちら|どっち|誰|どこ)[^、。！？ 　]{0,3}$", text[:starts[i]]):
                hit("ka-or", i)             # not いくらか, 何年か, いちかばちか (Gemini batch 11)
        elif s == "と":
            if _surf(nxt) in ("一緒", "いっしょ"):
                hit("to-with", i)
            elif _person(prev) and not (_nounish(nxt) and _surf(at(i, 2)) in ("が", "は", "も")) \
                    and any(_is_word(w) and (w[2] in _WITH or w[0] in _WITH) for w in clause_words(i)):
                # お父さんとお母さんが喧嘩 is "and" (Gemini batch 11)
                # the verb can come later: 先生と日本語で話します
                hit("to-with", i)
            elif _nounish(prev) and _surf(nxt) in ("が", "は", "を", "も") and _surf(at(i, -2)) == "と" \
                    and _nounish(at(i, -3)):
                hit("to-and", i)            # 幸福とお金とが (recall test 13)
            elif _nounish(prev) and _nounish(nxt) and _surf(at(i, 2)) in ("が", "は", "を", "も", "に", "で", "の", "って", "と") \
                    and nxt[2] not in _TO_RELATION and not (_person(prev) and not _person(nxt) and _surf(at(i, 2)) != "の"):
                hit("to-and", i)            # 彼と年を比べる is "with" (accuracy test 3)            # not 事件と関係がある / あなたと意見が違う
            elif _verbish(prev) and (prev[4] is None or _surf(nxt) == "、" and prev[5][:1] in (("ている",), ("でいる",))) \
                    and (_surf(nxt) == "、" or _is_word(nxt) and not any(
                    _is_word(w) and w[2] in _QUOTE_VERBS for w in clause_words(i))
                    and not text.startswith(("とも", "と共", "と同時", "とと", "とおり", "と通り"), starts[i])
                    and nxt[2] not in _PERMISSION):     # 〜といい is its own point
                hit("to", i)            # + 帰ると私は… (no comma; not a quote: 行くと言った; recall test 5)
        elif s == "から":
            if _ends(prev, _TIME_END) or _ends(prev, _PLACE_END) \
                    or _nounish(prev) and nw is not None and nw[2] in _MOVE \
                    or _ends(prev, ("前",)) and not re.match("(?:には|こそ|して|する|すれ)", text[starts[i] + 2:]) \
                    or _nounish(prev) and _surf(prev) not in ("そば", "側", "こと", "事", "べ") \
                    and not re.match("(?:には|こそ|して|する|すれ|見|み[るれ]|いう|いっ|言|と|な[るりっ]|成|ず(?!っと)|ざ)",
                                                       text[starts[i] + 2:]):
                hit("kara-from", i)     # + 休暇から帰る (recall test 5)
            elif (_surf(prev) in ("です", "だ", "ます", "ません", "でした", "ました", "た", "ない", "なかった",
                                  "のだ", "んだ", "のです", "んです")
                  or (_verbish(prev) and prev[1] == "word")) \
                    and _surf(prev) != "頼む" and _surf(nxt) != "に" \
                    and not (prev[5] and prev[5][0].endswith(("て", "で"))):   # 読んでから is 〜てから
                hit("kara-reason", i)       # not 頼むから, 見るからに (Gemini batch 12)
        elif s == "まで":
            cw = clause_words(i)
            # + ビーチまで乗せて (recall test 10); not 雨まで降ってきた ("even": the
            # くる there is a て-auxiliary) nor までに
            moving = any(_is_word(w) and w[2] in _MOVE | {"乗せる", "送る", "歩く", "走る", "運ぶ", "連れる", "泳ぐ", "飛ぶ", "続く", "待つ"}
                         and not (k > 0 and cw[k - 1][0].endswith(("て", "で"))) for k, w in enumerate(cw))
            if (_ends(prev, _TIME_END) or _ends(prev, _PLACE_END) or _nounish(prev) and moving) and _surf(nxt) != "に" \
                    and not text[:starts[i]].endswith("ま"):   # 入れたままで (まま + で)
                hit("made", i)
        elif s == "も":
            if _num_counter_before(text, starts[i]) or text[:starts[i]].endswith(("片時", "一瞬")):
                hit("mo-emphasis", i)   # + 片時も目を離せない (recall test 13)
            elif _person(prev) or _nounish(prev) and not _surf(prev).endswith(_QUESTION_WORDS) \
                    or _surf(prev) in ("に", "で", "から", "へ") and _is_word(at(i, -2)) \
                    or _surf(prev) == "と" and _nounish(at(i, -2)):
                hit("mo", i)            # + nouns, どこにも (recall test 5)
        elif s == "の":
            # possessive / attributive: noun の noun (was: a person only; recall test)
            if (_person(prev) or _nounish(prev) and not _verbish(prev) or _is_num(prev)
                    or _surf(prev) in ("ばかり", "だけ", "くらい", "ぐらい", "ほど", "％", "%")
                    or _surf(prev) == "ら" and _surf(at(i, -2)) in ("それ", "これ", "あれ", "彼", "彼女")) and (
                    _nounish(nxt) or _verbish(nxt) and nxt[1] == "word" and (
                        _nounish(at(i, 2)) or _verbish(at(i, 2)) and at(i, 2)[1] == "word" and _nounish(at(i, 3)))):
                hit("no", i)    # + 僕の知らない人, 地図上の赤い線 (subject / attributive の; accuracy test 3)
            elif _verbish(prev) and (_clause_end(nxt) or _surf(nxt) in ("か", "かな", "かしら")
                                     or _surf(nxt) in ("よ", "ね") and _clause_end(at(i, 2))) \
                    and (nxt is None or _surf(nxt) != "で"):
                hit("n-desu-no-desu", i)    # explanatory の (引っ越すの？, 行くのか; あるのよ: recall tests 13–14)
            elif _verbish(prev) and _surf(nxt) in ("が", "を", "は"):
                hit("no-koto-nominalizer", i)
            elif _surf(prev) == "な" and _is_word(at(i, -2)) and (_clause_end(nxt) or _surf(nxt) in ("よ", "ね", "か")):
                hit("n-desu-no-desu", i)    # 大嫌いなのよ (recall test 8)
        elif s == "な":
            if _is_word(prev) and ("na-adjective" in pos_text(prev[2], prev[3])
                                   or prev[0].endswith("的") and len(prev[0]) >= 2) and (
                    _nounish(nxt) or _surf(nxt) in ("こと", "事", "もの", "物", "ところが")):   # 重要なこと (recall test 8)
                hit("na-na-adjective", i)
            elif (_verbish(prev) and (prev[4] is None or prev[5] == ("する",))   # 信用するな (recall test 8)
                  and (_clause_end(nxt) or _surf(nxt) == "よ" and _clause_end(at(i, 2)))
                  and "adj-i" not in kinds_of(prev[2], prev[3])
                  and prev[2] not in ("ある", "有る", "在る", "いい")):   # 心細いな / 必要があるな / といいな are exclamations
                hit("na-prohibition", i)
        elif s == "のに":
            if _is_word(nxt) and nxt[2] in ("気付く", "気づく", "驚く"):
                hit("no-koto-nominalizer", i)   # 切らしているのに気付いた (recall test 13)
            elif re.match("[^。！？]{0,12}?(?:かか|掛か)", text[starts[i] + 2:]):
                hit("noni-purpose", i)  # 組み立てるのに３０分かかった (Gemini batch 9)
            elif _clause_end(nxt):
                hit("noni-although", i)
            elif nw is not None and nw[2] in ("使う", "必要", "いい", "便利", "役立つ", "十分", "かかる"):
                hit("noni-purpose", i)
        elif s == "ながら":
            fixed = _NAGARA_NOUNS + _NAGARA_NOT_CONCESSIVE
            if _is_word(prev) and prev[4] is None and not _verb_stem(prev) and (
                    "adj-i" in kinds_of(prev[2], prev[3])
                    or (_nounish(prev) or "adjective" in pos_text(prev[2], prev[3]))
                    and any(0x4E00 <= ord(c) <= 0x9FFF for c in _surf(prev))) \
                    and not (_surf(prev) in fixed or _surf(prev).endswith(tuple(x for x in fixed if len(x) > 1))) \
                    and _surf(nxt) != "の":
                # an adjective or noun: "although" (残念ながら, 狭いながらも,
                # 子供ながら), never "while" (owner's deck audit 2026-10-17:
                # 狭いながら was 〜ながら, 残念ながら was nothing)
                hit("nagara-mo", i)
            elif starts[i] > 0 and (text[starts[i] - 1] in _STEM_END or _verb_stem(prev)) \
                    and _surf(nxt) != "の" and not (_surf(prev) in _NAGARA_NOUNS and _surf(nxt) == "に"):
                hit("nagara", i)            # not 生まれながらの (Gemini batch 12); + 見ながら (deck audit)
        elif s == "しか":
            if re.match("しかた(?:が|な|の|あ)", text[starts[i]:]):
                pass                        # しかたがない / しかたありません (仕方 in kana, split しか + た);
                                            # 3日しかたたない stays
            elif _surf(nxt) == "ない" and _verbish(prev):
                hit("shika-nai-no-choice", i)
            elif any(tt[0] in ("ない", "ません", "なかった") or
                     (tt[1] == "word" and any(p.endswith(("ない", "ません", "なかった")) for p in tt[5]))
                     for tt in toks[i + 1:i + 8]):
                hit("shika-nai", i)
        elif s == "でも":
            if _nounish(prev) and re.search("(?:ませんか|ましょう|どう)", text[starts[i]:]):   # お茶でもどうぞ
                hit("de-mo-suggestion", i)

    # Plain-text checks for a few shared forms (context sits in the endings).
    m = re.search("(?<=[るたいだ])(?<!かわい)そう(?:だ|です)", text)
    if m and text[m.start() - 1] == "い":
        # a verb stem's い (会いそうだ) is appearance, not hearsay (Gemini batch 9)
        t, _s, _p = _token_at(text, m.start() - 1)
        if t is not None and t[4] in ("v1", "v5", "v5-iku", "vk", "vs", "vsn") and t[5] \
                and not t[5][0].endswith(("ない", "たい")):
            hit_rx("sou-da-appearance", m)
            m = None
    hit_rx("sou-da-hearsay", m)
    hit_rx("sou-da-appearance",
           re.search("(?<=[" + "ぎきしちにびみりえけげせてねべめれ" + "])(?<!本当に)(?<!ほんとうに)(?<!ほんとに)"
                     "(?<!確かに)(?<!たしかに)(?<!まさに)(?<!実に)(?<!全く)そう(?:だ|です|な|に)", text))
    # (本当にそうだ: "that's really so", not 死にそう's stem に; 2026-10-20)
    # "Typical of" (女らしい) needs a clue: an adverb before it (とても女らしい)
    # or a noun after it (男らしい声); a bare 外国人らしい。is hearsay.
    m = re.search("(?<=[男女子人])らしい", text)
    if m and not (re.search("(?:" + _TYPICAL_ADVERBS + ")[^、。]{0,6}$", text[:m.start()])
                  or not re.match("(?:[。、！？!?」』）)]|よ|ね|です|で|って|か|わ|ぞ|の|ん|$)", text[m.end():])):
        hit_rx("rashii", m)
        m = None
    if not hit_rx("rashii-typical-of", m):
        hit_rx("rashii", re.search("(?<=[るたいだ])(?<!わい)らしい", text))   # not かわいらしい
    # Noun + らしく (君らしくない, 学生らしく振る舞う: hearsay らしい has no く form here)
    # and the seasons (春らしい) are always "typical of" (2026-10-20)
    hit_rx("rashii-typical-of", re.search(
        "(?:(?<=[" + _KANJI + "ァ-ヺー])|(?<=あなた))(?<!素晴)(?<!汚)(?<!憎)(?<!愛)(?<!嫌)(?<!馬鹿)(?<!誇)"
        "(?<!阿呆)(?<!長)らしく|(?<=[春夏秋冬])らしい", text))
    if not hit_rx("you-na-you-ni-like", re.search("(?<=の)(?<![どそこあ]の)ように|"
                                                  "(?:(?<=言った)|(?<=いった)|(?<=述べた)|(?<=書いた)|(?<=話した)|"
                                                  "(?<=思った)|(?<=示した)|(?<=説明した))ように", text)):
        # + 先生が言ったように (as the teacher said; 2026-10-20)
        m = re.search("(?:(?<=[うくぐすつぬぶむる])|(?<=ない))ように(?!(?:な|す|し|言))", text)
        if m and text[:m.start()].endswith("ます"):
            hit_rx("masu-you-ni", m)      # 繋がれますように (a wish)
        elif m and re.match("(?:見え|みえ|思え|感じ)", text[m.end():]):
            hit_rx("you-na-you-ni-like", m)   # 逆らっているように見える (recall test 8)
        elif m and re.match("[^。！？]{0,10}?(?:言|いっ|頼|勧め|すすめ|説得|命じ|伝え)", text[m.end():]):
            hit_rx("you-ni-iu-you-ni-tanomu", m)   # 禁煙するように勧めた (Gemini batch 9; not 注意 / という)
        else:
            hit_rx("you-ni", m)
    hit_rx("kurai-gurai", re.search("[" + _NUM + "]+[" + _COUNTER + "]{1,3}[くぐ]らい|(?:どの|どれ)[くぐ]らい", text))   # + どのくらい (recall test 10)
    for m in re.finditer("[くぐ]らい(?!なら)", text):
        if _kurai_extent(text, m):
            hit_rx("kurai-gurai-extent", m)   # 歩けないくらい, 俺くらいの, 挨拶ぐらいしろ
            break
    for gid, rx in _NEVER_SEARCHED_RX:
        hit_rx(gid, rx.search(text))
    return [g for g in found if g in data()]


# くらい / ぐらい after these is an amount ("about"), not extent
_KURAI_APPROX = ("どの", "どれ", "この", "その", "あの", "これ", "それ", "あれ", "ここ", "そこ", "あそこ",
                 "同じ", "半分", "半", "全部", "少し", "ちょっと", "たくさん", "大体", "ほとんど", "いくら")
_KURAI_TIME = {"昼", "朝", "夜", "夕方", "今", "明日", "昨日", "今日", "来年", "去年", "今年", "来週", "先週",
               "今週", "来月", "先月", "今月", "頃", "時", "日", "年", "月", "週", "時間", "分", "秒", "前", "後"}


def _kurai_extent(text: str, m) -> bool:
    """くらい / ぐらい of extent or "at least" (owner's deck audit
    2026-10-17: 俺くらいの一流ボクサー, 挨拶ぐらいしろ were never credited):
    right after a verb, an adjective or a noun that isn't an amount or a time
    (10分くらい, どれくらい, 昼くらい are "about"; 同じくらい / これくらい
    are left out as unclear)."""
    before = text[:m.start()]
    if not before or before[-1] in _PUNCT or before.endswith(_KURAI_APPROX) \
            or re.search("[" + _NUM + "][" + _COUNTER + "ヶヵかカケ箇所]{0,3}$", before):   # ３ヶ月ぐらい
        return False
    t, start, _p = _token_at(text, m.start() - 1)
    if t is None or start + len(t[0]) != m.start() or not _is_word(t) or t[2] in _KURAI_TIME \
            or t[0] in _KURAI_TIME:
        return False                      # くらい inside a word, or after a particle (がくらい = 暗い)
    return _verbish(t) or _nounish(t)


# ── points that were never searched (point coverage, 2026-10-17) ──────────────
# Owner: "check for grammar points that are not being detected". These had 0
# Tatoeba hits because nothing looked for them; each rule was read against
# its Tatoeba hits. Points skipped on purpose (_SKIP_PATTERNS) stay skipped;
# ones that need meaning (て reason, まで even, くらい extent, とは) too.

# 〜中 that is part of the word itself, not "during / throughout"
_CHUU_LEXICAL = {"途中", "最中", "集中", "背中", "夢中", "熱中", "連中", "心中", "女中", "渦中", "胸中",
                 "水中", "空中", "地中", "海中", "意中", "日中", "道中", "中中", "宇宙中", "市中", "眼中",
                 "命中", "的中", "手中", "懐中", "掌中", "文中", "車中", "獄中", "忙中", "寒中", "暑中", "陣中",
                 "夜中", "真夜中", "街中", "田中", "山中"}
_GARU_LEXICAL = {"広がる", "ひろがる", "上がる", "あがる", "下がる", "さがる", "曲がる", "まがる", "転がる",
                 "群がる", "繋がる", "つながる", "強がる", "宛がう", "やわらかがる"}
_HODO_WORDS = {"先ほど", "後ほど", "なるほど", "成程", "程", "ちょうど", "さっき", "先"}


def _never_searched(t, i, prev, nxt, toks, text, starts, hit):
    from .sentence_parser import lookup, kinds_of
    s, kind, disp, read, typ, path = t
    # 〜中 (じゅう / ちゅう): 一日中, 世界中, 授業中, 顔中 (not 途中, 背中, 箱の中)
    if s.endswith("中") and kind in ("word", "lone"):
        if len(s) >= 2 and s not in _CHUU_LEXICAL and lookup(s[:-1]):
            hit("chuu-juu", i)
        elif s == "中" and prev is not None and prev[1] == "word" and prev[0][-1:] \
                and 0x4E00 <= ord(prev[0][-1]) <= 0x9FFF and prev[0] + "中" not in _CHUU_LEXICAL:
            hit("chuu-juu", i)
        elif s == "日中" and _is_num(prev):
            hit("chuu-juu", i)          # １日中 (the parser reads 日中 "daytime"; recall test 8)
    # 〜ずに (not ずにはいられない / ずに済む, their own points)
    if nxt is not None and nxt[0] == "に" and (
            (kind == "word" and path and path[0].endswith("ず"))
            or (s == "ず" and kind == "func" and prev is not None and prev[1] == "word" and prev[0][-1:] in _A_ROW)):
        after = toks[i + 2][0] if i + 2 < len(toks) else ""
        if after not in ("は",) and not text.startswith(("済", "す"), starts[i] + len(s) + 1):
            hit("zu-ni", i)
    # 〜さ (高さ, 大切さ): an i-adjective's さ, or さ after a na-adjective before a particle
    if kind == "word" and typ == "adj-i" and path and path[0] == "さ":
        hit("sa", i)
    elif kind == "word" and typ is None and len(s) >= 2 and s.endswith("さ") and lookup(s[:-1] + "い") \
            and "adj-i" in kinds_of(*lookup(s[:-1] + "い")):
        hit("sa", i)                    # 強さ, 高さ (compound tiles)
    elif s == "さ" and kind == "func" and prev is not None and prev[1] == "word" and prev[4] is None \
            and "na-adjective" in _pos(prev) and nxt is not None and nxt[0] in ("が", "を", "は", "に", "も", "の", "で"):
        hit("sa", i)                    # 大切さを
    # 〜ほど (degree): 死ぬほど疲れた (not 〜ば〜ほど, ほど〜ない, 先ほど)
    if s == "ほど" and kind in ("func", "word") and prev is not None and prev[1] == "word" and prev[2] not in _HODO_WORDS:
        clause = text[starts[i]:]
        clause = re.split("[、。！？!?]", clause)[0]
        before = re.split("[、。！？!?]", text[:starts[i]])[-1]
        if not re.search("ない|ません|なかった", clause) and not re.search("(?:ば|れば|なら)", before) \
                and not re.match("[" + _NUM + "]", prev[0][-1:] or "x") and not _is_num(prev) \
                and not re.search("[0-9０-９" + _NUM + "]+[^、。！？!?]{0,3}$", text[:starts[i]]):   # 4年ほど: about
            hit("hodo", i)
    # 〜まま: 開けたまま, そのまま, 靴のまま
    if s in ("まま", "儘") and prev is not None and (
            prev[0].endswith(("た", "だ", "ない")) or prev[0] in ("の", "その", "この", "あの", "な")):
        hit("mama", i)
    # 〜方 (way of doing): 読み方, 考え方 (a verb stem + 方)
    if kind == "word" and len(s) >= 2 and s.endswith("方") and read.endswith("かた"):
        from .sentence_parser import _as_verb
        v = _as_verb(s[:-1])
        if v and len(v[3]) == 1 and len(v[3][0]) <= 1:
            hit("kata", i)
    elif s == "方" and read == "かた" and prev is not None and _verb_stem(prev):
        hit("kata", i)
    # 〜がる (怖がる, 欲しがる): not たがる (its own point)
    if kind == "word" and disp.endswith("がる") and len(disp) >= 3:
        base = lookup(disp[:-2] + "い")
        if base and "adj-i" in kinds_of(*base) and not disp.endswith("たがる") and disp not in _GARU_LEXICAL:
            hit("garu", i)
    elif disp == "がる" and prev is not None and prev[4] == "adj-i" and prev[5] and not prev[5][0].endswith("たい"):
        hit("garu", i)
    elif kind == "word" and t[4] == "adj-i" and t[5] and t[5][-1] == "がる" and disp not in ("たい", "暗い", "薄暗い") \
            and not (len(disp) <= 2 and not any(is_kanji_char(c) for c in disp)) and not (prev is not None and prev[1] == "unk"):
        hit("garu", i)                  # 欲しがる read as 欲しい + がる (recall test 10); not 薄暗がり, うちひ|しがれる
    # 〜し (reasons listed): 安いし、近いし (after a predicate, not する's stem)
    if s == "し" and kind == "func" and prev is not None and nxt is not None and not nxt[0].startswith("そう") \
            and (nxt[0] in ("、", "，", ",") or _is_word(nxt)) and (
            prev[0] in ("だ", "です", "だった", "でした", "ない", "なかった", "ます", "ました", "た", "だろう")
            or (prev[1] == "word" and (prev[4] == "adj-i" and prev[5] and prev[5][0] in ("い", "かった", "くない")
                                       or prev[4] is None and "adj-i" in kinds_of(prev[2], prev[3])
                                       or prev[4] in ("v1", "v5", "v5-iku", "vk", "vs") and prev[5]
                                       and prev[5][0].endswith(("た", "だ", "ない", "ます", "る", "う"))
                                       or prev[4] is None and kinds_of(prev[2], prev[3]) & {"v1", "v5", "vk"}))):
        hit("shi", i)
    # さえ / こそ / すら as particles (さえ〜ば is its own point)
    if kind == "func" and s == "さえ" and prev is not None:
        rest = re.split("[、。！？!?]", text[starts[i]:])[0]
        if not re.search("(?:ば|れば|たら)", rest):
            hit("sae", i)
    if kind == "func" and s == "こそ" and prev is not None and not prev[0].endswith("よう"):
        hit("koso", i)                  # 今度こそ, だからこそ
    if kind == "func" and s == "すら" and prev is not None and not (nxt is not None and nxt[0][:1] in ("り", "っ")):
        hit("sura", i)


def _give_verb(i, toks) -> bool:
    """A giving / telling verb (_GIVE) later in the clause of the に at i: the
    next word, or a later one when the verbs in between are embedded (トムに
    ドッグフードを食べるのを止めるように言った, メアリーに窓を開けるようお願いした;
    recall test 7, 2026-10-17)."""
    for j in range(i + 1, len(toks)):
        t = toks[j]
        if t[1] == "punct" and not _is_num(t):
            return False
        if not _is_word(t):
            continue
        if t[2] in ("言う", "いう") and toks[j - 1][0] == "と" and j + 1 < len(toks) and _nounish(toks[j + 1]):
            continue                    # 〜という名前: naming, not telling
        if t[2] in _GIVE or t[0] in _GIVE:
            nx = toks[j + 1][0] if j + 1 < len(toks) else ""
            if t[5] and (t[5] == ("",) and nx in ("が", "は", "を", "の", "も")
                         or t[4] in ("v5", "v5-iku") and t[5][-1].endswith("れる") and t[5][-1][-3:-2] in _A_ROW):
                return False            # 借りがある (a noun), 誰に言われよう (passive agent)
            return True
        if _verbish(t):
            nxt = toks[j + 1][0] if j + 1 < len(toks) else ""
            if j + 1 < len(toks) and _nounish(toks[j + 1]) and (t[4] is None or t[5] == ("",)) \
                    and "adj-i" in _kinds(t):
                continue                # 私たちにおいしい牛乳を与えて (an adjective before its noun; recall test 10)
            if t[0].endswith(("て", "で")) and j + 1 < len(toks) and toks[j + 1][2] in _BENEFACTIVE \
                    and t[2] not in ("なる", "成る", "する", "為る"):   # not 仲間になってくれる
                return True             # 君に作ってあげよう (recall test 8)
            if nxt not in ("の", "こと", "ように", "よう", "と", "か"):
                return False
    return False


def _pos(t) -> str:
    from .sentence_parser import pos_text
    return pos_text(t[2], t[3])


def _kinds(t) -> set:
    from .sentence_parser import kinds_of
    return kinds_of(t[2], t[3])


def _ichidan_word(s: str) -> bool:
    """s is an ichidan verb as written (込める), not a conjugated form."""
    from .sentence_parser import lookup_full, kinds_of
    w = lookup_full(s)
    return bool(w) and w[2] is None and "v1" in kinds_of(w[0], w[1])


_NEVER_SEARCHED_RX = [(g, re.compile(rx)) for g, rx in [
    ("buri", "(?:久し|ひさし)ぶり|[" + "0-9０-９一二三四五六七八九十百千何数" + "]+(?:年|か月|ヶ月|カ月|箇月|日|週間|時間|年間|日間)ぶり"),
    ("kke", "(?<=[だた])っけ(?=[？?。！!、」]|$|ね|な|か)"),           # not あっけない, 見っけ
    ("gachi", "(?<=[ぁ-ゖ一-鿿])(?<!が)がち(?=[だなでのにじです。、]|$)"),
    ("beku", "(?<!なる)(?<!成る)(?<=[うくぐすつぬぶむる])べく(?!して|もな|も無)"),   # not なるべく / 成るべく (sample 11)
    ("nari", "(?<!なり)(?<![くし]なり)(?<=[うぐすつぬぶむる])なり[、，]"),   # 入るなり (not 大きくなり、, 煮るなり焼くなり)
    ("taru", "(?:親|子|学生|医者|男|女|教師|人|王|国民|社会人|大人|武士|紳士|棟梁|指導者|政治家|先生|教育者|"
             "母|父|夫|妻|リーダー|プロ|主人|兄|姉|長男|師|弟子|君主|国家|政府|警察官|裁判官|学者)たる(?=者|もの|べき)"),
    ("kiri", "(?:一人|二人|三人|ふたり|ひとり|一度|一回|これ|それ|あれ|た)っ?きり(?![としの]|だす|出)"),
    ("mono-mon", "(?:(?:だ|ない|たい|しい|かった)もん|(?:(?<!ん)|(?<=[ないるた]ん))だもの)(?=[。！？!?」]|$|ね|よ|な(?!ど))"),
    ("koto-instruction", "(?<=ない)こと(?=[。！!]|$)"),
    ("toka-hearsay", "^(?!.*とか.*とか)[^。]*?(?:(?:んだ|だ)とか(?:で[、，]|(?=[。！？!?」]|$))"
                     "|(?:る|た|い)とか(?:で[、，]|(?=[。！？!?])))"),   # not a とか list or a bare fragment
    ("meku", "(?:春|夏|秋|冬|謎|秘密|冗談|皮肉|色|艶|古|子供|説教|脅迫|作り事)め(?:く|いた|いて|いている|かし)"),
    ("ge", "(?:悲し|寂し|さびし|楽し|嬉し|うれし|苦し|恥ずかし|自信あり|意味あり|満足|得意|不安|不満|退屈|怪し|"
           "惜し|危な|おかし|物欲し|懐かし|誇らし|親し|心細|言いた|知りた|眠た|恐ろし|怖)げ(?=[なにだで]|$)"),
    ("mai", "(?<=[くぐすつぬぶむる])(?<!しま)(?<!ふる)(?<!振る)まい(?=[とか。、]|$|が|ね)"),   # not ふるまい (sample 9)   # not うまい; あるまいし is its own point
    ("dani", "(?:想像|夢|考える|聞く|思う|一顧|微動)だに"),
    ("tsu-tsu", "持ちつ持たれつ|行きつ戻りつ|抜きつ抜かれつ|浮きつ沈みつ|追いつ追われつ|差しつ差されつ|押しつ押されつ"),
]]


# ── parse cache ───────────────────────────────────────────────────────────────
# Grammar ids per sentence text, kept on disk so Refresh doesn't re-parse
# every sentence. The first parse in an Anki session costs ~2 s (the parser's
# lookups warm up); with the cache only new or edited sentences are parsed.
# The result depends only on the add-on's own code and bundled data, so the
# cache is keyed by those files' sizes + modification times: any change to
# them (an add-on update, a parser fix) throws it away. Kept in user_files/,
# which Anki preserves across add-on updates.

_PCACHE_PATH = os.path.join(_HERE, "user_files", "parse_cache.json")
_PCACHE_FILES = ("sentence_parser.py", "grammar_data.py", "jlpt_data.py", "freq_data.py", "freq_splits.py",
                 "kanji_data.py", "meanings.py", "meanings.json", "grammar_jlpt.json",
                 "freq_bccwj.txt", "jlpt_n5.txt", "jlpt_n4.txt", "jlpt_n3.txt",
                 "jlpt_n2.txt", "jlpt_n1.txt", "kana_ok.txt", "kana_usual.txt", "kinds_fix.txt")
_pcache: dict | None = None   # {"sig": str, "ids": {text: [ids]}}


def _parse_sig() -> str:
    import hashlib
    from . import freq_data
    h = hashlib.sha1(freq_data.LIST_VERSION.encode())
    for name in _PCACHE_FILES:
        try:
            st = os.stat(os.path.join(_HERE, name))
            h.update(f"{name}:{st.st_size}:{st.st_mtime_ns}\n".encode())
        except OSError:
            h.update(f"{name}:-\n".encode())
    return h.hexdigest()[:16]


def _cached_ids() -> dict:
    """text → grammar ids from the cache, or {} if it's missing or stale."""
    global _pcache
    sig = _parse_sig()
    if _pcache is None or _pcache.get("sig") != sig:
        try:
            with open(_PCACHE_PATH, encoding="utf-8") as f:
                _pcache = json.load(f)
        except Exception:
            _pcache = {}
        if not isinstance(_pcache, dict) or _pcache.get("sig") != sig:
            _pcache = {"sig": sig, "ids": {}}
    return _pcache["ids"]


def _save_ids(ids: dict):
    """Store this run's sentences only, so edited or deleted ones drop out."""
    global _pcache
    _pcache = {"sig": _parse_sig(), "ids": ids}
    try:
        os.makedirs(os.path.dirname(_PCACHE_PATH), exist_ok=True)
        with open(_PCACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(_pcache, f, ensure_ascii=False, separators=(",", ":"))
    except Exception:
        pass   # a cache that can't be written just means a slower Refresh


# ── analysis ──────────────────────────────────────────────────────────────────

# Written forms that are also everyday words, so a vocab card for them is
# the word, not the grammar (出す "take out" ≠ 〜出す "start to").
_WORD_CARD_NOT_GRAMMAR = {"始める", "終わる", "続ける", "出す", "切る", "切れない", "かける", "合う", "直す",
                          "抜く", "得る", "得ない", "かねる", "かねない", "やすい", "にくい", "向き", "向け"}


def word_card_ids(deck: str, mappings: list, seen_only: bool = True) -> dict[int, tuple[str, list[str]]]:
    """nid → (word, grammar ids) for the deck's vocab cards whose word field
    is exactly a grammar point's written form (〜 and HTML dropped): でも →
    〜ても/でも (even if) and 〜でも (suggestion). Only the word field, never
    the dictionary or example fields. Kanji-only forms (方, 中, 以上, 手前)
    are left out: as a vocab card they're usually the word's other meaning."""
    from . import sentence_parser
    out: dict[int, tuple[str, list[str]]] = {}
    if not deck:
        return out
    idx = key_index()
    for nid, note in card_state.deck_notes(deck, seen_only).items():
        for m in mappings:
            if m.get("note_type") and m["note_type"] != note.type_name:
                continue
            f = m.get("field", "")
            if f and f in note:
                word = sentence_parser.clean(note[f]).strip()
                key = _jp_only(word)
                ids = idx.get(key) if key else None
                if (ids and key not in _WORD_CARD_NOT_GRAMMAR
                        and any(0x3041 <= ord(c) <= 0x30FF for c in key)):
                    out[nid] = (word[:40], list(ids))
                break
            if m.get("note_type"):       # an all-types row that doesn't fit: next row
                break
    return out


def source_config(cfg: dict) -> dict:
    """mode "sentence" (default: the sentence parser, phase 3) or "fields"
    (a grammar deck's field). Marking points found by hand (middle-click)
    always works, as for words and kanji (owner 2026-10-09: not a setting).
    An old saved mode "none" reads as "sentence"."""
    src = dict(cfg.get("grammar_source") or {})
    if src.get("mode") not in ("sentence", "fields"):
        src["mode"] = "sentence"
    src.pop("manual", None)
    src.setdefault("deck", "")
    src.setdefault("mappings", [])
    return src


def analyse(cfg: dict, overrides=None) -> dict:
    """{source, deck, stats{id: score/cards/best/words}, levels, known,
    unmatched: [field texts of grammar-deck notes that matched no point]}"""
    from aqt import mw
    from anki.utils import ids2str

    src = source_config(cfg)
    stats_in: dict[str, dict] = {}
    unmatched: list[str] = []
    note_ids: dict[int, tuple[str, list[str]]] = {}
    if src["mode"] == "sentence":
        # The sentence fields of the vocab deck's note-type mappings.
        from . import sentence_parser
        deck = cfg.get("deck_name", "")
        cached, fresh = _cached_ids(), {}
        # Never-studied cards too: they don't make a point known, but its
        # tile shows it's in your deck (owner 2026-10-17).
        for nid, text in sentence_parser.sentence_texts(
                deck, cfg.get("field_mappings", []), seen_only=False).items():
            ids = cached.get(text)
            if ids is None:
                ids = sentence_ids(text)
            fresh[text] = ids
            if ids:
                note_ids[nid] = (text[:40], ids)
        if fresh != cached:
            _save_ids(fresh)
        # A vocab card whose word is itself a grammar form (でも, ながら,
        # つつ) counts for every point written that way: a good dictionary
        # on the card explains all its uses (owner 2026-10-17).
        for nid, (word, ids) in word_card_ids(deck, cfg.get("field_mappings", []), seen_only=False).items():
            old = note_ids.get(nid, ("", []))[1]
            note_ids[nid] = (word, old + [g for g in ids if g not in old])   # "Your cards: でも"
    else:
        deck = src["deck"]
    if src["mode"] == "fields" and deck and src["mappings"]:
        for nid, note in card_state.deck_notes(deck, seen_only=False).items():
            model = note.type_name
            for m in src["mappings"]:
                if m.get("note_type") and m["note_type"] != model:
                    continue
                f = m.get("field", "")
                if f and f in note and note[f].strip():
                    ids = match_field(note[f])
                    text = field_text(re.sub(r"<br\s*/?>", " ", note[f], flags=re.I))[:40]
                    if ids:
                        note_ids[nid] = (text, ids)
                    elif text:
                        unmatched.append(text)
                    break
    cids = mw.col.find_cards(card_state.deck_search(deck, seen_only=False)) if deck and note_ids else []
    if cids:
        for nid, ctype, queue, ivl, factor, lapses, cdata in mw.col.db.all(
                "select nid, type, queue, ivl, factor, lapses, data from cards "
                f"where id in {ids2str(cids)}"):
            if nid not in note_ids:
                continue
            text, ids = note_ids[nid]
            state = card_state.NEW if queue == -1 else card_state.card_state(ctype, ivl)
            learned = state >= card_state.LEARNING          # studied (owner 2026-10-21)
            sc = card_score(ivl, factor, lapses, cdata) if learned else None
            for gid in ids:
                s = stats_in.setdefault(gid, {"scores": [], "best": -1, "words": {}})
                if learned:
                    s["scores"].append(sc)
                s["best"] = max(s["best"], state)
                if state > s["words"].get(nid, (None, -1))[1]:
                    s["words"][nid] = (text, state)

    stats = {}
    for gid, s in stats_in.items():
        sc = s["scores"]
        stats[gid] = {
            "score": sum(sc) / len(sc) if sc else None,
            "cards": len(sc),
            "best":  max(s["best"], card_state.NEW),
            "words": sorted(((t, st, n) for n, (t, st) in s["words"].items()),
                            key=lambda w: -w[1]),
        }
    weigh_contexts(stats)       # more cards (contexts) → a little stronger
    found = {k.split("\t", 1)[0] for k in overrides.found} if overrides else set()
    known = {g for g, s in stats.items() if s["cards"]} | (found & set(data()))
    return {"source": src, "deck": deck, "stats": stats, "levels": level_ids(),
            "known": known, "unmatched": sorted(set(unmatched)),
            "has_sentences": any(m.get("sentence_field") for m in cfg.get("field_mappings", [])),
            "sentence_fields": field_labels(cfg.get("field_mappings", []), "sentence_field")}


def level_counts(gres: dict, suspended: set = frozenset()) -> dict:
    out = {}
    tk = tt = 0
    for lvl in LEVELS:
        ids = [g for g in gres["levels"].get(lvl, []) if g not in suspended]
        k = sum(1 for g in ids if g in gres["known"])
        out[lvl] = (k, len(ids))
        tk += k; tt += len(ids)
    out["All"] = (tk, tt)
    return out
