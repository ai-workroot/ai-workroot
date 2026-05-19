from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts/workroot_cli.py"


class WorkrootInitCliTest(unittest.TestCase):
    def run_cli(self, env: dict[str, str], *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(CLI), *args],
            cwd=ROOT,
            env={**os.environ, **env},
            text=True,
            capture_output=True,
            check=False,
        )

    def test_init_creates_clean_mode_state_outside_user_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            user_dir.mkdir()
            result = self.run_cli(
                {"AI_WORKROOT_HOME": str(home)},
                "init",
                "--name",
                "Demo Workroot",
                "--directory",
                str(user_dir),
                "--no-native-agent-entry",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            state_path = home / "workroots/wr_demo_workroot/workroot.json"
            self.assertTrue(state_path.exists())
            self.assertFalse((user_dir / ".workroot").exists())
            self.assertFalse((user_dir / ".ai-workroot").exists())
            self.assertFalse((user_dir / "context").exists())
            self.assertFalse((user_dir / "runtime").exists())
            payload = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["mode"], "clean")

    def test_list_and_status_show_registered_workroot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            user_dir.mkdir()
            env = {"AI_WORKROOT_HOME": str(home)}
            init = self.run_cli(
                env,
                "init",
                "--name",
                "Demo Workroot",
                "--directory",
                str(user_dir),
                "--no-native-agent-entry",
            )
            self.assertEqual(init.returncode, 0, init.stderr)
            listed = self.run_cli(env, "list")
            self.assertEqual(listed.returncode, 0, listed.stderr)
            self.assertIn("wr_demo_workroot", listed.stdout)
            status = self.run_cli(env, "status", "--cwd", str(user_dir))
            self.assertEqual(status.returncode, 0, status.stderr)
            self.assertIn("wr_demo_workroot", status.stdout)

    def test_init_native_agent_entry_requires_explicit_authorization(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            user_dir.mkdir()
            result = self.run_cli(
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


if __name__ == "__main__":
    unittest.main()
