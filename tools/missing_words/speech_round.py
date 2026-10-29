# Word Addition Project, spoken round (owner 2026-10-28): the top 6,000 of
# everyday conversation (CEJC) that no list covers (speech_candidates.py),
# judged by one question: would the JLPT use this word? The test writes
# standard Japanese about daily life, school, work, shopping, food, health
# and travel (official level descriptions, Can-do lists). It avoids slang,
# dialect, crude words, brand names and very specific items, and uses the
# common onomatopoeia (the official 2008 draft adopted ~350 of them).
# Levels as in the fit check: everyday things N4 (food, household, body,
# animals a child knows), daily-life Japanese N3 (school, shops, notices,
# Japanese food), articles and work N2, editorial / specialised N1.
#
# LEVELS: level → words. SKIPS: reason id → (explanation, words).
# Every candidate appears exactly once (checked by __main__).

LEVELS = {
"N5": """本屋""",

"N4": """スマホ すいか エアコン カボチャ スパゲッティ ドーナツ ヨーグルト  ピザ ギョーザ 土日 唐揚げ ポテト 納豆 オーブン おにぎり コーラ ティッシュ 天ぷら パスタ パンダ
卓球 シャンプー マヨネーズ メロン クッキー ブロッコリー ピーマン レタス きりん 花屋 ペンギン 折り紙
右足 左足 冬休み 春休み ゴミ箱 トースト パイナップル ハンバーガー ソーセージ ベーコン 肉屋 バドミントン
レシート""",

"N3": """合宿 アプリ ストレッチ チキン  パーマ ファミレス ボウル 味付け 漬物 終電 鮭 麦 部活 葉っぱ  飲み会 酔っ払う 炭酸 バーベキュー くも しょっぱい  スタンプ
店長 ドリンク ボウリング 抹茶   長生き 居酒屋  入試 焼肉 かえる 鳩 ジム  のり
  焼き鳥  タブレット ヘルメット アカウント 充電 わさび 手書き ドラム 半日
 味見 シール トレーナー ナビ 班長 ちらし    フロア アイドル 国旗 イタリアン
大騒ぎ 飲み屋 西口 南口 北口  青空 隊長  半袖 長袖  閉店 開店 前髪 インフルエンザ
お好み焼き  新年 すき焼き   ノンアルコール モール ラップ インスタント 
 スタジアム  パンフレット ひき肉 ベランダ  大盛り 柿 外食  墓参り バイキング
バレエ メダル わくわく 和室 今頃 書き順  クッション 白黒 惣菜 とんかつ 走り回る 一歩 カッター
ミーティング ラグビー  時給 銭湯 泊まり ぬいぐるみ プリンター ポンド  ゆで卵 緑茶 リレー
 クーポン  セルフ 団子 年始   フレンチ 眉毛  きらきら サングラス
食券       ヒーター ビザ 蛇 細長い 持ち歩く  アナウンス
 係長 髪型 個室    スパイス チャット 煮物 プロジェクター 最寄り やり直し
和食  ウエスト アトラクション おかしな かき氷 カタログ  グラウンド 単品 ターミナル 半額
バレー パズル パレード 一人っ子 ヘルシー 前歯 揚げ物 足首 洗い物 行き先 銀色 酒屋 鹿 ディナー デザイナー
花束 風呂場 ヘッドホン ホワイトボード まつげ 水色 山登り あぶらっこい 開場 帰り道 カート キック クリップ
ココア ゴミ袋 裏側 向こう側""",

"N2": """ワークショップ ごちゃごちゃ さらさら だらだら コンセプト ゴージャス ダッシュ フラッシュ ポリシー リニューアル 出店 常温  打ち上げ 用例 納品 買い出し チューブ 機材 ぐるぐる 理系  炭 こぶ 古文 そこそこ 坪 所長 スカウト 散々 目線 
フォロー テンション ぼろぼろ くるくる ばたばた 分厚い 気合 常勤 ズーム トーク 年表 本番 イラストレーター
プレゼン 点滴 都立 県立 ばっちり  リハビリ エントリー クレーム サポーター 年少 モチベーション 今時
カウント 漢文 チーフ 添加 辛口 局長 就活 バザー 引き継ぎ 部署 プライド 学長 ころころ スクラップ センサー
卒論 朝礼 鉄板 ナチュラル ミックス つるつる セーブ 年明け ハードル ブレンド プライベート プレッシャー
目玉 甘味  裏表 口コミ ぐちゃぐちゃ 計量 ごろごろ 立ち上げる 鶴 寝かす 屋台 理工  ダメージ
ディベート 電動 どかす 払い戻し 反則 人前 備品  民家 留年 がたがた どろどろ がらがら 
インパクト 園長 エース 経理 しみ 視力 ドキュメンタリー 配信 腹筋 文系 本数 ぼうっと 面談 よだれ
アスファルト 気まずい 説教  出だし 夏場 冬場 バリエーション 肥満 振り回す プレミアム 盆踊り 守り
ロゴ べたべた アシスタント 大昔 カリキュラム 火力 球団 根性 茶道 接客 先発 出番 ノウハウ 迫力
フィードバック 法事 夜勤 レール  オファー 買い取る キット 気遣い 食感 新卒 常連 待機 ターゲット
定時 年配 別途 路地 空き家 胃腸 エール 買い換える 飼い主 貸し出す 筋力  グルメ 高卒 コンテンツ コンパクト
シニア 染み込む 旬 初回 上映 人名 厨房 直行 読解 内定 煮込む 剥がれる  爆笑 文通 ブース
町中 マニア 名言 揺らす   例年 ローカル アウトレット アナログ 入れ替える 入れ替わる 色合い
歌声 エラー 音符 カプセル 筋トレ キープ ぐったり 紅白 最強 車線 週休 時短 だんとつ 長文 通販 鉄分
ディスカッション 洞窟 バトン 引き寄せる ピックアップ フライト 万が一 読み聞かせ リゾート リハーサル
若葉 ワクチン びしょびしょ ぺらぺら 一人前 インストラクター 旨み 送り迎え 夏期 夏季 かき混ぜる 壁紙 学童
合奏  帰省 キャスト  雑草 下見 じわじわ スタミナ 声優 セッティング 背骨 喘息  台数 段取り 手持ち
店頭 出来 当分 トピック トータル にやにや 年内 ヒアリング 不燃 プロデューサー 褒め言葉 ミュージシャン
幼虫 落語 リピーター リフォーム リリース ぽろぽろ からから 相棒  厚み 癒し 入れ替え 大当たり 改装
海藻 書き込み 格安 観戦 機内 学内 好物 コンビ 手動""",

"N1": """搬入 染料 直近 絡める 設営 試作 鉱石 進捗 なおかつ 断層 永住 根元 傍聴 如何 食らう 骨董 接待 大腸 簿記 満々 一任 換金 協賛 濃厚
開ける 不動 補佐 前倒し 装う まるきり 異様 遠隔 近世 石碑 専務 都度 発声 病棟 割り切る 跡地 急性 形容
告知 御殿 所詮 接着 選抜 俗 大河 弾丸 宙 なぞる 威嚇 糧 極力 和歌 ベンチャー どうこう 却下 講評 撤収
いっとき さばく 深読み 石垣 大口 格闘 稼働 兼ね合い 完結 肝 くだり 香ばしい 工房 今期 仕入れ 囚人 集約 所帯
シンポジウム 前面 台帳 ちゃっかり 集い 定例 特化 土器 乳がん 派生 本題 身内 やけ 劣化 高々 ありきたり 一式
いんちき おもむろに 改名 肩書き 外注 急患 切り捨て 凝縮 構図 酷評 校正 ぶれる""",
}

SKIPS = {
"piece": ("Not a word on its own: a particle, a counter, a reading cut out of a longer word (かあ from お母さん, 人差し from 人差し指, ゴールデン from ゴールデンウィーク), or a form of a listed word (やった, 損する).",
    """で 母 父 兄 いしょ たら があ から 一所 ウーロン ゴールデン 首 うえ やった かあ うお ふ ぐう パー はん 乗り 合
    すう ぱあ 地 たい 飲み 明解 ちょこ 付け こま 人差し 見知り 遊園 ぽい 込み 通し 忘年 押し クレー さぎ どこどこ 屋
    触り しゅう 明け 握り 受け 売り さび 奨学 放課 文科 林間 分け 上げ 送り おし 落ち かむ 留め たち 染め 中高
    難易 賞味 ぺら 抑え 返し がら 削れる 海産 差し 化け 歩き 胡散 お好み 替え くる さら 懇親 自販 展覧 ベーキング
    はてな 急便 ゲー がし 脚 ごう ちい ちゅう 悪 んだ あう 臙脂 ぼん メーリング 引き手 びい ぴいぴい 圧 とっく
    ほお ラッシュ かも くう シア 冷や 団 昼三 盛り 締め ちん かしこまる 損する 年取る 発泡 ぶち開ける はねる パンフ 遅く 抗がん 不尽 頚髄"""),
"sound": ("A sound word, filler or interjection the test doesn't use (onomatopoeia that JLPT does test, like ぐるぐる, ばたばた, わくわく, are added).",
    """んー おっ よいしょ うい すっ ははは ばんばん ひい ぽんぽん うわ ああん ふう ばあ はっ きゃあ がんがん ばーん おっと ぴっ ちょこちょこ こら ばりばり
    あい ほい ふっ ふふん くっ とんとん ぽん どーん もったり ちょろちょろ ぱんぱん ぱりぱり ぱーん ぱらぱら しい
    すりすり があん ぱちん よっこいしょ かりかり ぎゃあ どん ありゃ しゃかしゃか ぴよぴよ あはは ざあ えへへ
    がつがつ やれ よっしゃ オー ははあ ぴりぴり ほほほ がりがり えいさあ しゅっしゅっ すかすか ふわ もちもち やあ
    ぼこぼこ あちち はは ぽーん ごりごり えいしょ しゅわしゅわ せえの ぶうぶう がり つんつん がさがさ かちかち
    しゃきん どかーん ちゅっ ちょんちょん ちーん ひゅう へへ ぺろぺろ むずむず わあわあ わっ あちゃ うふふ かちん
    ぎゃあぎゃあ ぎゅう ふにゃふにゃ がたん かちゃかちゃ かん ぐりぐり しましま とろとろ もこもこ もふもふ
"""),
"spoken": ("Slang, dialect, a casual contraction, baby talk or a spoken short form; the test uses the standard word (ちょっと, 落ちる, 本当, 難しい).",
    """ちび ちょい ほんま いけメン うざい がち ぎり ださい ついつい わんこ サンド 事故る 兄者 めちゃめちゃ 端っこ 乗っける 己 落っこちる いっぺん ざっくり ちょこっと しんどい やらす
    乗っかる おしっこ へたくそ むずい ナイス がっつり むかつく 兄貴 きもい あざっす 気持ちい ディスる にゃんこ
    おら ちょいちょい スルー ちゃり １００均 マックス 甥っ子 根っこ ぼちぼち 待たす やらかす 楽チン リハ 輪っか
    ワンチャン いかれる インフル ガーリー 自腹 近場 ほな ヤンキー あつあつ あるある エモい 愚痴る しょぼい
    どっちみち なんぼ 時たま 朝一 角っこ がき ちびっこ ちゃらい べろ 後々 ごつい けちる 先っぽ 朝飯 えぐい
    はっちゃける みいはあ ミスる ういっす 言わす 飲ます ぶち込む 追いコン がらけい コスパ 合コン スクショ ググる
    ギガ ぼけ 夜ご飯 ギャル 軽トラ ドンマイ メモる フェス スケボー 男前 コラボ ロケ ヘリ
    コンサル バスケ こける 甘ったるい レス びびる とっぽい ぐる"""),
"katakana": ("Katakana stand-in for a native word the test would use (フェース for 顔, ラスト for 最後, ミュージアム for 博物館).",
    """ラフ フェース シー スイート アイアン アンダー サンクス スタンス センシティブ ハッピー ポップ メタル ロス ロー ウイーク ドッグ ハンド イレブン テン スリー ツリー アップル キング スカイ ロール
    ファイブ マート ファイア プディング キッド レクチャー カルチャー コール ダイレクト ドット アニマル エンター
    ガード ソング ローリング ウルトラ アーマー コア サマー ダック エンド クオリティー ストーン ツイスト ウォーター
    エッセンス ジンジャー ハロー バトル パウダー ブラウン ベイ レア サニー ノン ブレーク ビック ベリー
    アドベンチャー エコノミー オンリー ガーデン サーティー シューズ ネオ ビーフ ブリンク アメリカン ウエルカム
    カクタス ゴースト シックス ジャスト ジュニア バースデー フラワー プレ ミッドナイト ムーチョ インター エイト
    アフター キーパー ストア ソーリー トラップ ハイランド ハニー ビューティフル フレンド ペースト ポール マンデー
    トライ スロー ウォッチ エクササイズ ガン キャンデー キャンドル セカンド セーフ ネック フラット プッシュ ワイルド
    ミー イレギュラー ウォーク ウエア アングル カーボン ミート ネービー ネール ファイナル フィッシュ テースト
    スティック スパン タイガー シャープ シルク ミュージアム リッチ メガ ラリー レーン フォーン チェックポイント
    フェスティバル オーガニック ラボ ラスト モビール クラッシュ ビートル"""),
"niche": ("Too specific for the test: a particular dish, ingredient, plant, animal, sport detail or hobby item. The test sticks to things every learner meets.",
    """サーカス ピッチャー キャッチャー バッター ナッツ くり まぐろ さば うなぎ わかめ しいたけ もやし 白菜 唐辛子 枝豆 さくらんぼう 黄身 せんべい おでん そうめん 牛丼 焼きそば オムライス チャーハン 卵焼き たぬき 蝉 あひる しまうま ごきぶり 恐竜 ミキサー スナック テラス こんろ 爪切り スプレー スポンジ ドレッシング フライ パイ コロッケ ソーダ コーン ビュッフェ ほたる ふくろう いのしし 鯉 菊 朝顔 雑煮 干支 線香 海賊 まめ 千切り 泡立てる こねる 串 焼酎 アロマ ヨーガ あさり かぶ かわせみ くるみ こけ こげら つまみ みょうが オリーブ クラッカー コースター シューマイ セロリ ターバン チリ トリートメント パクチー パッド パンチ プレールーム メチル モンスター ラッテ 伊達巻 入道 太極 家元 山の手 岩牡蠣 明太 木の芽 点てる 白墨 頭皮 麹 黒豆 たれ たけのこ ハーブ あじ 梅酒 プロレス サワー かき ジェル 羊羹 キムチ
    そらまめ ゴーヤー ブルーベリー マーボー メレンゲ シフォン バニラ サイダー 蕎麦屋 タコス 寿司屋 アボカド セッション
    ランタン レスラー きじ 鍬形 玄米 サンチュ ひえ ビーカー ウィンナ 逆上がり 下敷き チヂミ パプリカ 神輿 やすり ゆず
    遅番 弓道 ココナッツ ごぼう 精油 せきれい トリミング 念仏 マンゴー 最中 レフェリー 浮き輪 数の子 パステル
    片栗粉 クレープ しらす 樽 天守 とんこつ 糠 モカ イースト オーロラ 既読 しそ 竹炭 はけ フェルト 薪 みずすまし
    もつ 予熱 れんこん ワイナリー 朝市 厚揚げ からすみ タピオカ たらこ トリッパ 中継ぎ ピクルス マリーナ 卵白
    リフレクソロジー 老眼 アーモンド いちょう 桶 クミン けやき タン ちくわ 肉球 盛り合わせ アヒージョ 油揚げ 角煮
    型紙 カルボナーラ 急須 古道 ささみ シナモン 素数 卒園 痛風 ディスコ 豆乳 寅 ナツメグ なます ハワイアン ほたるいか
    マクロビ 饅頭 右利き 蒸し焼き 和える あめんぼ ウォーマー からし キウイ きくらげ グラタン ケイ素 コンマ 塩麹
    しじゅうから シャンパン ショコラ スイング たくあん 代打 稚児 中トロ トライアスロン 鶏皮 パセリ 日持ち 張り替える
    半纏 めだか めんつゆ もず モルト ラザーニャ ラック ワンタン 甘酢 カリフラワー 喜寿 黒子 グリセリン サブレー
    三振 参道 獅子 七味 ショーロンポー シロップ シード ジャンボリー 浄水 スナイパー スパークリング スフレ 頭巾
    軟式 馬刺し ピーナッツ マリネ みりん 山寺 雪かき 甘酒 あゆ 鵜 オクラ 花木 げんごろう 小町 米粉 コープ 逆さ吊り
    五月 晒し 三脚 ざる シーフード スパ 製菓 だし巻き チャンプルー ねぶた バレリーナ ピラミッド ふりかけ 篩う ペソ
    マコロン 蜜蝋 リフト ロースト グリル うに おひたし キャノピー 銀杏 草刈り 語釈 榊 桜海老 塩気 白子 しろくま 炭火
    土鍋 緞帳 乳酸 海苔巻き 初盆 バッティング パンケーキ ヒーリング ふき ぶり ホルダー 町家 冷麺 横笛 余熱 ワイングラス
    小豆 アメフト 泡盛 居残り いわし 薄味 オイスター 飾り棚 かつお カピバラ かぶとむし 窯 噛み合わせ 桔梗 きんとん
    講談 こく コーリャン 菜箸 師範 笙 スウェット すみれ スモーク たい焼き たか タルト 打球 ダブルス つげ 椿 ティラミス
    鉄鉱 手羽 デリ 倒立 盗塁 飛魚 トルマリン トレード なまず なまはげ ナン 軟骨 ナンプラー 煮干 ヌートリア パフェ 譜面
    フリース まがも マロン 水煮 ミディアム ミニゲーム 湯煎 ラタトゥイユ 離乳 レーズン 湧き水 揚げ出し あなご アンドロイド
    アンバサダー 一塁 瓜 オカリナ 甲冑 かなぶん かまきり かまぼこ かるがも カルパッチョ カプレーゼ 金物 コカ 小鉢
    こんにゃく トート タッパー 河童 天狗 妖怪 魔女 ストライク あんこ 外野 クラウド 白身 血行 オーラ 大関
 通園 青果 被服 方形 報国 文様 武者 茶屋 塚 てんさい 縄文 黒船 冠位 式部 検非違使 貴人 華厳 管長
    家紋 五黄 卍 稲荷 八幡 天神 大師 南無阿弥陀仏 いろは 裏方 取り皿
 メタファー オノマトペ 生協 数理 つとに レコーダー
"""),
"pattern": ("Built regularly from listed parts: a school year (高２, 中１), 〜め (多め, 甘め), 何 + noun, こちら + 側, raw + noun.",
    """こちら側 高２ 高３ 高１ 中１ 中２ 小６ 何色 いつ頃 多め 少なめ 大きめ 高め 甘め 濃いめ 薄め 誰々 生卵 木金
"""),
"register": ("Work or official jargon, or a technical term, outside what the test reads and hears (議事, 入稿, 検品).",
    """ルーター ハードディスク 会派 コーパス 町会 師長 回忌 議事 納会 月報 検品 入稿 創発 物販 教案 所外 渉外 所内 上水 平米 月例 役務 教具 教務
    満額 各派 二元"""),
"name": ("A proper noun, brand or product name; the lists have none.",
    """ポケモン 神宮 東名 デジモン 楽天 マーベル ガスト 御苑 ジェンガ 無印 都庁 英検 カープ コロナ 白鯨
    キングダム ツイート"""),
"notjlpt": ("Crude, sexual, insulting or dated in a way the test avoids (like キス and エッチ in earlier rounds).",
    """ハーフ くそ げろ おなら 外人 ぶす 貴様 うんち うんこ でぶ げっぷ エロい エロ 熟女 ちんちん けつ 逝く しゃば"""),
}


SHORT = {"piece": "Word piece", "sound": "Sound word", "spoken": "Slang or casual form",
         "katakana": "Katakana stand-in", "niche": "Too specific", "pattern": "Pattern word",
         "register": "Jargon", "name": "Name", "notjlpt": "Not test material"}


def judgements():
    out = {}
    for lv, block in LEVELS.items():
        for w in block.split():
            out[w] = (lv, "")
    for rid, (_, block) in SKIPS.items():
        for w in block.split():
            out[w] = ("skip", rid)
    return out


# Frequency rule (owner 2026-10-29): an added word must sit inside its level's
# frequency size (the bars' cumulative sizes, §8 of the handbook); a word too
# rare for its judged level moves up one level at a time until it fits.
# Speech rank here (CEJC), since that's what brought these words in.
LEVEL_CAP = {"N5": 800, "N4": 1500, "N3": 3900, "N2": 6000, "N1": 13400}


# The owner's "Other…" notes on the page (db doc review/speech, 2026-10-29),
# decided by speech rank. "Pattern word" here means our skip reason: built
# regularly from listed parts (〜め, 何 + noun, school years). Ordinary
# compounds with their own dictionary entry stay, as on the lists (出口, 右手).
RESOLVED = {
    1327: "N3",    # 飲み会: a set compound (宴会 N2 is listed); 〜会 isn't a pattern we skip
    1770: "N3",    # スタンプ: point-card stamps, LINE stamps; everyday
    1951: "N2",    # 長生き: owner leaned N2
    2160: "N3",    # 卓球: school-club sport (テニス N4, ゴルフ N3); speech-common from club talk
    2639: "N3",    # シール: sticker (false friend of "seal"); owner: N3 seems right
    2789: "N3",    # 南口: station exits are signs every learner reads; 口 → ぐち (出口 N5); level set by final_additions.SETS (N2)
    2921: "N2",    # 漬物: a food category like 煮物, which the owner set N2
    3012: "N3",    # ピーマン: French (piment), flagged loan-fre, not counted as English
    3248: "N3",    # 大騒ぎ: own dictionary entry, common set word
    3610: "N2",    # 右足: pairs share a level (owner): 左足 is #4,068 → both N2; 右手 / 左手 both N3
    3906: "N2",    # バドミントン: past N3 by rank
    3951: "N2",    # 和室: #3,952, just past N3's 3,900; 洋室 (≈#25,600) is too rare for any level
    4067: "N2",    # 左足: with 右足
    4107: "N2",    # ラグビー: past N3 by rank
}


def fit_level(lv, rank):
    if lv == "skip":
        return lv, ""
    order = list(LEVEL_CAP)
    i = order.index(lv)
    while rank > LEVEL_CAP[order[i]] and i < len(order) - 1:
        i += 1
    if order[i] == lv:
        return lv, ""
    return order[i], f"Judged {lv}, moved to {order[i]}: speech rank #{rank:,} is past {lv}'s top {LEVEL_CAP[lv]:,}."


def jmdict_glosses():
    # Fallback meanings for the review page: meanings.json only covers list +
    # BCCWJ words, so 447 rows (スマホ, 終電 …) had none. Full JMdict from
    # %TEMP%\data\JMdict_e.gz (§6); first 3 senses, 3 glosses each.
    # Keys (spelling, hiragana reading), and spelling alone as a last resort.
    import gzip, os, xml.etree.ElementTree as ET
    hira = lambda s: "".join(chr(ord(c) - 96) if "ァ" <= c <= "ヶ" else c for c in s)
    out = {}
    for _, el in ET.iterparse(gzip.open(os.path.join(os.environ["TEMP"], "data", "JMdict_e.gz")), events=("end",)):
        if el.tag != "entry":
            continue
        keb = [k.findtext("keb") for k in el.findall("k_ele")]
        reb = [r.findtext("reb") for r in el.findall("r_ele")]
        gl = "; ".join(", ".join(g.text for g in s.findall("gloss")[:3]) for s in el.findall("sense")[:3])
        for r in reb:
            for f in keb + [r]:
                out.setdefault((f, hira(r)), gl)
                out.setdefault(f, gl)
        el.clear()
    return lambda d, r: out.get((d, hira(r))) or out.get(d)


if __name__ == "__main__":
    import collections, json, os, sys
    sys.stdout.reconfigure(encoding="utf-8")
    HERE = os.path.dirname(os.path.abspath(__file__))
    cands = [x for x in json.load(open(os.path.join(HERE, "speech_candidates.json"), encoding="utf-8")) if not x["earlier"]]
    words = {x["d"] for x in cands}
    seen = collections.Counter()
    for block in list(LEVELS.values()) + [b for _, b in SKIPS.values()]:
        seen.update(block.split())
    print("twice:", [w for w, n in seen.items() if n > 1])
    print("missing:", [w for w in sorted(words) if w not in seen])
    print("extra:", [w for w in seen if w not in words])
    j = judgements()
    print(collections.Counter(j[w][0] for w in words if w in j))
    # Review page (Word Additions Artifact, db doc review/speech):
    #   py -I tools/missing_words/speech_round.py <out.html>
    if len(sys.argv) > 1:
        import html
        rows, seen_w = [], set()
        gloss = jmdict_glosses()
        for x in cands:
            if x["d"] in seen_w:
                continue                      # the same word under two readings: one row
            seen_w.add(x["d"])
            v, why = j[x["d"]]
            fv, note = fit_level(v, x["srank"])
            rows.append({"rank": x["srank"], "d": x["d"], "r": "" if x["r"] == x["d"] else x["r"],
                         "m": x["m"] or gloss(x["d"], x["r"]) or "(no dictionary meaning)", "g": fv, "s": fv, "why": why,
                         "note": note})
        groups = {lv: [lv, f"Pre-set to {lv}. Change any word you'd put elsewhere."] for lv in LEVELS}
        groups["skip"] = ["Skip", "Pre-set to skip, with the reason under each word. Pick a level to add one after all."]
        n_skip = collections.Counter(r["why"] for r in rows if r["s"] == "skip")
        lis = "".join(f"<li><b>{html.escape(SHORT[rid])}</b> ({n_skip[rid]}): {html.escape(why)}</li>"
                      for rid, (why, _) in SKIPS.items())
        add = sum(1 for r in rows if r["s"] != "skip")
        tpl = open(os.path.join(HERE, "speech_template.html"), encoding="utf-8").read()
        js = lambda o: json.dumps(o, ensure_ascii=False).replace("</", "<\\/")
        out = (tpl.replace("__ROWS__", js(rows)).replace("__GROUPS__", js(groups))
                  .replace("__SKIPWHY__", js({rid: [SHORT[rid], why] for rid, (why, _) in SKIPS.items()}))
                  .replace("__SKIPLIST__", lis).replace("__ADD__", str(add)).replace("__SKIP__", str(len(rows) - add))
                  .replace("__TOTAL__", str(len(rows))))
        open(sys.argv[1], "w", encoding="utf-8").write(out)
        print(len(rows), "rows →", sys.argv[1])
