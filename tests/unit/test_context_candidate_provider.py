from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

import ai_workroot.capabilities.retrieval.providers.candidate_provider as candidate_provider
from ai_workroot.capabilities.retrieval.providers.candidate_provider import (
    query_context_candidates,
    upsert_context_candidate,
)
from ai_workroot.state.sqlite import initialize_workroot_sqlite


class ContextCandidateProviderTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db_path = Path(self.tmp.name) / "workroot.sqlite"
        initialize_workroot_sqlite(self.db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.addCleanup(self.conn.close)

    def test_query_candidates_handles_quoted_natural_language_without_broad_fallback(self) -> None:
        upsert_context_candidate(
            self.conn,
            {
                "candidate_id": "cand-office",
                "workroot_id": "wr_demo",
                "source_type": "asset",
                "source_id": "asset-office",
                "title": "Quiet office seats",
                "summary": "Choose quiet office seats because traffic is lower in the afternoon.",
                "importance": "normal",
            },
        )
        upsert_context_candidate(
            self.conn,
            {
                "candidate_id": "cand-unrelated",
                "workroot_id": "wr_demo",
                "source_type": "asset",
                "source_id": "asset-unrelated",
                "title": "Inventory note",
                "summary": "A warehouse inventory note.",
                "importance": "critical",
            },
        )

        matches = query_context_candidates(self.conn, "wr_demo", query='why did we choose "quiet office" seats?')

        self.assertEqual([match.candidate_id for match in matches], ["cand-office"])
        self.assertIn("candidate-fts-match", matches[0].reasons)

    def test_query_candidates_handles_cjk_query_without_broad_recent_fallback(self) -> None:
        upsert_context_candidate(
            self.conn,
            {
                "candidate_id": "cand-office",
                "workroot_id": "wr_demo",
                "source_type": "asset",
                "source_id": "asset-office",
                "title": "安静办公位",
                "summary": "下午安静办公位适合低峰时段，因为客流压力较低。",
                "importance": "normal",
            },
        )
        upsert_context_candidate(
            self.conn,
            {
                "candidate_id": "cand-unrelated",
                "workroot_id": "wr_demo",
                "source_type": "asset",
                "source_id": "asset-unrelated",
                "title": "Inventory note",
                "summary": "A warehouse inventory note.",
                "importance": "critical",
            },
        )

        matches = query_context_candidates(self.conn, "wr_demo", query="为什么选择下午安静办公位？")

        self.assertEqual([match.candidate_id for match in matches], ["cand-office"])
        self.assertIn("candidate-term-match", matches[0].reasons)

    def test_query_candidates_respects_task_scope(self) -> None:
        upsert_context_candidate(
            self.conn,
            {
                "candidate_id": "cand-task-one",
                "workroot_id": "wr_demo",
                "source_type": "decision",
                "source_id": "decision-one",
                "title": "Pricing decision",
                "summary": "Current task decision.",
                "domains": "task:task-one scope:task",
                "importance": "normal",
            },
        )
        upsert_context_candidate(
            self.conn,
            {
                "candidate_id": "cand-task-two",
                "workroot_id": "wr_demo",
                "source_type": "decision",
                "source_id": "decision-two",
                "title": "Pricing decision",
                "summary": "Other task decision.",
                "domains": "task:task-two scope:task",
                "importance": "critical",
            },
        )

        matches = query_context_candidates(self.conn, "wr_demo", query="pricing", scope="task:task-one")

        self.assertEqual([match.candidate_id for match in matches], ["cand-task-one"])
        self.assertIn("scope-match", matches[0].reasons)

    def test_query_candidates_respects_legacy_bare_task_scope_tokens(self) -> None:
        upsert_context_candidate(
            self.conn,
            {
                "candidate_id": "cand-task-one",
                "workroot_id": "wr_demo",
                "source_type": "context_recall_hint",
                "source_id": "hint-one",
                "title": "Pricing decision",
                "summary": "Current task hint.",
                "domains": "task-one",
                "importance": "normal",
            },
        )
        upsert_context_candidate(
            self.conn,
            {
                "candidate_id": "cand-task-two",
                "workroot_id": "wr_demo",
                "source_type": "context_recall_hint",
                "source_id": "hint-two",
                "title": "Pricing decision",
                "summary": "Other task hint.",
                "domains": "task-two",
                "importance": "critical",
            },
        )

        matches = query_context_candidates(self.conn, "wr_demo", query="pricing", scope="task:task-one")

        self.assertEqual([match.candidate_id for match in matches], ["cand-task-one"])

    def test_query_candidates_uses_bounded_sql_pools(self) -> None:
        for index in range(20):
            upsert_context_candidate(
                self.conn,
                {
                    "candidate_id": f"cand-{index:02d}",
                    "workroot_id": "wr_demo",
                    "source_type": "asset",
                    "source_id": f"asset-{index:02d}",
                    "title": f"Candidate {index:02d}",
                    "summary": "needle" if index == 19 else "unrelated",
                    "importance": "normal",
                },
            )

        original_fetch_rows = candidate_provider._fetch_rows
        unbounded_context_queries: list[str] = []

        def spy_fetch_rows(conn: sqlite3.Connection, query: str, params: tuple[object, ...]) -> list[sqlite3.Row]:
            normalized = " ".join(query.split()).lower()
            if "from context_candidates" in normalized and " limit " not in normalized:
                unbounded_context_queries.append(normalized)
            return original_fetch_rows(conn, query, params)

        candidate_provider._fetch_rows = spy_fetch_rows
        self.addCleanup(setattr, candidate_provider, "_fetch_rows", original_fetch_rows)

        matches = query_context_candidates(self.conn, "wr_demo", query="needle", limit=3)

        self.assertEqual([match.candidate_id for match in matches], ["cand-19"])
        self.assertEqual(unbounded_context_queries, [])

    def test_query_candidates_uses_language_neutral_unicode_fallback_terms(self) -> None:
        upsert_context_candidate(
            self.conn,
            {
                "candidate_id": "cand-arabic",
                "workroot_id": "wr_demo",
                "source_type": "asset",
                "source_id": "asset-arabic",
                "title": "خطة العملاء",
                "summary": "تجربة العملاء تحتاج متابعة أسبوعية.",
                "importance": "normal",
            },
        )

        matches = query_context_candidates(self.conn, "wr_demo", query="كيف نتابع تجربة العملاء؟", limit=3)

        self.assertEqual([match.candidate_id for match in matches], ["cand-arabic"])

    def test_upsert_does_not_commit_caller_transaction(self) -> None:
        self.conn.execute("BEGIN")
        upsert_context_candidate(
            self.conn,
            {
                "candidate_id": "cand-rollback",
                "workroot_id": "wr_demo",
                "source_type": "asset",
                "source_id": "asset-rollback",
                "title": "Rollback candidate",
                "summary": "This candidate should be rolled back by the caller.",
            },
        )
        self.conn.rollback()

        count = self.conn.execute(
            "SELECT COUNT(*) FROM context_candidates WHERE candidate_id = 'cand-rollback'"
        ).fetchone()[0]
        self.assertEqual(count, 0)

    def test_upsert_does_not_migrate_old_candidate_schema_inside_provider(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "old-context-candidates.sqlite"
            with sqlite3.connect(db_path) as conn:
                conn.execute(
                    """
                    CREATE TABLE context_candidates (
                      candidate_id TEXT PRIMARY KEY,
                      workroot_id TEXT NOT NULL,
                      source_type TEXT NOT NULL,
                      source_id TEXT NOT NULL,
                      title TEXT,
                      summary TEXT
                    )
                    """
                )
                conn.execute("CREATE VIRTUAL TABLE context_candidates_fts USING fts5(candidate_id, title, summary)")
                conn.commit()

            with sqlite3.connect(db_path) as conn:
                with self.assertRaises(sqlite3.OperationalError):
                    upsert_context_candidate(
                        conn,
                        {
                            "candidate_id": "cand-old",
                            "workroot_id": "wr_demo",
                            "source_type": "asset",
                            "source_id": "asset-old",
                            "title": "Old schema candidate",
                            "summary": "Provider must not alter this schema.",
                        },
                    )
                columns = {row[1] for row in conn.execute("PRAGMA table_info(context_candidates)").fetchall()}

        self.assertNotIn("domains", columns)


if __name__ == "__main__":
    unittest.main()
