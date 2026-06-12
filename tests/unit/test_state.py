from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from ai_workroot.commands.init_workroot import initialize_workroot
from ai_workroot.state.environment import initialize_environment as initialize_environment_state
from ai_workroot.state.environment import register_workroot
from ai_workroot.state.registry import find_workroot_by_cwd, list_workroots


class WorkrootStateTest(unittest.TestCase):
    def test_active_environment_initialization_replaces_old_state_initializer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"

            initialize_environment_state(home)
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

    def test_registry_handles_malformed_workroot_json_with_binding_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            user_dir = Path(tmp) / "project"
            user_dir.mkdir()
            initialize_environment_state(home)
            registration = register_workroot(home, "wr_demo", "Demo", user_dir)
            Path(registration.state_directory, "workroot.json").write_text("{bad json", encoding="utf-8")

            records = list_workroots(ai_workroot_home=home)
            located = find_workroot_by_cwd(user_dir, ai_workroot_home=home)

            self.assertEqual(records[0]["workrootId"], "wr_demo")
            self.assertEqual(records[0]["userDirectory"], str(user_dir.resolve()))
            self.assertIn("malformed_workroot_json", records[0]["metadataWarning"])
            self.assertEqual(located["workrootId"], "wr_demo")


if __name__ == "__main__":
    unittest.main()
