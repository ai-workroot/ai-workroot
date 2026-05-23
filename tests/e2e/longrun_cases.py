from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from ai_workroot.runtime.context import ContextRequest, build_context_package
from tests.e2e.longrun import run_longrun
from tests.e2e.persona_smoke import run_persona_smoke
from tests.e2e.safety import new_default_run_root


def _runner_roots() -> tuple[Path, Path] | None:
    run_root = os.environ.get("AI_WORKROOT_E2E_RUN_ROOT")
    sandbox_base = os.environ.get("AI_WORKROOT_E2E_SANDBOX_BASE")
    if not run_root or not sandbox_base:
        return None
    return Path(run_root), Path(sandbox_base)


class LongrunE2ETest(unittest.TestCase):
    def test_level3_longrun_runs_reusable_cases_and_writes_context_audit(self) -> None:
        roots = _runner_roots()
        if roots:
            run_root, sandbox_base = roots
            result = run_longrun(run_root=run_root, sandbox_base=sandbox_base, level=3, tasks_per_persona=6)
        else:
            with tempfile.TemporaryDirectory() as tmp:
                sandbox_base = Path(tmp) / "ai-workroot-e2e-sandboxes"
                result = run_longrun(
                    run_root=new_default_run_root(base=sandbox_base),
                    sandbox_base=sandbox_base,
                    level=3,
                    tasks_per_persona=6,
                )

        self.assertTrue(result.passed, result.failures_path.read_text(encoding="utf-8"))
        self.assertEqual(result.task_count, 30)
        self.assertIn("AI Workroot Level 3 Longrun: PASS", result.client_report)
        audit = result.context_audit_path.read_text(encoding="utf-8")
        self.assertIn('"protectedLeakCount": 0', audit)
        self.assertIn('"zeroTokenUsageCount": 0', audit)

    def test_level4_longrun_scales_to_forty_tasks_and_prints_client_report(self) -> None:
        roots = _runner_roots()
        if roots:
            run_root, sandbox_base = roots
            result = run_longrun(run_root=run_root, sandbox_base=sandbox_base, level=4, tasks_per_persona=8)
        else:
            with tempfile.TemporaryDirectory() as tmp:
                sandbox_base = Path(tmp) / "ai-workroot-e2e-sandboxes"
                result = run_longrun(
                    run_root=new_default_run_root(base=sandbox_base),
                    sandbox_base=sandbox_base,
                    level=4,
                    tasks_per_persona=8,
                )

        self.assertTrue(result.passed, result.failures_path.read_text(encoding="utf-8"))
        self.assertEqual(result.task_count, 40)
        self.assertIn("AI Workroot Level 4 Longrun: PASS", result.client_report)
        self.assertIn("Hard trims:", result.client_report)
        self.assertTrue(any(persona.hard_trim_checks > 0 for persona in result.persona_results))


class ActiveContextRuntimeLongrunTest(unittest.TestCase):
    def test_debug_context_keeps_trace_lines_when_hard_trim_runs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sandbox_base = Path(tmp) / "ai-workroot-e2e-sandboxes"
            smoke = run_persona_smoke(run_root=new_default_run_root(base=sandbox_base), sandbox_base=sandbox_base)
            self.assertTrue(smoke.passed, smoke.failures)
            user_dir = smoke.run_root / "user-dirs/persona-software-engineer"

            package = build_context_package(
                ContextRequest(
                    agent="codex",
                    cwd=user_dir,
                    query="large context trim budget",
                    debug=True,
                    target_tokens=120,
                    hard_token_limit=180,
                ),
                ai_workroot_home=smoke.ai_workroot_home,
            )

            self.assertIn("## Debug Trace", package)
            self.assertIn("candidateSources:", package)
            self.assertIn("scoring:", package)
            self.assertIn("timing:", package)
            self.assertIn("tokenUsage:", package)


if __name__ == "__main__":
    unittest.main()
