exec(open("loans.py", encoding="utf-8").read().split("from jlpt_progress import jlpt_data")[0])
import time
from jlpt_progress import text_check
text = ("昨日は雨が降っていたので、家で本を読んでいました。友達に会うわけにはいかなかったけれど、"
        "電話で話すことができました。経済の発展に伴い、生活は便利になりつつある。"
        "彼は約束を守るに違いない。雨が降ったら、試合は中止になるそうです。")
res = {"kanji": {"known": set("昨日雨降家本読友達会話電")}, "grammar": {"known": {"te-iru", "node", "koto-ga-dekiru"}}}
t = time.time()
words = text_check.check_text(text, text_check.Knowledge({}))["words"]
k = text_check.check_kanji(text, res, words)
g = text_check.check_grammar(text, res)
print(f"{time.time() - t:.2f}s")
print("kanji:", k["unique"], "known", k["known"], [(r["char"], r["count"], r["level"], r["known"], r["words"][:2]) for r in sorted(k["rows"], key=lambda r: -r["count"])[:8]])
from jlpt_progress import grammar_data
for r in sorted(g["rows"], key=lambda r: (r["level"] or "N9")):
    p = grammar_data.data()[r["gid"]]
    s, sp = r["examples"][0]
    print(r["level"], p["pattern"], "|", p["meaning"][:40], "| known:", r["known"], "|", s[:sp[0][0]] + "【" + s[sp[0][0]:sp[0][1]] + "】" if sp else s)
