exec(open("loans.py", encoding="utf-8").read().split("lists = ")[0])
import os, tempfile
from jlpt_progress import overrides as ovm
lists = jlpt_data.build_lists({})
d = tempfile.mkdtemp(dir=os.path.dirname(os.path.abspath("loans.py")))
def fresh(found=()):
    o = ovm.Overrides(os.path.join(d, f"ov{len(os.listdir(d))}.json"))
    if found: o.add_found_many(found)
    return o
cfg = {}
o = fresh()
n = ovm.apply_loanword_default(lists, lambda: cfg, cfg.update, o)
print("fresh install: marked", n, "| flag", cfg.get("loanwords_default_done"), "| テレビ found:", o.is_found("テレビ", "てれび") or o.is_found("テレビ", "テレビ"))
print("second run:", ovm.apply_loanword_default(lists, lambda: cfg, cfg.update, fresh()))
cfg2 = {}
print("install with marks already:", ovm.apply_loanword_default(lists, lambda: cfg2, cfg2.update, fresh([("猫", "ねこ")])), "| flag", cfg2.get("loanwords_default_done"))
import shutil; shutil.rmtree(d)
