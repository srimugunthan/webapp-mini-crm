CREATE TABLE pipeline_templates (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL UNIQUE COLLATE NOCASE
);
CREATE TABLE pipeline_template_stages (
  template_id INTEGER NOT NULL REFERENCES pipeline_templates(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  position INTEGER NOT NULL,
  is_final INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (template_id, position)
);
INSERT INTO pipeline_templates (id, name) VALUES (1, 'Starter');
INSERT INTO pipeline_template_stages (template_id, name, position, is_final) VALUES
  (1, 'Connected', 0, 0), (1, 'Reached out', 1, 0), (1, 'In conversation', 2, 0), (1, 'Closed', 3, 1);
