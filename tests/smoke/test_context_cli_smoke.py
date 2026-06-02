from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tests.support.cli import run_workroot_cli


class ContextCliSmokeTest(unittest.TestCase):
    def test_context_help_exposes_hard_token_limit(self) -> None:
        result = run_workroot_cli({}, "context", "--help")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--hard-token-limit", result.stdout)
        self.assertIn("--target-tokens", result.stdout)

    def test_context_hard_token_limit_has_final_estimator_fallback(self) -> None:
        from ai_workroot.context.builder import _enforce_hard_token_limit, estimate_tokens

        rendered = "# AI Workroot Context Package\n" + ("unspacedcontextcontent" * 100)

        trimmed, steps = _enforce_hard_token_limit(rendered, 1)

        self.assertIn("final-fallback", steps)
        self.assertLessEqual(estimate_tokens(trimmed), 1)
        self.assertNotEqual(trimmed.strip(), "")

    def test_context_uses_environment_config_budget_when_cli_budget_is_omitted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            home.mkdir()
            (home / "config.json").write_text(
                json.dumps(
                    {
                        "kind": "WorkrootEnvironment",
                        "contextControl": {
                            "defaultTargetTokens": 111,
                            "defaultHardTokenLimit": 222,
                        },
                    }
                ),
                encoding="utf-8",
            )
            env = {"AI_WORKROOT_HOME": str(home)}
            init = run_workroot_cli(
                env, "init", "--name", "Budget", "--directory", str(user_dir), "--no-native-agent-entry"
            )
            self.assertEqual(init.returncode, 0, init.stderr)

            context = run_workroot_cli(env, "context", "--agent", "codex", "--cwd", str(user_dir), "--debug")

            self.assertEqual(context.returncode, 0, context.stderr)
            self.assertIn("TokenUsage:", context.stdout)
            self.assertIn("/222", context.stdout)
            self.assertIn("tokenUsage: estimated=", context.stdout)
            self.assertIn("target=111 hard=222", context.stdout)
            self.assertIn("budgetSource: config", context.stdout)

    def test_context_cli_budget_overrides_environment_config_budget(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            home.mkdir()
            (home / "config.json").write_text(
                json.dumps(
                    {
                        "kind": "WorkrootEnvironment",
                        "contextControl": {
                            "defaultTargetTokens": 111,
                            "defaultHardTokenLimit": 222,
                        },
                    }
                ),
                encoding="utf-8",
            )
            env = {"AI_WORKROOT_HOME": str(home)}
            init = run_workroot_cli(
                env, "init", "--name", "Budget", "--directory", str(user_dir), "--no-native-agent-entry"
            )
            self.assertEqual(init.returncode, 0, init.stderr)

            context = run_workroot_cli(
                env,
                "context",
                "--agent",
                "codex",
                "--cwd",
                str(user_dir),
                "--debug",
                "--target-tokens",
                "333",
                "--hard-token-limit",
                "444",
            )

            self.assertEqual(context.returncode, 0, context.stderr)
            self.assertIn("/444", context.stdout)
            self.assertIn("target=333 hard=444", context.stdout)
            self.assertIn("budgetSource: cli", context.stdout)


if __name__ == "__main__":
    unittest.main()
