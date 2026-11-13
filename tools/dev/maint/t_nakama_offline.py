"""Nakama with no server: refused (127.0.0.1:9) and silent (a blackhole
address → the 12 s timeout). Every call must return at once (work in the
background), report a readable error, keep the local state, and the
Nakama tab must stay usable. Nothing ever goes to the real Worker."""
import os, sys, time
mode = sys.argv[1] if len(sys.argv) > 1 else "refused"
os.environ["KOTODAMA_NAKAMA_URL"] = {"refused": "http://127.0.0.1:9",
                                     "timeout": "http://10.255.255.1:81"}[mode]
import stubenv as E
os.environ["KOTODAMA_NAKAMA_URL"] = {"refused": "http://127.0.0.1:9",
                                     "timeout": "http://10.255.255.1:81"}[mode]
import mkcol
E.mw.col = mkcol.Col({"V": ["Word"]}, ["Main"], [])
nk = E.load("nakama")
E.check(f"[{mode}] not the real Worker", "workers.dev" not in nk.SERVER and nk.SERVER.startswith("http://"))
got = {}


def wait(key, limit):
    t0 = time.monotonic()
    while key not in got and time.monotonic() - t0 < limit:
        E.pump(0.05)
    return time.monotonic() - t0


limit = 30 if mode == "timeout" else 10
t0 = time.monotonic()
nk.join("Tester", lambda ok, err: got.__setitem__("join", (ok, err)))
E.check(f"[{mode}] join returns at once (background)", time.monotonic() - t0 < 0.5)
# the main thread keeps running while it waits: count event-loop turns
turns = [0]
QTimer = E.QtCore.QTimer
tick = QTimer(); tick.timeout.connect(lambda: turns.__setitem__(0, turns[0] + 1)); tick.start(20)
took = wait("join", limit)
tick.stop()
ok, err = got.get("join", (None, None))
print(f"  join: ok={ok} err={err!r} after {took:.1f}s, main-thread ticks {turns[0]}")
E.check(f"[{mode}] join fails with a readable message", ok is False and err and "Nakama server" in err)
E.check(f"[{mode}] main thread never froze", turns[0] >= took / 0.02 * 0.5)
E.check(f"[{mode}] still not joined, nothing half-saved", not nk.joined() and not nk.state().get("id"))

# pretend we had joined before (code from the collection): upload / fetch / leave offline
s = nk.state()
s.update(id="ABCD2345", key="k" * 32, name="Tester", mine={"v": 1, "rank": 5})
nk.upload_if_changed(lambda sent, err: got.__setitem__("up", (sent, err)))
wait("up", limit)
print("  upload:", got.get("up"))
E.check(f"[{mode}] upload fails quietly with a message, not marked sent",
        got.get("up", (1, None))[0] is False and got["up"][1] and not s.get("sent"))
nk.add_friend("WXYZ6789")
nk.fetch_friends(lambda err: got.__setitem__("fetch", err))
wait("fetch", limit)
print("  fetch:", got.get("fetch"))
E.check(f"[{mode}] fetch reports an error, friends kept", got.get("fetch") and "WXYZ6789" in s["friends"])
nk.leave(lambda ok, err: got.__setitem__("leave", (ok, err)))
wait("leave", limit)
print("  leave:", got.get("leave"))
E.check(f"[{mode}] leave fails, still joined (code not lost)", got.get("leave", (True,))[0] is False and nk.joined())

# the Nakama tab with the server down
nv = E.load("nakama_view")
tab = nv.NakamaTab()
tab.resize(800, 600); tab.show()
E.pump(1.0)
t1 = time.monotonic()
while time.monotonic() - t1 < limit:
    E.pump(0.2)
    if mode == "refused" and time.monotonic() - t1 > 3:
        break
E.check(f"[{mode}] Nakama tab built and shown offline", tab.isVisible())
E.finish()
