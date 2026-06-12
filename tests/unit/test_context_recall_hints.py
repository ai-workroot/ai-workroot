from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from ai_workroot.capabilities.retrieval.providers.context_recall_hint_provider import (
    ContextRecallHint,
    query_context_recall_hints,
    upsert_context_recall_hint,
)
from ai_workroot.state.sqlite import initialize_workroot_sqlite


class ContextRecallHintsTest(unittest.TestCase):
    def open_db(self) -> sqlite3.Connection:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        db_path = Path(tmp.name) / "workroot.sqlite"
        initialize_workroot_sqlite(db_path)
        return sqlite3.connect(db_path)

    def test_upsert_context_recall_hint_inserts_and_indexes_hint(self) -> None:
        conn = self.open_db()
        hint = ContextRecallHint(
            hint_id="hint-clean-mode",
            workroot_id="wr_demo",
            target_type="asset",
            target_id="asset-clean-mode",
            title="Clean Mode Context Card",
            summary="Recall Clean Mode when user-directory cleanliness is discussed.",
            priority="high",
            recall_rule="always",
        )

        upsert_context_recall_hint(conn, hint)

        row = conn.execute(
            """
            SELECT target_type, target_id, title, summary, priority, recall_rule, lifecycle_status
            FROM context_recall_hints
            WHERE hint_id = ?
            """,
            (hint.hint_id,),
        ).fetchone()
        fts_row = conn.execute(
            """
            SELECT hint_id
            FROM context_recall_hints_fts
            WHERE context_recall_hints_fts MATCH ?
            """,
            ("Clean",),
        ).fetchone()

        self.assertEqual(
            row,
            (
                "asset",
                "asset-clean-mode",
                "Clean Mode Context Card",
                "Recall Clean Mode when user-directory cleanliness is discussed.",
                "high",
                "always",
                "active",
            ),
        )
        self.assertEqual(fts_row[0], "hint-clean-mode")

    def test_upsert_context_recall_hint_does_not_commit_caller_transaction(self) -> None:
        conn = self.open_db()
        hint = ContextRecallHint(
            hint_id="hint-rollback",
            workroot_id="wr_demo",
            target_type="asset",
            target_id="asset-rollback",
            title="Rollback hint",
            summary="This hint should remain under caller transaction control.",
        )

        conn.execute("BEGIN")
        upsert_context_recall_hint(conn, hint)
        conn.rollback()

        hint_row = conn.execute(
            "SELECT hint_id FROM context_recall_hints WHERE hint_id = ?",
            (hint.hint_id,),
        ).fetchone()
        fts_row = conn.execute(
            "SELECT hint_id FROM context_recall_hints_fts WHERE hint_id = ?",
            (hint.hint_id,),
        ).fetchone()

        self.assertIsNone(hint_row)
        self.assertIsNone(fts_row)

    def test_context_recall_hint_is_core_retrieval_model(self) -> None:
        from ai_workroot.capabilities.retrieval.model import ContextRecallHint as CoreContextRecallHint

        self.assertIs(ContextRecallHint, CoreContextRecallHint)

    def test_query_context_recall_hints_filters_workroot_and_lifecycle(self) -> None:
        conn = self.open_db()
        upsert_context_recall_hint(
            conn,
            ContextRecallHint(
                hint_id="hint-active",
                workroot_id="wr_demo",
                target_type="task",
                target_id="task-clean",
                title="Active clean hint",
                summary="Clean Workroot active recall anchor.",
            ),
        )
        upsert_context_recall_hint(
            conn,
            ContextRecallHint(
                hint_id="hint-inactive",
                workroot_id="wr_demo",
                target_type="task",
                target_id="task-inactive",
                title="Inactive clean hint",
                lifecycle_status="archived",
            ),
        )
        upsert_context_recall_hint(
            conn,
            ContextRecallHint(
                hint_id="hint-other-workroot",
                workroot_id="wr_other",
                target_type="task",
                target_id="task-other",
                title="Other clean hint",
            ),
        )

        hints = query_context_recall_hints(conn, "wr_demo", query="clean")

        self.assertEqual([hint.hint_id for hint in hints], ["hint-active"])
        self.assertEqual(hints[0].target_type, "task")
        self.assertEqual(hints[0].target_id, "task-clean")

    def test_query_context_recall_hints_handles_cjk_query_without_broad_fallback(self) -> None:
        conn = self.open_db()
        upsert_context_recall_hint(
            conn,
            ContextRecallHint(
                hint_id="hint-office",
                workroot_id="wr_demo",
                target_type="asset",
                target_id="asset-office",
                title="安静办公位",
                summary="下午安静办公位适合低峰时段。",
                priority="high",
            ),
        )
        upsert_context_recall_hint(
            conn,
            ContextRecallHint(
                hint_id="hint-unrelated",
                workroot_id="wr_demo",
                target_type="asset",
                target_id="asset-unrelated",
                title="Unrelated report",
                summary="A different operating note.",
                priority="critical",
            ),
        )

        hints = query_context_recall_hints(conn, "wr_demo", query="为什么选择下午安静办公位？")

        self.assertEqual([hint.hint_id for hint in hints], ["hint-office"])

    def test_query_context_recall_hints_respects_task_scope(self) -> None:
        conn = self.open_db()
        upsert_context_recall_hint(
            conn,
            ContextRecallHint(
                hint_id="hint-task-one",
                workroot_id="wr_demo",
                target_type="task",
                target_id="task-one",
                scope_type="task",
                scope_id="task-one",
                title="Pricing decision",
                summary="Current task pricing context.",
            ),
        )
        upsert_context_recall_hint(
            conn,
            ContextRecallHint(
                hint_id="hint-task-two",
                workroot_id="wr_demo",
                target_type="task",
                target_id="task-two",
                scope_type="task",
                scope_id="task-two",
                title="Pricing decision",
                summary="Other task pricing context.",
                priority="critical",
            ),
        )

        hints = query_context_recall_hints(conn, "wr_demo", query="pricing", scope="task:task-one")

        self.assertEqual([hint.hint_id for hint in hints], ["hint-task-one"])

    def test_query_context_recall_hints_does_not_mutate_connection_row_factory(self) -> None:
        conn = self.open_db()
        upsert_context_recall_hint(
            conn,
            ContextRecallHint(
                hint_id="hint-row-factory",
                workroot_id="wr_demo",
                target_type="task",
                target_id="task-row-factory",
                title="Row factory hint",
            ),
        )

        query_context_recall_hints(conn, "wr_demo")
        row = conn.execute("SELECT hint_id FROM context_recall_hints WHERE hint_id = 'hint-row-factory'").fetchone()

        self.assertEqual(row, ("hint-row-factory",))


if __name__ == "__main__":
    unittest.main()
