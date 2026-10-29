# Word Addition Project, fit check (owner 2026-10-28): "do the additions
# really fit the purpose, theme and logic of each level?" Research behind
# the groups below (sources in the page):
#   - JLPT publishes no word lists since 2010 (FAQ); levels are defined by
#     can-do descriptions. N4/N5 = classroom Japanese, N3 = bridge, N2/N1 =
#     real-life Japanese (N1: editorials, abstract texts).
#   - The real, unpublished post-2010 table (Japan Foundation report, 2008):
#     chosen by frequency + teacher judgement + the old list, aimed at
#     10,000-18,000 words, affixes listed as their own entries (〜的), and
#     everyday modern words placed low (うどん / エアコン N5, ATM N4,
#     駅ビル N3). Specialist terms "ordinary people don't need" are left out.
#   - Our own lists: affixes are entries (的 性 不 全 昨 方), predictable
#     derivatives are mostly absent; computer words sit at N4/N3, job titles
#     at N4/N3, food at N5/N4.
# GROUPS: id → (title, explanation). SUGGEST: word → (group, suggested
# value). The page shows the level each word has now (round 2) next to the
# suggestion; the owner's answers go to db doc fit/choices.
GROUPS = {
    "pattern": ("Pattern words",
        "The lists teach the ending once and leave out words it builds: 的 and 性 have their own entries, "
        "〜さ and 〜方 are N4 grammar. Only words whose meaning you can't guess are listed (目的, 積極的, 比較的, 仕方). "
        "Someone who knows 大きい and 〜さ already reads 大きさ. Kept: 本格的 and 公的 (meaning or reading isn't predictable), "
        "可能性 (used as one word everywhere), 私たち (your rule)."),
    "digital": ("Computer and job words",
        "The lists put computer words low: コンピューター, パソコン, ソフト, ファックス at N4; 情報, 通信, 操作, 機能, コピー at N3. "
        "Job titles too: 社長, 店員 N4; 同僚, 作家, 記者, 画家 N3. Everyday web words and job names fit N3 (ホームページ N4, "
        "next to メール and インターネット). You already moved 画像 and 検索 to N3. Technical words stay at N2: "
        "サーバー, メモリー, ディスク, 起動, 出力, 回線, 容量, 変換, ネットワーク, ユーザー, 更新."),
    "food": ("Food words",
        "Food sits low in the lists (肉, 野菜, 果物, 卵, 牛肉, 豚肉 N5; ぶどう N4) and in the official 2008 draft (うどん and 朝ごはん N5). "
        "Everyday vegetables and tofu fit N4. Cooking words for recipes fit N3 (N4–N3 can-do: simple instructions with pictures, e.g. how to cook)."),
    "pairs": ("Level matches",
        "Words whose closest list partner sits at another level. 昼食 is N3, so 朝食 and 夕食 belong there too. "
        "戦争 is N4 and 戦後 is ordinary news Japanese (戦後80年), so N2 rather than N1."),
    "register": ("Not test words",
        "High in the frequency list only because the corpus (BCCWJ) includes white papers, laws and Diet minutes, or because of a name. "
        "The official table leaves out specialist terms ordinary people don't need, and the lists have no proper nouns (no 江戸, 明治, 昭和). "
        "N1 reads editorials and news, not contracts or Diet records."),
}
SUGGEST = {
    # pattern words → skip
    **{w: ("pattern", "skip") for w in
       "大きさ 高さ 長さ 強さ 良さ 考え方 やり方 作り方 使い方 言い方 生き方 "
       "具体的 基本的 一般的 個人的 最終的 効果的 精神的 経済的 国際的 総合的 法的 それら 必要性".split()},
    # computer / job words
    **{w: ("digital", "N3") for w in
       "サイト ブログ クリック アドレス リンク ウェブ アクセス 送信 受信 入力 インストール "
       "社員 スタッフ 弁護士 専門家 政治家".split()},
    "ホームページ": ("digital", "N4"),
    # food
    **{w: ("food", "N4") for w in "トマト にんじん 玉ねぎ 大根 豆腐 豚".split()},
    **{w: ("food", "N3") for w in "ごま 麺 大さじ".split()},
    # level matches
    "朝食": ("pairs", "N3"), "夕食": ("pairs", "N3"), "戦後": ("pairs", "N2"),
    # register / name
    **{w: ("register", "skip") for w in
       "朝日 江戸時代 政府委員 地方公共団体 当該 計上 納付 登記 譲渡 債権 商法 貸付 前述 本書".split()},
}
# Extra one-line notes for single words.
NOTES = {
    "朝日": "Rank inflated by 朝日新聞 in the newspaper part of the corpus; \"morning sun\" itself is rare.",
    "江戸時代": "A proper noun (an era name).",
    "政府委員": "A Diet-record term; the post was abolished in 1999.",
    "地方公共団体": "The legal name; even the everyday 自治体 isn't on the lists.",
    "本書": "\"This book\": frequent because the corpus is full of books talking about themselves.",
    "前述": "Written-document word (\"as stated above\"); borderline, editorials can use it.",
    "必要性": "必要 (N4) + 性 (N3), meaning fully predictable.",
    "それら": "それ + 〜ら; the lists have 彼ら but no other 〜ら words.",
    "ホームページ": "Same level as メール and インターネット.",
    "豚": "豚肉 is N5.",
}


if __name__ == "__main__":
    import json, os, sys
    sys.stdout.reconfigure(encoding="utf-8")
    HERE = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, HERE)
    import confidence_3900 as C
    import confidence_rules as R
    # current levels = round 2 rules + the owner's round-2 answers (db doc review/round2, saved as JSON)
    r2 = json.load(open(sys.argv[1], encoding="utf-8"))["choices"] if len(sys.argv) > 1 else {}
    cands = [x for x in json.load(open(os.path.join(HERE, "wa_candidates.json"), encoding="utf-8")) if x["rank"] <= 3900]
    own = json.load(open(os.path.join(HERE, R.OWNER_FILE), encoding="utf-8"))["choices"]
    res = R.final(cands, C.judgements(), own)
    rows, seen = [], set()
    for x in cands:
        if x["d"] not in SUGGEST:
            continue
        now = r2.get("r%d" % x["rank"], res[x["rank"]][0])
        g, s = SUGGEST[x["d"]]
        if now == s:
            continue
        seen.add(x["d"])
        rows.append({"rank": x["rank"], "d": x["d"], "r": "" if x["r"] == x["d"] else x["r"], "m": x["m"],
                     "g": g, "now": now, "s": s, "note": NOTES.get(x["d"], "")})
    missing = set(SUGGEST) - seen
    if missing:
        print("not changed / not found:", " ".join(sorted(missing)))
    tpl = open(os.path.join(HERE, "fit_template.html"), encoding="utf-8").read()
    out = tpl.replace("__ROWS__", json.dumps(rows, ensure_ascii=False).replace("</", "<\\/")) \
             .replace("__GROUPS__", json.dumps(GROUPS, ensure_ascii=False).replace("</", "<\\/"))
    path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "fit_check.html")
    open(path, "w", encoding="utf-8").write(out)
    import collections
    print(len(rows), "suggestions", dict(collections.Counter(r["g"] for r in rows)), "→", path)
