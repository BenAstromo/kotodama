"""Today's rebuilt history value == today's live snapshot (real deck copy)."""
import sys, os, io, contextlib
S = sys.argv[1]; sys.argv = [sys.argv[0], S, "--ignore-suspended"]
with contextlib.redirect_stdout(io.StringIO()):
    exec(open(os.path.join(S, "harness.py"), encoding="utf-8").read())
sys.stdout.reconfigure(encoding="utf-8")
from jlpt_progress import history
deck = cfg["deck_name"]
live = history.snapshot_values(res, deck, True)
data = history.rebuild(res, deck, True)
last = {k: v[-1] for k, v in data["values"].items() if v}
print("days rebuilt:", len(data["days"]), data["days"][0], "→", data["days"][-1], " today:", history.today())
diffs = {k: (live[k], last[k]) for k in live if k in last and live[k] != last[k]}
print("keys compared:", sorted(k for k in live if k in last))
print("only live:", sorted(set(live) - set(last)), " only rebuilt:", sorted(set(last) - set(live)))
print("DIFFER (live, rebuilt):", diffs if diffs else "none")
