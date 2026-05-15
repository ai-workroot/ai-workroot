from __future__ import annotations

import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_client_module():
    spec = importlib.util.spec_from_file_location("workroot_client", ROOT / "scripts/workroot_client.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load workroot_client.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class WorkrootClientTest(unittest.TestCase):
    def copy_workroot(self) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        tmp = tempfile.TemporaryDirectory()
        work = Path(tmp.name) / "workroot"
        shutil.copytree(
            ROOT,
            work,
            ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
        )
        return tmp, work

    def test_create_l0_task_uses_stable_tasks_path(self) -> None:
        tmp, work = self.copy_workroot()
        with tmp:
            client_mod = load_client_module()
            client = client_mod.WorkrootClient(work)
            created = client.create_task(
                title="Test task",
                task_id="task-test",
                goal="Test goal",
                why="Test why",
                expected="Test result",
                next_action="Do next thing",
                owner_scope="personal",
                visibility="internal",
                created_at="2026-05-15T00:00:00Z",
            )
            self.assertEqual(created.task_id, "task-test")
            self.assertEqual(created.process_level, "L0")
            self.assertEqual(
                created.source_path,
                ".workroot/runtime/work/tasks/task-test",
            )
            task_dir = work / created.source_path
            self.assertTrue((task_dir / "task.json").exists())
            self.assertTrue((task_dir / "outputs").is_dir())
            self.assertTrue((task_dir / "archive").is_dir())
            self.assertFalse((task_dir / "plans").exists())
            payload = json.loads((task_dir / "task.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["process_level"], "L0")
            registry = (work / ".workroot/runtime/index/task_registry.csv").read_text(encoding="utf-8")
            self.assertIn("process_level", registry.splitlines()[0])
            self.assertIn(".workroot/runtime/work/tasks/task-test", registry)

    def test_create_l1_task_adds_process_directories(self) -> None:
        tmp, work = self.copy_workroot()
        with tmp:
            client_mod = load_client_module()
            client = client_mod.WorkrootClient(work)
            created = client.create_task(
                title="Process task",
                task_id="task-process",
                process_level="L1",
                created_at="2026-05-15T00:00:00Z",
            )
            task_dir = work / created.source_path
            for name in ("plans", "runs", "outputs", "retrieval_cards", "checkpoints", "archive"):
                self.assertTrue((task_dir / name).is_dir(), name)
            self.assertFalse((task_dir / "actions").exists())

    def test_create_l2_task_adds_evidence_directories(self) -> None:
        tmp, work = self.copy_workroot()
        with tmp:
            client_mod = load_client_module()
            client = client_mod.WorkrootClient(work)
            created = client.create_task(
                title="Evidence task",
                task_id="task-evidence",
                process_level="L2",
                created_at="2026-05-15T00:00:00Z",
            )
            task_dir = work / created.source_path
            for name in (
                "plans",
                "runs",
                "actions",
                "recipes",
                "outputs",
                "data",
                "validation",
                "invalidations",
                "retrieval_cards",
                "checkpoints",
                "archive",
            ):
                self.assertTrue((task_dir / name).is_dir(), name)
            self.assertFalse((task_dir / "artifacts").exists())

    def test_add_process_records_updates_registries_and_files(self) -> None:
        tmp, work = self.copy_workroot()
        with tmp:
            client_mod = load_client_module()
            client = client_mod.WorkrootClient(work)
            client.create_task(
                title="Evidence task",
                task_id="task-evidence",
                process_level="L2",
                created_at="2026-05-15T00:00:00Z",
            )
            run = client.add_run(
                task_id="task-evidence",
                run_id="run-001",
                title="First run",
                status="completed",
                started_at="2026-05-15T00:00:00Z",
                completed_at="2026-05-15T00:01:00Z",
                conclusion_preview="Validation passed.",
            )
            action = client.add_action(
                task_id="task-evidence",
                action_id="action-001",
                run_id=run.run_id,
                type="test_run",
                status="completed",
                summary="Ran validation.",
                created_at="2026-05-15T00:01:00Z",
            )
            artifact = client.add_artifact(
                artifact_id="artifact-001",
                task_id="task-evidence",
                run_id=run.run_id,
                action_id=action.action_id,
                type="validation_log",
                path=run.path,
                audience="internal",
                status="active",
                created_at="2026-05-15T00:01:00Z",
            )
            card = client.add_retrieval_card(
                task_id="task-evidence",
                card_id="card-001",
                freshness="hot",
                source_paths=run.path,
                created_at="2026-05-15T00:01:00Z",
            )
            checkpoint = client.add_checkpoint(
                task_id="task-evidence",
                checkpoint_id="checkpoint-001",
                current_status="active",
                last_valid_run_id=run.run_id,
                next_action="Continue implementation.",
                required_context_paths=card.path,
                created_at="2026-05-15T00:01:00Z",
            )
            invalidation = client.add_invalidation(
                task_id="task-evidence",
                invalidation_id="invalidation-001",
                invalidated_claim="Old claim",
                reason="Superseded by test.",
                path="",
                created_at="2026-05-15T00:01:00Z",
            )
            for record in (run, action, artifact, card, checkpoint, invalidation):
                self.assertTrue(record.id)
            self.assertTrue((work / run.path).exists())
            self.assertTrue((work / action.path).exists())
            self.assertTrue((work / card.path).exists())
            self.assertTrue((work / checkpoint.path).exists())
            self.assertTrue((work / invalidation.path).exists())
            self.assertIn("run-001", (work / ".workroot/runtime/index/run_registry.csv").read_text(encoding="utf-8"))
            self.assertIn("action-001", (work / ".workroot/runtime/index/action_registry.csv").read_text(encoding="utf-8"))
            self.assertIn("artifact-001", (work / ".workroot/runtime/index/artifact_registry.csv").read_text(encoding="utf-8"))
            self.assertIn("card-001", (work / ".workroot/runtime/index/retrieval_card_registry.csv").read_text(encoding="utf-8"))
            self.assertIn("checkpoint-001", (work / ".workroot/runtime/index/checkpoint_registry.csv").read_text(encoding="utf-8"))
            self.assertIn("invalidation-001", (work / ".workroot/runtime/index/invalidation_registry.csv").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
