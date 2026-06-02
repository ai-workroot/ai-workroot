from __future__ import annotations

import unittest

from ai_workroot.protocol.recovery import derive_run_recovery_state


class ContextRecoveryTest(unittest.TestCase):
    def test_active_run_older_than_six_hours_without_handoff_is_stale(self) -> None:
        state = derive_run_recovery_state(
            run_status="active",
            started_at="2026-05-27T00:00:00Z",
            now="2026-05-27T07:00:00Z",
            has_summary=False,
            has_handoff=False,
        )

        self.assertEqual(state, "stale_active_run")

    def test_incomplete_run_older_than_seven_days_is_old_incomplete(self) -> None:
        state = derive_run_recovery_state(
            run_status="incomplete",
            started_at="2026-05-01T00:00:00Z",
            now="2026-05-27T00:00:00Z",
            has_summary=True,
            has_handoff=False,
        )

        self.assertEqual(state, "old_incomplete_run")


if __name__ == "__main__":
    unittest.main()
