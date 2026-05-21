from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ai_workroot.runtime.state import initialize_ai_workroot_home, initialize_workroot_state, read_jsonl


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

    def test_malformed_config_is_backed_up_before_repair(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            home.mkdir()
            config = home / "config.json"
            config.write_text("{not-json", encoding="utf-8")

            initialize_ai_workroot_home(home, now="2026-05-19T00:00:00Z")

            backups = list(home.glob("config.json.bak.*"))
            self.assertEqual(len(backups), 1)
            self.assertEqual(backups[0].read_text(encoding="utf-8"), "{not-json")
            repaired = json.loads(config.read_text(encoding="utf-8"))
            self.assertEqual(repaired["version"], "0.9.529")

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

    def test_initialize_workroot_state_writes_context_runtime_hints(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            user_dir.mkdir()
            initialize_workroot_state(home, "wr_demo", "Demo", user_dir, now="2026-05-19T00:00:00Z")

            hints = json.loads((home / "workroots/wr_demo/state/runtime-hints.json").read_text(encoding="utf-8"))
            context = hints["contextGuide"]

            self.assertEqual(context["defaultMode"], "standard")
            self.assertEqual(context["agentBudgets"]["codex"]["hardTokenLimit"], 6000)
            self.assertGreater(context["agentBudgets"]["claude"]["hardTokenLimit"], context["agentBudgets"]["codex"]["hardTokenLimit"])
            self.assertEqual(context["modes"]["standard"]["targetLatencyMs"], 1000)
            self.assertEqual(context["modes"]["quality"]["softLatencyMs"], 3000)
            self.assertTrue(context["modes"]["deep"]["requiresExplicitRequest"])
            self.assertFalse(context["hotPath"]["allowRemoteLlm"])
            self.assertFalse(context["hotPath"]["allowRemoteEmbedding"])
            self.assertFalse(context["hotPath"]["allowVectorSearch"])

    def test_rejected_user_directory_does_not_initialize_home_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = home / "project"

            with self.assertRaises(ValueError):
                initialize_workroot_state(home, "wr_bad", "Bad", user_dir, now="2026-05-19T00:00:00Z")

            self.assertFalse((home / "config.json").exists())
            self.assertFalse((home / "registry").exists())
            self.assertFalse((home / "workroots").exists())
            self.assertFalse(user_dir.exists())

    def test_initialize_rejects_duplicate_user_directory_binding(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            user_dir.mkdir()

            initialize_workroot_state(home, "wr_one", "One", user_dir, now="2026-05-19T00:00:00Z")

            with self.assertRaisesRegex(ValueError, "wr_one"):
                initialize_workroot_state(home, "wr_two", "Two", user_dir, now="2026-05-19T00:00:00Z")

    def test_initialize_rejects_unsafe_workroot_id_before_creating_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            user_dir.mkdir()

            with self.assertRaisesRegex(ValueError, "invalid Workroot ID"):
                initialize_workroot_state(home, "../bad", "Bad", user_dir, now="2026-05-19T00:00:00Z")

            self.assertFalse((base / "bad").exists())
            self.assertFalse((home / "workroots").exists())


if __name__ == "__main__":
    unittest.main()
