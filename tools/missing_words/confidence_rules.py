# Word Addition Project, round 2 (owner 2026-10-20): the owner's review of
# Sure / Likely (owner_choices_2026-10-20.json) and the rules agreed after it,
# applied on top of confidence_3900.py. final() gives every top-3,900
# candidate its level (or "skip") and, where a rule or the owner changed it,
# the reason.
#
# Agreed rules (owner's words in quotes):
#   R-N2   N2 = working Japanese: office, IT, consumer, everyday news/society
#          ("N2 makes you a functional employee for the general job market").
#   R-N1   N1 = legal, finance (technical), government, academic, history,
#          military, abstract/editorial ("abstract, legal, or editorial
#          Japanese") — these are N1 words, not "unsure".
#   R-TACHI plurals with 〜たち / 〜ら and 〜自身 compounds are skipped; only
#          私たち stays ("the most basic and common application of たち").
#          〜的 / 〜性 words stay (性 doesn't always change the meaning
#          predictably).
#   R-INTJ  interjections stay ("put interjections back"): they fill JLPT
#          listening.
#   R-FANT  fantasy / fiction words are skipped unless real-world use
#          overlaps.
#   R-PAIR  opposite pairs share a level (上記/下記, 前年/翌年, 高齢/高齢者).
#   R-NOTJLPT words the test would never use (キス).
#   R-FOOD  ingredients N3, Japanese-cuisine items N2 (owner's own picks kept).

OWNER_FILE = "owner_choices_2026-10-20.json"

# Explicit decisions after the owner's review: word → (level, reason).
OVERRIDES = {
    # owner, 2026-10-20
    "わかりやすい": ("N3", "owner: put on N3"),
    "えっ": ("N4", "R-INTJ: interjections back"), "ほら": ("N4", "R-INTJ: interjections back"),
    "へえ": ("N4", "R-INTJ: interjections back"), "おい": ("N3", "R-INTJ: interjections back"),
    "ううん": ("N3", "R-INTJ: interjections back"),
    "キス": ("skip", "R-NOTJLPT: owner, never on the test"),
    "クリック": ("N2", "R-N2: web / form instructions are common in N3–N2 reading (owner thought never on the test)"),
    "人たち": ("skip", "R-TACHI: only 私たち keeps 〜たち"),
    "私自身": ("skip", "R-TACHI: 〜自身 compound"), "自分自身": ("skip", "R-TACHI: 〜自身 compound"),
    "魔法": ("skip", "R-FANT: fantasy"), "姫": ("skip", "R-FANT: fantasy"), "剣": ("skip", "R-FANT: fantasy"),
    "竜": ("skip", "R-FANT: fantasy"), "霊": ("skip", "R-FANT: supernatural"),
    "上記": ("N3", "R-PAIR: same level as 下記 (owner N3)"),
    "翌年": ("N3", "R-PAIR: same level as 前年 (owner N3)"),
    "高齢者": ("N3", "R-PAIR: same level as 高齢 (owner N3)"),
    # R-N2: office / IT / society words still at N3
    "送信": ("N2", "R-N2: IT / office"), "受信": ("N2", "R-N2: IT / office"), "検索": ("N2", "R-N2: IT / office"),
    "アクセス": ("N2", "R-N2: IT / office"), "スタッフ": ("N2", "R-N2: workplace"), "社員": ("N2", "R-N2: workplace"),
    "専門家": ("N2", "R-N2: society word, like 政治家 (owner N2)"),
    "弁護士": ("N2", "R-N2: society word, like 政治家 (owner N2)"),
    "画像": ("N2", "R-N2: IT"), "アドレス": ("N2", "R-N2: IT"), "サイト": ("N2", "R-N2: IT"),
    "ブログ": ("N2", "R-N2: IT"), "リンク": ("N2", "R-N2: IT"), "ウェブ": ("N2", "R-N2: IT"),
    "起動": ("N2", "R-N2: IT"), "更新": ("N2", "R-N2: IT / office"), "オプション": ("N2", "R-N2: consumer / IT"),
    "プロジェクト": ("N2", "R-N2: workplace"),
    # Unsure, N3 suggestions
    "メモリー": ("N2", "R-N2: IT"), "ディスク": ("N2", "R-N2: IT"), "マシン": ("N2", "R-N2: IT / workplace"),
    "リーグ": ("N2", "R-N2: sports news"), "ブラック": ("N2", "R-N2: ブラック企業 is a common work term"),
    "ロック": ("N2", "R-N2: locking a phone / door (consumer)"),
    "グリーン": ("skip", "katakana stand-in for 緑; the test uses the native word"),
    "サイド": ("skip", "katakana stand-in for 横 / 側; the test uses the native words"),
    # Unsure, N2 suggestions
    "わし": ("N2", "real speech (older men, western Japan), not only fiction"),
    "オークション": ("N2", "R-N2: consumer"), "引き続く": ("N2", "R-N2: office / news"),
    "将軍": ("N1", "R-N1: history"), "金利": ("N2", "R-N2: consumer finance (loans, savings)"),
    "帝国": ("N1", "R-N1: history"), "海軍": ("N1", "R-N1: military"), "陸軍": ("N1", "R-N1: military"),
    "米軍": ("N1", "R-N1: military"), "まちづくり": ("N2", "R-N2: everyday news / society"),
    "日米": ("N2", "R-N2: everyday news"), "初心": ("N2", "R-N2: general (初心に返る)"),
    "受診": ("N2", "R-N2: consumer health"), "次元": ("N1", "R-N1: abstract"),
    "巨人": ("N1", "R-N1: editorial (知の巨人); real-world use, so not fantasy"),
    "皇帝": ("N1", "R-N1: history"), "ホルモン": ("N2", "R-N2: health / food"), "母子": ("N2", "R-N2: health / society (母子手帳)"),
    "ねた": ("N2", "R-N2: everyday (話のねた)"), "サーバー": ("N2", "R-N2: IT"), "投手": ("N2", "R-N2: sports news"),
    "同年": ("N1", "R-N1: editorial"), "容量": ("N2", "R-N2: IT / consumer"), "前年度": ("N2", "R-N2: office"),
    "出力": ("N2", "R-N2: IT"), "機種": ("N2", "R-N2: consumer (phone models)"), "検診": ("N2", "R-N2: consumer health"),
    # Unsure, N1 suggestions that are office / consumer / everyday news (R-N2)
    "落札": ("N2", "R-N2: consumer (online auctions)"), "出品者": ("N2", "R-N2: consumer (online selling)"),
    "構築": ("N2", "R-N2: workplace (システム構築)"), "拠点": ("N2", "R-N2: workplace"),
    "業種": ("N2", "R-N2: job hunting"), "人員": ("N2", "R-N2: workplace"), "広報": ("N2", "R-N2: company department"),
    "調達": ("N2", "R-N2: workplace"), "回線": ("N2", "R-N2: consumer IT"), "既存": ("N2", "R-N2: workplace"),
    "推移": ("N2", "R-N2: office reports (売上の推移)"), "株価": ("N2", "R-N2: everyday news"),
    "開設": ("N2", "R-N2: consumer (口座開設)"), "免疫": ("N2", "R-N2: health news"), "接種": ("N2", "R-N2: health news"),
    # No group: whole formal terms (R-N1)
    "地方公共団体": ("N1", "R-N1: government term"), "政府委員": ("N1", "R-N1: government term"),
}
# Every other Unsure word with an N1 suggestion: R-N1 (legal, finance, government, academic).
UNSURE_N1_REASON = "R-N1: legal / finance / government / academic Japanese"


def final(cands, judge, owner_choices):
    """cands: candidate rows (rank, d …); judge: confidence_3900.judgements();
    owner_choices: {"r<rank>": value}. Returns {rank: (value, reason or "",
    value the owner last saw)}."""
    out = {}
    for x in cands:
        tier, lvl = judge[x["d"]]
        dflt = "?" if tier == "unsure" else (lvl or "skip")
        seen = owner_choices.get("r%d" % x["rank"], dflt)
        if x["d"] in OVERRIDES:
            v, why = OVERRIDES[x["d"]]
        elif tier == "unsure" and lvl == "N1":
            v, why = "N1", UNSURE_N1_REASON
        elif "r%d" % x["rank"] in owner_choices:
            v, why = seen, ""
        else:
            v, why = (lvl or "skip"), ""
        if tier == "unsure" and v == "?":
            raise ValueError("undecided: " + x["d"])
        out[x["rank"]] = (v, why, seen)
    return out
