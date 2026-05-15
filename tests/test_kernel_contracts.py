from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import datetime as dt
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class KernelContractsTest(unittest.TestCase):
    def test_kernel_version(self) -> None:
        version = (ROOT / ".workroot/kernel/VERSION").read_text(encoding="utf-8").strip()
        kernel = json.loads((ROOT / ".workroot/kernel/contracts/kernel.json").read_text(encoding="utf-8"))
        self.assertEqual(kernel["kernel_version"], version)

    def test_required_contracts_are_json(self) -> None:
        for path in (ROOT / ".workroot/kernel/contracts").glob("*.json"):
            with self.subTest(path=path.name):
                data = json.loads(path.read_text(encoding="utf-8"))
                self.assertIn("contract_id", data)

    def test_validate_kernel(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/validate_kernel.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_timezone_free_registry_instant_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / "workroot"
            shutil.copytree(
                ROOT,
                work,
                ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
            )
            registry = work / ".workroot/runtime/index/task_registry.csv"
            registry.write_text(
                registry.read_text(encoding="utf-8")
                + "task-x,Timezone free,active,L0,personal,internal,,2026-05-15T17:00:00,2026-05-15T17:00:00,,,,,\n",
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, "scripts/validate_kernel.py"],
                cwd=work,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("must be UTC ISO-8601 or date-only", result.stderr)

    def test_future_registry_instant_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / "workroot"
            shutil.copytree(
                ROOT,
                work,
                ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
            )
            future = (
                dt.datetime.now(dt.timezone.utc)
                + dt.timedelta(days=1)
            ).replace(microsecond=0).isoformat().replace("+00:00", "Z")
            registry = work / ".workroot/runtime/index/task_registry.csv"
            registry.write_text(
                registry.read_text(encoding="utf-8")
                + f"task-future,Future,active,L0,personal,internal,,{future},{future},,,,,\n",
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, "scripts/validate_kernel.py"],
                cwd=work,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("is in the future", result.stderr)

    def test_missing_registry_path_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / "workroot"
            shutil.copytree(
                ROOT,
                work,
                ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
            )
            registry = work / ".workroot/runtime/index/artifact_registry.csv"
            registry.write_text(
                registry.read_text(encoding="utf-8")
                + "artifact-missing,,,,report,space/work/reports/missing.md,public,active,,,2026-05-14T00:00:00Z,2026-05-14T00:00:00Z\n",
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, "scripts/validate_kernel.py"],
                cwd=work,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("path does not exist", result.stderr)

    def test_related_output_requires_non_template_task_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / "workroot"
            shutil.copytree(
                ROOT,
                work,
                ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
            )
            task_id = "task-20260514-000000-demo"
            task_dir = work / ".workroot/runtime/work/tasks" / task_id
            task_dir.mkdir(parents=True)
            for name, content in {
                "brief.md": "# Brief\n\nTask created; no work completed yet.\n\nNothing yet.\n",
                "handoff.md": "# Handoff\n\nShort continuation status.\n\nWhat should happen next?\n",
                "todo.md": "# Todo\n\n- [ ] Define next step\n",
                "index.md": "# Index\n",
            }.items():
                (task_dir / name).write_text(content, encoding="utf-8")
            report = work / "space/work/reports/demo.md"
            report.parent.mkdir(parents=True, exist_ok=True)
            report.write_text("# Demo\n", encoding="utf-8")
            (work / ".workroot/runtime/index/task_registry.csv").write_text(
                "task_id,title,status,process_level,owner_scope,visibility,priority,created_at,updated_at,user_visible_output_path,source_path,brief_path,handoff_path,next_action\n"
                f"{task_id},Demo,active,L0,personal,internal,,2026-05-14T00:00:00Z,2026-05-14T00:00:00Z,,.workroot/runtime/work/tasks/{task_id},.workroot/runtime/work/tasks/{task_id}/brief.md,.workroot/runtime/work/tasks/{task_id}/handoff.md,\n",
                encoding="utf-8",
            )
            (work / ".workroot/runtime/index/artifact_registry.csv").write_text(
                "artifact_id,task_id,run_id,action_id,type,path,audience,status,size,checksum,created_at,updated_at\n"
                f"artifact-demo,{task_id},,,report,space/work/reports/demo.md,internal,active,,,2026-05-14T00:00:00Z,2026-05-14T00:00:00Z\n",
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, "scripts/validate_kernel.py"],
                cwd=work,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("empty user_visible_output_path", result.stderr)
            self.assertIn("template placeholders", result.stderr)

    def test_invalid_process_level_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / "workroot"
            shutil.copytree(
                ROOT,
                work,
                ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
            )
            registry = work / ".workroot/runtime/index/task_registry.csv"
            registry.write_text(
                registry.read_text(encoding="utf-8")
                + "task-bad,Bad,active,L9,personal,internal,,2026-05-15T00:00:00Z,2026-05-15T00:00:00Z,,.workroot/runtime/work/tasks/task-bad,.workroot/runtime/work/tasks/task-bad/brief.md,.workroot/runtime/work/tasks/task-bad/handoff.md,\n",
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, "scripts/validate_kernel.py"],
                cwd=work,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("invalid process_level", result.stderr)

    def test_broken_work_process_reference_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / "workroot"
            shutil.copytree(
                ROOT,
                work,
                ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
            )
            registry = work / ".workroot/runtime/index/action_registry.csv"
            registry.write_text(
                registry.read_text(encoding="utf-8")
                + "action-bad,missing-task,,test_run,active,Bad action,,,,,low,2026-05-15T00:00:00Z,2026-05-15T00:00:00Z\n",
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, "scripts/validate_kernel.py"],
                cwd=work,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("unknown task_id", result.stderr)

    def test_invalid_tombstone_registry_state_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / "workroot"
            shutil.copytree(
                ROOT,
                work,
                ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
            )
            registry = work / ".workroot/runtime/index/mind_registry.csv"
            registry.write_text(
                registry.read_text(encoding="utf-8")
                + "mind-tombstone,Tombstone,tombstone,released,released,sensitive,tombstone,,2026-05-15T00:00:00Z,2026-05-15T00:00:00Z,space/mind/released/tombstone.md,,\n",
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, "scripts/validate_kernel.py"],
                cwd=work,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("tombstone entries must use temperature=tombstone", result.stderr)
            self.assertIn("tombstone entries require retrieval_rule", result.stderr)

    def test_deleted_registry_entry_with_source_path_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / "workroot"
            shutil.copytree(
                ROOT,
                work,
                ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
            )
            registry = work / ".workroot/runtime/index/mind_registry.csv"
            registry.write_text(
                registry.read_text(encoding="utf-8")
                + "mind-deleted,Deleted,released,released,deleted,sensitive,deleted,never,2026-05-15T00:00:00Z,2026-05-15T00:00:00Z,space/mind/released/deleted.md,,\n",
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, "scripts/validate_kernel.py"],
                cwd=work,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("deleted entries must not keep source_path details", result.stderr)

    def test_tombstone_release_level_requires_tombstone_type_and_temperature(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / "workroot"
            shutil.copytree(
                ROOT,
                work,
                ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
            )
            registry = work / ".workroot/runtime/index/mind_registry.csv"
            registry.write_text(
                registry.read_text(encoding="utf-8")
                + "mind-mixed,Tombstone Mismatch,released,released,released,sensitive,tombstone,explicit_request,2026-05-15T00:00:00Z,2026-05-15T00:00:00Z,space/mind/released/tombstone.md,,\n",
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, "scripts/validate_kernel.py"],
                cwd=work,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("tombstone entries must use type=tombstone", result.stderr)
            self.assertIn("tombstone entries must use temperature=tombstone", result.stderr)


if __name__ == "__main__":
    unittest.main()
