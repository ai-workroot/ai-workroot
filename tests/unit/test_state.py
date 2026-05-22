from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from ai_workroot.runtime.environment import initialize_environment
from ai_workroot.runtime.init import initialize_workroot


class WorkrootStateRetirementTest(unittest.TestCase):
    def test_old_compatibility_state_initializers_are_retired(self) -> None:
        from ai_workroot.runtime import state

        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            user_dir = Path(tmp) / "project"

            with self.assertRaisesRegex(RuntimeError, "retired"):
                state.initialize_ai_workroot_home(home, now="2026-05-19T00:00:00Z")

            with self.assertRaisesRegex(RuntimeError, "retired"):
                state.initialize_workroot_state(
                    home,
                    workroot_id="wr_demo",
                    name="Demo",
                    user_directory=user_dir,
                    now="2026-05-19T00:00:00Z",
                )

    def test_active_environment_initialization_replaces_old_state_initializer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"

            initialize_environment(home)
            config = json.loads((home / "config.json").read_text(encoding="utf-8"))

            self.assertEqual(config["kind"], "WorkrootEnvironment")
            self.assertTrue((home / "registry/workroots.jsonl").is_file())
            self.assertFalse((home / "user/profile.md").exists())
            self.assertFalse((home / "knowledge").exists())
            self.assertFalse((home / "graph").exists())

    def test_active_init_keeps_state_outside_user_directory_and_initializes_sqlite(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"

            result = initialize_workroot(
                name="Demo",
                directory=user_dir,
                workroot_id="wr_demo",
                native_agent_entry=False,
                ai_workroot_home=home,
            )
            db_path = Path(result.registration.state_directory) / "cache/workroot.sqlite"

            self.assertTrue(db_path.is_file())
            self.assertFalse((user_dir / ".workroot").exists())
            self.assertFalse((user_dir / ".ai-workroot").exists())
            with sqlite3.connect(db_path) as conn:
                tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
            self.assertIn("workroots", tables)
            self.assertIn("context_candidates", tables)


if __name__ == "__main__":
    unittest.main()
