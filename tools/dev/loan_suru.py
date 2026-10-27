exec(open("loans.py", encoding="utf-8").read().split("lists = ")[0])
from jlpt_progress import card_state
for d in ("チェックする", "コピーする", "チェック", "サラリーマン", "勉強する"):
    print(d, jlpt_data.is_english_loanword(d, d if d != "勉強する" else "べんきょうする"))
print("rows:", card_state._found_rank("チェックする", "チェックする"), freq_data.word_rank("チェック", "チェック"))
res = {"N4": {"known_words": [("チェックする", "チェックする", None)]},
       "frequency": {"found_ranks": {freq_data.word_rank("チェック", "チェック") - 1},
                     "entries": [(i + 1, r[0], r[1], None) for i, r in enumerate(freq_data.load())]}}
print("marked both チェックする and チェック → words:", card_state.found_words_in(res), "| parts:", card_state.found_parts(res))
