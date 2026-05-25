from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from ai_workroot.assets.operations import (
    create_internal_asset,
    mark_asset_missing,
    publish_asset,
    publish_asset_to_surface,
    query_assets,
    record_asset_publication,
)
from ai_workroot.state.sqlite import initialize_workroot_sqlite


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
        self.assertEqual(
            [asset.asset_id for asset in query_assets(conn, "wr_demo", asset_type="decision")], ["asset-decision"]
        )
        invalidations = {
            row
            for row in conn.execute(
                """
                SELECT index_id, reason
                FROM index_invalidations
                WHERE invalidation_id LIKE 'idxinv:wr_demo:asset:%'
                """
            ).fetchall()
        }
        self.assertIn(("assets", "asset-changed:asset-decision"), invalidations)
        self.assertIn(("assets", "asset-changed:asset-result"), invalidations)
        self.assertIn(("assets", "asset-changed:asset-knowledge"), invalidations)

    def test_record_asset_publication_is_explicit_metadata_only_and_writes_no_file(self) -> None:
        conn = self.open_db()
        with tempfile.TemporaryDirectory() as tmp:
            surface_path = Path(tmp) / "docs"
            create_internal_asset(
                conn,
                workroot_id="wr_demo",
                asset_id="asset-result",
                asset_type="result",
                title="Review result",
            )

            publication = record_asset_publication(
                conn,
                workroot_id="wr_demo",
                asset_id="asset-result",
                surface_id="surface-docs",
                surface_path=str(surface_path),
                surface_type="docs",
                target_path="review-result.md",
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

            self.assertEqual(asset_row, ("metadata-only", "surface-docs", "review-result.md"))
            self.assertEqual(publication_row, ("asset-result", "surface-docs", "review-result.md", "metadata-only"))
            self.assertFalse((surface_path / "review-result.md").exists())
            invalidation = conn.execute(
                """
                SELECT index_id, reason
                FROM index_invalidations
                WHERE invalidation_id = 'idxinv:wr_demo:asset-publication:asset-result'
                """
            ).fetchone()
            self.assertEqual(invalidation, ("asset-publications", "asset-publication-changed:asset-result"))

    def test_publish_asset_compatibility_wrapper_records_metadata_only(self) -> None:
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
            target_path="review-result.md",
            published_by="test",
            allowed_asset_types=("result", "decision"),
        )

        self.assertEqual(publication.publication_status, "metadata-only")

    def test_publish_asset_to_surface_writes_explicit_file(self) -> None:
        conn = self.open_db()
        with tempfile.TemporaryDirectory() as tmp:
            surface_path = Path(tmp) / "docs"
            create_internal_asset(
                conn,
                workroot_id="wr_demo",
                asset_id="asset-result",
                asset_type="result",
                title="Review result",
            )

            publication = publish_asset_to_surface(
                conn,
                workroot_id="wr_demo",
                asset_id="asset-result",
                surface_id="surface-docs",
                surface_path=surface_path,
                surface_type="docs",
                target_path="review-result.md",
                published_by="test",
                allowed_asset_types=("result", "decision"),
                content="# Review result\n",
            )

            self.assertEqual(publication.publication_status, "published")
            self.assertEqual((surface_path / "review-result.md").read_text(encoding="utf-8"), "# Review result\n")
            asset_row = conn.execute(
                "SELECT publication_status, surface_id, current_path FROM assets WHERE asset_id = 'asset-result'"
            ).fetchone()
            self.assertEqual(asset_row, ("published", "surface-docs", "review-result.md"))

    def test_publish_asset_to_surface_rejects_path_traversal_without_writing(self) -> None:
        conn = self.open_db()
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            surface_path = base / "docs"
            create_internal_asset(
                conn,
                workroot_id="wr_demo",
                asset_id="asset-result",
                asset_type="result",
                title="Review result",
            )

            with self.assertRaises(ValueError):
                publish_asset_to_surface(
                    conn,
                    workroot_id="wr_demo",
                    asset_id="asset-result",
                    surface_id="surface-docs",
                    surface_path=surface_path,
                    surface_type="docs",
                    target_path="../escape.md",
                    published_by="test",
                    allowed_asset_types=("result", "decision"),
                    content="escape",
                )

            self.assertFalse((base / "escape.md").exists())

    def test_mark_asset_missing_updates_lifecycle(self) -> None:
        conn = self.open_db()
        create_internal_asset(
            conn,
            workroot_id="wr_demo",
            asset_id="asset-missing",
            asset_type="source",
            title="Missing source",
        )

        asset = mark_asset_missing(
            conn, workroot_id="wr_demo", asset_id="asset-missing", missing_since="2026-05-21T00:00:00Z"
        )

        row = conn.execute("SELECT lifecycle_status, updatedAt FROM assets WHERE asset_id = 'asset-missing'").fetchone()
        self.assertEqual(asset.lifecycle_status, "missing")
        self.assertEqual(row, ("missing", "2026-05-21T00:00:00Z"))


if __name__ == "__main__":
    unittest.main()
