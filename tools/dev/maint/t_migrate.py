"""migrate.import_old_copy in temp folders: a shared copy (jlpt_progress)
next to an AnkiWeb copy (numbered folder)."""
import importlib.util, json, os, shutil, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8")
spec = importlib.util.spec_from_file_location(
    "migrate", r"C:\Users\benne\AppData\Roaming\Anki2\addons21\jlpt_progress\migrate.py")
mg = importlib.util.module_from_spec(spec); spec.loader.exec_module(mg)
R = []
def check(n, c): R.append(c); print(("PASS " if c else "FAIL ") + n)

class Mgr:
    def __init__(self, cfgs): self.cfgs, self.toggled = cfgs, []
    def getConfig(self, name): return dict(self.cfgs.get(name) or {})
    def writeConfig(self, name, c): self.cfgs[name] = c
    def toggleEnabled(self, name, enable=None): self.toggled.append((name, enable))

base = tempfile.mkdtemp(prefix="kt_mig_ü_")
old = os.path.join(base, "jlpt_progress"); new = os.path.join(base, "1234567890")
os.makedirs(os.path.join(old, "user_files", "sub")); os.makedirs(os.path.join(new, "user_files"))
w = lambda p, t: open(p, "w", encoding="utf-8").write(t)
w(os.path.join(old, "user_files", "history.json"), '{"old": 1}')
w(os.path.join(old, "user_files", "overrides.json"), '{"old": 2}')
w(os.path.join(old, "user_files", "sub", "deep.txt"), "x")
w(os.path.join(new, "user_files", "overrides.json"), '{"new": 9}')       # already here: keep
w(os.path.join(old, "meta.json"), json.dumps({"config": {"deck_name": "Old deck"}}))
m = Mgr({"1234567890": {"deck_name": "", "rain": True}})
out = mg.import_old_copy(new, m)
print("  ->", out)
check("files copied (2 new, 1 kept)", out and out["files"] == 2)
check("existing file never overwritten", json.load(open(os.path.join(new, "user_files", "overrides.json")))["new"] == 9)
check("nested file copied", os.path.exists(os.path.join(new, "user_files", "sub", "deep.txt")))
check("settings brought over, own keys kept", m.cfgs["1234567890"] == {"deck_name": "Old deck", "rain": True})
check("old copy disabled", ("jlpt_progress", False) in m.toggled)
check("marker written", os.path.exists(os.path.join(new, "user_files", mg.MARKER)))
w(os.path.join(old, "user_files", "later.json"), "{}")
check("runs once (marker)", mg.import_old_copy(new, m) is None)
check("old folder itself does nothing", mg.import_old_copy(old, m) is None)
# a new copy that already has its own settings keeps them
new2 = os.path.join(base, "999"); os.makedirs(new2)
w(os.path.join(new2, "meta.json"), json.dumps({"config": {"deck_name": "Mine"}}))
m2 = Mgr({"999": {"deck_name": "Mine"}})
out2 = mg.import_old_copy(new2, m2)
check("own settings not replaced", out2 and not out2["config"] and m2.cfgs["999"]["deck_name"] == "Mine")
# no old copy: nothing happens, no marker
base2 = tempfile.mkdtemp(); n3 = os.path.join(base2, "555"); os.makedirs(n3)
check("no old copy: nothing", mg.import_old_copy(n3, Mgr({})) is None and not os.path.exists(os.path.join(n3, "user_files")))
# old copy without user_files / meta.json
base3 = tempfile.mkdtemp(); os.makedirs(os.path.join(base3, "jlpt_progress")); n4 = os.path.join(base3, "777"); os.makedirs(n4)
o4 = mg.import_old_copy(n4, Mgr({}))
check("bare old copy: disables it, 0 files, marker", o4 == {"files": 0, "config": False, "disabled": True})
for b in (base, base2, base3): shutil.rmtree(b, ignore_errors=True)
print("ALL PASS" if all(R) else "SOME FAILED")
