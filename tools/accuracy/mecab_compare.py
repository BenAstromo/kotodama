"""Dev tool (2026-10-14): compare the add-on's sentence parser with MeCab
(fugashi + unidic-lite, installed outside the add-on in
%LOCALAPPDATA%\\jlpt_devtools\\pylib; never shipped) over Tatoeba, to list
likely parser misreads. MeCab cuts finer than our parser (食べ+まし+た vs
食べました), so a plain boundary diff is noise; two kinds of disagreement are
reported instead:

  CUT    our parser splits inside a word MeCab reads as one content word
         (飛び込んで → 飛び + 込 + ん; unknown characters inside a word):
         missing vocabulary or a failed conjugation.
  SWALLOW one of our words contains a MeCab boundary right before a
         particle (今日は read as こんにちは = 今日 + は).

    python -I -X utf8 tools/accuracy/mecab_compare.py <jpn_sentences.tsv> [max sentences]

Writes tools/accuracy/mecab_diff.txt: each group (MeCab word / our word)
with its count and up to 3 example sentences, most frequent first.
"""
import collections, os, sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.join(os.environ["LOCALAPPDATA"], "jlpt_devtools", "pylib"))
from fugashi import Tagger  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
exec(open(os.path.join(TOOLS, "gemini_grammar_review", "verdicts", "gem_head.py"), encoding="utf-8").read())
HERE = os.path.dirname(os.path.abspath(__file__))
sp = __import__("jlpt_progress.sentence_parser", fromlist=["x"])

CONTENT = {"名詞", "動詞", "形容詞", "副詞", "形状詞"}
PARTICLES = {"は", "が", "を", "に", "で", "と", "も", "の", "へ", "から", "まで", "より", "や"}
LIMIT = int(sys.argv[2]) if len(sys.argv) > 2 else 10 ** 9

tagger = Tagger()
cut = collections.defaultdict(list)       # MeCab word (lemma) → examples
swallow = collections.defaultdict(list)   # our word → examples
n = 0
with open(sys.argv[1], encoding="utf-8") as f:
    for line in f:
        parts = line.rstrip("\n").split("\t")
        if len(parts) < 3:
            continue
        text = sp.clean(parts[2])
        if not text:
            continue
        n += 1
        if n > LIMIT:
            break
        if n % 25000 == 0:
            print(f"  {n:,}", flush=True)
        # our tokens → boundary positions
        ours, pos = [], 0
        for t in sp.tokens(text):
            ours.append((pos, pos + len(t[0]), t))
            pos += len(t[0])
        our_cuts = {b for _a, b, _t in ours}
        # MeCab tokens with positions
        mec, pos = [], 0
        for w in tagger(text):
            s = w.surface
            i = text.find(s, pos)
            if i < 0:
                continue
            mec.append((i, i + len(s), w))
            pos = i + len(s)
        mec_starts = {a: w for a, _b, w in mec}
        # CUT: one of our boundaries strictly inside a MeCab content word
        for a, b, w in mec:
            if w.feature.pos1 in CONTENT and b - a >= 2 and any(a < c < b for c in our_cuts):
                key = f"{w.surface} ({w.feature.lemma}, {w.feature.pos1})"
                if len(cut[key]) < 50:
                    cut[key].append(text)
                else:
                    cut[key].append(None)
        # SWALLOW: a MeCab particle starts strictly inside one of our words
        for a, b, t in ours:
            if t[1] != "word":
                continue
            for c in range(a + 1, b):
                w = mec_starts.get(c)
                if w is not None and w.feature.pos1 == "助詞" and w.surface in PARTICLES:
                    key = f"{t[0]} (read as {t[2]})"
                    if len(swallow[key]) < 50:
                        swallow[key].append(text)
                    else:
                        swallow[key].append(None)
                    break

lines = [f"MeCab comparison over {min(n, LIMIT):,} Tatoeba sentences", ""]
for title, groups in (("CUT: our parser splits inside one MeCab word", cut),
                      ("SWALLOW: one of our words contains a particle", swallow)):
    lines.append("=" * 78)
    lines.append(f"{title} — {len(groups):,} distinct, {sum(len(v) for v in groups.values()):,} sentences")
    lines.append("=" * 78)
    for key, ex in sorted(groups.items(), key=lambda kv: -len(kv[1]))[:400]:
        shown = [e for e in ex if e][:3]
        lines.append(f"{len(ex):6,}  {key}")
        for e in shown:
            lines.append(f"          {e[:70]}")
    lines.append("")
open(os.path.join(HERE, "mecab_diff.txt"), "w", encoding="utf-8", newline="\n").write("\n".join(lines))
print("wrote mecab_diff.txt;", len(cut), "CUT groups,", len(swallow), "SWALLOW groups")
