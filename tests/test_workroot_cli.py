from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class WorkrootCliTest(unittest.TestCase):
    def copy_workroot(self, tmp: str) -> Path:
        work = Path(tmp) / "workroot"
        shutil.copytree(
            ROOT,
            work,
            ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
        )
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
                "--continue-summary",
                "Draft report is ready; resume by reviewing it.",
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
