from __future__ import annotations

import os
import json
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from scripts.workroot_candidates import ContextCandidate, upsert_context_candidate
from scripts.workroot_context import (
    ContextRequest,
    build_candidate_pool,
    build_context_package,
    estimate_context_package_tokens,
    load_context_guide_config,
)
from scripts.workroot_indexing import index_text_file
from scripts.workroot_paths import workroot_sqlite_path
from scripts.workroot_sqlite import initialize_workroot_sqlite, open_sqlite
from scripts.workroot_state import initialize_workroot_state, write_json


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts/workroot_cli.py"


class WorkrootContextTest(unittest.TestCase):
    def create_fixture(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        base = Path(tmp.name)
        home = base / "home"
        user_dir = base / "project"
        user_dir.mkdir()
        initialized = initialize_workroot_state(
            home,
            "wr_demo",
            "Demo",
            user_dir,
            now="2026-05-19T00:00:00Z",
        )
        write_json(
            initialized.state_directory / "state/current.json",
            {
                "currentFocus": "Ship Clean Mode and local Context Guide.",
                "activeTaskId": "task-1",
                "nextSuggestedAction": "Run doctor and context verification.",
                "contextVersion": 1,
                "lastActivityAt": "2026-05-19T00:00:00Z",
            },
        )
        db_path = workroot_sqlite_path(initialized.state_directory)
        initialize_workroot_sqlite(db_path)
        with open_sqlite(db_path) as conn:
            upsert_context_candidate(
                conn,
                ContextCandidate(
                    candidate_id="cand_clean_mode",
                    workroot_id="wr_demo",
                    source_type="decision",
                    source_id="decision-1",
                    title="Clean Mode decision",
                    summary="Managed state stays outside user-selected directories.",
                    importance="high",
                    confidence=0.95,
                    context_policy="always",
                    token_estimate=12,
                    updated_at="2026-05-19T00:00:00Z",
                ),
            )
            upsert_context_candidate(
                conn,
                ContextCandidate(
                    candidate_id="cand_stale",
                    workroot_id="wr_demo",
                    source_type="decision",
                    source_id="decision-old",
                    title="Stale decision",
                    summary="Old behavior.",
                    status="stale",
                    updated_at="2026-05-19T00:00:00Z",
                ),
            )
            upsert_context_candidate(
                conn,
                ContextCandidate(
                    candidate_id="cand_never",
                    workroot_id="wr_demo",
                    source_type="knowledge",
                    source_id="secret-1",
                    title="Manual only private note",
                    summary="Do not include automatically.",
                    context_policy="never-auto",
                    updated_at="2026-05-19T00:00:00Z",
                ),
            )
            doc = user_dir / "notes.md"
            doc.write_text(
                "# Retrieval Notes\nLocal FTS should explain why clean mode context was selected.\n",
                encoding="utf-8",
            )
            index_text_file(conn, "wr_demo", user_dir, doc, indexed_at="2026-05-19T00:00:00Z")
            conn.execute(
                """
                INSERT INTO graph_nodes (
                  node_id, node_type, kind, title, summary, status, importance, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "decision-1",
                    "decision",
                    "architecture",
                    "Clean Mode",
                    "Clean Mode protects user directories.",
                    "active",
                    "high",
                    "2026-05-19T00:00:00Z",
                    "2026-05-19T00:00:00Z",
                ),
            )
            conn.execute(
                """
                INSERT INTO graph_nodes (
                  node_id, node_type, kind, title, summary, status, importance, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "clean-mode-signal",
                    "knowledge",
                    "context",
                    "Clean Mode signal",
                    "Clean Mode protects user directories.",
                    "active",
                    "high",
                    "2026-05-19T00:00:00Z",
                    "2026-05-19T00:00:00Z",
                ),
            )
            conn.execute(
                """
                INSERT INTO graph_edges (
                  edge_id, from_node_id, to_node_id, relation, strength, confidence, status, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "edge-clean-mode-task",
                    "decision-1",
                    "clean-mode-signal",
                    "supports",
                    1.0,
                    0.9,
                    "active",
                    "2026-05-19T00:00:00Z",
                    "2026-05-19T00:00:00Z",
                ),
            )
            conn.commit()
        return home, user_dir, initialized.state_directory

    def test_build_context_package_uses_local_state_candidates_fts_and_graph(self) -> None:
        home, user_dir, state_dir = self.create_fixture()

        package = build_context_package(
            ContextRequest(
                home=home,
                agent="codex",
                cwd=user_dir,
                query="clean mode",
                now="2026-05-19T00:00:00Z",
            )
        )

        self.assertIn("# AI Workroot Context Package", package.markdown)
        self.assertIn("## Context Metadata", package.markdown)
        self.assertIn("Mode: standard", package.markdown)
        self.assertIn("Confidence: high", package.markdown)
        self.assertIn("Tokens:", package.markdown)
        self.assertIn("## Current State", package.markdown)
        self.assertIn("Ship Clean Mode", package.markdown)
        self.assertIn("## Selected Context", package.markdown)
        self.assertIn("Clean Mode decision", package.markdown)
        self.assertIn("## FTS Matches", package.markdown)
        self.assertIn("notes.md", package.markdown)
        self.assertIn("## Graph Signals", package.markdown)
        self.assertIn("Clean Mode protects user directories", package.markdown)
        self.assertNotIn("Stale decision", package.markdown)
        self.assertNotIn("Manual only private note", package.markdown)
        self.assertTrue((state_dir / "context/packages/latest.md").exists())
        self.assertFalse((user_dir / ".workroot").exists())
        self.assertFalse((user_dir / ".ai-workroot").exists())
        self.assertFalse((user_dir / "context").exists())

    def test_fts_match_promotes_related_context_candidate(self) -> None:
        home, user_dir, state_dir = self.create_fixture()
        db_path = workroot_sqlite_path(state_dir)
        with open_sqlite(db_path) as conn:
            upsert_context_candidate(
                conn,
                ContextCandidate(
                    candidate_id="cand_query_match",
                    workroot_id="wr_demo",
                    source_type="knowledge",
                    source_id="knowledge-query",
                    title="Query specific retrieval",
                    summary="This summary is found only through context candidate FTS.",
                    domains="rare-domain",
                    importance="low",
                    confidence=0.8,
                    context_policy="on-demand",
                    token_estimate=6,
                    updated_at="2026-05-19T00:00:00Z",
                ),
            )

        package = build_context_package(
            ContextRequest(
                home=home,
                agent="codex",
                cwd=user_dir,
                query="rare-domain",
                now="2026-05-19T00:00:00Z",
            )
        )

        selected = {item["candidateId"]: item for item in package.trace["selectedCandidates"]}
        self.assertIn("cand_query_match", selected)
        self.assertIn("candidate-fts-match", selected["cand_query_match"]["reasons"])

    def test_candidate_fts_keeps_unquoted_hits_when_phrase_fallback_is_empty(self) -> None:
        home, user_dir, state_dir = self.create_fixture()
        db_path = workroot_sqlite_path(state_dir)
        with open_sqlite(db_path) as conn:
            upsert_context_candidate(
                conn,
                ContextCandidate(
                    candidate_id="cand_accumulated_fts",
                    workroot_id="wr_demo",
                    source_type="knowledge",
                    source_id="knowledge-accumulated-fts",
                    title="Separated candidate query terms",
                    summary="alpha appears before several filler words and beta appears later.",
                    importance="low",
                    confidence=0.8,
                    context_policy="on-demand",
                    token_estimate=6,
                    updated_at="2026-05-19T00:00:00Z",
                ),
            )

        package = build_context_package(
            ContextRequest(
                home=home,
                agent="codex",
                cwd=user_dir,
                query="alpha beta",
                now="2026-05-19T00:00:00Z",
            )
        )

        selected = {item["candidateId"]: item for item in package.trace["selectedCandidates"]}
        self.assertIn("cand_accumulated_fts", selected)
        self.assertIn("candidate-fts-match", selected["cand_accumulated_fts"]["reasons"])

    def test_context_does_not_require_loading_all_candidates_for_large_candidate_set(self) -> None:
        home, user_dir, state_dir = self.create_fixture()
        db_path = workroot_sqlite_path(state_dir)
        with open_sqlite(db_path) as conn:
            for i in range(260):
                upsert_context_candidate(
                    conn,
                    ContextCandidate(
                        candidate_id=f"cand_bulk_{i:03d}",
                        workroot_id="wr_demo",
                        source_type="knowledge",
                        source_id=f"knowledge-bulk-{i:03d}",
                        title=f"Bulk candidate {i:03d}",
                        summary="Large Workroot filler candidate.",
                        importance="low",
                        confidence=0.2,
                        context_policy="task-related",
                        token_estimate=2,
                        updated_at=f"2026-05-19T00:{i % 60:02d}:00Z",
                    ),
                )

        package = build_context_package(
            ContextRequest(home=home, agent="codex", cwd=user_dir, query="clean mode", now="2026-05-19T00:00:00Z")
        )

        self.assertLessEqual(package.trace["candidatePool"]["size"], 200)
        self.assertEqual(package.trace["candidatePool"]["strategy"], "bounded-sql-pool")
        self.assertGreater(package.trace["candidateQuality"]["totalAvailable"], package.trace["candidatePool"]["size"])

    def test_context_candidate_pool_is_bounded_for_large_workroot(self) -> None:
        home, user_dir, state_dir = self.create_fixture()
        db_path = workroot_sqlite_path(state_dir)
        with open_sqlite(db_path) as conn:
            for i in range(1000):
                upsert_context_candidate(
                    conn,
                    ContextCandidate(
                        candidate_id=f"cand_large_{i:04d}",
                        workroot_id="wr_demo",
                        source_type="knowledge",
                        source_id=f"knowledge-large-{i:04d}",
                        title=f"Large candidate {i:04d}",
                        summary="Bounded candidate pool filler.",
                        importance="low",
                        confidence=0.1,
                        context_policy="task-related",
                        token_estimate=1,
                        updated_at=f"2026-05-19T00:{i % 60:02d}:00Z",
                    ),
                )

        package = build_context_package(
            ContextRequest(home=home, agent="codex", cwd=user_dir, query="", now="2026-05-19T00:00:00Z")
        )

        self.assertLessEqual(package.trace["candidatePool"]["size"], 200)
        self.assertEqual(package.trace["candidatePool"]["maxInitialCandidates"], 200)

    def test_fts_candidates_are_included_even_when_not_in_recent_top_candidates(self) -> None:
        home, user_dir, state_dir = self.create_fixture()
        db_path = workroot_sqlite_path(state_dir)
        with open_sqlite(db_path) as conn:
            for i in range(230):
                upsert_context_candidate(
                    conn,
                    ContextCandidate(
                        candidate_id=f"cand_recent_{i:03d}",
                        workroot_id="wr_demo",
                        source_type="knowledge",
                        source_id=f"knowledge-recent-{i:03d}",
                        title=f"Recent candidate {i:03d}",
                        summary="Recent filler.",
                        importance="normal",
                        confidence=0.6,
                        context_policy="task-related",
                        token_estimate=2,
                        updated_at=f"2026-05-19T01:{i % 60:02d}:00Z",
                    ),
                )
            upsert_context_candidate(
                conn,
                ContextCandidate(
                    candidate_id="cand_rare_fts",
                    workroot_id="wr_demo",
                    source_type="knowledge",
                    source_id="knowledge-rare-fts",
                    title="Rare bounded pool result",
                    summary="The only candidate containing ultrararekeyword.",
                    importance="low",
                    confidence=0.8,
                    context_policy="on-demand",
                    token_estimate=4,
                    updated_at="2020-01-01T00:00:00Z",
                ),
            )

        package = build_context_package(
            ContextRequest(home=home, agent="codex", cwd=user_dir, query="ultrararekeyword", now="2026-05-19T00:00:00Z")
        )

        selected = {item["candidateId"]: item for item in package.trace["selectedCandidates"]}
        self.assertIn("cand_rare_fts", selected)
        self.assertIn("candidate-fts-match", selected["cand_rare_fts"]["reasons"])

    def test_explicit_candidate_is_not_starved_by_many_always_candidates(self) -> None:
        home, _user_dir, state_dir = self.create_fixture()
        db_path = workroot_sqlite_path(state_dir)
        with open_sqlite(db_path) as conn:
            for i in range(12):
                upsert_context_candidate(
                    conn,
                    ContextCandidate(
                        candidate_id=f"cand_always_starve_{i:02d}",
                        workroot_id="wr_demo",
                        source_type="knowledge",
                        source_id=f"knowledge-always-starve-{i:02d}",
                        title=f"Always filler {i:02d}",
                        summary="Always filler candidate.",
                        importance="normal",
                        confidence=0.6,
                        context_policy="always",
                        token_estimate=1,
                        updated_at=f"2026-05-19T00:{i:02d}:00Z",
                    ),
                )
            upsert_context_candidate(
                conn,
                ContextCandidate(
                    candidate_id="cand_explicit_starved",
                    workroot_id="wr_demo",
                    source_type="knowledge",
                    source_id="knowledge-explicit-starved",
                    title="Explicit match",
                    summary="Explicit candidate must enter bounded pool.",
                    importance="low",
                    confidence=0.5,
                    context_policy="on-demand",
                    token_estimate=1,
                    updated_at="2020-01-01T00:00:00Z",
                ),
            )

            candidates, pool = build_candidate_pool(
                conn,
                "wr_demo",
                {"activeTaskId": ""},
                {"cand_explicit_starved"},
                set(),
                set(),
                max_initial_candidates=5,
            )

        self.assertEqual(pool["maxInitialCandidates"], 5)
        self.assertIn("cand_explicit_starved", {candidate.candidate_id for candidate in candidates})

    def test_graph_candidate_is_not_starved_by_many_always_candidates(self) -> None:
        home, _user_dir, state_dir = self.create_fixture()
        db_path = workroot_sqlite_path(state_dir)
        with open_sqlite(db_path) as conn:
            for i in range(12):
                upsert_context_candidate(
                    conn,
                    ContextCandidate(
                        candidate_id=f"cand_graph_always_starve_{i:02d}",
                        workroot_id="wr_demo",
                        source_type="knowledge",
                        source_id=f"knowledge-graph-always-starve-{i:02d}",
                        title=f"Graph always filler {i:02d}",
                        summary="Always filler candidate.",
                        importance="normal",
                        confidence=0.6,
                        context_policy="always",
                        token_estimate=1,
                        updated_at=f"2026-05-19T00:{i:02d}:00Z",
                    ),
                )
            upsert_context_candidate(
                conn,
                ContextCandidate(
                    candidate_id="cand_graph_starved",
                    workroot_id="wr_demo",
                    source_type="knowledge",
                    source_id="knowledge-graph-starved",
                    title="Graph match",
                    summary="Graph candidate must enter bounded pool.",
                    importance="low",
                    confidence=0.5,
                    context_policy="on-demand",
                    token_estimate=1,
                    updated_at="2020-01-01T00:00:00Z",
                ),
            )

            candidates, _pool = build_candidate_pool(
                conn,
                "wr_demo",
                {"activeTaskId": ""},
                set(),
                set(),
                {"cand_graph_starved"},
                max_initial_candidates=5,
            )

        self.assertIn("cand_graph_starved", {candidate.candidate_id for candidate in candidates})

    def test_always_candidates_are_included_even_when_candidate_pool_is_bounded(self) -> None:
        home, user_dir, state_dir = self.create_fixture()
        db_path = workroot_sqlite_path(state_dir)
        with open_sqlite(db_path) as conn:
            for i in range(260):
                upsert_context_candidate(
                    conn,
                    ContextCandidate(
                        candidate_id=f"cand_recent_always_test_{i:03d}",
                        workroot_id="wr_demo",
                        source_type="knowledge",
                        source_id=f"knowledge-recent-always-test-{i:03d}",
                        title=f"Recent always test filler {i:03d}",
                        summary="Recent filler.",
                        importance="normal",
                        confidence=0.6,
                        context_policy="task-related",
                        token_estimate=2,
                        updated_at=f"2026-05-19T02:{i % 60:02d}:00Z",
                    ),
                )
            upsert_context_candidate(
                conn,
                ContextCandidate(
                    candidate_id="cand_old_always",
                    workroot_id="wr_demo",
                    source_type="decision",
                    source_id="decision-old-always",
                    title="Old always rule",
                    summary="Always candidates must survive bounded pooling.",
                    importance="low",
                    confidence=0.8,
                    context_policy="always",
                    token_estimate=4,
                    updated_at="2020-01-01T00:00:00Z",
                ),
            )

        package = build_context_package(
            ContextRequest(home=home, agent="codex", cwd=user_dir, query="", now="2026-05-19T00:00:00Z")
        )

        selected_ids = {item["candidateId"] for item in package.trace["selectedCandidates"]}
        self.assertIn("cand_old_always", selected_ids)

    def test_blocked_safety_candidates_do_not_starve_safe_candidates_from_pool(self) -> None:
        home, user_dir, state_dir = self.create_fixture()
        db_path = workroot_sqlite_path(state_dir)
        with open_sqlite(db_path) as conn:
            for i in range(205):
                upsert_context_candidate(
                    conn,
                    ContextCandidate(
                        candidate_id=f"cand_blocked_starve_{i:03d}",
                        workroot_id="wr_demo",
                        source_type="knowledge",
                        source_id=f"knowledge-blocked-starve-{i:03d}",
                        title=f"Blocked starve filler {i:03d}",
                        summary="Blocked safety candidates must not occupy the auto-selection pool.",
                        importance="critical",
                        confidence=1.0,
                        context_policy="always",
                        safety_policy="sensitive",
                        token_estimate=1,
                        updated_at=f"2026-05-19T03:{i % 60:02d}:00Z",
                    ),
                )
            upsert_context_candidate(
                conn,
                ContextCandidate(
                    candidate_id="cand_safe_not_starved",
                    workroot_id="wr_demo",
                    source_type="knowledge",
                    source_id="knowledge-safe-not-starved",
                    title="Safe not starved",
                    summary="Safe candidate should remain eligible even when blocked candidates are numerous.",
                    importance="low",
                    confidence=0.5,
                    context_policy="task-related",
                    token_estimate=1,
                    updated_at="2020-01-01T00:00:00Z",
                ),
            )

        package = build_context_package(
            ContextRequest(home=home, agent="codex", cwd=user_dir, query="", debug=True, now="2026-05-19T00:00:00Z")
        )

        selected_ids = {item["candidateId"] for item in package.trace["selectedCandidates"]}
        pool = package.trace["candidatePool"]
        dropped = {item["candidateId"]: item["reason"] for item in package.trace["droppedCandidates"]}
        self.assertIn("cand_safe_not_starved", selected_ids)
        self.assertEqual(pool["totalAvailable"], 209)
        self.assertFalse(any(candidate_id.startswith("cand_blocked_starve_") for candidate_id in selected_ids))
        self.assertIn("safety-sensitive", set(dropped.values()))

    def test_graph_signals_are_related_to_selected_candidates(self) -> None:
        home, user_dir, state_dir = self.create_fixture()
        db_path = workroot_sqlite_path(state_dir)
        with open_sqlite(db_path) as conn:
            conn.execute(
                """
                INSERT INTO graph_nodes (
                  node_id, node_type, kind, title, summary, status, importance, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "unrelated-critical",
                    "decision",
                    "architecture",
                    "Unrelated critical node",
                    "This high priority node is unrelated and should not appear.",
                    "active",
                    "critical",
                    "2026-05-19T00:00:00Z",
                    "2026-05-19T00:00:00Z",
                ),
            )
            conn.execute(
                """
                INSERT INTO graph_edges (
                  edge_id, from_node_id, to_node_id, relation, strength, confidence, status, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "edge-clean-task",
                    "decision-1",
                    "task-1",
                    "belongs_to_task",
                    1.0,
                    0.9,
                    "active",
                    "2026-05-19T00:00:00Z",
                    "2026-05-19T00:00:00Z",
                ),
            )
            conn.execute(
                """
                INSERT INTO graph_nodes (
                  node_id, node_type, kind, title, summary, status, importance, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "task-1",
                    "task",
                    "work",
                    "Clean Mode task",
                    "Task linked by one-hop graph edge.",
                    "active",
                    "normal",
                    "2026-05-19T00:00:00Z",
                    "2026-05-19T00:00:00Z",
                ),
            )
            conn.commit()

        package = build_context_package(
            ContextRequest(
                home=home,
                agent="codex",
                cwd=user_dir,
                query="clean mode",
                now="2026-05-19T00:00:00Z",
            )
        )

        titles = {signal["title"] for signal in package.trace["graphSignals"]}
        self.assertIn("Clean Mode task", titles)
        self.assertNotIn("Unrelated critical node", titles)

    def test_graph_signals_do_not_use_broad_focus_terms_for_unrelated_nodes(self) -> None:
        home, user_dir, state_dir = self.create_fixture()
        write_json(
            state_dir / "state/current.json",
            {
                "currentFocus": "Clean Mode local Context Guide review.",
                "activeTaskId": "task-1",
                "nextSuggestedAction": "Review context output.",
                "contextVersion": 1,
                "lastActivityAt": "2026-05-19T00:00:00Z",
            },
        )
        db_path = workroot_sqlite_path(state_dir)
        with open_sqlite(db_path) as conn:
            conn.execute(
                """
                INSERT INTO graph_nodes (
                  node_id, node_type, kind, title, summary, status, importance, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "unrelated-critical",
                    "decision",
                    "architecture",
                    "Unrelated critical context node",
                    "This unrelated node contains context and should not appear without a related edge.",
                    "active",
                    "critical",
                    "2026-05-19T00:00:00Z",
                    "2026-05-19T00:00:00Z",
                ),
            )
            conn.commit()

        package = build_context_package(
            ContextRequest(
                home=home,
                agent="codex",
                cwd=user_dir,
                now="2026-05-19T00:00:00Z",
            )
        )

        titles = {signal["title"] for signal in package.trace["graphSignals"]}
        self.assertNotIn("Unrelated critical context node", titles)

    def test_graph_query_only_weak_match_does_not_enter_context(self) -> None:
        home, user_dir, state_dir = self.create_fixture()
        db_path = workroot_sqlite_path(state_dir)
        with open_sqlite(db_path) as conn:
            conn.execute(
                """
                INSERT INTO graph_nodes (
                  node_id, node_type, kind, title, summary, status, importance, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "query-only-node",
                    "knowledge",
                    "context",
                    "Clean Mode query-only graph node",
                    "This broad query match has no relation-backed edge.",
                    "active",
                    "critical",
                    "2026-05-19T00:00:00Z",
                    "2026-05-19T00:00:00Z",
                ),
            )
            conn.commit()

        package = build_context_package(
            ContextRequest(home=home, agent="codex", cwd=user_dir, query="Clean Mode", now="2026-05-19T00:00:00Z")
        )

        titles = {signal["title"] for signal in package.trace["graphSignals"]}
        self.assertNotIn("Clean Mode query-only graph node", titles)

    def test_graph_query_match_requires_relation_backing_for_context_signal(self) -> None:
        home, user_dir, state_dir = self.create_fixture()
        db_path = workroot_sqlite_path(state_dir)
        with open_sqlite(db_path) as conn:
            conn.execute(
                """
                INSERT INTO graph_nodes (
                  node_id, node_type, kind, title, summary, status, importance, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "relation-backed-query-node",
                    "knowledge",
                    "context",
                    "Clean Mode relation-backed graph node",
                    "This query match is relation-backed by a selected source.",
                    "active",
                    "high",
                    "2026-05-19T00:00:00Z",
                    "2026-05-19T00:00:00Z",
                ),
            )
            conn.execute(
                """
                INSERT INTO graph_edges (
                  edge_id, from_node_id, to_node_id, relation, strength, confidence, status, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "edge-relation-backed-query",
                    "decision-1",
                    "relation-backed-query-node",
                    "supports",
                    1.0,
                    0.9,
                    "active",
                    "2026-05-19T00:00:00Z",
                    "2026-05-19T00:00:00Z",
                ),
            )
            conn.commit()

        package = build_context_package(
            ContextRequest(home=home, agent="codex", cwd=user_dir, query="Clean Mode", now="2026-05-19T00:00:00Z")
        )

        titles = {signal["title"] for signal in package.trace["graphSignals"]}
        self.assertIn("Clean Mode relation-backed graph node", titles)

    def test_graph_one_hop_match_promotes_candidate_selection(self) -> None:
        home, user_dir, state_dir = self.create_fixture()
        hints = json.loads((state_dir / "state/runtime-hints.json").read_text(encoding="utf-8"))
        hints["contextGuide"]["agentBudgets"]["codex"]["targetTokens"] = 5
        (state_dir / "state/runtime-hints.json").write_text(json.dumps(hints, ensure_ascii=False, indent=2), encoding="utf-8")
        db_path = workroot_sqlite_path(state_dir)
        with open_sqlite(db_path) as conn:
            upsert_context_candidate(
                conn,
                ContextCandidate(
                    candidate_id="cand_unrelated",
                    workroot_id="wr_demo",
                    source_type="knowledge",
                    source_id="knowledge-unrelated",
                    title="Unrelated normal context",
                    summary="This candidate has a stronger base score but no graph relation.",
                    importance="normal",
                    confidence=0.8,
                    context_policy="task-related",
                    token_estimate=5,
                    updated_at="2026-05-19T00:00:00Z",
                ),
            )
            upsert_context_candidate(
                conn,
                ContextCandidate(
                    candidate_id="cand_graph_task",
                    workroot_id="wr_demo",
                    source_type="decision",
                    source_id="decision-task-related",
                    title="Task graph context",
                    summary="This candidate is related through a one-hop active task graph edge.",
                    importance="low",
                    confidence=0.8,
                    context_policy="on-demand",
                    token_estimate=5,
                    updated_at="2026-05-19T00:00:00Z",
                ),
            )
            conn.execute(
                """
                INSERT INTO graph_nodes (
                  node_id, node_type, kind, title, summary, status, importance, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "decision-task-related",
                    "decision",
                    "architecture",
                    "Task related graph node",
                    "Graph node connected to the active task.",
                    "active",
                    "low",
                    "2026-05-19T00:00:00Z",
                    "2026-05-19T00:00:00Z",
                ),
            )
            conn.execute(
                """
                INSERT INTO graph_edges (
                  edge_id, from_node_id, to_node_id, relation, strength, confidence, status, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "edge-task-related-decision",
                    "decision-task-related",
                    "task-1",
                    "belongs_to_task",
                    1.0,
                    0.9,
                    "active",
                    "2026-05-19T00:00:00Z",
                    "2026-05-19T00:00:00Z",
                ),
            )
            conn.commit()

        package = build_context_package(
            ContextRequest(
                home=home,
                agent="codex",
                cwd=user_dir,
                query="",
                mode="fast",
                target_token_budget=5,
                now="2026-05-19T00:00:00Z",
            )
        )

        selected = {item["candidateId"]: item for item in package.trace["selectedCandidates"]}
        self.assertIn("cand_graph_task", selected)
        self.assertIn("graph-one-hop-match", selected["cand_graph_task"]["reasons"])
        self.assertNotIn("cand_unrelated", selected)

    def test_graph_expansion_uses_source_id_when_candidate_id_differs(self) -> None:
        home, user_dir, state_dir = self.create_fixture()
        hints = json.loads((state_dir / "state/runtime-hints.json").read_text(encoding="utf-8"))
        hints["contextGuide"]["agentBudgets"]["codex"]["targetTokens"] = 5
        (state_dir / "state/runtime-hints.json").write_text(json.dumps(hints, ensure_ascii=False, indent=2), encoding="utf-8")
        db_path = workroot_sqlite_path(state_dir)
        with open_sqlite(db_path) as conn:
            upsert_context_candidate(
                conn,
                ContextCandidate(
                    candidate_id="cand_source_seed",
                    workroot_id="wr_demo",
                    source_type="decision",
                    source_id="decision-source-seed",
                    title="Source seed",
                    summary="ultra_source_seed should seed graph by source ID.",
                    importance="low",
                    confidence=0.9,
                    context_policy="on-demand",
                    token_estimate=5,
                    updated_at="2026-05-19T00:00:00Z",
                ),
            )
            upsert_context_candidate(
                conn,
                ContextCandidate(
                    candidate_id="cand_source_neighbor",
                    workroot_id="wr_demo",
                    source_type="knowledge",
                    source_id="knowledge-source-neighbor",
                    title="Source neighbor",
                    summary="Candidate connected through the source ID edge.",
                    importance="low",
                    confidence=0.9,
                    context_policy="on-demand",
                    token_estimate=5,
                    updated_at="2026-05-19T00:00:00Z",
                ),
            )
            conn.execute(
                """
                INSERT INTO graph_edges (
                  edge_id, from_node_id, to_node_id, relation, strength, confidence, status, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "edge-source-to-neighbor",
                    "decision-source-seed",
                    "knowledge-source-neighbor",
                    "supports",
                    1.0,
                    0.9,
                    "active",
                    "2026-05-19T00:00:00Z",
                    "2026-05-19T00:00:00Z",
                ),
            )
            conn.commit()

        package = build_context_package(
            ContextRequest(
                home=home,
                agent="codex",
                cwd=user_dir,
                query="ultra_source_seed",
                mode="fast",
                target_token_budget=10,
                now="2026-05-19T00:00:00Z",
            )
        )

        selected = {item["candidateId"]: item for item in package.trace["selectedCandidates"]}
        self.assertIn("cand_source_neighbor", selected)
        self.assertIn("graph-one-hop-match", selected["cand_source_neighbor"]["reasons"])

    def test_graph_expansion_uses_active_task_id(self) -> None:
        home, user_dir, state_dir = self.create_fixture()
        db_path = workroot_sqlite_path(state_dir)
        with open_sqlite(db_path) as conn:
            upsert_context_candidate(
                conn,
                ContextCandidate(
                    candidate_id="cand_active_task_edge",
                    workroot_id="wr_demo",
                    source_type="decision",
                    source_id="decision-active-task-edge",
                    title="Active task edge context",
                    summary="Candidate connected directly to active task.",
                    importance="low",
                    confidence=0.8,
                    context_policy="on-demand",
                    token_estimate=5,
                    updated_at="2026-05-19T00:00:00Z",
                ),
            )
            conn.execute(
                """
                INSERT INTO graph_edges (
                  edge_id, from_node_id, to_node_id, relation, strength, confidence, status, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "edge-active-task-context",
                    "decision-active-task-edge",
                    "task-1",
                    "belongs_to_task",
                    1.0,
                    0.9,
                    "active",
                    "2026-05-19T00:00:00Z",
                    "2026-05-19T00:00:00Z",
                ),
            )
            conn.commit()

        package = build_context_package(
            ContextRequest(home=home, agent="codex", cwd=user_dir, query="", mode="fast", target_token_budget=20, now="2026-05-19T00:00:00Z")
        )

        selected = {item["candidateId"]: item for item in package.trace["selectedCandidates"]}
        self.assertIn("cand_active_task_edge", selected)
        self.assertIn("graph-one-hop-match", selected["cand_active_task_edge"]["reasons"])

    def test_graph_signal_boosts_candidate_connected_by_source_id(self) -> None:
        home, user_dir, state_dir = self.create_fixture()
        db_path = workroot_sqlite_path(state_dir)
        with open_sqlite(db_path) as conn:
            upsert_context_candidate(
                conn,
                ContextCandidate(
                    candidate_id="cand_signal_source",
                    workroot_id="wr_demo",
                    source_type="decision",
                    source_id="decision-signal-source",
                    title="Signal source",
                    summary="signal_source_query should seed a graph edge.",
                    importance="low",
                    confidence=0.9,
                    context_policy="on-demand",
                    token_estimate=5,
                    updated_at="2026-05-19T00:00:00Z",
                ),
            )
            conn.execute(
                """
                INSERT INTO graph_nodes (
                  node_id, node_type, kind, title, summary, status, importance, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "knowledge-signal-neighbor",
                    "knowledge",
                    "context",
                    "Signal neighbor node",
                    "Graph signal connected by source ID.",
                    "active",
                    "high",
                    "2026-05-19T00:00:00Z",
                    "2026-05-19T00:00:00Z",
                ),
            )
            conn.execute(
                """
                INSERT INTO graph_edges (
                  edge_id, from_node_id, to_node_id, relation, strength, confidence, status, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "edge-signal-source",
                    "decision-signal-source",
                    "knowledge-signal-neighbor",
                    "supports",
                    1.0,
                    0.9,
                    "active",
                    "2026-05-19T00:00:00Z",
                    "2026-05-19T00:00:00Z",
                ),
            )
            conn.commit()

        package = build_context_package(
            ContextRequest(home=home, agent="codex", cwd=user_dir, query="signal_source_query", now="2026-05-19T00:00:00Z")
        )

        titles = {signal["title"] for signal in package.trace["graphSignals"]}
        self.assertIn("Signal neighbor node", titles)

    def test_graph_signals_exclude_selected_node_pseudo_signals(self) -> None:
        home, user_dir, state_dir = self.create_fixture()

        package = build_context_package(
            ContextRequest(home=home, agent="codex", cwd=user_dir, query="clean mode", debug=True, now="2026-05-19T00:00:00Z")
        )

        relations = {signal.get("relation") for signal in package.trace["graphSignals"]}
        self.assertNotIn("selected-node", relations)
        self.assertIn("graphSeedExplanations", package.trace)

    def test_context_candidate_safety_never_auto_is_dropped(self) -> None:
        home, user_dir, state_dir = self.create_fixture()
        db_path = workroot_sqlite_path(state_dir)
        with open_sqlite(db_path) as conn:
            upsert_context_candidate(
                conn,
                ContextCandidate(
                    candidate_id="cand_safety_never",
                    workroot_id="wr_demo",
                    source_type="knowledge",
                    source_id="knowledge-safety-never",
                    title="Safety never auto",
                    summary="This safety-blocked item must not enter context.",
                    importance="critical",
                    confidence=1.0,
                    context_policy="always",
                    safety_policy="never-auto",
                    token_estimate=5,
                    updated_at="2026-05-19T00:00:00Z",
                ),
            )

        package = build_context_package(
            ContextRequest(home=home, agent="codex", cwd=user_dir, query="safety", now="2026-05-19T00:00:00Z")
        )

        selected_ids = {item["candidateId"] for item in package.trace["selectedCandidates"]}
        dropped = {item["candidateId"]: item["reason"] for item in package.trace["droppedCandidates"]}
        self.assertNotIn("cand_safety_never", selected_ids)
        self.assertEqual(dropped["cand_safety_never"], "safety-never-auto")
        self.assertNotIn("Safety never auto", package.markdown)

    def test_context_candidate_needs_confirmation_is_dropped_by_default(self) -> None:
        home, user_dir, state_dir = self.create_fixture()
        db_path = workroot_sqlite_path(state_dir)
        with open_sqlite(db_path) as conn:
            upsert_context_candidate(
                conn,
                ContextCandidate(
                    candidate_id="cand_needs_confirmation",
                    workroot_id="wr_demo",
                    source_type="knowledge",
                    source_id="knowledge-needs-confirmation",
                    title="Needs confirmation",
                    summary="This item requires explicit user confirmation.",
                    importance="critical",
                    confidence=1.0,
                    context_policy="always",
                    safety_policy="needs-confirmation",
                    token_estimate=5,
                    updated_at="2026-05-19T00:00:00Z",
                ),
            )

        package = build_context_package(
            ContextRequest(home=home, agent="codex", cwd=user_dir, query="confirmation", now="2026-05-19T00:00:00Z")
        )

        dropped = {item["candidateId"]: item["reason"] for item in package.trace["droppedCandidates"]}
        self.assertEqual(dropped["cand_needs_confirmation"], "safety-needs-confirmation")
        self.assertNotIn("Needs confirmation", package.markdown)

    def test_context_candidate_sensitive_is_dropped_by_default(self) -> None:
        home, user_dir, state_dir = self.create_fixture()
        db_path = workroot_sqlite_path(state_dir)
        with open_sqlite(db_path) as conn:
            upsert_context_candidate(
                conn,
                ContextCandidate(
                    candidate_id="cand_sensitive",
                    workroot_id="wr_demo",
                    source_type="knowledge",
                    source_id="knowledge-sensitive",
                    title="Sensitive item",
                    summary="This item is sensitive.",
                    importance="critical",
                    confidence=1.0,
                    context_policy="always",
                    safety_policy="sensitive",
                    token_estimate=5,
                    updated_at="2026-05-19T00:00:00Z",
                ),
            )

        package = build_context_package(
            ContextRequest(home=home, agent="codex", cwd=user_dir, query="sensitive", now="2026-05-19T00:00:00Z")
        )

        dropped = {item["candidateId"]: item["reason"] for item in package.trace["droppedCandidates"]}
        self.assertEqual(dropped["cand_sensitive"], "safety-sensitive")
        self.assertNotIn("Sensitive item", package.markdown)

    def test_debug_trace_reports_safety_filter_reason(self) -> None:
        home, user_dir, state_dir = self.create_fixture()
        db_path = workroot_sqlite_path(state_dir)
        with open_sqlite(db_path) as conn:
            upsert_context_candidate(
                conn,
                ContextCandidate(
                    candidate_id="cand_sensitive_debug",
                    workroot_id="wr_demo",
                    source_type="knowledge",
                    source_id="knowledge-sensitive-debug",
                    title="Sensitive debug item",
                    summary="This item is sensitive and should be explained as dropped.",
                    importance="critical",
                    confidence=1.0,
                    context_policy="always",
                    safety_policy="sensitive",
                    token_estimate=5,
                    updated_at="2026-05-19T00:00:00Z",
                ),
            )

        package = build_context_package(
            ContextRequest(home=home, agent="codex", cwd=user_dir, query="sensitive", debug=True, now="2026-05-19T00:00:00Z")
        )

        trace = json.loads((state_dir / "context/debug/latest.json").read_text(encoding="utf-8"))
        dropped = {item["candidateId"]: item["reason"] for item in trace["droppedCandidates"]}
        self.assertEqual(dropped["cand_sensitive_debug"], "safety-sensitive")
        self.assertEqual(package.trace["droppedCandidates"], trace["droppedCandidates"])

    def test_token_usage_estimates_full_context_package(self) -> None:
        home, user_dir, _ = self.create_fixture()

        package = build_context_package(
            ContextRequest(
                home=home,
                agent="codex",
                cwd=user_dir,
                query="clean mode",
                now="2026-05-19T00:00:00Z",
            )
        )

        estimated = package.trace["tokenBudget"]["estimatedUsed"]
        self.assertGreater(estimated, sum(item["tokenEstimate"] for item in package.trace["selectedCandidates"]))
        self.assertNotIn("Tokens: 0", package.markdown)

    def test_token_estimator_is_conservative_for_cjk_and_code(self) -> None:
        english = estimate_context_package_tokens("Clean Mode keeps managed state outside user directories.")
        cjk = estimate_context_package_tokens("干净模式确保用户目录不会写入托管状态")
        code = estimate_context_package_tokens("def f():\n    return very_long_identifier_without_spaces_abcdefghijklmnopqrstuvwxyz0123456789\n")

        self.assertGreaterEqual(english, 8)
        self.assertGreaterEqual(cjk, 10)
        self.assertGreaterEqual(code, 12)

    def test_context_package_trims_to_hard_token_limit_after_render(self) -> None:
        home, user_dir, state_dir = self.create_fixture()
        hints = json.loads((state_dir / "state/runtime-hints.json").read_text(encoding="utf-8"))
        hints["contextGuide"]["agentBudgets"]["codex"]["targetTokens"] = 80
        hints["contextGuide"]["agentBudgets"]["codex"]["hardTokenLimit"] = 120
        (state_dir / "state/runtime-hints.json").write_text(json.dumps(hints, ensure_ascii=False, indent=2), encoding="utf-8")
        db_path = workroot_sqlite_path(state_dir)
        with open_sqlite(db_path) as conn:
            for i in range(8):
                upsert_context_candidate(
                    conn,
                    ContextCandidate(
                        candidate_id=f"cand_trim_{i}",
                        workroot_id="wr_demo",
                        source_type="knowledge",
                        source_id=f"knowledge-trim-{i}",
                        title=f"Trim candidate {i}",
                        summary=" ".join([f"candidate{i}"] * 30),
                        importance="low",
                        confidence=0.5,
                        context_policy="task-related",
                        token_estimate=20,
                        updated_at="2026-05-19T00:00:00Z",
                    ),
                )

        package = build_context_package(
            ContextRequest(
                home=home,
                agent="codex",
                cwd=user_dir,
                query="clean mode",
                mode="fast",
                target_token_budget=80,
                hard_token_budget=120,
                debug=True,
                now="2026-05-19T00:00:00Z",
            )
        )

        self.assertLessEqual(package.trace["tokenBudget"]["estimatedUsed"], package.trace["tokenBudget"]["hard"])
        self.assertTrue(package.trace["budgetTrim"]["applied"])
        self.assertEqual(package.trace["budgetTrim"]["reason"], "hard-token-limit")

    def test_context_package_uses_final_fallback_when_optional_content_cannot_satisfy_hard_limit(self) -> None:
        home, user_dir, _state_dir = self.create_fixture()

        package = build_context_package(
            ContextRequest(
                home=home,
                agent="codex",
                cwd=user_dir,
                query="clean mode",
                mode="fast",
                target_token_budget=1,
                hard_token_budget=12,
                debug=True,
                now="2026-05-19T00:00:00Z",
            )
        )

        self.assertTrue(package.trace["budgetTrim"]["applied"])
        self.assertTrue(package.trace["budgetTrim"]["finalFallback"])
        self.assertLessEqual(package.trace["tokenBudget"]["estimatedUsed"], package.trace["tokenBudget"]["hard"])
        self.assertLessEqual(estimate_context_package_tokens(package.markdown), package.trace["tokenBudget"]["hard"])
        self.assertNotEqual(package.markdown.strip(), "")

    def test_context_package_final_fallback_handles_tiny_hard_limit(self) -> None:
        home, user_dir, _state_dir = self.create_fixture()

        package = build_context_package(
            ContextRequest(
                home=home,
                agent="codex",
                cwd=user_dir,
                query="clean mode",
                mode="fast",
                target_token_budget=1,
                hard_token_budget=1,
                debug=True,
                now="2026-05-19T00:00:00Z",
            )
        )

        self.assertTrue(package.trace["budgetTrim"]["finalFallback"])
        self.assertLessEqual(package.trace["tokenBudget"]["estimatedUsed"], package.trace["tokenBudget"]["hard"])
        self.assertLessEqual(estimate_context_package_tokens(package.markdown), package.trace["tokenBudget"]["hard"])
        self.assertNotEqual(package.markdown.strip(), "")

    def test_candidates_trimmed_after_render_are_not_marked_used(self) -> None:
        home, user_dir, state_dir = self.create_fixture()
        db_path = workroot_sqlite_path(state_dir)
        with open_sqlite(db_path) as conn:
            upsert_context_candidate(
                conn,
                ContextCandidate(
                    candidate_id="cand_trimmed_usage",
                    workroot_id="wr_demo",
                    source_type="knowledge",
                    source_id="knowledge-trimmed-usage",
                    title="Trimmed usage candidate",
                    summary=" ".join(["trimmedusage"] * 120),
                    importance="low",
                    confidence=0.5,
                    context_policy="task-related",
                    token_estimate=10,
                    updated_at="2026-05-19T00:00:00Z",
                ),
            )

        package = build_context_package(
            ContextRequest(
                home=home,
                agent="codex",
                cwd=user_dir,
                query="trimmedusage",
                mode="fast",
                target_token_budget=150,
                hard_token_budget=160,
                debug=True,
                now="2026-05-19T00:00:00Z",
            )
        )

        self.assertIn("cand_trimmed_usage", package.trace["budgetTrim"]["removedCandidates"])
        with open_sqlite(db_path) as conn:
            row = conn.execute(
                "SELECT last_used_at, use_count FROM context_candidates WHERE candidate_id = ?",
                ("cand_trimmed_usage",),
            ).fetchone()
        self.assertEqual(row[0] or "", "")
        self.assertEqual(row[1], 0)

    def test_budget_trim_removes_graph_signals_before_candidates(self) -> None:
        home, user_dir, state_dir = self.create_fixture()
        hints = json.loads((state_dir / "state/runtime-hints.json").read_text(encoding="utf-8"))
        hints["contextGuide"]["agentBudgets"]["codex"]["targetTokens"] = 60
        hints["contextGuide"]["agentBudgets"]["codex"]["hardTokenLimit"] = 160
        (state_dir / "state/runtime-hints.json").write_text(json.dumps(hints, ensure_ascii=False, indent=2), encoding="utf-8")
        db_path = workroot_sqlite_path(state_dir)
        with open_sqlite(db_path) as conn:
            for i in range(5):
                conn.execute(
                    """
                    INSERT INTO graph_nodes (
                      node_id, node_type, kind, title, summary, status, importance, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"graph-trim-{i}",
                        "knowledge",
                        "context",
                        f"Graph trim signal {i}",
                        " ".join([f"graphsignal{i}"] * 25),
                        "active",
                        "normal",
                        "2026-05-19T00:00:00Z",
                        "2026-05-19T00:00:00Z",
                    ),
                )
                conn.execute(
                    """
                    INSERT INTO graph_edges (
                      edge_id, from_node_id, to_node_id, relation, strength, confidence, status, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"edge-graph-trim-{i}",
                        "decision-1",
                        f"graph-trim-{i}",
                        "supports",
                        1.0,
                        0.9,
                        "active",
                        "2026-05-19T00:00:00Z",
                        "2026-05-19T00:00:00Z",
                    ),
                )
            conn.commit()

        package = build_context_package(
            ContextRequest(
                home=home,
                agent="codex",
                cwd=user_dir,
                query="clean mode",
                mode="fast",
                target_token_budget=60,
                hard_token_budget=160,
                debug=True,
                now="2026-05-19T00:00:00Z",
            )
        )

        trim = package.trace["budgetTrim"]
        self.assertGreater(trim["removedGraphSignals"], 0)
        self.assertEqual(trim["removedCandidates"], [])

    def test_debug_trace_reports_hard_limit_trim(self) -> None:
        home, user_dir, state_dir = self.create_fixture()
        hints = json.loads((state_dir / "state/runtime-hints.json").read_text(encoding="utf-8"))
        hints["contextGuide"]["agentBudgets"]["codex"]["targetTokens"] = 80
        hints["contextGuide"]["agentBudgets"]["codex"]["hardTokenLimit"] = 120
        (state_dir / "state/runtime-hints.json").write_text(json.dumps(hints, ensure_ascii=False, indent=2), encoding="utf-8")
        db_path = workroot_sqlite_path(state_dir)
        with open_sqlite(db_path) as conn:
            upsert_context_candidate(
                conn,
                ContextCandidate(
                    candidate_id="cand_debug_trim",
                    workroot_id="wr_demo",
                    source_type="knowledge",
                    source_id="knowledge-debug-trim",
                    title="Debug trim candidate",
                    summary=" ".join(["debugtrim"] * 100),
                    importance="low",
                    confidence=0.5,
                    context_policy="task-related",
                    token_estimate=60,
                    updated_at="2026-05-19T00:00:00Z",
                ),
            )

        build_context_package(
            ContextRequest(
                home=home,
                agent="codex",
                cwd=user_dir,
                query="debugtrim",
                mode="fast",
                target_token_budget=80,
                hard_token_budget=120,
                debug=True,
                now="2026-05-19T00:00:00Z",
            )
        )

        trace = json.loads((state_dir / "context/debug/latest.json").read_text(encoding="utf-8"))
        self.assertTrue(trace["budgetTrim"]["applied"])
        self.assertEqual(trace["budgetTrim"]["reason"], "hard-token-limit")
        self.assertLessEqual(trace["tokenBudget"]["estimatedUsed"], trace["tokenBudget"]["hard"])

    def test_context_package_history_written(self) -> None:
        home, user_dir, state_dir = self.create_fixture()

        build_context_package(
            ContextRequest(home=home, agent="codex", cwd=user_dir, query="clean mode", debug=True, now="2026-05-19T12:34:56Z")
        )

        history = list((state_dir / "context/packages/history").glob("*.md"))
        self.assertEqual(len(history), 1)
        self.assertIn("codex", history[0].name)
        self.assertIn("standard", history[0].name)
        self.assertEqual(history[0].read_text(encoding="utf-8"), (state_dir / "context/packages/latest.md").read_text(encoding="utf-8"))

    def test_context_uses_agent_specific_token_budgets(self) -> None:
        home, user_dir, _ = self.create_fixture()

        codex_package = build_context_package(
            ContextRequest(
                home=home,
                agent="codex",
                cwd=user_dir,
                query="clean mode",
                now="2026-05-19T00:00:00Z",
            )
        )
        claude_package = build_context_package(
            ContextRequest(
                home=home,
                agent="claude",
                cwd=user_dir,
                query="clean mode",
                now="2026-05-19T00:00:00Z",
            )
        )

        self.assertEqual(codex_package.trace["tokenBudget"]["source"], "agent:codex")
        self.assertEqual(codex_package.trace["tokenBudget"]["hard"], 6000)
        self.assertEqual(claude_package.trace["tokenBudget"]["source"], "agent:claude")
        self.assertEqual(claude_package.trace["tokenBudget"]["hard"], 8000)
        self.assertIn("Tokens:", codex_package.markdown)

    def test_standard_to_quality_escalation_reselects_with_quality_budget(self) -> None:
        home, user_dir, state_dir = self.create_fixture()
        hints = json.loads((state_dir / "state/runtime-hints.json").read_text(encoding="utf-8"))
        hints["contextGuide"]["agentBudgets"]["codex"]["targetTokens"] = 5
        hints["contextGuide"]["modes"]["quality"]["targetTokens"] = 50
        (state_dir / "state/runtime-hints.json").write_text(json.dumps(hints, ensure_ascii=False, indent=2), encoding="utf-8")
        write_json(
            state_dir / "state/current.json",
            {
                "currentFocus": "clean mode",
                "activeTaskId": None,
                "nextSuggestedAction": "",
                "contextVersion": 1,
                "lastActivityAt": "2026-05-19T00:00:00Z",
            },
        )
        db_path = workroot_sqlite_path(state_dir)
        with open_sqlite(db_path) as conn:
            upsert_context_candidate(
                conn,
                ContextCandidate(
                    candidate_id="cand_quality_extra",
                    workroot_id="wr_demo",
                    source_type="decision",
                    source_id="decision-quality",
                    title="Quality extra context",
                    summary="Quality mode should include this candidate after escalation.",
                    importance="high",
                    confidence=0.9,
                    context_policy="always",
                    token_estimate=4,
                    updated_at="2026-05-19T00:00:00Z",
                ),
            )

        package = build_context_package(
            ContextRequest(
                home=home,
                agent="codex",
                cwd=user_dir,
                query="clean mode",
                debug=True,
                now="2026-05-19T00:00:00Z",
            )
        )

        self.assertEqual(package.trace["contextMode"], "quality")
        self.assertEqual(package.trace["qualityBehavior"], "quality-budget-expansion")
        selected_ids = {item["candidateId"] for item in package.trace["selectedCandidates"]}
        dropped = {item["candidateId"]: item["reason"] for item in package.trace["droppedCandidates"]}
        self.assertIn("cand_quality_extra", selected_ids)
        self.assertNotEqual(dropped.get("cand_quality_extra"), "token-budget")
        self.assertEqual(package.trace["tokenBudget"]["target"], 50)

    def test_malformed_runtime_hint_numeric_values_fall_back_safely(self) -> None:
        home, user_dir, state_dir = self.create_fixture()
        hints = json.loads((state_dir / "state/runtime-hints.json").read_text(encoding="utf-8"))
        hints["contextGuide"]["agentBudgets"]["codex"]["targetTokens"] = "abc"
        (state_dir / "state/runtime-hints.json").write_text(json.dumps(hints, ensure_ascii=False, indent=2), encoding="utf-8")

        package = build_context_package(
            ContextRequest(
                home=home,
                agent="codex",
                cwd=user_dir,
                query="clean mode",
                now="2026-05-19T00:00:00Z",
            )
        )

        self.assertIn("runtime-hints-invalid-budget", package.trace["fallbacks"])
        self.assertEqual(package.trace["tokenBudget"]["hard"], 6000)

    def test_runtime_hints_deep_merge_preserves_nested_defaults(self) -> None:
        _home, _user_dir, state_dir = self.create_fixture()
        hints = {
            "contextGuide": {
                "agentBudgets": {
                    "codex": {
                        "targetTokens": 1234,
                    }
                }
            }
        }
        (state_dir / "state/runtime-hints.json").write_text(json.dumps(hints, ensure_ascii=False, indent=2), encoding="utf-8")

        config, fallbacks = load_context_guide_config(state_dir)

        self.assertEqual(fallbacks, [])
        self.assertEqual(config["agentBudgets"]["codex"]["targetTokens"], 1234)
        self.assertEqual(config["agentBudgets"]["codex"]["hardTokenLimit"], 6000)
        self.assertEqual(config["agentBudgets"]["claude"]["hardTokenLimit"], 8000)

    def test_fts_operational_error_is_recorded_in_debug_trace(self) -> None:
        home, user_dir, state_dir = self.create_fixture()

        def broken_search(*_args, **_kwargs):
            import sqlite3

            raise sqlite3.OperationalError("malformed MATCH expression")

        with patch("scripts.workroot_context.search_fts", side_effect=broken_search):
            package = build_context_package(
                ContextRequest(
                    home=home,
                    agent="codex",
                    cwd=user_dir,
                    query="clean mode",
                    debug=True,
                    now="2026-05-19T00:00:00Z",
                )
            )

        trace = json.loads((state_dir / "context/debug/latest.json").read_text(encoding="utf-8"))
        self.assertEqual(package.trace["ftsFallbacks"], trace["ftsFallbacks"])
        self.assertTrue(any("malformed MATCH expression" in item["error"] for item in trace["ftsFallbacks"]))

    def test_cli_context_prints_markdown_package(self) -> None:
        home, user_dir, _ = self.create_fixture()

        result = subprocess.run(
            [
                sys.executable,
                str(CLI),
                "context",
                "--agent",
                "codex",
                "--cwd",
                str(user_dir),
                "--query",
                "clean mode",
            ],
            cwd=ROOT,
            env={**os.environ, "AI_WORKROOT_HOME": str(home)},
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("# AI Workroot Context Package", result.stdout)
        self.assertIn("Clean Mode decision", result.stdout)

    def test_cli_context_supports_quality_mode_and_debug_trace(self) -> None:
        home, user_dir, state_dir = self.create_fixture()

        result = subprocess.run(
            [
                sys.executable,
                str(CLI),
                "context",
                "--agent",
                "codex",
                "--cwd",
                str(user_dir),
                "--query",
                "clean mode",
                "--mode",
                "quality",
                "--debug",
            ],
            cwd=ROOT,
            env={**os.environ, "AI_WORKROOT_HOME": str(home)},
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Mode: quality", result.stdout)
        trace = json.loads((state_dir / "context/debug/latest.json").read_text(encoding="utf-8"))
        self.assertEqual(trace["requestedMode"], "quality")
        self.assertEqual(trace["contextMode"], "quality")
        self.assertEqual(trace["tokenBudget"]["hard"], 12000)

    def test_cli_context_deep_requires_explicit_request_and_records_it(self) -> None:
        home, user_dir, state_dir = self.create_fixture()

        result = subprocess.run(
            [
                sys.executable,
                str(CLI),
                "context",
                "--agent",
                "codex",
                "--cwd",
                str(user_dir),
                "--deep",
                "--debug",
            ],
            cwd=ROOT,
            env={**os.environ, "AI_WORKROOT_HOME": str(home)},
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Mode: deep", result.stdout)
        trace = json.loads((state_dir / "context/debug/latest.json").read_text(encoding="utf-8"))
        self.assertTrue(trace["deepExplicitlyRequested"])
        self.assertEqual(trace["contextMode"], "deep")

    def test_cli_context_rejects_target_tokens_over_hard_limit(self) -> None:
        home, user_dir, _ = self.create_fixture()

        result = subprocess.run(
            [
                sys.executable,
                str(CLI),
                "context",
                "--agent",
                "codex",
                "--cwd",
                str(user_dir),
                "--target-tokens",
                "999999",
            ],
            cwd=ROOT,
            env={**os.environ, "AI_WORKROOT_HOME": str(home)},
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("exceeds hard token limit", result.stderr)

    def test_cli_context_accepts_hard_token_limit_override(self) -> None:
        home, user_dir, state_dir = self.create_fixture()

        result = subprocess.run(
            [
                sys.executable,
                str(CLI),
                "context",
                "--agent",
                "codex",
                "--cwd",
                str(user_dir),
                "--target-tokens",
                "40",
                "--hard-token-limit",
                "80",
                "--debug",
            ],
            cwd=ROOT,
            env={**os.environ, "AI_WORKROOT_HOME": str(home)},
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        trace = json.loads((state_dir / "context/debug/latest.json").read_text(encoding="utf-8"))
        self.assertEqual(trace["tokenBudget"]["target"], 40)
        self.assertEqual(trace["tokenBudget"]["hard"], 80)
        self.assertIn("source", trace["tokenBudget"])

    def test_cli_context_after_init_uses_initialized_sqlite_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            user_dir.mkdir()
            env = {**os.environ, "AI_WORKROOT_HOME": str(home)}
            init = subprocess.run(
                [
                    sys.executable,
                    str(CLI),
                    "init",
                    "--name",
                    "Demo",
                    "--directory",
                    str(user_dir),
                    "--no-native-agent-entry",
                ],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(init.returncode, 0, init.stderr)

            result = subprocess.run(
                [sys.executable, str(CLI), "context", "--agent", "codex", "--cwd", str(user_dir)],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("# AI Workroot Context Package", result.stdout)


if __name__ == "__main__":
    unittest.main()
