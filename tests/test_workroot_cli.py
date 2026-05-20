from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
import csv
import hashlib
import json
from pathlib import Path

from tests.fixtures.public_seed import copy_repo_with_public_seed


ROOT = Path(__file__).resolve().parents[1]


class WorkrootCliTest(unittest.TestCase):
    def copy_workroot(self, tmp: str) -> Path:
        work = Path(tmp) / "workroot"
        copy_repo_with_public_seed(work)
        return work

    def run_cli(self, work: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "scripts/workroot_cli.py", *args],
            cwd=work,
            text=True,
            capture_output=True,
            check=False,
        )

    def create_task(self, work: Path, task_id: str = "task-cli", level: str = "L1") -> None:
        create = self.run_cli(
            work,
            "task",
            "create",
            "CLI task",
            "--id",
            task_id,
            "--process-level",
            level,
            "--created-at",
            "2026-05-15T00:00:00Z",
        )
        self.assertEqual(create.returncode, 0, create.stderr)

    def test_cli_creates_l1_task(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = self.copy_workroot(tmp)
            result = self.run_cli(
                work,
                "task",
                "create",
                "CLI task",
                "--id",
                "task-cli",
                "--process-level",
                "L1",
                "--created-at",
                "2026-05-15T00:00:00Z",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(".workroot/runtime/work/tasks/task-cli", result.stdout)
            self.assertTrue((work / ".workroot/runtime/work/tasks/task-cli/plans").is_dir())

    def test_cli_adds_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = self.copy_workroot(tmp)
            self.create_task(work)
            result = self.run_cli(
                work,
                "run",
                "add",
                "--task-id",
                "task-cli",
                "--run-id",
                "run-cli",
                "--title",
                "CLI run",
                "--status",
                "completed",
                "--started-at",
                "2026-05-15T00:01:00Z",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("run-cli", result.stdout)
            self.assertTrue((work / ".workroot/runtime/work/tasks/task-cli/runs/run-cli.md").exists())

    def test_cli_updates_task_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = self.copy_workroot(tmp)
            self.create_task(work)
            result = self.run_cli(
                work,
                "task",
                "update",
                "--task-id",
                "task-cli",
                "--status",
                "paused",
                "--updated-at",
                "2026-05-15T00:02:00Z",
                "--next-action",
                "Resume from the saved report.",
                "--user-visible-output-path",
                "space/work/reports/task-cli.md",
                "--brief-current-state",
                "The report draft exists.",
                "--brief-latest-result",
                "Saved the draft report.",
                "--handoff-status",
                "Paused after report draft.",
                "--handoff-latest-result",
                "Draft report is ready.",
                "--index-output",
                "space/work/reports/task-cli.md",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads((work / ".workroot/runtime/work/tasks/task-cli/task.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "paused")
            with (work / ".workroot/runtime/index/task_registry.csv").open(newline="", encoding="utf-8") as f:
                row = next(csv.DictReader(f))
            self.assertEqual(row["next_action"], "Resume from the saved report.")
            self.assertIn(
                "The report draft exists.",
                (work / ".workroot/runtime/work/tasks/task-cli/brief.md").read_text(encoding="utf-8"),
            )

    def test_cli_updates_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = self.copy_workroot(tmp)
            self.create_task(work)
            add = self.run_cli(
                work,
                "run",
                "add",
                "--task-id",
                "task-cli",
                "--run-id",
                "run-cli",
                "--title",
                "CLI run",
                "--started-at",
                "2026-05-15T00:01:00Z",
            )
            self.assertEqual(add.returncode, 0, add.stderr)
            result = self.run_cli(
                work,
                "run",
                "update",
                "--run-id",
                "run-cli",
                "--status",
                "completed",
                "--validity",
                "valid",
                "--completed-at",
                "2026-05-15T00:03:00Z",
                "--conclusion-preview",
                "CLI validation passed.",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            with (work / ".workroot/runtime/index/run_registry.csv").open(newline="", encoding="utf-8") as f:
                row = next(csv.DictReader(f))
            self.assertEqual(row["status"], "completed")
            self.assertEqual(row["validity"], "valid")
            self.assertEqual(row["completed_at"], "2026-05-15T00:03:00Z")

    def test_cli_artifact_add_can_create_file_and_compute_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = self.copy_workroot(tmp)
            self.create_task(work)
            result = self.run_cli(
                work,
                "artifact",
                "add",
                "--artifact-id",
                "artifact-cli",
                "--task-id",
                "task-cli",
                "--type",
                "report",
                "--path",
                "space/work/reports/cli-artifact.md",
                "--audience",
                "user",
                "--created-at",
                "2026-05-15T00:02:00Z",
                "--create-file",
                "--content",
                "# CLI Artifact\n",
                "--compute-metadata",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            artifact_file = work / "space/work/reports/cli-artifact.md"
            self.assertTrue(artifact_file.exists())
            expected_checksum = "sha256:" + hashlib.sha256(artifact_file.read_bytes()).hexdigest()
            with (work / ".workroot/runtime/index/artifact_registry.csv").open(newline="", encoding="utf-8") as f:
                row = next(csv.DictReader(f))
            self.assertEqual(row["size"], str(artifact_file.stat().st_size))
            self.assertEqual(row["checksum"], expected_checksum)

    def test_cli_mind_add_writes_file_and_registry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = self.copy_workroot(tmp)
            self.create_task(work)
            result = self.run_cli(
                work,
                "mind",
                "add",
                "--mind-id",
                "mind-cli",
                "--title",
                "CLI lesson",
                "--type",
                "knowledge",
                "--summary",
                "CLI can preserve a reusable lesson.",
                "--related-task-id",
                "task-cli",
                "--created-at",
                "2026-05-15T00:02:00Z",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("space/mind/knowledge/mind-cli.md", result.stdout)
            self.assertTrue((work / "space/mind/knowledge/mind-cli.md").exists())
            with (work / ".workroot/runtime/index/mind_registry.csv").open(newline="", encoding="utf-8") as f:
                row = next(csv.DictReader(f))
            self.assertEqual(row["mind_id"], "mind-cli")
            self.assertEqual(row["related_task_id"], "task-cli")

    def test_cli_mind_add_path_and_from_path_do_not_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = self.copy_workroot(tmp)
            self.create_task(work)
            source = work / "space/work/reports/source.md"
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_text("# Source\n", encoding="utf-8")
            result = self.run_cli(
                work,
                "mind",
                "add",
                "--mind-id",
                "mind-cli-knowledge",
                "--title",
                "Mind CLI Test Knowledge",
                "--type",
                "knowledge",
                "--path",
                "space/mind/knowledge/custom-mind.md",
                "--from-path",
                "space/work/reports/source.md",
                "--related-task-id",
                "task-cli",
                "--created-at",
                "2026-05-15T00:02:00Z",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((work / "space/mind/knowledge/custom-mind.md").exists())
            links = (work / ".workroot/runtime/index/link_registry.csv").read_text(encoding="utf-8")
            self.assertIn("space/work/reports/source.md", links)
            self.assertIn("mind-cli-knowledge", links)

    def test_continue_rebuild_uses_registry_tasks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = self.copy_workroot(tmp)
            result = self.run_cli(work, "task", "create", "Active Task", "--id", "active-task", "--next", "Do active task.")
            self.assertEqual(result.returncode, 0, result.stderr)
            result = self.run_cli(work, "task", "create", "Closed Task", "--id", "closed-task", "--next", "Review closed task.")
            self.assertEqual(result.returncode, 0, result.stderr)
            result = self.run_cli(work, "task", "update", "--task-id", "closed-task", "--status", "closed")
            self.assertEqual(result.returncode, 0, result.stderr)
            result = self.run_cli(work, "continue", "rebuild", "--recent", "2")
            self.assertEqual(result.returncode, 0, result.stderr)
            text = (work / "space/work/continue.md").read_text(encoding="utf-8")
            self.assertIn("Active Task", text)
            self.assertIn("Closed Task", text)

    def test_task_complete_creates_report_artifact_and_closes_task(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = self.copy_workroot(tmp)
            report = work / "report.md"
            report.write_text("# Report\n\nDone.\n", encoding="utf-8")
            result = self.run_cli(work, "task", "create", "Complete Me", "--id", "complete-me")
            self.assertEqual(result.returncode, 0, result.stderr)
            result = self.run_cli(
                work,
                "task",
                "complete",
                "--task-id",
                "complete-me",
                "--report-path",
                "space/work/reports/complete-me.md",
                "--report-content-file",
                str(report),
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((work / "space/work/reports/complete-me.md").exists())
            self.assertIn("complete-me", (work / ".workroot/runtime/index/artifact_registry.csv").read_text(encoding="utf-8"))
            self.assertIn('"status": "closed"', (work / ".workroot/runtime/work/tasks/complete-me/task.json").read_text(encoding="utf-8"))

    def test_batch_apply_creates_common_lightweight_records(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = self.copy_workroot(tmp)
            report = work / "report.md"
            report.write_text("# Batch Report\n", encoding="utf-8")
            batch = work / "batch.json"
            batch.write_text(
                json.dumps(
                    {
                        "operations": [
                            {"op": "task.create", "title": "Batch A", "task_id": "batch-a"},
                            {"op": "task.update", "task_id": "batch-a", "next_action": "Review batch output."},
                            {
                                "op": "artifact.add",
                                "artifact_id": "batch-artifact",
                                "task_id": "batch-a",
                                "path": "space/work/reports/batch-report.md",
                                "content_file": str(report),
                                "audience": "user",
                                "compute_metadata": True,
                            },
                            {
                                "op": "action.add",
                                "action_id": "batch-action",
                                "task_id": "batch-a",
                                "type": "manual_check",
                                "summary": "Reviewed batch output.",
                            },
                            {
                                "op": "checkpoint.add",
                                "checkpoint_id": "batch-checkpoint",
                                "task_id": "batch-a",
                                "current_status": "Batch checkpoint created.",
                                "required_context_paths": ["space/work/reports/batch-report.md", "space/work/reports/extra-context.md"],
                            },
                            {
                                "op": "retrieval_card.add",
                                "card_id": "batch-card",
                                "task_id": "batch-a",
                                "source_paths": "space/work/reports/batch-report.md",
                            },
                            {
                                "op": "session.summarize",
                                "task_ids": ["batch-a"],
                                "summary": "Batch operation complete.",
                                "next_action": "Review batch output.",
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )
            result = self.run_cli(work, "batch", "apply", "--file", str(batch))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("batch-a", (work / ".workroot/runtime/index/task_registry.csv").read_text(encoding="utf-8"))
            self.assertIn("batch-artifact", (work / ".workroot/runtime/index/artifact_registry.csv").read_text(encoding="utf-8"))
            self.assertIn("batch-action", (work / ".workroot/runtime/index/action_registry.csv").read_text(encoding="utf-8"))
            checkpoint_registry = (work / ".workroot/runtime/index/checkpoint_registry.csv").read_text(encoding="utf-8")
            self.assertIn("batch-checkpoint", checkpoint_registry)
            self.assertIn("space/work/reports/batch-report.md;space/work/reports/extra-context.md", checkpoint_registry)
            self.assertNotIn("['space/work/reports/batch-report.md'", checkpoint_registry)
            checkpoint = (work / ".workroot/runtime/work/tasks/batch-a/checkpoints/batch-checkpoint.md").read_text(encoding="utf-8")
            self.assertIn("space/work/reports/batch-report.md;space/work/reports/extra-context.md", checkpoint)
            self.assertIn("batch-card", (work / ".workroot/runtime/index/retrieval_card_registry.csv").read_text(encoding="utf-8"))
            self.assertIn("Batch operation complete.", (work / "space/work/continue.md").read_text(encoding="utf-8"))

    def test_batch_apply_supports_process_mind_and_invalidation_records(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = self.copy_workroot(tmp)
            batch = work / "batch.json"
            batch.write_text(
                json.dumps(
                    {
                        "operations": [
                            {"op": "task.create", "title": "Rich Batch", "task_id": "rich-batch", "process_level": "L2"},
                            {
                                "op": "run.add",
                                "run_id": "rich-run",
                                "task_id": "rich-batch",
                                "title": "Rich batch run",
                                "status": "completed",
                                "validation": "Validated in batch.",
                                "conclusion_preview": "Run finished.",
                                "started_at": "2026-05-15T00:01:00Z",
                                "completed_at": "2026-05-15T00:02:00Z",
                            },
                            {
                                "op": "mind.add",
                                "mind_id": "rich-batch-knowledge",
                                "title": "Rich batch knowledge",
                                "type": "knowledge",
                                "summary": "Batch can promote reusable knowledge.",
                                "related_task_id": "rich-batch",
                                "from_task_ids": ["rich-batch"],
                                "created_at": "2026-05-15T00:03:00Z",
                            },
                            {
                                "op": "invalidation.add",
                                "invalidation_id": "rich-invalidated",
                                "task_id": "rich-batch",
                                "run_id": "rich-run",
                                "invalidated_claim": "Old claim",
                                "reason": "New evidence replaced it.",
                                "created_at": "2026-05-15T00:04:00Z",
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )
            result = self.run_cli(work, "batch", "apply", "--file", str(batch))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("rich-run", (work / ".workroot/runtime/index/run_registry.csv").read_text(encoding="utf-8"))
            self.assertIn("rich-batch-knowledge", (work / ".workroot/runtime/index/mind_registry.csv").read_text(encoding="utf-8"))
            self.assertIn("rich-invalidated", (work / ".workroot/runtime/index/invalidation_registry.csv").read_text(encoding="utf-8"))
            self.assertTrue((work / "space/mind/knowledge/rich-batch-knowledge.md").exists())
            self.assertTrue((work / ".workroot/runtime/work/tasks/rich-batch/invalidations/rich-invalidated.md").exists())

    def test_batch_apply_rolls_back_mind_file_when_later_operation_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = self.copy_workroot(tmp)
            batch = work / "batch.json"
            batch.write_text(
                json.dumps(
                    {
                        "operations": [
                            {"op": "task.create", "title": "Rollback Mind", "task_id": "rollback-mind", "process_level": "L1"},
                            {
                                "op": "mind.add",
                                "mind_id": "rollback-knowledge",
                                "title": "Rollback knowledge",
                                "type": "knowledge",
                                "summary": "This should be rolled back.",
                                "related_task_id": "rollback-mind",
                            },
                            {
                                "op": "artifact.add",
                                "artifact_id": "missing-after-mind",
                                "task_id": "rollback-mind",
                                "path": "space/work/reports/missing-after-mind.md",
                                "compute_metadata": True,
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )
            result = self.run_cli(work, "batch", "apply", "--file", str(batch))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("artifact path does not exist", result.stderr)
            self.assertNotIn("rollback-mind", (work / ".workroot/runtime/index/task_registry.csv").read_text(encoding="utf-8"))
            self.assertNotIn("rollback-knowledge", (work / ".workroot/runtime/index/mind_registry.csv").read_text(encoding="utf-8"))
            self.assertFalse((work / ".workroot/runtime/work/tasks/rollback-mind").exists())
            self.assertFalse((work / "space/mind/knowledge/rollback-knowledge.md").exists())

    def test_batch_apply_rolls_back_when_later_operation_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = self.copy_workroot(tmp)
            batch = work / "batch.json"
            batch.write_text(
                json.dumps(
                    {
                        "operations": [
                            {"op": "task.create", "title": "Rollback A", "task_id": "rollback-a"},
                            {"op": "artifact.add", "artifact_id": "missing-artifact", "task_id": "rollback-a", "path": "space/work/reports/missing.md", "compute_metadata": True},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            result = self.run_cli(work, "batch", "apply", "--file", str(batch))
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn("rollback-a", (work / ".workroot/runtime/index/task_registry.csv").read_text(encoding="utf-8"))
            self.assertFalse((work / ".workroot/runtime/work/tasks/rollback-a").exists())
            transactions = list((work / ".workroot/runtime/transactions").glob("*.json"))
            self.assertTrue(transactions)

    def test_cli_task_update_continue_summary_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = self.copy_workroot(tmp)
            self.create_task(work)
            result = self.run_cli(work, "task", "update", "--task-id", "task-cli", "--continue-summary", "This should not be ignored.")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("session summarize", result.stderr)

    def test_session_summarize_from_registry_avoids_long_task_id_list(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = self.copy_workroot(tmp)
            for task_id in ("registry-a", "registry-b", "registry-c"):
                result = self.run_cli(work, "task", "create", f"Task {task_id}", "--id", task_id)
                self.assertEqual(result.returncode, 0, result.stderr)
            result = self.run_cli(
                work,
                "session",
                "summarize",
                "--from-registry",
                "--recent",
                "3",
                "--summary",
                "Registry-selected tasks were summarized.",
                "--next-action",
                "Review registry-selected work.",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            text = (work / "space/work/continue.md").read_text(encoding="utf-8")
            self.assertIn("Task registry-a", text)
            self.assertIn("Task registry-b", text)
            self.assertIn("Task registry-c", text)
            self.assertIn("Registry-selected tasks were summarized.", text)

    def test_batch_apply_does_not_write_json_null_as_none_string(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = self.copy_workroot(tmp)
            batch = work / "batch.json"
            batch.write_text(
                json.dumps(
                    {
                        "operations": [
                            {"op": "task.create", "title": "Null Field Task", "task_id": "null-field-task", "process_level": "L2"},
                            {
                                "op": "action.add",
                                "action_id": "null-field-action",
                                "task_id": "null-field-task",
                                "type": "manual_check",
                                "run_id": None,
                                "tool": None,
                                "summary": "Checked null handling.",
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )
            result = self.run_cli(work, "batch", "apply", "--file", str(batch))
            self.assertEqual(result.returncode, 0, result.stderr)
            action_registry = (work / ".workroot/runtime/index/action_registry.csv").read_text(encoding="utf-8")
            self.assertNotIn("None", action_registry)

    def test_cli_rejects_future_timestamp_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = self.copy_workroot(tmp)
            result = self.run_cli(
                work,
                "task",
                "create",
                "Future task",
                "--id",
                "task-future",
                "--created-at",
                "2999-01-01T00:00:00Z",
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("future", result.stderr.casefold())
            self.assertNotIn(
                "task-future",
                (work / ".workroot/runtime/index/task_registry.csv").read_text(encoding="utf-8"),
            )


if __name__ == "__main__":
    unittest.main()
