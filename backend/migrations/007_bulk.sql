CREATE TABLE bulk_staging (
  token TEXT PRIMARY KEY,
  group_id INTEGER NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
  stage_id INTEGER,
  rows_json TEXT NOT NULL,
  problems_json TEXT NOT NULL,
  counts_json TEXT NOT NULL,
  created_at INTEGER NOT NULL
);
CREATE TABLE bulk_batches (
  batch_id TEXT PRIMARY KEY,
  group_id INTEGER NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
  epoch INTEGER NOT NULL,
  created_at INTEGER NOT NULL,
  undone_at INTEGER
);
