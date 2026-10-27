"""
freq_splits.py
Hand-made decisions about which frequency-list words are one tile and which
are several (owner 2026-10-12). The rule: words that differ in meaning or
use get their own tiles; the same word with another reading (明日 あした /
あす) or another kanji spelling with the same meaning (年配 / 年輩) stays one
tile. Frequency list only: the JLPT lists are never changed by this.

Why, from a learner's side (the owner's words: "those have different
meanings and should have their own cards"): a tile stands for something you
learn once. Recognising 聞く doesn't mean you understand 聴く ("listen
attentively"), and knowing 返る ("be returned") doesn't cover 帰る ("go
home"), so each needs its own card and its own tile; one tile for both
would show a word as known when half of it isn't. But 年配 / 年輩 or 明日
あした / あす are one word to a learner: recognising either is the same
knowledge, and splitting them would ask for redundant cards. The corpus
(UniDic) often lumps the first kind together and splits the second, which
is why these lists exist. Changing a list: add the pair with a comment
saying how the meanings differ, then bump freq_data.LIST_VERSION (and
rebuild freq_bccwj.txt for KIND1_SPLITS).

Used by tools/build_freq.py (KIND1_SPLITS) and freq_data.load() (the rest).
No imports: the build script loads this file on its own.
"""

# ── Kind 1: different BCCWJ words that JMdict files under one entry ─────────
# BCCWJ counted them separately; JMdict's shared entry gave them the same
# display and spellings, so they used to merge into one tile. Each group is
# {BCCWJ lemma: display}. The build keeps each lemma its own row, shown as
# its display, without the other members' spellings.
# (Kept merged on purpose — same meaning: 唯/只, 何れ/どれ, 扠/さて, 割/割り,
# 巻/巻き, 落葉/落ち葉, 年配/年輩, 過酷/苛酷, 呆然/茫然, 御輿/神輿, 城跡/城址,
# 繊維/線維, 柔らかい/軟らかい, 定形/定型, 知/智, 共同/協同,
# 基準/規準, 入れる/容れる.)
KIND1_SPLITS = [
    {"最も": "最も", "尤も": "尤も"},                 # most / reasonable; however
    {"元": "元", "基": "基", "素": "素"},             # origin / basis / ingredient
    {"町": "町", "街": "街"},                         # town / street, downtown
    {"足": "足", "脚": "脚"},                         # foot / leg (also furniture legs)
    {"始め": "始め", "初め": "初め"},                 # start of an activity / first time
    {"開ける": "開ける", "明ける": "明ける", "空ける": "空ける"},   # open / dawn, end / empty
    # BCCWJ has no 開く (あく) of its own: "open" is counted as 明く.
    {"空く": "空く", "明く": "開く"},                 # become vacant / open
    {"絵": "絵", "画": "画"},                         # picture (え) / painting suffix (が)
    {"保証": "保証", "保障": "保障"},                 # guarantee / security (安全保障)
    {"基板": "基板", "基盤": "基盤"},                 # circuit board / foundation
    {"玉": "玉", "弾": "弾"},                         # ball, bead / bullet
    {"主席": "主席", "首席": "首席"},                 # chairman / top of the class
    {"故事": "故事", "古事": "古事"},                 # historical anecdote / ancient matters
    {"剛": "剛", "豪": "豪"},                         # hardness, firmness / might; Australia
    {"飛び": "飛び", "跳び": "跳び"},                 # flying / jumping
    {"凝り": "凝り", "痼": "しこり"},                 # stiffness / lump; lingering ill feeling
    {"勤め": "勤め", "務め": "務め"},                 # job, employment / duty
    {"習得": "習得", "修得": "修得"},                 # learning (a skill) / completing (a course)
    {"趣旨": "趣旨", "主旨": "主旨"},                 # intent / main point
    {"機械": "機械", "器械": "器械"},                 # machine / instrument, apparatus
    {"直感": "直感", "直観": "直観"},                 # gut feeling / intuition (philosophy)
    {"一人": "一人", "独り": "独り"},                 # one person / alone
    {"広聴": "広聴", "公聴": "公聴"},                 # gathering public opinion / public hearing
    {"混じる": "混じる", "交じる": "交じる"},          # blend in / mingle (still distinguishable); owner 2026-10-12
]

# ── Kind 2: one BCCWJ word read two ways, where the readings differ in
# meaning. Every other reading split (明日 あした / あす …) is merged at load.
# 今日 きょう today / こんにち nowadays; 汚す よごす dirty / けがす defile;
# 避ける さける avoid / よける dodge; 汁 しる juice, soup / つゆ broth, dipping sauce.
READING_SPLITS = {"今日", "汚す", "避ける", "汁"}

# ── Kind 3: spellings BCCWJ never separated (UniDic counts 聴く as 聞く,
# 帰る as 返る). Each gets its own tile right after the row it's counted in,
# with that row's frequency (approximate: the corpus has no split), and the
# row stops matching it. (row spelling, reading) → its own spellings.
# Mostly the 異字同訓 pairs (same reading, different kanji and use).
SHARED_SPELLINGS = [
    (("会う", "あう"), ["遭う"]),   # meet / meet with (something bad)
    (("上げる", "あげる"), ["挙げる", "揚げる"]),   # raise / raise (a hand, an example), hold (a ceremony); deep-fry
    (("暖かい", "あたたかい"), ["温かい"]),   # warm (weather, air) / warm (to the touch, kind)
    (("温める", "あたためる"), ["暖める"]),   # warm (a thing) / warm (a room, the air)
    (("当てる", "あてる"), ["充てる", "宛てる"]),   # hit, apply / allot; address (a letter)
    (("表す", "あらわす"), ["現す"]),   # express / reveal, appear
    (("現れる", "あらわれる"), ["表れる"]),   # appear / show (feelings, results)
    (("打つ", "うつ"), ["討つ", "撃つ"]),   # hit / attack, defeat; shoot
    (("生む", "うむ"), ["産む"]),   # produce, create / give birth
    (("犯す", "おかす"), ["侵す", "冒す"]),   # commit (a crime) / invade; brave (danger)
    (("収める", "おさめる"), ["納める", "治める", "修める"]),   # put away, obtain / pay, deliver; govern; study
    (("収まる", "おさまる"), ["納まる", "治まる"]),   # fit, settle / be paid; be at peace
    (("降りる", "おりる"), ["下りる"]),   # get off / go down; be granted
    (("変える", "かえる"), ["換える", "替える", "代える"]),   # change / exchange; replace; substitute
    (("返る", "かえる"), ["帰る"]),   # be returned / go home
    (("返す", "かえす"), ["帰す"]),   # return (a thing) / send (someone) home
    (("掛ける", "かける"), ["懸ける", "架ける", "賭ける"]),   # hang, put on / stake; build across; bet
    (("掛かる", "かかる"), ["懸かる", "架かる"]),   # hang, take (time) / depend on; span
    (("硬い", "かたい"), ["固い", "堅い"]),   # hard (material) / firm; solid, steady
    (("聞く", "きく"), ["聴く"]),   # hear / listen attentively
    (("効く", "きく"), ["利く"]),   # be effective / work, function (気が利く)
    (("切る", "きる"), ["斬る"]),   # cut / slay with a sword
    (("差す", "さす"), ["指す", "刺す", "挿す", "射す"]),   # shine, hold up / point; stab; insert; (light) shine in
    (("探す", "さがす"), ["捜す"]),   # look for (something wanted) / search for (something lost)
    (("締める", "しめる"), ["閉める", "絞める"]),   # tighten / close; strangle
    (("勧める", "すすめる"), ["薦める"]),   # advise, urge / recommend
    (("立つ", "たつ"), ["建つ"]),   # stand / be built
    (("断つ", "たつ"), ["絶つ"]),   # cut off / sever (ties), end
    (("立てる", "たてる"), ["建てる"]),   # stand (something) up / build
    (("付く", "つく"), ["就く"]),   # attach / take (a post), go to (bed)
    (("付ける", "つける"), ["着ける"]),   # attach / wear, put on
    (("作る", "つくる"), ["造る", "創る"]),   # make / build on a large scale; create
    (("勤める", "つとめる"), ["務める"]),   # work at (a job) / serve as (a role)
    (("取る", "とる"), ["採る", "執る", "捕る", "撮る"]),   # take / adopt, hire; exercise (authority); catch; photograph
    (("直す", "なおす"), ["治す"]),   # repair / cure
    (("直る", "なおる"), ["治る"]),   # be repaired / heal
    (("上る", "のぼる"), ["登る", "昇る"]),   # go up / climb; rise
    (("計る", "はかる"), ["量る"]),   # measure (time, length) / weigh, gauge
    (("図る", "はかる"), ["謀る"]),   # plan / plot
    (("早い", "はやい"), ["速い"]),   # early / fast
    (("張る", "はる"), ["貼る"]),   # stretch / stick, paste
    (("増える", "ふえる"), ["殖える"]),   # increase / multiply, breed
    (("見る", "みる"), ["診る", "観る", "看る"]),   # see / examine (a patient); watch (a show); look after
    (("沸く", "わく"), ["湧く"]),   # boil / gush, spring up
    (("伸びる", "のびる"), ["延びる"]),   # stretch, grow / be extended, postponed
    (("伸ばす", "のばす"), ["延ばす"]),   # stretch / extend, postpone
    (("乗る", "のる"), ["載る"]),   # ride / be placed on; be published
    (("乗せる", "のせる"), ["載せる"]),   # give a ride / load; publish
    (("乾く", "かわく"), ["渇く"]),   # dry / be thirsty
    (("静める", "しずめる"), ["鎮める"]),   # quiet / suppress, pacify
    (("整える", "ととのえる"), ["調える"]),   # put in order / prepare, arrange
    (("離れる", "はなれる"), ["放れる"]),   # move away / be set free
    (("越える", "こえる"), ["超える"]),   # cross over / exceed
    (("思う", "おもう"), ["想う"]),   # think / think of fondly, long for
    (("吊る", "つる"), ["釣る"]),   # hang / fish
    (("早める", "はやめる"), ["速める"]),   # bring forward (in time) / speed up
    (("止める", "やめる"), ["辞める"]),   # stop / quit (a job)
    # Owner 2026-10-12 (受ける's 承ける stays with it).
    (("有る", "ある"), ["在る"]),   # have / be located
    (("他", "ほか"), ["外"]),   # other (他) / outside of, besides (外)
    (("目", "め"), ["眼"]),   # eye / eyeball; insight
    (("使う", "つかう"), ["遣う"]),   # use / use with care (気を遣う); spend
    (("受ける", "うける"), ["請ける"]),   # receive / undertake (work)
    # Owner 2026-10-14 (JLPT-tested pairs; "if they need separate cards they
    # should have their own tile"). "a|b": tile a, also spelled b.
    (("飛ぶ", "とぶ"), ["跳ぶ"]),   # fly / jump, leap
    (("出会う", "であう"), ["出合う"]),   # meet (a person) / come across (a thing, an event)
    (("長い", "ながい"), ["永い"]),   # long / eternal, lasting
    (("捉える", "とらえる"), ["捕らえる|捕える"]),   # grasp (a meaning, a feature) / catch, arrest
]

# ── Fix 2: compounds the short-unit list splits (でも = で+も, お金 = お+金)
# join the ranking when their estimated rank (freq_extra.txt, "e") is above
# this. Below it they'd mostly be transparent compounds (環境問題 …).
COMPOUND_RANK_LIMIT = 6000
# Display/reading fixes for those compounds (freq_extra keeps JMdict's first
# spelling and BCCWJ's reading).
COMPOUND_DISPLAY = {"其れから": "それから", "其れでは": "それでは"}
COMPOUND_READING = {"私たち": "わたしたち", "日本人": "にほんじん", "日本語": "にほんご"}

# ── Meanings for tiles whose JMdict entry is shared with another tile (聴く
# shares 聞く's) or missing. (display, reading) → [part of speech, meanings].
# Written for this add-on; shown instead of meanings.json for these keys.
GLOSSES = {
    # Kind 3
    ("温かい", "あたたかい"): ["i-adjective", "warm (to the touch: food, drinks, the body)",
                           "warm-hearted; kind; genial"],
    ("充てる", "あてる"): ["Ichidan verb, transitive", "to allot; to assign; to set aside (money, time) for"],
    ("表れる", "あらわれる"): ["Ichidan verb, intransitive",
                           "to show; to be expressed (feelings in one's face, in words)",
                           "to be reflected (in results, in figures)"],
    ("冒す", "おかす"): ["Godan verb, transitive", "to brave; to risk (danger)",
                       "to affect; to attack (of a disease)", "to desecrate; to profane"],
    ("修める", "おさめる"): ["Ichidan verb, transitive", "to study; to master (a subject or skill)",
                         "to cultivate (one's character); to conduct oneself well"],
    ("懸ける", "かける"): ["Ichidan verb, transitive", "to stake; to risk (one's life, honour)",
                        "to offer (a reward or prize)"],
    ("架ける", "かける"): ["Ichidan verb, transitive", "to build (a bridge); to span; to lay (a cable) across"],
    ("懸かる", "かかる"): ["Godan verb, intransitive", "to depend on; to rest on (an outcome)",
                        "to be at stake", "to hang (in the sky)"],
    ("架かる", "かかる"): ["Godan verb, intransitive", "to span; to be built across (a bridge over a river)"],
    ("聴く", "きく"): ["Godan verb, transitive", "to listen (attentively: music, a lecture, a radio)",
                     "to hear (testimony, someone's opinion)"],
    ("利く", "きく"): ["Godan verb, intransitive", "to work; to function (brakes, one's sense of smell)",
                     "to be possible; to allow (e.g. 無理が利く, 融通が利く)",
                     "気が利く: to be thoughtful; to be tactful"],
    ("薦める", "すすめる"): ["Ichidan verb, transitive",
                         "to recommend (a person or thing for a post or purpose)"],
    ("着ける", "つける"): ["Ichidan verb, transitive", "to put on; to wear (accessories, a seatbelt, a uniform)",
                        "to bring (a car or boat) alongside; to pull up"],
    ("創る", "つくる"): ["Godan verb, transitive", "to create (something new and original); to found"],
    ("執る", "とる"): ["Godan verb, transitive", "to take up (a pen); to conduct (business)",
                     "to exercise (authority); to carry out (procedures)"],
    ("謀る", "はかる"): ["Godan verb, transitive", "to plot; to scheme", "to deceive; to trick"],
    ("観る", "みる"): ["Ichidan verb, transitive", "to watch (a film, play or sport); to view",
                     "to see (the sights)"],
    ("看る", "みる"): ["Ichidan verb, transitive", "to look after; to care for (a patient, a child)"],
    ("鎮める", "しずめる"): ["Ichidan verb, transitive", "to calm; to suppress (a riot); to quell",
                         "to soothe (pain); to put out (a fire)"],
    ("調える", "ととのえる"): ["Ichidan verb, transitive",
                           "to prepare; to arrange (a meal, funds, documents)",
                           "to settle (a deal); to tune; to season"],
    ("想う", "おもう"): ["Godan verb, transitive", "to think of fondly; to long for; to love",
                       "to dwell on (someone)"],
    ("速める", "はやめる"): ["Ichidan verb, transitive", "to quicken; to speed up (pace, tempo)"],
    ("跳ぶ", "とぶ"): ["Godan verb, intransitive", "to jump; to leap; to spring; to bound (off the ground)"],
    ("出合う", "であう"): ["Godan verb, intransitive",
                        "to come across; to happen upon (a thing, an event, a scene)",
                        "to meet; to flow together (rivers)"],
    ("永い", "ながい"): ["i-adjective", "eternal; lasting; long (in time: 永い眠り, 永い別れ)"],
    ("捕らえる", "とらえる"): ["Ichidan verb, transitive", "to catch; to capture; to arrest (a criminal, prey)",
                           "to seize; to grab hold of"],
    ("捉える", "とらえる"): ["Ichidan verb, transitive", "to grasp; to perceive; to understand (a meaning, a situation)",
                         "to capture (a feature, someone's heart, a likeness)",
                         "to pick up (on radar, a camera)"],
    ("遭う", "あう"): ["Godan verb, intransitive",
                     "to meet with (an accident, misfortune); to encounter; to experience (something bad)"],
    ("暖める", "あたためる"): ["Ichidan verb, transitive", "to warm (a room, the air); to heat"],
    ("現す", "あらわす"): ["Godan verb, transitive", "to show; to reveal (oneself, one's true nature)",
                         "to appear; to come into view"],
    ("産む", "うむ"): ["Godan verb, transitive", "to give birth to; to bear (a child)", "to lay (eggs)"],
    ("納める", "おさめる"): ["Ichidan verb, transitive", "to pay (taxes, fees); to deliver; to supply (goods)",
                         "to put away; to store; to offer (to a shrine)"],
    ("納まる", "おさまる"): ["Godan verb, intransitive", "to be paid; to be delivered",
                         "to fit into; to settle into (a place, a position)"],
    ("下りる", "おりる"): ["Ichidan verb, intransitive", "to go down (stairs, a slope); to come down",
                         "to be granted (a permit, a payment)",
                         "to come down; to close (a curtain, a shutter)"],
    ("固い", "かたい"): ["i-adjective", "hard; firm; solid (not easily changed or broken)",
                       "tight (a knot, a lid)", "firm (a resolve, a promise)"],
    ("堅い", "かたい"): ["i-adjective", "solid; strong (a structure, wood)",
                       "steady; reliable; serious; strait-laced (a person, a job)",
                       "certain (a win)"],
    ("捜す", "さがす"): ["Godan verb, transitive",
                       "to search for; to look for (something lost, a missing person, a suspect)"],
    ("絶つ", "たつ"): ["Godan verb, transitive", "to sever; to cut off (ties, contact)",
                     "to end (one's life); to wipe out"],
    ("造る", "つくる"): ["Godan verb, transitive", "to build; to construct (ships, buildings; on a large scale)",
                       "to brew (sake); to manufacture"],
    ("登る", "のぼる"): ["Godan verb, intransitive", "to climb (a mountain, a tree, stairs)"],
    ("昇る", "のぼる"): ["Godan verb, intransitive", "to rise (the sun, the moon, smoke)",
                       "to be promoted; to ascend (to a rank)"],
    ("量る", "はかる"): ["Godan verb, transitive", "to weigh; to measure (volume)",
                       "to guess; to surmise (someone's feelings)"],
    ("速い", "はやい"): ["i-adjective", "fast; quick; rapid (speed)"],
    ("貼る", "はる"): ["Godan verb, transitive", "to stick; to paste; to affix (a stamp, a poster, a label)"],
    ("殖える", "ふえる"): ["Ichidan verb, intransitive",
                        "to multiply; to breed (living things); to grow (savings, assets)"],
    ("延びる", "のびる"): ["Ichidan verb, intransitive", "to be extended; to lengthen (in time or distance)",
                         "to be postponed; to be delayed"],
    ("延ばす", "のばす"): ["Godan verb, transitive", "to extend; to prolong (a stay, a deadline)",
                         "to postpone; to put off"],
    ("載せる", "のせる"): ["Ichidan verb, transitive", "to place on; to load (cargo)",
                         "to publish; to print (in a newspaper or magazine); to post"],
    ("超える", "こえる"): ["Ichidan verb, intransitive",
                         "to exceed; to go beyond (a limit, a number, a standard); to surpass"],
    ("在る", "ある"): ["Godan verb, intransitive", "to be (located); to exist; to be situated (somewhere)",
                     "to be in (a position, a state)"],
    ("外", "ほか"): ["noun", "outside (of a given range); other than; besides",
                    "(with negative) nothing but; no choice but (…するほか(は)ない)"],
    ("眼", "め"): ["noun", "eye; eyeball (as an organ)", "an eye for (something); insight; discernment"],
    ("遣う", "つかう"): ["Godan verb, transitive",
                       "to use with care; to be mindful of (気を遣う: to be considerate, to worry about others)",
                       "to spend (money, time); to use (honorific language: 敬語を遣う)"],
    ("請ける", "うける"): ["Ichidan verb, transitive", "to undertake; to contract to do (work)",
                         "to redeem (a pawned item)"],
    ("交じる", "まじる"): ["Godan verb, intransitive",
                         "to mingle; to be mixed in (while staying distinguishable: 白髪が交じる, 子供に交じって遊ぶ)"],
    # Kind 1
    ("尤も", "もっとも"): ["na-adjective, conjunction", "reasonable; natural; quite right",
                        "(conjunction) however; though; but then"],
    ("脚", "あし"): ["noun", "leg (esp. the whole leg); leg (of furniture)", "pier (of a bridge)"],
    ("空ける", "あける"): ["Ichidan verb, transitive", "to empty; to vacate; to clear out",
                         "to make space; to leave a gap (a line, time)", "to be away from (home)"],
    ("画", "が"): ["noun, suffix", "picture; painting; drawing (e.g. 日本画, 映画, 漫画)"],
    ("首席", "しゅせき"): ["noun", "top seat; head", "top of the class (e.g. 首席で卒業する)"],
    ("古事", "こじ"): ["noun", "ancient matters; old events (as in 古事記)"],
    ("豪", "ごう"): ["noun, prefix", "strength; might; greatness", "(abbreviation) Australia"],
    ("跳び", "とび"): ["noun", "jump; jumping (e.g. 縄跳び, 走り高跳び)"],
    ("しこり", "しこり"): ["noun", "lump; stiffness (in muscles)",
                        "lingering ill feeling; bad aftertaste (between people)"],
    ("修得", "しゅうとく"): ["noun, する verb, transitive", "learning; completing (a course); earning (credits)"],
    ("主旨", "しゅし"): ["noun", "main point; gist; purpose (of a text or an argument)"],
    ("直観", "ちょっかん"): ["noun, する verb, transitive", "intuition; direct perception (philosophy)"],
    ("公聴", "こうちょう"): ["noun", "public hearing (e.g. 公聴会)"],
    ("基", "もと"): ["noun", "basis; foundation; base (on which something is founded)"],
    ("素", "もと"): ["noun", "element; ingredient; source material", "(soup) base; mix"],
    ("街", "まち"): ["noun", "street; downtown; shopping district; city streets"],
    ("初め", "はじめ"): ["noun", "the first time; the beginning (in time)", "early (part of a period)"],
    ("明ける", "あける"): ["Ichidan verb, intransitive", "to dawn; to grow light",
                         "to end; to be over (e.g. 梅雨が明ける, 年が明ける)"],
    ("空く", "あく"): ["Godan verb, intransitive",
                     "to become empty; to become vacant; to be free (a seat, a room, time)",
                     "to have a gap; to open up (a space)"],
    ("保障", "ほしょう"): ["noun, する verb, transitive",
                        "security; guarantee (of rights, safety); protection (e.g. 安全保障, 社会保障)"],
    ("弾", "たま"): ["noun", "bullet; shot; shell (ammunition)"],
    ("務め", "つとめ"): ["noun", "duty; obligation; role; responsibility"],
    ("器械", "きかい"): ["noun",
                       "instrument; apparatus; appliance (often small or hand-operated, e.g. gymnastics apparatus)"],
    ("独り", "ひとり"): ["noun, adverb", "alone; by oneself; single; unmarried", "(adverb) only; simply"],
    # Kind 2
    ("今日", "こんにち"): ["noun, adverb", "these days; nowadays; the present day"],
    ("汚す", "けがす"): ["Godan verb, transitive", "to disgrace; to dishonour; to defile; to desecrate"],
    ("避ける", "よける"): ["Ichidan verb, transitive",
                         "to dodge; to step aside; to get out of the way (physically)",
                         "to protect against (rain, frost)"],
    ("汁", "つゆ"): ["noun", "soup; broth (esp. for noodles)", "dipping sauce (e.g. for soba, tempura)"],
}
