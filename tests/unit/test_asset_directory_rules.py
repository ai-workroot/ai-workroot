from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ai_workroot.capabilities.assets.rules import (
    DEFAULT_OUTPUT_DIRECTORY,
    GUIDE_FILENAME,
    ensure_default_asset_rules,
    load_asset_rules,
)


class AssetDirectoryRulesTest(unittest.TestCase):
    def test_ensure_default_asset_rules_creates_output_directory_guide_and_rule(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "state"
            user_dir = root / "user"
            user_dir.mkdir()

            ensure_default_asset_rules(state_directory=state_dir, user_directory=user_dir, workroot_id="wr_demo")

            output_dir = user_dir / DEFAULT_OUTPUT_DIRECTORY
            guide = output_dir / GUIDE_FILENAME
            self.assertTrue(output_dir.is_dir())
            self.assertTrue(guide.is_file())
            guide_text = guide.read_text(encoding="utf-8")
            self.assertIn("Put future reports in reports/.", guide_text)
            self.assertIn("Build a local knowledge index for docs/.", guide_text)
            self.assertNotIn("SQLite", guide_text)
            self.assertNotIn("lease", guide_text.lower())

            rules = load_asset_rules(state_dir)
            self.assertEqual(len(rules.rules), 1)
            rule = rules.rules[0]
            self.assertEqual(rule.role, "default_output")
            self.assertEqual(rule.source, "system_default")
            self.assertEqual(rule.path, DEFAULT_OUTPUT_DIRECTORY)
            self.assertTrue(rule.writable)

    def test_user_declared_rule_is_persisted_and_selected_by_asset_kind(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "state"
            user_dir = root / "user"
            user_dir.mkdir()
            ensure_default_asset_rules(state_directory=state_dir, user_directory=user_dir, workroot_id="wr_demo")

            from ai_workroot.capabilities.assets.rules import save_declared_output_rule, select_output_path

            save_declared_output_rule(
                state_directory=state_dir,
                user_directory=user_dir,
                workroot_id="wr_demo",
                asset_kind="report",
                path="reports",
            )

            selected = select_output_path(
                state_directory=state_dir,
                user_directory=user_dir,
                asset_kind="report",
                filename="analysis.md",
            )
            self.assertEqual(selected.relative_path, "reports/analysis.md")
            self.assertFalse((user_dir / "reports").exists())
            selected.ensure_parent()
            self.assertTrue((user_dir / "reports").is_dir())

    def test_select_output_path_rejects_escaping_declared_rule(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "state"
            user_dir = root / "user"
            user_dir.mkdir()
            ensure_default_asset_rules(state_directory=state_dir, user_directory=user_dir, workroot_id="wr_demo")

            from ai_workroot.capabilities.assets.rules import save_declared_output_rule

            with self.assertRaisesRegex(ValueError, "relative"):
                save_declared_output_rule(
                    state_directory=state_dir,
                    user_directory=user_dir,
                    workroot_id="wr_demo",
                    asset_kind="report",
                    path="/tmp/reports",
                )


if __name__ == "__main__":
    unittest.main()
