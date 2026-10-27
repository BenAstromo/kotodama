"""User files: an unreadable file is kept (backed up) before it's replaced;
overrides are saved atomically (a crash mid-save keeps the old file)."""
import glob, json, os
import stubenv as E
import mkcol
E.mw.col = mkcol.Col({"V": ["Word"]}, ["Main"], [])
ov = E.load("overrides")
hi = E.load("history")
go = E.load("goal")
nk = E.load("nakama")
uf = os.path.join(E.ADDON, "user_files")
BROKEN = '{"found": ["食べる\tたべる", "水\tみず"'          # truncated mid-write

def backups(name):
    return glob.glob(os.path.join(uf, name + ".unreadable-*"))

# 1. overrides: unreadable → backed up once, then replaced on the next save
p = ov._PATH
open(p, "w", encoding="utf-8").write(BROKEN)
o = ov.Overrides()
o2 = ov.Overrides()                           # loaded again: no second copy
E.check("unreadable overrides.json backed up", len(backups("overrides.json")) == 1)
E.check("backup holds the original bytes",
        backups("overrides.json") and open(backups("overrides.json")[0], encoding="utf-8").read() == BROKEN)
o.toggle_found("猫", "ねこ")
E.check("then saved fresh", json.load(open(p, encoding="utf-8"))["found"] == ["猫\tねこ"])
E.check("still one backup", len(backups("overrides.json")) == 1)

# 2. atomic save: a failure mid-write leaves the previous file whole
real_dump = json.dump
def failing_dump(obj, f, **k):
    f.write('{"found": ["half')
    raise OSError("disk full")
json.dump = failing_dump
o.toggle_found("犬", "いぬ")
json.dump = real_dump
E.check("crash mid-save keeps the old overrides.json", json.load(open(p, encoding="utf-8"))["found"] == ["猫\tねこ"])
E.check("no temp file left behind", not glob.glob(p + ".tmp*"))

# 3. history / goal days / nakama: unreadable → backed up
for path, load, name in ((hi._PATH, hi._load, "history.json"),
                         (go._DAYS_PATH, go._load_days if hasattr(go, "_load_days") else None, os.path.basename(go._DAYS_PATH)),
                         (nk._PATH, lambda: (setattr(nk, "_state", None), nk.state()), "nakama.json")):
    open(path, "w", encoding="utf-8").write('{"x": [1, 2')
    if load is None:
        print("  (no loader found for", name, ")")
        continue
    load()
    E.check(f"unreadable {name} backed up", len(backups(name)) == 1)
# a missing file is normal: no backup
os.remove(hi._PATH)
hi._load()
E.check("missing history.json: nothing backed up", len(backups("history.json")) == 1)
E.finish()
