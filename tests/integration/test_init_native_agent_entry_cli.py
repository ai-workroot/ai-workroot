from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from contextlib import redirect_stderr
import io
from unittest.mock import patch

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
            self.assertRegex(result.stdout, r"^initialized wr_demo_[a-z0-9]{8} agent-ready\n$")
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

    def test_init_native_agent_entry_write_failure_returns_clean_cli_error(self) -> None:
        from ai_workroot.entrypoints.cli.main import main

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            user_dir.mkdir()
            with patch.dict("os.environ", {"AI_WORKROOT_HOME": str(home)}):
                with patch(
                    "ai_workroot.entrypoints.cli.main._sync_native_agent_entries",
                    side_effect=OSError("entry write failed"),
                ):
                    stderr = io.StringIO()
                    with redirect_stderr(stderr):
                        with self.assertRaises(SystemExit) as raised:
                            main(
                                [
                                    "init",
                                    "--name",
                                    "Demo",
                                    "--directory",
                                    str(user_dir),
                                    "--native-agent-entry",
                                ]
                            )

            self.assertEqual(raised.exception.code, 1)
            self.assertEqual(stderr.getvalue(), "entry write failed\n")
            self.assertFalse((home / "registry/workroots.jsonl").read_text(encoding="utf-8").strip())
            self.assertFalse((home / "registry/directory-bindings.jsonl").read_text(encoding="utf-8").strip())
            self.assertEqual(list((home / "workroots").iterdir()), [])
            self.assertFalse((user_dir / "AGENTS.md").exists())
            self.assertFalse((user_dir / "CLAUDE.md").exists())

            with patch.dict("os.environ", {"AI_WORKROOT_HOME": str(home)}):
                stdout = io.StringIO()
                with patch("sys.stdout", stdout):
                    exit_code = main(
                        [
                            "init",
                            "--name",
                            "Demo",
                            "--directory",
                            str(user_dir),
                            "--native-agent-entry",
                        ]
                    )

            self.assertEqual(exit_code, 0)
            self.assertIn("agent-ready", stdout.getvalue())
            self.assertTrue((user_dir / "AGENTS.md").exists())
            self.assertTrue((user_dir / "CLAUDE.md").exists())

    def test_init_native_agent_entry_write_failure_restores_partial_entry_files(self) -> None:
        from ai_workroot.entrypoints.cli.main import main

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            user_dir.mkdir()
            existing_agents = "# User Notes\n\nKeep this content.\n"
            (user_dir / "AGENTS.md").write_text(existing_agents, encoding="utf-8")

            def sync_partial_then_fail(path: Path, agent: str) -> None:
                if agent == "codex":
                    path.write_text("partial native entry\n", encoding="utf-8")
                    return
                raise OSError("claude entry write failed")

            with patch.dict("os.environ", {"AI_WORKROOT_HOME": str(home)}):
                with patch(
                    "ai_workroot.entrypoints.cli.main.sync_native_agent_entry",
                    side_effect=sync_partial_then_fail,
                ):
                    stderr = io.StringIO()
                    with redirect_stderr(stderr):
                        with self.assertRaises(SystemExit) as raised:
                            main(
                                [
                                    "init",
                                    "--name",
                                    "Demo",
                                    "--directory",
                                    str(user_dir),
                                    "--native-agent-entry",
                                ]
                            )

            self.assertEqual(raised.exception.code, 1)
            self.assertEqual(stderr.getvalue(), "claude entry write failed\n")
            self.assertFalse((home / "registry/workroots.jsonl").read_text(encoding="utf-8").strip())
            self.assertFalse((home / "registry/directory-bindings.jsonl").read_text(encoding="utf-8").strip())
            self.assertEqual((user_dir / "AGENTS.md").read_text(encoding="utf-8"), existing_agents)
            self.assertFalse((user_dir / "CLAUDE.md").exists())

    def test_init_native_agent_entry_write_failure_is_not_masked_by_rollback_failure(self) -> None:
        from ai_workroot.entrypoints.cli.main import main

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            user_dir.mkdir()
            with patch.dict("os.environ", {"AI_WORKROOT_HOME": str(home)}):
                with (
                    patch(
                        "ai_workroot.entrypoints.cli.main._sync_native_agent_entries",
                        side_effect=OSError("entry write failed"),
                    ),
                    patch(
                        "ai_workroot.entrypoints.cli.main.rollback_initialized_workroot",
                        side_effect=OSError("rollback failed"),
                    ),
                ):
                    stderr = io.StringIO()
                    with redirect_stderr(stderr):
                        with self.assertRaises(SystemExit) as raised:
                            main(
                                [
                                    "init",
                                    "--name",
                                    "Demo",
                                    "--directory",
                                    str(user_dir),
                                    "--native-agent-entry",
                                ]
                            )

            self.assertEqual(raised.exception.code, 1)
            self.assertTrue(stderr.getvalue().startswith("entry write failed\n"))
            self.assertIn(
                "warning: cleanup after Native Agent Entry failure also failed: rollback failed", stderr.getvalue()
            )

    def test_init_native_agent_entry_write_failure_is_not_masked_by_entry_restore_failure(self) -> None:
        from ai_workroot.entrypoints.cli.main import main

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            user_dir.mkdir()

            def sync_partial_then_fail(path: Path, agent: str) -> None:
                if agent == "codex":
                    path.write_text("partial native entry\n", encoding="utf-8")
                    return
                raise OSError("claude entry write failed")

            with patch.dict("os.environ", {"AI_WORKROOT_HOME": str(home)}):
                with (
                    patch(
                        "ai_workroot.entrypoints.cli.main.sync_native_agent_entry",
                        side_effect=sync_partial_then_fail,
                    ),
                    patch(
                        "ai_workroot.entrypoints.cli.main._restore_native_agent_entry_snapshots",
                        side_effect=OSError("entry restore failed"),
                    ),
                ):
                    stderr = io.StringIO()
                    with redirect_stderr(stderr):
                        with self.assertRaises(SystemExit) as raised:
                            main(
                                [
                                    "init",
                                    "--name",
                                    "Demo",
                                    "--directory",
                                    str(user_dir),
                                    "--native-agent-entry",
                                ]
                            )

            self.assertEqual(raised.exception.code, 1)
            self.assertTrue(stderr.getvalue().startswith("claude entry write failed\n"))
            self.assertIn(
                "warning: cleanup after Native Agent Entry partial write also failed: entry restore failed",
                stderr.getvalue(),
            )


if __name__ == "__main__":
    unittest.main()
