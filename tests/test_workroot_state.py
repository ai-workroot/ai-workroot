from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.workroot_state import initialize_ai_workroot_home, initialize_workroot_state, read_jsonl


class WorkrootStateTest(unittest.TestCase):
    def test_initialize_home_creates_global_layout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            initialize_ai_workroot_home(home, now="2026-05-19T00:00:00Z")
            self.assertTrue((home / "config.json").exists())
            self.assertTrue((home / "registry/workroots.jsonl").exists())
            self.assertTrue((home / "registry/directory-bindings.jsonl").exists())
            self.assertTrue((home / "global-index").is_dir())
            self.assertTrue((home / "global-cache").is_dir())

    def test_initialize_workroot_state_keeps_state_outside_user_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            user_dir.mkdir()
            result = initialize_workroot_state(
                home,
                workroot_id="wr_demo",
                name="Demo",
                user_directory=user_dir,
                now="2026-05-19T00:00:00Z",
            )
            self.assertEqual(result.workroot_id, "wr_demo")
            self.assertTrue((home / "workroots/wr_demo/workroot.json").exists())
            self.assertFalse((user_dir / ".workroot").exists())
            self.assertFalse((user_dir / ".ai-workroot").exists())
            records = read_jsonl(home / "registry/workroots.jsonl")
            self.assertEqual(records[0]["workrootId"], "wr_demo")

    def test_workroot_json_contains_clean_mode_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            user_dir.mkdir()
            initialize_workroot_state(home, "wr_demo", "Demo", user_dir, now="2026-05-19T00:00:00Z")
            payload = json.loads((home / "workroots/wr_demo/workroot.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["mode"], "clean")
            self.assertEqual(payload["workrootId"], "wr_demo")
            self.assertEqual(payload["userDirectory"], str(user_dir.resolve()))
            self.assertEqual(payload["stateDirectory"], str((home / "workroots/wr_demo").resolve()))


if __name__ == "__main__":
    unittest.main()
