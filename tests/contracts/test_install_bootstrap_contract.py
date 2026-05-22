from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests.contracts.helpers import ROOT


class InstallBootstrapContractTest(unittest.TestCase):
    def test_install_and_bootstrap_scripts_exist(self) -> None:
        expected = [
            ROOT / "install/unix/install.sh",
            ROOT / "install/windows/install.ps1",
            ROOT / "scripts/dev/bootstrap-dev.sh",
            ROOT / "scripts/dev/bootstrap-dev.ps1",
        ]

        for path in expected:
            self.assertTrue(path.exists(), f"missing script: {path}")

    def test_install_script_help_and_dry_run_do_not_write_wrapper(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            install_dir = Path(tmp) / "bin"
            env = {**os.environ, "AI_WORKROOT_INSTALL_DIR": str(install_dir)}

            help_result = subprocess.run(
                [str(ROOT / "install/unix/install.sh"), "--help"],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            dry_run_result = subprocess.run(
                [str(ROOT / "install/unix/install.sh"), "--dry-run"],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(help_result.returncode, 0, help_result.stderr)
            self.assertIn("CLI wrapper installer", help_result.stdout)
            self.assertEqual(dry_run_result.returncode, 0, dry_run_result.stderr)
            self.assertIn("would install", dry_run_result.stdout)
            self.assertFalse((install_dir / "workroot").exists())

    def test_local_bootstrap_state_is_ignored(self) -> None:
        gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")

        self.assertIn(".ai-workroot-local/", gitignore.splitlines())

    def test_windows_powershell_validation_gap_is_documented(self) -> None:
        checklist = (ROOT / "docs/release-checklist.md").read_text(encoding="utf-8")

        self.assertIn("Windows PowerShell parse validation is pending", checklist)
        self.assertIn("install/windows/install.ps1", checklist)
        self.assertIn("scripts/dev/bootstrap-dev.ps1", checklist)


if __name__ == "__main__":
    unittest.main()
