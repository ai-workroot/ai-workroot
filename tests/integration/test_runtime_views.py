from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ai_workroot.commands.build_context import build_context
from ai_workroot.protocol.controller import commit, sync
from ai_workroot.state.environment import initialize_environment, register_workroot
from ai_workroot.state.layout import workroot_sqlite_path
from ai_workroot.state.runtime_views import write_context_runtime_view
from ai_workroot.state.sqlite import initialize_workroot_sqlite


CONTEXT_LATEST_PREVIEW_MAX_BYTES = 64 * 1024


class RuntimeViewsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name) / "ai-home"
        self.user_dir = Path(self.tmp.name) / "workspace"
        self.user_dir.mkdir()
        initialize_environment(self.home)
        self.registration = register_workroot(
            self.home,
            workroot_id="wr_demo",
            name="Demo",
            user_directory=self.user_dir,
        )
        initialize_workroot_sqlite(workroot_sqlite_path(Path(self.registration.state_directory)))
        self.previous_home = os.environ.get("AI_WORKROOT_HOME")
        os.environ["AI_WORKROOT_HOME"] = str(self.home)
        self.addCleanup(self.restore_home)

    def restore_home(self) -> None:
        if self.previous_home is None:
            os.environ.pop("AI_WORKROOT_HOME", None)
        else:
            os.environ["AI_WORKROOT_HOME"] = self.previous_home

    def test_commit_and_context_write_rebuildable_runtime_views(self) -> None:
        first_sync = sync(
            {
                "protocol_version": "workroot.v1",
                "request_id": "req-sync-runtime-views",
                "agent": {"name": "codex", "transport": "cli"},
                "cwd": str(self.user_dir),
                "reason": "before_work",
                "query": "Implement runtime views.",
                "work_signal": {"phase": "planning", "work_kind": "task", "intended_action": "plan"},
            }
        )
        intent = commit(
            self.commit_request(
                self.lease_id(first_sync),
                "intent",
                "evt-runtime-intent",
                {
                    "intent_text": "Implement runtime views",
                    "classification": {"persistence": "normal"},
                    "task_hint": {"title": "Runtime Views", "task_id": None, "parent_task_id": None},
                },
            )
        )
        task_id = self.task_id(intent)
        run_id = self.run_id(intent)
        progress = commit(
            self.commit_request(
                self.lease_id(intent),
                "progress",
                "evt-runtime-progress",
                {
                    "task_id": task_id,
                    "run_id": run_id,
                    "summary": "Runtime view writer is wired.",
                    "items_created": [{"title": "Write views", "status": "done", "result_summary": "Views exist."}],
                },
            )
        )
        commit(
            self.commit_request(
                self.lease_id(progress),
                "handoff",
                "evt-runtime-handoff",
                {
                    "task_id": task_id,
                    "run_id": run_id,
                    "current_state": "Runtime views are generated from SQLite.",
                    "next_action": "Review runtime view contents.",
                },
            )
        )

        build_context(agent="codex", cwd=self.user_dir, query="Continue runtime views.", mode="standard")

        state_dir = Path(self.registration.state_directory)
        expected = (
            "state/current.json",
            "tasks/current.json",
            "tasks/active.json",
            "handoffs/current.md",
            "handoffs/current.json",
            "assets/manifest.json",
            "relationships/summary.json",
            "indexes/manifest.json",
            "context/latest.md",
            "context/latest-trace.json",
            "diagnostics/protocol-friction.json",
        )
        for relative in expected:
            with self.subTest(relative=relative):
                self.assertTrue((state_dir / relative).is_file(), relative)

        current_task = json.loads((state_dir / "tasks/current.json").read_text(encoding="utf-8"))
        self.assertEqual(current_task["taskId"], task_id)
        self.assertIn("Runtime view writer is wired.", current_task["summary"])
        self.assertIn("Continue runtime views.", (state_dir / "context/latest-trace.json").read_text(encoding="utf-8"))

    def test_context_latest_markdown_is_bounded_diagnostic_preview(self) -> None:
        state_dir = Path(self.registration.state_directory)
        rendered = "A" * (CONTEXT_LATEST_PREVIEW_MAX_BYTES + 4096)

        write_context_runtime_view(
            state_directory=state_dir,
            rendered=rendered,
            trace={"workrootId": "wr_demo", "query": "large context"},
        )

        latest = (state_dir / "context/latest.md").read_bytes()
        trace = json.loads((state_dir / "context/latest-trace.json").read_text(encoding="utf-8"))
        self.assertLessEqual(len(latest), CONTEXT_LATEST_PREVIEW_MAX_BYTES)
        self.assertTrue(trace["latestContextPreview"]["truncated"])
        self.assertEqual(trace["latestContextPreview"]["renderedBytes"], len(rendered.encode("utf-8")))
        self.assertEqual(trace["latestContextPreview"]["maxBytes"], CONTEXT_LATEST_PREVIEW_MAX_BYTES)

    def test_handoff_on_older_task_becomes_current_runtime_view(self) -> None:
        first = self.create_task(
            sync_id="req-sync-runtime-task-a",
            intent_id="evt-runtime-task-a",
            title="Runtime task A",
            goal="Track runtime task A.",
        )
        task_a = self.task_id(first)
        run_a = self.run_id(first)
        self.commit_progress(
            lease_id=self.lease_id(first),
            event_id="evt-runtime-task-a-progress",
            task_id=task_a,
            run_id=run_a,
            summary="Task A initial progress.",
        )
        second = self.create_task(
            sync_id="req-sync-runtime-task-b",
            intent_id="evt-runtime-task-b",
            title="Start a new task for runtime task B",
            goal="Track runtime task B.",
            switching=True,
        )
        task_b = self.task_id(second)
        run_b = self.run_id(second)
        self.commit_progress(
            lease_id=self.lease_id(second),
            event_id="evt-runtime-task-b-progress",
            task_id=task_b,
            run_id=run_b,
            summary="Task B later progress.",
        )
        with sqlite3.connect(self.sqlite_path()) as conn:
            conn.execute("UPDATE tasks SET updated_at = '2026-05-28T00:01:00Z' WHERE task_id = ?", (task_a,))
            conn.execute("UPDATE tasks SET updated_at = '2026-05-28T00:02:00Z' WHERE task_id = ?", (task_b,))
            conn.commit()

        return_to_a = sync(
            {
                "protocol_version": "workroot.v1",
                "request_id": "req-sync-return-runtime-task-a",
                "agent": {"name": "codex", "transport": "cli"},
                "cwd": str(self.user_dir),
                "reason": "continue",
                "query": "Return to runtime task A and preserve a handoff.",
                "known_state": {"task_id": task_a, "run_id": run_a},
                "work_signal": {"work_kind": "continuation", "intended_action": "preserve"},
            }
        )
        with patch("ai_workroot.capabilities.composition.projections.now_utc", return_value="2026-05-28T00:03:00Z"):
            commit(
                self.commit_request(
                    self.lease_id(return_to_a),
                    "handoff",
                    "evt-runtime-task-a-handoff",
                    {
                        "task_id": task_a,
                        "run_id": run_a,
                        "current_state": "Task A has the newest handoff.",
                        "next_action": "Resume Task A from the handoff.",
                    },
                )
            )

        state_dir = Path(self.registration.state_directory)
        current_task = json.loads((state_dir / "tasks/current.json").read_text(encoding="utf-8"))
        self.assertEqual(current_task["taskId"], task_a)
        self.assertEqual(current_task["currentState"], "Task A has the newest handoff.")

    def create_task(
        self,
        *,
        sync_id: str,
        intent_id: str,
        title: str,
        goal: str,
        switching: bool = False,
    ) -> dict[str, object]:
        sync_response = sync(
            {
                "protocol_version": "workroot.v1",
                "request_id": sync_id,
                "agent": {"name": "codex", "transport": "cli"},
                "cwd": str(self.user_dir),
                "reason": "before_task_switch" if switching else "before_work",
                "query": title,
                "work_signal": {
                    "phase": "switching" if switching else "planning",
                    "work_kind": "task",
                    "intended_action": "plan",
                },
            }
        )
        return commit(
            self.commit_request(
                self.lease_id(sync_response),
                "intent",
                intent_id,
                {
                    "intent_text": goal,
                    "classification": {"persistence": "normal"},
                    "task_hint": {"title": title, "task_id": None, "parent_task_id": None},
                },
            )
        )

    def commit_progress(
        self,
        *,
        lease_id: str,
        event_id: str,
        task_id: str,
        run_id: str,
        summary: str,
    ) -> dict[str, object]:
        return commit(
            self.commit_request(
                lease_id,
                "progress",
                event_id,
                {
                    "task_id": task_id,
                    "run_id": run_id,
                    "summary": summary,
                },
            )
        )

    def sqlite_path(self) -> Path:
        return workroot_sqlite_path(Path(self.registration.state_directory))

    def commit_request(
        self,
        lease_id: str,
        kind: str,
        event_id: str,
        payload: dict[str, object],
    ) -> dict[str, object]:
        return {
            "protocol_version": "workroot.v1",
            "request_id": f"req-{event_id}",
            "exchange_lease_id": lease_id,
            "idempotency_key": f"idem-{event_id}",
            "events": [
                {
                    "event_id": event_id,
                    "kind": kind,
                    "schema_version": f"{kind}.v1",
                    "occurred_at": "2026-05-28T00:00:00Z",
                    "source": {"actor_type": "agent", "actor_name": "codex", "session_id": "session-1"},
                    "confirmation": {"status": "agent_observed", "confirmed_by": None},
                    "payload": payload,
                    "evidence": [],
                }
            ],
        }

    def lease_id(self, response: dict[str, object]) -> str:
        return str(response["workroot_contract"]["commit_contract"]["lease_id"])

    def task_id(self, response: dict[str, object]) -> str:
        return str(response["workroot_contract"]["state_refs"]["task_ref"])

    def run_id(self, response: dict[str, object]) -> str:
        return str(response["workroot_contract"]["state_refs"]["run_ref"])


if __name__ == "__main__":
    unittest.main()
