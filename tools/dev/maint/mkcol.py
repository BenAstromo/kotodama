"""A small fake Anki collection over in-memory sqlite, for scenario tests.

    col = mkcol.Col(note_types={"Vocab": ["Word", "Reading"]},
                    decks=["Main"],
                    notes=[("Main", "Vocab", {"Word": "食べる", "Reading": "たべる"}, (2, 2, 30))])
card tuple = (type, queue, ivl): type 0 new / 1 learn / 2 review / 3 relearn; queue -1 suspended.
"""
import sqlite3, time


def _deck_name(q):
    i = q.index('"deck:') + 6
    out, esc = [], False
    while i < len(q):
        c = q[i]
        if esc:
            out.append(c); esc = False
        elif c == "\\":
            esc = True
        elif c == '"':
            break
        else:
            out.append(c)
        i += 1
    return "".join(out)


class Col:
    def __init__(self, note_types=None, decks=None, notes=None):
        db = self._db = sqlite3.connect(":memory:", check_same_thread=False)
        db.executescript("""
          create table notetypes (id integer primary key, name text);
          create table fields (ntid integer, ord integer, name text);
          create table decks (id integer primary key, name text);
          create table notes (id integer primary key, mid integer, mod integer, flds text);
          create table cards (id integer primary key, nid integer, did integer, odid integer,
                              type integer, queue integer, ivl integer, factor integer,
                              lapses integer, data text);
          create table revlog (id integer primary key, cid integer, type integer, ivl integer);""")
        self._nt = {}
        for i, (name, flds) in enumerate((note_types or {}).items(), 1):
            db.execute("insert into notetypes values (?,?)", (i, name))
            for o, f in enumerate(flds):
                db.execute("insert into fields values (?,?,?)", (i, o, f))
            self._nt[name] = (i, flds)
        self._decks = {}
        for i, name in enumerate(decks or [], 1):
            db.execute("insert into decks values (?,?)", (i, name.replace("::", "\x1f")))
            self._decks[name] = i
        nid = 1_600_000_000_000
        for deck, nt, fields, card in notes or []:
            nid += 1
            mid, flds = self._nt[nt]
            db.execute("insert into notes values (?,?,?,?)",
                       (nid, mid, int(time.time()), "\x1f".join(fields.get(f, "") for f in flds)))
            t, q, ivl = card
            db.execute("insert into cards values (?,?,?,?,?,?,?,?,?,?)",
                       (nid + 7, nid, self._decks[deck], 0, t, q, ivl, 2500, 0, "{}"))
            if t:
                db.execute("insert into revlog values (?,?,?,?)", (nid + 9, nid + 7, 0, ivl))
        db.commit()
        self.db = _DB(db)
        self.models = _Models(self)
        self.decks = _Decks(self)
        self._config = {}
        import types
        self.sched = types.SimpleNamespace(day_cutoff=int(time.time()) + 3600)

    def _where(self, q):
        name = _deck_name(q).replace("::", "\x1f")
        dids = [i for i, n in self._db.execute("select id,name from decks")
                if n == name or n.startswith(name + "\x1f")]
        qs = ",".join(map(str, dids)) or "-1"
        w = f"(did in ({qs}) or odid in ({qs}))"
        if "-is:new" in q:
            w += " and type != 0"
        if "-is:suspended" in q:
            w += " and queue != -1"
        if " is:review" in q:
            w += " and type in (2,3)"
        return w

    def find_notes(self, q):
        if '"deck:' not in q:
            return []
        return [r[0] for r in self._db.execute(f"select distinct nid from cards where {self._where(q)}")]

    def find_cards(self, q):
        if '"deck:' not in q:
            return []
        return [r[0] for r in self._db.execute(f"select id from cards where {self._where(q)}")]

    def get_config(self, key, default=None):
        return self._config.get(key, default)

    def set_config(self, key, val):
        self._config[key] = val

    def get_note(self, nid):
        mid, flds = self._db.execute("select mid,flds from notes where id=?", (nid,)).fetchone()
        name = [n for n, (i, _f) in self._nt.items() if i == mid][0]
        return _Note(dict(zip(self._nt[name][1], flds.split("\x1f"))), name)


class _Note(dict):
    def __init__(self, d, name):
        super().__init__(d)
        self._name = name

    def note_type(self):
        return {"name": self._name}


class _DB:
    def __init__(self, db):
        self._db = db

    def all(self, sql, *a):
        return self._db.execute(sql, a).fetchall()

    def first(self, sql, *a):
        return self._db.execute(sql, a).fetchone()

    def scalar(self, sql, *a):
        r = self._db.execute(sql, a).fetchone()
        return r[0] if r else None

    def list(self, sql, *a):
        return [r[0] for r in self._db.execute(sql, a)]


class _Models:
    def __init__(self, col):
        self._c = col

    def get(self, mid):
        for name, (i, flds) in self._c._nt.items():
            if i == mid:
                return {"id": i, "name": name, "flds": [{"name": f, "ord": o} for o, f in enumerate(flds)]}
        return None

    def all(self):
        return [self.get(i) for i, _f in self._c._nt.values()]

    def all_names_and_ids(self):
        return [type("N", (), {"name": n, "id": i})() for n, (i, _f) in self._c._nt.items()]


class _Decks:
    def __init__(self, col):
        self._c = col

    def all(self):
        return [{"id": i, "name": n} for n, i in self._c._decks.items()]

    def all_names_and_ids(self):
        return [type("D", (), {"name": n, "id": i})() for n, i in self._c._decks.items()]

    def id_for_name(self, name):
        return self._c._decks.get(name)
