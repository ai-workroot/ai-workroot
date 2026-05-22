from __future__ import annotations

import unittest

from tests.support.cli import run_workroot_cli


class ContextCliSmokeTest(unittest.TestCase):
    def test_context_help_exposes_hard_token_limit(self) -> None:
        result = run_workroot_cli({}, "context", "--help")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--hard-token-limit", result.stdout)
        self.assertIn("--target-tokens", result.stdout)

    def test_context_hard_token_limit_has_final_estimator_fallback(self) -> None:
        from ai_workroot.runtime.context import _enforce_hard_token_limit, estimate_tokens

        rendered = "# AI Workroot Context Package\n" + ("这是没有空格的中文内容" * 100)

        trimmed, steps = _enforce_hard_token_limit(rendered, 1)

        self.assertIn("final-fallback", steps)
        self.assertLessEqual(estimate_tokens(trimmed), 1)
        self.assertNotEqual(trimmed.strip(), "")


if __name__ == "__main__":
    unittest.main()
