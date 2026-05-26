"""SQLite schema helpers for Clean Workroot."""

from __future__ import annotations

import sqlite3
from pathlib import Path

REQUIRED_TABLES = (
    "schema_migrations",
    "workroots",
    "directory_bindings",
    "workroot_aliases",
    "workroot_relationships",
    "assets",
    "asset_surfaces",
    "asset_publications",
    "asset_path_history",
    "asset_provenance",
    "release_records",
    "tombstones",
    "redactions",
    "deletion_records",
    "release_propagation_events",
    "protocol_commit_batches",
    "protocol_events",
    "protocol_event_effects",
    "exchange_leases",
    "state_versions",
    "tasks",
    "task_runs",
    "task_summaries",
    "task_items",
    "agent_runs",
    "work_actions",
    "work_checkpoints",
    "retrieval_cards",
    "context_recall_hints",
    "context_recall_hints_fts",
    "invalidation_records",
    "handoffs",
    "time_events",
    "work_events",
    "operation_transactions",
    "relationship_nodes",
    "relationship_edges",
    "relationship_evidence",
    "indexes",
    "index_manifests",
    "index_builds",
    "index_invalidations",
    "indexed_files",
    "indexed_chunks",
    "indexed_chunks_fts",
    "context_candidates",
    "context_candidates_fts",
    "global_index_entries",
    "context_packages",
    "context_traces",
    "candidate_selections",
    "budget_trim_decisions",
    "doctor_runs",
    "diagnostic_findings",
    "maintenance_actions",
)


SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_migrations (
  migration_id TEXT PRIMARY KEY,
  appliedAt TEXT
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
  surface_id TEXT,
  current_path TEXT,
  content_hash TEXT,
  updatedAt TEXT
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
  publication_status TEXT,
  publishedAt TEXT
);

CREATE TABLE IF NOT EXISTS asset_path_history (
  history_id TEXT PRIMARY KEY,
  asset_id TEXT NOT NULL,
  path TEXT NOT NULL,
  observedAt TEXT
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
  status TEXT,
  task_kind TEXT,
  process_level TEXT,
  role TEXT NOT NULL DEFAULT 'normal',
  parent_task_id TEXT,
  root_task_id TEXT,
  retention_policy TEXT NOT NULL DEFAULT 'until_closed',
  visibility TEXT NOT NULL DEFAULT 'normal',
  summary_id TEXT,
  rollup_summary_id TEXT,
  created_at TEXT NOT NULL DEFAULT '1970-01-01T00:00:00Z',
  updated_at TEXT NOT NULL DEFAULT '1970-01-01T00:00:00Z',
  closed_at TEXT,
  archived_at TEXT,
  metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS task_runs (
  run_id TEXT PRIMARY KEY,
  task_id TEXT NOT NULL,
  workroot_id TEXT NOT NULL,
  agent_name TEXT NOT NULL,
  agent_instance_id TEXT,
  status TEXT NOT NULL,
  goal TEXT,
  input_summary TEXT,
  output_summary TEXT,
  detail_body_ref TEXT,
  source_lease_id TEXT,
  started_at TEXT NOT NULL,
  ended_at TEXT
);

CREATE TABLE IF NOT EXISTS task_summaries (
  summary_id TEXT PRIMARY KEY,
  task_id TEXT NOT NULL,
  workroot_id TEXT NOT NULL,
  status TEXT NOT NULL,
  summary_text TEXT NOT NULL,
  open_questions_json TEXT NOT NULL DEFAULT '[]',
  next_actions_json TEXT NOT NULL DEFAULT '[]',
  source_refs_json TEXT NOT NULL DEFAULT '[]',
  generated_by TEXT NOT NULL,
  generated_at TEXT NOT NULL,
  superseded_by TEXT
);

CREATE TABLE IF NOT EXISTS task_items (
  item_id TEXT PRIMARY KEY,
  workroot_id TEXT NOT NULL,
  task_id TEXT NOT NULL,
  run_id TEXT,
  title TEXT NOT NULL,
  status TEXT NOT NULL,
  item_order INTEGER NOT NULL DEFAULT 0,
  detail TEXT,
  result_summary TEXT,
  source_event_id TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  completed_at TEXT,
  metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_task_items_task_status
  ON task_items(workroot_id, task_id, status, item_order);

CREATE TABLE IF NOT EXISTS agent_runs (
  run_id TEXT PRIMARY KEY,
  task_id TEXT,
  workroot_id TEXT NOT NULL,
  status TEXT,
  validity TEXT
);

CREATE TABLE IF NOT EXISTS work_actions (
  action_id TEXT PRIMARY KEY,
  task_id TEXT,
  workroot_id TEXT NOT NULL,
  action_type TEXT,
  risk_level TEXT
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

CREATE TABLE IF NOT EXISTS context_recall_hints (
  hint_id TEXT PRIMARY KEY,
  workroot_id TEXT NOT NULL,
  target_type TEXT NOT NULL,
  target_id TEXT NOT NULL,
  scope_type TEXT,
  scope_id TEXT,
  kind TEXT,
  title TEXT,
  summary TEXT,
  priority TEXT,
  recall_rule TEXT,
  lifecycle_status TEXT,
  origin TEXT,
  source_ref TEXT,
  createdAt TEXT,
  updatedAt TEXT
);

CREATE VIRTUAL TABLE IF NOT EXISTS context_recall_hints_fts USING fts5(hint_id, title, summary);

CREATE TABLE IF NOT EXISTS invalidation_records (
  invalidation_id TEXT PRIMARY KEY,
  workroot_id TEXT NOT NULL,
  invalidated_claim TEXT,
  reason TEXT
);

CREATE TABLE IF NOT EXISTS handoffs (
  handoff_id TEXT PRIMARY KEY,
  workroot_id TEXT NOT NULL,
  title TEXT,
  target TEXT,
  body TEXT,
  task_id TEXT,
  run_id TEXT,
  status TEXT,
  current_state TEXT,
  next_action TEXT,
  open_items_json TEXT NOT NULL DEFAULT '[]',
  open_questions_json TEXT NOT NULL DEFAULT '[]',
  important_refs_json TEXT NOT NULL DEFAULT '[]',
  source_refs_json TEXT NOT NULL DEFAULT '[]',
  created_at TEXT,
  superseded_by TEXT
);

CREATE TABLE IF NOT EXISTS protocol_commit_batches (
  batch_id TEXT PRIMARY KEY,
  workroot_id TEXT NOT NULL,
  request_id TEXT NOT NULL,
  idempotency_key TEXT NOT NULL,
  request_hash TEXT NOT NULL,
  response_json TEXT,
  status TEXT NOT NULL,
  received_at TEXT NOT NULL,
  completed_at TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_protocol_commit_batches_idempotency
  ON protocol_commit_batches(workroot_id, idempotency_key);

CREATE TABLE IF NOT EXISTS protocol_events (
  event_id TEXT PRIMARY KEY,
  batch_id TEXT NOT NULL,
  workroot_id TEXT NOT NULL,
  request_id TEXT NOT NULL,
  lease_id TEXT,
  idempotency_key TEXT NOT NULL,
  kind TEXT NOT NULL,
  schema_version TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  evidence_json TEXT NOT NULL DEFAULT '[]',
  confirmation_json TEXT NOT NULL DEFAULT '{}',
  source_json TEXT NOT NULL DEFAULT '{}',
  occurred_at TEXT NOT NULL,
  received_at TEXT NOT NULL,
  status TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_protocol_events_workroot_event
  ON protocol_events(workroot_id, event_id);

CREATE INDEX IF NOT EXISTS idx_protocol_events_kind_time
  ON protocol_events(workroot_id, kind, received_at);

CREATE TABLE IF NOT EXISTS protocol_event_effects (
  effect_id TEXT PRIMARY KEY,
  event_id TEXT NOT NULL,
  effect_type TEXT NOT NULL,
  target_type TEXT NOT NULL,
  target_id TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS exchange_leases (
  lease_id TEXT PRIMARY KEY,
  workroot_id TEXT NOT NULL,
  scope TEXT NOT NULL,
  task_id TEXT,
  run_id TEXT,
  observed_versions_json TEXT NOT NULL,
  allowed_events_json TEXT NOT NULL,
  required_before_stop_json TEXT NOT NULL DEFAULT '[]',
  status TEXT NOT NULL,
  issued_at TEXT NOT NULL,
  expires_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS state_versions (
  workroot_id TEXT NOT NULL,
  scope TEXT NOT NULL,
  version INTEGER NOT NULL,
  updated_at TEXT NOT NULL,
  PRIMARY KEY (workroot_id, scope)
);

CREATE TABLE IF NOT EXISTS time_events (
  event_id TEXT PRIMARY KEY,
  workroot_id TEXT NOT NULL,
  subject_type TEXT NOT NULL,
  subject_id TEXT NOT NULL,
  event_type TEXT NOT NULL,
  occurredAt TEXT NOT NULL,
  timezoneId TEXT,
  localDate TEXT,
  timeRangeStart TEXT,
  timeRangeEnd TEXT,
  source_ref TEXT,
  createdAt TEXT
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
  title TEXT,
  target_type TEXT,
  target_id TEXT
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
  relative_path TEXT NOT NULL,
  source_type TEXT,
  source_id TEXT
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
  updatedAt TEXT,
  lastUsedAt TEXT,
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

INSERT OR IGNORE INTO schema_migrations (migration_id, appliedAt)
VALUES ('001-clean-workroot-schema', strftime('%Y-%m-%dT%H:%M:%SZ','now'));

CREATE INDEX IF NOT EXISTS idx_release_records_workroot_target
  ON release_records(workroot_id, target_type, target_id);
CREATE INDEX IF NOT EXISTS idx_tombstones_workroot_target
  ON tombstones(workroot_id, target_type, target_id);
CREATE INDEX IF NOT EXISTS idx_redactions_workroot_target
  ON redactions(workroot_id, target_type, target_id);
CREATE INDEX IF NOT EXISTS idx_deletion_records_workroot_target
  ON deletion_records(workroot_id, target_type, target_id);
CREATE INDEX IF NOT EXISTS idx_context_recall_hints_workroot_target
  ON context_recall_hints(workroot_id, target_type, target_id);
CREATE INDEX IF NOT EXISTS idx_context_candidates_workroot_source
  ON context_candidates(workroot_id, source_type, source_id);
CREATE INDEX IF NOT EXISTS idx_indexed_files_workroot_source
  ON indexed_files(workroot_id, source_type, source_id);
CREATE INDEX IF NOT EXISTS idx_relationship_nodes_workroot_type
  ON relationship_nodes(workroot_id, node_type, node_id);
CREATE INDEX IF NOT EXISTS idx_relationship_nodes_workroot_target
  ON relationship_nodes(workroot_id, target_type, target_id);
CREATE INDEX IF NOT EXISTS idx_relationship_edges_workroot_nodes
  ON relationship_edges(workroot_id, from_node_id, to_node_id);
CREATE INDEX IF NOT EXISTS idx_time_events_workroot_subject
  ON time_events(workroot_id, subject_type, subject_id, occurredAt);

INSERT OR IGNORE INTO schema_migrations (migration_id, appliedAt)
VALUES ('002-release-target-resolution-indexes', strftime('%Y-%m-%dT%H:%M:%SZ','now'));

INSERT OR IGNORE INTO schema_migrations (migration_id, appliedAt)
VALUES ('003-context-recall-hints', strftime('%Y-%m-%dT%H:%M:%SZ','now'));

INSERT OR IGNORE INTO schema_migrations (migration_id, appliedAt)
VALUES ('004-active-work-runtime-fields', strftime('%Y-%m-%dT%H:%M:%SZ','now'));

INSERT OR IGNORE INTO schema_migrations (migration_id, appliedAt)
VALUES ('005-active-asset-runtime-fields', strftime('%Y-%m-%dT%H:%M:%SZ','now'));

INSERT OR IGNORE INTO schema_migrations (migration_id, appliedAt)
VALUES ('006-time-events', strftime('%Y-%m-%dT%H:%M:%SZ','now'));

INSERT OR IGNORE INTO schema_migrations (migration_id, appliedAt)
VALUES ('007-relationship-node-canonical-targets', strftime('%Y-%m-%dT%H:%M:%SZ','now'));

INSERT OR IGNORE INTO schema_migrations (migration_id, appliedAt)
VALUES ('008-handoff-package-fields', strftime('%Y-%m-%dT%H:%M:%SZ','now'));
"""


def initialize_workroot_sqlite(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.executescript(_schema_without_release_indexes())
        _ensure_indexed_file_source_columns(connection)
        _ensure_active_work_runtime_columns(connection)
        _ensure_handoff_package_columns(connection)
        _ensure_protocol_runtime_columns(connection)
        _ensure_active_asset_runtime_columns(connection)
        _ensure_relationship_node_target_columns(connection)
        _ensure_context_candidate_time_columns(connection)
        _ensure_context_recall_hint_time_columns(connection)
        connection.executescript(SCHEMA)


def record_index_invalidation(
    connection: sqlite3.Connection,
    *,
    workroot_id: str,
    index_id: str,
    subject_type: str,
    subject_id: str,
    reason: str,
) -> None:
    connection.execute(
        """
        INSERT INTO index_invalidations (invalidation_id, index_id, reason)
        VALUES (?, ?, ?)
        ON CONFLICT(invalidation_id) DO UPDATE SET
          index_id=excluded.index_id,
          reason=excluded.reason
        """,
        (f"idxinv:{workroot_id}:{subject_type}:{subject_id}", index_id, reason),
    )


def _ensure_indexed_file_source_columns(connection: sqlite3.Connection) -> None:
    columns = {row[1] for row in connection.execute("PRAGMA table_info(indexed_files)").fetchall()}
    for name in ("source_type", "source_id"):
        if name not in columns:
            connection.execute(f"ALTER TABLE indexed_files ADD COLUMN {name} TEXT")


def _ensure_active_work_runtime_columns(connection: sqlite3.Connection) -> None:
    for table, expected in {
        "tasks": {"task_kind": "TEXT", "process_level": "TEXT"},
        "agent_runs": {"validity": "TEXT"},
        "work_actions": {"risk_level": "TEXT"},
    }.items():
        columns = {row[1] for row in connection.execute(f"PRAGMA table_info({table})").fetchall()}
        for name, column_type in expected.items():
            if name not in columns:
                connection.execute(f"ALTER TABLE {table} ADD COLUMN {name} {column_type}")


def _ensure_handoff_package_columns(connection: sqlite3.Connection) -> None:
    columns = {row[1] for row in connection.execute("PRAGMA table_info(handoffs)").fetchall()}
    for name in ("target", "body"):
        if name not in columns:
            connection.execute(f"ALTER TABLE handoffs ADD COLUMN {name} TEXT")


def _add_column_if_missing(connection: sqlite3.Connection, table: str, name: str, definition: str) -> None:
    columns = {row[1] for row in connection.execute(f"PRAGMA table_info({table})").fetchall()}
    if name not in columns:
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")


def _ensure_protocol_runtime_columns(connection: sqlite3.Connection) -> None:
    task_columns = {
        "role": "TEXT NOT NULL DEFAULT 'normal'",
        "parent_task_id": "TEXT",
        "root_task_id": "TEXT",
        "retention_policy": "TEXT NOT NULL DEFAULT 'until_closed'",
        "visibility": "TEXT NOT NULL DEFAULT 'normal'",
        "summary_id": "TEXT",
        "rollup_summary_id": "TEXT",
        "created_at": "TEXT NOT NULL DEFAULT '1970-01-01T00:00:00Z'",
        "updated_at": "TEXT NOT NULL DEFAULT '1970-01-01T00:00:00Z'",
        "closed_at": "TEXT",
        "archived_at": "TEXT",
        "metadata_json": "TEXT NOT NULL DEFAULT '{}'",
    }
    for name, definition in task_columns.items():
        _add_column_if_missing(connection, "tasks", name, definition)

    handoff_columns = {
        "task_id": "TEXT",
        "run_id": "TEXT",
        "status": "TEXT",
        "current_state": "TEXT",
        "next_action": "TEXT",
        "open_items_json": "TEXT NOT NULL DEFAULT '[]'",
        "open_questions_json": "TEXT NOT NULL DEFAULT '[]'",
        "important_refs_json": "TEXT NOT NULL DEFAULT '[]'",
        "source_refs_json": "TEXT NOT NULL DEFAULT '[]'",
        "created_at": "TEXT",
        "superseded_by": "TEXT",
    }
    for name, definition in handoff_columns.items():
        _add_column_if_missing(connection, "handoffs", name, definition)


def _ensure_active_asset_runtime_columns(connection: sqlite3.Connection) -> None:
    columns = {row[1] for row in connection.execute("PRAGMA table_info(assets)").fetchall()}
    if "surface_id" not in columns:
        connection.execute("ALTER TABLE assets ADD COLUMN surface_id TEXT")
    if "updatedAt" not in columns:
        connection.execute("ALTER TABLE assets ADD COLUMN updatedAt TEXT")
    publication_columns = {row[1] for row in connection.execute("PRAGMA table_info(asset_publications)").fetchall()}
    if "publishedAt" not in publication_columns:
        connection.execute("ALTER TABLE asset_publications ADD COLUMN publishedAt TEXT")


def _ensure_relationship_node_target_columns(connection: sqlite3.Connection) -> None:
    columns = {row[1] for row in connection.execute("PRAGMA table_info(relationship_nodes)").fetchall()}
    for name in ("target_type", "target_id"):
        if name not in columns:
            connection.execute(f"ALTER TABLE relationship_nodes ADD COLUMN {name} TEXT")


def _ensure_context_candidate_time_columns(connection: sqlite3.Connection) -> None:
    columns = {row[1] for row in connection.execute("PRAGMA table_info(context_candidates)").fetchall()}
    for name in ("updatedAt", "lastUsedAt"):
        if name not in columns:
            connection.execute(f"ALTER TABLE context_candidates ADD COLUMN {name} TEXT")


def _ensure_context_recall_hint_time_columns(connection: sqlite3.Connection) -> None:
    columns = {row[1] for row in connection.execute("PRAGMA table_info(context_recall_hints)").fetchall()}
    for name in ("createdAt", "updatedAt"):
        if name not in columns:
            connection.execute(f"ALTER TABLE context_recall_hints ADD COLUMN {name} TEXT")


def _schema_without_release_indexes() -> str:
    marker = "CREATE INDEX IF NOT EXISTS idx_release_records_workroot_target"
    head, _, _tail = SCHEMA.partition(marker)
    return head


def sqlite_table_names(connection: sqlite3.Connection) -> set[str]:
    rows = connection.execute("SELECT name FROM sqlite_master WHERE type IN ('table', 'virtual table')").fetchall()
    return {str(row[0]) for row in rows}


def verify_workroot_sqlite(path: Path) -> list[str]:
    if not path.exists():
        return [f"missing SQLite database: {path}"]
    with sqlite3.connect(path) as connection:
        tables = sqlite_table_names(connection)
    return [f"missing SQLite table: {table}" for table in REQUIRED_TABLES if table not in tables]


STRICT_RELEASE_PLACEHOLDERS = {"", "[redacted]", "[deleted]", "[safety-sensitive]"}


def verify_release_derived_index_safety(path: Path) -> list[str]:
    """Report derived index rows that still expose strict release targets."""

    if not path.exists():
        return []
    findings: list[str] = []
    with sqlite3.connect(path) as connection:
        for workroot_id, target_type, target_id, level in _strict_release_targets(connection):
            findings.extend(_leaky_context_candidates(connection, workroot_id, target_type, target_id, level))
            findings.extend(_leaky_indexed_chunks(connection, workroot_id, target_type, target_id, level))
            findings.extend(_leaky_context_recall_hints(connection, workroot_id, target_type, target_id, level))
    return findings


def verify_workroot_logic_integrity(path: Path) -> list[str]:
    if not path.exists():
        return []
    with sqlite3.connect(path) as connection:
        findings: list[str] = []
        findings.extend(_orphan_relationship_edge_findings(connection))
        findings.extend(_orphan_relationship_evidence_findings(connection))
        findings.extend(_missing_release_target_findings(connection))
        findings.extend(_missing_context_candidate_source_findings(connection))
        findings.extend(_missing_context_recall_hint_target_findings(connection))
        findings.extend(_context_package_without_trace_findings(connection))
        return findings


def _orphan_relationship_edge_findings(connection: sqlite3.Connection) -> list[str]:
    findings: list[str] = []
    for edge_id, node_id in _fetchall_safely(
        connection,
        """
        SELECT e.edge_id, e.from_node_id
        FROM relationship_edges e
        LEFT JOIN relationship_nodes n
          ON n.workroot_id = e.workroot_id AND n.node_id = e.from_node_id
        WHERE n.node_id IS NULL
        """,
    ):
        findings.append(f"relationship edge {edge_id} references missing from_node {node_id}")
    for edge_id, node_id in _fetchall_safely(
        connection,
        """
        SELECT e.edge_id, e.to_node_id
        FROM relationship_edges e
        LEFT JOIN relationship_nodes n
          ON n.workroot_id = e.workroot_id AND n.node_id = e.to_node_id
        WHERE n.node_id IS NULL
        """,
    ):
        findings.append(f"relationship edge {edge_id} references missing to_node {node_id}")
    return findings


def _orphan_relationship_evidence_findings(connection: sqlite3.Connection) -> list[str]:
    return [
        f"relationship evidence {evidence_id} references missing edge {edge_id}"
        for evidence_id, edge_id in _fetchall_safely(
            connection,
            """
            SELECT ev.evidence_id, ev.edge_id
            FROM relationship_evidence ev
            LEFT JOIN relationship_edges e ON e.edge_id = ev.edge_id
            WHERE e.edge_id IS NULL
            """,
        )
    ]


def _missing_release_target_findings(connection: sqlite3.Connection) -> list[str]:
    findings: list[str] = []
    for workroot_id, target_type, target_id in _fetchall_safely(
        connection,
        """
        SELECT workroot_id, target_type, target_id
        FROM release_records
        """,
    ):
        if _release_target_exists(connection, str(workroot_id), str(target_type), str(target_id)):
            continue
        findings.append(f"release target {target_type}:{target_id} is missing")
    return findings


def _missing_context_candidate_source_findings(connection: sqlite3.Connection) -> list[str]:
    findings: list[str] = []
    for workroot_id, candidate_id, source_type, source_id in _fetchall_safely(
        connection,
        """
        SELECT workroot_id, candidate_id, source_type, source_id
        FROM context_candidates
        """,
    ):
        source_type = str(source_type)
        source_id = str(source_id)
        if source_type in {"file", "indexed_file", "indexed_chunk", "fts_match"}:
            continue
        if _release_target_exists(connection, str(workroot_id), source_type, source_id):
            continue
        findings.append(f"context candidate {candidate_id} source {source_type}:{source_id} is missing")
    return findings


def _missing_context_recall_hint_target_findings(connection: sqlite3.Connection) -> list[str]:
    findings: list[str] = []
    for workroot_id, hint_id, target_type, target_id in _fetchall_safely(
        connection,
        """
        SELECT workroot_id, hint_id, target_type, target_id
        FROM context_recall_hints
        """,
    ):
        target_type = str(target_type)
        target_id = str(target_id)
        if _release_target_exists(connection, str(workroot_id), target_type, target_id):
            continue
        findings.append(f"context recall hint {hint_id} target {target_type}:{target_id} is missing")
    return findings


def _release_target_exists(connection: sqlite3.Connection, workroot_id: str, target_type: str, target_id: str) -> bool:
    table_by_type = {
        "asset": ("assets", "asset_id"),
        "task": ("tasks", "task_id"),
        "work_action": ("work_actions", "action_id"),
        "agent_run": ("agent_runs", "run_id"),
        "checkpoint": ("work_checkpoints", "checkpoint_id"),
        "handoff": ("handoffs", "handoff_id"),
        "retrieval_card": ("retrieval_cards", "card_id"),
        "context_recall_hint": ("context_recall_hints", "hint_id"),
        "relationship_edge": ("relationship_edges", "edge_id"),
    }
    table = table_by_type.get(target_type)
    if table is None:
        return True
    table_name, id_column = table
    row = _fetch_one_safely(
        connection,
        f"""
        SELECT 1
        FROM {table_name}
        WHERE workroot_id = ? AND {id_column} = ?
        LIMIT 1
        """,
        (workroot_id, target_id),
    )
    return row is not None


def _context_package_without_trace_findings(connection: sqlite3.Connection) -> list[str]:
    return [
        f"context package {package_id} has no trace"
        for (package_id,) in _fetchall_safely(
            connection,
            """
            SELECT p.package_id
            FROM context_packages p
            LEFT JOIN context_traces t
              ON t.workroot_id = p.workroot_id AND t.package_id = p.package_id
            WHERE t.trace_id IS NULL
            """,
        )
    ]


def _strict_release_targets(connection: sqlite3.Connection) -> list[tuple[str, str, str, str]]:
    targets: dict[tuple[str, str, str], str] = {}
    for row in _fetchall_safely(
        connection,
        """
        SELECT workroot_id, target_type, target_id, release_level
        FROM release_records
        WHERE lower(replace(COALESCE(release_level, ''), '_', '-')) IN ('deleted', 'redacted', 'safety-sensitive', 'sensitive')
        """,
    ):
        workroot_id, target_type, target_id, level = (str(row[0]), str(row[1]), str(row[2]), str(row[3]))
        targets[(workroot_id, target_type, target_id)] = _normalize_strict_release_level(level)
    for table, level in (("redactions", "redacted"), ("deletion_records", "deleted")):
        for row in _fetchall_safely(
            connection,
            f"""
            SELECT workroot_id, target_type, target_id
            FROM {table}
            """,
        ):
            workroot_id, target_type, target_id = (str(row[0]), str(row[1]), str(row[2]))
            targets[(workroot_id, target_type, target_id)] = _most_protective_level(
                targets.get((workroot_id, target_type, target_id), "none"),
                level,
            )
    return [
        (workroot_id, target_type, target_id, level)
        for (workroot_id, target_type, target_id), level in sorted(targets.items())
    ]


def _leaky_context_candidates(
    connection: sqlite3.Connection,
    workroot_id: str,
    target_type: str,
    target_id: str,
    level: str,
) -> list[str]:
    rows = _fetchall_safely(
        connection,
        """
        SELECT candidate_id, title, summary
        FROM context_candidates
        WHERE workroot_id = ? AND source_type = ? AND source_id = ?
        """,
        (workroot_id, target_type, target_id),
    )
    findings = [
        f"release-derived index safety: context_candidates:{row[0]} exposes {level} target {target_type}:{target_id}"
        for row in rows
        if _has_non_placeholder_text(row[1], row[2])
    ]
    findings.extend(
        f"release-derived index safety: context_candidates_fts:{row[0]} exposes {level} target {target_type}:{target_id}"
        for row in _context_candidate_fts_rows(connection, workroot_id, target_type, target_id)
        if _has_non_placeholder_text(row[1], row[2])
    )
    for row in _fetchall_safely(
        connection,
        """
        SELECT c.candidate_id, c.title, c.summary
        FROM context_candidates c
        JOIN context_recall_hints h ON h.hint_id = c.source_id
        WHERE c.workroot_id = ?
          AND c.source_type = 'context_recall_hint'
          AND h.workroot_id = ?
          AND h.target_type = ?
          AND h.target_id = ?
        """,
        (workroot_id, workroot_id, target_type, target_id),
    ):
        if _has_non_placeholder_text(row[1], row[2]):
            findings.append(
                f"release-derived index safety: context_candidates:{row[0]} exposes {level} target {target_type}:{target_id}"
            )
    return findings


def _leaky_indexed_chunks(
    connection: sqlite3.Connection,
    workroot_id: str,
    target_type: str,
    target_id: str,
    level: str,
) -> list[str]:
    rows = _fetchall_safely(
        connection,
        """
        SELECT c.chunk_id, c.body
        FROM indexed_chunks c
        JOIN indexed_files f ON f.file_id = c.file_id
        WHERE c.workroot_id = ?
          AND f.workroot_id = ?
          AND f.source_type = ?
          AND f.source_id = ?
        """,
        (workroot_id, workroot_id, target_type, target_id),
    )
    return [
        f"release-derived index safety: indexed_chunks:{row[0]} exposes {level} target {target_type}:{target_id}"
        for row in rows
        if _has_non_placeholder_text(row[1])
    ] + [
        f"release-derived index safety: indexed_chunks_fts:{row[0]} exposes {level} target {target_type}:{target_id}"
        for row in _indexed_chunk_fts_rows(connection, workroot_id, target_type, target_id)
        if _has_non_placeholder_text(row[1])
    ]


def _leaky_context_recall_hints(
    connection: sqlite3.Connection,
    workroot_id: str,
    target_type: str,
    target_id: str,
    level: str,
) -> list[str]:
    rows = list(
        _fetchall_safely(
            connection,
            """
        SELECT hint_id, title, summary
        FROM context_recall_hints
        WHERE workroot_id = ? AND target_type = ? AND target_id = ?
        """,
            (workroot_id, target_type, target_id),
        )
    )
    if target_type == "context_recall_hint":
        rows.extend(
            _fetchall_safely(
                connection,
                """
                SELECT hint_id, title, summary
                FROM context_recall_hints
                WHERE workroot_id = ? AND hint_id = ?
                """,
                (workroot_id, target_id),
            )
        )
    return [
        f"release-derived index safety: context_recall_hints:{row[0]} exposes {level} target {target_type}:{target_id}"
        for row in rows
        if _has_non_placeholder_text(row[1], row[2])
    ] + [
        f"release-derived index safety: context_recall_hints_fts:{row[0]} exposes {level} target {target_type}:{target_id}"
        for row in _context_recall_hint_fts_rows(connection, workroot_id, target_type, target_id)
        if _has_non_placeholder_text(row[1], row[2])
    ]


def _context_candidate_fts_rows(
    connection: sqlite3.Connection,
    workroot_id: str,
    target_type: str,
    target_id: str,
) -> list[tuple[object, ...]]:
    rows = _fetchall_safely(
        connection,
        """
        SELECT f.candidate_id, f.title, f.summary
        FROM context_candidates_fts f
        JOIN context_candidates c ON c.candidate_id = f.candidate_id
        WHERE c.workroot_id = ? AND c.source_type = ? AND c.source_id = ?
        """,
        (workroot_id, target_type, target_id),
    )
    rows.extend(
        _fetchall_safely(
            connection,
            """
            SELECT f.candidate_id, f.title, f.summary
            FROM context_candidates_fts f
            JOIN context_candidates c ON c.candidate_id = f.candidate_id
            JOIN context_recall_hints h ON h.hint_id = c.source_id
            WHERE c.workroot_id = ?
              AND c.source_type = 'context_recall_hint'
              AND h.workroot_id = ?
              AND h.target_type = ?
              AND h.target_id = ?
            """,
            (workroot_id, workroot_id, target_type, target_id),
        )
    )
    return rows


def _indexed_chunk_fts_rows(
    connection: sqlite3.Connection,
    workroot_id: str,
    target_type: str,
    target_id: str,
) -> list[tuple[object, ...]]:
    return _fetchall_safely(
        connection,
        """
        SELECT fts.chunk_id, fts.body
        FROM indexed_chunks_fts fts
        JOIN indexed_chunks c ON c.chunk_id = fts.chunk_id
        JOIN indexed_files f ON f.file_id = c.file_id
        WHERE c.workroot_id = ?
          AND f.workroot_id = ?
          AND f.source_type = ?
          AND f.source_id = ?
        """,
        (workroot_id, workroot_id, target_type, target_id),
    )


def _context_recall_hint_fts_rows(
    connection: sqlite3.Connection,
    workroot_id: str,
    target_type: str,
    target_id: str,
) -> list[tuple[object, ...]]:
    rows = list(
        _fetchall_safely(
            connection,
            """
        SELECT f.hint_id, f.title, f.summary
        FROM context_recall_hints_fts f
        JOIN context_recall_hints h ON h.hint_id = f.hint_id
        WHERE h.workroot_id = ? AND h.target_type = ? AND h.target_id = ?
        """,
            (workroot_id, target_type, target_id),
        )
    )
    if target_type == "context_recall_hint":
        rows.extend(
            _fetchall_safely(
                connection,
                """
                SELECT f.hint_id, f.title, f.summary
                FROM context_recall_hints_fts f
                JOIN context_recall_hints h ON h.hint_id = f.hint_id
                WHERE h.workroot_id = ? AND h.hint_id = ?
                """,
                (workroot_id, target_id),
            )
        )
    return rows


def _fetchall_safely(
    connection: sqlite3.Connection,
    sql: str,
    params: tuple[object, ...] = (),
) -> list[tuple[object, ...]]:
    try:
        return connection.execute(sql, params).fetchall()
    except sqlite3.OperationalError:
        return []


def _fetch_one_safely(
    connection: sqlite3.Connection,
    sql: str,
    params: tuple[object, ...] = (),
) -> tuple[object, ...] | None:
    try:
        return connection.execute(sql, params).fetchone()
    except sqlite3.OperationalError:
        return None


def _has_non_placeholder_text(*values: object) -> bool:
    return any(str(value or "").strip() not in STRICT_RELEASE_PLACEHOLDERS for value in values)


def _normalize_strict_release_level(level: str) -> str:
    normalized = (level or "").lower().strip().replace("_", "-")
    if normalized == "sensitive":
        return "safety-sensitive"
    return normalized


def _most_protective_level(existing: str, incoming: str) -> str:
    order = {
        "deleted": 4,
        "redacted": 3,
        "safety-sensitive": 2,
        "none": 0,
        "": 0,
    }
    existing_level = _normalize_strict_release_level(existing)
    incoming_level = _normalize_strict_release_level(incoming)
    return incoming_level if order.get(incoming_level, 0) > order.get(existing_level, 0) else existing_level
