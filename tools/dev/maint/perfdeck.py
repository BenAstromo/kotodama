"""The mid-size synthetic deck of t_perf.py / t_prof.py (2026-11-10):
~3,000 JLPT words (most N5, few N1) + 700 frequency words + 200 sentence
cards, with a realistic mix of card states. install(E) puts it in place."""
import os, random
import mkcol


def install(E) -> int:
    def _list(lvl):
        path = os.path.join(E.ADDON, f"jlpt_{lvl.lower()}.txt")
        out = []
        for line in open(path, encoding="utf-8"):
            if line.startswith("#") or not line.strip():
                continue
            p = line.rstrip("\n").split("\t")
            out.append((p[0], p[1] if len(p) > 1 else ""))
        return out


    rnd = random.Random(7)
    STATES = [(0, 0, 0)] * 15 + [(1, 1, 0)] * 5 + [(2, 2, 7)] * 40 + [(2, 2, 60)] * 37 + [(2, -1, 30)] * 3
    SENTS = ["私は毎日学校に行きます。", "昨日は雨が降ったので、家で本を読みました。", "水を飲みたいです。",
             "彼は先生に褒められたそうだ。", "明日までに宿題を終わらせなければならない。",
             "日本に行ったことがありますか。", "忙しいにもかかわらず、手伝ってくれた。",
             "電車が遅れたせいで、会議に間に合わなかった。", "食べれば食べるほど太る。",
             "この本は読みやすいと思います。"]
    notes = []
    for lvl, share in (("N5", .92), ("N4", .85), ("N3", .5), ("N2", .25), ("N1", .15)):
        for w, r in _list(lvl):
            if rnd.random() < share:
                notes.append(("Main", "Vocab", {"Word": w, "Reading": r,
                                                "Sentence": rnd.choice(SENTS)}, rnd.choice(STATES)))
    freq_words = []
    for i, line in enumerate(open(os.path.join(E.ADDON, "freq_bccwj.txt"), encoding="utf-8")):
        p = line.split("\t")
        if line.startswith("#") or len(p) < 2:
            continue
        freq_words.append((p[0], p[1]))
    for w, r in rnd.sample(freq_words[6000:20000], 700):
        notes.append(("Main", "Vocab", {"Word": w, "Reading": r, "Sentence": ""}, rnd.choice(STATES)))
    notes += [("Main", "SentOnly", {"Sentence": s}, (2, 2, 25)) for s in SENTS * 20]
    col = mkcol.Col({"Vocab": ["Word", "Reading", "Sentence"], "SentOnly": ["Sentence"]}, ["Main"], notes)
    E.mw.col = col
    E.CFG.update(deck_name="Main", field_mappings=[
        {"note_type": "Vocab", "field": "Word", "reading_field": "Reading", "sentence_field": "Sentence"},
        {"note_type": "SentOnly", "field": "", "reading_field": "", "sentence_field": "Sentence"}])
    return len(notes)
