"""Build the add-on's jlpt_n*.txt files from OpenJLPT + JMdict.

Usage (from the folder containing data/ and ojlpt/):
    python data/build_jlpt.py <addon_dir>
"""
import json, pickle, re, collections, sys

A = sys.argv[1]
J = pickle.load(open("data/jmdict.pkl", "rb"))
KATA = re.compile(r"^[゠-ヿー・]+$")
# Corrections to OpenJLPT: words its data is missing. Each is added to the
# given level (as OpenJLPT-style entries, so they get JMdict spellings too).
# 2026-10-08: + words on Waller's lists (via stephenmk/yomitan-jlpt-vocab
# original_data, which keeps Waller's levels + JMdict ids) that OpenJLPT
# dropped, chosen by the owner: modern spellings only, no archaic words, and
# single-kanji readings only when JMdict has an entry for them.
ADDITIONS = {
    "5": [
        {"word": "私", "reading": "わたし", "jmdict_id": 1311110},   # only わたくし/あたし were listed
        {"word": "一日", "reading": "ついたち", "jmdict_id": 2225040},   # first of month
        {"word": "キロメートル", "reading": "キロメートル", "jmdict_id": 1042650},   # Kilometer
        {"word": "キログラム", "reading": "キログラム", "jmdict_id": 1042620},   # Kilogram
    ],
    "4": [
        {"word": "止める", "reading": "やめる", "jmdict_id": 1310680},   # to stop
        {"word": "君", "reading": "くん", "jmdict_id": 1247260},   # suffix for familiar young male
    ],
    "3": [
        {"word": "度", "reading": "ど", "jmdict_id": 1445160},   # counter for occurrences
        {"word": "数", "reading": "すう", "jmdict_id": 1580825},   # number,figure
        {"word": "綿", "reading": "わた", "jmdict_id": 1533340},   # cotton,padding
        {"word": "金", "reading": "きん", "jmdict_id": 1242600},   # (1) gold,(2) gold general (shogi) (abbr)
        {"word": "注ぐ", "reading": "つぐ", "jmdict_id": 2145240},   # to pour (into),to irrigate,to pay
        {"word": "柄", "reading": "がら", "jmdict_id": 1508300},   # hilt (of a sword),haft (of a dagger),han
        {"word": "訳", "reading": "やく", "jmdict_id": 2057030},   # meaning,reason,circumstances,can be dedu
        {"word": "分", "reading": "ぶ", "jmdict_id": 1502850},   # dividing,part
        {"word": "軒", "reading": "けん", "jmdict_id": 2078590},   # eaves
        {"word": "額", "reading": "ひたい", "jmdict_id": 1207510},   # forehead,brow
        {"word": "方々", "reading": "ほうぼう", "jmdict_id": 1584105},   # persons,this and that,here and there,eve
        {"word": "上", "reading": "じょう", "jmdict_id": 1352170},   # (1) first volume,(2) superior quality,(3
        {"word": "得る", "reading": "うる", "jmdict_id": 1454500},   # to get,to gain,to win
        {"word": "品", "reading": "ひん", "jmdict_id": 2648780},   # thing,article,goods,dignity,article (goo
        {"word": "上", "reading": "かみ", "jmdict_id": 1352150},   # (own JMdict entry)
        {"word": "下", "reading": "しも", "jmdict_id": 2080210},   # (own JMdict entry)
        {"word": "下", "reading": "げ", "jmdict_id": 2080200},   # (own JMdict entry)
        {"word": "無", "reading": "ぶ", "jmdict_id": 2423740},   # (own JMdict entry)
    ],
    "2": [
        {"word": "一段", "reading": "いちだん", "jmdict_id": 1164690},   # greater,more,further,still more
        {"word": "ばつ", "reading": "ばつ", "jmdict_id": 2197150},   # 
        {"word": "鈍い", "reading": "のろい", "jmdict_id": 2838553},   # dull (e.g. a knife),thickheaded,slow (op
        {"word": "紅葉", "reading": "もみじ", "jmdict_id": 2857870},   # (1) (Japanese) maple
        {"word": "なだらか", "reading": "なだらか", "jmdict_id": 1632290},   # 
    ],
    "1": [
        {"word": "よほど", "reading": "よほど", "jmdict_id": 1605980},   # very, greatly, much, to a large extent, 
        {"word": "著", "reading": "ちょ", "jmdict_id": 1956680},   # counter for suits of clothing, arriving 
        {"word": "修行", "reading": "しゅぎょう", "jmdict_id": 2650010},   # pursuit of knowledge, studying, learning
        {"word": "だけ", "reading": "だけ", "jmdict_id": 1007340},   # only, just, as
        {"word": "供する", "reading": "きょうする", "jmdict_id": 1233550},   # offer, present, submit, serve (a meal), 
        {"word": "的", "reading": "まと", "jmdict_id": 1437270},   # mark, target
        {"word": "しなやか", "reading": "しなやか", "jmdict_id": 1566110},   # supple, flexible, elastic
        {"word": "ほとり", "reading": "ほとり", "jmdict_id": 2842190},   # (in the) neighbourhood, vicinity, nearby
        {"word": "あからさま", "reading": "あからさま", "jmdict_id": 1000225},   # obvious, overt, plainly, frankly
        {"word": "流行り", "reading": "はやり", "jmdict_id": 2834093},   # fashionable, fad, in vogue, prevailing
        {"word": "灰汁", "reading": "あく", "jmdict_id": 1201960},   # puckery juice
        {"word": "万", "reading": "ばん", "jmdict_id": 1525750},   # (own JMdict entry)
    ],
}


# 2026-10-08: words on community JLPT lists built from Waller's lists plus Jisho
# tags, older list versions and textbook tags (jamsinclair/open-anki-jlpt-decks,
# elzup/jlpt-word-list), but on neither OpenJLPT nor Waller's current lists:
# 顔, 母, 頑張る, 当然, 仕方がない … The owner chose to add all 211 (set phrases
# included: 仕方がない means more than 仕方 + ない). Levels are those lists' (the
# easiest one when they disagree). Flagged "community" in the list files.
COMMUNITY_ADDITIONS = {
    "5": [
        {"word": "ない", "reading": "ない", "jmdict_id": 1529520, "flags": ["community"]},   # there isn't, doesn't have
        {"word": "顔", "reading": "かお", "jmdict_id": 1217730, "flags": ["community"]},   # face (body part)
        {"word": "母", "reading": "はは", "jmdict_id": 1514990, "flags": ["community"]},   # (my) mother
        {"word": "父", "reading": "ちち", "jmdict_id": 1497610, "flags": ["community"]},   # (my) father
        {"word": "もしもし", "reading": "もしもし", "jmdict_id": 1012550, "flags": ["community"]},   # Hello? (used on the phone)
    ],
    "4": [
        {"word": "専門", "reading": "せんもん", "jmdict_id": 1389880, "flags": ["community"]},   # major; speciality
        {"word": "頑張る", "reading": "がんばる", "jmdict_id": 1217700, "flags": ["community"]},   # to try one's best, to try hard, to persi
        {"word": "スーパー", "reading": "スーパー", "jmdict_id": 1066710, "flags": ["community"]},   # supermarket
        {"word": "パパ", "reading": "パパ", "jmdict_id": 1102140, "flags": ["community"]},   # papa, daddy
        {"word": "正月", "reading": "しょうがつ", "jmdict_id": 1377030, "flags": ["community"]},   # New Year, New Year's Day
        {"word": "失礼", "reading": "しつれい", "jmdict_id": 1320230, "flags": ["community"]},   # discourtesy, impoliteness; Excuse me
        {"word": "お子さん", "reading": "おこさん", "jmdict_id": 1002000, "flags": ["community"]},   # (someone else's) child (polite)
        {"word": "ハンバーグ", "reading": "ハンバーグ", "jmdict_id": 1096870, "flags": ["community"]},   # hamburger steak
    ],
    "3": [
        {"word": "表示", "reading": "ひょうじ", "jmdict_id": 1489610, "flags": ["community"]},   # display, indication
        {"word": "当然", "reading": "とうぜん", "jmdict_id": 1449190, "flags": ["community"]},   # obvious; natural
        {"word": "件", "reading": "けん", "jmdict_id": 1255940, "flags": ["community"]},   # matter, case, item
        {"word": "イメージ", "reading": "イメージ", "jmdict_id": 1021750, "flags": ["community"]},   # one's image
        {"word": "生涯", "reading": "しょうがい", "jmdict_id": 1378840, "flags": ["community"]},   # one's lifetime
        {"word": "迷う", "reading": "まよう", "jmdict_id": 1532710, "flags": ["community"]},   # to be puzzled, to be perplexed, to lose 
        {"word": "体重", "reading": "たいじゅう", "jmdict_id": 1409540, "flags": ["community"]},   # (body) weight
        {"word": "出場", "reading": "しゅつじょう", "jmdict_id": 1339220, "flags": ["community"]},   # participation
        {"word": "菌", "reading": "きん", "jmdict_id": 1956120, "flags": ["community"]},   # germ, bacterium
        {"word": "意", "reading": "い", "jmdict_id": 2081180, "flags": ["community"]},   # will
        {"word": "経緯", "reading": "けいい", "jmdict_id": 1251120, "flags": ["community"]},   # sequence of events, course
        {"word": "正体", "reading": "しょうたい", "jmdict_id": 1377530, "flags": ["community"]},   # natural shape, one's true colors, true c
        {"word": "苦", "reading": "く", "jmdict_id": 2037710, "flags": ["community"]},   # trouble, worry, difficulty
        {"word": "めくる", "reading": "めくる", "jmdict_id": 1257810, "flags": ["community"]},   # to turn over, to turn pages of a book
        {"word": "狩り", "reading": "かり", "jmdict_id": 1328710, "flags": ["community"]},   # hunting
        {"word": "医院", "reading": "いいん", "jmdict_id": 1159730, "flags": ["community"]},   # doctor's office (surgery), clinic
        {"word": "供", "reading": "とも", "jmdict_id": 1233560, "flags": ["community"]},   # accompanying, attendant, companion, reti
        {"word": "摘む", "reading": "つむ", "jmdict_id": 1437060, "flags": ["community"]},   # to pluck, to pick, to trim
        {"word": "抱く", "reading": "だく", "jmdict_id": 2844997, "flags": ["community"]},   # to embrace, to hug
        {"word": "精算", "reading": "せいさん", "jmdict_id": 1379930, "flags": ["community"]},   # exact calculation, adjustment
        {"word": "優", "reading": "ゆう", "jmdict_id": 1539030, "flags": ["community"]},   # superiority, high grade
        {"word": "童謡", "reading": "どうよう", "jmdict_id": 1453990, "flags": ["community"]},   # children's song, nursery rhyme
        {"word": "隊", "reading": "たい", "jmdict_id": 1956610, "flags": ["community"]},   # party, troops
        {"word": "対", "reading": "つい", "jmdict_id": 1409810, "flags": ["community"]},   # pair, couple, set
        {"word": "末", "reading": "まつ", "jmdict_id": 1525260, "flags": ["community"]},   # the end of
        {"word": "異", "reading": "い", "jmdict_id": 2056700, "flags": ["community"]},   # difference (of opinion)
    ],
    "2": [
        {"word": "限り", "reading": "かぎり", "jmdict_id": 1264610, "flags": ["community"]},   # limit(s), as far as possible
        {"word": "自ら", "reading": "みずから", "jmdict_id": 1317340, "flags": ["community"]},   # for one's self, personally
        {"word": "主人", "reading": "しゅじん", "jmdict_id": 1579780, "flags": ["community"]},   # (one's own) husband
        {"word": "見つめる", "reading": "みつめる", "jmdict_id": 1604580, "flags": ["community"]},   # to stare at, to gaze at
        {"word": "叔父", "reading": "おじ", "jmdict_id": 1607070, "flags": ["community"]},   # (humble) uncle (older than one's parent)
        {"word": "頷く", "reading": "うなずく", "jmdict_id": 1574310, "flags": ["community"]},   # to nod
        {"word": "自宅", "reading": "じたく", "jmdict_id": 1318260, "flags": ["community"]},   # one's own home (same as 自分の家 (じぶんのいえ))
        {"word": "叔母", "reading": "おば", "jmdict_id": 1607100, "flags": ["community"]},   # (humble) aunt (older than one's parent)
        {"word": "職場", "reading": "しょくば", "jmdict_id": 1357540, "flags": ["community"]},   # workplace
        {"word": "懸命", "reading": "けんめい", "jmdict_id": 1257730, "flags": ["community"]},   # eagerness, strenuous
        {"word": "人事", "reading": "じんじ", "jmdict_id": 1367870, "flags": ["community"]},   # human resources, personnel management
        {"word": "地面", "reading": "じめん", "jmdict_id": 1421510, "flags": ["community"]},   # ground, earth's surface
        {"word": "ただいま", "reading": "ただいま", "jmdict_id": 1538960, "flags": ["community"]},   # Here I am, I'm home!
        {"word": "見上げる", "reading": "みあげる", "jmdict_id": 1259740, "flags": ["community"]},   # to look up at, to admire
        {"word": "足元", "reading": "あしもと", "jmdict_id": 1586390, "flags": ["community"]},   # at one's feet
        {"word": "弟子", "reading": "でし", "jmdict_id": 1581960, "flags": ["community"]},   # pupil, disciple, apprentice
        {"word": "行方", "reading": "ゆくえ", "jmdict_id": 1282180, "flags": ["community"]},   # one's whereabouts
        {"word": "せりふ", "reading": "せりふ", "jmdict_id": 1577270, "flags": ["community"]},   # speech, words, one's lines, remarks
        {"word": "振り向く", "reading": "ふりむく", "jmdict_id": 1361190, "flags": ["community"]},   # to turn one's face, to turn around
        {"word": "隙", "reading": "すき", "jmdict_id": 1253780, "flags": ["community"]},   # unguarded moment, chance
        {"word": "水面", "reading": "すいめん", "jmdict_id": 1372120, "flags": ["community"]},   # water's surface
        {"word": "ふるさと", "reading": "ふるさと", "jmdict_id": 1603050, "flags": ["community"]},   # home town, birthplace
        {"word": "全力", "reading": "ぜんりょく", "jmdict_id": 1396390, "flags": ["community"]},   # all one's power, whole energy
        {"word": "着替える", "reading": "きがえる", "jmdict_id": 1423170, "flags": ["community"]},   # to change (one's) clothes
        {"word": "荒れる", "reading": "あれる", "jmdict_id": 1281490, "flags": ["community"]},   # to be stormy, to be rough, to be ruined
        {"word": "思い切り", "reading": "おもいきり", "jmdict_id": 2834138, "flags": ["community"]},   # with all one's strength (heart), resigna
        {"word": "上品", "reading": "じょうひん", "jmdict_id": 1354230, "flags": ["community"]},   # refined, elegant, well-mannered
        {"word": "洗面", "reading": "せんめん", "jmdict_id": 1391050, "flags": ["community"]},   # wash up (one's face), have a wash
        {"word": "水着", "reading": "みずぎ", "jmdict_id": 1371830, "flags": ["community"]},   # bathing suit (woman's)
        {"word": "初歩", "reading": "しょほ", "jmdict_id": 1343050, "flags": ["community"]},   # elements, rudiments
        {"word": "元日", "reading": "がんじつ", "jmdict_id": 1261010, "flags": ["community"]},   # New Year's Day
        {"word": "塩辛", "reading": "しおから", "jmdict_id": 1178740, "flags": ["community"]},   # salty (taste)
        {"word": "しめた", "reading": "しめた", "jmdict_id": 1389450, "flags": ["community"]},   # I've got it, all right, fine
        {"word": "琴", "reading": "きん", "jmdict_id": 2229960, "flags": ["community"]},   # 13-string Japanese zither
        {"word": "行ってきます", "reading": "いってきます", "jmdict_id": 2020140, "flags": ["community"]},   # (Lit.) I'll go and come back, 'I'm going
        {"word": "お構いなく", "reading": "おかまいなく", "jmdict_id": 1001900, "flags": ["community"]},   # please don't fuss over me
        {"word": "勝手に", "reading": "かってに", "jmdict_id": 1346200, "flags": ["community"]},   # arbitrarily,
        {"word": "構いません", "reading": "かまいません", "jmdict_id": 1279670, "flags": ["community"]},   # it's all right; one doesn’t mind
        {"word": "仕方がない", "reading": "しかたがない", "jmdict_id": 1305420, "flags": ["community"]},   # it can't be helped, it's inevitable
        {"word": "失礼しました", "reading": "しつれいしました", "jmdict_id": 1320240, "flags": ["community"]},   # Excuse me., I'm sorry.
        {"word": "絞める", "reading": "しめる", "jmdict_id": 1280820, "flags": ["community"]},   # to be wet, to become wet, to be damp
        {"word": "それなら", "reading": "それなら", "jmdict_id": 1406070, "flags": ["community"]},   # If that's the case..., If so..., That be
        {"word": "どういたしまして", "reading": "どういたしまして", "jmdict_id": 1009030, "flags": ["community"]},   # you are welcome, don't mention it
        {"word": "乗り越し", "reading": "のりこし", "jmdict_id": 1600480, "flags": ["community"]},   # riding past (one's station)
    ],
    "1": [
        {"word": "市場", "reading": "しじょう", "jmdict_id": 1308305, "flags": ["community"]},   # (the) market (as a concept)
        {"word": "むら", "reading": "むら", "jmdict_id": 1481330, "flags": ["community"]},   # unevenness, inconsistency, irregularity
        {"word": "やつ", "reading": "やつ", "jmdict_id": 1445640, "flags": ["community"]},   # (vulg.) fellow, guy, chap
        {"word": "空間", "reading": "くうかん", "jmdict_id": 1245450, "flags": ["community"]},   # space, room, airspace
        {"word": "主", "reading": "しゅ", "jmdict_id": 1324950, "flags": ["community"]},   # owner, master, god
        {"word": "所有", "reading": "しょゆう", "jmdict_id": 1343390, "flags": ["community"]},   # one's possessions, ownership
        {"word": "ゆえ", "reading": "ゆえ", "jmdict_id": 1267120, "flags": ["community"]},   # reason, cause, circumstances
        {"word": "勝手", "reading": "かって", "jmdict_id": 1346190, "flags": ["community"]},   # kitchen; one's way, selfishness
        {"word": "我", "reading": "われ", "jmdict_id": 1196670, "flags": ["community"]},   # me, oneself, self, ego
        {"word": "振り返る", "reading": "ふりかえる", "jmdict_id": 1361290, "flags": ["community"]},   # to turn head, to turn around, to look ba
        {"word": "天", "reading": "てん", "jmdict_id": 1438210, "flags": ["community"]},   # heaven, sky
        {"word": "ひび", "reading": "ひび", "jmdict_id": 1010590, "flags": ["community"]},   # crack, fissure, flaw
        {"word": "みなす", "reading": "みなす", "jmdict_id": 1604630, "flags": ["community"]},   # to consider as, to regard
        {"word": "実家", "reading": "じっか", "jmdict_id": 1320900, "flags": ["community"]},   # (one's parents') home
        {"word": "おやじ", "reading": "おやじ", "jmdict_id": 1365330, "flags": ["community"]},   # one's father, old man, one's boss
        {"word": "魂", "reading": "たましい", "jmdict_id": 1579170, "flags": ["community"]},   # soul, spirit
        {"word": "出現", "reading": "しゅつげん", "jmdict_id": 1338820, "flags": ["community"]},   # appearance, arrival
        {"word": "主", "reading": "ぬし", "jmdict_id": 1324960, "flags": ["community"]},   # owner, master, god
        {"word": "圧倒", "reading": "あっとう", "jmdict_id": 1153260, "flags": ["community"]},   # overwhelm, overpower
        {"word": "折", "reading": "おり", "jmdict_id": 1385780, "flags": ["community"]},   # chance, occasion
        {"word": "相対", "reading": "そうたい", "jmdict_id": 1401110, "flags": ["community"]},   # relative
        {"word": "陣", "reading": "じん", "jmdict_id": 1956490, "flags": ["community"]},   # battle formation, camp, encampment
        {"word": "取り付ける", "reading": "とりつける", "jmdict_id": 1326910, "flags": ["community"]},   # to furnish, to install; to get someone's
        {"word": "天下", "reading": "てんか", "jmdict_id": 1438470, "flags": ["community"]},   # the world, whole country
        {"word": "一見", "reading": "いっけん", "jmdict_id": 1162170, "flags": ["community"]},   # a look, a glimpse, glance; first meeting
        {"word": "リード", "reading": "リード", "jmdict_id": 1140700, "flags": ["community"]},   # lead; reed
        {"word": "傷つける", "reading": "きずつける", "jmdict_id": 1345930, "flags": ["community"]},   # to wound, to hurt someone's feelings
        {"word": "汚れ", "reading": "よごれ", "jmdict_id": 1612200, "flags": ["community"]},   # dirt, filth
        {"word": "転ずる", "reading": "てんずる", "jmdict_id": 1441050, "flags": ["community"]},   # to turn, to shift
        {"word": "種々", "reading": "しゅじゅ", "jmdict_id": 1594850, "flags": ["community"]},   # variety
        {"word": "情けない", "reading": "なさけない", "jmdict_id": 1599480, "flags": ["community"]},   # miserable, pitiable, shameful
        {"word": "速やか", "reading": "すみやか", "jmdict_id": 1405000, "flags": ["community"]},   # speedy
        {"word": "芸", "reading": "げい", "jmdict_id": 1956190, "flags": ["community"]},   # art, accomplishment, performance
        {"word": "踏み込む", "reading": "ふみこむ", "jmdict_id": 1450150, "flags": ["community"]},   # to step into (someone else's territory, 
        {"word": "バッテリー", "reading": "バッテリー", "jmdict_id": 1099210, "flags": ["community"]},   # battery
        {"word": "潮", "reading": "しお", "jmdict_id": 1428620, "flags": ["community"]},   # tide
        {"word": "フィルタ", "reading": "フィルタ", "jmdict_id": 1109330, "flags": ["community"]},   # filter
        {"word": "郷土", "reading": "きょうど", "jmdict_id": 1238510, "flags": ["community"]},   # homeland
        {"word": "斡旋", "reading": "あっせん", "jmdict_id": 1153410, "flags": ["community"]},   # kind offices, mediation
        {"word": "予言", "reading": "よげん", "jmdict_id": 1584920, "flags": ["community"]},   # prediction, promise, prognostication
        {"word": "題する", "reading": "だいする", "jmdict_id": 1983720, "flags": ["community"]},   # to title
        {"word": "内心", "reading": "ないしん", "jmdict_id": 1458550, "flags": ["community"]},   # innermost thoughts, real intention, inmo
        {"word": "打ち明ける", "reading": "うちあける", "jmdict_id": 1588130, "flags": ["community"]},   # to confess, to be open
        {"word": "だったら", "reading": "だったら", "jmdict_id": 1007400, "flags": ["community"]},   # if it's the case
        {"word": "凝らす", "reading": "こらす", "jmdict_id": 1239010, "flags": ["community"]},   # to concentrate, to devote, to peer into
        {"word": "年賀", "reading": "ねんが", "jmdict_id": 1468240, "flags": ["community"]},   # New Year's greetings, New Year's card
        {"word": "溝", "reading": "みぞ", "jmdict_id": 1578720, "flags": ["community"]},   # ditch, drain, gutter, gap
        {"word": "凝る", "reading": "こる", "jmdict_id": 1239070, "flags": ["community"]},   # to stiffen, to harden
        {"word": "脅かす", "reading": "おびやかす", "jmdict_id": 1578075, "flags": ["community"]},   # to threaten, to coerce
        {"word": "生きがい", "reading": "いきがい", "jmdict_id": 1378550, "flags": ["community"]},   # something one lives for, very important
        {"word": "立ち去る", "reading": "たちさる", "jmdict_id": 1551310, "flags": ["community"]},   # to leave, to depart
        {"word": "敗北", "reading": "はいぼく", "jmdict_id": 1472610, "flags": ["community"]},   # defeat (as a verb it means 'to be defeat
        {"word": "人影", "reading": "ひとかげ", "jmdict_id": 1580660, "flags": ["community"]},   # man's shadow, soul
        {"word": "類", "reading": "るい", "jmdict_id": 1556040, "flags": ["community"]},   # kind, class, family
        {"word": "原型", "reading": "げんけい", "jmdict_id": 1261300, "flags": ["community"]},   # prototype, model, archetypal
        {"word": "晩年", "reading": "ばんねん", "jmdict_id": 1482230, "flags": ["community"]},   # (one's) last years
        {"word": "うつむく", "reading": "うつむく", "jmdict_id": 1563570, "flags": ["community"]},   # to look downward, to stoop
        {"word": "切り替え", "reading": "きりかえ", "jmdict_id": 1591760, "flags": ["community"]},   # exchange, conversion, switchover
        {"word": "内緒", "reading": "ないしょ", "jmdict_id": 1458510, "flags": ["community"]},   # secrecy, privacy, secret
        {"word": "内蔵", "reading": "ないぞう", "jmdict_id": 1458750, "flags": ["community"]},   # internal organ; built-in
        {"word": "本国", "reading": "ほんごく", "jmdict_id": 1522530, "flags": ["community"]},   # one's own country
        {"word": "つくづく", "reading": "つくづく", "jmdict_id": 1008110, "flags": ["community"]},   # completely, really
        {"word": "ふらふら", "reading": "ふらふら", "jmdict_id": 1011060, "flags": ["community"]},   # unsteady on one's feet, totter, dizzy
        {"word": "抱っこ", "reading": "だっこ", "jmdict_id": 1516410, "flags": ["community"]},   # (child's) hug
        {"word": "ぼける", "reading": "ぼける", "jmdict_id": 1288490, "flags": ["community"]},   # to grow senile, to fade
        {"word": "おふくろ", "reading": "おふくろ", "jmdict_id": 1002370, "flags": ["community"]},   # mother
        {"word": "かばう", "reading": "かばう", "jmdict_id": 1483060, "flags": ["community"]},   # to protect someone, to&nbsp;&nbsp;cover 
        {"word": "玩具", "reading": "がんぐ", "jmdict_id": 2863107, "flags": ["community"]},   # toy
        {"word": "めど", "reading": "めど", "jmdict_id": 1535470, "flags": ["community"]},   # goal, outlook
        {"word": "スト", "reading": "スト", "jmdict_id": 1070780, "flags": ["community"]},   # (abbr.) strike
        {"word": "ふける", "reading": "ふける", "jmdict_id": 1419010, "flags": ["community"]},   # to indulge in, to give oneself up to, to
        {"word": "立方", "reading": "りっぽう", "jmdict_id": 1551820, "flags": ["community"]},   # cube
        {"word": "てっぺん", "reading": "てっぺん", "jmdict_id": 1440340, "flags": ["community"]},   # top, summit, apex
        {"word": "念願", "reading": "ねんがん", "jmdict_id": 1469390, "flags": ["community"]},   # one's heart's desire, earnest petition
        {"word": "身の回り", "reading": "みのまわり", "jmdict_id": 1365590, "flags": ["community"]},   # one's personal appearance, personal belo
        {"word": "束ねる", "reading": "たばねる", "jmdict_id": 1581320, "flags": ["community"]},   # to tie up in a bundle, to control
        {"word": "強", "reading": "きょう", "jmdict_id": 2020300, "flags": ["community"]},   # strong
        {"word": "札", "reading": "ふだ", "jmdict_id": 1298970, "flags": ["community"]},   # token, label; ticket, card; charm, talis
        {"word": "見習う", "reading": "みならう", "jmdict_id": 1259700, "flags": ["community"]},   # to follow another's example
        {"word": "ブル", "reading": "ブル", "jmdict_id": 1114300, "flags": ["community"]},   # bull
        {"word": "母国", "reading": "ぼこく", "jmdict_id": 1515060, "flags": ["community"]},   # one's home country (same as 自分の国 (じぶんのくに
        {"word": "くじ", "reading": "くじ", "jmdict_id": 1570360, "flags": ["community"]},   # lottery, lot
        {"word": "はらはら", "reading": "はらはら", "jmdict_id": 1096260, "flags": ["community"]},   # feel nervous
        {"word": "へり", "reading": "へり", "jmdict_id": 2056370, "flags": ["community"]},   # edge
        {"word": "ありふれる", "reading": "ありふれる", "jmdict_id": 2007210, "flags": ["community"]},   # common, ordinary, routine
        {"word": "渚", "reading": "なぎさ", "jmdict_id": 1343540, "flags": ["community"]},   # water's edge, beach, shore
        {"word": "身の上", "reading": "みのうえ", "jmdict_id": 1365600, "flags": ["community"]},   # one's future, one's welfare, one's perso
        {"word": "決", "reading": "けつ", "jmdict_id": 1956210, "flags": ["community"]},   # decision, vote
        {"word": "びら", "reading": "びら", "jmdict_id": 1105970, "flags": ["community"]},   # handout, leaflet
        {"word": "見計らう", "reading": "みはからう", "jmdict_id": 1259510, "flags": ["community"]},   # to choose at one's own discretion
        {"word": "灌漑", "reading": "かんがい", "jmdict_id": 1213270, "flags": ["community"]},   # irrigation
        {"word": "華奢", "reading": "きゃしゃ", "jmdict_id": 1195660, "flags": ["community"]},   # delicate, slender
        {"word": "目下", "reading": "もっか", "jmdict_id": 1535330, "flags": ["community"]},   # at present, now
        {"word": "寒気", "reading": "さむけ", "jmdict_id": 1210410, "flags": ["community"]},   # chill, shiver, cold
        {"word": "押し切る", "reading": "おしきる", "jmdict_id": 1180270, "flags": ["community"]},   # to have one's own way
        {"word": "大家", "reading": "たいか", "jmdict_id": 1413150, "flags": ["community"]},   # rich family, distinguished family
        {"word": "中腹", "reading": "ちゅうふく", "jmdict_id": 1425440, "flags": ["community"]},   # mountain side, halfway up
        {"word": "ひな祭り", "reading": "ひなまつり", "jmdict_id": 1373440, "flags": ["community"]},   # Girls' (dolls') Festival
        {"word": "失脚", "reading": "しっきゃく", "jmdict_id": 1319850, "flags": ["community"]},   # losing one's standing, being overthrown,
        {"word": "とぼける", "reading": "とぼける", "jmdict_id": 1610900, "flags": ["community"]},   # to play dumb, to feign ignorance, to pla
        {"word": "おんぶ", "reading": "おんぶ", "jmdict_id": 1498040, "flags": ["community"]},   # carrying on one's back (erg. Baby)
        {"word": "はたく", "reading": "はたく", "jmdict_id": 2829135, "flags": ["community"]},   # to strike, to clap, to dust, to beat
        {"word": "往診", "reading": "おうしん", "jmdict_id": 1179710, "flags": ["community"]},   # doctor's visit, house call
        {"word": "うたた寝", "reading": "うたたね", "jmdict_id": 1663100, "flags": ["community"]},   # dozing, napping
        {"word": "埋める", "reading": "うずめる", "jmdict_id": 1524490, "flags": ["community"]},   # to bury, to fill
        {"word": "つっつく", "reading": "つっつく", "jmdict_id": 1456960, "flags": ["community"]},   # to prompt someone
        {"word": "ほどける", "reading": "ほどける", "jmdict_id": 1198920, "flags": ["community"]},   # to come untied, to come apart
        {"word": "立て替える", "reading": "たてかえる", "jmdict_id": 1551550, "flags": ["community"]},   # to pay in advance, to pay for another
        {"word": "受け持ち", "reading": "うけもち", "jmdict_id": 1588070, "flags": ["community"]},   # charge (of something), matter in one's c
        {"word": "ティシュペーパー", "reading": "ティシュペーパー", "jmdict_id": 1079110, "flags": ["community"]},   # tissue
        {"word": "成育", "reading": "せいいく", "jmdict_id": 1375640, "flags": ["community"]},   # growth, raising
        {"word": "しとやか", "reading": "しとやか", "jmdict_id": 1337340, "flags": ["community"]},   # graceful
        {"word": "人気", "reading": "ひとけ", "jmdict_id": 1367020, "flags": ["community"]},   # sign of life
        {"word": "つぶら", "reading": "つぶら", "jmdict_id": 1598070, "flags": ["community"]},   # round, rotund
        {"word": "どぶ", "reading": "どぶ", "jmdict_id": 2853262, "flags": ["community"]},   # ditch, drain, gap
        {"word": "ひずむ", "reading": "ひずむ", "jmdict_id": 2846709, "flags": ["community"]},   # to warp, to be distorted
        {"word": "マイクロフォン", "reading": "マイクロフォン", "jmdict_id": 1126770, "flags": ["community"]},   # microphone
        {"word": "ロープウエイ", "reading": "ロープウエイ", "jmdict_id": 1146760, "flags": ["community"]},   # ropeway, aerial tram
        {"word": "言付け", "reading": "ことづけ", "jmdict_id": 1593320, "flags": ["community"]},   # to leave a message
        {"word": "とっさに", "reading": "とっさに", "jmdict_id": 1565180, "flags": ["community"]},   # at once
        {"word": "かなわない", "reading": "かなわない", "jmdict_id": 1002950, "flags": ["community"]},   # be beyond one's power, be unable
        {"word": "仮に", "reading": "かりに", "jmdict_id": 1187300, "flags": ["community"]},   # temporarily; if, for argument's sake
        {"word": "群衆", "reading": "ぐんしゅう", "jmdict_id": 1592510, "flags": ["community"]},   # (social) group, crowd, mob
        {"word": "あしからず", "reading": "あしからず", "jmdict_id": 1151300, "flags": ["community"]},   # don't take me wrong, but..., I'm sorry
        {"word": "イェス", "reading": "イェス", "jmdict_id": 2843921, "flags": ["community"]},   # yes; Jesus
        {"word": "粋", "reading": "すい", "jmdict_id": 2848938, "flags": ["community"]},   # essence
        {"word": "先", "reading": "せん", "jmdict_id": 1387220, "flags": ["community"]},   # priority, precedence, previous
        {"word": "やけに", "reading": "やけに", "jmdict_id": 1012770, "flags": ["community"]},   # sure, very
    ],
}
for _l, _words in COMMUNITY_ADDITIONS.items():
    ADDITIONS.setdefault(_l, []).extend(_words)

# 2026-10-14 (owner): words on no list at all, with levels we chose. Flagged
# "ours". First batch: the other half of JLPT-tested kanji pairs (産む / 生む,
# 絶つ / 断つ …), which since the same-kanji rule need their own tiles: a 生む
# card no longer counts for 産む. The Word Addition Project adds more here.
OUR_ADDITIONS = {
    "3": [
        {"word": "捕らえる", "reading": "とらえる", "jmdict_id": 1598960, "flags": ["ours"]},   # catch, arrest (vs 捉える)
    ],
    "2": [
        {"word": "生む", "reading": "うむ", "jmdict_id": 1588410, "flags": ["ours"]},   # produce, give rise to (vs 産む)
        {"word": "捉える", "reading": "とらえる", "jmdict_id": 1598960, "flags": ["ours"]},   # grasp, perceive (vs 捕らえる)
        {"word": "薦める", "reading": "すすめる", "jmdict_id": 1595680, "flags": ["ours"]},   # recommend (a thing, a person) (vs 勧める)
    ],
    "1": [
        {"word": "断つ", "reading": "たつ", "jmdict_id": 1597030, "flags": ["ours"]},   # cut off, give up (a habit) (vs 絶つ)
        {"word": "修める", "reading": "おさめる", "jmdict_id": 1331900, "flags": ["ours"]},   # study, master (vs 収める / 納める / 治める)
        {"word": "創る", "reading": "つくる", "jmdict_id": 1597890, "flags": ["ours"]},   # create (something new) (vs 作る / 造る)
    ],
}
for _l, _words in OUR_ADDITIONS.items():
    ADDITIONS.setdefault(_l, []).extend(_words)

# OpenJLPT entries written in kana whose word is a kanji one (owner
# 2026-10-28): Waller's N3 出 (で) "coming out; outflow; graduate (of)",
# JMdict 1896380, was listed as で, so the particle / conjunction で (no
# kanji) borrowed 出 as its spelling and meaning. (word, reading, jmdict_id) → word.
WORD_FIXES = {("で", "で", 1896380): "出"}

UK = "word usually written using kana alone"
KANJI = re.compile(r"[一-鿿㐀-䶿々]")
out = {}; stats = collections.Counter(); kata_words = []; added = 0; added_r = 0
to_kana = []
for l in "54321":
    rows = []
    entries = json.load(open(f"ojlpt/n{l}.json", encoding="utf-8"))
    present = {(e["word"], e["reading"]) for e in entries}
    entries += [a for a in ADDITIONS.get(l, []) if (a["word"], a["reading"]) not in present]
    for e in entries:
        w, r = e["word"].strip(), e["reading"].strip()
        w = WORD_FIXES.get((w, r, e.get("jmdict_id")), w)
        alts = [a for a in (e.get("other_forms") or []) if a and a != w]
        alt_reads = []
        flags = list(e.get("flags") or [])   # e.g. "community" for COMMUNITY_ADDITIONS
        ent = J.get(e.get("jmdict_id"))
        if ent:
            # Every kanji spelling JMdict knows for this word, so a kana list
            # entry (できる, あと, ない) also matches 出来る / 後 / 無い cards.
            # Matching still checks the card's reading, so homographs are safe.
            for k in ent["keb"]:
                if k != w and k not in alts:
                    alts.append(k); added += 1
            # Every reading of the same word, so 私 (わたくし) on the list also
            # matches a 私 (わたし) card.
            alt_reads = [x for x in ent["reb"] if x != r]
            added_r += len(alt_reads)
            # Words JMdict marks as usually written in kana are listed in kana
            # (煩い → うるさい, 流石 → さすが), with the kanji kept as an
            # alternate spelling. Learners shouldn't need the archaic kanji,
            # and under the add-on's script rule a kana card can only count for
            # a kana list entry. Based on the word's first sense.
            first_misc = ent["misc"][0] if ent["misc"] else []
            if (UK in (first_misc or []) and KANJI.search(w)
                    and not KANJI.search(r)):
                alts = [w] + [a for a in alts if a != w and a != r]
                w = r
                to_kana.append((l, alts[0], r))
        if KATA.match(w) and ent:
            nonen = [x for x in ent["langs"] if x != "eng"]
            abbr = any("abbreviation" in m for m in ent["misc"])
            if ent["wasei"]: flags.append("wasei")
            elif nonen: flags.append("loan-" + nonen[0])
            elif abbr: flags.append("abbr")
            else: flags.append("eng")
            kata_words.append((w, "N" + l, flags[-1]))
        for f in flags: stats[f] += 1
        rows.append((w, r, alts, flags, alt_reads))
    out["N" + l] = rows

print("flags:", dict(stats), "| JMdict spellings added:", added, "| readings added:", added_r)
print("listed in kana (usually-kana words):", len(to_kana))
for lvl in "54321":
    print(f"  N{lvl}:", " ".join(f"{k}→{r}" for l, k, r in to_kana if l == lvl)[:900])
for lvl, rows in out.items():
    with open(f"{A}/jlpt_{lvl.lower()}.txt", "w", encoding="utf-8", newline="\n") as f:
        f.write(f"# JLPT {lvl} vocabulary list — {len(rows)} words\n")
        f.write("# Source: OpenJLPT (github.com/evanclan/OpenJLPT), CC BY-SA 4.0,\n")
        f.write("#   levels from Jonathan Waller's JLPT lists (tanos.co.uk), CC BY.\n")
        f.write("# Alternate spellings and loanword flags derived from JMdict (EDRDG), CC BY-SA 4.0.\n")
        f.write("# Format: word<TAB>reading<TAB>alternate spellings (|)<TAB>flags (,)<TAB>alternate readings (|)\n")
        f.write("# Flags: eng = English loanword, wasei = wasei-eigo, abbr = abbreviated loanword,\n")
        f.write("#        loan-xxx = loanword from another language (ISO 639-2 code),\n")
        f.write("#        community = not on Waller's lists; added from community JLPT lists\n")
        f.write("#        ours = on no list; added by this add-on with a level we chose\n")
        f.write("#        (jamsinclair/open-anki-jlpt-decks, elzup/jlpt-word-list), their level\n\n")
        for w, r, alts, flags, alt_reads in rows:
            cols = [w, r, "|".join(alts), ",".join(flags), "|".join(alt_reads)]
            while cols[-1] == "":
                cols.pop()
            f.write("\t".join(cols) + "\n")
    print(lvl, len(rows))
