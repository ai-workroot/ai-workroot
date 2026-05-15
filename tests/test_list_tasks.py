from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ListTasksScriptTest(unittest.TestCase):
    def test_empty_seed_outputs_no_tasks(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/list_tasks.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "No tasks found.\n")

    def test_lists_tasks_in_updated_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / "workroot"
            shutil.copytree(
                ROOT,
                work,
                ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
            )
            registry = work / ".workroot/runtime/index/task_registry.csv"
            registry.write_text(
                "task_id,title,status,process_level,owner_scope,visibility,priority,created_at,updated_at,user_visible_output_path,source_path,brief_path,handoff_path,next_action\n"
                "task-old,Old task,closed,L0,personal,private,,2026-05-14T00:00:00Z,2026-05-14T01:00:00Z,space/work/old.md,.workroot/runtime/work/tasks/task-old,.workroot/runtime/work/tasks/task-old/brief.md,.workroot/runtime/work/tasks/task-old/handoff.md,\n"
                "task-new,New task,active,L1,personal,private,,2026-05-14T00:00:00Z,2026-05-14T02:00:00Z,space/work/new.md,.workroot/runtime/work/tasks/task-new,.workroot/runtime/work/tasks/task-new/brief.md,.workroot/runtime/work/tasks/task-new/handoff.md,\n",
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
            shutil.copytree(
                ROOT,
                work,
                ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
            )
            registry = work / ".workroot/runtime/index/task_registry.csv"
            registry.write_text(
                "task_id,title,status,process_level,owner_scope,visibility,priority,created_at,updated_at,user_visible_output_path,source_path,brief_path,handoff_path,next_action\n"
                "task-active,Active task,active,L0,personal,private,,2026-05-14T00:00:00Z,2026-05-14T02:00:00Z,space/work/active.md,.workroot/runtime/work/tasks/task-active,.workroot/runtime/work/tasks/task-active/brief.md,.workroot/runtime/work/tasks/task-active/handoff.md,\n"
                "task-closed,Closed task,closed,L0,personal,private,,2026-05-14T00:00:00Z,2026-05-14T01:00:00Z,space/work/closed.md,.workroot/runtime/work/tasks/task-closed,.workroot/runtime/work/tasks/task-closed/brief.md,.workroot/runtime/work/tasks/task-closed/handoff.md,\n",
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
            shutil.copytree(
                ROOT,
                work,
                ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
            )
            task_dir = work / ".workroot/runtime/work/tasks/task-study"
            task_dir.mkdir(parents=True)
            (task_dir / "handoff.md").write_text(
                "# Handoff\n\n## Continue With\n\nPractice five fraction questions.\n",
                encoding="utf-8",
            )
            registry = work / ".workroot/runtime/index/task_registry.csv"
            registry.write_text(
                "task_id,title,status,process_level,owner_scope,visibility,priority,created_at,updated_at,user_visible_output_path,source_path,brief_path,handoff_path,next_action\n"
                "task-study,Study fractions,active,L1,personal,private,,2026-05-14T00:00:00Z,2026-05-14T02:00:00Z,space/work/reports/fractions.md,.workroot/runtime/work/tasks/task-study,.workroot/runtime/work/tasks/task-study/brief.md,.workroot/runtime/work/tasks/task-study/handoff.md,\n",
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

    def test_lists_legacy_active_path_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / "workroot"
            shutil.copytree(
                ROOT,
                work,
                ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
            )
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
            shutil.copytree(
                ROOT,
                work,
                ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
            )
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
