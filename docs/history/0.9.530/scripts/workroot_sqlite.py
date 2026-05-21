#!/usr/bin/env python3
"""Archived 0.9.529 SQLite helpers before package migration."""

from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA_MIGRATIONS = ("001-initial-schema", "002-context-candidate-use-count")


GRAPH_SCHEMA = """
CREATE TABLE IF NOT EXISTS graph_nodes (
  node_id TEXT PRIMARY KEY,
  node_type TEXT NOT NULL,
  kind TEXT,
  title TEXT,
  summary TEXT,
  status TEXT,
  importance TEXT,
  created_at TEXT,
  updated_at TEXT
);

CREATE TABLE IF NOT EXISTS graph_edges (
  edge_id TEXT PRIMARY KEY,
  from_node_id TEXT NOT NULL,
  to_node_id TEXT NOT NULL,
  relation TEXT NOT NULL,
  strength REAL,
  confidence REAL,
  status TEXT,
  created_at TEXT,
  updated_at TEXT
);

CREATE TABLE IF NOT EXISTS graph_edge_evidence (
  edge_id TEXT,
  evidence_type TEXT,
  relative_path TEXT,
  heading TEXT,
  snippet TEXT,
  source_id TEXT
);

CREATE INDEX IF NOT EXISTS idx_graph_edges_from ON graph_edges(from_node_id);
CREATE INDEX IF NOT EXISTS idx_graph_edges_to ON graph_edges(to_node_id);
CREATE INDEX IF NOT EXISTS idx_graph_edges_relation ON graph_edges(relation);
CREATE INDEX IF NOT EXISTS idx_graph_nodes_type ON graph_nodes(node_type);
"""

CANDIDATE_SCHEMA = """
CREATE TABLE IF NOT EXISTS context_candidates (
  candidate_id TEXT PRIMARY KEY,
  workroot_id TEXT NOT NULL,
  source_type TEXT NOT NULL,
  source_id TEXT NOT NULL,
  title TEXT,
  summary TEXT,
  domains TEXT,
  related_tasks TEXT,
  related_assets TEXT,
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

CREATE VIRTUAL TABLE IF NOT EXISTS context_candidates_fts USING fts5(
  candidate_id,
  title,
  summary,
  domains
);

CREATE INDEX IF NOT EXISTS idx_context_candidates_workroot ON context_candidates(workroot_id);
CREATE INDEX IF NOT EXISTS idx_context_candidates_status ON context_candidates(status);
CREATE INDEX IF NOT EXISTS idx_context_candidates_policy ON context_candidates(context_policy);
CREATE INDEX IF NOT EXISTS idx_context_candidates_importance ON context_candidates(importance);
"""

MANAGEMENT_SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
  task_id TEXT PRIMARY KEY,
  workroot_id TEXT NOT NULL,
  title TEXT,
  status TEXT,
  updated_at TEXT
);

CREATE TABLE IF NOT EXISTS assets (
  asset_id TEXT PRIMARY KEY,
  workroot_id TEXT NOT NULL,
  relative_path TEXT,
  title TEXT,
  status TEXT,
  updated_at TEXT
);

CREATE TABLE IF NOT EXISTS knowledge_items (
  knowledge_id TEXT PRIMARY KEY,
  workroot_id TEXT NOT NULL,
  title TEXT,
  summary TEXT,
  status TEXT,
  updated_at TEXT
);

CREATE TABLE IF NOT EXISTS domains (
  domain_id TEXT PRIMARY KEY,
  workroot_id TEXT NOT NULL,
  name TEXT,
  summary TEXT,
  status TEXT,
  updated_at TEXT
);

CREATE TABLE IF NOT EXISTS handoffs (
  handoff_id TEXT PRIMARY KEY,
  workroot_id TEXT NOT NULL,
  title TEXT,
  summary TEXT,
  status TEXT,
  updated_at TEXT
);

CREATE TABLE IF NOT EXISTS time_events (
  event_id TEXT PRIMARY KEY,
  workroot_id TEXT NOT NULL,
  event_type TEXT,
  occurred_at TEXT,
  summary TEXT
);
"""

FTS_SCHEMA = """
CREATE TABLE IF NOT EXISTS indexed_files (
  file_id TEXT PRIMARY KEY,
  workroot_id TEXT NOT NULL,
  relative_path TEXT NOT NULL,
  source_type TEXT NOT NULL,
  title TEXT,
  size_bytes INTEGER,
  modified_at TEXT,
  content_hash TEXT,
  indexed_at TEXT,
  status TEXT
);

CREATE TABLE IF NOT EXISTS indexed_chunks (
  chunk_id TEXT PRIMARY KEY,
  file_id TEXT NOT NULL,
  workroot_id TEXT NOT NULL,
  relative_path TEXT NOT NULL,
  heading TEXT,
  ordinal INTEGER,
  token_estimate INTEGER,
  content_hash TEXT,
  indexed_at TEXT
);

CREATE VIRTUAL TABLE IF NOT EXISTS indexed_chunks_fts USING fts5(
  chunk_id,
  title,
  heading,
  body
);
"""

MIGRATION_SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_migrations (
  migration_id TEXT PRIMARY KEY,
  applied_at TEXT NOT NULL
);
"""


def required_tables() -> list[str]:
    return [
        "graph_nodes",
        "graph_edges",
        "graph_edge_evidence",
        "context_candidates",
        "context_candidates_fts",
        "indexed_files",
        "indexed_chunks",
        "indexed_chunks_fts",
        "tasks",
        "assets",
        "knowledge_items",
        "domains",
        "handoffs",
        "time_events",
        "schema_migrations",
    ]


def open_sqlite(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA foreign_keys=ON")
    return connection


def initialize_workroot_sqlite(path: Path) -> None:
    with open_sqlite(path) as connection:
        connection.executescript(GRAPH_SCHEMA)
        connection.executescript(CANDIDATE_SCHEMA)
        ensure_context_candidate_columns(connection)
        connection.executescript(MANAGEMENT_SCHEMA)
        connection.executescript(FTS_SCHEMA)
        ensure_schema_migrations(connection)
        connection.commit()


def ensure_context_candidate_columns(connection: sqlite3.Connection) -> None:
    columns = {row[1] for row in connection.execute("PRAGMA table_info(context_candidates)").fetchall()}
    if "use_count" not in columns:
        connection.execute("ALTER TABLE context_candidates ADD COLUMN use_count INTEGER DEFAULT 0")


def ensure_schema_migrations(connection: sqlite3.Connection) -> None:
    connection.executescript(MIGRATION_SCHEMA)
    for migration_id in SCHEMA_MIGRATIONS:
        connection.execute(
            """
            INSERT OR IGNORE INTO schema_migrations (migration_id, applied_at)
            VALUES (?, datetime('now'))
            """,
            (migration_id,),
        )


def sqlite_table_names(connection: sqlite3.Connection) -> set[str]:
    rows = connection.execute("SELECT name FROM sqlite_master WHERE type IN ('table', 'virtual table')").fetchall()
    return {row[0] for row in rows}


def verify_workroot_sqlite(path: Path) -> list[str]:
    if not path.exists():
        return [f"missing SQLite database: {path}"]
    issues: list[str] = []
    with sqlite3.connect(path) as connection:
        tables = sqlite_table_names(connection)
    for table in required_tables():
        if table not in tables:
            issues.append(f"missing SQLite table: {table}")
    return issues
