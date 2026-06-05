from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from ai_workroot.state.environment import initialize_environment
from ai_workroot.commands.init_workroot import initialize_workroot


class WorkrootStateTest(unittest.TestCase):
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
                ai_workroot_home=home,
            )
            db_path = Path(result.registration.state_directory) / "cache/workroot.sqlite"

            self.assertEqual(result.message(), "initialized wr_demo registered")
            self.assertFalse(hasattr(result, "native_agent_entry"))
            self.assertFalse((user_dir / "AGENTS.md").exists())
            self.assertFalse((user_dir / "CLAUDE.md").exists())
            self.assertTrue(db_path.is_file())
            self.assertFalse((user_dir / ".workroot").exists())
            self.assertFalse((user_dir / ".ai-workroot").exists())
            with sqlite3.connect(db_path) as conn:
                tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
            self.assertIn("workroots", tables)
            self.assertIn("context_candidates", tables)


if __name__ == "__main__":
    unittest.main()
