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


# Community-list words (jamsinclair/open-anki-jlpt-decks, elzup/jlpt-word-list;
# flag "community"): 211 added 2026-10-08, all removed 2026-11-03 (owner):
# the bars are Waller's lists only (OpenJLPT + the Waller words it drops).
# Most carried only old-test tags, so their levels were the list makers'
# guesses, and two were misread rows (塩辛, 絞める). In git history.
COMMUNITY_ADDITIONS = {}
for _l, _words in COMMUNITY_ADDITIONS.items():
    ADDITIONS.setdefault(_l, []).extend(_words)

# Our own additions (words on no list, levels we chose; flag "ours"): the
# kanji-pair batch of 2026-10-14 and the Word Addition Project (2026-10-28,
# 1,742 words, trimmed to 1,092 on 2026-11-02) were all removed on
# 2026-11-03 (owner): the bars are Waller's lists plus the community words
# only, so every word has an outside source. Common words beyond the lists
# still count in the rank, the Frequency Check and the Off-list tab. The
# removed list is in git history (tools/missing_words/word_additions.json).
OUR_ADDITIONS = {}
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
        f.write("#        loan-xxx = loanword from another language (ISO 639-2 code)\n\n")
        for w, r, alts, flags, alt_reads in rows:
            cols = [w, r, "|".join(alts), ",".join(flags), "|".join(alt_reads)]
            while cols[-1] == "":
                cols.pop()
            f.write("\t".join(cols) + "\n")
    print(lvl, len(rows))
