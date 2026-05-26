from __future__ import annotations

import os
import unittest
from pathlib import Path

from tests.e2e.live_agent import REQUIRED_CONTEXT_COMMAND, run_codex_live_agent


class LiveAgentE2ETest(unittest.TestCase):
    def test_codex_client_runs_inside_sandbox_workroot(self) -> None:
        run_root = os.environ.get("AI_WORKROOT_E2E_RUN_ROOT")
        sandbox_base = os.environ.get("AI_WORKROOT_E2E_SANDBOX_BASE")
        if not run_root or not sandbox_base:
            self.fail("live-agent E2E must run through tests.e2e.runner")

        result = run_codex_live_agent(run_root=Path(run_root), sandbox_base=Path(sandbox_base))

        self.assertEqual(result.returncode, 0, result.stderr_path.read_text(encoding="utf-8"))
        self.assertTrue(result.last_message_path.is_file())
        self.assertIn("LIVE_AGENT_E2E_OK", result.last_message_path.read_text(encoding="utf-8"))
        self.assertIn(REQUIRED_CONTEXT_COMMAND, result.stderr_path.read_text(encoding="utf-8"))
        self.assertTrue(result.summary_path.is_file())


if __name__ == "__main__":
    unittest.main()
