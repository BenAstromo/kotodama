exec(open("loans.py", encoding="utf-8").read().split("lists = ")[0])
words = {"fantasy / anime": [("魔法","まほう"),("勇者","ゆうしゃ"),("魔王","まおう"),("剣","けん"),("騎士","きし"),("呪い","のろい"),("冒険","ぼうけん"),("貴様","きさま"),("忍者","にんじゃ"),("妖怪","ようかい"),("姫","ひめ"),("覚醒","かくせい")],
         "spoken / casual": [("すごい","すごい"),("ちゃんと","ちゃんと"),("やばい","やばい"),("マジ","まじ"),("めっちゃ","めっちゃ"),("可愛い","かわいい"),("美味しい","おいしい"),("うるさい","うるさい"),("先輩","せんぱい"),("お前","おまえ"),("ずるい","ずるい"),("怖い","こわい")],
         "newer / net / games": [("スマホ","すまほ"),("ネタバレ","ねたばれ"),("推し","おし"),("ガチャ","がちゃ"),("配信","はいしん"),("ログイン","ろぐいん"),("ボス","ぼす"),("レベル","れべる")],
         "names / excluded": [("東京","とうきょう"),("田中","たなか"),("ナルト","なると")]}
for group, ws in words.items():
    out = []
    for d, r in ws:
        rk = freq_data.word_rank(d, r, jlpt_data.alt_forms(d, r))
        ri = freq_data.word_rank_info(d, r, jlpt_data.alt_forms(d, r))
        out.append(f"{d} {('#%s' % format(rk, ',')) if rk else ('~#%s' % format(ri[0], ',') if ri else 'not ranked')}")
    print(group + ": " + " · ".join(out))
