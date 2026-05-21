from __future__ import annotations

import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class PublicSeedQuarantineSmokeTest(unittest.TestCase):
    def test_public_seed_active_root_is_not_tracked(self) -> None:
        tracked = subprocess.run(
            ["git", "ls-files", "AGENTS.md", "CLAUDE.md", "space/**", ".workroot/**"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(tracked.returncode, 0, tracked.stderr)
        self.assertEqual(tracked.stdout.strip(), "")

    def test_public_seed_history_fixture_is_preserved(self) -> None:
        history = ROOT / "docs/history/public-seed"

        self.assertTrue((history / "AGENTS.md").is_file())
        self.assertTrue((history / "CLAUDE.md").is_file())
        self.assertTrue((history / "space/README.md").is_file())
        self.assertTrue((history / ".workroot/kernel/VERSION").is_file())


if __name__ == "__main__":
    unittest.main()
