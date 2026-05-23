from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from ai_workroot.agent.native_entry import (
    MANAGED_BLOCK_BEGIN,
    MANAGED_BLOCK_END,
    render_native_agent_entry,
    sync_native_agent_entry,
)
from ai_workroot.runtime.bootstrap import bootstrap_dev


ROOT = Path(__file__).resolve().parents[2]


class NativeAgentEntryTest(unittest.TestCase):
    def test_templates_render_short_relative_agent_context_commands(self) -> None:
        cases = {
            "codex": "AGENTS.md",
            "claude": "CLAUDE.md",
        }

        for agent, filename in cases.items():
            with self.subTest(agent=agent):
                rendered = render_native_agent_entry(agent)
                self.assertIn(f"workroot context --agent {agent} --cwd .", rendered)
                self.assertIn(MANAGED_BLOCK_BEGIN, rendered)
                self.assertIn(MANAGED_BLOCK_END, rendered)
                self.assertLess(len(rendered.encode("utf-8")), 2048)
                self.assertNotIn(str(Path.home()), rendered)
                self.assertNotIn("AI_WORKROOT_HOME", rendered)
                self.assertNotIn("workroot_id", rendered)
                self.assertNotIn("logs", rendered.lower())
                self.assertNotIn("indexes", rendered.lower())
                self.assertNotIn("handoffs", rendered.lower())
                self.assertNotIn("context package history", rendered.lower())
                self.assertTrue(filename.endswith(".md"))

    def test_sync_native_agent_entry_preserves_user_content_outside_managed_block(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "AGENTS.md"
            path.write_text("# User Notes\n\nUser content mentions logs/ and indexes/.\n", encoding="utf-8")

            sync_native_agent_entry(path, "codex")

            text = path.read_text(encoding="utf-8")
            self.assertIn("# User Notes", text)
            self.assertIn("User content mentions logs/ and indexes/.", text)
            self.assertEqual(text.count(MANAGED_BLOCK_BEGIN), 1)
            self.assertEqual(text.count(MANAGED_BLOCK_END), 1)
            self.assertIn("workroot context --agent codex --cwd .", text)


class BootstrapDevReplacementTest(unittest.TestCase):
    def make_minimal_repo(self, repo: Path) -> None:
        repo.mkdir(parents=True)
        (repo / "src").mkdir()
        (repo / "scripts").mkdir()
        (repo / "workroot.project.json").write_text(
            (
                "{\n"
                '  "project": "ai-workroot",\n'
                '  "bootstrapDevSupported": true,\n'
                '  "architecture": "clean-workroot",\n'
                '  "version": "0.9.530"\n'
                "}\n"
            ),
            encoding="utf-8",
        )
        (repo / ".gitignore").write_text(".DS_Store\n", encoding="utf-8")

    def test_bootstrap_dev_uses_project_marker_not_public_seed_root_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            home = Path(tmp) / "home"
            self.make_minimal_repo(repo)

            result = bootstrap_dev(repo, ai_workroot_home=home)

            self.assertEqual(result.status, "initialized")
            self.assertEqual(result.workroot_id, "wr_ai_workroot")
            self.assertTrue((home / "workroots/wr_ai_workroot/workroot.json").is_file())
            self.assertTrue((home / "workroots/wr_ai_workroot/cache/workroot.sqlite").is_file())
            self.assertTrue((repo / ".ai-workroot-local/context-packages").is_dir())
            self.assertIn("/AGENTS.md", (repo / ".gitignore").read_text(encoding="utf-8"))
            self.assertIn("/CLAUDE.md", (repo / ".gitignore").read_text(encoding="utf-8"))
            self.assertIn("/.ai-workroot-local/", (repo / ".gitignore").read_text(encoding="utf-8"))
            self.assertIn("workroot context --agent codex --cwd .", (repo / "AGENTS.md").read_text(encoding="utf-8"))
            self.assertIn("workroot context --agent claude --cwd .", (repo / "CLAUDE.md").read_text(encoding="utf-8"))

    def test_bootstrap_dev_is_idempotent_for_same_marker_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            home = Path(tmp) / "home"
            self.make_minimal_repo(repo)

            first = bootstrap_dev(repo, ai_workroot_home=home)
            second = bootstrap_dev(repo, ai_workroot_home=home)

            self.assertEqual(first.status, "initialized")
            self.assertEqual(second.status, "reused")
            records = [
                line
                for line in (home / "registry/workroots.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            self.assertEqual(len(records), 1)

    def test_bootstrap_dev_shell_wrapper_uses_new_package_entrypoint(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            home = Path(tmp) / "home"
            self.make_minimal_repo(repo)

            result = subprocess.run(
                [str(ROOT / "scripts/dev/bootstrap-dev.sh")],
                cwd=repo,
                env={**os.environ, "PYTHONPATH": str(ROOT / "src"), "AI_WORKROOT_HOME": str(home)},
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("bootstrap-dev initialized wr_ai_workroot", result.stdout)
            self.assertTrue((home / "workroots/wr_ai_workroot/cache/workroot.sqlite").is_file())


if __name__ == "__main__":
    unittest.main()
