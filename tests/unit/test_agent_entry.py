from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ai_workroot.entrypoints.native_agent.native import (
    NativeAgentEntryError,
    apply_managed_block,
    codex_block,
    validate_entry_content,
)


class WorkrootAgentEntryTest(unittest.TestCase):
    def test_codex_block_uses_relative_context_command(self) -> None:
        block = codex_block()
        self.assertIn("workroot context --agent codex --cwd .", block)
        self.assertIn("<!-- AI_WORKROOT_BEGIN -->", block)
        self.assertIn("<!-- AI_WORKROOT_END -->", block)
        self.assertIn("Use Workroot guidance privately", block)
        self.assertIn("keep helping the user", block)
        self.assertNotIn(str(Path.home()), block)
        self.assertNotIn(".ai-workroot/workroots", block)
        self.assertLess(len(block.encode("utf-8")), 2 * 1024)

    def test_apply_block_preserves_user_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "AGENTS.md"
            path.write_text("# Existing\n\nKeep me.\n", encoding="utf-8")
            apply_managed_block(path, codex_block())
            text = path.read_text(encoding="utf-8")
            self.assertIn("Keep me.", text)
            self.assertIn("<!-- AI_WORKROOT_BEGIN -->", text)
            self.assertIn("<!-- AI_WORKROOT_END -->", text)

    def test_validate_rejects_absolute_state_path(self) -> None:
        with self.assertRaises(NativeAgentEntryError):
            validate_entry_content("state at /Users/example/.ai-workroot/workroots/wr_demo")

    def test_apply_block_does_not_reject_user_owned_existing_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "AGENTS.md"
            path.write_text("# Existing\n\nUser notes may mention logs/ and indexes/.\n", encoding="utf-8")

            apply_managed_block(path, codex_block())

            text = path.read_text(encoding="utf-8")
            self.assertIn("User notes may mention logs/ and indexes/.", text)
            self.assertIn("<!-- AI_WORKROOT_BEGIN -->", text)


if __name__ == "__main__":
    unittest.main()
