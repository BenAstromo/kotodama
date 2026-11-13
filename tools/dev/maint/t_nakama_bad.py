"""Odd friend cards (guide item 9): profiles holding unexpected values (made
by hand against the server, or by a newer version) go through
nakama.clean_profile, the list row (_Row), the card image (render_profile)
and the whole Nakama tab without an error. Never talks to a server."""
import os, sys, io, traceback
os.environ["KOTODAMA_NAKAMA_URL"] = "http://127.0.0.1:9"
import stubenv as E
import mkcol
E.mw.col = mkcol.Col({"V": ["Word"]}, ["Main"], [])
nk = E.load("nakama")
nv = E.load("nakama_view")
sc = E.load("share_card")

BAD = [
    {"id": "AAAA2222", "name": "rank", "data": {"rank": "lots"}},
    {"id": "BBBB3333", "name": "week", "data": {"rank": 50, "week": "x", "month": [1]}},
    {"id": "CCCC4444", "name": "jlpt", "data": {"jlpt": "x", "freq": "y", "kanji": [1, 2], "grammar": {"All": "z"}}},
    {"id": "DDDD5555", "name": 12345, "data": "not a dict", "updated": "yesterday"},
    {"id": "EEEE6666", "name": "x" * 100, "data": {"rank": -5, "found": "3", "loyal": None,
                                                     "goal": 7, "sun": "yes", "future_key": {"a": 1}}},
    {"id": "FFFF7777", "name": "huge", "data": {"rank": 10 ** 12, "jlpt": {"N5": ["1", "x"], "N4": [3, 9]}}},
]
errs = []
for p in BAD:
    c = nk.clean_profile(p)
    for key in ("rank", "week", "kanji", "grammar"):
        try:
            nv._Row(dict(c), False, key)
        except Exception:
            errs.append(f"_Row {p['id']} {key}: " + traceback.format_exc())
    try:
        sc.render_profile(c, {"rank": 10})
    except Exception:
        errs.append(f"render {p['id']}: " + traceback.format_exc())
E.check("odd cards: every row and card image draws", not errs)
if errs:
    print("\n".join(errs)[:4000])
c = nk.clean_profile(BAD[4])
E.check("name capped at 32 characters", len(c["name"]) == 32)
E.check("negative rank → 0", c["data"]["rank"] == 0)
E.check("unknown keys kept", c["data"]["future_key"] == {"a": 1})
E.check("rank capped at 20,000", nk.clean_profile(BAD[5])["data"]["rank"] == 20_000)
E.check("bad pairs dropped, good ones kept", nk.clean_profile(BAD[5])["data"]["jlpt"] == {"N4": [3, 9]})
E.check("not a dict → {}", nk.clean_profile("x") == {})

# the whole tab with these friends in the cache (as an old version stored them)
s = nk.state()
s.update(id="ZZZZ9999", key="k" * 32, name="Me", mine={"rank": 5})
for p in BAD:
    s["friends"].append(p["id"])
    s["cache"][p["id"]] = p
s["cache"]["GGGG8888"] = None
s["friends"].append("GGGG8888")
ERRS = []
_real = sys.stderr
class Tee(io.TextIOBase):
    def write(self, t):
        if "Traceback" in t:
            ERRS.append(t)
        return _real.write(t)
sys.stderr = Tee()
sys.excepthook = lambda *a: ERRS.append("".join(traceback.format_exception(*a)))
tab = nv.NakamaTab()
tab.resize(800, 600); tab.show()
E.pump(1.5)
tab._fill_list()
for i in range(tab._list.count()):
    tab._list.setCurrentRow(i)
    E.pump(0.1)
E.check("the Nakama tab lists every member without an error", not ERRS and tab._list.count() >= len(BAD) + 1)
E.finish()
