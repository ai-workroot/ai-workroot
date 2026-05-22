from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests.support.cli import ROOT


class InstallCliSmokeTest(unittest.TestCase):
    def test_unix_install_wrapper_installs_new_package_entrypoint(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            install_dir = Path(tmp) / "bin"
            env = {**os.environ, "AI_WORKROOT_INSTALL_DIR": str(install_dir)}

            dry_run = subprocess.run(
                [str(ROOT / "install/unix/install.sh"), "--dry-run"],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            install = subprocess.run(
                [str(ROOT / "install/unix/install.sh")],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(dry_run.returncode, 0, dry_run.stderr)
            self.assertIn("Clean Workroot package entrypoint", dry_run.stdout)
            self.assertEqual(install.returncode, 0, install.stderr)
            wrapper = install_dir / "workroot"
            self.assertTrue(wrapper.is_file())
            text = wrapper.read_text(encoding="utf-8")
            self.assertIn("python3 -m ai_workroot", text)
            self.assertNotIn("scripts/compat/workroot_cli.py", text)


if __name__ == "__main__":
    unittest.main()
