"""SQLite schema helpers for Clean Workroot."""

from __future__ import annotations

import sqlite3
from pathlib import Path


SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_migrations (
  migration_id TEXT PRIMARY KEY,
  applied_at TEXT
);

CREATE TABLE IF NOT EXISTS workroots (
  workroot_id TEXT PRIMARY KEY,
  name TEXT,
  state_directory TEXT,
  user_directory TEXT
);

CREATE TABLE IF NOT EXISTS directory_bindings (
  user_directory TEXT PRIMARY KEY,
  workroot_id TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS workroot_aliases (
  alias TEXT PRIMARY KEY,
  workroot_id TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS workroot_relationships (
  relationship_id TEXT PRIMARY KEY,
  from_workroot_id TEXT NOT NULL,
  to_workroot_id TEXT NOT NULL,
  relationship_type TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS assets (
  asset_id TEXT PRIMARY KEY,
  workroot_id TEXT NOT NULL,
  asset_type TEXT NOT NULL,
  title TEXT,
  lifecycle_status TEXT,
  publication_status TEXT,
  current_path TEXT,
  content_hash TEXT,
  updated_at TEXT
);

CREATE TABLE IF NOT EXISTS asset_surfaces (
  surface_id TEXT PRIMARY KEY,
  workroot_id TEXT NOT NULL,
  path TEXT NOT NULL,
  surface_type TEXT NOT NULL,
  git_policy TEXT
);

CREATE TABLE IF NOT EXISTS asset_publications (
  publication_id TEXT PRIMARY KEY,
  asset_id TEXT NOT NULL,
  workroot_id TEXT NOT NULL,
  surface_id TEXT NOT NULL,
  target_path TEXT NOT NULL,
  publication_status TEXT
);

CREATE TABLE IF NOT EXISTS asset_path_history (
  history_id TEXT PRIMARY KEY,
  asset_id TEXT NOT NULL,
  path TEXT NOT NULL,
  observed_at TEXT
);

CREATE TABLE IF NOT EXISTS asset_provenance (
  provenance_id TEXT PRIMARY KEY,
  asset_id TEXT NOT NULL,
  source_ref TEXT
);

CREATE TABLE IF NOT EXISTS release_records (
  release_id TEXT PRIMARY KEY,
  workroot_id TEXT NOT NULL,
  target_type TEXT NOT NULL,
  target_id TEXT NOT NULL,
  release_level TEXT NOT NULL,
  recall_rule TEXT
);

CREATE TABLE IF NOT EXISTS tombstones (
  tombstone_id TEXT PRIMARY KEY,
  workroot_id TEXT NOT NULL,
  target_type TEXT NOT NULL,
  target_id TEXT NOT NULL,
  title TEXT,
  symbolic_note TEXT
);

CREATE TABLE IF NOT EXISTS redactions (
  redaction_id TEXT PRIMARY KEY,
  workroot_id TEXT NOT NULL,
  target_type TEXT NOT NULL,
  target_id TEXT NOT NULL,
  redacted_fields TEXT,
  redaction_reason TEXT
);

CREATE TABLE IF NOT EXISTS deletion_records (
  deletion_id TEXT PRIMARY KEY,
  workroot_id TEXT NOT NULL,
  target_type TEXT NOT NULL,
  target_id TEXT NOT NULL,
  minimum_audit_note TEXT
);

CREATE TABLE IF NOT EXISTS release_propagation_events (
  event_id TEXT PRIMARY KEY,
  release_id TEXT NOT NULL,
  event_type TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tasks (
  task_id TEXT PRIMARY KEY,
  workroot_id TEXT NOT NULL,
  title TEXT,
  status TEXT
);

CREATE TABLE IF NOT EXISTS agent_runs (
  run_id TEXT PRIMARY KEY,
  task_id TEXT,
  workroot_id TEXT NOT NULL,
  status TEXT
);

CREATE TABLE IF NOT EXISTS work_actions (
  action_id TEXT PRIMARY KEY,
  task_id TEXT,
  workroot_id TEXT NOT NULL,
  action_type TEXT
);

CREATE TABLE IF NOT EXISTS work_checkpoints (
  checkpoint_id TEXT PRIMARY KEY,
  task_id TEXT,
  workroot_id TEXT NOT NULL,
  current_status TEXT
);

CREATE TABLE IF NOT EXISTS retrieval_cards (
  card_id TEXT PRIMARY KEY,
  task_id TEXT,
  workroot_id TEXT NOT NULL,
  source_paths TEXT
);

CREATE TABLE IF NOT EXISTS invalidation_records (
  invalidation_id TEXT PRIMARY KEY,
  workroot_id TEXT NOT NULL,
  invalidated_claim TEXT,
  reason TEXT
);

CREATE TABLE IF NOT EXISTS handoffs (
  handoff_id TEXT PRIMARY KEY,
  workroot_id TEXT NOT NULL,
  title TEXT
);

CREATE TABLE IF NOT EXISTS work_events (
  event_id TEXT PRIMARY KEY,
  workroot_id TEXT NOT NULL,
  event_type TEXT
);

CREATE TABLE IF NOT EXISTS operation_transactions (
  transaction_id TEXT PRIMARY KEY,
  workroot_id TEXT NOT NULL,
  status TEXT
);

CREATE TABLE IF NOT EXISTS relationship_nodes (
  node_id TEXT PRIMARY KEY,
  workroot_id TEXT NOT NULL,
  node_type TEXT NOT NULL,
  title TEXT
);

CREATE TABLE IF NOT EXISTS relationship_edges (
  edge_id TEXT PRIMARY KEY,
  workroot_id TEXT NOT NULL,
  from_node_id TEXT NOT NULL,
  to_node_id TEXT NOT NULL,
  relationship_type TEXT NOT NULL,
  confidence REAL,
  status TEXT
);

CREATE TABLE IF NOT EXISTS relationship_evidence (
  evidence_id TEXT PRIMARY KEY,
  edge_id TEXT NOT NULL,
  evidence_type TEXT NOT NULL,
  source_ref TEXT
);

CREATE TABLE IF NOT EXISTS indexes (
  index_id TEXT PRIMARY KEY,
  workroot_id TEXT NOT NULL,
  index_kind TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS index_manifests (
  index_id TEXT PRIMARY KEY,
  index_kind TEXT NOT NULL,
  source_high_watermark TEXT,
  built_high_watermark TEXT,
  status TEXT
);

CREATE TABLE IF NOT EXISTS index_builds (
  build_id TEXT PRIMARY KEY,
  index_id TEXT NOT NULL,
  status TEXT
);

CREATE TABLE IF NOT EXISTS index_invalidations (
  invalidation_id TEXT PRIMARY KEY,
  index_id TEXT NOT NULL,
  reason TEXT
);

CREATE TABLE IF NOT EXISTS indexed_files (
  file_id TEXT PRIMARY KEY,
  workroot_id TEXT NOT NULL,
  relative_path TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS indexed_chunks (
  chunk_id TEXT PRIMARY KEY,
  file_id TEXT NOT NULL,
  workroot_id TEXT NOT NULL,
  body TEXT
);

CREATE VIRTUAL TABLE IF NOT EXISTS indexed_chunks_fts USING fts5(chunk_id, body);

CREATE TABLE IF NOT EXISTS context_candidates (
  candidate_id TEXT PRIMARY KEY,
  workroot_id TEXT NOT NULL,
  source_type TEXT NOT NULL,
  source_id TEXT NOT NULL,
  title TEXT,
  summary TEXT,
  domains TEXT,
  importance TEXT,
  confidence REAL,
  status TEXT,
  context_policy TEXT,
  safety_policy TEXT,
  token_estimate INTEGER,
  updated_at TEXT,
  last_used_at TEXT,
  use_count INTEGER DEFAULT 0
);

CREATE VIRTUAL TABLE IF NOT EXISTS context_candidates_fts USING fts5(candidate_id, title, summary, domains);

CREATE TABLE IF NOT EXISTS global_index_entries (
  entry_id TEXT PRIMARY KEY,
  workroot_id TEXT NOT NULL,
  entry_type TEXT NOT NULL,
  title TEXT
);

CREATE TABLE IF NOT EXISTS context_packages (
  package_id TEXT PRIMARY KEY,
  workroot_id TEXT NOT NULL,
  mode TEXT,
  rendered TEXT
);

CREATE TABLE IF NOT EXISTS context_traces (
  trace_id TEXT PRIMARY KEY,
  workroot_id TEXT NOT NULL,
  package_id TEXT,
  debug_json TEXT
);

CREATE TABLE IF NOT EXISTS candidate_selections (
  selection_id TEXT PRIMARY KEY,
  trace_id TEXT NOT NULL,
  candidate_id TEXT NOT NULL,
  reason TEXT
);

CREATE TABLE IF NOT EXISTS budget_trim_decisions (
  decision_id TEXT PRIMARY KEY,
  trace_id TEXT NOT NULL,
  section TEXT,
  reason TEXT
);

CREATE TABLE IF NOT EXISTS doctor_runs (
  doctor_run_id TEXT PRIMARY KEY,
  workroot_id TEXT,
  status TEXT
);

CREATE TABLE IF NOT EXISTS diagnostic_findings (
  finding_id TEXT PRIMARY KEY,
  doctor_run_id TEXT,
  severity TEXT,
  message TEXT
);

CREATE TABLE IF NOT EXISTS maintenance_actions (
  action_id TEXT PRIMARY KEY,
  workroot_id TEXT,
  action_type TEXT,
  status TEXT
);

INSERT OR IGNORE INTO schema_migrations (migration_id, applied_at)
VALUES ('001-clean-workroot-schema', datetime('now'));
"""


def initialize_workroot_sqlite(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.executescript(SCHEMA)
