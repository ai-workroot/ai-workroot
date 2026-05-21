from __future__ import annotations

import csv
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from ai_workroot.runtime.legacy_seed import upgrade

from tests.fixtures.public_seed import PUBLIC_SEED, copy_repo_with_public_seed


ROOT = Path(__file__).resolve().parents[1]


class UpgradeWorkrootTest(unittest.TestCase):
    def test_package_upgrade_exports_upgrade_function(self) -> None:
        self.assertTrue(callable(upgrade.upgrade))

    def test_upgrade_preserves_instance_content_and_migrates_legacy_task_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "founder-space"
            copy_repo_with_public_seed(target)

            (target / ".workroot/kernel/VERSION").write_text("0.9.527\n", encoding="utf-8")
            legacy_task = target / ".workroot/runtime/work/active/task-legacy"
            legacy_task.mkdir(parents=True, exist_ok=True)
            (legacy_task / "task.md").write_text("# Legacy Task\n", encoding="utf-8")
            (legacy_task / "brief.md").write_text("# Brief\n", encoding="utf-8")
            (legacy_task / "todo.md").write_text("# Todo\n", encoding="utf-8")
            (legacy_task / "handoff.md").write_text("# Handoff\n\n## Next Step\n\nContinue legacy work.\n", encoding="utf-8")
            (legacy_task / "index.md").write_text("# Index\n", encoding="utf-8")
            (legacy_task / "decisions.md").write_text("# Decisions\n", encoding="utf-8")
            (legacy_task / "scratch.md").write_text("# Scratch\n", encoding="utf-8")
            (legacy_task / "task.json").write_text(
                '{"task_id":"task-legacy","title":"Legacy task","status":"active"}\n',
                encoding="utf-8",
            )
            (target / ".workroot/runtime/work/tasks").mkdir(parents=True, exist_ok=True)
            shutil.rmtree(target / ".workroot/runtime/work/tasks")
            (target / ".workroot/runtime/work/closed").mkdir(parents=True, exist_ok=True)
            (target / ".workroot/runtime/work/closed/.gitkeep").write_text("", encoding="utf-8")
            (target / ".workroot/runtime/index/task_registry.csv").write_text(
                "task_id,title,status,owner_scope,visibility,created_at,updated_at,user_visible_output_path,source_path,handoff_path\n"
                "task-legacy,Legacy task,active,organization,internal,2026-05-15T00:00:00Z,2026-05-15T00:00:00Z,space/work/legacy.md,.workroot/runtime/work/active/task-legacy,.workroot/runtime/work/active/task-legacy/handoff.md\n",
                encoding="utf-8",
            )

            local_doc = target / "docs/superpowers/specs/local-founder-note.md"
            local_doc.parent.mkdir(parents=True, exist_ok=True)
            local_doc.write_text("# Local Founder Note\n", encoding="utf-8")
            profile = target / "space/profile/profile.md"
            profile.write_text("# Profile\n\nFounder-specific profile.\n", encoding="utf-8")
            work_output = target / "space/work/local-output.md"
            work_output.write_text("# Local Output\n", encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/upgrade_workroot.py"),
                    "--source",
                    str(PUBLIC_SEED),
                    "--target",
                    str(target),
                    "--backup-dir",
                    str(Path(tmp) / "backup"),
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

            self.assertEqual((target / ".workroot/kernel/VERSION").read_text(encoding="utf-8").strip(), "0.9.528")
            self.assertEqual(profile.read_text(encoding="utf-8"), "# Profile\n\nFounder-specific profile.\n")
            self.assertTrue(work_output.exists())
            self.assertTrue(local_doc.exists())
            self.assertTrue((target / ".workroot/runtime/work/tasks/task-legacy").is_dir())
            self.assertFalse((target / ".workroot/runtime/work/active").exists())
            self.assertFalse((target / ".workroot/runtime/work/closed").exists())

            with (target / ".workroot/runtime/index/task_registry.csv").open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(rows[0]["process_level"], "L0")
            self.assertEqual(rows[0]["source_path"], ".workroot/runtime/work/tasks/task-legacy")
            self.assertEqual(rows[0]["brief_path"], ".workroot/runtime/work/tasks/task-legacy/brief.md")
            self.assertEqual(rows[0]["handoff_path"], ".workroot/runtime/work/tasks/task-legacy/handoff.md")


if __name__ == "__main__":
    unittest.main()
