import csv, pickle, collections, re, sys
csv.field_size_limit(10**9)
J=pickle.load(open("data/jmdict.pkl","rb"))
byk=collections.defaultdict(list); byr=collections.defaultdict(list)
for s,e in J.items():
    for k in e["keb"]: byk[k].append(s)
    for r in e["reb"]: byr[r].append(s)
k2h=lambda s:"".join(chr(ord(c)-0x60) if "\u30A1"<=c<="\u30F6" else c for c in s)
KEEP=("名詞-普通名詞","動詞","形容詞","形状詞-一般","形状詞-タリ","副詞","連体詞","接続詞","感動詞-一般","代名詞")
# The laws register (OL) is excluded: ~1% of the corpus, but it repeats legal
# jargon (当該, 条, 項, 規定 ...) so heavily that it distorts the ranking, and
# statutes never appear on the JLPT.
EXCLUDED_REGISTERS=("OL",)
# Lemmas dropped by hand: ウ and ア are list bullets (ア・イ・ウ …) that UniDic
# counts as words; ウ mapped to 鵜 (cormorant). Removed at the owner's
# request, 2026-10-09.
DROP_LEMMAS={"ウ","ア"}
# BCCWJ (UniDic) part of speech → words in JMdict's POS text that fit it.
POS_FITS={"感動詞":("interjection",),"副詞":("adverb",),"代名詞":("pronoun",),
          "接続詞":("conjunction",),"連体詞":("pre-noun adjectival","acting prenominally"),
          "動詞":("verb",),"形容詞":("adjective (keiyoushi)",),
          "形状詞":("adjectival nouns","'taru' adjective"),"名詞":("noun",)}
def _pos_fits(bpos, jpos):
    for head, words in POS_FITS.items():
        if bpos.startswith(head):
            return any(w in jpos for w in words)
    return False
# Which BCCWJ words stay apart though JMdict shares their entry (町 / 街):
# freq_splits.py in the add-on folder (sys.argv[1]), shared with freq_data.
import importlib.util as _ilu
_spec=_ilu.spec_from_file_location("freq_splits", sys.argv[1]+"/freq_splits.py")
_fs=_ilu.module_from_spec(_spec); _spec.loader.exec_module(_fs)
SPLIT={}; SPLIT_GROUP={}
for _g in _fs.KIND1_SPLITS:
    for _lem,_disp in _g.items():
        SPLIT[_lem]=_disp
        SPLIT_GROUP[_lem]={x for l,d in _g.items() if l!=_lem for x in (l,d)}
KANJI=r"[一-鿿㐀-䶿々〆]"
# UniDic files the じる verbs under their classical ずる form (感ずる): count
# them as the modern じる word, keeping ずる as a spelling (owner 2026-10-12).
ZURU={}
agg=collections.OrderedDict()
total_tokens=0
with open("data/BCCWJ_frequencylist_suw_ver1_0.tsv",encoding="utf-8") as f:
    for row in csv.DictReader(f, delimiter="\t"):
        freq=int(row["frequency"])-sum(int(row[r+"_frequency"] or 0) for r in EXCLUDED_REGISTERS)
        total_tokens+=freq
        pos=row["pos"]
        if not pos.startswith(KEEP): continue
        lemma=row["lemma"]; rd=k2h(row["lForm"])
        if lemma in DROP_LEMMAS: continue
        if not lemma or not rd or not re.fullmatch(r"[぀-ヿ一-鿿㐀-䶿々〆]+", lemma): continue
        if lemma.endswith("ずる") and rd.endswith("ずる") and lemma[:-2]+"じる" in byk:
            ZURU[lemma[:-2]+"じる"]=lemma
            lemma, rd = lemma[:-2]+"じる", rd[:-2]+"じる"
        k=(lemma,rd)
        if k not in agg: agg[k]=[0,0.0,pos]   # pos of its most frequent row
        agg[k][0]+=freq
for v in agg.values():
    v[1]=v[0]/total_tokens*1e6   # per million words of the remaining corpus
items=sorted(agg.items(), key=lambda kv:-kv[1][0])
out=[]; unmapped=0; UNM=[]
for (lemma,rd),(fr,pmw,pos) in items:
    cands=[s for s in set(byk.get(lemma,[])+byr.get(lemma,[])) if rd in [k2h(r) for r in J[s]["reb"]]]
    forms=[lemma]; display=lemma
    is_kana = not re.search(r"[一-鿿㐀-䶿々〆]", lemma)
    if cands:
        # One entry only: prefer lemma as a kanji spelling, then an entry whose
        # PRIMARY reading is this word (なあ particle, not 七 which merely lists なあ).
        def _rpos(s):
            rs=[k2h(r) for r in J[s]["reb"]]
            return rs.index(rd) if rd in rs else 99
        # A kana lemma also prefers an entry of its own part of speech, so the
        # interjection おっと ("oops") isn't 夫 おっと, はは ("haha") isn't 母,
        # and ばん ("bang") isn't 晩 (owner 2026-10-10).
        def _pos_miss(s):
            # Hiragana only: for katakana it reshuffled loanword flags
            # (バイ "bye" → 貝, シャー → Persian shah).
            if not re.fullmatch(r"[ぁ-ゖー]+", lemma): return 0
            return 0 if any(_pos_fits(pos, p) for p in J[s].get("pos", ())) else 1
        # Then one normally written in kana (the sound word かん "clang", not 間).
        def _kanji_word(s):
            if not re.fullmatch(r"[ぁ-ゖー]+", lemma): return 0
            e=J[s]
            return 0 if not e["keb"] or (e["misc"] and "word usually written using kana alone" in (e["misc"][0] or [])) else 1
        cands.sort(key=lambda s:(0 if lemma in J[s]["keb"] else 1, _pos_miss(s), _kanji_word(s), _rpos(s), s))
        e=J[cands[0]]
        uk = bool(e["misc"]) and "word usually written using kana alone" in (e["misc"][0] or [])
        if is_kana or uk or not e["keb"]:
            display = lemma if is_kana else rd
        else:
            display = e["keb"][0]
        # No entry of its part of speech (the sound adverbs くる, びく …): the
        # row keeps only its own kana, rather than borrowing 繰る or 比丘.
        # A kana-only entry is still this word (ちっ|チッ, わっ|ワッ).
        if not _pos_miss(cands[0]) or not e["keb"]:
            for x in e["keb"]+e["reb"]:
                if x not in forms: forms.append(x)
    else:
        unmapped+=1
        UNM.append((len(out)+1,lemma,rd))
        continue   # word fragments / legal abbreviations with no dictionary entry
    if display not in forms: forms.insert(0,display)
    if lemma in ZURU and ZURU[lemma] not in forms: forms.append(ZURU[lemma])
    if lemma in SPLIT:
        # Its own tile (町 apart from 街): shown as its display, keeping only
        # spellings that share a kanji with it and kana of its own reading,
        # so the other group members' cards don't match it.
        display=SPLIT[lemma]
        own=set(re.findall(KANJI, display+lemma)); others=SPLIT_GROUP[lemma]
        own_rd=lemma if is_kana else rd
        forms=[display]+[x for x in forms if x!=display and x not in others and (
            bool(set(re.findall(KANJI,x)) & own) if re.search(KANJI,x) else k2h(x)==own_rd)]
        if lemma not in forms: forms.append(lemma)
    # Loanword flag for katakana words, same rules as build_jlpt.py (used by
    # the "Mark English Loanwords as Found" button).
    flag=""
    if re.fullmatch(r"[゠-ヿー・]+", display):
        nonen=[x for x in e["langs"] if x!="eng"]
        abbr=any("abbreviation" in m for m in e["misc"])
        flag=("wasei" if e["wasei"] else "loan-"+nonen[0] if nonen
              else "abbr" if abbr else "eng")
    out.append((display, lemma if is_kana else rd, pmw, forms, flag))
    if len(out)>=20000: break
print("unmapped in top20k:",unmapped, file=sys.stderr)
open("data/unmapped.txt","w",encoding="utf-8").write("\n".join(f"{a}\t{b}\t{c}" for a,b,c in UNM))
A=sys.argv[1]
with open(A+"/freq_bccwj.txt","w",encoding="utf-8",newline="\n") as f:
    f.write("# Top 20,000 content words in the BCCWJ (Balanced Corpus of Contemporary Written Japanese)\n")
    f.write("# Source: NINJAL, BCCWJ short-unit-word frequency list v1.0 (CC BY-NC-ND 3.0).\n")
    f.write("#   Laws register excluded (legal jargon such as 当該/条/項 skewed the ranking).\n")
    f.write("#   Particles, auxiliaries, affixes, numerals, proper nouns and fragments absent from JMdict removed;\n")
    f.write("#   spellings mapped via JMdict (EDRDG, CC BY-SA 4.0).\n")
    f.write("# Format: display<TAB>reading<TAB>per-million-words<TAB>all spellings (|-separated)<TAB>loanword flag; line order = rank\n")
    f.write("# Flags (katakana words, from JMdict): eng = English loanword, wasei = wasei-eigo,\n")
    f.write("#   abbr = abbreviated loanword, loan-xxx = loanword from another language (ISO 639-2)\n\n")
    for d,r,p,forms,fl in out: f.write(f"{d}\t{r}\t{p:.2f}\t{'|'.join(forms)}\t{fl}\n")
print(len(out))
