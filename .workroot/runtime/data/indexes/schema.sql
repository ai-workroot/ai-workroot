-- AI Workroot local SQLite index schema.
--
-- Files remain the source of truth. This database is an optional,
-- rebuildable accelerator for lookup and continuity.
--
-- Temporal columns intentionally use ISO-8601 TEXT. SQLite has no
-- dedicated datetime storage class, and Workroot CSV/Markdown files
-- are the durable source of truth.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS tasks (
  task_id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  status TEXT NOT NULL,
  owner_scope TEXT,
  visibility TEXT,
  created_at TEXT,
  updated_at TEXT,
  user_visible_output_path TEXT,
  source_path TEXT,
  handoff_path TEXT
);

CREATE TABLE IF NOT EXISTS artifacts (
  artifact_id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  type TEXT,
  status TEXT,
  privacy_level TEXT,
  created_at TEXT,
  updated_at TEXT,
  source_path TEXT,
  output_path TEXT,
  related_task_id TEXT,
  FOREIGN KEY (related_task_id) REFERENCES tasks(task_id)
);

CREATE TABLE IF NOT EXISTS decisions (
  decision_id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  status TEXT,
  created_at TEXT,
  updated_at TEXT,
  decision_path TEXT,
  related_task_id TEXT,
  replaces_decision_id TEXT,
  FOREIGN KEY (related_task_id) REFERENCES tasks(task_id)
);

CREATE TABLE IF NOT EXISTS mind_entries (
  mind_id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  type TEXT,
  status TEXT,
  temperature TEXT,
  privacy_level TEXT,
  release_level TEXT,
  retrieval_rule TEXT,
  created_at TEXT,
  updated_at TEXT,
  source_path TEXT,
  related_task_id TEXT,
  replaces_mind_id TEXT,
  FOREIGN KEY (related_task_id) REFERENCES tasks(task_id)
);

CREATE TABLE IF NOT EXISTS links (
  link_id TEXT PRIMARY KEY,
  source_type TEXT NOT NULL,
  source_id TEXT NOT NULL,
  target_type TEXT NOT NULL,
  target_id TEXT NOT NULL,
  relation TEXT NOT NULL,
  created_at TEXT,
  updated_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_owner_scope ON tasks(owner_scope);
CREATE INDEX IF NOT EXISTS idx_artifacts_task ON artifacts(related_task_id);
CREATE INDEX IF NOT EXISTS idx_decisions_task ON decisions(related_task_id);
CREATE INDEX IF NOT EXISTS idx_mind_type ON mind_entries(type);
CREATE INDEX IF NOT EXISTS idx_mind_temperature ON mind_entries(temperature);
CREATE INDEX IF NOT EXISTS idx_links_source ON links(source_type, source_id);
CREATE INDEX IF NOT EXISTS idx_links_target ON links(target_type, target_id);
