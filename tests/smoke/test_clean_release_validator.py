from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class CleanReleaseValidatorSmokeTest(unittest.TestCase):
    def test_doctor_release_reports_clean_workroot_release_checks(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "ai_workroot", "doctor", "--release"],
            cwd=ROOT,
            env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("AI Workroot release doctor: PASS", result.stdout)
        self.assertIn("import boundaries", result.stdout)
        self.assertIn("Native Agent Entry templates", result.stdout)
        self.assertIn("Release Control context protection", result.stdout)
        self.assertIn("Release Control target protection", result.stdout)
        self.assertIn("Release Control relationship protection", result.stdout)
        self.assertIn("Public Seed quarantine", result.stdout)

    def test_validate_release_script_runs_clean_release_validator(self) -> None:
        result = subprocess.run(
            [str(ROOT / "scripts/dev/validate-release.sh")],
            cwd=ROOT,
            env={
                **os.environ,
                "PATH": f"{ROOT / '.venv/bin'}{os.pathsep}{os.environ.get('PATH', '')}",
                "PYTHONPATH": str(ROOT / "src"),
            },
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Clean Workroot release validation passed", result.stdout)

    def test_setup_dev_script_is_explicit_developer_environment_setup(self) -> None:
        script = ROOT / "scripts/dev/setup-dev.sh"
        result = subprocess.run(["bash", "-n", str(script)], text=True, capture_output=True, check=False)
        text = script.read_text(encoding="utf-8")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('python3 -m pip install -e ".[dev]"', text)
        self.assertIn("AI_WORKROOT_DEV_VENV", text)
        self.assertNotIn("uvx", text)
        self.assertNotIn("workroot init", text)

    def test_release_doctor_fails_tracked_public_seed_root_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            subprocess.run(["git", "init"], cwd=tmp, check=True, capture_output=True)
            repo.mkdir()
            for rel in (
                "src/ai_workroot/core",
                "src/ai_workroot/contracts",
                "src/ai_workroot/runtime",
                "src/ai_workroot/storage",
                "src/ai_workroot/indexing/providers",
                "src/ai_workroot/resources/templates/native_agent_entry",
                "tests/negative",
                "install/unix",
            ):
                (repo / rel).mkdir(parents=True, exist_ok=True)
            for rel in (
                "src/ai_workroot/agent/native_entry.py",
                "tests/negative/test_release_protection_context.py",
                "tests/negative/test_release_protection_targets.py",
                "tests/negative/test_release_protection_relationships.py",
                "install/unix/install.sh",
            ):
                (repo / rel).parent.mkdir(parents=True, exist_ok=True)
                (repo / rel).write_text("", encoding="utf-8")
            (repo / "src/ai_workroot/resources/templates/native_agent_entry/AGENTS.md.template").write_text(
                "", encoding="utf-8"
            )
            (repo / "AGENTS.md").write_text("tracked seed entry\n", encoding="utf-8")
            subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
            subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)

            result = subprocess.run(
                [sys.executable, "-m", "ai_workroot", "doctor", "--release"],
                cwd=repo,
                env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("tracked Public Seed root paths", result.stdout)

    def test_release_doctor_fails_unignored_generated_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            for rel in (
                "src/ai_workroot/core",
                "src/ai_workroot/contracts",
                "src/ai_workroot/runtime",
                "src/ai_workroot/storage",
                "src/ai_workroot/indexing/providers",
                "src/ai_workroot/resources/templates/native_agent_entry",
                "tests/negative",
                "install/unix",
            ):
                (repo / rel).mkdir(parents=True, exist_ok=True)
            for rel in (
                "src/ai_workroot/agent/native_entry.py",
                "tests/negative/test_release_protection_context.py",
                "tests/negative/test_release_protection_targets.py",
                "tests/negative/test_release_protection_relationships.py",
                "install/unix/install.sh",
                "cache/generated.txt",
            ):
                (repo / rel).parent.mkdir(parents=True, exist_ok=True)
                (repo / rel).write_text("", encoding="utf-8")
            (repo / "src/ai_workroot/resources/templates/native_agent_entry/AGENTS.md.template").write_text(
                "", encoding="utf-8"
            )
            subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)

            result = subprocess.run(
                [sys.executable, "-m", "ai_workroot", "doctor", "--release"],
                cwd=repo,
                env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("release surface", result.stdout)
            self.assertIn("cache/generated.txt", result.stdout)

    def test_export_review_zip_excludes_ignored_local_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            output = Path(tmp) / "review.zip"
            subprocess.run(["git", "init", str(repo)], check=True, capture_output=True)
            (repo / "src/ai_workroot/runtime").mkdir(parents=True)
            (repo / "src/ai_workroot/runtime/context.py").write_text("# tracked\n", encoding="utf-8")
            (repo / ".gitignore").write_text(".idea/\n.ai-workroot-local/\n/AGENTS.md\n/CLAUDE.md\n", encoding="utf-8")
            (repo / "scripts/dev").mkdir(parents=True)
            (repo / "scripts/dev/export-review-zip.sh").write_text(
                (ROOT / "scripts/dev/export-review-zip.sh").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            (repo / "scripts/dev/export-review-zip.sh").chmod(0o755)
            (repo / ".ai-workroot-local").mkdir()
            (repo / ".ai-workroot-local/local.txt").write_text("local\n", encoding="utf-8")
            (repo / ".idea").mkdir()
            (repo / ".idea/workspace.xml").write_text("<local />\n", encoding="utf-8")
            (repo / "AGENTS.md").write_text("local agent entry\n", encoding="utf-8")
            (repo / "CLAUDE.md").write_text("local claude entry\n", encoding="utf-8")
            subprocess.run(["git", "add", ".gitignore", "src", "scripts"], cwd=repo, check=True, capture_output=True)
            subprocess.run(
                ["git", "config", "user.name", "AI Workroot Test"], cwd=repo, check=True, capture_output=True
            )
            subprocess.run(
                ["git", "config", "user.email", "ai-workroot-test@example.invalid"],
                cwd=repo,
                check=True,
                capture_output=True,
            )
            subprocess.run(["git", "commit", "-m", "seed"], cwd=repo, check=True, capture_output=True)

            result = subprocess.run(
                [str(repo / "scripts/dev/export-review-zip.sh"), str(output)],
                cwd=repo,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(output.is_file())
            with zipfile.ZipFile(output) as archive:
                names = set(archive.namelist())
            self.assertIn("src/ai_workroot/runtime/context.py", names)
            self.assertNotIn(".ai-workroot-local/local.txt", names)
            self.assertNotIn(".idea/workspace.xml", names)
            self.assertNotIn("AGENTS.md", names)
            self.assertNotIn("CLAUDE.md", names)


if __name__ == "__main__":
    unittest.main()
