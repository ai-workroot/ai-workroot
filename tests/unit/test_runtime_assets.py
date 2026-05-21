from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from ai_workroot.runtime.assets import create_internal_asset, mark_asset_missing, publish_asset, query_assets
from ai_workroot.storage.sqlite import initialize_workroot_sqlite


class RuntimeAssetsTest(unittest.TestCase):
    def open_db(self) -> sqlite3.Connection:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        db_path = Path(tmp.name) / "workroot.sqlite"
        initialize_workroot_sqlite(db_path)
        return sqlite3.connect(db_path)

    def test_create_internal_asset_supports_result_decision_and_knowledge_types(self) -> None:
        conn = self.open_db()

        decision = create_internal_asset(
            conn,
            workroot_id="wr_demo",
            asset_id="asset-decision",
            asset_type="decision",
            title="Clean Workroot decision",
            summary="Keep managed state outside user directories.",
        )
        result = create_internal_asset(
            conn,
            workroot_id="wr_demo",
            asset_id="asset-result",
            asset_type="result",
            title="Spec result",
        )
        knowledge = create_internal_asset(
            conn,
            workroot_id="wr_demo",
            asset_id="asset-knowledge",
            asset_type="knowledge",
            title="Architecture knowledge",
        )

        self.assertEqual(decision.publication_status, "internal")
        self.assertEqual(result.asset_type, "result")
        self.assertEqual(knowledge.asset_type, "knowledge")
        self.assertEqual([asset.asset_id for asset in query_assets(conn, "wr_demo", asset_type="decision")], ["asset-decision"])

    def test_publish_asset_records_surface_and_publication_without_writing_user_directory(self) -> None:
        conn = self.open_db()
        create_internal_asset(
            conn,
            workroot_id="wr_demo",
            asset_id="asset-result",
            asset_type="result",
            title="Review result",
        )

        publication = publish_asset(
            conn,
            workroot_id="wr_demo",
            asset_id="asset-result",
            surface_id="surface-docs",
            surface_path="docs",
            surface_type="docs",
            target_path="docs/review-result.md",
            published_by="test",
            allowed_asset_types=("result", "decision"),
        )

        asset_row = conn.execute(
            """
            SELECT publication_status, surface_id, current_path
            FROM assets
            WHERE asset_id = 'asset-result'
            """
        ).fetchone()
        publication_row = conn.execute(
            """
            SELECT asset_id, surface_id, target_path, publication_status
            FROM asset_publications
            WHERE publication_id = ?
            """,
            (publication.publication_id,),
        ).fetchone()

        self.assertEqual(asset_row, ("published", "surface-docs", "docs/review-result.md"))
        self.assertEqual(publication_row, ("asset-result", "surface-docs", "docs/review-result.md", "published"))

    def test_mark_asset_missing_updates_lifecycle(self) -> None:
        conn = self.open_db()
        create_internal_asset(
            conn,
            workroot_id="wr_demo",
            asset_id="asset-missing",
            asset_type="source",
            title="Missing source",
        )

        asset = mark_asset_missing(conn, workroot_id="wr_demo", asset_id="asset-missing", missing_since="2026-05-21T00:00:00Z")

        row = conn.execute(
            "SELECT lifecycle_status, updated_at FROM assets WHERE asset_id = 'asset-missing'"
        ).fetchone()
        self.assertEqual(asset.lifecycle_status, "missing")
        self.assertEqual(row, ("missing", "2026-05-21T00:00:00Z"))


if __name__ == "__main__":
    unittest.main()
