from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]


def iter_suite_ids(suite: unittest.TestSuite) -> list[str]:
    ids: list[str] = []
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            ids.extend(iter_suite_ids(item))
        else:
            ids.append(item.id())
    return ids


class E2EOptInPolicyTest(unittest.TestCase):
    def test_default_unittest_discovery_does_not_include_e2e_cases(self) -> None:
        loader = unittest.TestLoader()
        suite = loader.discover(str(ROOT / "tests"), top_level_dir=str(ROOT))
        e2e_ids = [test_id for test_id in iter_suite_ids(suite) if ".e2e." in test_id or test_id.startswith("e2e.")]

        self.assertEqual(e2e_ids, [])

    def test_e2e_directory_has_no_default_discoverable_test_files(self) -> None:
        discoverable = sorted(path.relative_to(ROOT).as_posix() for path in (ROOT / "tests/e2e").glob("test*.py"))

        self.assertEqual(discoverable, [])

    def test_e2e_runner_requires_explicit_environment_opt_in(self) -> None:
        env = dict(os.environ)
        env.pop("AI_WORKROOT_RUN_E2E", None)
        result = subprocess.run(
            [sys.executable, "-m", "tests.e2e.runner", "--suite", "safety", "--dry-run"],
            cwd=ROOT,
            env={**env, "PYTHONPATH": str(ROOT / "src")},
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("E2E tests are opt-in only", result.stderr)

    def test_e2e_runner_lists_suites_when_explicitly_enabled(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "tests.e2e.runner", "--list"],
            cwd=ROOT,
            env={**os.environ, "PYTHONPATH": str(ROOT / "src"), "AI_WORKROOT_RUN_E2E": "1"},
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("safety", result.stdout)
        self.assertIn("persona-smoke", result.stdout)
        self.assertIn("longrun", result.stdout)

    def test_e2e_runner_dry_run_reports_preserved_sandbox_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sandbox_base = Path(tmp) / "ai-workroot-e2e-sandboxes"
            result = subprocess.run(
                [sys.executable, "-m", "tests.e2e.runner", "--suite", "persona-smoke", "--dry-run", "--sandbox-base", str(sandbox_base)],
                cwd=ROOT,
                env={**os.environ, "PYTHONPATH": str(ROOT / "src"), "AI_WORKROOT_RUN_E2E": "1"},
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Selected E2E suites:", result.stdout)
            self.assertIn("Sandbox run root:", result.stdout)
            self.assertIn(str(sandbox_base), result.stdout)

    def test_direct_longrun_entrypoint_requires_explicit_environment_opt_in(self) -> None:
        from tests.e2e import longrun

        env = dict(os.environ)
        env.pop("AI_WORKROOT_RUN_E2E", None)
        with patch.dict(os.environ, env, clear=True):
            with patch.object(sys, "argv", ["longrun"]):
                with patch.object(longrun, "run_longrun") as run_longrun:
                    exit_code = longrun.main()

        self.assertEqual(exit_code, 2)
        run_longrun.assert_not_called()

    def test_direct_longrun_module_subprocess_requires_explicit_environment_opt_in(self) -> None:
        env = dict(os.environ)
        env.pop("AI_WORKROOT_RUN_E2E", None)
        result = subprocess.run(
            [sys.executable, "-m", "tests.e2e.longrun", "--level", "3"],
            cwd=ROOT,
            env={**env, "PYTHONPATH": str(ROOT / "src")},
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("E2E tests are opt-in only", result.stderr)


if __name__ == "__main__":
    unittest.main()
