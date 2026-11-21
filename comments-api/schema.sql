CREATE TABLE IF NOT EXISTS comments (
  id TEXT PRIMARY KEY,
  post_key TEXT NOT NULL,
  nickname TEXT NOT NULL,
  content TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending','approved','rejected')),
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  reviewed_at TEXT,
  ip_hash TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS comments_public
ON comments(post_key, status, created_at DESC);
CREATE INDEX IF NOT EXISTS comments_rate_limit
ON comments(ip_hash, created_at DESC);
