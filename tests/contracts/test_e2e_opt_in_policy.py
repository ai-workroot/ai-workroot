from __future__ import annotations

import json
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
                [
                    sys.executable,
                    "-m",
                    "tests.e2e.runner",
                    "--suite",
                    "persona-smoke",
                    "--dry-run",
                    "--sandbox-base",
                    str(sandbox_base),
                ],
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

    def test_live_agent_suite_requires_remote_llm_opt_in_even_when_e2e_is_enabled(self) -> None:
        env = dict(os.environ)
        env.pop("AI_WORKROOT_E2E_ALLOW_REMOTE_LLM", None)
        result = subprocess.run(
            [sys.executable, "-m", "tests.e2e.runner", "--suite", "live-agent", "--dry-run"],
            cwd=ROOT,
            env={**env, "PYTHONPATH": str(ROOT / "src"), "AI_WORKROOT_RUN_E2E": "1"},
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("Live-agent E2E requires AI_WORKROOT_E2E_ALLOW_REMOTE_LLM=1", result.stderr)

    def test_live_agent_environment_uses_sandbox_codex_home_by_default(self) -> None:
        from tests.e2e.live_agent import build_live_agent_environment

        with tempfile.TemporaryDirectory() as tmp:
            run_root = Path(tmp) / "run-live"
            run_root.mkdir()
            base_env = {
                "HOME": str(run_root / "home"),
                "AI_WORKROOT_HOME": str(run_root / "ai-workroot-home"),
                "PYTHONPATH": str(ROOT / "src"),
            }
            with patch.dict(os.environ, {"PATH": os.environ.get("PATH", "")}, clear=True):
                live_env = build_live_agent_environment(base_env, run_root=run_root)

            self.assertEqual(live_env["CODEX_HOME"], str(run_root / "home/.codex"))
            self.assertNotEqual(live_env["CODEX_HOME"], str(Path.home() / ".codex"))
            self.assertTrue((run_root / "home/.codex").is_dir())

    def test_live_agent_environment_copies_only_codex_auth_config_and_rules(self) -> None:
        from tests.e2e.live_agent import build_live_agent_environment

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            real_codex_home = base / "real-codex"
            real_codex_home.mkdir()
            for name in ("auth.json", "config.toml", "AGENTS.md"):
                (real_codex_home / name).write_text(f"{name}\n", encoding="utf-8")
            for ignored_name in ("history.jsonl", "logs_2.sqlite", "state_5.sqlite"):
                (real_codex_home / ignored_name).write_text("ignore\n", encoding="utf-8")
            (real_codex_home / "sessions").mkdir()
            (real_codex_home / "sessions/session.jsonl").write_text("ignore\n", encoding="utf-8")
            run_root = base / "run-live"
            run_root.mkdir()
            base_env = {
                "HOME": str(run_root / "home"),
                "AI_WORKROOT_HOME": str(run_root / "ai-workroot-home"),
                "PYTHONPATH": str(ROOT / "src"),
            }
            with patch.dict(
                os.environ, {"PATH": os.environ.get("PATH", ""), "CODEX_HOME": str(real_codex_home)}, clear=True
            ):
                live_env = build_live_agent_environment(base_env, run_root=run_root)

            sandbox_codex_home = Path(live_env["CODEX_HOME"])
            self.assertEqual(
                sorted(path.name for path in sandbox_codex_home.iterdir()), ["AGENTS.md", "auth.json", "config.toml"]
            )
            self.assertFalse((sandbox_codex_home / "history.jsonl").exists())
            self.assertFalse((sandbox_codex_home / "logs_2.sqlite").exists())
            self.assertFalse((sandbox_codex_home / "sessions").exists())

    def test_live_agent_prompt_requires_workroot_context_call(self) -> None:
        from tests.e2e.live_agent import LIVE_AGENT_PROMPT, REQUIRED_CONTEXT_COMMAND

        self.assertIn(REQUIRED_CONTEXT_COMMAND, LIVE_AGENT_PROMPT)
        self.assertIn("Do not inspect README.md directly", LIVE_AGENT_PROMPT)

    def test_live_agent_targets_all_personas(self) -> None:
        from tests.e2e.live_agent import expected_live_agent_persona_slugs
        from tests.e2e.personas import PERSONAS

        self.assertEqual(expected_live_agent_persona_slugs(), tuple(persona.slug for persona in PERSONAS))

    def test_e2e_harness_enables_context_diagnostic_logging_by_default(self) -> None:
        from tests.e2e.harness import env_for
        from tests.e2e.safety import new_default_run_root, prepare_run_root

        with tempfile.TemporaryDirectory() as tmp:
            sandbox_base = Path(tmp) / "ai-workroot-e2e-sandboxes"
            run_root = prepare_run_root(new_default_run_root(base=sandbox_base), sandbox_base=sandbox_base)

            env_for(run_root / "ai-workroot-home")

            config = json.loads((run_root / "ai-workroot-home/config.json").read_text(encoding="utf-8"))
            diagnostics = config["contextControl"]["diagnosticLogging"]
            self.assertTrue(diagnostics["enabled"])
            self.assertTrue(diagnostics["includeRenderedPackage"])
            self.assertTrue(diagnostics["includeTraceSummary"])
            self.assertTrue(diagnostics["includeRetrievalSummary"])
            self.assertTrue(diagnostics["includeTokenEstimate"])
            self.assertEqual(config["contextControl"]["defaultTargetTokens"], 1200)
            self.assertEqual(config["contextControl"]["defaultHardTokenLimit"], 2400)
            self.assertNotIn("paths", config)

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
