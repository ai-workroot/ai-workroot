from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from ai_workroot.indexing.global_indexes import query_global_workroot_index, refresh_global_workroot_index
from ai_workroot.runtime.environment import initialize_environment, register_workroot
from ai_workroot.storage.sqlite import initialize_workroot_sqlite


class GlobalIndexesTest(unittest.TestCase):
    def test_refresh_and_query_global_workroot_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            user_dir.mkdir()
            initialize_environment(home)
            registration = register_workroot(home, workroot_id="wr_demo", name="Demo", user_directory=user_dir)
            db_path = Path(registration.state_directory) / "cache/workroot.sqlite"
            initialize_workroot_sqlite(db_path)

            entry_count = refresh_global_workroot_index(home)
            entries = query_global_workroot_index(home, query="Demo")

            self.assertEqual(entry_count, 1)
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["entryType"], "workroot")
            self.assertEqual(entries[0]["workrootId"], "wr_demo")
            self.assertEqual(entries[0]["title"], "Demo")
            index_path = home / "global-index/workroots.index.jsonl"
            self.assertTrue(index_path.is_file())
            self.assertIn('"workrootId": "wr_demo"', index_path.read_text(encoding="utf-8"))
            with sqlite3.connect(db_path) as conn:
                row = conn.execute(
                    """
                    SELECT entry_type, title
                    FROM global_index_entries
                    WHERE entry_id = 'workroot:wr_demo'
                    """
                ).fetchone()
            self.assertEqual(row, ("workroot", "Demo"))

    def test_global_workroot_index_does_not_create_context_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            user_dir.mkdir()
            initialize_environment(home)
            registration = register_workroot(home, workroot_id="wr_demo", name="Demo", user_directory=user_dir)
            db_path = Path(registration.state_directory) / "cache/workroot.sqlite"
            initialize_workroot_sqlite(db_path)

            refresh_global_workroot_index(home)

            with sqlite3.connect(db_path) as conn:
                candidate_count = conn.execute("SELECT COUNT(*) FROM context_candidates").fetchone()[0]

            self.assertEqual(candidate_count, 0)


if __name__ == "__main__":
    unittest.main()
