from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ai_workroot.entrypoints.native_agent.native import (
    NativeAgentEntryError,
    apply_managed_block,
    codex_block,
    render_native_agent_entry,
    validate_entry_content,
)


class WorkrootAgentEntryTest(unittest.TestCase):
    def test_codex_block_uses_relative_sync_command(self) -> None:
        block = codex_block()
        self.assertIn(
            'workroot agent sync --agent codex --cwd . --query "<current user request>" --format packet',
            block,
        )
        self.assertIn("Start each meaningful user turn", block)
        self.assertIn("Optional: add `--work-signal` with stable enum fields when clear", block)
        self.assertIn("Direct answer: work_kind=quick, intended_action=answer", block)
        self.assertIn("Continuation, checkpoint, handoff, or continuing inbox: work_kind=continuation", block)
        self.assertIn("Decision in current work: work_kind=decision", block)
        self.assertIn("Current file: work_kind=authoring", block)
        self.assertIn("Separate long-running work: phase=starting, work_kind=task", block)
        self.assertIn("New loose side thought: phase=switching, work_kind=inbox", block)
        self.assertIn("Do not use boundary=separate_work for quick answers", block)
        self.assertIn("boundary=separate_work", block)
        self.assertIn("For recall inside a normal user turn, use sync", block)
        self.assertIn(
            "Use `workroot context` only for startup, recovery, or debugging outside the normal turn loop", block
        )
        self.assertIn('"intended_action":"inspect"', block)
        self.assertIn('"concerns":["needs_evidence"]', block)
        self.assertIn("rationale, source, proof, citation, or original detail", block)
        self.assertIn("<!-- AI_WORKROOT_BEGIN -->", block)
        self.assertIn("<!-- AI_WORKROOT_END -->", block)
        self.assertIn("Use Workroot guidance privately", block)
        self.assertIn("keep helping the user", block)
        self.assertLessEqual(len(block.splitlines()), 13)
        self.assertNotIn(str(Path.home()), block)
        self.assertNotIn(".ai-workroot/workroots", block)
        self.assertLess(len(block.encode("utf-8")), 3 * 1024)

    def test_unknown_safe_agent_uses_generic_sync_first_entry(self) -> None:
        block = render_native_agent_entry("cursor")

        self.assertIn(
            'workroot agent sync --agent cursor --cwd . --query "<current user request>" --format packet',
            block,
        )
        self.assertIn("boundary=separate_work", block)
        self.assertIn("Direct answer: work_kind=quick, intended_action=answer", block)
        self.assertIn("Do not use boundary=separate_work for quick answers", block)
        self.assertIn("Use Workroot guidance privately", block)
        self.assertNotIn("unsupported Native Agent Entry", block)
        self.assertLess(len(block.encode("utf-8")), 3 * 1024)

    def test_unknown_unsafe_agent_descriptor_is_rejected(self) -> None:
        with self.assertRaises(NativeAgentEntryError):
            render_native_agent_entry("bad agent; rm -rf")

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
