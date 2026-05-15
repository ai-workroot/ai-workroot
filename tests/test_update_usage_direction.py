import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class UpdateUsageDirectionTest(unittest.TestCase):
    def test_updates_only_profile_file(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / "workroot"
            shutil.copytree(repo, work, ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache"))

            profile = work / "space/profile/profile.md"
            roles = work / "space/profile/roles.md"
            values = work / "space/profile/values.md"
            preferences = work / "space/profile/preferences.md"
            before = {
                roles: roles.read_text(encoding="utf-8"),
                values: values.read_text(encoding="utf-8"),
                preferences: preferences.read_text(encoding="utf-8"),
            }

            subprocess.run(
                [
                    sys.executable,
                    "scripts/update_usage_direction.py",
                    "--direction",
                    "The user wants CTO-level technical collaboration.",
                    "--focus",
                    "Support product-aware engineering judgment, architecture, team execution, technical strategy, delivery tradeoffs, and risk decisions.",
                ],
                cwd=work,
                check=True,
                capture_output=True,
                text=True,
            )

            profile_text = profile.read_text(encoding="utf-8")
            self.assertIn("CTO-level technical collaboration", profile_text)
            self.assertIn("product-aware engineering judgment", profile_text)
            for path, content in before.items():
                self.assertEqual(content, path.read_text(encoding="utf-8"))

    def test_preserves_existing_custom_profile_sections(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / "workroot"
            shutil.copytree(repo, work, ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache"))

            profile = work / "space/profile/profile.md"
            profile.write_text(
                "# Profile\n\n## Subject\n\nExisting subject.\n\n## Custom Boundary\n\nNever overwrite this section.\n",
                encoding="utf-8",
            )

            subprocess.run(
                [
                    sys.executable,
                    "scripts/update_usage_direction.py",
                    "--direction",
                    "The user wants product leadership collaboration.",
                    "--focus",
                    "Support strategy, roadmap, and execution tradeoffs.",
                ],
                cwd=work,
                check=True,
                capture_output=True,
                text=True,
            )

            profile_text = profile.read_text(encoding="utf-8")
            self.assertIn("product leadership collaboration", profile_text)
            self.assertIn("Support strategy, roadmap", profile_text)
            self.assertIn("## Custom Boundary", profile_text)
            self.assertIn("Never overwrite this section.", profile_text)


if __name__ == "__main__":
    unittest.main()
