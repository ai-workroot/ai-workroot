from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
