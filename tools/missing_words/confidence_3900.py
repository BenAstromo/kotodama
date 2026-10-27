# Word Addition Project (owner 2026-10-19): the frequency words in the top
# 3,900 that no JLPT list covers, split by how confident we are that they
# belong on the lists ("so useful and common in modern Japanese that it
# wouldn't be surprising to see them on the test"), each with a level.
#   sure   — everyday / modern words; leaving them off looks like an oversight
#   likely — common general words, a bit more written or narrower
#   unsure — high mainly because the frequency corpus is heavy on news,
#            official papers, law and finance; or borderline — owner decides
#   no     — not a learner's word on its own: suffix / counter readings,
#            pieces of longer words, title fragments, fillers, counter
#            compounds (三人), ministry-name fragments
# Blocks: "tier level": words (whitespace-separated). Checked by
# tools/missing_words/check_confidence.py (every candidate once, no extras).

BLOCKS = {
"sure N5": """私たち 日本人 日本語 りんご 何人""",

"sure N4": """多く 人々 人たち 子供たち メール インターネット 野球 サッカー 夕食 朝食 トマト 豚
お店 お客さん お客様 右手 左手 両手 大きさ 高さ 長さ 強さ 休日 本日 皆様 チケット キッチン
携帯電話 電話番号 半年 いろんな ラーメン 豆腐 にんじん 玉ねぎ 大根 鶏 ゴルフ アニメ 彼氏
僕たち ねえ ほら へえ 中学生 ネット""",

"sure N3": """可能性 具体的 考え方 最大 国内 ちなみに 基本的 チェック 画面 昨年 一般的 社員 入力
男女 大量 検索 若者 後半 前半 イベント 子育て スタッフ やり方 間違いない 主な ボランティア
翌日 前日 昨夜 デジタル つい アドレス 親子 プロジェクト まだまだ ウイルス 各国 アドバイス
アクセス 作り方 使い方 言い方 生き方 自分自身 我が家 不可能 消費者 わかりやすい 仕方ない 人数
労働者 被害者 あいつ こいつ 俺たち 僕ら リスト 個人的 ホームページ 前回 リーダー 帰国 内側
専門家 弁護士 最新 政治家 室内 市内 高齢者 大声 メリット 得 早め シンプル 国際的
ファッション 年末 リサイクル 悲しみ 体調 送信 ダイエット 人間関係 何事 問題点 利用者""",

"sure N2": """自体 時点 あり得る 近年 そもそも 今や 最終的 生み出す 作り出す 本格的 必要性 精神的
経済的 効果的""",

"likely N4": """ドル センチメートル ミリメートル お話 えっ""",

"likely N3": """思い ブログ クリック サイト それら 画像 ライン あんた ネットワーク キー
ブランド 会長 大型 プレー 朝日 ボックス 地上 パワー シーン ユーザー おい ケア ライブ ライト
ツール モード ツアー バイク リンク キス この世 ウェブ ルート パック ヒット 小型 大さじ
不要 男たち ううん 都道府県 起動 受信 ステップ カウンター ごま ランキング ブロック アート
南部 ばら オリジナル 魔法 サポート プレーヤー ケーブル シェア オプション アイテム 麺
インストール デビュー ストーリー 私自身 良さ 更新""",

"likely N2": """我が 支援 年金 高齢 層 取得 多数 前年 防災 戦後 戦略 私ども コスト 遺伝 初期 リスク
総理 視線 当初 講座 人権 機器 連携 取り組み あり方 車両 認定 新規 事例 件数 同じく 解消
特性 数値 たんぱく 口調 顧客 市町村 在住 口座 上記 公的 共有 救急 仏教 早期 両者 想定
総額 分割 大手 店舗 見直し 総合的 プロセス 路線 発送 ニーズ 後期 死者 ローン テロ 海上
役員 関節 受講 思い切る 見守る 保険料 概要 保護者 変換 中小企業 やりとり 全面 疑い 数多く
持ち込む 双方 下記 裁判所 コミュニティー 由来 翌年 関わり 数量 違法 経営者 前方 業界 再度
関係者 遺産 視聴 長年 受賞 欠かす 周年 震災 江戸時代 押し付ける 幅広い""",

"likely N1": """何ら 旨 発する 陥る いかなる 見出す 放つ 晒す 己 苦笑 追求 披露 こなす""",

"unsure N3": """グリーン サイド リーグ 姫 ロック メモリー ブラック ディスク マシン""",

"unsure N2": """わし オークション 引き続く 将軍 金利 帝国 海軍 まちづくり 日米 初心 剣 受診 次元
巨人 皇帝 ホルモン 米軍 母子 陸軍 ねた サーバー 投手 竜 同年 容量 前年度 出力 機種 霊 検診""",

"unsure N1": """法人 落札 推移 債務 当該 諸国 債権 保全 証券 執行 施策 給付 理事 療法 入札 部隊
構築 藩 監査 要件 株主 幕府 適正 策定 譲渡 著作 講じる 助成 人員 保有 本書 答弁 編成 登記
疾患 広報 株価 出品者 調達 排出 当局 拠点 行使 指数 業種 司令 認知 前述 法的 条例 理念
制御 関数 際する 締結 連結 開設 集落 被告 表明 指標 復帰 定着 既存 商法 回線 計上 納付
創設 担保 金融機関 保安 倫理 摂取 搭載 消滅 挿入 保持 民営 一貫 接種 動脈 民衆 貸付 投与
特例 銘柄 加盟 免疫 検察""",

"no": """年 月 時 ござる 知れる 代 機 風 条 感 社 町 名 体 下 論 後 府 割り 項 常 因み 道 積極
三人 土 ワン 比 食 増 米 イン 厚生 ばば ザ 重 あり 小学 が マン 水 火 ウインドー 歩 オン 巻
入り 真 じい 兵 動産 活性 杯 ツー オブ 従業 総務 マイ 具 国務 炉 減 テル 並び 博物 伸び
ワード 文部 アンド メーン 術 デ 存知 先進 ハウス 公民 当事 オフ ミニ ボディー ハイ 外務
イスラム デー ルーム 財務 農林 カ国 フル 地方公共団体 ラブ 大蔵 政府委員 ホワイト ラン おお
艦 間 京 バンク バイ 法務 突き込む 出でる ワーク セル ワールド 五人 徒 植民 とんでも うう
共済 両 んっ 周波 ランド 英 イオン 十字 フード 勝""",
}

WHY = {
    "sure":   "everyday or modern word; leaving it off looks like an oversight",
    "likely": "common general word, a bit more written or narrower in use",
    "unsure": "high mainly from news / official / legal / finance text, or borderline",
    "no":     "not a learner's word on its own (suffix or counter reading, piece of a longer word, title fragment, filler, counter compound)",
}


def judgements() -> dict:
    """word → (tier, level or None)."""
    out = {}
    for key, block in BLOCKS.items():
        tier, _, lvl = key.partition(" ")
        for w in block.split():
            out[w] = (tier, lvl or None)
    return out
