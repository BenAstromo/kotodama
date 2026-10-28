CREATE TABLE IF NOT EXISTS profiles (
  id       TEXT PRIMARY KEY,     -- the friend code (8 chars)
  key_hash TEXT NOT NULL,        -- SHA-256 of the owner's secret key
  name     TEXT NOT NULL,
  data     TEXT NOT NULL,        -- the add-on's snapshot (JSON, ≤ 6 KB)
  created  INTEGER NOT NULL,
  updated  INTEGER NOT NULL,
  supporter INTEGER                -- first Ko-fi tip with this code in the message (unix time), or NULL
);
-- An existing database gets the column once (2026-10-27):
--   npx wrangler d1 execute kotodama-nakama --remote --command "ALTER TABLE profiles ADD COLUMN supporter INTEGER"

CREATE INDEX IF NOT EXISTS profiles_updated ON profiles (updated);
