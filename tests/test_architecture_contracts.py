from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


class ArchitectureContractsTest(unittest.TestCase):
    def test_routing_uses_stable_task_directory_not_status_directory(self) -> None:
        text = read(".workroot/kernel/agent/routing.md")
        self.assertIn(".workroot/runtime/work/tasks/<task-id>/", text)
        self.assertNotIn(".workroot/runtime/work/active/", text)

    def test_state_sync_docs_separate_task_local_from_session_global(self) -> None:
        docs = {
            "AGENTS.md": read("AGENTS.md"),
            "docs/product-hardening.md": read("docs/product-hardening.md"),
        }
        for rel, text in docs.items():
            with self.subTest(rel=rel):
                self.assertIn("Task-local", text)
                self.assertIn("Session/global", text)
                self.assertIn("session summarize", text)
                self.assertIn("continue rebuild", text)

    def test_core_architecture_docs_include_agent_operation_layer(self) -> None:
        docs = {
            "docs/architecture.md": read("docs/architecture.md"),
            "docs/architecture-map.md": read("docs/architecture-map.md"),
        }
        for rel, text in docs.items():
            with self.subTest(rel=rel):
                self.assertIn("Agent Operation Layer", text)

    def test_work_model_documents_process_levels(self) -> None:
        text = read("docs/architecture.md")
        self.assertIn("L0", text)
        self.assertIn("L1", text)
        self.assertIn("L2", text)
        self.assertIn("Run", text)
        self.assertIn("Action", text)
        self.assertIn("Checkpoint", text)
        self.assertIn("Retrieval Card", text)
        self.assertIn("Invalidation", text)

    def test_agent_operation_spec_documents_batch_rollback_journal(self) -> None:
        text = read("docs/history/0.9.529/specs/2026-05-15-agent-operation-layer.md")
        self.assertIn(".workroot/runtime/transactions/", text)
        self.assertIn("rolled_back", text)
        self.assertIn(".workroot/runtime/index", text)
        self.assertIn(".workroot/runtime/work/tasks", text)
        self.assertIn("space/work", text)
        self.assertIn("space/mind", text)

    def test_agent_fast_start_prefers_operation_manifest_over_source_code(self) -> None:
        text = read(".workroot/kernel/boot/agent-fast-start.md")
        self.assertIn("operation manifest", text)
        self.assertIn("scripts/workroot_cli.py manifest --format json", text)
        self.assertIn("scripts/workroot_cli.py recipe batch-12-tasks --format json", text)
        self.assertIn("Do not read `scripts/workroot_client.py`", text)


if __name__ == "__main__":
    unittest.main()
