"""A mark made while a background count reads the marks must not break
the count ("Set changed size during iteration")."""
import sys, threading
import stubenv as E
ov = E.load("overrides")
o = ov.Overrides(ov.os.path.join(E.ADDON, "user_files", "race.json"))
o.found = {f"w{i}\tr{i}" for i in range(20000)}
o._save = lambda: None                      # no disk writes in the loop
sys.setswitchinterval(1e-6)
errors, stop = [], threading.Event()
def reader():
    while not stop.is_set():
        try:
            o.found_pairs(); [k for k in o.found]; {k.split("\t")[0] for k in o.suspended}
        except RuntimeError as e:
            errors.append(str(e)); return
t = threading.Thread(target=reader); t.start()
for i in range(20000):
    o.toggle_found(f"x{i}", "y"); o.toggle_suspended(f"s{i}", "y")
    if errors: break
stop.set(); t.join()
E.check("background reads survive marks made meanwhile", not errors, errors[:1])
E.finish()
