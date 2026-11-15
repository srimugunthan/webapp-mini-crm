ALTER TABLE groups ADD COLUMN pipeline_epoch INTEGER NOT NULL DEFAULT 0;
CREATE TABLE stages (
  id INTEGER PRIMARY KEY,
  group_id INTEGER NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
  name TEXT NOT NULL COLLATE NOCASE,
  position INTEGER NOT NULL,
  is_final INTEGER NOT NULL DEFAULT 0,
  UNIQUE (group_id, name)
);
ALTER TABLE group_members ADD COLUMN stage_id INTEGER REFERENCES stages(id) ON DELETE SET NULL;
ALTER TABLE group_members ADD COLUMN stage_changed_at INTEGER;
ALTER TABLE group_members ADD COLUMN next_follow_up_at INTEGER;
CREATE TABLE stage_history (
  id INTEGER PRIMARY KEY,
  group_id INTEGER NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
  contact_id INTEGER NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
  from_stage_id INTEGER REFERENCES stages(id) ON DELETE SET NULL,
  to_stage_id INTEGER REFERENCES stages(id) ON DELETE SET NULL,
  from_stage_name TEXT,
  to_stage_name TEXT,
  changed_at INTEGER NOT NULL,
  source TEXT NOT NULL DEFAULT 'manual' CHECK (source IN ('manual', 'bulk')),
  batch_id TEXT,
  added_to_group INTEGER NOT NULL DEFAULT 0,
  note TEXT
);
CREATE INDEX idx_history_contact ON stage_history(contact_id);
CREATE INDEX idx_history_batch ON stage_history(batch_id);
