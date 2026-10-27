CREATE TABLE IF NOT EXISTS profiles (
  id       TEXT PRIMARY KEY,     -- the friend code (8 chars)
  key_hash TEXT NOT NULL,        -- SHA-256 of the owner's secret key
  name     TEXT NOT NULL,
  data     TEXT NOT NULL,        -- the add-on's snapshot (JSON, ≤ 6 KB)
  created  INTEGER NOT NULL,
  updated  INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS profiles_updated ON profiles (updated);
