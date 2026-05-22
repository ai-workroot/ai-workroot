from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from ai_workroot.indexing.providers.candidate_provider import upsert_context_candidate
from ai_workroot.indexing.providers.context_recall_hint_provider import ContextRecallHint, upsert_context_recall_hint
from ai_workroot.runtime.context import ContextRequest, build_context_package
from ai_workroot.runtime.init import initialize_workroot


class ContextReleaseFilteringTest(unittest.TestCase):
    def test_fallback_is_disabled_after_protected_release_drop(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            user_dir.mkdir()
            (user_dir / "redacted-payroll-secret.md").write_text("fallback should not expose this filename\n", encoding="utf-8")
            init = initialize_workroot(name="Demo", directory=user_dir, native_agent_entry=False, ai_workroot_home=home)
            workroot_id = init.registration.workroot_id
            db_path = next((home / "workroots").glob("*/cache/workroot.sqlite"))
            with sqlite3.connect(db_path) as conn:
                upsert_context_candidate(
                    conn,
                    {
                        "candidate_id": "cand-protected-only",
                        "workroot_id": workroot_id,
                        "source_type": "asset",
                        "source_id": "asset-protected-only",
                        "title": "Redacted payroll secret",
                        "summary": "Protected candidate should be dropped.",
                        "importance": "critical",
                        "context_policy": "always",
                    },
                )
                conn.execute(
                    """
                    INSERT INTO release_records (release_id, workroot_id, target_type, target_id, release_level, recall_rule)
                    VALUES ('rel-protected-only', ?, 'asset', 'asset-protected-only', 'redacted', 'ordinary-context-excluded')
                    """,
                    (workroot_id,),
                )
                conn.commit()

            package = build_context_package(
                ContextRequest(agent="codex", cwd=user_dir, query="payroll", debug=True),
                ai_workroot_home=home,
            )

            self.assertNotIn("redacted-payroll-secret.md", package)
            self.assertIn("- No context candidates selected.", package)
            self.assertIn("fallbackUserAssetCandidates: attempted=false reason=disabled_due_to_release_protected_drop", package)
            with sqlite3.connect(db_path) as conn:
                trace_json = conn.execute("SELECT debug_json FROM context_traces ORDER BY rowid DESC LIMIT 1").fetchone()[0]
            import json

            trace = json.loads(trace_json)
            self.assertEqual(
                trace["fallbackUserAssetCandidates"],
                {"attempted": False, "reason": "disabled_due_to_release_protected_drop"},
            )

    def test_redacted_context_recall_hint_target_is_excluded_from_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            init = initialize_workroot(name="Demo", directory=user_dir, native_agent_entry=False, ai_workroot_home=home)
            workroot_id = init.registration.workroot_id
            db_path = next((home / "workroots").glob("*/cache/workroot.sqlite"))
            with sqlite3.connect(db_path) as conn:
                upsert_context_recall_hint(
                    conn,
                    ContextRecallHint(
                        hint_id="hint-redacted-target",
                        workroot_id=workroot_id,
                        target_type="task",
                        target_id="task-redacted",
                        title="Redacted target hint",
                        summary="This should be blocked through its target release state.",
                        priority="critical",
                        recall_rule="always",
                    ),
                )
                conn.execute(
                    """
                    INSERT INTO redactions (
                      redaction_id, workroot_id, target_type, target_id, redacted_fields, redaction_reason
                    )
                    VALUES ('redact-task', ?, 'task', 'task-redacted', 'summary', 'test')
                    """,
                    (workroot_id,),
                )

            package = build_context_package(
                ContextRequest(agent="codex", cwd=user_dir, query="target", debug=True),
                ai_workroot_home=home,
            )

            self.assertNotIn("Redacted target hint", package)
            self.assertIn("releaseFilters: dropped=hint:hint-redacted-target:redacted", package)

    def test_tombstone_context_recall_hint_target_is_annotated_not_hard_excluded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            init = initialize_workroot(name="Demo", directory=user_dir, native_agent_entry=False, ai_workroot_home=home)
            workroot_id = init.registration.workroot_id
            db_path = next((home / "workroots").glob("*/cache/workroot.sqlite"))
            with sqlite3.connect(db_path) as conn:
                upsert_context_recall_hint(
                    conn,
                    ContextRecallHint(
                        hint_id="hint-tombstone-target",
                        workroot_id=workroot_id,
                        target_type="task",
                        target_id="task-tombstone",
                        title="Tombstone target hint",
                        summary="This should stay recallable with tombstone annotation.",
                        priority="critical",
                        recall_rule="always",
                    ),
                )
                conn.execute(
                    """
                    INSERT INTO tombstones (
                      tombstone_id, workroot_id, target_type, target_id, title, symbolic_note
                    )
                    VALUES ('tomb-task', ?, 'task', 'task-tombstone', 'Old task', 'kept as tombstone')
                    """,
                    (workroot_id,),
                )

            package = build_context_package(
                ContextRequest(agent="codex", cwd=user_dir, query="tombstone", debug=True),
                ai_workroot_home=home,
            )

            self.assertIn("Tombstone target hint", package)
            self.assertIn("annotated-release-state", package)
            self.assertIn("releaseFilters: dropped=none annotated=hint-tombstone-target", package)


if __name__ == "__main__":
    unittest.main()
