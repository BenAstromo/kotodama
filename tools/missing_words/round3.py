# Word Addition Project, round 3 (owner 2026-10-28): frequency #3,901–6,000,
# judged with the round-2 rules (confidence_rules.py) plus the fit-check
# reasoning (fit_check.py): levels follow the official level descriptions
# and how the lists treat similar words; pattern words, katakana stand-ins,
# word pieces and document-register terms are skipped.
#
# LEVELS: level → words. SKIPS: reason id → (explanation, words).
# Every candidate appears exactly once (checked by __main__).

LEVELS = {
"N4": """バイト アイス カフェ 結婚式 桃 ミリリットル わあ えび 芋 片手 週末 右側 左側 コンビニ にんにく
寿司 駅前 ハム ミリグラム じゃがいも ねぎ セント しょうが キャベツ レモン 片方 チョコレート いか
いちご きのこ 奥様 チョコ お願い お湯 お世話 きゅうり みかん かに バナナ たこ カラオケ""",

"N3": """マウス 熊 フォルダー 日常生活 最小 北部 オリンピック エリア 外側 最悪 本社 次回 ペース 研究者
ジャケット 一口 そいつ 国道 手作り 動画 仲良く 市長 絵本 チェーン 委員会 順位 キャラクター やる気
参加費 キャラ ボリューム ロボット マネージャー バージョン イラスト 食材 小さじ 喫煙 レシピ 苦しみ
再開 報告書 ダウンロード マット 委員長 初心者 やばい 毎回 アレルギー 大豆 だし 参加者 オペラ
裁判官 寝室 ハート 亀 見た目 いじめ 海水 からす 店内 投稿 ボトル なあ キロカロリー 交通事故
チャレンジ 不安定 添付 知り合う 録画 不十分 持ち物 指先 ばらばら デジカメ マナー クリニック 西側
町内 インチ カップル 市役所 ラッキー 繰り返し シングル クレジット 西部 グッズ
リラックス リビング 眠り ホット きつね 顔色 手足 警察官 ショッピング 持ち帰る キャンセル 少量
初日 メイン 羊 昆布 レンタル いまいち 都内 パスワード 年上 本店 一人暮らし 返信 残業 入国 通話
保育園 担任 足音 観光客 ライオン 翌朝 会費 休館 タッチ お尻""",

"N2": """届け出 パネル 里 クリア 最適 作り上げる 体質 バブル 物件 巻き込む レーザー まとも 在宅 文庫
虐待 市販 黒人 落札者 ふれあい リアル 両国 音声 取り込む 東南 戦前 大規模 価値観 一覧 フィールド
容疑 入り込む 半数 社内 不法 略 収納 メーク リング ピーク 振込 変わり 自治体 ヘクタール 書き込む
歌詞 読み取る 発信 グローバル パーツ 名乗る 体内 見回す 遺伝子 同期 レート 乗り越える 一行 天使
フレーム 持ち主 大地 学園 連載 入金 セミナー マネージメント 健診 覗き込む 陸上 アクション 現役
不快 軍人 指名 ぎりぎり 数々 スポット セキュリティー 指導者 有害 スムーズ 探偵 開業 中期 引き継ぐ
第三者 自社 通報 持ち出す ミサイル 白人 マニュアル 糖 タンク ほう パートナー 久々 備考 駆けつける
見張る 飲食 処方 キリスト教 運行 王国 キャッシュ 取り消し 相性 障害者 内外 目撃 木造 ログ 死後
頼り 私的 上部 合理的 早朝 ばれる ゆったり 入居 製造業 大企業 週刊 耐震 無意識 ちっ サロン そうそう
高額 ドーム 日数 送付 ストック アピール ゲット 円高 キャンペーン 自国 若手 所要 アーチスト 賃貸
予選 差し込む 被災 シフト 風味 ふん 庭園 上流 振り込む 前向き メジャー まじ 言い換える 着用
カルシウム ストレート パフォーマンス 年々 キーワード テクニック 税率 奇跡 無理やり エコ プレート
必着 データーベース 五輪 コラム 副作用 大国 同行 北方 タグ 総数 吸い込む 前期 文字通り 貼り付ける
やたら 淡い 心地よい 院長 飲料 検定 ゾーン はっと 対象者 幹事 変身 初代 選択肢 違和感 生き残る
一目 整形 浮かび上がる 端末 ターン ニット クール スペシャル アレンジ 転職 ライバル 浸かる 年数
後日 月額 こだわり パッケージ 手数料 レイアウト ボス フォント 反面 見当たる ランク ギャラリー
オーダー ラウンド 先着順 一員 何者 仮面 食生活 全額 ジェット 定番 戸惑う 銀河 振替 平面 うつ病
アプリケーション 後方 次男 エピソード 支部 抱きしめる""",

"N1": """配当 検証 粒子 受給 懸念 広域 納税 おおむね 笑み 法令 指針 半身 子宮 振るう 売却 任意 考察
出資 民法 解明 枠組み 景観 借り入れ 土壌 侵害 省庁 闘争 遂行 税制 解析 移植 実証 遺族 回避 一族
一環 オーナー ハード 水質 生成 浸透 臨床 品目 付加 除去 奴隷 艦隊 療養 他者 公益 古墳 認可 補正
収録 いささか 馴染む 葬儀 歩行 通商 小児 薬剤 破綻 当面 出土 開示 分泌 増殖 代替 上場 陛下 某
野郎 薬物 見込む 馴染み 実務 遺言 同社 欲求 卸売 明記 検挙 浄化 生態 提起 判明 解する 負荷
申し立て 乗り出す 示唆 手形 買収 検出 解体 立地 新設 総裁 もとより 当事者 形状 潜在 名義 殺害
工程 癒す 事実上 あほう 表記 脅威 親族 継承 信託 啓発 変形 喪失 酵素 客観的 支所 顕著 源泉
大名 幻想 財団 戦場 下落 支障 慢性 大将 主流 一向 着実 参入 適合 出荷 変数 集積 系列 推計 入所
流動 部位 鑑定 提言 頻度 守護 参画 反論 留意 広大 表彰 奉行 法定 囚われる 遺体 麻薬 代謝
メカニズム 需給 強度 養子 処遇 後継 委ねる 戦車 甲斐 仕草 急増 言及 融合 防御 選定 因子
リース 閣僚 肝臓 乳房 新生 出願 活性化 仮説 更生 算出 装着 駆る 修復 事業者 所得税 抽出 損傷
建造 原価 史料 国債 眼差し 打ち出す 腫瘍 覚醒 騎士 信念 中核 称える 名目 発症 周知 凄まじい 染色
宅地 乳幼児 突入 沙汰 近隣 均等 刑法 照射 あたかも 特異 潜める 妄想 実体 書記 相次ぐ 潜む 民事
感性 師匠 横たわる 復元 姑 合戦 朝廷 坊主 種子 在日 槍 民主主義 即 採取 再編 窒素 施工 隣接 百姓
視界 撤退 対外 局面 盛り込む 自律 境内 応答 天文 犯行 不倫 発酵 培養 創業 擁護 発現 顧問 塗装
習得 言い切る 聴取 発注 低迷 阻害 無償 曰く 露出 不能 欲 飛躍 戦国 引き上げ 宴 拍子 計測 皇后
高値 下回る 抜群 管轄 類型 多発 主力 付与 受注 早々 引きつける 包括 決済""",
}

SKIPS = {
"pattern": ("Pattern word: built from a listed word with a regular ending (〜的, 〜さ, 〜性, 〜ら / 達, 〜人 for a nationality or count, 〜中, 〜とも, どう + にも). The lists teach the ending once.",
    """社会的 重要性 美しさ 二人とも 圧倒的 自動的 伝統的 一時的 効率的 午前中 安全性 代表的 徹底的 実質的
    寒さ アメリカ人 世界的 奴ら 重さ 中国人 魅力的 十人 今後とも 問い合わせ先 定期的 決定的 女達 危険性
    速さ 国々 結果的 一方的 政治的 根本的 ユダヤ人 一位 数人 典型的 歴史的 現実的 深さ 計画的 俺ら
    全体的 全国的 前年比 どうにも 六人 研究開発 早く 古く 区民"""),
"oform": ("Polite ご on a listed word that people mostly use bare (協力). The お / ご form is listed only when it is the usual form, as the lists do with お茶 or お互い; a card for either form counts.",
    """ご協力"""),
"piece": ("Not a word a learner studies on its own: a suffix or counter reading, part of a longer listed word (滅多に, しきりに, 配偶者, 調味料), or a grammar ending (〜放題, 挙句).",
    """座 意気 精 サン 軽 分間 ん 宮 勿体 連 商工 弁 取り 省 配偶 買い 馳走 詞 しゃべり 糖尿 書 石 警視
    滅多 姉 要 銭 民 申 月 昭 カ年 乗 師 調味 引き 抜き 医薬 公 修道 木 腺 しきり 知 盤 農産 違和 基 兼
    一昨 理 好奇 直 待ち 黄 受話 農 館 放題 挙句 助 坊 菜 刑務 衆議 自家 分科 症候 祝 経 生う 臥せる
    あん 聞かす 愛す こと自体 しかり やっぱ めちゃ けど 露"""),
"katakana": ("Katakana stand-in for a native word the test would use (like グリーン and サイド in round 2).",
    """ライフ オール ショート ファースト エアー パーク ピース ファミリー ロード フォー レッド シティー ビッグ
    マップ ヘッド プラザ ショット ロング ユー ボード フロー ド ブック フォト ペーパー アイ ベビー ヘア
    ドラッグ マルチ ウィン シルバー オート ゴールド リア マイクロ ゴー ミスター ティー セブン マクロ
    アット ウエート ナイト フルーツ ダイアローグ タウン グッド オブジェクト ソフトウェア"""),
"register": ("Document or official-register term: high only because the corpus includes laws, white papers and Diet records. N1 reads editorials and news, not these documents.",
    """税務 前掲 本件 郵政 答申 判例 履行 償却 庁舎 公社 政令 所管 価額 国務大臣 条項 歳出 経常 損益 税額
    定形 算定 部会 貸借 贈与 法制 公庫 弁済 資する"""),
"name": ("Proper noun or product name; the lists have none (no 江戸, 明治).",
    """ウインドーズ 自衛隊 エクセル 農協"""),
"notjlpt": ("A word the test wouldn't use: sexual, discriminatory or dated (like キス in round 2).",
    """エッチ 性的 部落 痴呆 リンパ"""),
}

SHORT = {"pattern": "Pattern word", "oform": "Polite form, usually said bare", "piece": "Word piece",
         "katakana": "Katakana stand-in", "register": "Document term", "name": "Name",
         "notjlpt": "Not test material"}


def judgements():
    out = {}
    for lv, block in LEVELS.items():
        for w in block.split():
            out[w] = (lv, "")
    for rid, (why, block) in SKIPS.items():
        for w in block.split():
            out[w] = ("skip", rid)
    return out


if __name__ == "__main__":
    import collections, json, os, sys
    sys.stdout.reconfigure(encoding="utf-8")
    HERE = os.path.dirname(os.path.abspath(__file__))
    cands = [x for x in json.load(open(os.path.join(HERE, "wa_candidates.json"), encoding="utf-8"))
             if 3900 < x["rank"] <= 6000]
    j = judgements()
    words = [x["d"] for x in cands]
    seen = collections.Counter()
    for lv, block in LEVELS.items():
        seen.update(w for w in block.split())
    for rid, (_, block) in SKIPS.items():
        seen.update(w for w in block.split())
    print("twice:", [w for w, n in seen.items() if n > 1])
    print("missing:", [w for w in words if w not in j])
    print("extra:", [w for w in j if w not in set(words)])
    print(collections.Counter(v[0] for w, v in j.items() if w in set(words)))
    # Review page (Artifact https://claude.ai/artifact/NHt9rMw2icW5aSLuNxSLuq, db doc review/round3):
    #   py -I tools/missing_words/round3.py <out.html>
    if len(sys.argv) > 1:
        import html
        rows = [{"rank": x["rank"], "d": x["d"], "r": "" if x["r"] == x["d"] else x["r"], "m": x["m"],
                 "g": j[x["d"]][0], "s": j[x["d"]][0], "why": j[x["d"]][1]} for x in cands]
        groups = {lv: [lv, f"Pre-set to {lv}. Change any word you'd put elsewhere."] for lv in LEVELS}
        groups["skip"] = ["Skip", "Pre-set to skip, with the reason under each word. Pick a level to add one after all."]
        skipwhy = {rid: [SHORT[rid], why] for rid, (why, _) in SKIPS.items()}
        n_skip = collections.Counter(v[1] for v in j.values() if v[0] == "skip")
        lis = "".join(f"<li><b>{html.escape(SHORT[rid])}</b> ({n_skip[rid]}): {html.escape(why)}</li>"
                      for rid, (why, _) in SKIPS.items())
        add = sum(1 for r in rows if r["s"] != "skip")
        tpl = open(os.path.join(HERE, "round3_template.html"), encoding="utf-8").read()
        js = lambda o: json.dumps(o, ensure_ascii=False).replace("</", "<\\/")
        out = (tpl.replace("__ROWS__", js(rows)).replace("__GROUPS__", js(groups)).replace("__SKIPWHY__", js(skipwhy))
                  .replace("__SKIPLIST__", lis).replace("__ADD__", str(add)).replace("__SKIP__", str(len(rows) - add)))
        open(sys.argv[1], "w", encoding="utf-8").write(out)
        print(len(rows), "rows →", sys.argv[1])
