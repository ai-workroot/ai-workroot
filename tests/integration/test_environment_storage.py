from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from ai_workroot.runtime.environment import initialize_environment, register_workroot
from ai_workroot.storage.jsonl_registry import read_jsonl
from ai_workroot.storage.sqlite import initialize_workroot_sqlite


class EnvironmentStorageTest(unittest.TestCase):
    def test_initialize_environment_creates_clean_global_layout_without_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "ai-workroot-home"

            environment = initialize_environment(home)

            self.assertEqual(environment.home, str(home.resolve()))
            self.assertTrue((home / "config.json").is_file())
            self.assertTrue((home / "registry/workroots.jsonl").is_file())
            self.assertTrue((home / "registry/directory-bindings.jsonl").is_file())
            self.assertTrue((home / "registry/.registry.lock").exists())
            self.assertTrue((home / "preferences/operator-preferences.json").is_file())
            self.assertTrue((home / "preferences/policy-defaults.json").is_file())
            self.assertTrue((home / "global-index").is_dir())
            self.assertTrue((home / "global-cache").is_dir())
            self.assertFalse((home / "user/profile.md").exists())

    def test_register_workroot_writes_locked_registry_and_rejects_duplicate_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "ai-workroot-home"
            user_dir = Path(tmp) / "project"
            user_dir.mkdir()
            initialize_environment(home)

            registration = register_workroot(home, workroot_id="wr_demo", name="Demo", user_directory=user_dir)

            self.assertEqual(registration.workroot_id, "wr_demo")
            self.assertEqual(registration.user_directory, str(user_dir.resolve()))
            self.assertTrue((home / "workroots/wr_demo/workroot.json").is_file())
            self.assertTrue((home / "workroots/wr_demo/relationships").is_dir())
            self.assertTrue((home / "workroots/wr_demo/release").is_dir())

            workroots = read_jsonl(home / "registry/workroots.jsonl")
            bindings = read_jsonl(home / "registry/directory-bindings.jsonl")
            self.assertEqual(len(workroots), 1)
            self.assertEqual(len(bindings), 1)

            with self.assertRaises(ValueError):
                register_workroot(home, workroot_id="wr_other", name="Other", user_directory=user_dir)

    def test_initialize_workroot_sqlite_creates_0530_canonical_tables(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "workroot.sqlite"

            initialize_workroot_sqlite(db_path)

            with sqlite3.connect(db_path) as connection:
                tables = {
                    row[0]
                    for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type IN ('table', 'virtual')"
                    )
                }

            for table in (
                "schema_migrations",
                "assets",
                "asset_surfaces",
                "release_records",
                "tombstones",
                "redactions",
                "deletion_records",
                "relationship_nodes",
                "relationship_edges",
                "relationship_evidence",
                "index_manifests",
                "context_candidates",
                "context_packages",
                "context_traces",
                "doctor_runs",
            ):
                with self.subTest(table=table):
                    self.assertIn(table, tables)

            self.assertNotIn("knowledge_items", tables)


if __name__ == "__main__":
    unittest.main()
