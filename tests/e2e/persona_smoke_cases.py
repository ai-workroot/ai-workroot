from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from tests.e2e.persona_smoke import run_persona_smoke
from tests.e2e.safety import new_default_run_root


class PersonaSmokeE2ETest(unittest.TestCase):
    def test_persona_smoke_creates_five_level2_workroots_and_reports_success(self) -> None:
        run_root_env = os.environ.get("AI_WORKROOT_E2E_RUN_ROOT")
        sandbox_base_env = os.environ.get("AI_WORKROOT_E2E_SANDBOX_BASE")
        if run_root_env and sandbox_base_env:
            result = run_persona_smoke(run_root=Path(run_root_env), sandbox_base=Path(sandbox_base_env))
        else:
            with tempfile.TemporaryDirectory() as tmp:
                sandbox_base = Path(tmp) / "ai-workroot-e2e-sandboxes"
                result = run_persona_smoke(run_root=new_default_run_root(base=sandbox_base), sandbox_base=sandbox_base)

        self.assertTrue(result.passed, result.failures)
        self.assertTrue(result.report_path.is_file())
        self.assertIn("Overall: PASS", result.client_report)
        self.assertIn("PersonaCount: 5", result.client_report)


if __name__ == "__main__":
    unittest.main()
