"""Nakama keep-your-code + collection restore, and the loyalty badge's
collection backup, against the LOCAL wrangler server (port 8799)."""
import datetime, json, os, sys, urllib.request
sys.stdout.reconfigure(encoding="utf-8")
ADDON = r"C:\Users\benne\AppData\Roaming\Anki2\addons21\jlpt_progress"
SCR = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.join(ADDON, "tools")
exec(open(os.path.join(TOOLS, "gemini_grammar_review", "verdicts", "gem_head.py"), encoding="utf-8").read())
import aqt
nk = __import__("jlpt_progress.nakama", fromlist=["x"])
ly = __import__("jlpt_progress.loyalty", fromlist=["x"])
hist = __import__("jlpt_progress.history", fromlist=["x"])
pkg = sys.modules["jlpt_progress"]

class Col:
    def __init__(self): self.conf = {}
    def get_config(self, k, default=None): return json.loads(json.dumps(self.conf.get(k, default)))
    def set_config(self, k, v): self.conf[k] = json.loads(json.dumps(v))

class MW: pass
mw = MW(); mw.col = Col(); mw.taskman = None
aqt.mw = mw; nk.mw = mw
nk.SERVER = "http://127.0.0.1:8799"
LOCAL = os.path.join(SCR, "nakama_test.json")
nk._PATH = LOCAL
results = []
def check(name, ok, extra=""):
    results.append(ok); print(("PASS " if ok else "FAIL ") + name, extra)

def reset_local():
    if os.path.exists(LOCAL): os.remove(LOCAL)
    nk._state = None

def call(fn, *a):
    out = {}
    fn(*a, lambda *r: out.setdefault("r", r))
    return out["r"]

def server_get(ids):
    with urllib.request.urlopen(f"{nk.SERVER}/profiles?ids={','.join(ids)}") as r:
        return {p["id"]: p for p in json.load(r)["profiles"]}

reset_local()
s = nk.state(); s["mine"] = {"v": 1, "rank": 1234, "loyal": 3}; nk.save()
ok, err = call(nk.join, "Ben")
A = nk.state().get("id")
check("join creates a code", ok and bool(A), err or "")
check("collection mirrors the login", mw.col.conf.get(nk.COL_KEY, {}).get("id") == A and mw.col.conf[nk.COL_KEY]["active"])
# a friend
req = urllib.request.Request(nk.SERVER + "/profile", data=json.dumps({"name": "Friend", "data": {"v": 1, "rank": 5}}).encode(),
                             method="POST", headers={"content-type": "application/json", "user-agent": "Kotodama-Anki"})
B = json.load(urllib.request.urlopen(req))["id"]
nk.add_friend(B)
check("friends mirrored", B in mw.col.conf[nk.COL_KEY]["friends"])
# leave keeps the code
ok, err = call(nk.leave)
check("leave ok", ok, err or "")
check("left profile hidden from friends", A not in server_get([A, B]) and B in server_get([A, B]))
check("code parked locally", nk.parked_code() == A and not nk.joined())
check("collection says left", mw.col.conf[nk.COL_KEY]["active"] is False and mw.col.conf[nk.COL_KEY]["id"] == A)
# rejoin at once (no once-a-minute wait), same code, new name
ok, err = call(nk.join, "Ben2")
check("rejoin gets the same code", ok and nk.state().get("id") == A, err or "")
check("rejoined profile listed with the new name", server_get([A]).get(A, {}).get("name") == "Ben2")
# reinstall: local file gone, collection kept
reset_local()
check("reinstall restores the login + friends", nk.state().get("id") == A and nk.joined() and B in nk.state()["friends"])
# new computer while left
call(nk.leave)
reset_local()
check("new PC while left: parked code restored", nk.parked_code() == A and not nk.joined())
nk.state()["mine"] = {"v": 1, "rank": 1}
ok, err = call(nk.join, "Ben3")
check("…and joining there reuses it", ok and nk.state().get("id") == A, err or "")
# a key that doesn't match: falls back to a new code
call(nk.leave)
nk.state()["parked"]["key"] = "0" * 64
ok, err = call(nk.join, "Ben4")
check("wrong key → a new code instead of an error", ok and nk.state().get("id") not in (None, A), err or "")
# old server without /leave → DELETE, no parked code
orig = nk._request
def old_server(method, path, body=None):
    if path.endswith("/leave"):
        raise nk.NakamaError("Not found")
    return orig(method, path, body)
nk._request = old_server
C = nk.state()["id"]
ok, err = call(nk.leave)
nk._request = orig
check("old server: leave deletes, nothing parked", ok and nk.parked_code() is None and C not in server_get([C]), err or "")
# an existing user upgrading (no collection copy yet): the first save mirrors it
mw.col = Col(); nk.mw = mw; reset_local()
s = nk.state(); s["id"], s["key"] = "ABCDEFGH", "1" * 64; nk.save()
check("upgrade: existing login copied to the collection", mw.col.conf.get(nk.COL_KEY, {}).get("id") == "ABCDEFGH")

# ── loyalty ──
real_today = hist.today
hist.today = lambda: datetime.date(2026, 11, 5)
ly._CACHE["key"] = None
mw.col = Col()
m = ly.months_with_kotodama()
check("owner's history: October counts in November", m == 1, f"months={m}")
check("months saved in the collection", "2026-10" in mw.col.conf.get(ly.COL_KEY, {}).get("months", []))
# new computer: no history, collection has October
real_path = hist._PATH
hist._PATH = os.path.join(SCR, "no_history.json")
ly._CACHE["key"] = None
check("new PC: badge restored from the collection", ly.months_with_kotodama() == 1)
# this PC adds December 2026: months merge (Oct + Dec), counted in January
with open(hist._PATH, "w", encoding="utf-8") as f:
    json.dump({"version": 1, "decks": {"D": {"days": {"2026-12-03": {}}}}}, f)
hist.today = lambda: datetime.date(2027, 1, 2)
ly._CACHE["key"] = None
m = ly.months_with_kotodama()
check("months from both PCs add up", m == 2 and mw.col.conf[ly.COL_KEY]["months"] == ["2026-10", "2026-12"], f"months={m}")
os.remove(hist._PATH); hist._PATH = real_path; hist.today = real_today
# Sun Diamond flag: config → collection, then collection alone
pkg._cfg = lambda: {"amaterasu_reached": "2027-01-01"}
check("Amaterasu flag copied to the collection", ly.sun_reached() and mw.col.conf[ly.COL_KEY].get("sun") == "2027-01-01")
pkg._cfg = lambda: {}
check("reinstall: Amaterasu flag restored from the collection", ly.sun_reached())
reset_local()
print(f"\n{sum(results)}/{len(results)} passed")
