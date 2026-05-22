from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tests.support.cli import run_workroot_cli


class InitNativeAgentEntryCliTest(unittest.TestCase):
    def test_init_native_agent_entry_requires_explicit_authorization(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            user_dir.mkdir()
            result = run_workroot_cli(
                {"AI_WORKROOT_HOME": str(home)},
                "init",
                "--name",
                "Demo",
                "--directory",
                str(user_dir),
                "--native-agent-entry",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            agents = user_dir / "AGENTS.md"
            claude = user_dir / "CLAUDE.md"
            self.assertTrue(agents.exists())
            self.assertTrue(claude.exists())
            self.assertIn("<!-- AI_WORKROOT_BEGIN -->", agents.read_text(encoding="utf-8"))
            self.assertIn("workroot context --agent codex --cwd .", agents.read_text(encoding="utf-8"))
            self.assertIn("workroot context --agent claude --cwd .", claude.read_text(encoding="utf-8"))

    def test_init_native_agent_entry_flags_are_mutually_exclusive(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            result = run_workroot_cli(
                {"AI_WORKROOT_HOME": str(base / "home")},
                "init",
                "--name",
                "Bad Flags",
                "--directory",
                str(base / "project"),
                "--native-agent-entry",
                "--no-native-agent-entry",
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("not allowed with argument", result.stderr)


if __name__ == "__main__":
    unittest.main()
