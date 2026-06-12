from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import os
import subprocess

from tests.e2e import harness
from tests.e2e.harness import REPO_ROOT, env_for, run_cli
from tests.e2e.personas import Persona
from tests.e2e.harness import validate_user_directory
from tests.e2e.safety import (
    E2E_RUNNER_ACTIVE_ENV,
    classify_shell_command,
    default_sandbox_base,
    ensure_not_real_repo_cwd_for_live_e2e,
    new_default_run_root,
    prepare_run_root,
    safe_quarantine_owned_path,
    validate_run_root,
)


class E2ESafetyTest(unittest.TestCase):
    def test_validate_run_root_rejects_empty_current_root_and_repo_paths(self) -> None:
        unsafe = (
            "",
            ".",
            "..",
            "/",
            str(Path.home()),
            str(REPO_ROOT),
            str(REPO_ROOT.parent),
            str(REPO_ROOT.parent.parent),
        )

        for value in unsafe:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    validate_run_root(Path(value))

    def test_validate_run_root_rejects_paths_inside_repository(self) -> None:
        with self.assertRaises(ValueError):
            validate_run_root(REPO_ROOT / "reports" / "e2e-run")

    def test_default_run_root_uses_home_tmp_sandbox_base(self) -> None:
        base = default_sandbox_base()

        self.assertEqual(base, Path.home() / "tmp" / "ai-workroot-e2e-sandboxes")

    def test_new_default_run_root_uses_unique_run_directory_under_sandbox_base(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "ai-workroot-e2e-sandboxes"

            first = new_default_run_root(base=base)
            second = new_default_run_root(base=base)

            self.assertEqual(first.parent, base.resolve())
            self.assertEqual(second.parent, base.resolve())
            self.assertNotEqual(first, second)
            self.assertTrue(first.name.startswith("run-"))
            self.assertRegex(first.name, r"^run-\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}-[0-9a-f]{8}$")

    def test_prepare_run_root_creates_sandbox_and_owned_sentinels(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sandbox_base = Path(tmp) / "ai-workroot-e2e-sandboxes"
            run_root = new_default_run_root(base=sandbox_base)

            prepared = prepare_run_root(run_root, sandbox_base=sandbox_base)

            self.assertEqual(prepared, run_root.resolve())
            self.assertTrue((prepared / ".ai-workroot-e2e-sandbox").is_file())
            for name in ("ai-workroot-home", "home", "user-dirs", "reports", "transcripts"):
                self.assertTrue((prepared / name / ".ai-workroot-owned").is_file())

    def test_prepare_run_root_rejects_run_directory_outside_sandbox_base(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                prepare_run_root(Path(tmp) / "run-outside")

    def test_prepare_run_root_rejects_non_run_named_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sandbox_base = Path(tmp) / "ai-workroot-e2e-sandboxes"
            with self.assertRaises(ValueError):
                prepare_run_root(sandbox_base, sandbox_base=sandbox_base)

    def test_prepare_existing_run_root_quarantines_owned_contents(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sandbox_base = Path(tmp) / "ai-workroot-e2e-sandboxes"
            run_root = prepare_run_root(new_default_run_root(base=sandbox_base), sandbox_base=sandbox_base)
            old_file = run_root / "user-dirs" / "old.txt"
            old_file.write_text("old", encoding="utf-8")

            prepare_run_root(run_root, sandbox_base=sandbox_base)

            self.assertFalse(old_file.exists())
            quarantine = run_root / "reports" / "quarantine"
            self.assertTrue(any(path.name == "user-dirs" for path in quarantine.rglob("*")))

    def test_quarantine_rejects_missing_owned_sentinel(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sandbox_base = Path(tmp) / "ai-workroot-e2e-sandboxes"
            run_root = prepare_run_root(new_default_run_root(base=sandbox_base), sandbox_base=sandbox_base)
            target = run_root / "unsafe-owned"
            target.mkdir()

            with self.assertRaises(ValueError):
                safe_quarantine_owned_path(target, run_root=run_root, sandbox_base=sandbox_base)

    def test_env_for_isolates_home_under_run_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sandbox_base = Path(tmp) / "ai-workroot-e2e-sandboxes"
            run_root = prepare_run_root(new_default_run_root(base=sandbox_base), sandbox_base=sandbox_base)

            env = env_for(run_root / "ai-workroot-home")

            self.assertEqual(env["AI_WORKROOT_HOME"], str(run_root / "ai-workroot-home"))
            self.assertEqual(env["HOME"], str(run_root / "home"))

    def test_run_cli_records_timeout_result_without_hanging(self) -> None:
        original_run = harness.subprocess.run

        def fake_run(*args: object, **kwargs: object) -> object:
            raise subprocess.TimeoutExpired(cmd=("python", "-m", "ai_workroot"), timeout=0.01, output="partial")

        harness.subprocess.run = fake_run
        self.addCleanup(setattr, harness.subprocess, "run", original_run)

        result = run_cli(("status",), env={}, timeout_seconds=0.01)

        self.assertTrue(result.timed_out)
        self.assertGreaterEqual(result.elapsed_ms, 0)
        self.assertEqual(result.returncode, 124)
        self.assertIn("partial", result.stdout)
        self.assertTrue(result.as_dict()["timed_out"])

    def test_persona_smoke_case_skips_without_explicit_runner_marker(self) -> None:
        previous_marker = os.environ.pop(E2E_RUNNER_ACTIVE_ENV, None)
        previous_run_root = os.environ.pop("AI_WORKROOT_E2E_RUN_ROOT", None)
        previous_sandbox = os.environ.pop("AI_WORKROOT_E2E_SANDBOX_BASE", None)
        try:
            suite = unittest.defaultTestLoader.loadTestsFromName(
                "tests.e2e.persona_smoke_cases.PersonaSmokeE2ETest."
                "test_persona_smoke_creates_five_level2_workroots_and_reports_success"
            )
            result = unittest.TestResult()

            suite.run(result)

            self.assertEqual(len(result.skipped), 1)
            self.assertEqual(result.failures, [])
            self.assertEqual(result.errors, [])
        finally:
            if previous_marker is not None:
                os.environ[E2E_RUNNER_ACTIVE_ENV] = previous_marker
            if previous_run_root is not None:
                os.environ["AI_WORKROOT_E2E_RUN_ROOT"] = previous_run_root
            if previous_sandbox is not None:
                os.environ["AI_WORKROOT_E2E_SANDBOX_BASE"] = previous_sandbox

    def test_user_directory_validation_allows_preexisting_user_owned_state_like_names(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            user_directory = Path(tmp) / "user"
            ai_workroot_home = Path(tmp) / "ai-workroot-home"
            for name in ("logs", "cache", "state", "context"):
                path = user_directory / name
                path.mkdir(parents=True, exist_ok=True)
                (path / "user-owned.txt").write_text("user asset\n", encoding="utf-8")
            persona = Persona(
                slug="persona-test",
                name="Persona Test",
                workroot_id="wr_persona_test",
                native_agent_entry=False,
                user_files={},
            )

            failures = validate_user_directory(persona, user_directory, ai_workroot_home)

            self.assertEqual(failures, [])

    def test_classify_shell_command_rejects_destructive_and_same_line_env_reference(self) -> None:
        self.assertEqual(
            classify_shell_command('RUN_ROOT=/x python3 -m tests.e2e.longrun --run-root "$RUN_ROOT"').classification,
            "forbidden",
        )
        self.assertEqual(classify_shell_command("rm -rf some-dir").classification, "destructive")
        self.assertEqual(classify_shell_command(("python3", "-m", "tests.e2e.longrun")).classification, "safe")

    def test_live_e2e_rejects_real_repository_cwd(self) -> None:
        with self.assertRaises(ValueError):
            ensure_not_real_repo_cwd_for_live_e2e(REPO_ROOT)

    def test_e2e_runner_lists_live_agent_suite_when_explicitly_enabled(self) -> None:
        from tests.e2e.runner import SUITES

        self.assertIn("live-agent", SUITES)

    def test_e2e_runner_lists_live_protocol_suite_when_explicitly_enabled(self) -> None:
        from tests.e2e.runner import SUITES

        self.assertIn("live-protocol", SUITES)

    def test_e2e_runner_lists_live_task_continuity_suite_when_explicitly_enabled(self) -> None:
        from tests.e2e.runner import REMOTE_LLM_SUITES, SUITES

        self.assertIn("live-task-continuity", SUITES)
        self.assertIn("live-task-continuity", REMOTE_LLM_SUITES)

    def test_live_protocol_requires_remote_llm_opt_in(self) -> None:
        from tests.e2e.runner import main

        previous_run = os.environ.get("AI_WORKROOT_RUN_E2E")
        previous_remote = os.environ.get("AI_WORKROOT_E2E_ALLOW_REMOTE_LLM")
        try:
            os.environ["AI_WORKROOT_RUN_E2E"] = "1"
            os.environ.pop("AI_WORKROOT_E2E_ALLOW_REMOTE_LLM", None)
            with tempfile.TemporaryDirectory() as tmp:
                sandbox_base = Path(tmp) / "sandboxes"
                run_root = sandbox_base / "run-live-protocol-opt-in"

                rc = main(
                    [
                        "--suite",
                        "live-protocol",
                        "--dry-run",
                        "--sandbox-base",
                        str(sandbox_base),
                        "--run-root",
                        str(run_root),
                    ]
                )

            self.assertEqual(rc, 2)
        finally:
            if previous_run is None:
                os.environ.pop("AI_WORKROOT_RUN_E2E", None)
            else:
                os.environ["AI_WORKROOT_RUN_E2E"] = previous_run
            if previous_remote is None:
                os.environ.pop("AI_WORKROOT_E2E_ALLOW_REMOTE_LLM", None)
            else:
                os.environ["AI_WORKROOT_E2E_ALLOW_REMOTE_LLM"] = previous_remote

    def test_e2e_runner_accepts_live_task_role_and_rounds_in_dry_run(self) -> None:
        from tests.e2e.runner import main

        previous_run = os.environ.get("AI_WORKROOT_RUN_E2E")
        previous_remote = os.environ.get("AI_WORKROOT_E2E_ALLOW_REMOTE_LLM")
        try:
            os.environ["AI_WORKROOT_RUN_E2E"] = "1"
            os.environ["AI_WORKROOT_E2E_ALLOW_REMOTE_LLM"] = "1"
            with tempfile.TemporaryDirectory() as tmp:
                sandbox_base = Path(tmp) / "sandboxes"
                run_root = sandbox_base / "run-live-task-role-dry-run"

                rc = main(
                    [
                        "--suite",
                        "live-task-continuity",
                        "--dry-run",
                        "--rounds",
                        "50",
                        "--role",
                        "live-founder-operator",
                        "--sandbox-base",
                        str(sandbox_base),
                        "--run-root",
                        str(run_root),
                    ]
                )

            self.assertEqual(rc, 0)
        finally:
            if previous_run is None:
                os.environ.pop("AI_WORKROOT_RUN_E2E", None)
            else:
                os.environ["AI_WORKROOT_RUN_E2E"] = previous_run
            if previous_remote is None:
                os.environ.pop("AI_WORKROOT_E2E_ALLOW_REMOTE_LLM", None)
            else:
                os.environ["AI_WORKROOT_E2E_ALLOW_REMOTE_LLM"] = previous_remote


if __name__ == "__main__":
    unittest.main()
