from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from ai_workroot.capabilities.retrieval.providers.sqlite_fts import (
    index_file_chunk,
    search_fts,
    search_fts_by_refs,
)
from ai_workroot.capabilities.retrieval.providers.candidate_provider import upsert_context_candidate
from ai_workroot.state.sqlite import initialize_workroot_sqlite


class SqliteFtsProviderTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db_path = Path(self.tmp.name) / "workroot.sqlite"
        initialize_workroot_sqlite(self.db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.addCleanup(self.conn.close)

    def test_natural_language_query_with_quotes_and_punctuation_does_not_raise_or_error(self) -> None:
        index_file_chunk(
            self.conn,
            workroot_id="wr_demo",
            file_id="file-office",
            chunk_id="chunk-office",
            relative_path="workroot-output/office.md",
            body="Quiet office seats work in the afternoon because traffic is lower.",
            source_type="asset",
            source_id="asset-office",
        )

        matches, error = search_fts(self.conn, "wr_demo", 'why did we choose "quiet office" seats?')

        self.assertIsNone(error)
        self.assertEqual([match.chunk_id for match in matches], ["chunk-office"])

    def test_cjk_query_uses_bounded_fallback_scan_without_match_error(self) -> None:
        index_file_chunk(
            self.conn,
            workroot_id="wr_demo",
            file_id="file-shop",
            chunk_id="chunk-shop",
            relative_path="workroot-output/shop.md",
            body="下午安静办公位适合低峰时段，因为客流压力较低。",
            source_type="asset",
            source_id="asset-shop",
        )

        matches, error = search_fts(self.conn, "wr_demo", "为什么选择下午安静办公位？")

        self.assertIsNone(error)
        self.assertEqual([match.chunk_id for match in matches], ["chunk-shop"])
        self.assertEqual(matches[0].reason, "file-fallback-scan")

    def test_unicode_query_uses_language_neutral_bounded_fallback_scan(self) -> None:
        index_file_chunk(
            self.conn,
            workroot_id="wr_demo",
            file_id="file-arabic",
            chunk_id="chunk-arabic",
            relative_path="workroot-output/customer.md",
            body="تجربة العملاء تحتاج متابعة أسبوعية.",
            source_type="asset",
            source_id="asset-arabic",
        )

        matches, error = search_fts(self.conn, "wr_demo", "كيف نتابع تجربة العملاء؟")

        self.assertIsNone(error)
        self.assertEqual([match.chunk_id for match in matches], ["chunk-arabic"])
        self.assertEqual(matches[0].reason, "file-fallback-scan")

    def test_cjk_fallback_finds_relevant_late_chunk_within_bounded_scan(self) -> None:
        for index in range(80):
            index_file_chunk(
                self.conn,
                workroot_id="wr_demo",
                file_id=f"file-noise-{index:03d}",
                chunk_id=f"chunk-noise-{index:03d}",
                relative_path=f"workroot-output/noise-{index:03d}.md",
                body="unrelated placeholder body",
                source_type="asset",
                source_id=f"asset-noise-{index:03d}",
            )
        index_file_chunk(
            self.conn,
            workroot_id="wr_demo",
            file_id="file-target-late",
            chunk_id="chunk-target-late",
            relative_path="workroot-output/target-late.md",
            body="下午安静办公位适合低峰时段，因为客流压力较低。",
            source_type="asset",
            source_id="asset-target-late",
        )

        matches, error = search_fts(self.conn, "wr_demo", "为什么选择下午安静办公位？", limit=1)

        self.assertIsNone(error)
        self.assertEqual([match.chunk_id for match in matches], ["chunk-target-late"])

    def test_ref_scoped_chunk_retrieval_does_not_depend_on_match_query(self) -> None:
        index_file_chunk(
            self.conn,
            workroot_id="wr_demo",
            file_id="file-decision",
            chunk_id="chunk-decision",
            relative_path="workroot-output/decision.md",
            body="Source material for a prior decision.",
            source_type="decision",
            source_id="decision-pricing",
        )

        matches, error = search_fts_by_refs(self.conn, "wr_demo", ("decision:decision-pricing",), limit=3)

        self.assertIsNone(error)
        self.assertEqual([match.chunk_id for match in matches], ["chunk-decision"])
        self.assertEqual(matches[0].reason, "ref-scoped-evidence")

    def test_candidate_ref_drills_down_to_source_chunk(self) -> None:
        upsert_context_candidate(
            self.conn,
            {
                "candidate_id": "candidate-shop-plan",
                "workroot_id": "wr_demo",
                "source_type": "asset",
                "source_id": "asset-shop-plan",
                "title": "Shop plan",
                "summary": "Candidate summary for the shop plan.",
            },
        )
        index_file_chunk(
            self.conn,
            workroot_id="wr_demo",
            file_id="file-shop-plan",
            chunk_id="chunk-shop-plan",
            relative_path="workroot-output/shop-plan.md",
            body="Detailed source evidence for the shop plan.",
            source_type="asset",
            source_id="asset-shop-plan",
        )

        matches, error = search_fts_by_refs(self.conn, "wr_demo", ("candidate:candidate-shop-plan",), limit=3)

        self.assertIsNone(error)
        self.assertEqual([match.chunk_id for match in matches], ["chunk-shop-plan"])
        self.assertEqual(matches[0].reason, "ref-scoped-evidence")

    def test_index_file_chunk_does_not_commit_caller_transaction(self) -> None:
        self.conn.execute("BEGIN")
        index_file_chunk(
            self.conn,
            workroot_id="wr_demo",
            file_id="file-rollback",
            chunk_id="chunk-rollback",
            relative_path="workroot-output/rollback.md",
            body="This chunk should be rolled back by the caller.",
            source_type="asset",
            source_id="asset-rollback",
        )
        self.conn.rollback()

        count = self.conn.execute("SELECT COUNT(*) FROM indexed_chunks WHERE chunk_id = 'chunk-rollback'").fetchone()[0]
        self.assertEqual(count, 0)

    def test_index_file_chunk_does_not_migrate_old_indexed_files_schema_inside_provider(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "old-indexed-files.sqlite"
            with sqlite3.connect(db_path) as conn:
                conn.execute(
                    """
                    CREATE TABLE indexed_files (
                      file_id TEXT PRIMARY KEY,
                      workroot_id TEXT NOT NULL,
                      relative_path TEXT NOT NULL
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE indexed_chunks (
                      chunk_id TEXT PRIMARY KEY,
                      file_id TEXT NOT NULL,
                      workroot_id TEXT NOT NULL,
                      body TEXT
                    )
                    """
                )
                conn.execute("CREATE VIRTUAL TABLE indexed_chunks_fts USING fts5(chunk_id, body)")
                conn.commit()

            with sqlite3.connect(db_path) as conn:
                with self.assertRaises(sqlite3.OperationalError):
                    index_file_chunk(
                        conn,
                        workroot_id="wr_demo",
                        file_id="file-old",
                        chunk_id="chunk-old",
                        relative_path="workroot-output/old.md",
                        body="Provider must not alter this schema.",
                        source_type="asset",
                        source_id="asset-old",
                    )
                columns = {row[1] for row in conn.execute("PRAGMA table_info(indexed_files)").fetchall()}

        self.assertNotIn("source_type", columns)
        self.assertNotIn("source_id", columns)


if __name__ == "__main__":
    unittest.main()
