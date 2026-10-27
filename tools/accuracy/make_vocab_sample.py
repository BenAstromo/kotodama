"""Draft a word-split sample for tools/vocab_eval.py (2026-10-17).

Picks N unseen Tatoeba sentences of 18–60 characters (longer than the
grammar samples, closer to the texts the Text Check gets), and writes a
draft file: each sentence with the parser's counted words and MeCab's
content-word lemmas next to it. The draft is then checked by hand into
tools/vocab_cases.json (the gold words).

    python -I -X utf8 tools/accuracy/make_vocab_sample.py <jpn_sentences.tsv> <seed> <N> <out.txt>
"""
import json, os, random, sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.join(os.environ["LOCALAPPDATA"], "jlpt_devtools", "pylib"))
from fugashi import Tagger  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
exec(open(os.path.join(TOOLS, "gemini_grammar_review", "verdicts", "gem_head.py"), encoding="utf-8").read())
HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
sp = __import__("jlpt_progress.sentence_parser", fromlist=["x"])

tsv, seed, n, out_path = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
seen = set()
for name in ("grammar_cases.json", "vocab_cases.json"):
    p = os.path.join(TOOLS, name)
    if os.path.exists(p):
        for c in json.load(open(p, encoding="utf-8")):
            seen.add(c["text"] if isinstance(c, dict) else c[0])

texts = []
with open(tsv, encoding="utf-8") as f:
    for line in f:
        parts = line.rstrip("\n").split("\t")
        if len(parts) >= 3:
            t = sp.clean(parts[2])
            if 18 <= len(t) <= 60 and t not in seen:
                texts.append(t)
texts = sorted(set(texts))
random.Random(seed).shuffle(texts)

tagger = Tagger()
CONTENT = {"名詞", "動詞", "形容詞", "副詞", "形状詞", "代名詞", "連体詞", "接尾辞", "接頭辞", "感動詞"}
with open(out_path, "w", encoding="utf-8") as f:
    for i, t in enumerate(texts[:n]):
        ours = []
        for tok in sp.tokens(t):
            if tok[1] == "word" and tok[0] not in sp.FUNCTION_TOKENS:
                ours.append(f"{tok[2]}:{tok[3]}" if tok[2] != tok[0] or True else tok[0])
            elif tok[1] in ("unk", "lone"):
                ours.append(f"?{tok[0]}")
        mec = [w.feature.lemma or w.surface for w in tagger(t) if w.feature.pos1 in CONTENT]
        f.write(f"#{i}\t{t}\n  P: {' '.join(ours)}\n  M: {' '.join(mec)}\n")
print("wrote", min(n, len(texts)), "of", len(texts))
