#!/usr/bin/env python3
"""SQLite cache, graph, candidate, and FTS schema helpers for AI Workroot."""

from __future__ import annotations

import sqlite3
from pathlib import Path


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
  last_used_at TEXT
);

CREATE VIRTUAL TABLE IF NOT EXISTS context_candidates_fts USING fts5(
  candidate_id,
  title,
  summary
);

CREATE INDEX IF NOT EXISTS idx_context_candidates_workroot ON context_candidates(workroot_id);
CREATE INDEX IF NOT EXISTS idx_context_candidates_status ON context_candidates(status);
CREATE INDEX IF NOT EXISTS idx_context_candidates_policy ON context_candidates(context_policy);
CREATE INDEX IF NOT EXISTS idx_context_candidates_importance ON context_candidates(importance);
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
    ]


def open_sqlite(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def initialize_workroot_sqlite(path: Path) -> None:
    with open_sqlite(path) as conn:
        conn.executescript(GRAPH_SCHEMA)
        conn.executescript(CANDIDATE_SCHEMA)
        conn.executescript(FTS_SCHEMA)
        conn.commit()


def sqlite_table_names(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type IN ('table', 'virtual table')").fetchall()
    return {row[0] for row in rows}


def verify_workroot_sqlite(path: Path) -> list[str]:
    if not path.exists():
        return [f"missing SQLite database: {path}"]
    issues: list[str] = []
    with sqlite3.connect(path) as conn:
        tables = sqlite_table_names(conn)
    for table in required_tables():
        if table not in tables:
            issues.append(f"missing SQLite table: {table}")
    return issues
