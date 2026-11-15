CREATE TABLE contacts (
  id INTEGER PRIMARY KEY,
  first_name TEXT NOT NULL DEFAULT '',
  last_name TEXT NOT NULL DEFAULT '',
  company TEXT NOT NULL DEFAULT '',
  position TEXT NOT NULL DEFAULT '',
  linkedin_url TEXT NOT NULL UNIQUE,
  email TEXT NOT NULL DEFAULT '',
  connected_on TEXT,
  last_visited_at INTEGER,
  last_messaged_at INTEGER,
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL
);
CREATE INDEX idx_contacts_last_name ON contacts(last_name COLLATE NOCASE);
CREATE INDEX idx_contacts_company ON contacts(company COLLATE NOCASE);
