from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.fixtures.public_seed import copy_repo_with_public_seed


ROOT = Path(__file__).resolve().parents[1]

TASK_REGISTRY_HEADER = (
    "task_id,title,status,process_level,owner_scope,visibility,priority,"
    "created_at,updated_at,user_visible_output_path,source_path,brief_path,"
    "handoff_path,next_action\n"
)


def task_registry_row(
    task_id: str,
    title: str,
    status: str = "active",
    process_level: str = "L0",
    updated_at: str = "2026-05-14T02:00:00Z",
    user_visible_output_path: str = "",
) -> str:
    source_path = f".workroot/runtime/work/tasks/{task_id}"
    return (
        f"{task_id},{title},{status},{process_level},personal,private,,"
        f"2026-05-14T00:00:00Z,{updated_at},{user_visible_output_path},"
        f"{source_path},{source_path}/brief.md,{source_path}/handoff.md,\n"
    )


class ListTasksScriptTest(unittest.TestCase):
    def test_empty_seed_outputs_no_tasks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / "workroot"
            copy_repo_with_public_seed(work)
            result = subprocess.run(
                [sys.executable, "scripts/list_tasks.py"],
                cwd=work,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, "No tasks found.\n")

    def test_lists_tasks_in_updated_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / "workroot"
            copy_repo_with_public_seed(work)
            registry = work / ".workroot/runtime/index/task_registry.csv"
            registry.write_text(
                TASK_REGISTRY_HEADER
                + task_registry_row(
                    "task-old",
                    "Old task",
                    status="closed",
                    updated_at="2026-05-14T01:00:00Z",
                    user_visible_output_path="space/work/old.md",
                )
                + task_registry_row(
                    "task-new",
                    "New task",
                    process_level="L1",
                    user_visible_output_path="space/work/new.md",
                ),
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, "scripts/list_tasks.py", "--format", "json"],
                cwd=work,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            rows = json.loads(result.stdout)
            self.assertEqual([row["task_id"] for row in rows], ["task-new", "task-old"])

    def test_filters_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / "workroot"
            copy_repo_with_public_seed(work)
            registry = work / ".workroot/runtime/index/task_registry.csv"
            registry.write_text(
                TASK_REGISTRY_HEADER
                + task_registry_row(
                    "task-active",
                    "Active task",
                    user_visible_output_path="space/work/active.md",
                )
                + task_registry_row(
                    "task-closed",
                    "Closed task",
                    status="closed",
                    updated_at="2026-05-14T01:00:00Z",
                    user_visible_output_path="space/work/closed.md",
                ),
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, "scripts/list_tasks.py", "--status", "closed", "--format", "json"],
                cwd=work,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            rows = json.loads(result.stdout)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["task_id"], "task-closed")

    def test_markdown_output_hides_internal_handoff_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / "workroot"
            copy_repo_with_public_seed(work)
            task_dir = work / ".workroot/runtime/work/tasks/task-study"
            task_dir.mkdir(parents=True)
            (task_dir / "handoff.md").write_text(
                "# Handoff\n\n## Continue With\n\nPractice five fraction questions.\n",
                encoding="utf-8",
            )
            registry = work / ".workroot/runtime/index/task_registry.csv"
            registry.write_text(
                TASK_REGISTRY_HEADER
                + task_registry_row(
                    "task-study",
                    "Study fractions",
                    process_level="L1",
                    user_visible_output_path="space/work/reports/fractions.md",
                ),
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, "scripts/list_tasks.py"],
                cwd=work,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Practice five fraction questions.", result.stdout)
            self.assertIn("reports/fractions.md", result.stdout)
            self.assertNotIn(".workroot", result.stdout)
            self.assertNotIn("handoff.md", result.stdout)

    def test_reads_next_actions_heading(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / "workroot"
            copy_repo_with_public_seed(work)
            task_dir = work / ".workroot/runtime/work/tasks/task-next-actions"
            task_dir.mkdir(parents=True)
            (task_dir / "handoff.md").write_text(
                "# Handoff\n\n## Next Actions\n\n- Review the new draft.\n",
                encoding="utf-8",
            )
            registry = work / ".workroot/runtime/index/task_registry.csv"
            registry.write_text(
                TASK_REGISTRY_HEADER
                + task_registry_row(
                    "task-next-actions",
                    "Next actions task",
                    process_level="L1",
                    user_visible_output_path="space/work/next.md",
                ),
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, "scripts/list_tasks.py"],
                cwd=work,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Review the new draft.", result.stdout)

    def test_reads_continue_heading(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / "workroot"
            copy_repo_with_public_seed(work)
            task_dir = work / ".workroot/runtime/work/tasks/task-continue"
            task_dir.mkdir(parents=True)
            (task_dir / "handoff.md").write_text(
                "# Handoff\n\n## Continue\n\nResume the analysis.\n",
                encoding="utf-8",
            )
            registry = work / ".workroot/runtime/index/task_registry.csv"
            registry.write_text(
                TASK_REGISTRY_HEADER
                + task_registry_row(
                    "task-continue",
                    "Continue task",
                    process_level="L1",
                    user_visible_output_path="space/work/continue-report.md",
                ),
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, "scripts/list_tasks.py"],
                cwd=work,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Resume the analysis.", result.stdout)

    def test_lists_legacy_active_path_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / "workroot"
            copy_repo_with_public_seed(work)
            task_dir = work / ".workroot/runtime/work/active/task-legacy"
            task_dir.mkdir(parents=True)
            (task_dir / "handoff.md").write_text(
                "# Handoff\n\n## Next Step\n\nLegacy next.\n",
                encoding="utf-8",
            )
            registry = work / ".workroot/runtime/index/task_registry.csv"
            registry.write_text(
                "task_id,title,status,owner_scope,visibility,created_at,updated_at,user_visible_output_path,source_path,handoff_path\n"
                "task-legacy,Legacy task,active,personal,private,2026-05-14T00:00:00Z,2026-05-14T02:00:00Z,,.workroot/runtime/work/active/task-legacy,.workroot/runtime/work/active/task-legacy/handoff.md\n",
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, "scripts/list_tasks.py"],
                cwd=work,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Legacy next.", result.stdout)

    def test_uses_source_path_when_handoff_column_is_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / "workroot"
            copy_repo_with_public_seed(work)
            task_dir = work / ".workroot/runtime/work/tasks/task-fallback"
            task_dir.mkdir(parents=True)
            (task_dir / "handoff.md").write_text(
                "# Handoff\n\n## Next Step\n\nFallback next.\n",
                encoding="utf-8",
            )
            registry = work / ".workroot/runtime/index/task_registry.csv"
            registry.write_text(
                "task_id,title,status,process_level,owner_scope,visibility,priority,created_at,updated_at,user_visible_output_path,source_path,brief_path,handoff_path,next_action\n"
                "task-fallback,Fallback task,active,L0,personal,private,,2026-05-14T00:00:00Z,2026-05-14T02:00:00Z,,.workroot/runtime/work/tasks/task-fallback,,,\n",
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, "scripts/list_tasks.py"],
                cwd=work,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Fallback next.", result.stdout)


if __name__ == "__main__":
    unittest.main()
